#!/usr/bin/env python3
"""Bounded external C/P/D utility check for HCL v0.6 on frozen FANToM dev data."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in os.sys.path:
    os.sys.path.insert(0, str(ROOT))

from hcl.v06 import HCLV06Runtime, extract_conversation_events
from scripts.inventory_fantom_external_v02 import load_dataframe
from scripts.run_fantom_external_v02 import build_question_map, parse_binary, parse_mc
from scripts.run_v04_long_horizon_bounded_context_v01 import make_real_backend

SELECTION_FILE = ROOT / "eval/v06/fantom_cpd_selection_v01.json"

MODEL = "deepseek-flash"
BASE_URL = "https://api.deepseek.com"
TEMPERATURE = 0.0
ANSWER_MAX_TOKENS = 64
ADAPTER_MAX_TOKENS = 4096

# These are operational character/call safeguards, not billing tokens.
CAPS = {
    "C": {"calls": 8, "input_chars": 300_000, "output_chars": 10_000},
    "P": {"calls": 8, "input_chars": 320_000, "output_chars": 10_000},
    "D_ADAPTER": {"calls": 16, "input_chars": 320_000, "output_chars": 150_000},
    "D_ANSWER": {"calls": 8, "input_chars": 700_000, "output_chars": 10_000},
}

CONTROL_SYSTEM = (
    "Answer the benchmark task directly from the supplied conversation. "
    "Follow the requested final output format exactly. Do not add explanation."
)

PERSPECTIVE_SYSTEM = (
    "Before answering, internally track who was present for each utterance and "
    "which information each participant could actually access. Do not assume an "
    "absent or not-yet-joined person heard missed content. For second-order "
    "questions, reason about what the outer person can know about the inner "
    "person's access. Then return only the requested final answer format, with "
    "no explanation."
)

D_SYSTEM = (
    "Answer only from the supplied HCL perspective state. Character views are "
    "separate and must not be substituted for one another. Use first_order_views "
    "for what each person could access and second_order_access_event_ids for what "
    "one person has evidence another could access. Do not reconstruct an "
    "omniscient shared conversation. Information exposure does not itself prove "
    "belief acceptance. Return only the requested final answer format."
)


class BudgetExceeded(RuntimeError):
    pass


class CappedBackend:
    def __init__(self, backend: Any, *, name: str, caps: dict[str, int]):
        self.backend = backend
        self.name = name
        self.max_calls = int(caps["calls"])
        self.max_input_chars = int(caps["input_chars"])
        self.max_output_chars = int(caps["output_chars"])

    def _before(self, messages: list[dict[str, str]]) -> None:
        metrics = self.backend.metrics()
        added = sum(len(str(x.get("content", ""))) for x in messages)
        if int(metrics["calls"]) >= self.max_calls:
            raise BudgetExceeded(f"{self.name} call cap reached")
        if int(metrics["input_chars"]) + added > self.max_input_chars:
            raise BudgetExceeded(f"{self.name} input-char cap reached")
        if int(metrics["output_chars"]) >= self.max_output_chars:
            raise BudgetExceeded(f"{self.name} output-char cap reached")

    def _after(self) -> None:
        metrics = self.backend.metrics()
        if int(metrics["output_chars"]) > self.max_output_chars:
            raise BudgetExceeded(f"{self.name} output-char cap exceeded")

    def complete(self, messages, *, max_tokens, temperature=0.0):
        self._before(messages)
        out = self.backend.complete(
            messages, max_tokens=max_tokens, temperature=temperature
        )
        self._after()
        return out

    def complete_json(self, messages, *, max_tokens, temperature=0.0):
        self._before(messages)
        out = self.backend.complete_json(
            messages, max_tokens=max_tokens, temperature=temperature
        )
        self._after()
        return out

    def metrics(self) -> dict[str, Any]:
        return self.backend.metrics()


def _sha_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_selection() -> dict[str, Any]:
    data = json.loads(SELECTION_FILE.read_text(encoding="utf-8"))
    if data.get("selected_count") != 8 or len(data.get("selected", [])) != 8:
        raise RuntimeError("frozen FANToM C/P/D selection must contain 8 rows")
    return data


def build_task(record: dict[str, Any], manifest: dict[str, Any]) -> str:
    family = manifest["family"]
    question = record["question"]

    if family == "belief_mc":
        correct = str(record["correct_answer"])
        wrong = str(record["wrong_answer"])
        if manifest["correct_option"] == "A":
            option_a, option_b = correct, wrong
        elif manifest["correct_option"] == "B":
            option_a, option_b = wrong, correct
        else:
            raise RuntimeError("belief correct_option must be A or B")
        return (
            f"Question:\n{question}\n\n"
            f"Options:\n[A] {option_a}\n[B] {option_b}\n\n"
            "Return exactly [A] or [B]."
        )

    if family == "answerability_binary":
        return (
            f"Target: {record['target']}\n"
            f"Question: {question}\n\n"
            "Return exactly yes or no."
        )

    if family == "info_accessibility_binary":
        return (
            f"Information: {record['information_question']} "
            f"{record['information_answer']}\n"
            f"Question: {question}\n\n"
            "Return exactly yes or no."
        )

    raise RuntimeError(f"unsupported family {family}")


def score_response(
    response: str,
    *,
    record: dict[str, Any],
    manifest: dict[str, Any],
) -> dict[str, Any]:
    family = manifest["family"]
    if family == "belief_mc":
        pred = parse_mc(response)
        gold = manifest["correct_option"]
        return {"prediction": pred, "correct": pred == gold}

    if family in {"answerability_binary", "info_accessibility_binary"}:
        pred = parse_binary(response)
        raw_gold = str(record["correct_answer"]).lower()
        gold = "no" if raw_gold == "no:long" else raw_gold
        if gold not in {"yes", "no"}:
            raise RuntimeError(f"unexpected binary gold: {gold}")
        return {"prediction": pred, "correct": pred == gold}

    raise RuntimeError(f"unsupported family {family}")


def _answer(
    backend: CappedBackend,
    *,
    system: str,
    user: str,
) -> str:
    out = backend.complete(
        [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        max_tokens=ANSWER_MAX_TOKENS,
        temperature=TEMPERATURE,
    ).strip()
    if not out:
        raise RuntimeError(
            "empty final answer content; treat as provider/transport failure, "
            "not as an incorrect benchmark prediction"
        )
    return out


def evaluate_one(
    *,
    manifest: dict[str, Any],
    record: dict[str, Any],
    c_backend: CappedBackend,
    p_backend: CappedBackend,
    d_adapter_backend: CappedBackend,
    d_answer_backend: CappedBackend,
) -> dict[str, Any]:
    # State construction is intentionally completed before the question/task is
    # released to the D answer process.
    extraction = extract_conversation_events(
        record["context"],
        manifest["conversation_id"],
        d_adapter_backend,
        max_tokens=ADAPTER_MAX_TOKENS,
    )
    runtime = HCLV06Runtime()
    for event in extraction.events:
        runtime.ingest_prestructured_event(event)
    d_context = runtime.global_perspective_context()

    task = build_task(record, manifest)
    full_prompt = (
        f"Conversation:\n{record['context']}\n\n"
        f"{task}"
    )

    c_response = _answer(
        c_backend,
        system=CONTROL_SYSTEM,
        user=full_prompt,
    )
    p_response = _answer(
        p_backend,
        system=PERSPECTIVE_SYSTEM,
        user=full_prompt,
    )
    d_response = _answer(
        d_answer_backend,
        system=D_SYSTEM,
        user=json.dumps(
            {
                "hcl_perspective_state": d_context,
                "task": task,
            },
            ensure_ascii=False,
            sort_keys=True,
        ),
    )

    scored = {
        "C": {
            **score_response(c_response, record=record, manifest=manifest),
            "response_sha256": _sha_text(c_response),
            "response": c_response,
        },
        "P": {
            **score_response(p_response, record=record, manifest=manifest),
            "response_sha256": _sha_text(p_response),
            "response": p_response,
        },
        "D": {
            **score_response(d_response, record=record, manifest=manifest),
            "response_sha256": _sha_text(d_response),
            "response": d_response,
        },
    }

    return {
        "question_id": manifest["question_id"],
        "conversation_id": manifest["conversation_id"],
        "set_id": manifest["set_id"],
        "stratum": manifest["stratum"],
        "family": manifest["family"],
        "context_sha256": _sha_text(record["context"]),
        "question_sha256": _sha_text(record["question"]),
        "adapter": {
            "event_count": len(extraction.events),
            "repair_count": extraction.repair_count,
            "access_state_sha256": _sha_text(
                json.dumps(d_context, ensure_ascii=False, sort_keys=True)
            ),
        },
        "arms": scored,
    }


def summarize(results: list[dict[str, Any]]) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    for arm in ("C", "P", "D"):
        correct = sum(bool(row["arms"][arm]["correct"]) for row in results)
        summary[arm] = {
            "correct": correct,
            "total": len(results),
            "accuracy": correct / len(results) if results else 0.0,
        }

    for left, right in (("D", "C"), ("D", "P"), ("P", "C")):
        key = f"{left}_vs_{right}"
        summary[key] = {
            "left_only_correct": sum(
                bool(row["arms"][left]["correct"])
                and not bool(row["arms"][right]["correct"])
                for row in results
            ),
            "right_only_correct": sum(
                bool(row["arms"][right]["correct"])
                and not bool(row["arms"][left]["correct"])
                for row in results
            ),
            "both_correct": sum(
                bool(row["arms"][left]["correct"])
                and bool(row["arms"][right]["correct"])
                for row in results
            ),
            "both_wrong": sum(
                not bool(row["arms"][left]["correct"])
                and not bool(row["arms"][right]["correct"])
                for row in results
            ),
        }
    return summary


def aggregate_metrics(backends: dict[str, CappedBackend]) -> dict[str, Any]:
    result = {name: backend.metrics() for name, backend in backends.items()}
    total = {
        "calls": sum(int(x["calls"]) for x in result.values()),
        "input_chars": sum(int(x["input_chars"]) for x in result.values()),
        "output_chars": sum(int(x["output_chars"]) for x in result.values()),
        "provider_wall_seconds": round(
            sum(float(x["provider_wall_seconds"]) for x in result.values()), 6
        ),
    }
    # Conservative planning estimate only: treats one character as one token
    # and applies current DeepSeek Flash peak rates. It is not a billing record.
    total["char_as_token_peak_usd_upper_bound"] = round(
        total["input_chars"] / 1_000_000 * 0.30
        + total["output_chars"] / 1_000_000 * 1.20,
        6,
    )
    result["TOTAL"] = total
    return result


def make_backend(api_key: str, name: str) -> CappedBackend:
    return CappedBackend(
        make_real_backend(
            api_key,
            BASE_URL,
            MODEL,
            provider_profile="deepseek_flash",
        ),
        name=name,
        caps=CAPS[name],
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fantom-archive", type=Path, required=True)
    parser.add_argument(
        "--out",
        type=Path,
        default=ROOT / "artifacts/hcl-v06-fantom-cpd-v01/results.json",
    )
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()

    if args.validate_only == args.execute:
        parser.error("choose exactly one of --validate-only or --execute")

    selection = load_selection()
    if args.validate_only:
        print(
            json.dumps(
                {
                    "selected_count": selection["selected_count"],
                    "model": MODEL,
                    "caps": CAPS,
                    "provider_calls": 0,
                },
                sort_keys=True,
            )
        )
        return 0

    if os.getenv("GITHUB_ACTIONS") != "true":
        raise RuntimeError("provider-backed C/P/D execution requires GitHub Actions")
    if os.getenv("GITHUB_RUN_ATTEMPT") != "1":
        raise RuntimeError("C/P/D execution is first-attempt only")
    expected_token = os.getenv("HCL_V06_FANTOM_CPD_RUN_ONCE_TOKEN")
    if expected_token != "HCL_V06_FANTOM_CPD_V01_REPAIR_20260925_A2":
        raise RuntimeError("missing exact v0.6 FANToM C/P/D repair token")
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise RuntimeError("DEEPSEEK_API_KEY is required")

    archive = args.fantom_archive.read_bytes()
    digest = hashlib.sha256(archive).hexdigest()
    if digest != selection["source"]["dataset_sha256"]:
        raise RuntimeError("FANToM archive digest drift")
    df = load_dataframe(archive)
    question_map = build_question_map(df)

    backends = {
        "C": make_backend(api_key, "C"),
        "P": make_backend(api_key, "P"),
        "D_ADAPTER": make_backend(api_key, "D_ADAPTER"),
        "D_ANSWER": make_backend(api_key, "D_ANSWER"),
    }

    results: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []
    for manifest in selection["selected"]:
        qid = manifest["question_id"]
        try:
            record = question_map[qid]
            if str(record["set_id"]) != str(manifest["set_id"]):
                raise RuntimeError("set_id drift")
            if str(record["family"]) != str(manifest["family"]):
                raise RuntimeError("family drift")
            results.append(
                evaluate_one(
                    manifest=manifest,
                    record=record,
                    c_backend=backends["C"],
                    p_backend=backends["P"],
                    d_adapter_backend=backends["D_ADAPTER"],
                    d_answer_backend=backends["D_ANSWER"],
                )
            )
        except Exception as exc:
            failures.append(
                {
                    "question_id": qid,
                    "error_type": type(exc).__name__,
                    "error": str(exc)[:500],
                }
            )
            break

    metrics = aggregate_metrics(backends)
    if float(metrics["TOTAL"]["char_as_token_peak_usd_upper_bound"]) > 1.0:
        raise BudgetExceeded("conservative planning cost bound exceeded $1.00")

    output = {
        "format": "hcl-v06-fantom-cpd-results-repair-v01",
        "repair_of_run": 36128133383,
        "freshness": "same_already_consumed_development_selection_not_fresh",
        "status": (
            "complete"
            if not failures and len(results) == selection["selected_count"]
            else "partial_consumed"
        ),
        "model": MODEL,
        "temperature": TEMPERATURE,
        "selection_sha256": hashlib.sha256(
            SELECTION_FILE.read_bytes()
        ).hexdigest(),
        "selected_count": selection["selected_count"],
        "completed_count": len(results),
        "failures": failures,
        "summary": summarize(results),
        "metrics": metrics,
        "results": results,
        "claim_boundary": (
            "Repair execution on the same eight already-consumed development "
            "conversations after run 36128133383 produced empty text outputs. "
            "This repair is not fresh evidence. D evaluates only the v0.6 "
            "perspective slice; it does not validate all future human-cognition "
            "capabilities."
        ),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": output["status"],
                "completed": output["completed_count"],
                "summary": output["summary"],
                "metrics": output["metrics"]["TOTAL"],
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0 if output["status"] == "complete" else 3


if __name__ == "__main__":
    raise SystemExit(main())
