#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from hcl.v03.answer_loop import HCLAnswerLoop
from hcl.v03.backends import OpenAICompatibleBackend

BASE_URL = "https://api.deepseek.com"
MODEL = "deepseek-flash"
SEED = 42
FIXTURES = ROOT / "eval/answer_loop/info_state_output_interface_v01.json"


def parse_binary(text: str) -> str | None:
    match = re.match(
        r"^\s*(?:answer\s*:\s*)?(yes|no|true|false)\b",
        text,
        flags=re.IGNORECASE,
    )
    if not match:
        return None
    value = match.group(1).lower()
    return "yes" if value in {"yes", "true"} else "no"


def parse_ab(text: str) -> str | None:
    bracketed = re.findall(r"\[\s*([ABab])\s*\]", text)
    unique = {x.upper() for x in bracketed}
    if len(unique) == 1:
        return next(iter(unique))
    if len(unique) > 1:
        return None
    match = re.match(
        r"^\s*(?:answer\s*:\s*)?\(?\s*([ABab])\s*\)?(?:\s|[\.,:;]|$)",
        text,
        flags=re.IGNORECASE,
    )
    return match.group(1).upper() if match else None


def score_output(fmt: str, gold: str, text: str) -> dict[str, Any]:
    stripped = text.strip()
    if fmt == "binary":
        parsed = parse_binary(stripped)
        exact = stripped.lower() in {"yes", "no"}
    elif fmt == "ab":
        parsed = parse_ab(stripped)
        exact = stripped.upper() in {"[A]", "[B]"}
    else:
        raise RuntimeError(f"Unsupported format: {fmt}")
    return {
        "parsed": parsed,
        "parser_valid": parsed is not None,
        "semantic_correct": parsed == gold,
        "exact_format": exact,
        "response_chars": len(text),
    }


def run_case(loop: HCLAnswerLoop, case: dict[str, Any]) -> dict[str, Any]:
    family = case["family"]
    if family == "full_loop":
        run = loop.run(case["input"])
        score = score_output(case["format"], case["gold"], run.final_answer)
        return {
            "id": case["id"],
            "family": family,
            "format": case["format"],
            "gold": case["gold"],
            **score,
            "hcl_mode": run.state.get("mode"),
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

    if family == "forced_revision":
        state = loop.build_state(case["input"])
        first = loop.check(case["input"], state, case["candidate"])
        revised = (
            loop.revise(case["input"], state, case["candidate"], first)
            if first.get("status") == "REVISE"
            else case["candidate"]
        )
        final = loop.check(case["input"], state, revised)
        score = score_output(case["format"], case["gold"], revised)
        return {
            "id": case["id"],
            "family": family,
            "format": case["format"],
            "gold": case["gold"],
            **score,
            "hcl_mode": state.get("mode"),
            "uncertainty": (
                state.get("uncertainty", {}).get("level")
                if isinstance(state.get("uncertainty"), dict)
                else None
            ),
            "checker_revise": first.get("status") == "REVISE",
            "first_check_status": first.get("status"),
            "final_check_status": final.get("status"),
        }

    raise RuntimeError(f"Unsupported family: {family}")


def summarize(items: list[dict[str, Any]]) -> dict[str, Any]:
    n = len(items)
    return {
        "n": n,
        "semantic_correct": sum(bool(x["semantic_correct"]) for x in items),
        "semantic_accuracy": sum(bool(x["semantic_correct"]) for x in items) / n,
        "parser_valid": sum(bool(x["parser_valid"]) for x in items),
        "parser_valid_rate": sum(bool(x["parser_valid"]) for x in items) / n,
        "exact_format": sum(bool(x["exact_format"]) for x in items),
        "exact_format_rate": sum(bool(x["exact_format"]) for x in items) / n,
        "final_check_pass": sum(x.get("final_check_status") == "PASS" for x in items),
        "final_check_pass_rate": sum(x.get("final_check_status") == "PASS" for x in items) / n,
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument(
        "--out",
        type=Path,
        default=ROOT / "artifacts/hcl-info-state-output-interface-v01",
    )
    args = p.parse_args()

    key = os.getenv("DEEPSEEK_API_KEY")
    if not key:
        raise RuntimeError("DEEPSEEK_API_KEY is required")

    suite = json.loads(FIXTURES.read_text(encoding="utf-8"))
    cases = suite["cases"]

    results: list[dict[str, Any]] = []
    for case in cases:
        backend = OpenAICompatibleBackend(
            api_key=key,
            base_url=BASE_URL,
            model=MODEL,
            seed=SEED,
        )
        loop = HCLAnswerLoop(backend)
        result = run_case(loop, case)
        results.append(result)
        print(
            f"{case['id']}: family={case['family']} "
            f"semantic={result['semantic_correct']} "
            f"parser={result['parser_valid']} "
            f"exact={result['exact_format']} "
            f"final_check={result.get('final_check_status')}",
            flush=True,
        )

    full = [x for x in results if x["family"] == "full_loop"]
    forced = [x for x in results if x["family"] == "forced_revision"]

    full_summary = summarize(full)
    forced_summary = summarize(forced)
    forced_summary["checker_revise"] = sum(bool(x.get("checker_revise")) for x in forced)
    forced_summary["checker_revise_rate"] = (
        forced_summary["checker_revise"] / len(forced)
    )

    interface_defect_ids = [
        x["id"]
        for x in results
        if not x["parser_valid"]
        or (
            x.get("final_check_status") == "PASS"
            and not x["parser_valid"]
        )
    ]
    semantic_failure_ids = [
        x["id"] for x in results if not x["semantic_correct"]
    ]
    exact_format_failure_ids = [
        x["id"] for x in results if not x["exact_format"]
    ]

    abstract_defect_established = bool(interface_defect_ids)

    summary = {
        "suite": suite["suite"],
        "model": MODEL,
        "seed": SEED,
        "fixture_count": len(results),
        "full_loop": full_summary,
        "forced_revision": forced_summary,
        "interface_defect_ids": interface_defect_ids,
        "semantic_failure_ids": semantic_failure_ids,
        "exact_format_failure_ids": exact_format_failure_ids,
        "abstract_interface_defect_established": abstract_defect_established,
        "claim_boundary": (
            "Independent synthetic audit of frozen HCL answer/output interface; "
            "no FANToM/SOTOPIA data and no external efficacy claim."
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
    # Audit always exits 0 if all fixtures executed. The evidence may establish
    # a defect; that is an audit result, not a CI infrastructure failure.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
