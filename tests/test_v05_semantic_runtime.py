"""Provider-free semantic/runtime tests for HCL v0.5."""

from __future__ import annotations

import json
import unittest

from hcl.v04.model import EventRecord
from hcl.v05 import StanceSignal, StanceStatus
from hcl.v05.runtime import HCLV05Runtime
from hcl.v05.semantic import (
    SemanticExtractionError,
    extract_stance_events,
)


T0 = "2026-02-01T10:00:00+00:00"


class FakeBackend:
    def __init__(self, outputs):
        self.outputs = list(outputs)
        self.calls = []

    def complete_json(self, messages, *, max_tokens, temperature=0.0):
        self.calls.append(messages)
        if not self.outputs:
            raise AssertionError("unexpected backend call")
        return self.outputs.pop(0)


def event(
    event_id,
    text,
    *,
    actor=None,
    recipients=(),
    observers=(),
    minute=0,
):
    valid = f"2026-02-01T10:{minute:02d}:00+00:00"
    recorded = f"2026-02-01T10:{minute:02d}:01+00:00"
    return EventRecord(
        event_id=event_id,
        valid_time=valid,
        recorded_at=recorded,
        raw_text=text,
        source_id=actor or "source",
        actor_id=actor,
        recipient_ids=tuple(recipients),
        observer_ids=tuple(observers),
    )


def payload(*rows):
    return json.dumps({"stance_events": list(rows)})


class V05SemanticIntegrationTests(unittest.TestCase):
    def test_explicit_self_acceptance_extracts_affirm(self):
        raw = event(
            "e1",
            "Ari says: I accept Blue as the route.",
            actor="ari",
        )
        backend = FakeBackend(
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
        )
        result = extract_stance_events(raw, backend)
        self.assertEqual(result.repair_count, 0)
        self.assertEqual(len(result.stance_events), 1)
        self.assertEqual(result.stance_events[0].signal, StanceSignal.AFFIRM)
        self.assertEqual(result.stance_events[0].value_key, "BLUE")

    def test_revision_exposure_requires_real_access_path(self):
        raw = event(
            "e1",
            "Source tells Bob only: Blue replaces Red.",
            actor="source",
            recipients=("bob",),
        )
        invalid = payload(
            {
                "subject_agent_id": "alice",
                "issue_key": "route_assignment",
                "signal": "REVISION_EXPOSURE",
                "value_key": "BLUE",
                "prior_value_key": "RED",
            }
        )
        repaired = payload()
        backend = FakeBackend([invalid, repaired])
        result = extract_stance_events(raw, backend)
        self.assertEqual(result.repair_count, 1)
        self.assertEqual(result.stance_events, ())
        self.assertIn("information path", result.repair_reason)

    def test_other_person_stance_claim_cannot_become_target_belief(self):
        raw = event(
            "e1",
            "Bob says Alice accepts Blue.",
            actor="bob",
        )
        invalid = payload(
            {
                "subject_agent_id": "alice",
                "issue_key": "route_assignment",
                "signal": "AFFIRM",
                "value_key": "BLUE",
                "prior_value_key": None,
            }
        )
        backend = FakeBackend([invalid, payload()])
        result = extract_stance_events(raw, backend)
        self.assertEqual(result.stance_events, ())
        self.assertEqual(result.repair_count, 1)

    def test_known_catalog_is_supplied_to_backend(self):
        runtime = HCLV05Runtime()
        first = FakeBackend(
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
        )
        runtime.ingest_event(
            event("e1", "Ari accepts Red.", actor="ari"),
            first,
        )

        second = FakeBackend([payload()])
        runtime.ingest_event(
            event("e2", "Unrelated note.", actor="source", minute=1),
            second,
        )
        prompt = json.loads(second.calls[0][-1]["content"])
        self.assertEqual(
            prompt["known_issue_value_catalog"],
            {"route_assignment": ["RED"]},
        )

    def test_runtime_end_to_end_keeps_receipt_separate_from_stance(self):
        runtime = HCLV05Runtime()
        sequence = [
            (
                event("e1", "Ari accepts Red.", actor="ari", minute=1),
                payload(
                    {
                        "subject_agent_id": "ari",
                        "issue_key": "route_assignment",
                        "signal": "AFFIRM",
                        "value_key": "RED",
                        "prior_value_key": None,
                    }
                ),
            ),
            (
                event(
                    "e2",
                    "Source tells Ari: Blue replaces Red.",
                    actor="source",
                    recipients=("ari",),
                    minute=2,
                ),
                payload(
                    {
                        "subject_agent_id": "ari",
                        "issue_key": "route_assignment",
                        "signal": "REVISION_EXPOSURE",
                        "value_key": "BLUE",
                        "prior_value_key": "RED",
                    }
                ),
            ),
            (
                event(
                    "e3",
                    "Ari says: I have not decided whether to accept Blue.",
                    actor="ari",
                    minute=3,
                ),
                payload(
                    {
                        "subject_agent_id": "ari",
                        "issue_key": "route_assignment",
                        "signal": "UNRESOLVED",
                        "value_key": "BLUE",
                        "prior_value_key": None,
                    }
                ),
            ),
        ]
        for raw, semantic in sequence:
            runtime.ingest_event(raw, FakeBackend([semantic]))

        pending = runtime.current_stance("ari", "route_assignment")
        self.assertEqual(pending.status, StanceStatus.UNRESOLVED)
        self.assertEqual(pending.pending_revision_value_key, "BLUE")
        self.assertEqual(pending.suspended_value_key, "RED")

        runtime.ingest_event(
            event(
                "e4",
                "Ari says: I verified it and accept Blue.",
                actor="ari",
                minute=4,
            ),
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
        final = runtime.current_stance("ari", "route_assignment")
        self.assertEqual(final.status, StanceStatus.AFFIRMED)
        self.assertEqual(final.affirmed_value_key, "BLUE")

    def test_duplicate_event_is_idempotent_without_second_model_call(self):
        runtime = HCLV05Runtime()
        raw = event("e1", "Ari accepts Red.", actor="ari")
        backend = FakeBackend(
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
        )
        first = runtime.ingest_event(raw, backend)
        second = runtime.ingest_event(raw, backend)
        self.assertFalse(first.duplicate)
        self.assertTrue(second.duplicate)
        self.assertEqual(len(backend.calls), 1)

    def test_changed_duplicate_event_fails_closed(self):
        runtime = HCLV05Runtime()
        first = event("e1", "Ari accepts Red.", actor="ari")
        runtime.ingest_event(first, FakeBackend([payload()]))
        changed = event("e1", "Ari accepts Blue.", actor="ari")
        with self.assertRaises(ValueError):
            runtime.ingest_event(changed, FakeBackend([]))

    def test_repeated_invalid_extraction_stays_strict(self):
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
        backend = FakeBackend([invalid, invalid])
        with self.assertRaises(SemanticExtractionError):
            extract_stance_events(raw, backend)
        self.assertEqual(len(backend.calls), 2)


if __name__ == "__main__":
    unittest.main()
