#!/usr/bin/env python3
from __future__ import annotations

import argparse
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
from scripts.run_hcl_v03_state_fidelity import evaluate_fixture

BASE_URL = "https://api.deepseek.com"
MODEL = "deepseek-flash"
SEED = 42

STATE_FIXTURES = ROOT / "eval/state_fidelity/fixtures_v01.json"
CHECKER_FIXTURES = ROOT / "eval/answer_loop/checker_fixtures_v02_fresh.json"

STATE_ID = "epistemic_private_message"
CHECKER_ID = "fresh11_absence_of_evidence"
REPEATS = 4


def load_state_fixture() -> dict[str, Any]:
    rows = json.loads(STATE_FIXTURES.read_text(encoding="utf-8"))
    for row in rows:
        if row["id"] == STATE_ID:
            return row
    raise RuntimeError("state adjudication fixture not found")


def load_checker_fixture() -> dict[str, Any]:
    rows = json.loads(CHECKER_FIXTURES.read_text(encoding="utf-8"))
    for row in rows:
        if row["id"] == CHECKER_ID:
            return row
    raise RuntimeError("checker adjudication fixture not found")


def backend(api_key: str) -> OpenAICompatibleBackend:
    return OpenAICompatibleBackend(
        api_key=api_key,
        base_url=BASE_URL,
        model=MODEL,
        seed=SEED,
    )


def run_state_once(
    fixture: dict[str, Any],
    repetition: int,
    api_key: str,
) -> dict[str, Any]:
    loop = HCLAnswerLoop(backend(api_key))
    user_input = (
        "情境：\n"
        + fixture["scene"]
        + "\n\n问题：\n"
        + fixture["question"]
    )
    base = {
        "kind": "state_fidelity",
        "fixture_id": fixture["id"],
        "repetition": repetition,
    }

    try:
        state = loop.build_state(user_input)
    except Exception as exc:
        return {
            **base,
            "completed": False,
            "runtime_exception_type": type(exc).__name__,
        }

    raw_eval = evaluate_fixture(fixture, state)
    return {
        **base,
        "completed": True,
        "state": state,
        "raw_evaluation": raw_eval,
    }


def violation_types(verdict: dict[str, Any]) -> list[str]:
    return sorted({
        str(item.get("type"))
        for item in verdict.get("violations", [])
        if isinstance(item, dict) and item.get("type") is not None
    })


def run_checker_once(
    fixture: dict[str, Any],
    repetition: int,
    api_key: str,
) -> dict[str, Any]:
    loop = HCLAnswerLoop(backend(api_key))
    base = {
        "kind": "answer_checker",
        "fixture_id": fixture["id"],
        "repetition": repetition,
    }

    try:
        state = loop.build_state(fixture["input"])
        first = loop.check(fixture["input"], state, fixture["candidate"])
        revised = (
            loop.revise(fixture["input"], state, fixture["candidate"], first)
            if first.get("status") == "REVISE"
            else fixture["candidate"]
        )
        final = loop.check(fixture["input"], state, revised)
    except Exception as exc:
        return {
            **base,
            "completed": False,
            "runtime_exception_type": type(exc).__name__,
        }

    return {
        **base,
        "completed": True,
        "state": state,
        "candidate": fixture["candidate"],
        "first_verdict": first,
        "first_violation_types": violation_types(first),
        "revised_answer": revised,
        "final_verdict": final,
        "final_violation_types": violation_types(final),
        "expected_status": fixture["expected_status"],
        "expected_violation_types": fixture["expected_violation_types"],
    }


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    state_rows = [
        x for x in rows
        if x["kind"] == "state_fidelity"
    ]
    checker_rows = [
        x for x in rows
        if x["kind"] == "answer_checker"
    ]
    if len(state_rows) != REPEATS or len(checker_rows) != REPEATS:
        raise RuntimeError("adjudication repetition coverage mismatch")

    return {
        "suite": "HCL runtime-conformance regression adjudication v0.1",
        "model": MODEL,
        "seed": SEED,
        "state_fixture_id": STATE_ID,
        "checker_fixture_id": CHECKER_ID,
        "repeats_per_fixture": REPEATS,
        "run_count": len(rows),
        "state_completed": sum(bool(x.get("completed")) for x in state_rows),
        "checker_completed": sum(bool(x.get("completed")) for x in checker_rows),
        "runtime_exception_count": sum(
            not bool(x.get("completed"))
            for x in rows
        ),
        "raw_state_pass_count": sum(
            bool(x.get("raw_evaluation", {}).get("passed"))
            for x in state_rows
            if x.get("completed")
        ),
        "checker_revise_count": sum(
            x.get("first_verdict", {}).get("status") == "REVISE"
            for x in checker_rows
            if x.get("completed")
        ),
        "checker_final_pass_count": sum(
            x.get("final_verdict", {}).get("status") == "PASS"
            for x in checker_rows
            if x.get("completed")
        ),
        "first_violation_type_sets": sorted({
            tuple(x.get("first_violation_types", []))
            for x in checker_rows
            if x.get("completed")
        }),
        "adjudication_ready": (
            len(rows) == 8
            and all(x.get("completed") for x in rows)
        ),
        "claim_boundary": (
            "Bounded repository-owned synthetic adjudication evidence only; "
            "raw regression results remain unchanged."
        ),
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--workers", type=int, default=4)
    p.add_argument(
        "--out",
        type=Path,
        default=ROOT / "artifacts/hcl-runtime-conformance-regression-adjudication-v01",
    )
    args = p.parse_args()

    if not 1 <= args.workers <= 4:
        raise RuntimeError("workers must be between 1 and 4")

    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise RuntimeError("DEEPSEEK_API_KEY is required")

    state_fixture = load_state_fixture()
    checker_fixture = load_checker_fixture()

    tasks: list[tuple[str, int]] = []
    for repetition in range(1, REPEATS + 1):
        tasks.append(("state", repetition))
        tasks.append(("checker", repetition))

    rows: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {}
        for kind, repetition in tasks:
            if kind == "state":
                future = pool.submit(
                    run_state_once,
                    state_fixture,
                    repetition,
                    api_key,
                )
            else:
                future = pool.submit(
                    run_checker_once,
                    checker_fixture,
                    repetition,
                    api_key,
                )
            futures[future] = (kind, repetition)

        for future in as_completed(futures):
            row = future.result()
            rows.append(row)
            print(
                f"{row['kind']} repeat={row['repetition']} "
                f"completed={row['completed']} "
                f"raw_state_pass={row.get('raw_evaluation', {}).get('passed')} "
                f"first={row.get('first_verdict', {}).get('status')} "
                f"final={row.get('final_verdict', {}).get('status')}",
                flush=True,
            )

    rows.sort(key=lambda x: (x["kind"], x["repetition"]))
    summary = summarize(rows)

    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (args.out / "evidence.jsonl").write_text(
        "".join(json.dumps(x, ensure_ascii=False) + "\n" for x in rows),
        encoding="utf-8",
    )

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
