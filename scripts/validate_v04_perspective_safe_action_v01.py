"""Deterministic, provider-free preflight for the frozen correction-action fixture."""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from hcl.v04 import CognitionStore, EventRecord, HypothesisTarget, HypothesisTracker


FIXTURE = ROOT / "eval/v04/perspective_safe_action_v01.json"
FIXTURE_SHA256 = "f76844dac359059e0ffd14f69f4ef8d0f18a84878f915640b5f460b8cc3cd3b8"
ACTION_IDS = {"SEND_CORRECTION", "ASK_CONFIRMATION", "PROCEED", "VERIFY_SOURCE"}
NAMED_HYPOTHESES = {"NOT_RECEIVED", "RECEIVED_UNCONFIRMED", "ACCEPTED_CURRENT"}


def visible_case(case: dict) -> dict:
    """Use this projection in every model prompt; the scoring key is never visible."""
    return {key: value for key, value in case.items() if key not in {"expected_action", "forbidden_claims"}}


def validate_fixture(data: dict) -> None:
    cases = data.get("cases")
    if not isinstance(cases, list) or len(cases) != 6:
        raise ValueError("exactly six frozen synthetic cases are required")
    case_ids: set[str] = set()
    all_event_ids: set[str] = set()
    for case in cases:
        case_id = case["id"]
        if not isinstance(case_id, str) or not case_id or case_id in case_ids:
            raise ValueError("case IDs must be unique and nonempty")
        case_ids.add(case_id)
        target = case["target_recipient"]
        hypothesis = case["hypothesis_target"]
        if hypothesis["subject_agent_id"] != target:
            raise ValueError(f"{case_id}: hypothesis subject differs from target recipient")
        if {row[0] for row in hypothesis["candidates"]} != NAMED_HYPOTHESES:
            raise ValueError(f"{case_id}: frozen alternatives changed")
        actions = case["allowed_actions"]
        if len(actions) != 4 or {row[0] for row in actions} != ACTION_IDS:
            raise ValueError(f"{case_id}: allowed actions changed")
        if case["expected_action"] not in ACTION_IDS or not case["forbidden_claims"]:
            raise ValueError(f"{case_id}: missing gold or forbidden-claim audit")
        if "expected_action" in visible_case(case) or "forbidden_claims" in visible_case(case):
            raise ValueError(f"{case_id}: scoring key leaked to visible prompt")

        store = CognitionStore()
        try:
            tracker = HypothesisTracker(store)
            tracker.create_target(HypothesisTarget(
                target_id=hypothesis["target_id"], subject_agent_id=target,
                target_kind=hypothesis["target_kind"], question=hypothesis["question"],
                candidate_definitions=tuple((row[0], row[1]) for row in hypothesis["candidates"]),
            ))
            if {candidate.label for candidate in tracker.current(hypothesis["target_id"]).candidates} != NAMED_HYPOTHESES | {"OTHER_UNKNOWN"}:
                raise ValueError(f"{case_id}: OTHER_UNKNOWN is not available")
            previous_time: datetime | None = None
            events = case["events"]
            if not isinstance(events, list) or len(events) < 2 or len(events) > 5:
                raise ValueError(f"{case_id}: event count outside frozen bound")
            for event in events:
                event_id = event["event_id"]
                if event_id in all_event_ids:
                    raise ValueError(f"{case_id}: duplicate raw event ID")
                all_event_ids.add(event_id)
                valid_time = datetime.fromisoformat(event["valid_time"])
                recorded_at = datetime.fromisoformat(event["recorded_at"])
                if previous_time and valid_time <= previous_time or recorded_at < valid_time:
                    raise ValueError(f"{case_id}: invalid event chronology")
                previous_time = valid_time
                if "system" not in event["observer_ids"] or not event["source_id"] or not event["actor_id"]:
                    raise ValueError(f"{case_id}: missing system-visible provenance")
                if not isinstance(event["recipient_ids"], list) or not event["raw_text"].strip():
                    raise ValueError(f"{case_id}: invalid delivery or raw evidence")
                store.append_event(EventRecord(
                    event_id=event_id, valid_time=event["valid_time"], recorded_at=event["recorded_at"],
                    raw_text=event["raw_text"], source_id=event["source_id"], actor_id=event["actor_id"],
                    observer_ids=tuple(event["observer_ids"]), recipient_ids=tuple(event["recipient_ids"]),
                    metadata=event["metadata"],
                ))
        finally:
            store.close()


def preflight() -> dict:
    contents = FIXTURE.read_bytes()
    digest = hashlib.sha256(contents).hexdigest()
    if digest != FIXTURE_SHA256:
        raise ValueError(f"frozen fixture digest mismatch: {digest}")
    data = json.loads(contents)
    validate_fixture(data)
    return {"fixture_sha256": digest, "case_count": len(data["cases"]), "event_count": sum(len(case["events"]) for case in data["cases"])}


if __name__ == "__main__":
    print(json.dumps(preflight(), sort_keys=True))
