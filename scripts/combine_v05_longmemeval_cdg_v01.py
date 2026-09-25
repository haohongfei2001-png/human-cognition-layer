#!/usr/bin/env python3
"""Combine exactly eight complete one-shot answer shards before judge access."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.preflight_v05_longmemeval_cdg_v01 import validate_manifest
from scripts.qualify_longmemeval_knowledge_update_v01 import EXPECTED_DATASET_SHA256


class CombineError(ValueError):
    pass


def combine(shards: list[dict], selected: list[dict]) -> dict:
    if len(shards) != 8:
        raise CombineError("exactly eight shards required")
    run_heads = {x.get("run_head") for x in shards}
    if len(run_heads) != 1 or None in run_heads:
        raise CombineError("shard run heads differ or are missing")
    by_index = {}
    for shard in shards:
        i = shard.get("shard_index")
        if not isinstance(i, int) or i in by_index or not 0 <= i < 8:
            raise CombineError("invalid or duplicate shard index")
        if shard.get("format") != "hcl-v05-longmemeval-cdg-answers-v01":
            raise CombineError("answer format drift")
        if shard.get("status") != "answers_complete_unscored":
            raise CombineError("partial shard cannot be combined")
        if shard.get("shard_count") != 8 or shard.get("dataset_sha256") != EXPECTED_DATASET_SHA256:
            raise CombineError("shard topology or dataset drift")
        expected = [x["question_id"] for x in selected[i::8]]
        actual = [x.get("question_id") for x in shard.get("rows", [])]
        if len(expected) != 4 or actual != expected or shard.get("attempted_ids") != expected:
            raise CombineError("shard selected IDs differ from frozen topology")
        by_index[i] = shard
    if set(by_index) != set(range(8)):
        raise CombineError("missing shard")
    rows = {row["question_id"]: row for shard in shards for row in shard["rows"]}
    ids = [x["question_id"] for x in selected]
    if len(rows) != 32 or set(rows) != set(ids):
        raise CombineError("combined row identity mismatch")
    meters = {}
    for arm in ("C", "D", "G"):
        keys = ("calls", "json_calls", "text_calls", "input_chars", "output_chars",
                "provider_wall_seconds")
        meters[arm] = {key: sum(by_index[i]["backend"][arm][key] for i in range(8))
                       for key in keys}
    return {"format": "hcl-v05-longmemeval-cdg-answers-v01",
            "status": "answers_complete_unscored", "run_head": run_heads.pop(),
            "dataset_sha256": EXPECTED_DATASET_SHA256,
            "selected_count": 32, "attempted_ids": ids,
            "rows": [rows[qid] for qid in ids], "backend": meters,
            "source_shards": list(range(8))}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--shard-dir", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    _, selected = validate_manifest()
    files = sorted(args.shard_dir.rglob("raw-answers-shard-*.json"))
    if len(files) != 8:
        raise CombineError(f"found {len(files)} shard files, require eight")
    shards = [json.loads(x.read_text(encoding="utf-8")) for x in files]
    result = combine(shards, selected)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"selected_count": 32, "status": result["status"],
                      "run_head": result["run_head"]}, sort_keys=True))


if __name__ == "__main__":
    main()
