#!/usr/bin/env python3
"""One-shot fresh SAGA C/P/G/D pilot with question-blind G/D states."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from hcl.v06 import SYSTEM_VIEWER
from hcl.v07.generic_narrative import GenericNarrativeState
from scripts.prepare_v07_saga_dev_v01 import sha, story_text
from scripts.prepare_v07_saga_fresh_v01 import MANIFEST, verified_selection
from scripts.run_v06_fantom_cpd_v01 import CappedBackend
from scripts.run_v06_fantom_cpgd_fresh_v01 import BudgetLedger, OneCallDeepSeekBackend, _metrics
from scripts.run_v07_saga_dev_v01 import (
    ANSWER_MAX_TOKENS, COMMON, D_SYSTEM, P_SYSTEM, construct_state,
    narrative_events, parse_answer,
)

COST_CAP_USD = 0.50
RUN_ONCE_TOKEN = "HCL_V07_SAGA_FRESH_V01_ONCE"
CAPS = {
    "SEMANTIC": {"calls": 160, "input_chars": 350_000, "output_chars": 100_000},
    "C": {"calls": 16, "input_chars": 40_000, "output_chars": 12_000},
    "P": {"calls": 16, "input_chars": 45_000, "output_chars": 12_000},
    "G": {"calls": 16, "input_chars": 90_000, "output_chars": 12_000},
    "D": {"calls": 16, "input_chars": 120_000, "output_chars": 12_000},
}
G_SYSTEM = COMMON + (
    " Use the complete generic source chronology, actor/entity mentions, "
    "narrator provenance and uncertainty. Keep every event; do not turn an "
    "observed action into a certain private motive."
)


def construct_states(story: str, story_id: str, semantic_backend: CappedBackend) -> tuple[dict, object, dict]:
    """Full story only; no participant, source tier or goal annotation."""
    events = narrative_events(story, story_id)
    generic = GenericNarrativeState.from_events(events).as_dict()
    specialized, semantic_audit = construct_state(story, story_id, semantic_backend)
    if generic["event_count"] != len(events) or len(specialized.perspectives.events) != len(events):
        raise RuntimeError("G or D silently lost a source sentence")
    return generic, specialized, semantic_audit


def evaluate_one(item: dict, row: dict, backends: dict[str, CappedBackend]) -> dict:
    story = story_text(row)
    if sha(story) != item["story_sha256"]:
        raise RuntimeError("frozen story hash drift")
    generic, specialized, audit = construct_states(story, item["story_id"], backends["SEMANTIC"])
    # Task/participant is released only after both states have been committed.
    participant = item["participant"]
    task = f"Highlighted participant: {participant}"
    hcl_state = specialized.answer_context(participant, observer_agent_id=SYSTEM_VIEWER)
    prompts = {
        "C": (COMMON, f"Story:\n{story}\n\n{task}"),
        "P": (P_SYSTEM, f"Story:\n{story}\n\n{task}"),
        "G": (G_SYSTEM, json.dumps({"story": story, "generic_state": generic, "task": task}, ensure_ascii=False, sort_keys=True)),
        "D": (D_SYSTEM, json.dumps({"story": story, "hcl_state": hcl_state, "task": task}, ensure_ascii=False, sort_keys=True)),
    }
    arms = {}
    for arm in ("C", "P", "G", "D"):
        system, user = prompts[arm]
        raw = backends[arm].complete_json(
            [{"role": "system", "content": system}, {"role": "user", "content": user}],
            max_tokens=ANSWER_MAX_TOKENS, temperature=0.0,
        )
        try:
            answer = parse_answer(raw, story)
            invalid_reason = None
        except ValueError as exc:
            answer = None
            invalid_reason = str(exc)
        arms[arm] = {
            "answer": answer, "raw_response": raw,
            "response_sha256": sha(raw), "invalid_reason": invalid_reason,
            "source_tier_agreement": None if answer is None else answer["evidence_class"] == (
                "EXPLICIT" if item["source_tier"] == "explicit_goal" else "INFERRED"
            ),
        }
    return {
        "instance_id": item["instance_id"], "story_id": item["story_id"],
        "participant": participant, "source_tier": item["source_tier"],
        "story_sha256": item["story_sha256"],
        "G_state_sha256": sha(json.dumps(generic, sort_keys=True, ensure_ascii=False)),
        "D_state_sha256": sha(json.dumps(hcl_state, sort_keys=True, ensure_ascii=False)),
        "state_audit": audit, "arms": arms,
    }


def _character_cap_peak_usd() -> float:
    total_input = sum(v["input_chars"] for v in CAPS.values())
    total_output = sum(v["output_chars"] for v in CAPS.values())
    return (total_input * 0.30 + total_output * 1.20) / 1_000_000


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--development-source", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=ROOT / "artifacts/hcl-v07-saga-fresh-v01/results.json")
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    if args.validate_only == args.execute:
        parser.error("choose exactly one of --validate-only or --execute")
    if _character_cap_peak_usd() > COST_CAP_USD:
        raise RuntimeError("frozen character caps exceed planning cost cap")
    selected = verified_selection(args.source.read_bytes(), args.development_source.read_bytes())
    if args.validate_only:
        print(json.dumps({"selected": len(selected), "provider_calls": 0, "caps": CAPS, "cost_cap_usd": COST_CAP_USD}, sort_keys=True))
        return 0
    if os.getenv("GITHUB_ACTIONS") != "true" or os.getenv("GITHUB_RUN_ATTEMPT") != "1":
        raise RuntimeError("fresh provider execution requires a first-attempt GitHub Actions run")
    if os.getenv("HCL_V07_SAGA_FRESH_RUN_ONCE_TOKEN") != RUN_ONCE_TOKEN:
        raise RuntimeError("missing fresh one-shot token")
    if float(os.getenv("HCL_V07_SAGA_FRESH_COST_AUTHORIZED_USD", "0")) < COST_CAP_USD:
        raise RuntimeError("fresh v0.7 cost cap not separately owner-authorized")
    key = os.getenv("DEEPSEEK_API_KEY")
    if not key:
        raise RuntimeError("existing provider credential unavailable")
    ledger = BudgetLedger(cap_usd=COST_CAP_USD)
    backends = {name: CappedBackend(
        OneCallDeepSeekBackend(key, ledger), name=name, caps=caps,
    ) for name, caps in CAPS.items()}
    completed, started, failures = [], [], []
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
    if metrics["TOTAL"]["rated_cost_usd"] > COST_CAP_USD:
        failures.append({"error_type": "BudgetExceeded"})
    result = {
        "format": "hcl-v07-saga-fresh-cpgd-result-v01",
        "freshness": "first HCL provider exposure on disjoint validation story families; consumed once execution begins",
        "selection_sha256": sha(MANIFEST.read_bytes()),
        "selected_count": len(selected), "started_instance_ids": started,
        "completed_count": len(completed),
        "status": "SUCCESS" if len(completed) == len(selected) and not failures else "PARTIAL_CONSUMED",
        "failures": failures, "results": completed, "metrics": metrics,
        "invalid_answers": {arm: sum(
            row["arms"][arm]["invalid_reason"] is not None for row in completed
        ) for arm in ("C", "P", "G", "D")},
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "completed_count": len(completed), "metrics": metrics["TOTAL"]}, sort_keys=True))
    return 0 if result["status"] == "SUCCESS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
