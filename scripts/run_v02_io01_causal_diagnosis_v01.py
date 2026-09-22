#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
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
FIXTURES = ROOT / "eval/answer_loop/info_state_output_interface_v01.json"
TARGET_ID = "io01_full_binary_direct_access"
CONTROL_ID = "io02_full_binary_missing_access"
TARGET_AGENT = "Priya"
REPEATS = 8


def canonical_state_sha256(state: dict[str, Any]) -> str:
    encoded = json.dumps(
        state,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def load_cases() -> dict[str, dict[str, Any]]:
    suite = json.loads(FIXTURES.read_text(encoding="utf-8"))
    selected = {
        case["id"]: case
        for case in suite["cases"]
        if case["id"] in {TARGET_ID, CONTROL_ID}
    }
    if set(selected) != {TARGET_ID, CONTROL_ID}:
        raise RuntimeError("target/control fixture coverage mismatch")
    return selected


def extract_target_token(case: dict[str, Any]) -> str:
    match = re.search(r"\b\d{4}\b", case["input"])
    if not match:
        raise RuntimeError("synthetic target token not found")
    return match.group(0)


def list_contains_token(value: Any, token: str) -> bool:
    if not isinstance(value, list):
        return False
    return any(token in str(item) for item in value)


def state_probe(state: dict[str, Any], token: str) -> dict[str, Any]:
    agents = state.get("agents", {})
    if not isinstance(agents, dict):
        agents = {}

    target_key = None
    for key in agents:
        if str(key).casefold() == TARGET_AGENT.casefold():
            target_key = key
            break

    target = agents.get(target_key, {}) if target_key is not None else {}
    if not isinstance(target, dict):
        target = {}

    explicit_facts = state.get("explicit_facts", [])
    summary = state.get("decision_relevant_summary", "")

    probe = {
        "target_agent_found": target_key is not None,
        "observed_contains_target_token": list_contains_token(
            target.get("observed", []), token
        ),
        "knows_contains_target_token": list_contains_token(
            target.get("knows", []), token
        ),
        "believes_contains_target_token": list_contains_token(
            target.get("believes", []), token
        ),
        "explicit_facts_contains_target_token": list_contains_token(
            explicit_facts, token
        ),
        "summary_contains_target_token": token in str(summary),
    }
    probe["state_supports_gold"] = (
        probe["observed_contains_target_token"]
        or probe["knows_contains_target_token"]
    )
    return probe


def compact_score(fmt: str, gold: str, text: str) -> dict[str, Any]:
    scored = score_output(fmt, gold, text)
    return {
        "parsed": scored["parsed"],
        "parser_valid": scored["parser_valid"],
        "semantic_correct": scored["semantic_correct"],
        "exact_format": scored["exact_format"],
        "response_chars": scored["response_chars"],
    }


def violation_types(verdict: dict[str, Any]) -> list[str]:
    types = {
        str(item.get("type"))
        for item in verdict.get("violations", [])
        if isinstance(item, dict) and item.get("type") is not None
    }
    return sorted(types)


def derive_target_signals(
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
        "state_semantic_loss": not state_ok,
        "draft_inversion": state_ok and not draft_ok,
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
        "first_inversion_stage": first_inversion,
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
    }

    try:
        state = loop.build_state(case["input"])
        draft_text = loop.generate_draft(case["input"], state)
        first_check = loop.check(case["input"], state, draft_text)

        if first_check.get("status") == "REVISE":
            candidate_text = loop.revise(
                case["input"], state, draft_text, first_check
            )
            revision_performed = True
        else:
            candidate_text = draft_text
            revision_performed = False

        final_check = loop.check(case["input"], state, candidate_text)

        if final_check.get("status") == "REVISE":
            final_text = loop.revise(
                case["input"], state, candidate_text, final_check
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

    draft = compact_score(case["format"], case["gold"], draft_text)
    candidate = compact_score(case["format"], case["gold"], candidate_text)
    final = compact_score(case["format"], case["gold"], final_text)

    row = {
        **base,
        "completed": True,
        "state_mode": state.get("mode"),
        "uncertainty": (
            state.get("uncertainty", {}).get("level")
            if isinstance(state.get("uncertainty"), dict)
            else None
        ),
        "state_sha256": canonical_state_sha256(state),
        "draft": draft,
        "first_check": {
            "status": first_check.get("status"),
            "violation_types": violation_types(first_check),
        },
        "candidate": candidate,
        "final_check": {
            "status": final_check.get("status"),
            "violation_types": violation_types(final_check),
        },
        "final": final,
        "revision_performed": revision_performed,
        "second_revision_performed": second_revision_performed,
    }

    if case["id"] == TARGET_ID:
        token = extract_target_token(case)
        probe = state_probe(state, token)
        row["state_probe"] = probe
        row["signals"] = derive_target_signals(
            probe,
            draft,
            row["first_check"],
            candidate,
            row["final_check"],
            final,
        )
    return row


def final_success(row: dict[str, Any]) -> bool:
    return bool(
        row.get("completed")
        and row.get("final", {}).get("parser_valid")
        and row.get("final", {}).get("semantic_correct")
    )


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    target = sorted(
        (x for x in rows if x["fixture_id"] == TARGET_ID),
        key=lambda x: x["repetition"],
    )
    control = sorted(
        (x for x in rows if x["fixture_id"] == CONTROL_ID),
        key=lambda x: x["repetition"],
    )
    if len(target) != REPEATS or len(control) != REPEATS:
        raise RuntimeError("causal diagnosis coverage mismatch")

    runtime_exceptions = sum(not x.get("completed", False) for x in rows)
    target_agent_missing = sum(
        x.get("completed")
        and not x.get("state_probe", {}).get("target_agent_found", False)
        for x in target
    )
    control_success = sum(final_success(x) for x in control)
    target_final_success = sum(final_success(x) for x in target)

    stages = ["STATE", "DRAFT", "FIRST_REVISION", "SECOND_REVISION", "NONE"]
    first_inversion_counts = {
        stage: sum(
            x.get("signals", {}).get("first_inversion_stage") == stage
            for x in target
        )
        for stage in stages
    }

    signal_names = [
        "state_semantic_loss",
        "draft_inversion",
        "first_check_false_pass",
        "first_check_false_revise",
        "first_revision_failed_to_correct",
        "first_revision_inversion",
        "final_check_false_pass",
        "final_check_false_revise",
        "second_revision_failed_to_correct",
        "second_revision_inversion",
    ]
    signal_counts = {
        name: sum(bool(x.get("signals", {}).get(name)) for x in target)
        for name in signal_names
    }

    if runtime_exceptions or target_agent_missing > 2:
        interpretation = "DIAGNOSTIC_INCOMPLETE"
    elif control_success <= 6:
        interpretation = "BROAD_PIPELINE_INSTABILITY"
    elif signal_counts["state_semantic_loss"] >= 5:
        interpretation = "STATE_DOMINANT"
    elif (
        signal_counts["state_semantic_loss"] <= 2
        and first_inversion_counts["DRAFT"] >= 5
    ):
        interpretation = "DRAFT_DOMINANT"
    elif (
        signal_counts["state_semantic_loss"] <= 2
        and (
            first_inversion_counts["FIRST_REVISION"]
            + first_inversion_counts["SECOND_REVISION"]
        ) >= 5
    ):
        interpretation = "REVISION_DOMINANT"
    elif (
        signal_counts["state_semantic_loss"] <= 2
        and (
            signal_counts["first_check_false_pass"]
            + signal_counts["first_check_false_revise"]
            + signal_counts["final_check_false_pass"]
            + signal_counts["final_check_false_revise"]
        ) >= 5
    ):
        interpretation = "CHECKER_CONTROL_FAILURE"
    elif target_final_success <= 2:
        interpretation = "MIXED_CAUSAL_PATH"
    elif target_final_success >= 7:
        interpretation = "NOT_REPRODUCED_IN_CAUSAL_RUN"
    else:
        interpretation = "MIXED_CAUSAL_PATH"

    return {
        "suite": "HCL repair-v0.2 io01 causal diagnosis v0.1",
        "model": MODEL,
        "seed": SEED,
        "run_count": len(rows),
        "runtime_exception_count": runtime_exceptions,
        "target_agent_missing_count": target_agent_missing,
        "target_final_success_count": target_final_success,
        "control_final_success_count": control_success,
        "target_first_inversion_counts": first_inversion_counts,
        "target_signal_counts": signal_counts,
        "target_state_modes": sorted({
            str(x.get("state_mode"))
            for x in target
            if x.get("completed")
        }),
        "target_distinct_state_sha256_count": len({
            str(x.get("state_sha256"))
            for x in target
            if x.get("completed")
        }),
        "interpretation": interpretation,
        "claim_boundary": (
            "Synthetic causal localization under frozen repair-v0.2 behavior; "
            "no HCL behavior change and no external benchmark evidence."
        ),
    }


def assert_content_free(rows: list[dict[str, Any]], summary: dict[str, Any]) -> None:
    raw = json.dumps({"rows": rows, "summary": summary}, ensure_ascii=False).lower()
    for key in (
        '"input":',
        '"target_token":',
        '"text":',
        '"final_answer":',
        '"draft_text":',
        '"candidate_text":',
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
        default=ROOT / "artifacts/hcl-v02-io01-causal-diagnosis-v01",
    )
    args = p.parse_args()

    if not 1 <= args.workers <= 4:
        raise RuntimeError("workers must be between 1 and 4")

    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise RuntimeError("DEEPSEEK_API_KEY is required")

    cases = load_cases()
    tasks = [
        (cases[fixture_id], repetition)
        for fixture_id in (TARGET_ID, CONTROL_ID)
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
