#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

DIMENSIONS = [
    "believability",
    "relationship",
    "knowledge",
    "secret",
    "social_rules",
    "financial_and_material_benefits",
    "goal",
]


def mean(values: list[float]) -> float:
    return sum(values) / len(values)


def aggregate(settings: list[dict[str, Any]]) -> dict[str, Any]:
    if not settings:
        return {
            "completed_settings": 0,
            "overall": {},
            "dimensions": {},
        }

    control_overall = [float(x["tested_control"]["overall"]) for x in settings]
    treatment_overall = [float(x["tested_treatment"]["overall"]) for x in settings]
    deltas = [float(x["paired_overall_delta"]) for x in settings]

    dims: dict[str, dict[str, list[float]]] = {
        d: {"control": [], "treatment": [], "delta": []} for d in DIMENSIONS
    }
    for item in settings:
        for d in DIMENSIONS:
            cv = float(item["tested_control"]["dimensions"][d])
            tv = float(item["tested_treatment"]["dimensions"][d])
            dims[d]["control"].append(cv)
            dims[d]["treatment"].append(tv)
            dims[d]["delta"].append(tv - cv)

    return {
        "completed_settings": len(settings),
        "overall": {
            "control_mean": mean(control_overall),
            "treatment_mean": mean(treatment_overall),
            "paired_delta_mean": mean(deltas),
            "improved_settings": sum(x > 1e-9 for x in deltas),
            "tied_settings": sum(abs(x) <= 1e-9 for x in deltas),
            "worsened_settings": sum(x < -1e-9 for x in deltas),
        },
        "dimensions": {
            d: {
                "control_mean": mean(dims[d]["control"]),
                "treatment_mean": mean(dims[d]["treatment"]),
                "paired_delta_mean": mean(dims[d]["delta"]),
                "positive_settings": sum(x > 1e-9 for x in dims[d]["delta"]),
                "tied_settings": sum(abs(x) <= 1e-9 for x in dims[d]["delta"]),
                "negative_settings": sum(x < -1e-9 for x in dims[d]["delta"]),
            }
            for d in DIMENSIONS
        },
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--root", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--expected-start", type=int, default=10)
    p.add_argument("--expected-count", type=int, default=10)
    args = p.parse_args()

    by_ordinal: dict[int, dict[str, Any]] = {}
    failures: list[dict[str, Any]] = []

    for path in args.root.rglob("setting_*.json"):
        item = json.loads(path.read_text(encoding="utf-8"))
        by_ordinal[int(item["ordinal"])] = item

    for path in args.root.rglob("progress.json"):
        progress = json.loads(path.read_text(encoding="utf-8"))
        for failure in progress.get("failed_settings", []):
            key = (
                int(failure.get("ordinal", -1)),
                str(failure.get("error_type", "")),
                str(failure.get("error", "")),
            )
            if not any(
                (
                    int(x.get("ordinal", -1)),
                    str(x.get("error_type", "")),
                    str(x.get("error", "")),
                )
                == key
                for x in failures
            ):
                failures.append(failure)

    settings = [by_ordinal[k] for k in sorted(by_ordinal)]
    expected = list(
        range(args.expected_start, args.expected_start + args.expected_count)
    )
    missing = [x for x in expected if x not in by_ordinal]

    summary = {
        "expected_ordinals": expected,
        "completed_ordinals": sorted(by_ordinal),
        "missing_ordinals": missing,
        "failures": failures,
        "aggregate": aggregate(settings),
        "claim_boundary": (
            "Fresh fixed SOTOPIA-Hard holdout slice with custom DeepSeek "
            "partner/evaluator. Not official leaderboard-comparable and not a "
            "final efficacy claim without repeated runs."
        ),
    }

    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))

    return 0 if not missing and not failures else 3


if __name__ == "__main__":
    raise SystemExit(main())
