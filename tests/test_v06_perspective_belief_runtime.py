"""Provider-free correctness tests for HCL v0.6 minimal cognition runtime."""

from __future__ import annotations

import json
import unittest

from hcl.v04.model import EventRecord
from hcl.v06 import (
    BeliefStatus,
    HCLV06Runtime,
    SYSTEM_VIEWER,
    V06SemanticExtractionError,
)


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
    metadata=None,
):
    return EventRecord(
        event_id=event_id,
        valid_time=f"2026-09-25T10:{minute:02d}:00+00:00",
        recorded_at=f"2026-09-25T10:{minute:02d}:01+00:00",
        raw_text=text,
        source_id=actor or "narrator",
        actor_id=actor,
        recipient_ids=tuple(recipients),
        observer_ids=tuple(observers),
        metadata=dict(metadata or {}),
    )


def payload(evidence=(), challenges=()):
    return json.dumps(
        {
            "belief_evidence": list(evidence),
            "challenge_relations": list(challenges),
        }
    )


def claim(
    subject,
    proposition,
    signal,
    kind,
    *,
    supersedes=None,
    text=None,
):
    return {
        "subject_agent_id": subject,
        "proposition_key": proposition,
        "signal": signal,
        "evidence_kind": kind,
        "supersedes_proposition_key": supersedes,
        "evidence_text": text,
    }


class V06MinimalPerspectiveBeliefTests(unittest.TestCase):
    def test_reader_only_narrator_evidence_does_not_leak_to_character(self):
        runtime = HCLV06Runtime()
        runtime.ingest_event(
            event(
                "n1",
                "Narrator: Bo privately believes the bridge is unsafe.",
                metadata={"reader_only": True, "narrator": True},
            ),
            FakeBackend(
                [
                    payload(
                        [
                            claim(
                                "bo",
                                "bridge_unsafe",
                                "AFFIRM",
                                "NARRATOR_ASSERTION",
                            )
                        ]
                    )
                ]
            ),
        )

        self.assertEqual(runtime.perspective_view("bo").event_ids, ())
        reader = runtime.belief_estimate(
            "bo", "bridge_unsafe", viewer_agent_id=SYSTEM_VIEWER
        )
        bo_view = runtime.belief_estimate(
            "bo", "bridge_unsafe", viewer_agent_id="bo"
        )
        self.assertEqual(reader.status, BeliefStatus.AFFIRMED)
        self.assertEqual(bo_view.status, BeliefStatus.SYSTEM_INSUFFICIENT)

    def test_first_order_view_respects_private_recipient_boundary(self):
        runtime = HCLV06Runtime()
        runtime.ingest_event(
            event(
                "e1",
                "Mira tells Ana the meeting moved to room B.",
                actor="mira",
                recipients=("ana",),
            ),
            FakeBackend([payload()]),
        )
        self.assertEqual(runtime.perspective_view("ana").event_ids, ("e1",))
        self.assertEqual(runtime.perspective_view("bo").event_ids, ())

    def test_second_order_requires_viewer_to_know_target_had_access(self):
        runtime = HCLV06Runtime()
        runtime.ingest_event(
            event(
                "e1",
                "Mira tells both Ana and Bo the code changed.",
                actor="mira",
                recipients=("ana", "bo"),
            ),
            FakeBackend([payload()]),
        )
        runtime.ingest_event(
            event(
                "e2",
                "Mira privately tells Bo a second detail.",
                actor="mira",
                recipients=("bo",),
                minute=1,
            ),
            FakeBackend([payload()]),
        )

        view = runtime.second_order_view("ana", "bo")
        self.assertEqual(view.event_ids, ("e1",))
        self.assertNotIn("e2", view.event_ids)

    def test_challenge_exposure_does_not_erase_prior_belief(self):
        runtime = HCLV06Runtime()
        runtime.ingest_event(
            event(
                "b1",
                "Bo says: I believe route red is correct.",
                actor="bo",
                recipients=("ana",),
            ),
            FakeBackend(
                [
                    payload(
                        [
                            claim(
                                "bo",
                                "route_red",
                                "AFFIRM",
                                "SELF_REPORT",
                            )
                        ]
                    )
                ]
            ),
        )
        runtime.ingest_event(
            event(
                "b2",
                "Mira tells Bo and Ana that new evidence contradicts route red.",
                actor="mira",
                recipients=("bo", "ana"),
                minute=1,
            ),
            FakeBackend(
                [
                    payload(
                        challenges=[
                            {
                                "challenged_proposition_key": "route_red",
                                "alternative_proposition_key": "route_blue",
                            }
                        ]
                    )
                ]
            ),
        )

        state = runtime.belief_estimate("bo", "route_red")
        self.assertEqual(state.status, BeliefStatus.AFFIRMED)
        self.assertEqual(len(state.unresolved_challenge_evidence_ids), 1)

    def test_explicit_revision_supersedes_prior_belief(self):
        runtime = HCLV06Runtime()
        runtime.ingest_event(
            event("b1", "Bo says I believe red.", actor="bo"),
            FakeBackend(
                [payload([claim("bo", "route_red", "AFFIRM", "SELF_REPORT")])]
            ),
        )
        runtime.ingest_event(
            event(
                "b2",
                "Bo says I checked the evidence and now believe blue instead of red.",
                actor="bo",
                minute=1,
            ),
            FakeBackend(
                [
                    payload(
                        [
                            claim(
                                "bo",
                                "route_blue",
                                "AFFIRM",
                                "SELF_REPORT",
                                supersedes="route_red",
                            )
                        ]
                    )
                ]
            ),
        )

        old = runtime.belief_estimate("bo", "route_red")
        new = runtime.belief_estimate("bo", "route_blue")
        self.assertEqual(old.status, BeliefStatus.SUPERSEDED)
        self.assertEqual(old.superseded_by_proposition_key, "route_blue")
        self.assertEqual(new.status, BeliefStatus.AFFIRMED)

    def test_system_insufficient_is_distinct_from_character_uncertain(self):
        runtime = HCLV06Runtime()
        runtime.ingest_event(
            event(
                "r1",
                "Ana tells Cara that Bo believes the bridge is unsafe.",
                actor="ana",
                recipients=("cara",),
            ),
            FakeBackend(
                [
                    payload(
                        [
                            claim(
                                "bo",
                                "bridge_unsafe",
                                "AFFIRM",
                                "THIRD_PARTY_REPORT",
                            )
                        ]
                    )
                ]
            ),
        )
        indirect = runtime.belief_estimate("bo", "bridge_unsafe")
        self.assertEqual(indirect.status, BeliefStatus.SYSTEM_INSUFFICIENT)
        self.assertEqual(len(indirect.indirect_support_evidence_ids), 1)

        runtime.ingest_event(
            event(
                "r2",
                "Bo says: I am genuinely unsure whether the bridge is unsafe.",
                actor="bo",
                minute=1,
            ),
            FakeBackend(
                [
                    payload(
                        [
                            claim(
                                "bo",
                                "bridge_unsafe",
                                "UNCERTAIN",
                                "SELF_REPORT",
                            )
                        ]
                    )
                ]
            ),
        )
        explicit = runtime.belief_estimate("bo", "bridge_unsafe")
        self.assertEqual(explicit.status, BeliefStatus.CHARACTER_UNCERTAIN)

    def test_observed_action_is_indirect_not_private_belief_truth(self):
        runtime = HCLV06Runtime()
        runtime.ingest_event(
            event(
                "a1",
                "Bo avoids crossing the bridge.",
                actor="bo",
                observers=("ana",),
            ),
            FakeBackend(
                [
                    payload(
                        [
                            claim(
                                "bo",
                                "bridge_unsafe",
                                "AFFIRM",
                                "OBSERVED_ACTION",
                            )
                        ]
                    )
                ]
            ),
        )
        state = runtime.belief_estimate("bo", "bridge_unsafe")
        self.assertEqual(state.status, BeliefStatus.SYSTEM_INSUFFICIENT)
        self.assertEqual(len(state.indirect_support_evidence_ids), 1)

    def test_answer_context_keeps_second_order_information_and_belief_evidence_separate(self):
        runtime = HCLV06Runtime()
        runtime.ingest_event(
            event(
                "e1",
                "Mira tells Ana and Bo that the key is in drawer two.",
                actor="mira",
                recipients=("ana", "bo"),
            ),
            FakeBackend([payload()]),
        )
        runtime.ingest_event(
            event(
                "e2",
                "Bo privately tells Cara: I believe the key is in drawer two.",
                actor="bo",
                recipients=("cara",),
                minute=1,
            ),
            FakeBackend(
                [
                    payload(
                        [
                            claim(
                                "bo",
                                "key_in_drawer_two",
                                "AFFIRM",
                                "SELF_REPORT",
                            )
                        ]
                    )
                ]
            ),
        )

        context = runtime.answer_context("bo", observer_agent_id="ana")
        self.assertEqual(context.perspective_order, 2)
        self.assertEqual(context.target_information_view.event_ids, ("e1",))
        estimates = {x.proposition_key: x for x in context.belief_estimates}
        self.assertEqual(
            estimates["key_in_drawer_two"].status,
            BeliefStatus.SYSTEM_INSUFFICIENT,
        )

    def test_answer_messages_encode_core_semantic_guardrails(self):
        runtime = HCLV06Runtime()
        runtime.ingest_event(
            event(
                "e1",
                "Ana receives a private note.",
                actor="source",
                recipients=("ana",),
            ),
            FakeBackend([payload()]),
        )
        messages = runtime.answer_messages(
            "What can Ana conclude?",
            target_agent_id="ana",
        )
        self.assertEqual(len(messages), 2)
        self.assertIn("Information exposure does not imply belief acceptance", messages[0]["content"])
        self.assertIn("SYSTEM_INSUFFICIENT", messages[0]["content"])
        body = json.loads(messages[1]["content"])
        self.assertEqual(
            body["hcl_perspective_context"]["target_information_view"]["event_ids"],
            ["e1"],
        )

    def test_semantic_source_kind_validation_fails_closed(self):
        runtime = HCLV06Runtime()
        raw = event(
            "bad",
            "A non-narrator source claims Bo believes X.",
            actor="ana",
        )
        invalid = payload(
            [claim("bo", "x", "AFFIRM", "NARRATOR_ASSERTION")]
        )
        with self.assertRaises(V06SemanticExtractionError):
            runtime.ingest_event(raw, FakeBackend([invalid, invalid]))
        self.assertEqual(runtime.events, (raw,))
        self.assertIn("bad", runtime.semantic_failures)

    def test_duplicate_is_idempotent_without_second_model_call(self):
        runtime = HCLV06Runtime()
        raw = event("e1", "Routine exchange.", actor="ana")
        backend = FakeBackend([payload()])
        first = runtime.ingest_event(raw, backend)
        second = runtime.ingest_event(raw, backend)
        self.assertFalse(first.duplicate)
        self.assertTrue(second.duplicate)
        self.assertEqual(len(backend.calls), 1)


if __name__ == "__main__":
    unittest.main()
