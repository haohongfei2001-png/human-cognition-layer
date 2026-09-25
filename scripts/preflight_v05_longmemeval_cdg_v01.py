#!/usr/bin/env python3
"""Zero-provider, redacted validation of the sealed C/D/G input package."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.qualify_longmemeval_knowledge_update_v01 import (
    EXPECTED_DATASET_SHA256,
    assert_state_firewall,
    events_from_state_view,
    history_digest,
    sha256_file,
    state_input_view,
)

SELECTION = ROOT / "eval/longmemeval/knowledge_update_selection_v01.json"
DIAGNOSTIC = ROOT / "eval/longmemeval/knowledge_update_ingest_diagnostic_v01.json"


class PreflightError(ValueError):
    pass


def validate_manifest() -> tuple[dict, list[dict]]:
    selection = json.loads(SELECTION.read_text(encoding="utf-8"))
    diagnostic = json.loads(DIAGNOSTIC.read_text(encoding="utf-8"))
    if selection.get("format") != "hcl-v05-longmemeval-knowledge-update-selection-v01":
        raise PreflightError("selection format drift")
    if selection.get("dataset_sha256") != EXPECTED_DATASET_SHA256:
        raise PreflightError("selection dataset digest drift")
    rows = selection.get("selected")
    if not isinstance(rows, list) or len(rows) != 32:
        raise PreflightError("sealed selection must have 32 rows")
    if any(not isinstance(x, dict) or set(x) != {"question_id", "history_sha256"} for x in rows):
        raise PreflightError("selection entry schema drift")
    ids = [x["question_id"] for x in rows]
    if len(set(ids)) != 32 or any(not isinstance(x, str) or not x for x in ids):
        raise PreflightError("duplicate or invalid selected ID")
    if any(not isinstance(x["history_sha256"], str) or len(x["history_sha256"]) != 64 for x in rows):
        raise PreflightError("invalid selected history digest")
    diagnostic_ids = {x["question_id"] for x in diagnostic["selected"]}
    if set(ids) & diagnostic_ids:
        raise PreflightError("sealed/diagnostic overlap")
    return selection, rows


def preflight_dataset(path: Path, selected: list[dict]) -> dict:
    if sha256_file(path) != EXPECTED_DATASET_SHA256:
        raise PreflightError("pinned dataset digest mismatch")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise PreflightError("dataset must be a list")
    ids = [str(x.get("question_id", "")) for x in data]
    if len(ids) != len(set(ids)):
        raise PreflightError("duplicate dataset question ID")
    lookup = dict(zip(ids, data))
    summaries = []
    for item in selected:
        qid = item["question_id"]
        row = lookup.get(qid)
        if row is None or row.get("question_type") != "knowledge-update":
            raise PreflightError(f"selected row missing or wrong type: {qid}")
        view = state_input_view(row)
        assert_state_firewall(row, view)
        if history_digest(view) != item["history_sha256"]:
            raise PreflightError(f"selected history digest drift: {qid}")
        events = events_from_state_view(view, id_prefix="preflight")
        summaries.append({"question_id": qid, "history_sha256": item["history_sha256"],
                          "session_count": len(view["history"]), "event_count": len(events)})
    return {"format": "hcl-v05-longmemeval-cdg-preflight-v01",
            "provider_calls": 0, "dataset_sha256": EXPECTED_DATASET_SHA256,
            "selected_count": len(summaries),
            "total_events": sum(x["event_count"] for x in summaries),
            "maximum_events_per_row": max(x["event_count"] for x in summaries),
            "abstention_id_count": sum(x["question_id"].endswith("_abs") for x in summaries),
            "rows": summaries,
            "privacy_boundary": "IDs, hashes, and aggregate counts only; no question, answer, oracle labels, or raw history."}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    _, selected = validate_manifest()
    if args.dataset is None:
        result = {"selected_count": len(selected), "diagnostic_overlap": 0,
                  "dataset_checked": False, "provider_calls": 0}
    else:
        result = preflight_dataset(args.dataset, selected)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "rows"}, sort_keys=True))


if __name__ == "__main__":
    main()
