#!/usr/bin/env python3
"""Freeze the exact 8-question FANToM C/P/D development utility selection."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.inventory_fantom_external_v02 import (
    accessibility,
    load_dataframe,
    make_key,
    sha,
    tom_order,
)

CQ00_FILE = ROOT / "eval/v06/perspective_belief_cq00_v01.json"
SALT = "HCL-V06-FANTOM-CPD-V01-20260925"


def _full_binary_accessibility(qas: Any) -> str:
    if not isinstance(qas, list) or not qas:
        return "unknown"
    for qa in qas:
        if isinstance(qa, dict) and str(qa.get("correct_answer", "")).lower() != "yes":
            return "inaccessible"
    return "accessible"


def _candidate(
    *,
    set_id: str,
    family: str,
    ordinal: int,
    question: str,
    stratum: str,
) -> dict[str, Any]:
    qid = make_key(
        set_id=set_id,
        family=family,
        question=question,
        ordinal_in_family=ordinal,
    )
    return {
        "question_id": qid,
        "set_id": set_id,
        "family": family,
        "ordinal_in_family": ordinal,
        "stratum": stratum,
        "selection_rank": sha(f"{SALT}|{qid}"),
    }


def candidates_for_row(row: Any, desired_stratum: str) -> list[dict[str, Any]]:
    set_id = str(row["set_id"])
    result: list[dict[str, Any]] = []

    if desired_stratum in {
        "belief_inaccessible_first",
        "belief_inaccessible_second",
    }:
        desired_order = "first" if desired_stratum.endswith("_first") else "second"
        qas = row.get("beliefQAs")
        if isinstance(qas, list):
            for idx, qa in enumerate(qas):
                if not isinstance(qa, dict) or qa.get("question") is None:
                    continue
                if accessibility(qa) != "inaccessible":
                    continue
                if tom_order(qa) != desired_order:
                    continue
                result.append(
                    _candidate(
                        set_id=set_id,
                        family="belief_mc",
                        ordinal=idx,
                        question=str(qa["question"]),
                        stratum=desired_stratum,
                    )
                )
        return result

    if desired_stratum == "answerability_full_inaccessible_binary":
        qas = row.get("answerabilityQAs_binary")
        if _full_binary_accessibility(qas) != "inaccessible":
            return result
        if isinstance(qas, list):
            for idx, qa in enumerate(qas):
                if not isinstance(qa, dict) or qa.get("question") is None:
                    continue
                # The development probe targets a real information-asymmetry
                # miss, not an unrelated long-context outsider.
                if str(qa.get("correct_answer", "")).lower() != "no":
                    continue
                result.append(
                    _candidate(
                        set_id=set_id,
                        family="answerability_binary",
                        ordinal=idx,
                        question=str(qa["question"]),
                        stratum=desired_stratum,
                    )
                )
        return result

    if desired_stratum == "info_accessibility_full_inaccessible_binary":
        qas = row.get("infoAccessibilityQAs_binary")
        if _full_binary_accessibility(qas) != "inaccessible":
            return result
        if isinstance(qas, list):
            for idx, qa in enumerate(qas):
                if not isinstance(qa, dict) or qa.get("question") is None:
                    continue
                if str(qa.get("correct_answer", "")).lower() != "no":
                    continue
                result.append(
                    _candidate(
                        set_id=set_id,
                        family="info_accessibility_binary",
                        ordinal=idx,
                        question=str(qa["question"]),
                        stratum=desired_stratum,
                    )
                )
        return result

    raise ValueError(f"unsupported CQ-00 stratum: {desired_stratum}")


def freeze_selection(df: Any) -> dict[str, Any]:
    cq00 = json.loads(CQ00_FILE.read_text(encoding="utf-8"))
    source = cq00["fantom"]
    frozen: list[dict[str, Any]] = []

    for conversation in source["development_selection"]:
        cid = str(conversation["conversation_id"])
        stratum = str(conversation["stratum"])
        candidates: list[dict[str, Any]] = []
        for _, row in df.iterrows():
            set_id = str(row["set_id"])
            if set_id.split("-")[0] != cid:
                continue
            candidates.extend(candidates_for_row(row, stratum))

        if not candidates:
            raise RuntimeError(
                f"no eligible C/P/D question for conversation={cid} stratum={stratum}"
            )
        candidates.sort(key=lambda x: (x["selection_rank"], x["question_id"]))
        chosen = dict(candidates[0])
        chosen["conversation_id"] = cid
        if chosen["family"] == "belief_mc":
            chosen["correct_option"] = (
                "A"
                if int(sha(f"{SALT}|choice|{chosen['question_id']}"), 16) % 2 == 0
                else "B"
            )
        frozen.append(chosen)

    if len(frozen) != 8:
        raise RuntimeError(f"expected 8 development questions, got {len(frozen)}")
    if len({x["conversation_id"] for x in frozen}) != 8:
        raise RuntimeError("C/P/D questions are not conversation-disjoint")
    if len({x["question_id"] for x in frozen}) != 8:
        raise RuntimeError("duplicate C/P/D question id")

    frozen.sort(
        key=lambda x: (
            [str(y["conversation_id"]) for y in source["development_selection"]].index(
                x["conversation_id"]
            )
        )
    )
    return {
        "format": "hcl-v06-fantom-cpd-selection-v01",
        "source": {
            "repository": source["source_repo"],
            "commit": source["source_commit"],
            "dataset_sha256": source["dataset_sha256"],
        },
        "selection_salt": SALT,
        "selected_count": 8,
        "selected": frozen,
        "provider_calls": 0,
        "question_text_committed": False,
        "gold_text_committed": False,
        "claim_boundary": (
            "Development utility selection only. Conversations were frozen in "
            "CQ-00 before provider execution. One deterministic perspective-"
            "relevant question is selected per conversation without model outcomes."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fantom-archive", type=Path, required=True)
    parser.add_argument(
        "--out",
        type=Path,
        default=ROOT / "eval/v06/fantom_cpd_selection_v01.json",
    )
    args = parser.parse_args()

    df = load_dataframe(args.fantom_archive.read_bytes())
    result = freeze_selection(df)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "selected_count": result["selected_count"],
                "provider_calls": 0,
                "selected": result["selected"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
