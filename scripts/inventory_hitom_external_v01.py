#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

SALT = "HCL-HITOM-V01-20260922"
PINNED_COMMIT = "4279d3f783ff4f3b9fcced2a2fec9f6328683f82"
DATA_BLOB_SHA = "23ab2aee6b2e80115dd645d88b91529ad2a29309"
TARGET_PER_CELL = 2


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def parse_choices(text: str) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for part in re.split(r",\s*", str(text).strip()):
        match = re.match(r"^([A-Z])\.\s*(.*)$", part)
        if not match:
            raise RuntimeError(f"Unparseable choice segment: {part!r}")
        out.append((match.group(1), match.group(2)))
    return out


def gold_option(row: dict[str, Any]) -> str:
    matches = [
        letter
        for letter, value in parse_choices(row["choices"])
        if value == row["answer"]
    ]
    if len(matches) != 1:
        raise RuntimeError(
            f"Expected unique gold option for sample_id={row.get('sample_id')}, "
            f"got {matches}"
        )
    return matches[0]


def inventory(rows: list[dict[str, Any]]) -> dict[str, Any]:
    vp = [row for row in rows if row.get("prompting_type") == "VP"]
    if len(vp) != 600:
        raise RuntimeError(f"Expected 600 VP rows, got {len(vp)}")

    sample_ids = [str(row["sample_id"]) for row in vp]
    if len(set(sample_ids)) != 600:
        raise RuntimeError("VP sample_id is not globally unique")

    buckets: dict[tuple[int, bool, int], list[dict[str, Any]]] = {}

    for row in vp:
        order = int(row["question_order"])
        deception = bool(row["deception"])
        story_length = int(row["story_length"])
        if order not in {0,1,2,3,4}:
            raise RuntimeError(f"Unexpected question_order: {order}")
        if story_length not in {1,2,3}:
            raise RuntimeError(f"Unexpected story_length: {story_length}")

        story_hash = sha(str(row["story"]))
        item = {
            "sample_id": int(row["sample_id"]),
            "question_order": order,
            "deception": deception,
            "story_length": story_length,
            "story_sha256": story_hash,
            "gold_option": gold_option(row),
        }
        item["selection_rank"] = sha(
            f"{SALT}|{item['sample_id']}|{story_hash}|"
            f"{order}|{int(deception)}|{story_length}"
        )
        buckets.setdefault((order, deception, story_length), []).append(item)

    counts = {
        f"order{order}_deception{str(deception).lower()}_length{length}":
            len(buckets.get((order, deception, length), []))
        for order in range(5)
        for deception in (False, True)
        for length in (1,2,3)
    }

    expected_cells = 5 * 2 * 3
    if len(counts) != expected_cells or any(v != 20 for v in counts.values()):
        raise RuntimeError(f"Unexpected Hi-ToM VP cell counts: {counts}")

    selected: list[dict[str, Any]] = []
    used_stories: set[str] = set()

    for order in range(5):
        for deception in (False, True):
            for length in (1,2,3):
                candidates = sorted(
                    buckets[(order, deception, length)],
                    key=lambda item: item["selection_rank"],
                )
                chosen: list[dict[str, Any]] = []
                for item in candidates:
                    if item["story_sha256"] in used_stories:
                        continue
                    chosen.append(dict(item))
                    used_stories.add(item["story_sha256"])
                    if len(chosen) == TARGET_PER_CELL:
                        break
                if len(chosen) != TARGET_PER_CELL:
                    raise RuntimeError(
                        "Could not satisfy globally story-disjoint quota for "
                        f"order={order}, deception={deception}, length={length}"
                    )
                selected.extend(chosen)

    if len(selected) != 60:
        raise RuntimeError(f"Expected 60 selected rows, got {len(selected)}")
    if len({x["sample_id"] for x in selected}) != 60:
        raise RuntimeError("Selected sample IDs are not unique")
    if len({x["story_sha256"] for x in selected}) != 60:
        raise RuntimeError("Selected stories are not globally unique")

    return {
        "source": {
            "repository": "ying-hui-he/Hi-ToM_dataset",
            "commit": PINNED_COMMIT,
            "data_path": "Hi-ToM_data/Hi-ToM_data.json",
            "data_blob_sha": DATA_BLOB_SHA,
            "license": "Apache-2.0",
        },
        "selection": {
            "salt": SALT,
            "prompting_type": "VP",
            "target_per_cell": TARGET_PER_CELL,
            "total_selected": 60,
            "story_disjoint": True,
            "method": (
                "For each fixed order 0..4, deception false/true, story_length "
                "1..3 cell, rank VP rows by SHA256 of fixed salt and stable row "
                "identity; choose the first two whose story SHA has not been used "
                "anywhere earlier in the fixed cell order."
            ),
        },
        "dataset": {
            "total_rows": len(rows),
            "vp_rows": len(vp),
            "vp_unique_stories": len({sha(str(row["story"])) for row in vp}),
            "cell_counts": counts,
        },
        "selected": selected,
        "claim_boundary": (
            "Zero-provider inventory and deterministic sample selection only; "
            "no model calls or outcomes."
        ),
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--dataset", type=Path, required=True)
    p.add_argument(
        "--out",
        type=Path,
        default=Path("artifacts/hitom-external-v01-inventory"),
    )
    args = p.parse_args()

    rows = json.loads(args.dataset.read_text(encoding="utf-8"))
    if not isinstance(rows, list):
        raise RuntimeError("Hi-ToM dataset root must be a list")

    result = inventory(rows)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "inventory.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(json.dumps({
        "total_rows": result["dataset"]["total_rows"],
        "vp_rows": result["dataset"]["vp_rows"],
        "vp_unique_stories": result["dataset"]["vp_unique_stories"],
        "total_selected": result["selection"]["total_selected"],
        "selected": result["selected"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
