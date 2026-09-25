#!/usr/bin/env python3
"""Freeze a disjoint 32-conversation FANToM C/P/G/D pilot without provider calls."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.inventory_fantom_external_v02 import (
    FANTOM_REPO_COMMIT,
    FANTOM_SHA256,
    load_dataframe,
)
from scripts.prepare_v06_fantom_cpd_v01 import candidates_for_row

SALT = "HCL-V06-FANTOM-CPGD-FRESH-V01-20260925"
STRATA = (
    "belief_inaccessible_first",
    "belief_inaccessible_second",
    "answerability_full_inaccessible_binary",
    "info_accessibility_full_inaccessible_binary",
)
TARGET_PER_STRATUM = 8
HISTORICAL = (
    ROOT / "eval/fantom/selection_v01.json",
    ROOT / "eval/fantom/selection_v02.json",
)
DEVELOPMENT = ROOT / "eval/v06/fantom_cpd_selection_v01.json"


def sha(value: str | bytes) -> str:
    data = value.encode("utf-8") if isinstance(value, str) else value
    return hashlib.sha256(data).hexdigest()


def excluded_conversations() -> tuple[set[str], set[str]]:
    historical: set[str] = set()
    for path in HISTORICAL:
        data = json.loads(path.read_text(encoding="utf-8"))
        historical.update(str(row["conversation_id"]) for row in data["selected"])
    development = {
        str(row["conversation_id"])
        for row in json.loads(DEVELOPMENT.read_text(encoding="utf-8"))["selected"]
    }
    if len(historical) != 80 or len(development) != 8 or historical & development:
        raise RuntimeError("consumed FANToM exclusion register drift")
    return historical, development


def freeze_selection(archive: bytes, *, mechanism_main: str) -> dict[str, Any]:
    if sha(archive) != FANTOM_SHA256:
        raise RuntimeError("pinned FANToM archive digest mismatch")
    historical, development = excluded_conversations()
    excluded = historical | development
    dataframe = load_dataframe(archive)
    pools: dict[str, dict[str, dict[str, Any]]] = {stratum: {} for stratum in STRATA}

    for _, row in dataframe.iterrows():
        conversation_id = str(row["set_id"]).split("-")[0]
        if conversation_id in excluded:
            continue
        for stratum in STRATA:
            for candidate in candidates_for_row(row, stratum):
                item = dict(candidate)
                item["conversation_id"] = conversation_id
                item["selection_rank"] = sha(f"{SALT}|{stratum}|{item['question_id']}")
                item["context_sha256"] = sha(str(row["full_context"]).strip())
                family_field = {
                    "belief_mc": "beliefQAs",
                    "answerability_binary": "answerabilityQAs_binary",
                    "info_accessibility_binary": "infoAccessibilityQAs_binary",
                }[item["family"]]
                question = row[family_field][item["ordinal_in_family"]]["question"]
                item["question_sha256"] = sha(str(question))
                if item["family"] == "belief_mc":
                    item["correct_option"] = (
                        "A" if int(sha(f"{SALT}|choice|{item['question_id']}"), 16) % 2 == 0 else "B"
                    )
                previous = pools[stratum].get(conversation_id)
                if previous is None or (item["selection_rank"], item["question_id"]) < (
                    previous["selection_rank"], previous["question_id"]
                ):
                    pools[stratum][conversation_id] = item

    selected: list[dict[str, Any]] = []
    used: set[str] = set()
    for stratum in STRATA:
        ranked = sorted(
            pools[stratum].values(),
            key=lambda item: (item["selection_rank"], item["question_id"]),
        )
        chosen = [item for item in ranked if item["conversation_id"] not in used][
            :TARGET_PER_STRATUM
        ]
        if len(chosen) != TARGET_PER_STRATUM:
            raise RuntimeError(f"insufficient disjoint conversations for {stratum}")
        selected.extend(chosen)
        used.update(item["conversation_id"] for item in chosen)

    if len(selected) != 32 or len(used) != 32 or used & excluded:
        raise RuntimeError("fresh selection cardinality or disjointness failed")
    return {
        "format": "hcl-v06-fantom-cpgd-fresh-selection-v01",
        "claim_boundary": "Frozen fresh pilot selection; no provider outcome has been observed.",
        "source": {
            "repository": "skywalker023/fantom",
            "commit": FANTOM_REPO_COMMIT,
            "dataset_sha256": FANTOM_SHA256,
        },
        "mechanism_main": mechanism_main,
        "selection_salt": SALT,
        "excluded_historical_conversations": sorted(historical, key=int),
        "excluded_v06_development_conversations": sorted(development, key=int),
        "additional_consumed_conversations": [],
        "selected_count": 32,
        "selected": selected,
        "provider_calls": 0,
        "question_text_committed": False,
        "gold_text_committed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fantom-archive", type=Path, required=True)
    parser.add_argument("--mechanism-main", required=True)
    parser.add_argument(
        "--out", type=Path,
        default=ROOT / "eval/v06/fantom_cpgd_fresh_selection_v01.json",
    )
    args = parser.parse_args()
    result = freeze_selection(args.fantom_archive.read_bytes(), mechanism_main=args.mechanism_main)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"selected_count": 32, "provider_calls": 0, "ids": [x["conversation_id"] for x in result["selected"]]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
