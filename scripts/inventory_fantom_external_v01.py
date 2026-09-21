#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import io
import json
import tarfile
import urllib.request
from pathlib import Path
from typing import Any

import pandas as pd

FANTOM_URL = "https://storage.googleapis.com/ai2-mosaic-public/projects/fantom/fantom.tar.gz"
FANTOM_SHA256 = "1d08dfa0ea474c7f83b9bc7e3a7b466eab25194043489dd618b4c5223e1253a4"
FANTOM_REPO_COMMIT = "1cae6fa30f5ba04ca0fff5f5716b5ba7055e2e85"
SALT = "HCL-FANTOM-EXT-V01-20260921"

TARGETS = {
    "belief_inaccessible_first": 4,
    "belief_inaccessible_second": 4,
    "answerability_inaccessible_binary": 4,
    "info_accessibility_inaccessible_binary": 4,
    "belief_accessible_first": 4,
    "belief_accessible_second": 4,
    "fact_control": 8,
}

SELECTION_ORDER = [
    "belief_inaccessible_first",
    "belief_inaccessible_second",
    "answerability_inaccessible_binary",
    "info_accessibility_inaccessible_binary",
    "belief_accessible_first",
    "belief_accessible_second",
    "fact_control",
]


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def download_verified() -> bytes:
    with urllib.request.urlopen(FANTOM_URL, timeout=120) as response:
        data = response.read()
    actual = hashlib.sha256(data).hexdigest()
    if actual != FANTOM_SHA256:
        raise RuntimeError(
            f"FANToM archive hash mismatch: expected {FANTOM_SHA256}, got {actual}"
        )
    return data


def load_dataframe(archive: bytes) -> pd.DataFrame:
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as tar:
        members = [
            member
            for member in tar.getmembers()
            if member.isfile() and Path(member.name).name == "fantom_v1.json"
        ]
        if len(members) != 1:
            raise RuntimeError(
                f"Expected exactly one fantom_v1.json in archive, found {len(members)}"
            )
        fh = tar.extractfile(members[0])
        if fh is None:
            raise RuntimeError("Unable to read fantom_v1.json")
        raw = fh.read()
    return pd.read_json(io.BytesIO(raw))


def accessibility(qa: dict[str, Any]) -> str:
    value = str(qa.get("missed_info_accessibility", "")).lower()
    if value in {"accessible", "inaccessible"}:
        return value
    qtype = str(qa.get("question_type", "")).lower()
    if ":inaccessible" in qtype:
        return "inaccessible"
    if ":accessible" in qtype:
        return "accessible"
    return "unknown"


def tom_order(qa: dict[str, Any]) -> str:
    value = str(qa.get("tom_type", "")).lower()
    if "first" in value:
        return "first"
    if "second" in value:
        return "second"
    return "unknown"


def make_key(
    *,
    set_id: str,
    family: str,
    question: str,
    ordinal_in_family: int,
) -> str:
    canonical = json.dumps(
        [set_id, family, ordinal_in_family, question],
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return sha(canonical)


def add_candidate(
    buckets: dict[str, list[dict[str, Any]]],
    *,
    stratum: str,
    set_id: str,
    family: str,
    question: str,
    ordinal_in_family: int,
    question_type: str,
    order: str | None = None,
    access: str | None = None,
) -> None:
    key = make_key(
        set_id=set_id,
        family=family,
        question=question,
        ordinal_in_family=ordinal_in_family,
    )
    rank = sha(SALT + "|" + key)
    item: dict[str, Any] = {
        "question_id": key,
        "set_id": set_id,
        "family": family,
        "question_type": question_type,
        "selection_rank": rank,
    }
    if order is not None:
        item["tom_order"] = order
    if access is not None:
        item["accessibility"] = access
    if family == "belief_mc":
        item["correct_option"] = (
            "A" if int(sha(SALT + "|choice|" + key), 16) % 2 == 0 else "B"
        )
    buckets.setdefault(stratum, []).append(item)


def inventory(df: pd.DataFrame) -> dict[str, Any]:
    buckets: dict[str, list[dict[str, Any]]] = {}

    for _, row in df.iterrows():
        set_id = str(row["set_id"])

        fact = row.get("factQA")
        if isinstance(fact, dict) and fact.get("question") is not None:
            add_candidate(
                buckets,
                stratum="fact_control",
                set_id=set_id,
                family="fact",
                question=str(fact["question"]),
                ordinal_in_family=0,
                question_type=str(fact.get("question_type", "fact")),
            )

        belief_qas = row.get("beliefQAs")
        if isinstance(belief_qas, list):
            for idx, qa in enumerate(belief_qas):
                if not isinstance(qa, dict) or qa.get("question") is None:
                    continue
                access = accessibility(qa)
                order = tom_order(qa)
                if access not in {"accessible", "inaccessible"}:
                    continue
                if order not in {"first", "second"}:
                    continue
                stratum = f"belief_{access}_{order}"
                add_candidate(
                    buckets,
                    stratum=stratum,
                    set_id=set_id,
                    family="belief_mc",
                    question=str(qa["question"]),
                    ordinal_in_family=idx,
                    question_type=str(qa.get("question_type", "tom:belief")),
                    order=order,
                    access=access,
                )

        answer_qas = row.get("answerabilityQAs_binary")
        if isinstance(answer_qas, list):
            for idx, qa in enumerate(answer_qas):
                if not isinstance(qa, dict) or qa.get("question") is None:
                    continue
                if str(qa.get("correct_answer", "")).lower() == "no:long":
                    continue
                access = accessibility(qa)
                if access != "inaccessible":
                    continue
                add_candidate(
                    buckets,
                    stratum="answerability_inaccessible_binary",
                    set_id=set_id,
                    family="answerability_binary",
                    question=str(qa["question"]),
                    ordinal_in_family=idx,
                    question_type=str(qa.get("question_type", "")),
                    access=access,
                )

        access_qas = row.get("infoAccessibilityQAs_binary")
        if isinstance(access_qas, list):
            for idx, qa in enumerate(access_qas):
                if not isinstance(qa, dict) or qa.get("question") is None:
                    continue
                if str(qa.get("correct_answer", "")).lower() == "no:long":
                    continue
                access = accessibility(qa)
                if access != "inaccessible":
                    continue
                add_candidate(
                    buckets,
                    stratum="info_accessibility_inaccessible_binary",
                    set_id=set_id,
                    family="info_accessibility_binary",
                    question=str(qa["question"]),
                    ordinal_in_family=idx,
                    question_type=str(qa.get("question_type", "")),
                    access=access,
                )

    counts = {name: len(items) for name, items in sorted(buckets.items())}
    selected: list[dict[str, Any]] = []
    used_conversation_ids: set[str] = set()

    for stratum in SELECTION_ORDER:
        target = TARGETS[stratum]
        items = sorted(buckets.get(stratum, []), key=lambda item: item["selection_rank"])
        if len(items) < target:
            raise RuntimeError(
                f"FANToM stratum {stratum} has {len(items)} candidates, need {target}"
            )

        chosen: list[dict[str, Any]] = []
        for item in items:
            conversation_id = str(item["set_id"]).split("-")[0]
            if conversation_id in used_conversation_ids:
                continue
            item = dict(item)
            item["stratum"] = stratum
            item["conversation_id"] = conversation_id
            chosen.append(item)
            used_conversation_ids.add(conversation_id)
            if len(chosen) == target:
                break

        if len(chosen) != target:
            raise RuntimeError(
                f"FANToM stratum {stratum} could only provide {len(chosen)} "
                f"globally conversation-disjoint candidates, need {target}"
            )
        selected.extend(chosen)

    selected.sort(key=lambda item: (SELECTION_ORDER.index(item["stratum"]), item["selection_rank"]))

    if len(selected) != sum(TARGETS.values()):
        raise RuntimeError("Selected question count mismatch")
    if len({item["question_id"] for item in selected}) != len(selected):
        raise RuntimeError("Duplicate selected question_id")
    if len({item["conversation_id"] for item in selected}) != len(selected):
        raise RuntimeError("Selected questions are not conversation-disjoint")

    return {
        "source": {
            "repository": "skywalker023/fantom",
            "commit": FANTOM_REPO_COMMIT,
            "dataset_url": FANTOM_URL,
            "dataset_sha256": FANTOM_SHA256,
            "dataset_version": "1.0",
        },
        "selection": {
            "salt": SALT,
            "targets": TARGETS,
            "selection_order": SELECTION_ORDER,
            "total_selected": len(selected),
            "conversation_disjoint": True,
            "method": (
                "In fixed stratum order, greedily choose the lowest "
                "SHA256(salt|question_id) ranks whose FANToM conversation_id "
                "has not appeared in any previously selected question. Belief "
                "option orientation is SHA256-derived and fixed before model calls."
            ),
        },
        "dataset": {
            "rows": int(len(df)),
            "columns": sorted(str(c) for c in df.columns),
            "candidate_counts": counts,
        },
        "selected": selected,
        "claim_boundary": (
            "Inventory and deterministic selection only; no provider/model calls, "
            "no model outcomes, no tuning."
        ),
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument(
        "--out",
        type=Path,
        default=Path("artifacts/fantom-external-v01-inventory"),
    )
    args = p.parse_args()

    archive = download_verified()
    df = load_dataframe(archive)
    result = inventory(df)

    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "inventory.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "rows": result["dataset"]["rows"],
                "candidate_counts": result["dataset"]["candidate_counts"],
                "total_selected": result["selection"]["total_selected"],
                "selected": result["selected"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
