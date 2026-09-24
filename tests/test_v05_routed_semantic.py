"""Provider-free tests for HCL v0.5 routed semantic extraction."""

from __future__ import annotations

import json
import unittest

from hcl.v04.model import EventRecord
from hcl.v05.semantic import (
    SemanticExtractionError,
    extract_routed_stance_events,
)
from hcl.v05.stance import StanceSignal


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
    return EventRecord(
        event_id=event_id,
        valid_time=f"2026-05-01T10:{minute:02d}:00+00:00",
        recorded_at=f"2026-05-01T10:{minute:02d}:01+00:00",
        raw_text=text,
        source_id=actor or "source",
        actor_id=actor,
        recipient_ids=tuple(recipients),
        observer_ids=tuple(observers),
    )


def routed(*, self_stances=(), revision_relations=()):
    return json.dumps(
        {
            "self_stances": list(self_stances),
            "revision_relations": list(revision_relations),
        }
    )


def self_stance(issue, signal, value):
    return {"issue_key": issue, "signal": signal, "value_key": value}


def revision(issue, new, prior):
    return {
        "issue_key": issue,
        "new_value_key": new,
        "prior_value_key": prior,
    }


class RoutedSemanticTests(unittest.TestCase):
    def test_revision_routes_to_recipient_not_sender(self):
        raw = event(
            "e1",
            "Source tells Bob: Blue replaces Red.",
            actor="source",
            recipients=("bob",),
        )
        result = extract_routed_stance_events(
            raw,
            FakeBackend(
                [
                    routed(
                        revision_relations=(
                            revision("route_assignment", "BLUE", "RED"),
                        )
                    )
                ]
            ),
        )
        self.assertEqual(len(result.stance_events), 1)
        stance = result.stance_events[0]
        self.assertEqual(stance.subject_agent_id, "bob")
        self.assertEqual(stance.signal, StanceSignal.REVISION_EXPOSURE)
        self.assertEqual(stance.value_key, "BLUE")
        self.assertEqual(stance.prior_value_key, "RED")

    def test_revision_routes_to_observer_only_world_update(self):
        raw = event(
            "e1",
            "Console records Blue replacing Red. Dana sees the console update.",
            actor="console",
            observers=("dana",),
        )
        result = extract_routed_stance_events(
            raw,
            FakeBackend(
                [
                    routed(
                        revision_relations=(
                            revision("route_assignment", "BLUE", "RED"),
                        )
                    )
                ]
            ),
        )
        self.assertEqual(
            [(x.subject_agent_id, x.signal.value) for x in result.stance_events],
            [("dana", "REVISION_EXPOSURE")],
        )

    def test_relay_revision_routes_to_relay_recipient(self):
        raw = event(
            "e1",
            "Theo tells Cyra: Nia told me Normal replaces Eco.",
            actor="theo",
            recipients=("cyra",),
        )
        result = extract_routed_stance_events(
            raw,
            FakeBackend(
                [
                    routed(
                        revision_relations=(
                            revision("sensor_mode", "NORMAL", "ECO"),
                        )
                    )
                ]
            ),
        )
        self.assertEqual(len(result.stance_events), 1)
        self.assertEqual(result.stance_events[0].subject_agent_id, "cyra")

    def test_self_report_reference_does_not_recreate_revision_exposure(self):
        raw = event(
            "e1",
            "Ben says: I received the 45-day change but I have not decided whether to accept it.",
            actor="ben",
        )
        result = extract_routed_stance_events(
            raw,
            FakeBackend(
                [
                    routed(
                        self_stances=(
                            self_stance(
                                "retention_period",
                                "UNRESOLVED",
                                "D45",
                            ),
                        ),
                        revision_relations=(
                            revision("retention_period", "D45", "D30"),
                        ),
                    )
                ]
            ),
        )
        self.assertEqual(len(result.stance_events), 1)
        stance = result.stance_events[0]
        self.assertEqual(stance.subject_agent_id, "ben")
        self.assertEqual(stance.signal, StanceSignal.UNRESOLVED)

    def test_multiple_explicit_targets_are_deduplicated(self):
        raw = event(
            "e1",
            "Source tells Bob and Dana: Blue replaces Red.",
            actor="source",
            recipients=("bob", "dana", "bob"),
            observers=("dana",),
        )
        result = extract_routed_stance_events(
            raw,
            FakeBackend(
                [
                    routed(
                        revision_relations=(
                            revision("route_assignment", "BLUE", "RED"),
                        )
                    )
                ]
            ),
        )
        self.assertEqual(
            sorted(x.subject_agent_id for x in result.stance_events),
            ["bob", "dana"],
        )

    def test_revision_relation_never_routes_to_actor_without_explicit_access(self):
        raw = event(
            "e1",
            "Source tells Bob: Blue replaces Red.",
            actor="source",
            recipients=("bob",),
        )
        result = extract_routed_stance_events(
            raw,
            FakeBackend(
                [
                    routed(
                        revision_relations=(
                            revision("route_assignment", "BLUE", "RED"),
                        )
                    )
                ]
            ),
        )
        self.assertNotIn(
            "source",
            {x.subject_agent_id for x in result.stance_events},
        )

    def test_self_stance_is_bound_to_actor_without_model_subject_choice(self):
        raw = event(
            "e1",
            "Ari says: I reject Blue.",
            actor="ari",
        )
        result = extract_routed_stance_events(
            raw,
            FakeBackend(
                [
                    routed(
                        self_stances=(
                            self_stance(
                                "route_assignment",
                                "DENY",
                                "BLUE",
                            ),
                        )
                    )
                ]
            ),
        )
        self.assertEqual(len(result.stance_events), 1)
        self.assertEqual(result.stance_events[0].subject_agent_id, "ari")
        self.assertEqual(result.stance_events[0].signal, StanceSignal.DENY)

    def test_model_cannot_smuggle_subject_into_routed_schema(self):
        raw = event(
            "e1",
            "Source tells Bob: Blue replaces Red.",
            actor="source",
            recipients=("bob",),
        )
        invalid = json.dumps(
            {
                "self_stances": [],
                "revision_relations": [
                    {
                        "subject_agent_id": "source",
                        "issue_key": "route_assignment",
                        "new_value_key": "BLUE",
                        "prior_value_key": "RED",
                    }
                ],
            }
        )
        repaired = routed(
            revision_relations=(
                revision("route_assignment", "BLUE", "RED"),
            )
        )
        backend = FakeBackend([invalid, repaired])
        result = extract_routed_stance_events(raw, backend)
        self.assertEqual(result.repair_count, 1)
        self.assertEqual(result.stance_events[0].subject_agent_id, "bob")

    def test_self_stance_requires_actor(self):
        raw = event("e1", "Anonymous note: I accept Blue.")
        invalid = routed(
            self_stances=(
                self_stance("route_assignment", "AFFIRM", "BLUE"),
            )
        )
        backend = FakeBackend([invalid, routed()])
        result = extract_routed_stance_events(raw, backend)
        self.assertEqual(result.repair_count, 1)
        self.assertEqual(result.stance_events, ())

    def test_self_stance_schema_rejects_revision_signal(self):
        raw = event("e1", "Ari says something.", actor="ari")
        invalid = routed(
            self_stances=(
                self_stance(
                    "route_assignment",
                    "REVISION_EXPOSURE",
                    "BLUE",
                ),
            )
        )
        backend = FakeBackend([invalid, routed()])
        result = extract_routed_stance_events(raw, backend)
        self.assertEqual(result.repair_count, 1)
        self.assertEqual(result.stance_events, ())

    def test_prompt_explicitly_forbids_source_assertion_as_self_stance(self):
        raw = event(
            "e1",
            "Coordinator tells Ari: Blue is current.",
            actor="coordinator",
            recipients=("ari",),
        )
        backend = FakeBackend([routed()])
        extract_routed_stance_events(raw, backend)
        system = backend.calls[0][0]["content"]
        self.assertIn("source merely telling", system)
        self.assertIn("NOT evidence of the source's own belief", system)


if __name__ == "__main__":
    unittest.main()
