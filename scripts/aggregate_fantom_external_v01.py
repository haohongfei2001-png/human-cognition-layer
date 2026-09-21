#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import mean
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SELECTION_FILE = ROOT / "eval/fantom/selection_v01.json"

PRIMARY_STRATA = {
    "belief_inaccessible_first",
    "belief_inaccessible_second",
    "answerability_inaccessible_binary",
    "info_accessibility_inaccessible_binary",
}
PRIMARY_BELIEF = {
    "belief_inaccessible_first",
    "belief_inaccessible_second",
}
PRIMARY_INFO = {
    "answerability_inaccessible_binary",
    "info_accessibility_inaccessible_binary",
}
ACCESSIBLE_BELIEF = {
    "belief_accessible_first",
    "belief_accessible_second",
}
FACT_STRATUM = "fact_control"


def summarize_binary_like(items: list[dict[str, Any]]) -> dict[str, Any]:
    control_correct = sum(bool(x["control"]["correct"]) for x in items)
    treatment_correct = sum(bool(x["treatment"]["correct"]) for x in items)
    improved = sum(x.get("paired_outcome") == "improved" for x in items)
    worsened = sum(x.get("paired_outcome") == "worsened" for x in items)
    both_correct = sum(x.get("paired_outcome") == "both_correct" for x in items)
    both_wrong = sum(x.get("paired_outcome") == "both_wrong" for x in items)
    n = len(items)
    return {
        "n": n,
        "control_correct": control_correct,
        "treatment_correct": treatment_correct,
        "control_accuracy": control_correct / n if n else None,
        "treatment_accuracy": treatment_correct / n if n else None,
        "improved": improved,
        "worsened": worsened,
        "both_correct": both_correct,
        "both_wrong": both_wrong,
        "net_paired_gain": improved - worsened,
    }


def summarize_fact(items: list[dict[str, Any]]) -> dict[str, Any]:
    control = [float(x["control"]["token_f1"]) for x in items]
    treatment = [float(x["treatment"]["token_f1"]) for x in items]
    deltas = [t - c for c, t in zip(control, treatment)]
    return {
        "n": len(items),
        "control_mean_token_f1": mean(control),
        "treatment_mean_token_f1": mean(treatment),
        "paired_mean_delta": mean(deltas),
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--root", type=Path, required=True)
    p.add_argument(
        "--out",
        type=Path,
        default=ROOT / "artifacts/fantom-external-v01-summary",
    )
    args = p.parse_args()

    selection = json.loads(SELECTION_FILE.read_text(encoding="utf-8"))
    expected_ids = {x["question_id"] for x in selection["selected"]}
    expected_conversations = {x["conversation_id"] for x in selection["selected"]}

    shard_files = sorted(args.root.rglob("shard_*.json"))
    if len(shard_files) != 4:
        raise RuntimeError(f"Expected 4 FANToM shard files, found {len(shard_files)}")

    results: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    seen_shards: set[int] = set()

    for path in shard_files:
        data = json.loads(path.read_text(encoding="utf-8"))
        seen_shards.add(int(data["shard_index"]))
        failures.extend(data.get("failures", []))
        results.extend(data.get("results", []))

    if seen_shards != {0, 1, 2, 3}:
        raise RuntimeError(f"Unexpected shard indexes: {seen_shards}")
    if failures:
        raise RuntimeError(f"FANToM paired pilot has execution failures: {failures}")
    if len(results) != 32:
        raise RuntimeError(f"Expected 32 completed FANToM questions, got {len(results)}")

    ids = [x["question_id"] for x in results]
    conversations = [x["conversation_id"] for x in results]
    if len(set(ids)) != 32 or set(ids) != expected_ids:
        raise RuntimeError("FANToM completed question IDs do not match predeclaration")
    if len(set(conversations)) != 32 or set(conversations) != expected_conversations:
        raise RuntimeError("FANToM conversation IDs do not match disjoint predeclaration")

    by_stratum: dict[str, list[dict[str, Any]]] = {}
    for item in results:
        by_stratum.setdefault(item["stratum"], []).append(item)

    strata_summary: dict[str, Any] = {}
    for stratum, items in sorted(by_stratum.items()):
        if stratum == FACT_STRATUM:
            strata_summary[stratum] = summarize_fact(items)
        else:
            strata_summary[stratum] = summarize_binary_like(items)

    primary_items = [x for x in results if x["stratum"] in PRIMARY_STRATA]
    primary_belief_items = [x for x in results if x["stratum"] in PRIMARY_BELIEF]
    primary_info_items = [x for x in results if x["stratum"] in PRIMARY_INFO]
    accessible_items = [x for x in results if x["stratum"] in ACCESSIBLE_BELIEF]
    fact_items = [x for x in results if x["stratum"] == FACT_STRATUM]

    if not (
        len(primary_items) == 16
        and len(primary_belief_items) == 8
        and len(primary_info_items) == 8
        and len(accessible_items) == 8
        and len(fact_items) == 8
    ):
        raise RuntimeError("FANToM predeclared group sizes drifted")

    primary = summarize_binary_like(primary_items)
    primary_belief = summarize_binary_like(primary_belief_items)
    primary_info = summarize_binary_like(primary_info_items)
    accessible = summarize_binary_like(accessible_items)
    fact = summarize_fact(fact_items)

    positive = (
        primary["net_paired_gain"] >= 2
        and primary_belief["treatment_accuracy"] >= primary_belief["control_accuracy"]
        and primary_info["treatment_accuracy"] >= primary_info["control_accuracy"]
        and accessible["net_paired_gain"] >= -1
        and fact["paired_mean_delta"] >= -0.05
    )
    negative = (
        primary["net_paired_gain"] < 0
        or accessible["net_paired_gain"] <= -2
        or fact["paired_mean_delta"] < -0.05
    )
    interpretation = "positive" if positive else "negative" if negative else "mixed"

    compact_results = [
        {
            "question_id": x["question_id"],
            "set_id": x["set_id"],
            "conversation_id": x["conversation_id"],
            "stratum": x["stratum"],
            "family": x["family"],
            "paired_outcome": x.get("paired_outcome"),
            "paired_f1_delta": x.get("paired_f1_delta"),
            "control_correct": x["control"].get("correct"),
            "treatment_correct": x["treatment"].get("correct"),
            "control_token_f1": x["control"].get("token_f1"),
            "treatment_token_f1": x["treatment"].get("token_f1"),
            "control_prediction": x["control"].get("normalized_prediction"),
            "treatment_prediction": x["treatment"].get("normalized_prediction"),
            "hcl_mode": x["treatment"].get("hcl_mode"),
            "hcl_uncertainty": x["treatment"].get("hcl_uncertainty"),
            "revision_performed": x["treatment"].get("revision_performed"),
            "second_revision_performed": x["treatment"].get(
                "second_revision_performed"
            ),
        }
        for x in sorted(results, key=lambda item: item["question_id"])
    ]

    summary = {
        "source": selection["source"],
        "sample": {
            "questions": 32,
            "distinct_conversations": 32,
            "conversation_disjoint": True,
        },
        "strata": strata_summary,
        "primary": primary,
        "primary_belief": primary_belief,
        "primary_information_state": primary_info,
        "accessible_belief_control": accessible,
        "fact_control": fact,
        "predeclared_interpretation": interpretation,
        "interpretation_rules": {
            "positive": (
                "primary net >= +2; no primary-subblock accuracy regression; "
                "accessible belief net >= -1; fact F1 delta >= -0.05"
            ),
            "negative": (
                "primary net < 0 OR accessible belief net <= -2 OR "
                "fact F1 delta < -0.05"
            ),
            "otherwise": "mixed",
        },
        "question_level": compact_results,
        "claim_boundary": (
            "Bounded predeclared FANToM short-context paired pilot; not an "
            "official leaderboard result, not full-benchmark performance, not "
            "interactive Decision Policy efficacy, not cross-base transfer."
        ),
    }

    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(
        json.dumps(
            {
                "primary": primary,
                "primary_belief": primary_belief,
                "primary_information_state": primary_info,
                "accessible_belief_control": accessible,
                "fact_control": fact,
                "predeclared_interpretation": interpretation,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
