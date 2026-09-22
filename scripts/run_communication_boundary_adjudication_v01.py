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

BASE_URL = "https://api.deepseek.com"
MODEL = "deepseek-flash"
SEED = 42
FIXTURES = ROOT / "eval/state_fidelity/communication_boundary_fresh_v01.json"

CASE_IDS = [
    "cb02_direct_teacher",
    "cb06_unread_notice",
    "cb10_conflicting_sources",
]
REPEATS = 4


def state_sha(state: dict[str, Any]) -> str:
    raw = json.dumps(
        state,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def load_cases() -> dict[str, dict[str, Any]]:
    suite = json.loads(FIXTURES.read_text(encoding="utf-8"))
    selected = {x["id"]: x for x in suite["cases"] if x["id"] in set(CASE_IDS)}
    if set(selected) != set(CASE_IDS):
        raise RuntimeError("adjudication fixture coverage mismatch")
    return selected


def run_once(case: dict[str, Any], repetition: int, key: str) -> dict[str, Any]:
    backend = OpenAICompatibleBackend(
        api_key=key,
        base_url=BASE_URL,
        model=MODEL,
        seed=SEED,
    )
    loop = HCLAnswerLoop(backend)

    base = {"fixture_id": case["id"], "repetition": repetition}
    try:
        state = loop.build_state(case["input"])
    except Exception as exc:
        return {
            **base,
            "completed": False,
            "runtime_exception_type": type(exc).__name__,
        }

    uncertainty = state.get("uncertainty")
    agents = state.get("agents", {})
    agent_keys = sorted(str(x) for x in agents) if isinstance(agents, dict) else []

    return {
        **base,
        "completed": True,
        "state_sha256": state_sha(state),
        "mode": state.get("mode"),
        "uncertainty_level": (
            uncertainty.get("level") if isinstance(uncertainty, dict) else None
        ),
        "agent_keys": agent_keys,
        "hypothesis_count": (
            len(state.get("hypotheses", []))
            if isinstance(state.get("hypotheses"), list)
            else None
        ),
        "missing_bridge_count": (
            len(state.get("missing_bridges", []))
            if isinstance(state.get("missing_bridges"), list)
            else None
        ),
        "state": state,
    }


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_case: dict[str, dict[str, Any]] = {}
    for case_id in CASE_IDS:
        items = [x for x in rows if x["fixture_id"] == case_id]
        if len(items) != REPEATS:
            raise RuntimeError("adjudication repetition mismatch")
        completed = [x for x in items if x.get("completed")]
        by_case[case_id] = {
            "n": len(items),
            "completed": len(completed),
            "runtime_exception_count": len(items) - len(completed),
            "mode_counts": {
                mode: sum(x.get("mode") == mode for x in completed)
                for mode in sorted({str(x.get("mode")) for x in completed})
            },
            "uncertainty_counts": {
                level: sum(x.get("uncertainty_level") == level for x in completed)
                for level in sorted({str(x.get("uncertainty_level")) for x in completed})
            },
            "distinct_state_sha256_count": len({
                str(x.get("state_sha256")) for x in completed
            }),
        }

    return {
        "suite": "HCL communication boundary failure adjudication v0.1",
        "model": MODEL,
        "seed": SEED,
        "run_count": len(rows),
        "repeats_per_case": REPEATS,
        "cases": by_case,
        "audit_complete": (
            len(rows) == 12
            and all(v["completed"] >= 3 for v in by_case.values())
        ),
        "claim_boundary": (
            "Repository-owned synthetic full-state adjudication; "
            "does not rewrite the original raw 7/10 boundary result."
        ),
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--workers", type=int, default=4)
    p.add_argument(
        "--out",
        type=Path,
        default=ROOT / "artifacts/hcl-communication-boundary-adjudication-v01",
    )
    args = p.parse_args()

    if not 1 <= args.workers <= 4:
        raise RuntimeError("workers must be between 1 and 4")

    key = os.getenv("DEEPSEEK_API_KEY")
    if not key:
        raise RuntimeError("DEEPSEEK_API_KEY is required")

    cases = load_cases()
    tasks = [
        (cases[case_id], repetition)
        for case_id in CASE_IDS
        for repetition in range(1, REPEATS + 1)
    ]

    rows: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [
            pool.submit(run_once, case, repetition, key)
            for case, repetition in tasks
        ]
        for done_count, future in enumerate(as_completed(futures), 1):
            row = future.result()
            rows.append(row)
            print(
                f"[{done_count}/12] {row['fixture_id']} repeat={row['repetition']} "
                f"completed={row['completed']} mode={row.get('mode')} "
                f"uncertainty={row.get('uncertainty_level')}",
                flush=True,
            )

    rows.sort(key=lambda x: (x["fixture_id"], x["repetition"]))
    summary = summarize(rows)

    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (args.out / "states.jsonl").write_text(
        "".join(json.dumps(x, ensure_ascii=False) + "\n" for x in rows),
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
