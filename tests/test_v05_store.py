"""Provider-free persistence tests for HCL v0.5."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from hcl.v04.model import EventRecord
from hcl.v05 import HCLV05Runtime, StanceStatus, V05Store
from hcl.v05.semantic import SemanticExtractionError


class FakeBackend:
    def __init__(self, outputs):
        self.outputs = list(outputs)
        self.calls = []

    def complete_json(self, messages, *, max_tokens, temperature=0.0):
        self.calls.append(messages)
        if not self.outputs:
            raise AssertionError("unexpected backend call")
        return self.outputs.pop(0)


def event(event_id, text, *, actor=None, recipients=(), minute=0):
    return EventRecord(
        event_id=event_id,
        valid_time=f"2026-03-01T10:{minute:02d}:00+00:00",
        recorded_at=f"2026-03-01T10:{minute:02d}:01+00:00",
        raw_text=text,
        source_id=actor or "source",
        actor_id=actor,
        recipient_ids=tuple(recipients),
    )


def payload(*rows):
    return json.dumps({"stance_events": list(rows)})


class V05PersistenceTests(unittest.TestCase):
    def test_restart_preserves_raw_and_derived_stance(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = str(Path(tmp) / "stance.sqlite")
            runtime = HCLV05Runtime(path=db)
            runtime.ingest_event(
                event("e1", "Ari accepts Red.", actor="ari"),
                FakeBackend(
                    [
                        payload(
                            {
                                "subject_agent_id": "ari",
                                "issue_key": "route_assignment",
                                "signal": "AFFIRM",
                                "value_key": "RED",
                                "prior_value_key": None,
                            }
                        )
                    ]
                ),
            )
            before = runtime.current_stance("ari", "route_assignment")
            runtime.close()

            reopened = HCLV05Runtime(path=db)
            self.assertEqual(len(reopened.events), 1)
            self.assertEqual(len(reopened.stance_events), 1)
            after = reopened.current_stance("ari", "route_assignment")
            self.assertEqual(after, before)
            self.assertEqual(after.status, StanceStatus.AFFIRMED)
            self.assertEqual(after.affirmed_value_key, "RED")
            reopened.close()

    def test_semantic_failure_persists_across_restart_and_can_reprocess(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = str(Path(tmp) / "stance.sqlite")
            raw = event("e1", "Ari accepts Red.", actor="ari")
            invalid = payload(
                {
                    "subject_agent_id": "other",
                    "issue_key": "route_assignment",
                    "signal": "AFFIRM",
                    "value_key": "RED",
                    "prior_value_key": None,
                }
            )

            runtime = HCLV05Runtime(path=db)
            with self.assertRaises(SemanticExtractionError):
                runtime.ingest_event(raw, FakeBackend([invalid, invalid]))
            self.assertIn("e1", runtime.semantic_failures)
            runtime.close()

            reopened = HCLV05Runtime(path=db)
            self.assertEqual(reopened.events[0], raw)
            self.assertIn("e1", reopened.semantic_failures)
            repaired = reopened.reprocess_event(
                "e1",
                FakeBackend(
                    [
                        payload(
                            {
                                "subject_agent_id": "ari",
                                "issue_key": "route_assignment",
                                "signal": "AFFIRM",
                                "value_key": "RED",
                                "prior_value_key": None,
                            }
                        )
                    ]
                ),
            )
            self.assertFalse(repaired.duplicate)
            self.assertNotIn("e1", reopened.semantic_failures)
            self.assertEqual(
                reopened.current_stance(
                    "ari", "route_assignment"
                ).affirmed_value_key,
                "RED",
            )
            reopened.close()

    def test_empty_semantic_commit_is_persisted_as_completed(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = str(Path(tmp) / "stance.sqlite")
            raw = event("e1", "Routine note.", actor="source")
            runtime = HCLV05Runtime(path=db)
            first_backend = FakeBackend([payload()])
            first = runtime.ingest_event(raw, first_backend)
            self.assertEqual(first.stance_events, ())
            runtime.close()

            reopened = HCLV05Runtime(path=db)
            duplicate_backend = FakeBackend([])
            duplicate = reopened.ingest_event(raw, duplicate_backend)
            self.assertTrue(duplicate.duplicate)
            self.assertEqual(duplicate.stance_events, ())
            self.assertEqual(len(duplicate_backend.calls), 0)
            reopened.close()

    def test_changed_duplicate_fails_across_restart(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = str(Path(tmp) / "stance.sqlite")
            runtime = HCLV05Runtime(path=db)
            runtime.ingest_event(
                event("e1", "Routine note.", actor="source"),
                FakeBackend([payload()]),
            )
            runtime.close()

            reopened = HCLV05Runtime(path=db)
            with self.assertRaises(ValueError):
                reopened.ingest_event(
                    event("e1", "Changed routine note.", actor="source"),
                    FakeBackend([]),
                )
            reopened.close()

    def test_invalidation_removes_current_stance_but_preserves_raw_and_audit(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = str(Path(tmp) / "stance.sqlite")
            runtime = HCLV05Runtime(path=db)
            raw = event("e1", "Ari accepts Red.", actor="ari")
            runtime.ingest_event(
                raw,
                FakeBackend(
                    [
                        payload(
                            {
                                "subject_agent_id": "ari",
                                "issue_key": "route_assignment",
                                "signal": "AFFIRM",
                                "value_key": "RED",
                                "prior_value_key": None,
                            }
                        )
                    ]
                ),
            )
            self.assertEqual(
                runtime.current_stance(
                    "ari", "route_assignment"
                ).affirmed_value_key,
                "RED",
            )

            runtime.invalidate_semantics("e1", "semantic interpretation was wrong")
            state = runtime.current_stance("ari", "route_assignment")
            self.assertEqual(state.status, StanceStatus.NO_AFFIRMED_VALUE)
            self.assertEqual(runtime.events[0], raw)
            self.assertEqual(runtime.store.semantic_status("e1"), "INVALIDATED")
            history = runtime.store.invalidation_history("e1")
            self.assertEqual(len(history), 1)
            self.assertEqual(
                history[0]["prior_stance_payloads"][0]["value_key"],
                "RED",
            )
            self.assertEqual(
                history[0]["prior_receipt"]["status"],
                "COMMITTED",
            )
            runtime.close()

    def test_invalidated_duplicate_requires_explicit_reprocess(self):
        runtime = HCLV05Runtime()
        try:
            raw = event("e1", "Ari accepts Red.", actor="ari")
            runtime.ingest_event(
                raw,
                FakeBackend(
                    [
                        payload(
                            {
                                "subject_agent_id": "ari",
                                "issue_key": "route_assignment",
                                "signal": "AFFIRM",
                                "value_key": "RED",
                                "prior_value_key": None,
                            }
                        )
                    ]
                ),
            )
            runtime.invalidate_semantics("e1", "invalidate semantics")
            with self.assertRaisesRegex(ValueError, "INVALIDATED; use reprocess_event"):
                runtime.ingest_event(raw, FakeBackend([]))
        finally:
            runtime.close()

    def test_invalidated_semantics_persist_across_restart_and_reprocess(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = str(Path(tmp) / "stance.sqlite")
            runtime = HCLV05Runtime(path=db)
            raw = event("e1", "Ari states a route.", actor="ari")
            runtime.ingest_event(
                raw,
                FakeBackend(
                    [
                        payload(
                            {
                                "subject_agent_id": "ari",
                                "issue_key": "route_assignment",
                                "signal": "AFFIRM",
                                "value_key": "RED",
                                "prior_value_key": None,
                            }
                        )
                    ]
                ),
            )
            runtime.invalidate_semantics("e1", "replace incorrect derived stance")
            runtime.close()

            reopened = HCLV05Runtime(path=db)
            self.assertEqual(reopened.store.semantic_status("e1"), "INVALIDATED")
            self.assertEqual(reopened.stance_events, ())
            result = reopened.reprocess_event(
                "e1",
                FakeBackend(
                    [
                        payload(
                            {
                                "subject_agent_id": "ari",
                                "issue_key": "route_assignment",
                                "signal": "AFFIRM",
                                "value_key": "BLUE",
                                "prior_value_key": None,
                            }
                        )
                    ]
                ),
            )
            self.assertFalse(result.duplicate)
            self.assertEqual(reopened.store.semantic_status("e1"), "COMMITTED")
            self.assertEqual(
                reopened.current_stance(
                    "ari", "route_assignment"
                ).affirmed_value_key,
                "BLUE",
            )
            history = reopened.store.invalidation_history("e1")
            self.assertEqual(len(history), 1)
            self.assertEqual(
                history[0]["prior_stance_payloads"][0]["value_key"],
                "RED",
            )
            reopened.close()

    def test_failed_reprocess_after_invalidation_does_not_restore_old_stance(self):
        runtime = HCLV05Runtime()
        try:
            raw = event("e1", "Ari states a route.", actor="ari")
            runtime.ingest_event(
                raw,
                FakeBackend(
                    [
                        payload(
                            {
                                "subject_agent_id": "ari",
                                "issue_key": "route_assignment",
                                "signal": "AFFIRM",
                                "value_key": "RED",
                                "prior_value_key": None,
                            }
                        )
                    ]
                ),
            )
            runtime.invalidate_semantics("e1", "invalidate prior interpretation")
            invalid = payload(
                {
                    "subject_agent_id": "other",
                    "issue_key": "route_assignment",
                    "signal": "AFFIRM",
                    "value_key": "BLUE",
                    "prior_value_key": None,
                }
            )
            with self.assertRaises(SemanticExtractionError):
                runtime.reprocess_event(
                    "e1",
                    FakeBackend([invalid, invalid]),
                )
            self.assertEqual(runtime.store.semantic_status("e1"), "FAILED")
            self.assertEqual(runtime.stance_events, ())
            self.assertEqual(
                runtime.current_stance(
                    "ari", "route_assignment"
                ).status,
                StanceStatus.NO_AFFIRMED_VALUE,
            )
            self.assertEqual(len(runtime.store.invalidation_history("e1")), 1)
        finally:
            runtime.close()

    def test_only_committed_semantics_can_be_invalidated(self):
        runtime = HCLV05Runtime()
        try:
            raw = event("e1", "Routine note.", actor="source")
            runtime.store.append_event(raw)
            with self.assertRaises(ValueError):
                runtime.invalidate_semantics("e1", "no committed semantics")
        finally:
            runtime.close()

    def test_store_commit_is_atomic_on_duplicate_stance_ids(self):
        store = V05Store()
        try:
            raw = event("e1", "Ari accepts Red.", actor="ari")
            store.append_event(raw)
            from hcl.v05 import StanceEvent, StanceSignal

            valid = StanceEvent(
                event_id="same",
                subject_agent_id="ari",
                issue_key="route_assignment",
                signal=StanceSignal.AFFIRM,
                value_key="RED",
                valid_time=raw.valid_time,
                system_record_time=raw.recorded_at,
                evidence_event_ids=("e1",),
            )
            with self.assertRaises(ValueError):
                store.commit_semantics(
                    "e1",
                    (valid, valid),
                    repair_count=0,
                    repair_reason=None,
                )
            self.assertIsNone(store.semantic_status("e1"))
            self.assertEqual(store.stance_events_for_source("e1"), ())
        finally:
            store.close()


if __name__ == "__main__":
    unittest.main()
