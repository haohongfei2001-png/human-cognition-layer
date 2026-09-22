#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from hcl.v03.answer_loop import HCLAnswerLoop
from hcl.v03.backends import OpenAICompatibleBackend
from scripts.run_info_state_output_interface_audit_v01 import score_output

BASE_URL = "https://api.deepseek.com"
MODEL = "deepseek-flash"
SEED = 42
FIXTURES = ROOT / "eval/answer_loop/semantic_faithfulness_fresh_v01.json"

TARGET_ID = "sf07_exact_positive_signal"
CONTROL_AB_ID = "sf02_direct_positive_schedule"
CONTROL_EPISTEMIC_ID = "sf03_direct_positive_location"
REPEATS = 8

PROBES = {
    TARGET_ID: {
        "agent": "Lena",
        "terms": ("east gate", "open"),
    },
    CONTROL_AB_ID: {
        "agent": "Tariq",
        "terms": ("seminar", "noon"),
    },
    CONTROL_EPISTEMIC_ID: {
        "agent": "Nora",
        "terms": ("spare key", "blue drawer"),
    },
}


def canonical_state_sha256(state: dict[str, Any]) -> str:
    data = json.dumps(
        state,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def load_cases() -> dict[str, dict[str, Any]]:
    suite = json.loads(FIXTURES.read_text(encoding="utf-8"))
    selected_ids = {TARGET_ID, CONTROL_AB_ID, CONTROL_EPISTEMIC_ID}
    selected = {
        case["id"]: case
        for case in suite["cases"]
        if case["id"] in selected_ids
    }
    if set(selected) != selected_ids:
        raise RuntimeError("fresh target/control coverage mismatch")
    return selected


def contains_terms(value: Any, terms: tuple[str, str]) -> bool:
    if not isinstance(value, list):
        return False
    a, b = (x.casefold() for x in terms)
    for item in value:
        text = str(item).casefold()
        if a in text and b in text:
            return True
    return False


def probe_state(fixture_id: str, state: dict[str, Any]) -> dict[str, Any]:
    spec = PROBES[fixture_id]
    agents = state.get("agents", {})
    if not isinstance(agents, dict):
        agents = {}

    target_key = None
    for key in agents:
        if str(key).casefold() == spec["agent"].casefold():
            target_key = key
            break

    agent = agents.get(target_key, {}) if target_key is not None else {}
    if not isinstance(agent, dict):
        agent = {}

    observed = contains_terms(agent.get("observed", []), spec["terms"])
    knows = contains_terms(agent.get("knows", []), spec["terms"])

    return {
        "target_agent_found": target_key is not None,
        "observed_support": observed,
        "knows_support": knows,
        "state_supports_gold": observed or knows,
    }


def compact_score(case: dict[str, Any], text: str) -> dict[str, Any]:
    s = score_output(case["format"], case["gold"], text)
    return {
        "parsed": s["parsed"],
        "parser_valid": s["parser_valid"],
        "semantic_correct": s["semantic_correct"],
        "exact_format": s["exact_format"],
        "response_chars": s["response_chars"],
    }


def violation_types(verdict: dict[str, Any]) -> list[str]:
    return sorted({
        str(item.get("type"))
        for item in verdict.get("violations", [])
        if isinstance(item, dict) and item.get("type") is not None
    })


def derive_signals(
    probe: dict[str, Any],
    draft: dict[str, Any],
    first_check: dict[str, Any],
    candidate: dict[str, Any],
    final_check: dict[str, Any],
    final: dict[str, Any],
) -> dict[str, Any]:
    state_ok = bool(probe["state_supports_gold"])
    draft_ok = bool(draft["semantic_correct"])
    candidate_ok = bool(candidate["semantic_correct"])
    final_ok = bool(final["semantic_correct"])
    first_status = first_check.get("status")
    final_status = final_check.get("status")

    if not state_ok:
        first_inversion = "STATE"
    elif not draft_ok:
        first_inversion = "DRAFT"
    elif not candidate_ok:
        first_inversion = "FIRST_REVISION"
    elif not final_ok:
        first_inversion = "SECOND_REVISION"
    else:
        first_inversion = "NONE"

    return {
        "first_inversion_stage": first_inversion,
        "first_check_false_pass": (not draft_ok) and first_status == "PASS",
        "first_check_false_revise": draft_ok and first_status == "REVISE",
        "first_revision_failed_to_correct": (
            first_status == "REVISE" and (not draft_ok) and (not candidate_ok)
        ),
        "first_revision_inversion": draft_ok and not candidate_ok,
        "final_check_false_pass": (not candidate_ok) and final_status == "PASS",
        "final_check_false_revise": candidate_ok and final_status == "REVISE",
        "second_revision_failed_to_correct": (
            final_status == "REVISE" and (not candidate_ok) and (not final_ok)
        ),
        "second_revision_inversion": candidate_ok and not final_ok,
    }


def run_once(case: dict[str, Any], repetition: int, api_key: str) -> dict[str, Any]:
    backend = OpenAICompatibleBackend(
        api_key=api_key,
        base_url=BASE_URL,
        model=MODEL,
        seed=SEED,
    )
    loop = HCLAnswerLoop(backend)

    base = {
        "fixture_id": case["id"],
        "repetition": repetition,
        "gold": case["gold"],
        "format": case["format"],
    }

    try:
        state = loop.build_state(case["input"])
        draft_text = loop.generate_draft(case["input"], state)
        first_check_raw = loop.check(case["input"], state, draft_text)

        if first_check_raw.get("status") == "REVISE":
            candidate_text = loop.revise(
                case["input"], state, draft_text, first_check_raw
            )
            revision_performed = True
        else:
            candidate_text = draft_text
            revision_performed = False

        final_check_raw = loop.check(case["input"], state, candidate_text)

        if final_check_raw.get("status") == "REVISE":
            final_text = loop.revise(
                case["input"], state, candidate_text, final_check_raw
            )
            second_revision_performed = True
        else:
            final_text = candidate_text
            second_revision_performed = False

    except Exception as exc:
        return {
            **base,
            "completed": False,
            "runtime_exception_type": type(exc).__name__,
        }

    probe = probe_state(case["id"], state)
    draft = compact_score(case, draft_text)
    candidate = compact_score(case, candidate_text)
    final = compact_score(case, final_text)
    first_check = {
        "status": first_check_raw.get("status"),
        "violation_types": violation_types(first_check_raw),
    }
    final_check = {
        "status": final_check_raw.get("status"),
        "violation_types": violation_types(final_check_raw),
    }

    return {
        **base,
        "completed": True,
        "state_mode": state.get("mode"),
        "uncertainty": (
            state.get("uncertainty", {}).get("level")
            if isinstance(state.get("uncertainty"), dict)
            else None
        ),
        "state_sha256": canonical_state_sha256(state),
        "state_probe": probe,
        "draft": draft,
        "first_check": first_check,
        "candidate": candidate,
        "final_check": final_check,
        "final": final,
        "revision_performed": revision_performed,
        "second_revision_performed": second_revision_performed,
        "signals": derive_signals(
            probe,
            draft,
            first_check,
            candidate,
            final_check,
            final,
        ),
    }


def stage_count(rows: list[dict[str, Any]], stage: str) -> int:
    return sum(
        x.get("signals", {}).get("first_inversion_stage") == stage
        for x in rows
    )


def final_success(row: dict[str, Any]) -> bool:
    return bool(
        row.get("completed")
        and row.get("final", {}).get("parser_valid")
        and row.get("final", {}).get("semantic_correct")
    )


def fixture_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    completed = [x for x in rows if x.get("completed")]
    return {
        "n": len(rows),
        "completed": len(completed),
        "runtime_exception_count": len(rows) - len(completed),
        "agent_found_count": sum(
            bool(x.get("state_probe", {}).get("target_agent_found"))
            for x in completed
        ),
        "state_support_count": sum(
            bool(x.get("state_probe", {}).get("state_supports_gold"))
            for x in completed
        ),
        "draft_success_count": sum(
            bool(x.get("draft", {}).get("semantic_correct"))
            for x in completed
        ),
        "final_success_count": sum(final_success(x) for x in rows),
        "first_inversion_counts": {
            stage: stage_count(rows, stage)
            for stage in ["STATE", "DRAFT", "FIRST_REVISION", "SECOND_REVISION", "NONE"]
        },
        "first_check_false_pass_count": sum(
            bool(x.get("signals", {}).get("first_check_false_pass"))
            for x in completed
        ),
        "first_check_false_revise_count": sum(
            bool(x.get("signals", {}).get("first_check_false_revise"))
            for x in completed
        ),
        "final_check_false_pass_count": sum(
            bool(x.get("signals", {}).get("final_check_false_pass"))
            for x in completed
        ),
    }


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    grouped = {
        fixture_id: sorted(
            (x for x in rows if x["fixture_id"] == fixture_id),
            key=lambda x: x["repetition"],
        )
        for fixture_id in [TARGET_ID, CONTROL_AB_ID, CONTROL_EPISTEMIC_ID]
    }
    if any(len(v) != REPEATS for v in grouped.values()):
        raise RuntimeError("fresh causal diagnosis coverage mismatch")

    summaries = {k: fixture_summary(v) for k, v in grouped.items()}
    target = summaries[TARGET_ID]
    control_ab = summaries[CONTROL_AB_ID]
    control_epi = summaries[CONTROL_EPISTEMIC_ID]

    if target["runtime_exception_count"] > 2 or target["agent_found_count"] < 6:
        interpretation = "DIAGNOSTIC_INCOMPLETE"
    elif control_ab["final_success_count"] <= 6 or control_epi["final_success_count"] <= 6:
        interpretation = "BROAD_POSITIVE_PIPELINE_INSTABILITY"
    elif target["state_support_count"] <= 2:
        interpretation = "TARGET_STATE_DOMINANT"
    elif (
        target["state_support_count"] >= 7
        and target["first_inversion_counts"]["DRAFT"] >= 5
    ):
        interpretation = "TARGET_DRAFT_DOMINANT"
    elif (
        target["state_support_count"] >= 7
        and target["draft_success_count"] >= 7
        and target["final_success_count"] <= 2
    ):
        interpretation = "TARGET_CHECKER_REVISION_DOMINANT"
    elif target["final_success_count"] <= 2:
        interpretation = "TARGET_MIXED_CAUSAL_PATH"
    elif target["final_success_count"] >= 7:
        interpretation = "TARGET_FAILURE_LOW_REPEATABILITY"
    else:
        interpretation = "TARGET_MIXED_CAUSAL_PATH"

    return {
        "suite": "HCL fresh semantic-failure causal diagnosis v0.1",
        "model": MODEL,
        "seed": SEED,
        "run_count": len(rows),
        "repeats_per_fixture": REPEATS,
        "target": summaries[TARGET_ID],
        "control_ab": summaries[CONTROL_AB_ID],
        "control_epistemic": summaries[CONTROL_EPISTEMIC_ID],
        "interpretation": interpretation,
        "claim_boundary": (
            "Bounded synthetic causal diagnosis under frozen generic answer-loop repair; "
            "no repair change and no external benchmark evidence."
        ),
    }


def assert_content_free(rows: list[dict[str, Any]], summary: dict[str, Any]) -> None:
    raw = json.dumps({"rows": rows, "summary": summary}, ensure_ascii=False).lower()
    for key in (
        '"input":',
        '"draft_text":',
        '"candidate_text":',
        '"final_text":',
        '"final_answer":',
        '"state_body":',
        '"explanation":',
        '"revision_instruction":',
        '"messages":',
        '"api_key":',
        '"exception_text":',
    ):
        if key in raw:
            raise RuntimeError(f"content-free boundary violated: {key}")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--workers", type=int, default=4)
    p.add_argument(
        "--out",
        type=Path,
        default=ROOT / "artifacts/hcl-generic-answer-fresh-causal-v01",
    )
    args = p.parse_args()

    if not 1 <= args.workers <= 4:
        raise RuntimeError("workers must be between 1 and 4")

    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise RuntimeError("DEEPSEEK_API_KEY is required")

    cases = load_cases()
    fixture_order = [TARGET_ID, CONTROL_AB_ID, CONTROL_EPISTEMIC_ID]
    tasks = [
        (cases[fixture_id], repetition)
        for fixture_id in fixture_order
        for repetition in range(1, REPEATS + 1)
    ]

    rows: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {
            pool.submit(run_once, case, repetition, api_key): (case["id"], repetition)
            for case, repetition in tasks
        }
        for future in as_completed(futures):
            row = future.result()
            rows.append(row)
            print(
                f"{row['fixture_id']} repeat={row['repetition']} "
                f"completed={row['completed']} "
                f"draft_semantic={row.get('draft', {}).get('semantic_correct')} "
                f"final_semantic={row.get('final', {}).get('semantic_correct')} "
                f"first_inversion={row.get('signals', {}).get('first_inversion_stage')}",
                flush=True,
            )

    rows.sort(key=lambda x: (x["fixture_id"], x["repetition"]))
    summary = summarize(rows)
    assert_content_free(rows, summary)

    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (args.out / "results.jsonl").write_text(
        "".join(json.dumps(x, ensure_ascii=False) + "\n" for x in rows),
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
