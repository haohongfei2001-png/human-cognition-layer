#!/usr/bin/env python3
"""Verify the source-only frozen, provider-unconsumed SAGA fresh slice."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.prepare_v07_saga_dev_v01 import sha, story_text

MANIFEST = ROOT / "eval/v07/saga_fresh_selection_v01.json"
DEVELOPMENT_MANIFEST = ROOT / "eval/v07/saga_dev_selection_v01.json"
DEVELOPMENT_SOURCE_SHA256 = "a00ed709011dfdcb2016b0bb25753eaca4445afdbf8ae87bf4b33c213e415764"


def verified_selection(source: bytes, development_source: bytes, manifest_path: Path = MANIFEST) -> list[tuple[dict, dict]]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("format") != "hcl-v07-saga-fresh-selection-v01":
        raise ValueError("unexpected fresh selection format")
    if sha(source) != manifest["source_sha256"]:
        raise ValueError("pinned SAGA validation source digest drift")
    records = [json.loads(line) for line in source.decode("utf-8").splitlines() if line.strip()]
    if len(records) != 106:
        raise ValueError("pinned SAGA validation row count drift")
    if sha(development_source) != DEVELOPMENT_SOURCE_SHA256:
        raise ValueError("pinned SAGA development source digest drift")
    development_records = [json.loads(line) for line in development_source.decode("utf-8").splitlines() if line.strip()]
    if len(development_records) != 219:
        raise ValueError("pinned SAGA development row count drift")
    validation_story_ids = {row["storyid"] for row in records}
    if validation_story_ids & {row["storyid"] for row in development_records}:
        raise ValueError("validation and development story families overlap")
    by_id = {str(row["instance_id"]): row for row in records}
    if len(by_id) != len(records):
        raise ValueError("duplicate SAGA instance ID")
    development = json.loads(DEVELOPMENT_MANIFEST.read_text(encoding="utf-8"))
    development_story_ids = {item["story_id"] for item in development["selected"]}
    if manifest["development_story_ids_excluded"] != sorted(development_story_ids):
        raise ValueError("development exclusion manifest drift")
    selected = manifest["selected"]
    if len(selected) != manifest["selected_count"] or len(selected) != 16:
        raise ValueError("fresh selection count drift")
    if Counter(item["source_tier"] for item in selected) != {
        "explicit_goal": 8, "inferred_goal": 8,
    }:
        raise ValueError("fresh source tiers drift")
    story_ids = {item["story_id"] for item in selected}
    if len(story_ids) != 16 or story_ids & development_story_ids:
        raise ValueError("fresh story-family duplication or development overlap")
    verified = []
    for item in selected:
        row = by_id[item["instance_id"]]
        if item["story_id"] != row["storyid"] or item["participant_id"] != row["participantid"]:
            raise ValueError("story/participant identity drift")
        if item["participant"] != row["participant"]:
            raise ValueError("participant name drift")
        if item["story_sha256"] != sha(story_text(row)):
            raise ValueError("source story digest drift")
        verified.append((item, row))
    return verified


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--development-source", type=Path, required=True)
    args = parser.parse_args()
    selected = verified_selection(args.source.read_bytes(), args.development_source.read_bytes())
    print(json.dumps({"selected": len(selected), "distinct_story_families": 16, "provider_calls": 0}))


if __name__ == "__main__":
    main()
