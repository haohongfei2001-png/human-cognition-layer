from __future__ import annotations

import json
import unittest

from hcl.v04 import (
    CognitionStore,
    EventRecord,
    HypothesisStatus,
    HypothesisTarget,
    HypothesisTracker,
)
from hcl.v04.schema import SchemaValidationError


T0 = "2026-04-01T10:00:00+00:00"


class FakeBackend:
    def __init__(self, outputs):
        self.outputs = list(outputs)
        self.calls = []

    def complete_json(self, messages, *, max_tokens, temperature=0.0):
        self.calls.append(messages)
        if not self.outputs:
            raise AssertionError("unexpected complete_json call")
        return self.outputs.pop(0)


def event(event_id: str, text: str) -> EventRecord:
    return EventRecord(
        event_id=event_id,
        valid_time=T0,
        recorded_at=T0,
        raw_text=text,
        source_id="environment",
        actor_id="agent",
        observer_ids=("agent",),
    )


def target() -> HypothesisTarget:
    return HypothesisTarget(
        target_id="t1",
        subject_agent_id="agent",
        target_kind="INTENTION",
        question="Why is the agent delaying?",
        candidate_definitions=(
            ("BUSY", "The agent is overloaded with other work."),
            ("AVOIDING", "The agent is intentionally avoiding the task."),
        ),
    )


def state_payload(*, busy="PLAUSIBLE", avoiding="PLAUSIBLE", other="PLAUSIBLE"):
    return {
        "candidates": [
            {
                "label": "BUSY",
                "status": busy,
                "support_event_ids": ["e1"] if busy == "SUPPORTED" else [],
                "counterevidence_event_ids": [],
                "unresolved_event_ids": [],
                "rationale": "Evidence update for BUSY.",
            },
            {
                "label": "AVOIDING",
                "status": avoiding,
                "support_event_ids": [],
                "counterevidence_event_ids": ["e1"] if avoiding == "WEAKENED" else [],
                "unresolved_event_ids": [],
                "rationale": "Evidence update for AVOIDING.",
            },
            {
                "label": "OTHER_UNKNOWN",
                "status": other,
                "support_event_ids": [],
                "counterevidence_event_ids": [],
                "unresolved_event_ids": ["e1"] if other == "PLAUSIBLE" else [],
                "rationale": "Unknown alternatives remain possible.",
            },
        ]
    }


class HypothesisTrackerTests(unittest.TestCase):
    def setUp(self):
        self.store = CognitionStore()
        self.tracker = HypothesisTracker(self.store)
        self.tracker.create_target(target())
        self.store.append_event(event("e1", "The agent says there is a deadline conflict."))

    def tearDown(self):
        self.store.close()

    def test_other_unknown_is_mandatory(self):
        current = self.tracker.current("t1")
        labels = {c.label for c in current.candidates}
        self.assertEqual(labels, {"BUSY", "AVOIDING", "OTHER_UNKNOWN"})
        self.assertEqual(current.version, 0)

    def test_valid_update_creates_new_version(self):
        backend = FakeBackend([json.dumps(state_payload(busy="SUPPORTED", avoiding="WEAKENED"))])
        receipt = self.tracker.update("t1", ["e1"], backend)
        self.assertEqual(receipt.version, 1)
        current = self.tracker.current("t1")
        by_label = {c.label: c for c in current.candidates}
        self.assertEqual(by_label["BUSY"].status, HypothesisStatus.SUPPORTED)
        self.assertEqual(by_label["BUSY"].support_event_ids, ("e1",))
        self.assertEqual(by_label["AVOIDING"].status, HypothesisStatus.WEAKENED)
        self.assertEqual(by_label["AVOIDING"].counterevidence_event_ids, ("e1",))
        self.assertEqual(len(self.tracker.history("t1")), 2)

    def test_invalid_event_reference_is_atomic(self):
        bad = state_payload()
        bad["candidates"][0]["support_event_ids"] = ["missing"]
        repaired_bad = json.loads(json.dumps(bad))
        backend = FakeBackend([json.dumps(bad), json.dumps(repaired_bad)])
        with self.assertRaises(SchemaValidationError):
            self.tracker.update("t1", ["e1"], backend)
        self.assertEqual(self.tracker.current("t1").version, 0)
        self.assertEqual(len(self.tracker.history("t1")), 1)

    def test_candidate_label_mutation_is_rejected(self):
        bad = state_payload()
        bad["candidates"][0]["label"] = "NEW_LABEL"
        backend = FakeBackend([json.dumps(bad), json.dumps(bad)])
        with self.assertRaises(SchemaValidationError):
            self.tracker.update("t1", ["e1"], backend)
        self.assertEqual(self.tracker.current("t1").version, 0)

    def test_duplicate_evidence_roles_are_rejected(self):
        bad = state_payload()
        bad["candidates"][0]["support_event_ids"] = ["e1"]
        bad["candidates"][0]["counterevidence_event_ids"] = ["e1"]
        backend = FakeBackend([json.dumps(bad), json.dumps(bad)])
        with self.assertRaises(SchemaValidationError):
            self.tracker.update("t1", ["e1"], backend)
        self.assertEqual(self.tracker.current("t1").version, 0)

    def test_previous_version_remains_queryable(self):
        backend = FakeBackend([json.dumps(state_payload(busy="SUPPORTED"))])
        self.tracker.update("t1", ["e1"], backend)
        history = self.tracker.history("t1")
        self.assertEqual(history[0].version, 0)
        self.assertEqual(history[1].version, 1)
        first = {c.label: c.status for c in history[0].candidates}
        second = {c.label: c.status for c in history[1].candidates}
        self.assertEqual(first["BUSY"], HypothesisStatus.PLAUSIBLE)
        self.assertEqual(second["BUSY"], HypothesisStatus.SUPPORTED)

    def test_bounded_repair_can_recover_without_partial_commit(self):
        bad = state_payload()
        bad["candidates"][0]["label"] = "WRONG"
        repaired = state_payload(busy="SUPPORTED")
        backend = FakeBackend([json.dumps(bad), json.dumps(repaired)])
        receipt = self.tracker.update("t1", ["e1"], backend)
        self.assertTrue(receipt.repaired)
        self.assertIsNotNone(receipt.repair_reason)
        self.assertEqual(self.tracker.current("t1").version, 1)

    def test_rebuild_from_raw_events_creates_valid_new_version(self):
        first_backend = FakeBackend([json.dumps(state_payload(busy="SUPPORTED"))])
        self.tracker.update("t1", ["e1"], first_backend)
        rebuild_backend = FakeBackend([json.dumps(state_payload(busy="SUPPORTED"))])
        receipt = self.tracker.rebuild("t1", rebuild_backend)
        self.assertEqual(receipt.operation, "REBUILD")
        self.assertEqual(receipt.version, 2)
        current = self.tracker.current("t1")
        self.assertEqual(current.version, 2)
        labels = {c.label for c in current.candidates}
        self.assertEqual(labels, {"BUSY", "AVOIDING", "OTHER_UNKNOWN"})


if __name__ == "__main__":
    unittest.main()
