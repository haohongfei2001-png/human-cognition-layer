#!/usr/bin/env python3
"""Summarize official CogToM JSONL output and create a manual audit worksheet."""

from __future__ import annotations

import argparse
import csv
import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def load_dataset(path: Path) -> dict[str, dict[str, Any]]:
    # Defensive loader: CogToM's public README documents one JSON object per line.
    by_id: dict[str, dict[str, Any]] = {}
    for row in read_jsonl(path):
        if "id" in row:
            by_id[str(row["id"])] = row
    return by_id


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--results", type=Path, required=True)
    p.add_argument("--dataset", type=Path, required=True)
    p.add_argument("--metadata", type=Path, required=True)
    p.add_argument("--output-dir", type=Path, required=True)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    rows = read_jsonl(args.results)
    data_by_id = load_dataset(args.dataset)
    metadata = json.loads(args.metadata.read_text(encoding="utf-8"))

    if not rows:
        raise RuntimeError("No CogToM result rows found.")

    group_acc = [float(r.get("group_accuracy", 0.0)) for r in rows]
    consistency = [bool(r.get("is_consistent", False)) for r in rows]

    cat_values: dict[str, list[float]] = defaultdict(list)
    subcat_values: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        cat_values[str(row.get("category", "unknown"))].append(float(row.get("group_accuracy", 0.0)))
        subcat_values[str(row.get("subcategory", "unknown"))].append(float(row.get("group_accuracy", 0.0)))

    summary = {
        "metadata": metadata,
        "groups": len(rows),
        "mean_group_accuracy": statistics.fmean(group_acc),
        "strict_all_variants_correct_rate": sum(a == 1.0 for a in group_acc) / len(group_acc),
        "semantic_consistency_rate": sum(consistency) / len(consistency),
        "groups_with_any_error": sum(a < 1.0 for a in group_acc),
        "category_accuracy": {
            k: statistics.fmean(v) for k, v in sorted(cat_values.items())
        },
        "subcategory_accuracy": {
            k: statistics.fmean(v) for k, v in sorted(subcat_values.items())
        },
    }
    (args.output_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    error_rows: list[dict[str, Any]] = []
    for row in rows:
        if float(row.get("group_accuracy", 0.0)) >= 1.0:
            continue
        sample = data_by_id.get(str(row.get("id")), {})
        details = row.get("details", [])
        error_rows.append(
            {
                "id": row.get("id"),
                "category": row.get("category"),
                "subcategory": row.get("subcategory"),
                "group_accuracy": row.get("group_accuracy"),
                "is_consistent": row.get("is_consistent"),
                "scene": sample.get("scene"),
                "question": sample.get("question"),
                "options": sample.get("options"),
                "gold_answer": sample.get("answer"),
                "gold_content": (sample.get("options") or {}).get(sample.get("answer")),
                "variant_outputs": [
                    {
                        "permuted_answer": d.get("permuted_answer"),
                        "extracted_label": d.get("extracted_label"),
                        "extracted_content": d.get("extracted_content"),
                        "is_correct": d.get("is_correct"),
                        "raw_output": d.get("raw_output"),
                    }
                    for d in details
                ],
                "human_error_type": "",
                "human_why_wrong": "",
                "human_missing_information_or_reasoning": "",
                "human_repeated_pattern": "",
                "human_possible_fix": "",
            }
        )

    with (args.output_dir / "errors.jsonl").open("w", encoding="utf-8") as f:
        for row in error_rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    with (args.output_dir / "errors.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "id",
                "category",
                "subcategory",
                "group_accuracy",
                "is_consistent",
                "scene",
                "question",
                "options",
                "gold_answer",
                "gold_content",
                "human_error_type",
                "human_why_wrong",
                "human_missing_information_or_reasoning",
                "human_repeated_pattern",
                "human_possible_fix",
            ],
        )
        writer.writeheader()
        for row in error_rows:
            flat = dict(row)
            flat["options"] = json.dumps(flat.get("options"), ensure_ascii=False)
            flat.pop("variant_outputs", None)
            writer.writerow(flat)

    worst_subcats = sorted(
        summary["subcategory_accuracy"].items(), key=lambda kv: (kv[1], kv[0])
    )[:15]

    audit = [
        "# CogToM Baseline Manual Audit",
        "",
        "> This document is intentionally a human worksheet. Do not auto-fill the core error taxonomy before personally reading the failures.",
        "",
        "## Run",
        "",
        f"- Model: `{metadata['model']}`",
        f"- Language: `{metadata['language']}`",
        f"- Groups: {len(rows)} (5 option-order variants per group)",
        f"- CogToM commit: `{metadata['cogtom_commit']}`",
        "",
        "## Automatic metrics",
        "",
        f"- Mean group accuracy: **{summary['mean_group_accuracy']:.4f}**",
        f"- All-5-variants-correct rate: **{summary['strict_all_variants_correct_rate']:.4f}**",
        f"- Semantic consistency rate: **{summary['semantic_consistency_rate']:.4f}**",
        f"- Groups with any error: **{summary['groups_with_any_error']}**",
        "",
        "## Lowest-scoring subcategories",
        "",
        "| Subcategory | Mean group accuracy |",
        "|---|---:|",
    ]
    audit.extend(f"| {name} | {score:.4f} |" for name, score in worst_subcats)
    audit.extend(
        [
            "",
            "## Manual audit protocol",
            "",
            "Read at least 100 failed/partially failed groups before defining HCL v0.1.",
            "",
            "For each error, record:",
            "",
            "1. What is explicitly known in the scenario?",
            "2. What did the model infer incorrectly?",
            "3. What distinction did it miss (belief, knowledge access, intent, emotion, perspective, second-order belief, etc.)?",
            "4. Is this an isolated error or a repeated mechanism?",
            "5. What *general* intervention might fix the mechanism without encoding this benchmark answer?",
            "",
            "Use `errors.csv` or `errors.jsonl` for row-level annotation.",
            "",
            "## Human findings",
            "",
            "### Repeated failure pattern 1",
            "- Evidence:",
            "- Why it matters:",
            "- Candidate mechanism:",
            "",
            "### Repeated failure pattern 2",
            "- Evidence:",
            "- Why it matters:",
            "- Candidate mechanism:",
            "",
            "### Repeated failure pattern 3",
            "- Evidence:",
            "- Why it matters:",
            "- Candidate mechanism:",
            "",
            "## Gate decision",
            "",
            "- [ ] Enough repeated model failures are understood to justify HCL v0.1.",
            "- [ ] The proposed mechanisms are benchmark-general, not answer memorization.",
            "- [ ] At least one failure class appears tractable with a portable cognition layer.",
            "",
        ]
    )
    (args.output_dir / "AUDIT.md").write_text("\n".join(audit), encoding="utf-8")

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
