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
FIXTURES = ROOT / "eval/answer_loop/info_state_output_interface_v01.json"
TARGET_ID = "io01_full_binary_direct_access"
CONTROL_ID = "io02_full_binary_missing_access"
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
        run = loop.run(case["input"])
    except Exception as exc:
        return {
            **base,
            "runtime_exception_type": type(exc).__name__,
            "completed": False,
        }

    score = score_output(case["format"], case["gold"], run.final_answer)
    uncertainty = (
        run.state.get("uncertainty", {}).get("level")
        if isinstance(run.state.get("uncertainty"), dict)
        else None
    )

    return {
        **base,
        "completed": True,
        "parsed": score["parsed"],
        "parser_valid": score["parser_valid"],
        "semantic_correct": score["semantic_correct"],
        "exact_format": score["exact_format"],
        "response_chars": score["response_chars"],
        "state_mode": run.state.get("mode"),
        "uncertainty": uncertainty,
        "state_sha256": canonical_state_sha256(run.state),
        "first_check_status": run.first_check.get("status"),
        "final_check_status": run.final_check.get("status"),
        "revision_performed": run.revision_performed,
        "second_revision_performed": run.second_revision_performed,
    }


def repetition_success(row: dict[str, Any]) -> bool:
    return bool(
        row.get("completed")
        and row.get("parser_valid")
        and row.get("semantic_correct")
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
        raise RuntimeError("repeatability coverage mismatch")

    runtime_exception_count = sum(not x.get("completed", False) for x in rows)
    target_success = sum(repetition_success(x) for x in target)
    control_success = sum(repetition_success(x) for x in control)
    target_state_modes = sorted({
        str(x.get("state_mode"))
        for x in target
        if x.get("completed")
    })
    target_state_hashes = sorted({
        str(x.get("state_sha256"))
        for x in target
        if x.get("completed")
    })

    if runtime_exception_count:
        interpretation = "RUNTIME_EXCEPTION_BLOCK"
    elif target_state_modes != ["EPISTEMIC"]:
        interpretation = "TARGET_STATE_MODE_DRIFT_BLOCK"
    elif control_success <= 6:
        interpretation = "BROAD_OUTPUT_INSTABILITY"
    elif target_success <= 2:
        interpretation = "STABLE_IO01_REGRESSION"
    elif target_success <= 6:
        interpretation = "ISOLATED_STOCHASTIC_INTERFACE_INSTABILITY"
    else:
        interpretation = "LOW_REPEATABILITY_ORIGINAL_FAILURE"

    return {
        "suite": "HCL v0.2 output-interface regression repeatability investigation v0.1",
        "model": MODEL,
        "seed": SEED,
        "repeats_per_fixture": REPEATS,
        "fixture_count": 2,
        "run_count": len(rows),
        "runtime_exception_count": runtime_exception_count,
        "target": {
            "fixture_id": TARGET_ID,
            "success_count": target_success,
            "parser_valid_count": sum(bool(x.get("parser_valid")) for x in target),
            "semantic_correct_count": sum(bool(x.get("semantic_correct")) for x in target),
            "exact_format_count": sum(bool(x.get("exact_format")) for x in target),
            "state_modes": target_state_modes,
            "distinct_state_sha256_count": len(target_state_hashes),
            "revision_performed_count": sum(bool(x.get("revision_performed")) for x in target),
            "second_revision_performed_count": sum(bool(x.get("second_revision_performed")) for x in target),
            "final_check_pass_count": sum(x.get("final_check_status") == "PASS" for x in target),
        },
        "control": {
            "fixture_id": CONTROL_ID,
            "success_count": control_success,
            "parser_valid_count": sum(bool(x.get("parser_valid")) for x in control),
            "semantic_correct_count": sum(bool(x.get("semantic_correct")) for x in control),
            "exact_format_count": sum(bool(x.get("exact_format")) for x in control),
        },
        "interpretation": interpretation,
        "claim_boundary": (
            "Bounded synthetic repeatability investigation under frozen repair v0.2; "
            "does not erase the original failed regression and does not establish external efficacy."
        ),
    }


def assert_content_free(rows: list[dict[str, Any]], summary: dict[str, Any]) -> None:
    raw = json.dumps({"rows": rows, "summary": summary}, ensure_ascii=False).lower()
    for key in (
        '"input":',
        '"final_answer":',
        '"draft":',
        '"state":',
        '"first_check":',
        '"final_check":',
        '"messages":',
        '"response_text":',
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
        default=ROOT / "artifacts/hcl-v02-interface-investigation-v01",
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
                f"parsed={row.get('parsed')} "
                f"semantic={row.get('semantic_correct')} "
                f"final_check={row.get('final_check_status')}",
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
