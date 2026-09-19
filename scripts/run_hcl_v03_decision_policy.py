#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from hcl.v03.backends import OpenAICompatibleBackend
from hcl.v03.decision_policy import HCLDecisionPolicy

FIXTURES = ROOT / "eval/decision_policy/fixtures_v01_synthetic.json"
OUT = ROOT / "artifacts/decision-policy-v01"


def main() -> int:
    api_key = os.getenv("DEEPSEEK_API_KEY") or os.getenv("CUSTOM_API_KEY")
    if not api_key:
        raise RuntimeError("DEEPSEEK_API_KEY or CUSTOM_API_KEY is required")

    suite = json.loads(FIXTURES.read_text(encoding="utf-8"))
    backend = OpenAICompatibleBackend(
        api_key=api_key,
        base_url="https://api.deepseek.com",
        model="deepseek-flash",
        seed=42,
    )
    policy = HCLDecisionPolicy(backend)

    OUT.mkdir(parents=True, exist_ok=True)
    results = []
    passed = 0

    for case in suite["cases"]:
        try:
            plan = policy.build_plan(
                private_goal=case["private_goal"],
                visible_context=case["visible_context"],
                state=case["state"],
                available_actions=case["available_actions"],
            )
            actual = plan.get("strategy_type")
            ok = actual in case["expected_strategy_types"]

            # Structural invariants that should hold independent of wording.
            if actual == "INFORMATION_PROBE":
                ok = ok and bool(plan.get("critical_information_gap", "").strip())
            if plan.get("goal_progress_state") == "BLOCKED":
                ok = ok and bool(plan.get("hard_constraints"))

            result = {
                "id": case["id"],
                "passed": ok,
                "expected_strategy_types": case["expected_strategy_types"],
                "actual_strategy_type": actual,
                "plan": plan,
            }
        except Exception as exc:
            result = {
                "id": case["id"],
                "passed": False,
                "expected_strategy_types": case["expected_strategy_types"],
                "error_type": type(exc).__name__,
                "error": str(exc),
            }

        results.append(result)
        passed += int(result["passed"])
        print(
            f"{case['id']}: {'PASS' if result['passed'] else 'FAIL'} "
            f"expected={case['expected_strategy_types']} "
            f"actual={result.get('actual_strategy_type')}",
            flush=True,
        )

    summary = {
        "suite": suite["suite"],
        "total": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "pass_rate": passed / len(results),
        "results": results,
        "claim_boundary": (
            "Synthetic decision-policy unit test only. These fixtures are not "
            "SOTOPIA benchmark instances and do not establish benchmark efficacy."
        ),
    }

    (OUT / "result.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({k: summary[k] for k in ("total", "passed", "failed", "pass_rate")}, indent=2))
    return 0 if passed == len(results) else 2


if __name__ == "__main__":
    raise SystemExit(main())
