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
FIXTURES = ROOT / "eval/answer_loop/semantic_faithfulness_fresh_v01.json"

TARGET_ID = "sf07_exact_positive_signal"
CONTROL_AB_ID = "sf02_direct_positive_schedule"
CONTROL_EPI_ID = "sf03_direct_positive_location"
REPEATS = 8

PROBES = {
    TARGET_ID: {"agent": "Lena", "terms": ("east gate", "open")},
    CONTROL_AB_ID: {"agent": "Tariq", "terms": ("seminar", "noon")},
    CONTROL_EPI_ID: {"agent": "Nora", "terms": ("spare key", "blue drawer")},
}


def canonical_state_sha256(state: dict[str, Any]) -> str:
    raw = json.dumps(
        state,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def load_cases() -> dict[str, dict[str, Any]]:
    suite = json.loads(FIXTURES.read_text(encoding="utf-8"))
    wanted = {TARGET_ID, CONTROL_AB_ID, CONTROL_EPI_ID}
    selected = {
        x["id"]: x for x in suite["cases"] if x["id"] in wanted
    }
    if set(selected) != wanted:
        raise RuntimeError("state-conflict audit fixture coverage mismatch")
    return selected


def contains_terms(items: Any, terms: tuple[str, str]) -> bool:
    if not isinstance(items, list):
        return False
    a, b = (x.casefold() for x in terms)
    for item in items:
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
    }

    try:
        state = loop.build_state(case["input"])
    except Exception as exc:
        return {
            **base,
            "completed": False,
            "runtime_exception_type": type(exc).__name__,
        }

    uncertainty = state.get("uncertainty")
    return {
        **base,
        "completed": True,
        "state_sha256": canonical_state_sha256(state),
        "mode": state.get("mode"),
        "uncertainty_level": (
            uncertainty.get("level") if isinstance(uncertainty, dict) else None
        ),
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
        "probe": probe_state(case["id"], state),
        "state": state,
    }


def fixture_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    completed = [x for x in rows if x.get("completed")]
    return {
        "n": len(rows),
        "completed": len(completed),
        "runtime_exception_count": len(rows) - len(completed),
        "agent_found_count": sum(
            bool(x.get("probe", {}).get("target_agent_found"))
            for x in completed
        ),
        "state_support_count": sum(
            bool(x.get("probe", {}).get("state_supports_gold"))
            for x in completed
        ),
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


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    grouped = {}
    for fixture_id in [TARGET_ID, CONTROL_AB_ID, CONTROL_EPI_ID]:
        fixture_rows = sorted(
            (x for x in rows if x["fixture_id"] == fixture_id),
            key=lambda x: x["repetition"],
        )
        if len(fixture_rows) != REPEATS:
            raise RuntimeError("state-conflict audit repetition mismatch")
        grouped[fixture_id] = fixture_summary(fixture_rows)

    return {
        "suite": "HCL fresh target synthetic state-conflict audit v0.1",
        "model": MODEL,
        "seed": SEED,
        "run_count": len(rows),
        "repeats_per_fixture": REPEATS,
        "target": grouped[TARGET_ID],
        "control_ab": grouped[CONTROL_AB_ID],
        "control_epistemic": grouped[CONTROL_EPI_ID],
        "audit_complete": (
            len(rows) == 24
            and grouped[TARGET_ID]["runtime_exception_count"] <= 2
            and grouped[TARGET_ID]["agent_found_count"] >= 6
        ),
        "claim_boundary": (
            "Repository-owned synthetic full-state audit; no user/private data and no external benchmark evidence."
        ),
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--workers", type=int, default=4)
    p.add_argument(
        "--out",
        type=Path,
        default=ROOT / "artifacts/hcl-fresh-target-state-conflict-v01",
    )
    args = p.parse_args()

    if not 1 <= args.workers <= 4:
        raise RuntimeError("workers must be between 1 and 4")

    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise RuntimeError("DEEPSEEK_API_KEY is required")

    cases = load_cases()
    fixture_order = [TARGET_ID, CONTROL_AB_ID, CONTROL_EPI_ID]
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
                f"mode={row.get('mode')} "
                f"uncertainty={row.get('uncertainty_level')} "
                f"support={row.get('probe', {}).get('state_supports_gold')}",
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
