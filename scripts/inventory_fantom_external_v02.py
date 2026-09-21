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

ROOT = Path(__file__).resolve().parents[1]

FANTOM_URL = "https://storage.googleapis.com/ai2-mosaic-public/projects/fantom/fantom.tar.gz"
FANTOM_SHA256 = "1d08dfa0ea474c7f83b9bc7e3a7b466eab25194043489dd618b4c5223e1253a4"
FANTOM_REPO_COMMIT = "1cae6fa30f5ba04ca0fff5f5716b5ba7055e2e85"
SALT = "HCL-FANTOM-FULL-V02-20260921"

V01_SELECTION = ROOT / "eval/fantom/selection_v01.json"

TARGETS = {
    "belief_inaccessible_first": 8,
    "belief_inaccessible_second": 8,
    "answerability_full_inaccessible_binary": 8,
    "info_accessibility_full_inaccessible_binary": 8,
    "belief_accessible_first": 4,
    "belief_accessible_second": 4,
    "fact_control": 8,
}

SELECTION_ORDER = [
    "belief_inaccessible_first",
    "belief_inaccessible_second",
    "answerability_full_inaccessible_binary",
    "info_accessibility_full_inaccessible_binary",
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


def full_binary_accessibility(qas: Any) -> str:
    if not isinstance(qas, list) or not qas:
        return "unknown"
    # Mirrors FANToM full-context setup: any non-yes target makes the set's
    # binary questions inaccessible for full-context grouping.
    for qa in qas:
        if not isinstance(qa, dict):
            continue
        if str(qa.get("correct_answer", "")).lower() != "yes":
            return "inaccessible"
    return "accessible"


def used_v01_conversations() -> set[str]:
    data = json.loads(V01_SELECTION.read_text(encoding="utf-8"))
    return {str(item["conversation_id"]) for item in data["selected"]}


def inventory(df: pd.DataFrame) -> dict[str, Any]:
    buckets: dict[str, list[dict[str, Any]]] = {}
    excluded_v01 = used_v01_conversations()

    for _, row in df.iterrows():
        set_id = str(row["set_id"])
        conversation_id = set_id.split("-")[0]
        if conversation_id in excluded_v01:
            continue

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
                add_candidate(
                    buckets,
                    stratum=f"belief_{access}_{order}",
                    set_id=set_id,
                    family="belief_mc",
                    question=str(qa["question"]),
                    ordinal_in_family=idx,
                    question_type=str(qa.get("question_type", "tom:belief")),
                    order=order,
                    access=access,
                )

        answer_qas = row.get("answerabilityQAs_binary")
        full_answer_access = full_binary_accessibility(answer_qas)
        if isinstance(answer_qas, list) and full_answer_access == "inaccessible":
            for idx, qa in enumerate(answer_qas):
                if not isinstance(qa, dict) or qa.get("question") is None:
                    continue
                add_candidate(
                    buckets,
                    stratum="answerability_full_inaccessible_binary",
                    set_id=set_id,
                    family="answerability_binary",
                    question=str(qa["question"]),
                    ordinal_in_family=idx,
                    question_type=str(qa.get("question_type", "")),
                    access="inaccessible",
                )

        info_qas = row.get("infoAccessibilityQAs_binary")
        full_info_access = full_binary_accessibility(info_qas)
        if isinstance(info_qas, list) and full_info_access == "inaccessible":
            for idx, qa in enumerate(info_qas):
                if not isinstance(qa, dict) or qa.get("question") is None:
                    continue
                add_candidate(
                    buckets,
                    stratum="info_accessibility_full_inaccessible_binary",
                    set_id=set_id,
                    family="info_accessibility_binary",
                    question=str(qa["question"]),
                    ordinal_in_family=idx,
                    question_type=str(qa.get("question_type", "")),
                    access="inaccessible",
                )

    counts = {name: len(items) for name, items in sorted(buckets.items())}
    selected: list[dict[str, Any]] = []
    used_conversations: set[str] = set()

    for stratum in SELECTION_ORDER:
        target = TARGETS[stratum]
        items = sorted(buckets.get(stratum, []), key=lambda item: item["selection_rank"])
        if len(items) < target:
            raise RuntimeError(
                f"FANToM v0.2 stratum {stratum} has {len(items)} candidates, "
                f"need {target}"
            )

        chosen: list[dict[str, Any]] = []
        for item in items:
            conversation_id = str(item["set_id"]).split("-")[0]
            if conversation_id in excluded_v01 or conversation_id in used_conversations:
                continue
            frozen = dict(item)
            frozen["stratum"] = stratum
            frozen["conversation_id"] = conversation_id
            chosen.append(frozen)
            used_conversations.add(conversation_id)
            if len(chosen) == target:
                break

        if len(chosen) != target:
            raise RuntimeError(
                f"FANToM v0.2 stratum {stratum} could only provide "
                f"{len(chosen)} globally disjoint unused conversations, need {target}"
            )
        selected.extend(chosen)

    selected.sort(
        key=lambda item: (
            SELECTION_ORDER.index(item["stratum"]),
            item["selection_rank"],
        )
    )

    if len(selected) != 48:
        raise RuntimeError(f"Expected 48 selected questions, got {len(selected)}")
    if len({item["question_id"] for item in selected}) != 48:
        raise RuntimeError("Duplicate selected question_id")
    if len({item["conversation_id"] for item in selected}) != 48:
        raise RuntimeError("Selected v0.2 questions are not conversation-disjoint")
    if {item["conversation_id"] for item in selected} & excluded_v01:
        raise RuntimeError("v0.2 selection overlaps consumed v0.1 conversations")

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
            "total_selected": 48,
            "conversation_disjoint": True,
            "v01_conversation_overlap": 0,
            "context_type": "full",
            "method": (
                "Exclude every v0.1 conversation. In fixed stratum order, "
                "greedily select lowest SHA256(salt|question_id) candidates "
                "whose conversation_id is unused in v0.2. Belief A/B orientation "
                "is fixed by the same salt before provider calls."
            ),
        },
        "dataset": {
            "rows": int(len(df)),
            "excluded_v01_conversations": len(excluded_v01),
            "candidate_counts_after_v01_exclusion": counts,
        },
        "selected": selected,
        "claim_boundary": (
            "Zero-provider full-context inventory only; no model outcomes, "
            "no tuning, no reuse of v0.1 conversations."
        ),
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument(
        "--out",
        type=Path,
        default=Path("artifacts/fantom-external-v02-inventory"),
    )
    args = p.parse_args()

    df = load_dataframe(download_verified())
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
                "excluded_v01_conversations": result["dataset"][
                    "excluded_v01_conversations"
                ],
                "candidate_counts": result["dataset"][
                    "candidate_counts_after_v01_exclusion"
                ],
                "total_selected": result["selection"]["total_selected"],
                "v01_overlap": result["selection"]["v01_conversation_overlap"],
                "selected": result["selected"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
