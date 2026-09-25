#!/usr/bin/env python3
"""Zero-provider selection for LongMemEval external ingest compatibility v0.1."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from scripts.qualify_longmemeval_knowledge_update_v01 import (
    EXPECTED_DATASET_SHA256,
    history_digest,
    sha256_file,
    state_input_view,
)

DIAG_SALT = "HCL-LONGMEMEVAL-KU-INGEST-DIAG-V01-20260925"
DIAG_SIZE = 2


class SelectionError(ValueError):
    pass


def rank(qid: str) -> str:
    return hashlib.sha256(f"{DIAG_SALT}|{qid}".encode("utf-8")).hexdigest()


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--dataset", type=Path, required=True)
    p.add_argument(
        "--sealed-selection",
        type=Path,
        default=Path("eval/longmemeval/knowledge_update_selection_v01.json"),
    )
    p.add_argument(
        "--out",
        type=Path,
        default=Path(
            "artifacts/longmemeval-ingest-diagnostic-selection-v01/manifest.json"
        ),
    )
    args = p.parse_args()

    observed_sha = sha256_file(args.dataset)
    if observed_sha != EXPECTED_DATASET_SHA256:
        raise SelectionError(
            f"dataset SHA mismatch: {observed_sha} != {EXPECTED_DATASET_SHA256}"
        )

    data = json.loads(args.dataset.read_text(encoding="utf-8"))
    sealed = json.loads(args.sealed_selection.read_text(encoding="utf-8"))
    sealed_ids = {x["question_id"] for x in sealed["selected"]}
    if len(sealed_ids) != 32:
        raise SelectionError("sealed efficacy selection must contain 32 unique IDs")

    candidates = []
    for row in data:
        if row.get("question_type") != "knowledge-update":
            continue
        qid = str(row.get("question_id", "")).strip()
        if not qid or qid in sealed_ids:
            continue
        view = state_input_view(row)
        candidates.append(
            {
                "question_id": qid,
                "history_sha256": history_digest(view),
                "rank": rank(qid),
                "session_count": len(view["history"]),
                "turn_count": sum(len(x["turns"]) for x in view["history"]),
            }
        )

    if len(candidates) != 46:
        raise SelectionError(
            f"expected 46 unsealed knowledge-update rows, got {len(candidates)}"
        )

    candidates.sort(key=lambda x: (x["rank"], x["question_id"]))
    selected = candidates[:DIAG_SIZE]

    out = {
        "format": "hcl-v05-longmemeval-ingest-diagnostic-selection-v01",
        "provider_calls": 0,
        "dataset_sha256": observed_sha,
        "selection_salt": DIAG_SALT,
        "excluded_sealed_count": len(sealed_ids),
        "candidate_count": len(candidates),
        "selected_count": len(selected),
        "selected": [
            {
                "question_id": x["question_id"],
                "history_sha256": x["history_sha256"],
                "session_count": x["session_count"],
                "turn_count": x["turn_count"],
            }
            for x in selected
        ],
        "privacy_boundary": "IDs/hashes/counts only; no question, answer, or history text.",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(out, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(out, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
