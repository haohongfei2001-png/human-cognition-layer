#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from hcl.v03.answer_loop import HCLAnswerLoop
from hcl.v03.backends import OpenAICompatibleBackend

BASE_URL = "https://api.deepseek.com"


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--fixtures", default="eval/answer_loop/checker_fixtures_v01.json")
    p.add_argument("--model", default="deepseek-flash")
    p.add_argument("--workers", type=int, default=4)
    args = p.parse_args()

    key = os.getenv("DEEPSEEK_API_KEY")
    if not key:
        raise RuntimeError("DEEPSEEK_API_KEY is required")

    fixtures = json.loads((ROOT / args.fixtures).read_text(encoding="utf-8"))

    def run_one(index_fixture):
        index, f = index_fixture
        backend = OpenAICompatibleBackend(
            api_key=key,
            base_url=BASE_URL,
            model=args.model,
            seed=42,
        )
        loop = HCLAnswerLoop(backend)

        state = loop.build_state(f["input"])
        verdict = loop.check(f["input"], state, f["candidate"])

        expected_status = f["expected_status"]
        actual_types = {
            str(v.get("type"))
            for v in verdict.get("violations", [])
            if isinstance(v, dict)
        }
        expected_types = set(f.get("expected_violation_types", []))

        status_ok = verdict.get("status") == expected_status
        violation_ok = (
            True
            if expected_status == "PASS"
            else bool(actual_types & expected_types)
        )

        if verdict.get("status") == "REVISE":
            final_answer = loop.revise(f["input"], state, f["candidate"], verdict)
        else:
            final_answer = f["candidate"]

        final_verdict = loop.check(f["input"], state, final_answer)
        final_pass = final_verdict.get("status") == "PASS"

        final_required_ok = all(
            token in final_answer for token in f.get("final_required", [])
        )
        final_forbidden_ok = all(
            token not in final_answer for token in f.get("final_forbidden", [])
        )

        # Final lexical checks are advisory only. A semantically correct revision
        # must not fail merely because it says "不能确定" instead of "无法确定",
        # or mentions a rejected proposition under negation.
        passed = all(
            [
                status_ok,
                violation_ok,
                final_pass,
            ]
        )

        return index, {
            "id": f["id"],
            "passed": passed,
            "input": f["input"],
            "candidate": f["candidate"],
            "state": state,
            "verdict": verdict,
            "expected_status": expected_status,
            "expected_violation_types": sorted(expected_types),
            "actual_violation_types": sorted(actual_types),
            "status_ok": status_ok,
            "violation_ok": violation_ok,
            "final_answer": final_answer,
            "final_verdict": final_verdict,
            "final_pass": final_pass,
            "final_required_ok": final_required_ok,
            "final_forbidden_ok": final_forbidden_ok,
        }

    completed = []
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as ex:
        futures = [
            ex.submit(run_one, item)
            for item in enumerate(fixtures)
        ]
        for done_count, future in enumerate(as_completed(futures), 1):
            index, result = future.result()
            completed.append((index, result))
            print(
                f"[{done_count}/{len(fixtures)}] {result['id']}: "
                f"{'PASS' if result['passed'] else 'FAIL'}",
                flush=True,
            )

    results = [result for _, result in sorted(completed, key=lambda x: x[0])]

    passed_count = sum(r["passed"] for r in results)
    summary = {
        "model": args.model,
        "fixture_count": len(results),
        "passed": passed_count,
        "failed": len(results) - passed_count,
        "pass_rate": passed_count / len(results),
        "checker_status_accuracy": sum(r["status_ok"] for r in results) / len(results),
        "revision_family_hit_rate": (
            sum(
                r["violation_ok"]
                for r in results
                if r["expected_status"] == "REVISE"
            )
            / max(1, sum(r["expected_status"] == "REVISE" for r in results))
        ),
        "final_check_pass_rate": sum(r["final_pass"] for r in results) / len(results),
        "failed_ids": [r["id"] for r in results if not r["passed"]],
    }

    out = ROOT / "artifacts/hcl-v03-answer-checker"
    out.mkdir(parents=True, exist_ok=True)
    (out / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    with (out / "results.jsonl").open("w", encoding="utf-8") as fh:
        for r in results:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if passed_count == len(results) else 3


if __name__ == "__main__":
    raise SystemExit(main())
