#!/usr/bin/env python3
"""Bounded SAGA development check for evidence-constrained goal reasoning."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from hcl.v04.model import EventRecord
from hcl.v06 import SYSTEM_VIEWER
from hcl.v07 import HCLV07Runtime
from scripts.prepare_v07_saga_dev_v01 import MANIFEST, sha, story_text, verified_selection
from scripts.run_v06_fantom_cpd_v01 import CappedBackend
from scripts.run_v06_fantom_cpgd_fresh_v01 import BudgetLedger, OneCallDeepSeekBackend, _metrics

CAP_USD = 0.50
ANSWER_MAX_TOKENS = 256
EXTRACT_MAX_TOKENS = 1024
CAPS = {
    "SEMANTIC": {"calls": 120, "input_chars": 400_000, "output_chars": 100_000},
    "C": {"calls": 12, "input_chars": 30_000, "output_chars": 12_000},
    "P": {"calls": 12, "input_chars": 35_000, "output_chars": 12_000},
    "D": {"calls": 12, "input_chars": 200_000, "output_chars": 12_000},
}
RUN_ONCE_TOKEN = "HCL_V07_SAGA_DEV_V01_ONCE"
COMMON = (
    "Read the supplied story and identify the highlighted participant's most "
    "evidence-grounded goal. Distinguish a directly stated goal or intention "
    "from a plausible inference from action. An action alone does not prove "
    "the character's private intention. Return only JSON with keys "
    "evidence_class (EXPLICIT, INFERRED, or INSUFFICIENT), candidate_goal, "
    "supporting_quote. The quote must be an exact substring of the story, "
    "or empty for INSUFFICIENT. Do not assert that one inferred motive is unique."
)
P_SYSTEM = COMMON + " Briefly track which words state a goal and which only describe behavior before answering."
D_SYSTEM = COMMON + " Use the supplied HCL evidence state and preserve its source and uncertainty boundaries."


def narrative_events(story: str, story_id: str) -> tuple[EventRecord, ...]:
    """Reader-only sentences; neither task nor human goal labels enter here."""
    lines = story.split("\n")
    if len(lines) != 5 or not all(lines):
        raise ValueError("SAGA story must contain five nonempty lines")
    events = []
    for index, line in enumerate(lines):
        stamp = f"2026-01-01T00:00:{index:02d}+00:00"
        events.append(EventRecord(
            event_id=f"saga-{story_id}-{index}", valid_time=stamp,
            recorded_at=stamp, raw_text=line, source_id="public-narrator",
            actor_id=None, metadata={"reader_only": True, "sentence_index": index},
        ))
    return tuple(events)


def construct_state(story: str, story_id: str, backend: CappedBackend) -> tuple[HCLV07Runtime, dict]:
    """Question-blind, participant-blind and label-blind state construction."""
    runtime = HCLV07Runtime()
    repairs = 0
    for event in narrative_events(story, story_id):
        result = runtime.ingest_semantic_event(event, backend, max_tokens=EXTRACT_MAX_TOKENS)
        repairs += result.repair_count
    if len(runtime.perspectives.events) != 5:
        raise RuntimeError("semantic construction lost a source sentence")
    return runtime, {
        "source_events": 5,
        "semantic_evidence_count": len(runtime._evidence),
        "repair_count": repairs,
    }


def parse_answer(raw: str, story: str) -> dict:
    try:
        answer = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError("answer is not JSON") from exc
    if not isinstance(answer, dict):
        raise ValueError("answer must be an object")
    klass = answer.get("evidence_class")
    goal = answer.get("candidate_goal")
    quote = answer.get("supporting_quote")
    if klass not in {"EXPLICIT", "INFERRED", "INSUFFICIENT"}:
        raise ValueError("invalid evidence class")
    if not isinstance(goal, str) or not isinstance(quote, str):
        raise ValueError("goal and quote must be strings")
    if len(goal) > 500 or len(quote) > 600:
        raise ValueError("answer exceeds field cap")
    if klass == "INSUFFICIENT":
        if quote:
            raise ValueError("insufficient answer cites evidence")
    elif not goal.strip() or not quote.strip() or quote not in story:
        raise ValueError("goal answer lacks an exact source quote")
    return {"evidence_class": klass, "candidate_goal": goal, "supporting_quote": quote}


def evaluate_one(item: dict, row: dict, backends: dict[str, CappedBackend]) -> dict:
    story = story_text(row)
    if sha(story) != item["story_sha256"]:
        raise RuntimeError("source story hash drift")
    runtime, audit = construct_state(story, item["story_id"], backends["SEMANTIC"])
    # Only now release the highlighted participant to the answer arms.
    participant = item["participant"]
    state = runtime.answer_context(participant, observer_agent_id=SYSTEM_VIEWER)
    task = f"Highlighted participant: {participant}"
    prompts = {
        "C": (COMMON, f"Story:\n{story}\n\n{task}"),
        "P": (P_SYSTEM, f"Story:\n{story}\n\n{task}"),
        "D": (D_SYSTEM, json.dumps({"story": story, "hcl_state": state, "task": task}, ensure_ascii=False, sort_keys=True)),
    }
    arms = {}
    for arm in ("C", "P", "D"):
        system, user = prompts[arm]
        raw = backends[arm].complete_json(
            [{"role": "system", "content": system}, {"role": "user", "content": user}],
            max_tokens=ANSWER_MAX_TOKENS, temperature=0.0,
        )
        try:
            parsed = parse_answer(raw, story)
            invalid_reason = None
        except ValueError as exc:
            parsed = None
            invalid_reason = str(exc)
        arms[arm] = {
            "answer": parsed, "raw_response": raw, "response_sha256": sha(raw),
            "invalid_reason": invalid_reason,
            "source_tier_agreement": None if parsed is None else parsed["evidence_class"] == (
                "EXPLICIT" if item["source_tier"] == "explicit_goal" else "INFERRED"
            ),
        }
    return {
        "instance_id": item["instance_id"], "story_id": item["story_id"],
        "participant": participant, "story_sha256": item["story_sha256"],
        "source_tier": item["source_tier"], "state_sha256": sha(json.dumps(state, sort_keys=True, ensure_ascii=False)),
        "state_audit": audit, "arms": arms,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=ROOT / "artifacts/hcl-v07-saga-dev-v01/results.json")
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    if args.validate_only == args.execute:
        parser.error("choose exactly one of --validate-only or --execute")
    source = args.source.read_bytes()
    selected = verified_selection(source)
    if args.validate_only:
        print(json.dumps({"selected": len(selected), "provider_calls": 0, "caps": CAPS, "cost_cap_usd": CAP_USD}, sort_keys=True))
        return 0
    if os.getenv("GITHUB_ACTIONS") != "true" or os.getenv("GITHUB_RUN_ATTEMPT") != "1":
        raise RuntimeError("provider execution requires a first-attempt GitHub Actions run")
    if os.getenv("HCL_V07_SAGA_DEV_RUN_ONCE_TOKEN") != RUN_ONCE_TOKEN:
        raise RuntimeError("missing one-shot token")
    if float(os.getenv("HCL_V07_SAGA_DEV_COST_AUTHORIZED_USD", "0")) < CAP_USD:
        raise RuntimeError("v0.7 development cost cap not authorized")
    key = os.getenv("DEEPSEEK_API_KEY")
    if not key:
        raise RuntimeError("existing provider credential unavailable")
    ledger = BudgetLedger(cap_usd=CAP_USD)
    backends = {name: CappedBackend(
        OneCallDeepSeekBackend(key, ledger), name=name, caps=caps,
    ) for name, caps in CAPS.items()}
    completed = []
    started = []
    failures = []
    for item, row in selected:
        started.append(item["instance_id"])
        try:
            completed.append(evaluate_one(item, row, backends))
        except Exception as exc:
            failures.append({"instance_id": item["instance_id"], "error_type": type(exc).__name__, "error": str(exc)[:500]})
            break
    metrics = _metrics(backends)
    if len(metrics["TOTAL"]["provider_response_models"]) > 1:
        failures.append({"error_type": "ProviderModelDrift"})
    if metrics["TOTAL"]["rated_cost_usd"] > CAP_USD:
        failures.append({"error_type": "BudgetExceeded"})
    result = {
        "format": "hcl-v07-saga-development-result-v01",
        "freshness": "development only; exposed stories cannot become a fresh v0.7 set",
        "selection_sha256": sha(MANIFEST.read_bytes()),
        "selected_count": len(selected), "started_instance_ids": started,
        "completed_count": len(completed),
        "status": "SUCCESS" if len(completed) == len(selected) and not failures else "PARTIAL_CONSUMED",
        "failures": failures, "results": completed, "metrics": metrics,
        "invalid_answers": {arm: sum(
            row["arms"][arm]["invalid_reason"] is not None for row in completed
        ) for arm in ("C", "P", "D")},
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "completed_count": len(completed), "metrics": metrics["TOTAL"]}, sort_keys=True))
    return 0 if result["status"] == "SUCCESS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
