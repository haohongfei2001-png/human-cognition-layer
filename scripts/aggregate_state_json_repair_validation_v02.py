#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    json_failures = [x for x in rows if x["failure_class"] == "state_json_exhaustion"]
    other_failures = [x for x in rows if x["failure_class"] == "backend_or_other_exception"]

    by_stratum: dict[str, dict[str, int]] = {}
    for item in rows:
        key = f"{item['length_band']}/{item['complexity']}"
        slot = by_stratum.setdefault(
            key,
            {
                "n": 0,
                "success": 0,
                "state_json_exhaustion": 0,
                "backend_or_other_exception": 0,
            },
        )
        slot["n"] += 1
        if item["success"]:
            slot["success"] += 1
        elif item["failure_class"]:
            slot[item["failure_class"]] += 1

    all_structured = all(
        attempt.get("structured_mode") is True
        for item in rows
        for attempt in item["attempts"]
    )
    repair_pass = (
        len(rows) == 24
        and sum(bool(x["success"]) for x in rows) == 24
        and not json_failures
        and not other_failures
        and all_structured
    )

    return {
        "suite": "HCL state-JSON reliability repair validation v0.2",
        "fixture_count": len(rows),
        "success_count": sum(bool(x["success"]) for x in rows),
        "failure_count": sum(not bool(x["success"]) for x in rows),
        "state_json_exhaustion_count": len(json_failures),
        "backend_or_other_exception_count": len(other_failures),
        "all_state_attempts_used_structured_mode": all_structured,
        "by_stratum": by_stratum,
        "repair_pass": repair_pass,
        "claim_boundary": (
            "Independent synthetic validation of state JSON execution reliability; "
            "no external benchmark content and no efficacy claim."
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
        '"normalized_state":',
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
        default=ROOT / "artifacts/hcl-state-json-repair-v02-summary",
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
            raise RuntimeError("incomplete repair-validation shard")
        rows.extend(payload["results"])

    if shards != set(range(6)):
        raise RuntimeError("repair-validation shard coverage mismatch")
    if len(rows) != 24 or len({x["id"] for x in rows}) != 24:
        raise RuntimeError("repair-validation case coverage mismatch")

    summary = summarize(rows)
    assert_content_free(summary, rows)

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
