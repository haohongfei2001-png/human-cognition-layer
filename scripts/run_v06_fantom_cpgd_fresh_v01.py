#!/usr/bin/env python3
"""Question-blind state construction and capped C/P/G/D fresh pilot runner."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from hcl.v06 import HCLV06Runtime, extract_conversation_events
from hcl.v06.generic_state import GenericStructuredState
from scripts.inventory_fantom_external_v02 import load_dataframe
from scripts.prepare_v06_fantom_cpgd_fresh_v01 import freeze_selection, sha
from scripts.run_fantom_external_v02 import build_question_map
from scripts.run_v06_fantom_cpd_v01 import (
    ADAPTER_MAX_TOKENS, ANSWER_MAX_TOKENS, BASE_URL, CONTROL_SYSTEM,
    D_SYSTEM, MODEL, PERSPECTIVE_SYSTEM, TEMPERATURE, BudgetExceeded, CappedBackend,
    _answer, build_task, score_response,
)

SELECTION_FILE = ROOT / "eval/v06/fantom_cpgd_fresh_selection_v01.json"
CAPS = {
    "C": {"calls": 32, "input_chars": 1_200_000, "output_chars": 40_000},
    "P": {"calls": 32, "input_chars": 1_280_000, "output_chars": 40_000},
    "G": {"calls": 32, "input_chars": 2_000_000, "output_chars": 40_000},
    "D": {"calls": 32, "input_chars": 2_800_000, "output_chars": 40_000},
    "ACCESS": {"calls": 64, "input_chars": 1_280_000, "output_chars": 600_000},
}
COST_CAP_USD = 3.50
PEAK_INPUT_CACHE_MISS_USD_PER_M = 0.30
PEAK_INPUT_CACHE_HIT_USD_PER_M = 0.006
PEAK_OUTPUT_USD_PER_M = 1.20
PROMPT_FRAMING_TOKEN_ALLOWANCE = 1024
RUN_ONCE_TOKEN = "HCL_V06_FANTOM_CPGD_FRESH_V01_ONCE"
G_SYSTEM = (
    "Use the complete generic event timeline, speaker/source provenance, ordinary "
    "presence and hearing access, and uncertainty labels to answer the task. "
    "Do not treat a speaker's claim as independently verified. For a person's "
    "knowledge, check what they could actually hear, including departures and "
    "returns. A partial summary need not include every detail. Return only the "
    "requested final answer format."
)


class BudgetLedger:
    """Shared no-overrun preflight using worst-case input bytes and output cap."""

    def __init__(self, cap_usd: float = COST_CAP_USD):
        self.cap_usd = cap_usd
        self.spent_usd = 0.0

    def reserve_bound(self, messages: list[dict[str, str]], max_tokens: int) -> float:
        prompt_bytes = sum(len(str(m.get("content", "")).encode("utf-8")) for m in messages)
        input_token_bound = prompt_bytes + PROMPT_FRAMING_TOKEN_ALLOWANCE
        amount = (
            input_token_bound * PEAK_INPUT_CACHE_MISS_USD_PER_M
            + max_tokens * PEAK_OUTPUT_USD_PER_M
        ) / 1_000_000
        if self.spent_usd + amount > self.cap_usd:
            raise BudgetExceeded("shared rated-cost cap would be exceeded before provider request")
        return amount

    def charge(self, amount: float) -> None:
        self.spent_usd += amount
        if self.spent_usd > self.cap_usd:
            raise BudgetExceeded("shared rated-cost cap exceeded")


class OneCallDeepSeekBackend:
    """One metered SDK request per call, with SDK retries disabled."""

    def __init__(self, api_key: str, ledger: BudgetLedger):
        from openai import OpenAI
        self.client = OpenAI(api_key=api_key, base_url=BASE_URL, max_retries=0)
        self.ledger = ledger
        self.calls = self.input_chars = self.output_chars = 0
        self.rated_cost_usd = 0.0
        self.provider_wall_seconds = 0.0
        self.response_models: set[str] = set()

    def _request(self, messages, *, max_tokens, temperature, json_mode):
        reservation = self.ledger.reserve_bound(messages, max_tokens)
        self.calls += 1
        self.input_chars += sum(len(str(m.get("content", ""))) for m in messages)
        kwargs = {
            "model": MODEL, "messages": messages, "max_tokens": max_tokens,
            "temperature": temperature, "seed": 42,
            "extra_body": {"thinking": {"type": "disabled"}},
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        started = time.perf_counter()
        try:
            response = self.client.chat.completions.create(**kwargs)
        except Exception:
            # A transport error can occur after the provider has billed the
            # request. Charge the full reservation and stop this consumed run.
            self.ledger.charge(reservation)
            self.rated_cost_usd += reservation
            raise
        finally:
            self.provider_wall_seconds += time.perf_counter() - started
        usage = response.usage
        if usage is None or usage.prompt_tokens is None or usage.completion_tokens is None:
            self.ledger.charge(reservation)
            self.rated_cost_usd += reservation
            raise RuntimeError("provider omitted token usage; reserved maximum charged")
        prompt_tokens = int(usage.prompt_tokens)
        hit = int(getattr(usage, "prompt_cache_hit_tokens", 0) or 0)
        miss = int(getattr(usage, "prompt_cache_miss_tokens", prompt_tokens - hit) or 0)
        completion = int(usage.completion_tokens)
        if hit < 0 or miss < 0 or completion < 0 or hit + miss != prompt_tokens:
            self.ledger.charge(reservation)
            self.rated_cost_usd += reservation
            raise RuntimeError("invalid provider token usage accounting")
        rated_cost = (
            hit * PEAK_INPUT_CACHE_HIT_USD_PER_M
            + miss * PEAK_INPUT_CACHE_MISS_USD_PER_M
            + completion * PEAK_OUTPUT_USD_PER_M
        ) / 1_000_000
        if rated_cost > reservation:
            self.ledger.charge(rated_cost)
            self.rated_cost_usd += rated_cost
            raise BudgetExceeded("provider usage exceeded pre-request cost reservation")
        self.ledger.charge(rated_cost)
        self.rated_cost_usd += rated_cost
        model = str(response.model)
        if not model or model == "None":
            raise RuntimeError("provider response omitted model identity")
        self.response_models.add(model)
        if len(self.response_models) > 1:
            raise RuntimeError("provider response model identity changed within a backend")
        output = response.choices[0].message.content or ""
        self.output_chars += len(output)
        return output

    def complete(self, messages, *, max_tokens, temperature=0.0):
        return self._request(messages, max_tokens=max_tokens, temperature=temperature, json_mode=False)

    def complete_json(self, messages, *, max_tokens, temperature=0.0):
        return self._request(messages, max_tokens=max_tokens, temperature=temperature, json_mode=True)

    def metrics(self):
        return {
            "calls": self.calls, "input_chars": self.input_chars,
            "output_chars": self.output_chars,
            "provider_wall_seconds": round(self.provider_wall_seconds, 6),
            "rated_cost_usd": round(self.rated_cost_usd, 8),
            "response_models": sorted(self.response_models),
        }


def _cost(metrics: dict[str, Any]) -> float:
    return round(
        metrics["input_chars"] / 1_000_000 * 0.30
        + metrics["output_chars"] / 1_000_000 * 1.20, 6
    )


def _metrics(backends: dict[str, CappedBackend]) -> dict[str, Any]:
    by_arm = {name: backend.metrics() for name, backend in backends.items()}
    model_ids = sorted({model for metrics in by_arm.values() for model in metrics.get("response_models", [])})
    total = {
        "calls": sum(int(x["calls"]) for x in by_arm.values()),
        "input_chars": sum(int(x["input_chars"]) for x in by_arm.values()),
        "output_chars": sum(int(x["output_chars"]) for x in by_arm.values()),
        "provider_wall_seconds": round(sum(float(x["provider_wall_seconds"]) for x in by_arm.values()), 6),
        "provider_response_models": model_ids,
        "rated_cost_usd": round(sum(float(x["rated_cost_usd"]) for x in by_arm.values()), 8),
    }
    total["char_as_token_peak_usd_upper_bound"] = _cost(total)
    by_arm["TOTAL"] = total
    return by_arm


def _hard_cap_is_safe() -> bool:
    maximum = {
        "input_chars": sum(x["input_chars"] for x in CAPS.values()),
        "output_chars": sum(x["output_chars"] for x in CAPS.values()),
    }
    return _cost(maximum) <= COST_CAP_USD


def construct_states(context: str, conversation_id: str, access_backend: CappedBackend) -> tuple[dict, dict, dict]:
    """No task, options, stratum or gold may enter this function."""
    extraction = extract_conversation_events(
        context, conversation_id, access_backend, max_tokens=ADAPTER_MAX_TOKENS
    )
    generic = GenericStructuredState.from_events(extraction.events).as_dict()
    runtime = HCLV06Runtime()
    for event in extraction.events:
        runtime.ingest_prestructured_event(event)
    specialized = runtime.global_perspective_context()
    if generic["event_count"] != len(extraction.events):
        raise RuntimeError("G lost a source event")
    audit = {
        "event_count": len(extraction.events),
        "repair_count": extraction.repair_count,
        "access_normalization_count": extraction.access_normalization_count,
        "access_map": [
            {
                "turn_index": event.metadata.get("turn_index"),
                "speaker": event.actor_id,
                "heard_by_agent_ids": list(event.observer_ids),
            }
            for event in extraction.events
        ],
        "G_state_sha256": sha(json.dumps(generic, ensure_ascii=False, sort_keys=True)),
        "D_state_sha256": sha(json.dumps(specialized, ensure_ascii=False, sort_keys=True)),
    }
    return generic, specialized, audit


def evaluate_one(manifest: dict, record: dict, backends: dict[str, CappedBackend]) -> dict:
    if sha(record["context"]) != manifest["context_sha256"]:
        raise RuntimeError("frozen context hash drift")
    if sha(record["question"]) != manifest["question_sha256"]:
        raise RuntimeError("frozen question hash drift")
    if record["set_id"] != manifest["set_id"] or record["family"] != manifest["family"]:
        raise RuntimeError("frozen task identity drift")

    generic, specialized, audit = construct_states(
        record["context"], manifest["conversation_id"], backends["ACCESS"]
    )
    # The selected task is released only after both state arms have committed.
    task = build_task(record, manifest)
    raw = record["context"] + "\n\n" + task
    prompts = {
        "C": (CONTROL_SYSTEM, raw),
        "P": (PERSPECTIVE_SYSTEM, raw),
        "G": (G_SYSTEM, json.dumps({"generic_structured_state": generic, "task": task}, ensure_ascii=False, sort_keys=True)),
        "D": (D_SYSTEM, json.dumps({"hcl_perspective_state": specialized, "task": task}, ensure_ascii=False, sort_keys=True)),
    }
    arms = {}
    for arm in ("C", "P", "G", "D"):
        system, user = prompts[arm]
        response = _answer(backends[arm], system=system, user=user)
        arms[arm] = {
            **score_response(response, record=record, manifest=manifest),
            "response": response,
            "response_sha256": sha(response),
        }
    return {
        "conversation_id": manifest["conversation_id"],
        "set_id": manifest["set_id"],
        "question_id": manifest["question_id"],
        "context_sha256": manifest["context_sha256"],
        "question_sha256": manifest["question_sha256"],
        "stratum": manifest["stratum"],
        "adapter": audit,
        "arms": arms,
    }


def summarize(rows: list[dict]) -> dict:
    output = {
        arm: {"correct": sum(bool(row["arms"][arm]["correct"]) for row in rows), "total": len(rows)}
        for arm in ("C", "P", "G", "D")
    }
    for other in ("C", "P", "G"):
        output[f"D_vs_{other}"] = {
            "D_only_correct": sum(r["arms"]["D"]["correct"] and not r["arms"][other]["correct"] for r in rows),
            f"{other}_only_correct": sum(r["arms"][other]["correct"] and not r["arms"]["D"]["correct"] for r in rows),
            "both_correct": sum(r["arms"]["D"]["correct"] and r["arms"][other]["correct"] for r in rows),
            "both_wrong": sum(not r["arms"]["D"]["correct"] and not r["arms"][other]["correct"] for r in rows),
        }
    return output


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fantom-archive", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=ROOT / "artifacts/hcl-v06-fantom-cpgd-fresh-v01/results.json")
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    if args.validate_only == args.execute:
        parser.error("choose exactly one of --validate-only or --execute")
    if not _hard_cap_is_safe():
        raise RuntimeError("component character caps exceed frozen cost cap")
    selection = json.loads(SELECTION_FILE.read_text(encoding="utf-8"))
    archive = args.fantom_archive.read_bytes()
    if selection != freeze_selection(archive, mechanism_main=selection["mechanism_main"]):
        raise RuntimeError("frozen selection does not reproduce")
    if args.validate_only:
        print(json.dumps({"selected_count": 32, "provider_calls": 0, "caps": CAPS, "cost_cap_usd": COST_CAP_USD}, sort_keys=True))
        return 0

    if os.getenv("GITHUB_ACTIONS") != "true" or os.getenv("GITHUB_RUN_ATTEMPT") != "1":
        raise RuntimeError("fresh provider execution requires a first-attempt GitHub Actions run")
    if os.getenv("HCL_V06_FRESH_RUN_ONCE_TOKEN") != RUN_ONCE_TOKEN:
        raise RuntimeError("missing one-shot trigger token")
    if float(os.getenv("HCL_V06_FRESH_COST_AUTHORIZED_USD", "0")) < COST_CAP_USD:
        raise RuntimeError("fresh pilot cost cap has not been owner-authorized")
    key = os.getenv("DEEPSEEK_API_KEY")
    if not key:
        raise RuntimeError("existing DeepSeek credential unavailable")
    dataframe = load_dataframe(archive)
    question_map = build_question_map(dataframe)
    ledger = BudgetLedger()
    backends = {
        name: CappedBackend(
            OneCallDeepSeekBackend(key, ledger),
            name=name, caps=caps,
        )
        for name, caps in CAPS.items()
    }
    rows: list[dict] = []
    failures: list[dict] = []
    for manifest in selection["selected"]:
        try:
            rows.append(evaluate_one(manifest, question_map[manifest["question_id"]], backends))
        except Exception as exc:
            failures.append({"question_id": manifest["question_id"], "error_type": type(exc).__name__, "error": str(exc)[:500]})
            break
    metrics = _metrics(backends)
    if len(metrics["TOTAL"]["provider_response_models"]) > 1:
        failures.append({"error_type": "ProviderModelDrift", "error": "response model identity differed across arms"})
    if metrics["TOTAL"]["char_as_token_peak_usd_upper_bound"] > COST_CAP_USD:
        failures.append({"error_type": "BudgetExceeded", "error": "conservative cost cap exceeded"})
    if metrics["TOTAL"]["rated_cost_usd"] > COST_CAP_USD:
        failures.append({"error_type": "BudgetExceeded", "error": "rated token cost cap exceeded"})
    result = {
        "format": "hcl-v06-fantom-cpgd-fresh-result-v01",
        "freshness": "first provider exposure; consumed once execution begins",
        "selection_sha256": sha(SELECTION_FILE.read_bytes()),
        "model": MODEL,
        "temperature": TEMPERATURE,
        "answer_max_tokens": ANSWER_MAX_TOKENS,
        "selected_count": 32,
        "completed_count": len(rows),
        "status": "SUCCESS" if len(rows) == 32 and not failures else "PARTIAL_CONSUMED",
        "failures": failures,
        "results": rows,
        "summary": summarize(rows),
        "metrics": metrics,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "completed_count": len(rows), "summary": result["summary"], "metrics": metrics["TOTAL"]}, sort_keys=True))
    return 0 if result["status"] == "SUCCESS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
