#!/usr/bin/env python3
"""Zero-provider CQ-00 qualification for HCL v0.6 perspective/belief work."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import tarfile
from collections import defaultdict
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

FANTOM_SHA256 = "1d08dfa0ea474c7f83b9bc7e3a7b466eab25194043489dd618b4c5223e1253a4"
FANTOM_COMMIT = "1cae6fa30f5ba04ca0fff5f5716b5ba7055e2e85"
DYNTOM_COMMIT = "9c95b1b8300f3e352626feae51aaeeda111b6d3d"

FANTOM_SALT = "HCL-V06-CQ00-FANTOM-DEV-20260925"
DYNTOM_SALT = "HCL-V06-CQ00-DYNTOM-20260925"

FANTOM_TARGETS = {
    "belief_inaccessible_first": 2,
    "belief_inaccessible_second": 2,
    "answerability_full_inaccessible_binary": 2,
    "info_accessibility_full_inaccessible_binary": 2,
}
FANTOM_ORDER = list(FANTOM_TARGETS)

FANTOM_V01 = ROOT / "eval/fantom/selection_v01.json"
FANTOM_V02 = ROOT / "eval/fantom/selection_v02.json"


class QualificationError(RuntimeError):
    pass


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _accessibility(qa: dict[str, Any]) -> str:
    value = str(qa.get("missed_info_accessibility", "")).lower()
    if value in {"accessible", "inaccessible"}:
        return value
    qtype = str(qa.get("question_type", "")).lower()
    if ":inaccessible" in qtype:
        return "inaccessible"
    if ":accessible" in qtype:
        return "accessible"
    return "unknown"


def _tom_order(qa: dict[str, Any]) -> str:
    value = str(qa.get("tom_type", "")).lower()
    if "first" in value:
        return "first"
    if "second" in value:
        return "second"
    return "unknown"


def _full_binary_accessibility(qas: Any) -> str:
    if not isinstance(qas, list) or not qas:
        return "unknown"
    for qa in qas:
        if isinstance(qa, dict) and str(qa.get("correct_answer", "")).lower() != "yes":
            return "inaccessible"
    return "accessible"


def _load_fantom_archive(path: Path) -> pd.DataFrame:
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != FANTOM_SHA256:
        raise QualificationError(
            f"FANToM archive hash mismatch: expected {FANTOM_SHA256}, got {digest}"
        )
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:gz") as tar:
        members = [
            m for m in tar.getmembers()
            if m.isfile() and Path(m.name).name == "fantom_v1.json"
        ]
        if len(members) != 1:
            raise QualificationError(
                f"Expected one fantom_v1.json, found {len(members)}"
            )
        fh = tar.extractfile(members[0])
        if fh is None:
            raise QualificationError("Unable to extract fantom_v1.json")
        data = fh.read()
    return pd.read_json(io.BytesIO(data))


def historical_fantom_conversations() -> set[str]:
    used: set[str] = set()
    for path in (FANTOM_V01, FANTOM_V02):
        data = json.loads(path.read_text(encoding="utf-8"))
        for item in data["selected"]:
            used.add(str(item["conversation_id"]))
    if len(used) != 80:
        raise QualificationError(
            f"Historical FANToM exposure expected 80 conversations, found {len(used)}"
        )
    return used


def inventory_fantom(df: pd.DataFrame) -> dict[str, Any]:
    historical = historical_fantom_conversations()
    conversation_strata: dict[str, set[str]] = defaultdict(set)

    for _, row in df.iterrows():
        set_id = str(row["set_id"])
        conversation_id = set_id.split("-")[0]
        if conversation_id in historical:
            continue

        belief_qas = row.get("beliefQAs")
        if isinstance(belief_qas, list):
            for qa in belief_qas:
                if not isinstance(qa, dict):
                    continue
                access = _accessibility(qa)
                order = _tom_order(qa)
                if access == "inaccessible" and order in {"first", "second"}:
                    conversation_strata[conversation_id].add(
                        f"belief_inaccessible_{order}"
                    )

        if _full_binary_accessibility(row.get("answerabilityQAs_binary")) == "inaccessible":
            conversation_strata[conversation_id].add(
                "answerability_full_inaccessible_binary"
            )

        if _full_binary_accessibility(row.get("infoAccessibilityQAs_binary")) == "inaccessible":
            conversation_strata[conversation_id].add(
                "info_accessibility_full_inaccessible_binary"
            )

    selected: list[dict[str, Any]] = []
    used: set[str] = set()
    candidate_counts: dict[str, int] = {}

    for stratum in FANTOM_ORDER:
        candidates = sorted(
            (
                (sha(f"{FANTOM_SALT}|{stratum}|{cid}"), cid)
                for cid, strata in conversation_strata.items()
                if stratum in strata
            ),
            key=lambda x: x[0],
        )
        candidate_counts[stratum] = len(candidates)
        need = FANTOM_TARGETS[stratum]
        chosen = 0
        for rank, cid in candidates:
            if cid in used:
                continue
            selected.append(
                {
                    "conversation_id": cid,
                    "selection_stratum": stratum,
                    "selection_rank": rank,
                }
            )
            used.add(cid)
            chosen += 1
            if chosen == need:
                break
        if chosen != need:
            raise QualificationError(
                f"FANToM stratum {stratum} provided {chosen}/{need} disjoint conversations"
            )

    if len(selected) != 8 or len(used) != 8:
        raise QualificationError("FANToM CQ-00 selection must contain 8 distinct conversations")
    if used & historical:
        raise QualificationError("FANToM CQ-00 selection overlaps historical exposure")

    return {
        "source": {
            "repository": "skywalker023/fantom",
            "commit": FANTOM_COMMIT,
            "dataset_sha256": FANTOM_SHA256,
        },
        "historical_consumed_conversations": len(historical),
        "eligible_conversations": len(conversation_strata),
        "candidate_counts": candidate_counts,
        "selection_salt": FANTOM_SALT,
        "selected_development_conversations": selected,
        "selected_count": 8,
        "provider_calls": 0,
    }


def _question_subject(question: dict[str, Any]) -> str:
    text = str(question.get("question", "")).lower()
    for subject in ("belief", "emotion", "intention", "action"):
        if subject in text:
            return subject
    return "other"


def inventory_dyntom(root: Path) -> dict[str, Any]:
    data_root = root / "data" / "script" / "data"
    if not data_root.is_dir():
        raise QualificationError(f"DynToM data directory missing: {data_root}")

    eligible: list[dict[str, Any]] = []
    total_trials = 0
    malformed = 0

    for trial in sorted(data_root.glob("trial*")):
        if not trial.is_dir():
            continue
        story_path = trial / "story.json"
        questions_path = trial / "question_new.json"
        if not story_path.is_file() or not questions_path.is_file():
            continue
        total_trials += 1
        try:
            story = json.loads(story_path.read_text(encoding="utf-8"))
            questions = json.loads(questions_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            malformed += 1
            continue

        scenario_count = story.get("scenario numbers")
        public_story = story.get("story")
        hidden_sketch = story.get("sketch")
        if not isinstance(scenario_count, int) or scenario_count < 2:
            continue
        if not public_story:
            continue
        if not isinstance(questions, dict):
            continue

        belief_by_type: dict[str, int] = defaultdict(int)
        for q in questions.values():
            if not isinstance(q, dict) or _question_subject(q) != "belief":
                continue
            qtype = str(q.get("question type", "missing"))
            belief_by_type[qtype] += 1

        if belief_by_type.get("type_a", 0) < 1 or belief_by_type.get("type_d", 0) < 1:
            continue

        trial_id = trial.name.removeprefix("trial")
        eligible.append(
            {
                "trial_id": trial_id,
                "scenario_count": scenario_count,
                "belief_type_a_count": belief_by_type.get("type_a", 0),
                "belief_type_d_count": belief_by_type.get("type_d", 0),
                "hidden_sketch_present": hidden_sketch is not None,
                "selection_rank": sha(f"{DYNTOM_SALT}|{trial_id}"),
            }
        )

    if malformed:
        raise QualificationError(f"DynToM contains {malformed} malformed eligible trial files")
    if len(eligible) < 12:
        raise QualificationError(f"DynToM has only {len(eligible)} eligible belief trials")

    eligible.sort(key=lambda x: x["selection_rank"])
    audit = eligible[:4]
    development = eligible[4:12]

    return {
        "source": {
            "repository": "GAIR-NLP/DynToM",
            "commit": DYNTOM_COMMIT,
        },
        "total_trials_with_story_and_questions": total_trials,
        "eligible_belief_trials": len(eligible),
        "selection_salt": DYNTOM_SALT,
        "narrative_sufficiency_audit_trials": audit,
        "development_trials_reserved_after_audit": development,
        "audit_count": 4,
        "development_count": 8,
        "provider_calls": 0,
        "qualification_note": (
            "DynToM gold questions are generated from a hidden mental-state sketch. "
            "The four audit trials must be manually checked for whether the public story "
            "supports the belief labels before the eight reserved development trials may "
            "enter CQ-01. Hidden sketch content is never an HCL input."
        ),
    }


def qualify(fantom_archive: Path, dyntom_root: Path) -> dict[str, Any]:
    fantom = inventory_fantom(_load_fantom_archive(fantom_archive))
    dyntom = inventory_dyntom(dyntom_root)
    return {
        "format": "hcl-v06-perspective-belief-cq00-v01",
        "status": "selection_frozen_manual_dyntom_sufficiency_audit_required",
        "provider_calls": 0,
        "fantom": fantom,
        "dyntom": dyntom,
        "gold_or_question_text_committed": False,
        "longmemeval_paid_triggered": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fantom-archive", type=Path, required=True)
    parser.add_argument("--dyntom-root", type=Path, required=True)
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("artifacts/hcl-v06-perspective-belief-cq00/qualification.json"),
    )
    args = parser.parse_args()

    result = qualify(args.fantom_archive, args.dyntom_root)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": result["status"],
                "provider_calls": 0,
                "fantom_selected": result["fantom"]["selected_count"],
                "dyntom_audit": result["dyntom"]["audit_count"],
                "dyntom_reserved_development": result["dyntom"]["development_count"],
                "historical_fantom_excluded": result["fantom"]["historical_consumed_conversations"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
