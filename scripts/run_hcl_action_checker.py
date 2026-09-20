#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from hcl.v03.action_checker import HCLActionChecker
from hcl.v03.backends import OpenAICompatibleBackend

FIXTURES = ROOT / "eval/action_checker/fixtures_v01_synthetic.json"
OUT = ROOT / "artifacts/action-checker-v01"


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
    checker = HCLActionChecker(backend)

    OUT.mkdir(parents=True, exist_ok=True)
    results = []
    passed = 0

    for case in suite["cases"]:
        try:
            verdict = checker.check(
                turn_context=case["turn_context"],
                state=case["state"],
                decision_plan=case["decision_plan"],
                available_actions=case["available_actions"],
                candidate_action=case["candidate_action"],
            )
            status_ok = verdict.get("status") == case["expected_status"]
            family_ok = True
            acceptable = case.get("acceptable_violation_types", [])
            if case["expected_status"] == "REVISE" and acceptable:
                got = {
                    str(v.get("type"))
                    for v in verdict.get("violations", [])
                    if isinstance(v, dict)
                }
                family_ok = bool(got.intersection(acceptable))
            if case["expected_status"] == "PASS":
                family_ok = len(verdict.get("violations", [])) == 0
            ok = status_ok and family_ok
            result = {
                "id": case["id"],
                "passed": ok,
                "expected_status": case["expected_status"],
                "acceptable_violation_types": acceptable,
                "verdict": verdict,
            }
        except Exception as exc:
            result = {
                "id": case["id"],
                "passed": False,
                "expected_status": case["expected_status"],
                "error_type": type(exc).__name__,
                "error": str(exc),
            }

        results.append(result)
        passed += int(result["passed"])
        print(
            f"{case['id']}: {'PASS' if result['passed'] else 'FAIL'} "
            f"expected={case['expected_status']} "
            f"actual={result.get('verdict', {}).get('status')}",
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
            "Independent synthetic action-checker test only; not SOTOPIA "
            "performance evidence."
        ),
    }
    (OUT / "result.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({k: summary[k] for k in ("total","passed","failed","pass_rate")}, indent=2))
    return 0 if passed == len(results) else 2


if __name__ == "__main__":
    raise SystemExit(main())
