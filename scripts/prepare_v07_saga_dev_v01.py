#!/usr/bin/env python3
"""Verify the manually audited, development-only SAGA source slice."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "eval/v07/saga_dev_selection_v01.json"


def sha(data: bytes | str) -> str:
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def story_text(row: dict) -> str:
    return "\n".join(str(row[f"story_line{i}"]) for i in range(1, 6))


def verified_selection(source: bytes, manifest_path: Path = MANIFEST) -> list[tuple[dict, dict]]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("format") != "hcl-v07-saga-development-selection-v01":
        raise ValueError("unexpected selection format")
    if sha(source) != manifest["source_sha256"]:
        raise ValueError("pinned SAGA source digest drift")
    records = [json.loads(line) for line in source.decode("utf-8").splitlines() if line.strip()]
    if len(records) != 219:
        raise ValueError("pinned SAGA source row count drift")
    by_id = {str(row["instance_id"]): row for row in records}
    if len(by_id) != len(records):
        raise ValueError("duplicate SAGA instance ID")
    selected = manifest["selected"]
    if len(selected) != manifest["selected_count"] or len(selected) != 12:
        raise ValueError("development slice count drift")
    if Counter(item["source_tier"] for item in selected) != {
        "explicit_goal": 6, "inferred_goal": 6,
    }:
        raise ValueError("source-evidence tiers drift")
    if len({item["story_id"] for item in selected}) != len(selected):
        raise ValueError("one story appears more than once")
    verified = []
    for item in selected:
        row = by_id[item["instance_id"]]
        if item["story_id"] != row["storyid"] or item["participant_id"] != row["participantid"]:
            raise ValueError("story/participant identity drift")
        if item["participant"] != row["participant"]:
            raise ValueError("participant name drift")
        if item["story_sha256"] != sha(story_text(row)):
            raise ValueError("story source digest drift")
        verified.append((item, row))
    return verified


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    args = parser.parse_args()
    selected = verified_selection(args.source.read_bytes())
    print(json.dumps({"selected": len(selected), "story_groups": len({x[0]["story_id"] for x in selected}), "provider_calls": 0}))


if __name__ == "__main__":
    main()
