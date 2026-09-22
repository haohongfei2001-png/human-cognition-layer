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
from scripts.run_hcl_v03_state_fidelity import schema_errors

BASE_URL = "https://api.deepseek.com"
MODEL = "deepseek-flash"
SEED = 42
FIXTURES = ROOT / "eval/state_fidelity/communication_boundary_fresh_v01.json"


def field_text(agent: dict[str, Any], field: str) -> str:
    value = agent.get(field, [])
    if not isinstance(value, list):
        return ""
    return "\n".join(str(x) for x in value)


def run_case(index: int, case: dict[str, Any], api_key: str) -> tuple[int, dict[str, Any]]:
    backend = OpenAICompatibleBackend(
        api_key=api_key,
        base_url=BASE_URL,
        model=MODEL,
        seed=SEED,
    )
    loop = HCLAnswerLoop(backend)

    try:
        state = loop.build_state(case["input"])
    except Exception as exc:
        return index, {
            "id": case["id"],
            "completed": False,
            "runtime_exception_type": type(exc).__name__,
            "passed": False,
        }

    errors = schema_errors(state)
    agents = state.get("agents", {}) if isinstance(state.get("agents"), dict) else {}
    target_key = None
    for key in agents:
        if str(key).casefold() == str(case["agent"]).casefold():
            target_key = key
            break
    agent = agents.get(target_key, {}) if target_key is not None else {}
    if not isinstance(agent, dict):
        agent = {}

    knows = field_text(agent, "knows")
    believes = field_text(agent, "believes")

    mode_ok = state.get("mode") in set(case["expected_mode"])
    uncertainty = state.get("uncertainty", {})
    uncertainty_level = uncertainty.get("level") if isinstance(uncertainty, dict) else None
    uncertainty_ok = uncertainty_level in set(case["expected_uncertainty"])

    bridges = state.get("missing_bridges", [])
    bridge_count = len(bridges) if isinstance(bridges, list) else -1
    if case["require_missing_bridge"]:
        missing_bridge_ok = bridge_count > 0
    else:
        missing_bridge_ok = bridge_count == 0

    knows_required_ok = all(term.casefold() in knows.casefold() for term in case["knows_all"])
    believes_required_ok = all(term.casefold() in believes.casefold() for term in case["believes_all"])
    forbidden_knows_ok = all(term.casefold() not in knows.casefold() for term in case["forbidden_knows"])

    checks = {
        "schema_valid": not errors,
        "agent_found": target_key is not None,
        "mode_ok": mode_ok,
        "uncertainty_ok": uncertainty_ok,
        "missing_bridge_ok": missing_bridge_ok,
        "knows_required_ok": knows_required_ok,
        "believes_required_ok": believes_required_ok,
        "forbidden_knows_ok": forbidden_knows_ok,
    }
    passed = all(checks.values())

    return index, {
        "id": case["id"],
        "completed": True,
        "passed": passed,
        "mode": state.get("mode"),
        "uncertainty": uncertainty_level,
        "missing_bridge_count": bridge_count,
        "checks": checks,
        "schema_errors": errors,
    }


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    completed = [x for x in rows if x.get("completed")]
    passed = [x for x in completed if x.get("passed")]
    return {
        "suite": "HCL runtime state-prompt communication boundary fresh v0.1",
        "model": MODEL,
        "seed": SEED,
        "fixture_count": len(rows),
        "completed_count": len(completed),
        "runtime_exception_count": len(rows) - len(completed),
        "passed_count": len(passed),
        "failed_count": len(rows) - len(passed),
        "failed_ids": [x["id"] for x in rows if not x.get("passed")],
        "pass_gate": len(rows) == 10 and len(passed) == 10,
        "claim_boundary": (
            "Fresh repository-owned synthetic validation of runtime conformance "
            "to already-frozen HCL communication semantics."
        ),
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--workers", type=int, default=4)
    p.add_argument(
        "--out",
        type=Path,
        default=ROOT / "artifacts/hcl-runtime-state-prompt-conformance-v01",
    )
    args = p.parse_args()

    if not 1 <= args.workers <= 4:
        raise RuntimeError("workers must be between 1 and 4")

    key = os.getenv("DEEPSEEK_API_KEY")
    if not key:
        raise RuntimeError("DEEPSEEK_API_KEY is required")

    suite = json.loads(FIXTURES.read_text(encoding="utf-8"))
    cases = suite["cases"]
    if len(cases) != 10 or len({x["id"] for x in cases}) != 10:
        raise RuntimeError("expected 10 unique communication boundary fixtures")

    completed: list[tuple[int, dict[str, Any]]] = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [
            pool.submit(run_case, index, case, key)
            for index, case in enumerate(cases)
        ]
        for done_count, future in enumerate(as_completed(futures), 1):
            index, row = future.result()
            completed.append((index, row))
            print(
                f"[{done_count}/{len(cases)}] {row['id']}: "
                f"passed={row.get('passed')} mode={row.get('mode')} "
                f"uncertainty={row.get('uncertainty')}",
                flush=True,
            )

    rows = [row for _, row in sorted(completed, key=lambda x: x[0])]
    summary = summarize(rows)

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
