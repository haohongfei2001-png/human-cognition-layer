#!/usr/bin/env python3
"""Zero-provider LongMemEval knowledge-update qualification.

This script intentionally never calls an LLM. It verifies the pinned cleaned-S
dataset, enforces the state-construction firewall, and freezes a deterministic
question-id selection without persisting question/answer/history text.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

EXPECTED_DATASET_SHA256 = (
    "d6f21ea9d60a0d56f34a05b609c79c88a451d2ae03597821ea3d5a9678c3a442"
)
DATASET_REVISION = "98d7416c24c778c2fee6e6f3006e7a073259d48f"
UPSTREAM_CODE_COMMIT = "9e0b455f4ef0e2ab8f2e582289761153549043fc"
SELECTION_SALT = "HCL-LONGMEMEVAL-KU-EQ02-20260925"
TARGET_SIZE = 32

FORBIDDEN_STATE_FIELDS = {
    "answer",
    "answer_session_ids",
    "question",
    "has_answer",
    "autoeval_label",
    "gold",
    "correct_answer",
}


class QualificationError(ValueError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def selection_rank(question_id: str) -> str:
    return hashlib.sha256(
        f"{SELECTION_SALT}|{question_id}".encode("utf-8")
    ).hexdigest()


def parse_longmemeval_timestamp(value: str) -> datetime:
    try:
        dt = datetime.strptime(str(value), "%Y/%m/%d (%a) %H:%M")
    except ValueError as exc:
        raise QualificationError(
            f"unsupported LongMemEval timestamp format: {value!r}"
        ) from exc
    return dt.replace(tzinfo=timezone.utc)


def sanitized_turn(turn: dict[str, Any]) -> dict[str, str]:
    if not isinstance(turn, dict):
        raise QualificationError("history turn must be an object")
    role = str(turn.get("role", "")).strip()
    content = str(turn.get("content", ""))
    if role not in {"user", "assistant"}:
        raise QualificationError(f"unexpected history role: {role!r}")
    if not content.strip():
        raise QualificationError("history turn content must not be empty")
    # Deliberately discard all auxiliary labels such as has_answer.
    return {"role": role, "content": content}


def state_input_view(row: dict[str, Any]) -> dict[str, Any]:
    """Return the only benchmark material allowed to reach HCL state ingestion."""
    session_ids = row.get("haystack_session_ids")
    dates = row.get("haystack_dates")
    sessions = row.get("haystack_sessions")
    if not all(isinstance(x, list) for x in (session_ids, dates, sessions)):
        raise QualificationError("haystack ids/dates/sessions must be lists")
    if not (len(session_ids) == len(dates) == len(sessions)):
        raise QualificationError("haystack ids/dates/sessions length mismatch")

    history = []
    previous_dt: datetime | None = None
    for session_id, date, session in zip(session_ids, dates, sessions):
        dt = parse_longmemeval_timestamp(str(date))
        if previous_dt is not None and dt < previous_dt:
            raise QualificationError("cleaned-S haystack timestamps are not monotonic")
        previous_dt = dt
        if not isinstance(session, list):
            raise QualificationError("haystack session must be a list of turns")
        history.append(
            {
                "session_id": str(session_id),
                "date": str(date),
                "turns": [sanitized_turn(turn) for turn in session],
            }
        )
    return {"history": history}


def assert_state_firewall(row: dict[str, Any], view: dict[str, Any]) -> None:
    serialized = json.dumps(view, ensure_ascii=False, sort_keys=True)
    # Sentinel checks catch accidental value leakage in unit tests and real data
    # without needing to inspect/log those values.
    for field in ("question", "answer"):
        value = row.get(field)
        if isinstance(value, str) and value and value in serialized:
            raise QualificationError(f"{field} leaked into state input")
    for session in row.get("haystack_sessions") or []:
        for turn in session:
            if isinstance(turn, dict) and "has_answer" in turn:
                if "has_answer" in serialized:
                    raise QualificationError("has_answer leaked into state input")
    if "answer_session_ids" in serialized:
        raise QualificationError("answer_session_ids leaked into state input")


def history_digest(view: dict[str, Any]) -> str:
    material = json.dumps(
        view, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(material).hexdigest()


def events_from_state_view(
    view: dict[str, Any],
    *,
    id_prefix: str,
) -> list[dict[str, Any]]:
    """Convert only permitted history material into canonical event-shaped records."""
    events: list[dict[str, Any]] = []
    global_index = 0
    for session_index, session in enumerate(view["history"]):
        base = parse_longmemeval_timestamp(session["date"])
        for turn_index, turn in enumerate(session["turns"]):
            global_index += 1
            # Preserve benchmark chronology. Microsecond offsets only break ties
            # deterministically; they do not reorder sessions.
            valid = base + timedelta(microseconds=turn_index)
            recorded = base + timedelta(microseconds=global_index)
            role = turn["role"]
            actor = "longmemeval_user" if role == "user" else "longmemeval_assistant"
            recipient = (
                "longmemeval_assistant"
                if role == "user"
                else "longmemeval_user"
            )
            events.append(
                {
                    "event_id": (
                        f"{id_prefix}-s{session_index:03d}-t{turn_index:03d}"
                    ),
                    "valid_time": valid.isoformat(),
                    "recorded_at": recorded.isoformat(),
                    "source_id": actor,
                    "actor_id": actor,
                    "observer_ids": [],
                    "recipient_ids": [recipient],
                    "raw_text": turn["content"],
                    "metadata": {
                        "benchmark": "LongMemEval-cleaned-S",
                        "session_id": session["session_id"],
                        "role": role,
                    },
                }
            )
    return events


def audit_dataset(path: Path) -> dict[str, Any]:
    observed_sha = sha256_file(path)
    if observed_sha != EXPECTED_DATASET_SHA256:
        raise QualificationError(
            f"dataset SHA mismatch: {observed_sha} != {EXPECTED_DATASET_SHA256}"
        )

    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise QualificationError("LongMemEval cleaned-S must be a JSON list")

    qids: set[str] = set()
    counts: Counter[str] = Counter()
    knowledge_rows: list[dict[str, Any]] = []

    for row in data:
        if not isinstance(row, dict):
            raise QualificationError("dataset row must be an object")
        qid = str(row.get("question_id", "")).strip()
        qtype = str(row.get("question_type", "")).strip()
        if not qid or not qtype:
            raise QualificationError("row missing question_id/question_type")
        if qid in qids:
            raise QualificationError(f"duplicate question_id: {qid}")
        qids.add(qid)
        counts[qtype] += 1
        if qtype == "knowledge-update":
            view = state_input_view(row)
            assert_state_firewall(row, view)
            events = events_from_state_view(
                view, id_prefix=hashlib.sha256(qid.encode()).hexdigest()[:16]
            )
            if not events:
                raise QualificationError(
                    f"knowledge-update row {qid} has no ingestible events"
                )
            knowledge_rows.append(
                {
                    "question_id": qid,
                    "rank": selection_rank(qid),
                    "history_sha256": history_digest(view),
                    "session_count": len(view["history"]),
                    "turn_count": len(events),
                    "user_turn_count": sum(
                        event["actor_id"] == "longmemeval_user"
                        for event in events
                    ),
                    "assistant_turn_count": sum(
                        event["actor_id"] == "longmemeval_assistant"
                        for event in events
                    ),
                }
            )

    if len(data) != 500:
        raise QualificationError(f"expected 500 cleaned-S rows, observed {len(data)}")
    if len(knowledge_rows) < TARGET_SIZE:
        raise QualificationError(
            f"need at least {TARGET_SIZE} knowledge-update rows, "
            f"observed {len(knowledge_rows)}"
        )

    knowledge_rows.sort(key=lambda row: (row["rank"], row["question_id"]))
    selected = knowledge_rows[:TARGET_SIZE]

    return {
        "format": "hcl-v05-longmemeval-knowledge-update-eq02-qualification-v01",
        "provider_calls": 0,
        "upstream_code_commit": UPSTREAM_CODE_COMMIT,
        "dataset_revision": DATASET_REVISION,
        "dataset_sha256": observed_sha,
        "selection_salt": SELECTION_SALT,
        "total_rows": len(data),
        "question_type_counts": dict(sorted(counts.items())),
        "knowledge_update_rows": len(knowledge_rows),
        "selected_count": len(selected),
        "selected": [
            {
                "question_id": row["question_id"],
                "history_sha256": row["history_sha256"],
                "session_count": row["session_count"],
                "turn_count": row["turn_count"],
                "user_turn_count": row["user_turn_count"],
                "assistant_turn_count": row["assistant_turn_count"],
            }
            for row in selected
        ],
        "state_input_fields": [
            "haystack_session_ids",
            "haystack_dates",
            "haystack_sessions.role",
            "haystack_sessions.content",
        ],
        "forbidden_state_inputs": sorted(FORBIDDEN_STATE_FIELDS),
        "claim_boundary": (
            "Zero-provider qualification only. Manifest stores IDs/statistics/"
            "history hashes; no question, answer, or history text."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument(
        "--out",
        type=Path,
        default=Path(
            "artifacts/longmemeval-eq02-qualification/manifest.json"
        ),
    )
    args = parser.parse_args()
    result = audit_dataset(args.dataset)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "dataset_sha256": result["dataset_sha256"],
                "total_rows": result["total_rows"],
                "question_type_counts": result["question_type_counts"],
                "knowledge_update_rows": result["knowledge_update_rows"],
                "selected_count": result["selected_count"],
                "selected_question_ids": [
                    x["question_id"] for x in result["selected"]
                ],
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
