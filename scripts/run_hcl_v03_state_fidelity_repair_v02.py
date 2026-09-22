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
from scripts.run_hcl_v03_state_fidelity import evaluate_fixture

BASE_URL = "https://api.deepseek.com"


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--model", default="deepseek-flash")
    p.add_argument("--fixtures", default="eval/state_fidelity/fixtures_v01.json")
    p.add_argument("--workers", type=int, default=4)
    p.add_argument(
        "--out",
        type=Path,
        default=ROOT / "artifacts/hcl-v03-state-fidelity-repair-v02",
    )
    args = p.parse_args()

    key = os.getenv("DEEPSEEK_API_KEY")
    if not key:
        raise RuntimeError("DEEPSEEK_API_KEY is required")

    fixtures = json.loads((ROOT / args.fixtures).read_text(encoding="utf-8"))

    def run_one(index_fixture):
        index, fixture = index_fixture
        backend = OpenAICompatibleBackend(
            api_key=key,
            base_url=BASE_URL,
            model=args.model,
            seed=42,
        )
        loop = HCLAnswerLoop(backend)
        state = loop.build_state(
            "情境：\n"
            + fixture["scene"]
            + "\n\n问题：\n"
            + fixture["question"]
        )
        ev = evaluate_fixture(fixture, state)
        return index, {
            "id": fixture["id"],
            "expected": fixture["expected"],
            "state": state,
            "evaluation": ev,
        }

    completed = []
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as ex:
        futures = [ex.submit(run_one, item) for item in enumerate(fixtures)]
        for done_count, future in enumerate(as_completed(futures), 1):
            index, result = future.result()
            completed.append((index, result))
            print(
                f"[{done_count}/{len(fixtures)}] {result['id']}: "
                f"{'PASS' if result['evaluation']['passed'] else 'FAIL'}",
                flush=True,
            )

    results = [result for _, result in sorted(completed, key=lambda x: x[0])]
    gated = [
        r for r in results
        if not r["expected"].get("exclude_from_gate", False)
    ]
    excluded = [
        r for r in results
        if r["expected"].get("exclude_from_gate", False)
    ]
    passed = sum(r["evaluation"]["passed"] for r in gated)
    schema_valid = sum(
        r["evaluation"]["checks"].get("schema_valid", False)
        for r in gated
    )
    summary = {
        "model": args.model,
        "fixture_count": len(results),
        "gated_fixture_count": len(gated),
        "excluded_fixture_count": len(excluded),
        "passed": passed,
        "failed": len(gated) - passed,
        "pass_rate": passed / len(gated) if gated else 0.0,
        "schema_valid_rate": schema_valid / len(gated) if gated else 0.0,
        "failed_ids": [
            r["id"] for r in gated if not r["evaluation"]["passed"]
        ],
        "excluded_ids": [r["id"] for r in excluded],
        "execution_path": "HCLAnswerLoop.build_state",
        "claim_boundary": (
            "Post-repair synthetic state-fidelity regression using the existing "
            "fixture labels and evaluator; no external benchmark evidence."
        ),
    }

    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    with (args.out / "results.jsonl").open("w", encoding="utf-8") as fh:
        for result in results:
            fh.write(json.dumps(result, ensure_ascii=False) + "\n")

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if passed == len(gated) and schema_valid == len(gated) else 3


if __name__ == "__main__":
    raise SystemExit(main())
