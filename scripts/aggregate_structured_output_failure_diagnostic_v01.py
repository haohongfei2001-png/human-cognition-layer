#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from statistics import median
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def numeric_summary(values: list[int]) -> dict[str, int | float | None]:
    if not values:
        return {"n": 0, "min": None, "median": None, "max": None}
    return {
        "n": len(values),
        "min": min(values),
        "median": median(values),
        "max": max(values),
    }


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    calls = [call for row in rows for call in row["provider_calls"]]
    categories = Counter(call["category"] for call in calls)
    finish_reasons = Counter(str(call.get("finish_reason")) for call in calls)
    top_types = Counter(
        str(call.get("json_top_level_type"))
        for call in calls
        if call.get("full_json_syntax_valid")
    )

    by_category_tokens: dict[str, list[int]] = defaultdict(list)
    by_category_bytes: dict[str, list[int]] = defaultdict(list)
    by_category_duration: dict[str, list[int]] = defaultdict(list)
    for call in calls:
        category = call["category"]
        if isinstance(call.get("completion_tokens"), int):
            by_category_tokens[category].append(call["completion_tokens"])
        if isinstance(call.get("response_bytes"), int):
            by_category_bytes[category].append(call["response_bytes"])
        if isinstance(call.get("duration_ms"), int):
            by_category_duration[category].append(call["duration_ms"])

    by_stratum: dict[str, dict[str, int]] = {}
    for row in rows:
        key = f"{row['length_band']}/{row['complexity']}"
        slot = by_stratum.setdefault(
            key,
            {"n": 0, "success": 0, "state_json_exhaustion": 0, "provider_exception": 0},
        )
        slot["n"] += 1
        if row["success"]:
            slot["success"] += 1
        elif row["failure_class"] in slot:
            slot[row["failure_class"]] += 1

    return {
        "suite": "HCL structured-output failure diagnostic v0.1",
        "fixture_count": len(rows),
        "case_success_count": sum(bool(row["success"]) for row in rows),
        "case_failure_count": sum(not bool(row["success"]) for row in rows),
        "state_json_exhaustion_count": sum(
            row["failure_class"] == "state_json_exhaustion" for row in rows
        ),
        "provider_exception_case_count": sum(
            row["failure_class"] == "provider_exception" for row in rows
        ),
        "provider_call_count": len(calls),
        "provider_call_categories": dict(sorted(categories.items())),
        "finish_reason_counts": dict(sorted(finish_reasons.items())),
        "json_top_level_type_counts": dict(sorted(top_types.items())),
        "empty_provider_call_count": sum(bool(call.get("empty_after_strip")) for call in calls),
        "nonempty_provider_call_count": sum(
            call.get("empty_after_strip") is False for call in calls
        ),
        "hcl_object_parseable_call_count": sum(
            bool(call.get("hcl_object_parseable")) for call in calls
        ),
        "completion_tokens_by_category": {
            key: numeric_summary(values)
            for key, values in sorted(by_category_tokens.items())
        },
        "response_bytes_by_category": {
            key: numeric_summary(values)
            for key, values in sorted(by_category_bytes.items())
        },
        "duration_ms_by_category": {
            key: numeric_summary(values)
            for key, values in sorted(by_category_duration.items())
        },
        "by_stratum": by_stratum,
        "diagnostic_complete": len(rows) == 24,
        "claim_boundary": (
            "Content-free provider/output diagnostic on frozen synthetic state-generation "
            "requests; no external benchmark content and no repair claim."
        ),
    }


def assert_content_free(summary: dict[str, Any], rows: list[dict[str, Any]]) -> None:
    raw = json.dumps({"summary": summary, "rows": rows}, ensure_ascii=False).lower()
    for key in (
        '"input":',
        '"prompt":',
        '"messages":',
        '"response":',
        '"response_text":',
        '"state":',
        '"parsed_json":',
        '"api_key":',
        '"exception_text":',
    ):
        if key in raw:
            raise RuntimeError(f"content-free artifact boundary violated: {key}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument(
        "--out",
        type=Path,
        default=ROOT / "artifacts/hcl-structured-output-diagnostic-v01-summary",
    )
    args = parser.parse_args()

    files = sorted(args.root.rglob("shard_*.json"))
    if len(files) != 6:
        raise RuntimeError(f"expected 6 shard files, got {len(files)}")

    rows: list[dict[str, Any]] = []
    shards: set[int] = set()
    for path in files:
        payload = json.loads(path.read_text(encoding="utf-8"))
        shards.add(int(payload["shard_index"]))
        if payload["requested"] != 4 or payload["completed"] != 4:
            raise RuntimeError("incomplete diagnostic shard")
        rows.extend(payload["results"])

    if shards != set(range(6)):
        raise RuntimeError("diagnostic shard coverage mismatch")
    if len(rows) != 24 or len({row["id"] for row in rows}) != 24:
        raise RuntimeError("diagnostic case coverage mismatch")

    summary = summarize(rows)
    assert_content_free(summary, rows)

    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (args.out / "results.jsonl").write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
