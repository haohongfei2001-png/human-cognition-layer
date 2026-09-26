"""Small capped source-grounding check; author labels are never model inputs."""

from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from hcl.v04.model import EventRecord
from hcl.v06 import SYSTEM_VIEWER
from hcl.v08 import HCLV08Runtime, V08ExtractionError, AppraisalDimension
from scripts.prepare_v08_carebench_dev_v01 import (
    verified_selection,
    SourceNarrative,
    MANIFEST,
    sha,
)
from scripts.run_v06_fantom_cpd_v01 import CappedBackend
from scripts.run_v06_fantom_cpgd_fresh_v01 import (
    BudgetLedger,
    OneCallDeepSeekBackend,
    _metrics,
)

COST_CAP_USD = 0.25
TOKEN = "HCL_V08_CAREBENCH_DEV_V01_ONCE"
CAPS = {
    "SEMANTIC": {"calls": 16, "input_chars": 140000, "output_chars": 64000},
    "C": {"calls": 8, "input_chars": 20000, "output_chars": 16000},
    "P": {"calls": 8, "input_chars": 22000, "output_chars": 16000},
    "D": {"calls": 8, "input_chars": 80000, "output_chars": 16000},
}
COMMON = """Explain the public first-person narrative's experiencer emotions and appraisals with source evidence. Distinguish directly reported feelings from plausible inferences and another person's attributed judgments. Behavior, good/bad outcomes, and appraisals do not prove a unique private feeling. Preserve mixed feelings, alternative interpretations and narrated time scope. Missing evidence is not absence of feeling. Do not diagnose a condition or infer a personality.
Return JSON with emotions (up to four objects: value, strength DIRECT|INFERRED|ATTRIBUTED, quote, time_scope), appraisals (up to three objects: dimension GOAL_RELEVANCE|GOAL_CONGRUENCE|CONTROL|CERTAINTY|ACCOUNTABILITY, value, strength DIRECT|INFERRED|ATTRIBUTED, quote), and uncertainty (short string). Every claim requires an exact narrative quote. Empty lists are allowed when evidence is insufficient. Other people's feelings must not be assigned to the experiencer."""
P_SYSTEM = (
    COMMON
    + " Consider whose goal or expectation is affected, what is controllable or uncertain, and how that could support different feelings before answering."
)
D_SYSTEM = (
    COMMON
    + " Use the supplied typed affect evidence without promoting inferred or attributed claims to direct reports."
)


def build_state(source: SourceNarrative):
    t = "2026-01-01T00:00:00+00:00"
    # This timestamp orders ingestion only; no date or latent timeline is
    # inferred from the narrative. All source text is kept as one report.
    return EventRecord(
        event_id="care-" + source.narrative_sha256,
        valid_time=t,
        recorded_at=t,
        source_id="public-first-person-narrative",
        actor_id="experiencer",
        raw_text=source.text,
        metadata={
            "source_role": "PUBLIC_FIRST_PERSON_REPORT",
            "chronology": "INGESTION_PLACEHOLDER",
        },
    )


def parse_answer(raw, story):
    try:
        answer = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError("answer is not JSON") from exc
    if (
        not isinstance(answer, dict)
        or not isinstance(answer.get("uncertainty"), str)
        or len(answer["uncertainty"]) > 500
    ):
        raise ValueError("invalid uncertainty field")
    for field, cap in [("emotions", 4), ("appraisals", 3)]:
        rows = answer.get(field)
        if not isinstance(rows, list) or len(rows) > cap:
            raise ValueError("invalid claim count")
        for row in rows:
            if not isinstance(row, dict) or row.get("strength") not in {
                "DIRECT",
                "INFERRED",
                "ATTRIBUTED",
            }:
                raise ValueError("invalid claim strength")
            if (
                not isinstance(row.get("value"), str)
                or not row["value"].strip()
                or len(row["value"]) > 500
            ):
                raise ValueError("invalid claim value")
            quote = row.get("quote")
            if (
                not isinstance(quote, str)
                or not quote.strip()
                or quote not in story
                or len(quote) > 1000
            ):
                raise ValueError("claim lacks exact source quote")
            if field == "emotions" and (
                not isinstance(row.get("time_scope"), str)
                or not row["time_scope"].strip()
                or len(row["time_scope"]) > 120
            ):
                raise ValueError("invalid narrated time scope")
            if field == "appraisals" and row.get("dimension") not in {
                x.value for x in AppraisalDimension
            }:
                raise ValueError("invalid appraisal dimension")
    return answer


def evaluate_one(item, source: SourceNarrative, backends):
    runtime = HCLV08Runtime()
    event = build_state(source)
    failures = []
    try:
        result = runtime.ingest_semantic_event(
            event, backends["SEMANTIC"], max_tokens=1536
        )
        repairs = result.repair_count
    except V08ExtractionError as exc:
        repairs = 1
        failures.append({"error_type": type(exc).__name__, "error": str(exc)[:200]})
    state = runtime.answer_context("experiencer", observer_agent_id=SYSTEM_VIEWER)
    if len(runtime.intentions.perspectives.events) != 1:
        raise RuntimeError("source report lost")
    # Release the explanation task only after task-blind semantic construction.
    task = "Target: the first-person experiencer. Explain emotions and relevant appraisals across the narrated episode."
    prompts = {
        "C": (COMMON, f"Narrative:\n{source.text}\n\n{task}"),
        "P": (P_SYSTEM, f"Narrative:\n{source.text}\n\n{task}"),
        "D": (
            D_SYSTEM,
            json.dumps(
                {"narrative": source.text, "affect_state": state, "task": task},
                sort_keys=True,
                ensure_ascii=False,
            ),
        ),
    }
    arms = {}
    for arm in "CPD":
        system, user = prompts[arm]
        raw = backends[arm].complete_json(
            [{"role": "system", "content": system}, {"role": "user", "content": user}],
            max_tokens=512,
            temperature=0.0,
        )
        try:
            answer = parse_answer(raw, source.text)
            invalid = None
        except ValueError as exc:
            answer = None
            invalid = str(exc)
        arms[arm] = {
            "answer": answer,
            "raw_response": raw,
            "response_sha256": sha(raw),
            "invalid_reason": invalid,
        }
    return {
        "case_id": item["case_id"],
        "narrative_sha256": source.narrative_sha256,
        "state_sha256": sha(json.dumps(state, sort_keys=True, ensure_ascii=False)),
        "state_audit": {
            "source_reports": 1,
            "semantic_evidence_count": len(runtime._evidence),
            "repair_count": repairs,
            "semantic_failures": failures,
        },
        "arms": arms,
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--source", type=Path, required=True)
    p.add_argument(
        "--out",
        type=Path,
        default=ROOT / "artifacts/hcl-v08-carebench-dev-v01/results.json",
    )
    p.add_argument("--validate-only", action="store_true")
    p.add_argument("--execute", action="store_true")
    args = p.parse_args()
    if args.validate_only == args.execute:
        p.error("choose validate-only or execute")
    bound = (
        sum(x["input_chars"] for x in CAPS.values()) * 0.30
        + sum(x["output_chars"] for x in CAPS.values()) * 1.20
    ) / 1000000
    if bound > COST_CAP_USD:
        raise RuntimeError("planning cap unsafe")
    selected = verified_selection(args.source.read_bytes())
    if args.validate_only:
        print(
            json.dumps(
                {
                    "selected": len(selected),
                    "provider_calls": 0,
                    "call_cap": 40,
                    "cost_cap_usd": COST_CAP_USD,
                    "char_as_token_peak_planning_usd": bound,
                }
            )
        )
        return 0
    if (
        os.getenv("GITHUB_ACTIONS") != "true"
        or os.getenv("GITHUB_RUN_ATTEMPT") != "1"
        or os.getenv("HCL_V08_CAREBENCH_DEV_RUN_ONCE_TOKEN") != TOKEN
    ):
        raise RuntimeError("first-attempt cloud one-shot execution required")
    if (
        float(os.getenv("HCL_V08_CAREBENCH_DEV_COST_AUTHORIZED_USD") or "0")
        < COST_CAP_USD
    ):
        raise RuntimeError("separate v0.8 development authorization required")
    key = os.getenv("DEEPSEEK_API_KEY")
    if not key:
        raise RuntimeError("existing credential unavailable")
    ledger = BudgetLedger(cap_usd=COST_CAP_USD)
    backends = {
        a: CappedBackend(OneCallDeepSeekBackend(key, ledger), name=a, caps=cap)
        for a, cap in CAPS.items()
    }
    completed = []
    started = []
    failures = []
    for item, source in selected:
        started.append(item["case_id"])
        try:
            completed.append(evaluate_one(item, source, backends))
        except Exception as exc:
            failures.append(
                {
                    "case_id": item["case_id"],
                    "error_type": type(exc).__name__,
                    "error": str(exc)[:500],
                }
            )
            break
    metrics = _metrics(backends)
    if len(metrics["TOTAL"]["provider_response_models"]) > 1:
        failures.append({"error_type": "ProviderModelDrift"})
    result = {
        "format": "hcl-v08-carebench-dev-result-v01",
        "scope": "development source-grounding evidence, not official CAREBench or private-emotion accuracy",
        "selection_sha256": sha(MANIFEST.read_bytes()),
        "started_case_ids": started,
        "completed_count": len(completed),
        "status": (
            "SUCCESS"
            if len(completed) == 8 and not failures
            else "PARTIAL_DEVELOPMENT_CONSUMED"
        ),
        "failures": failures,
        "results": completed,
        "metrics": metrics,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    )
    print(
        json.dumps(
            {
                "status": result["status"],
                "completed_count": len(completed),
                "metrics": metrics["TOTAL"],
            },
            sort_keys=True,
        )
    )
    return 0 if result["status"] == "SUCCESS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
