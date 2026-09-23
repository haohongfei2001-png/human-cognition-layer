from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from hcl.v04.evidence_scoped_revision import EvidenceScopedRevision, PendingEvidenceError
from hcl.v04.hypotheses import HypothesisTarget
from hcl.v04.model import EventRecord
from hcl.v04.schema import SchemaValidationError
from hcl.v04.store import CognitionStore

T0 = "2026-04-01T10:00:00+00:00"


class FakeBackend:
    def __init__(self, *outputs: dict):
        self.outputs = list(outputs)
        self.calls = 0

    def complete_json(self, messages, *, max_tokens, temperature=0.0):
        self.calls += 1
        if not self.outputs:
            raise AssertionError("unexpected hypothesis call")
        return json.dumps(self.outputs.pop(0))


def target(target_id: str) -> HypothesisTarget:
    return HypothesisTarget(
        target_id=target_id,
        subject_agent_id=target_id,
        target_kind="INTENTION",
        question="Why did the subject delay?",
        candidate_definitions=(("BUSY", "Competing work"), ("AVOIDING", "Avoiding task")),
    )


def event(event_id: str, *, observer: str = "observer") -> EventRecord:
    return EventRecord(
        event_id=event_id, valid_time=T0, recorded_at=T0,
        raw_text=f"Synthetic observation {event_id}", source_id="environment",
        actor_id="observer", observer_ids=(observer,),
    )


def state(*, support: tuple[str, ...] = (), unknown: tuple[str, ...] = ()) -> dict:
    return {"candidates": [
        {"label": "BUSY", "status": "SUPPORTED" if support else "PLAUSIBLE",
         "support_event_ids": list(support), "counterevidence_event_ids": [],
         "unresolved_event_ids": [], "rationale": "Only cited evidence changes this candidate."},
        {"label": "AVOIDING", "status": "PLAUSIBLE", "support_event_ids": [],
         "counterevidence_event_ids": [], "unresolved_event_ids": [],
         "rationale": "No decisive evidence."},
        {"label": "OTHER_UNKNOWN", "status": "PLAUSIBLE", "support_event_ids": [],
         "counterevidence_event_ids": [], "unresolved_event_ids": list(unknown),
         "rationale": "Unknown remains possible."},
    ]}


class EvidenceScopedRevisionTests(unittest.TestCase):
    def setUp(self):
        self.store = CognitionStore()
        self.revision = EvidenceScopedRevision(self.store)
        self.revision.register_target(target("a"))
        self.revision.register_target(target("b"))

    def tearDown(self):
        self.store.close()

    def test_always_on_evidence_batches_before_action_and_is_idempotent(self):
        self.revision.record(event("e1"), target_ids=("a",))
        self.revision.record(event("e2"), target_ids=("a",))
        with self.assertRaises(PendingEvidenceError):
            self.revision.current("a")
        with self.assertRaises(PendingEvidenceError):
            self.revision.evidence_for_target("a")
        backend = FakeBackend(state(support=("e1",), unknown=("e2",)))
        result = self.revision.refresh("a", backend)
        self.assertEqual(result.new_event_ids, ("e1", "e2"))
        self.assertEqual(result.state.version, 1)
        self.assertEqual(backend.calls, 1)
        self.assertEqual(self.revision.refresh("a", backend).state.version, 1)
        self.assertEqual(backend.calls, 1)
        self.assertEqual([e.event_id for e in self.store.list_events()], ["e1", "e2"])
        self.assertEqual(self.store.get_event("e1").observer_ids, ("observer",))

    def test_explicit_scope_skips_unrelated_events_but_unknown_is_conservative(self):
        self.revision.record(event("a-only"), target_ids=("a",))
        self.revision.record(event("unscoped", observer="system"))
        backend = FakeBackend(state(support=("unscoped",)))
        result = self.revision.refresh("b", backend)
        self.assertEqual(result.new_event_ids, ("unscoped",))
        self.assertEqual(result.skipped_unrelated, 1)
        self.assertEqual(backend.calls, 1)
        self.assertEqual(self.store.get_event("unscoped").observer_ids, ("system",))
        self.assertEqual(self.revision.current("b").version, 1)
        self.assertEqual(
            [item.event_id for item in self.revision.evidence_for_target("b")],
            ["unscoped"],
        )

    def test_unrelated_evidence_reference_fails_closed_without_cursor_advance(self):
        self.revision.record(event("a-only"), target_ids=("a",))
        self.revision.record(event("b-only"), target_ids=("b",))
        bad = state(support=("b-only",))
        backend = FakeBackend(bad, bad)
        with self.assertRaises(SchemaValidationError):
            self.revision.refresh("a", backend)
        with self.assertRaises(PendingEvidenceError):
            self.revision.current("a")
        self.assertEqual(self.revision.tracker.current("a").version, 0)
        self.assertEqual(backend.calls, 2)

    def test_duplicate_event_cannot_change_explicit_scope(self):
        self.revision.record(event("e1"), target_ids=("a",))
        with self.assertRaises(SchemaValidationError):
            self.revision.record(event("e1"), target_ids=("b",))
        self.assertEqual(self.revision.refresh("b", FakeBackend()).new_event_ids, ())

    def test_committed_revision_recovers_cursor_without_repeating_model_call(self):
        self.revision.record(event("e1"), target_ids=("a",))
        self.revision.tracker.update(
            "a", ("e1",), FakeBackend(state(support=("e1",))),
            allowed_event_ids={"e1"},
        )
        with self.assertRaises(PendingEvidenceError):
            self.revision.current("a")
        backend = FakeBackend()
        result = self.revision.refresh("a", backend)
        self.assertEqual(result.state.version, 1)
        self.assertIsNone(result.receipt)
        self.assertEqual(backend.calls, 0)

    def test_cursor_and_raw_evidence_survive_reopen(self):
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / "evidence.sqlite")
            first_store = CognitionStore(path)
            first = EvidenceScopedRevision(first_store)
            first.register_target(target("persistent"))
            first.record(event("first"), target_ids=("persistent",))
            first.refresh("persistent", FakeBackend(state(support=("first",))))
            first_store.close()
            second_store = CognitionStore(path)
            try:
                second = EvidenceScopedRevision(second_store)
                self.assertEqual(second.current("persistent").version, 1)
                second.record(event("second", observer="other"), target_ids=("persistent",))
                with self.assertRaises(PendingEvidenceError):
                    second.current("persistent")
                updated = second.refresh("persistent", FakeBackend(state(support=("first", "second"))))
                self.assertEqual(updated.new_event_ids, ("second",))
                self.assertEqual(updated.state.version, 2)
                self.assertEqual(second_store.get_event("first").raw_text, "Synthetic observation first")
            finally:
                second_store.close()


if __name__ == "__main__":
    unittest.main()
