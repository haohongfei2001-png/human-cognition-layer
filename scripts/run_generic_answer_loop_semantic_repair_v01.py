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
from scripts.run_info_state_output_interface_audit_v01 import score_output

BASE_URL = "https://api.deepseek.com"
MODEL = "deepseek-flash"
SEED = 42
FIXTURES = ROOT / "eval/answer_loop/semantic_faithfulness_fresh_v01.json"


def run_case(index: int, case: dict[str, Any], api_key: str) -> tuple[int, dict[str, Any]]:
    backend = OpenAICompatibleBackend(
        api_key=api_key,
        base_url=BASE_URL,
        model=MODEL,
        seed=SEED,
    )
    loop = HCLAnswerLoop(backend)

    try:
        run = loop.run(case["input"])
    except Exception as exc:
        return index, {
            "id": case["id"],
            "direction": case["direction"],
            "format": case["format"],
            "gold": case["gold"],
            "requires_exact": bool(case["requires_exact"]),
            "completed": False,
            "runtime_exception_type": type(exc).__name__,
        }

    score = score_output(case["format"], case["gold"], run.final_answer)
    return index, {
        "id": case["id"],
        "direction": case["direction"],
        "format": case["format"],
        "gold": case["gold"],
        "requires_exact": bool(case["requires_exact"]),
        "completed": True,
        "parsed": score["parsed"],
        "parser_valid": score["parser_valid"],
        "semantic_correct": score["semantic_correct"],
        "exact_format": score["exact_format"],
        "response_chars": score["response_chars"],
        "state_mode": run.state.get("mode"),
        "uncertainty": (
            run.state.get("uncertainty", {}).get("level")
            if isinstance(run.state.get("uncertainty"), dict)
            else None
        ),
        "first_check_status": run.first_check.get("status"),
        "final_check_status": run.final_check.get("status"),
        "revision_performed": run.revision_performed,
        "second_revision_performed": run.second_revision_performed,
    }


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    completed = [x for x in rows if x.get("completed")]
    runtime_failures = [x for x in rows if not x.get("completed")]
    exact_required = [x for x in completed if x["requires_exact"]]

    by_direction: dict[str, dict[str, int]] = {}
    for row in completed:
        slot = by_direction.setdefault(
            row["direction"],
            {"n": 0, "semantic_correct": 0, "parser_valid": 0, "exact_format": 0},
        )
        slot["n"] += 1
        slot["semantic_correct"] += int(bool(row["semantic_correct"]))
        slot["parser_valid"] += int(bool(row["parser_valid"]))
        slot["exact_format"] += int(bool(row["exact_format"]))

    pass_gate = (
        len(rows) == 12
        and len(completed) == 12
        and not runtime_failures
        and all(x["semantic_correct"] for x in completed)
        and all(x["parser_valid"] for x in completed)
        and all(x["exact_format"] for x in exact_required)
    )

    return {
        "suite": "HCL generic answer-loop semantic-faithfulness fresh v0.1",
        "model": MODEL,
        "seed": SEED,
        "fixture_count": len(rows),
        "completed_count": len(completed),
        "runtime_exception_count": len(runtime_failures),
        "semantic_correct_count": sum(bool(x["semantic_correct"]) for x in completed),
        "parser_valid_count": sum(bool(x["parser_valid"]) for x in completed),
        "exact_required_count": len(exact_required),
        "exact_format_count": sum(bool(x["exact_format"]) for x in exact_required),
        "by_direction": by_direction,
        "failed_ids": [
            x["id"]
            for x in rows
            if (
                not x.get("completed")
                or not x.get("semantic_correct", False)
                or not x.get("parser_valid", False)
                or (x.get("requires_exact") and not x.get("exact_format", False))
            )
        ],
        "pass_gate": pass_gate,
        "claim_boundary": (
            "Fresh repository-owned synthetic answer-loop semantic-faithfulness validation; "
            "no external benchmark evidence."
        ),
    }


def assert_content_free(rows: list[dict[str, Any]], summary: dict[str, Any]) -> None:
    raw = json.dumps({"rows": rows, "summary": summary}, ensure_ascii=False).lower()
    for key in (
        '"input":',
        '"final_answer":',
        '"draft":',
        '"candidate_final":',
        '"state":',
        '"first_check":',
        '"final_check":',
        '"messages":',
        '"api_key":',
        '"exception_text":',
    ):
        if key in raw:
            raise RuntimeError(f"content-free artifact boundary violated: {key}")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--workers", type=int, default=4)
    p.add_argument(
        "--out",
        type=Path,
        default=ROOT / "artifacts/hcl-generic-answer-loop-semantic-repair-v01",
    )
    args = p.parse_args()

    if not 1 <= args.workers <= 4:
        raise RuntimeError("workers must be between 1 and 4")

    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise RuntimeError("DEEPSEEK_API_KEY is required")

    suite = json.loads(FIXTURES.read_text(encoding="utf-8"))
    cases = suite["cases"]
    if len(cases) != 12 or len({x["id"] for x in cases}) != 12:
        raise RuntimeError("expected 12 unique fresh semantic-faithfulness fixtures")

    completed: list[tuple[int, dict[str, Any]]] = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [
            pool.submit(run_case, index, case, api_key)
            for index, case in enumerate(cases)
        ]
        for done_count, future in enumerate(as_completed(futures), 1):
            index, row = future.result()
            completed.append((index, row))
            print(
                f"[{done_count}/{len(cases)}] {row['id']}: "
                f"completed={row['completed']} "
                f"semantic={row.get('semantic_correct')} "
                f"parser={row.get('parser_valid')} "
                f"exact={row.get('exact_format')}",
                flush=True,
            )

    rows = [row for _, row in sorted(completed, key=lambda x: x[0])]
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
