"""Provider-free tests for the v0.6 conversation access adapter."""

from __future__ import annotations

import json
import unittest

from hcl.v06 import HCLV06Runtime, extract_conversation_events


class FakeBackend:
    def __init__(self, outputs):
        self.outputs = list(outputs)
        self.calls = []

    def complete_json(self, messages, *, max_tokens, temperature=0.0):
        self.calls.append(messages)
        if not self.outputs:
            raise AssertionError("unexpected backend call")
        return self.outputs.pop(0)


class V06ConversationAdapterTests(unittest.TestCase):
    def test_leave_and_return_create_bounded_perspective(self):
        transcript = "\n".join([
            "Ana: We are all here.",
            "Bo: I have to leave now.",
            "Ana: The code is 4312.",
            "Cara: I heard the new code.",
            "Bo: I am back. What did I miss?",
            "Ana: Welcome back.",
        ])
        access = {
            "turn_access": [
                {"turn_index": 0, "heard_by_agent_ids": ["Bo", "Cara"]},
                {"turn_index": 1, "heard_by_agent_ids": ["Ana", "Cara"]},
                {"turn_index": 2, "heard_by_agent_ids": ["Cara"]},
                {"turn_index": 3, "heard_by_agent_ids": ["Ana"]},
                {"turn_index": 4, "heard_by_agent_ids": ["Ana", "Cara"]},
                {"turn_index": 5, "heard_by_agent_ids": ["Bo", "Cara"]},
            ]
        }
        result = extract_conversation_events(
            transcript,
            "demo",
            FakeBackend([json.dumps(access)]),
        )
        self.assertEqual(len(result.events), 6)

        runtime = HCLV06Runtime()
        for event in result.events:
            runtime.ingest_prestructured_event(event)

        bo = runtime.perspective_view("Bo")
        ana = runtime.perspective_view("Ana")
        self.assertNotIn(result.events[2].event_id, bo.event_ids)
        self.assertIn(result.events[2].event_id, ana.event_ids)

        second = runtime.second_order_view("Ana", "Bo")
        self.assertNotIn(result.events[2].event_id, second.event_ids)

    def test_late_joiner_does_not_receive_earlier_turns(self):
        transcript = "\n".join([
            "Ana: I love the red book.",
            "Bo: I like it too.",
            "Lisa: Hey, what are you discussing?",
            "Ana: We were talking about books.",
        ])
        access = {
            "turn_access": [
                {"turn_index": 0, "heard_by_agent_ids": ["Bo"]},
                {"turn_index": 1, "heard_by_agent_ids": ["Ana"]},
                {"turn_index": 2, "heard_by_agent_ids": ["Ana", "Bo"]},
                {"turn_index": 3, "heard_by_agent_ids": ["Bo", "Lisa"]},
            ]
        }
        result = extract_conversation_events(
            transcript,
            "late",
            FakeBackend([json.dumps(access)]),
        )
        runtime = HCLV06Runtime()
        for event in result.events:
            runtime.ingest_prestructured_event(event)
        lisa = runtime.perspective_view("Lisa")
        self.assertEqual(lisa.event_ids, (result.events[2].event_id, result.events[3].event_id))

    def test_global_context_is_question_independent_and_keeps_views_separate(self):
        transcript = "\n".join([
            "Ana: First fact.",
            "Bo: I am leaving.",
            "Ana: Private while Bo is gone.",
            "Bo: I am back.",
        ])
        access = {
            "turn_access": [
                {"turn_index": 0, "heard_by_agent_ids": ["Bo"]},
                {"turn_index": 1, "heard_by_agent_ids": ["Ana"]},
                {"turn_index": 2, "heard_by_agent_ids": []},
                {"turn_index": 3, "heard_by_agent_ids": ["Ana"]},
            ]
        }
        result = extract_conversation_events(
            transcript,
            "global",
            FakeBackend([json.dumps(access)]),
        )
        runtime = HCLV06Runtime()
        for event in result.events:
            runtime.ingest_prestructured_event(event)

        context = runtime.global_perspective_context()
        self.assertEqual(sorted(context["agents"]), ["Ana", "Bo"])
        ana_ids = context["first_order_views"]["Ana"]["event_ids"]
        bo_ids = context["first_order_views"]["Bo"]["event_ids"]
        self.assertIn(result.events[2].event_id, ana_ids)
        self.assertNotIn(result.events[2].event_id, bo_ids)
        self.assertNotIn(
            result.events[2].event_id,
            context["second_order_access_event_ids"]["Ana"]["Bo"],
        )

    def test_future_participant_is_removed_before_first_presence_evidence(self):
        transcript = "\n".join([
            "Ana: The launch code is 4312.",
            "Bo: I heard it.",
            "Harmony: Hello Ana and Bo!",
            "Ana: Welcome, Harmony.",
        ])
        # The model incorrectly leaks future participant Harmony into turn 0/1.
        access = {
            "turn_access": [
                {"turn_index": 0, "heard_by_agent_ids": ["Bo", "Harmony"]},
                {"turn_index": 1, "heard_by_agent_ids": ["Ana", "Harmony"]},
                {"turn_index": 2, "heard_by_agent_ids": ["Ana", "Bo"]},
                {"turn_index": 3, "heard_by_agent_ids": ["Bo", "Harmony"]},
            ]
        }
        result = extract_conversation_events(
            transcript,
            "future-presence",
            FakeBackend([json.dumps(access)]),
        )
        self.assertEqual(result.access_normalization_count, 2)

        runtime = HCLV06Runtime()
        for event in result.events:
            runtime.ingest_prestructured_event(event)

        harmony = runtime.perspective_view("Harmony")
        self.assertNotIn(result.events[0].event_id, harmony.event_ids)
        self.assertNotIn(result.events[1].event_id, harmony.event_ids)
        self.assertIn(result.events[2].event_id, harmony.event_ids)

    def test_direct_address_can_establish_presence_before_first_reply(self):
        transcript = "\n".join([
            "Ana: Bo, did you hear the launch code?",
            "Bo: Yes, I did.",
        ])
        access = {
            "turn_access": [
                {"turn_index": 0, "heard_by_agent_ids": ["Bo"]},
                {"turn_index": 1, "heard_by_agent_ids": ["Ana"]},
            ]
        }
        result = extract_conversation_events(
            transcript,
            "direct-address",
            FakeBackend([json.dumps(access)]),
        )
        self.assertEqual(result.access_normalization_count, 0)

        runtime = HCLV06Runtime()
        for event in result.events:
            runtime.ingest_prestructured_event(event)
        self.assertIn(result.events[0].event_id, runtime.perspective_view("Bo").event_ids)

    def test_invalid_access_map_repairs_once(self):
        transcript = "Ana: Hello.\nBo: Hi."
        invalid = json.dumps({
            "turn_access": [
                {"turn_index": 0, "heard_by_agent_ids": ["Ghost"]},
                {"turn_index": 1, "heard_by_agent_ids": ["Ana"]},
            ]
        })
        valid = json.dumps({
            "turn_access": [
                {"turn_index": 0, "heard_by_agent_ids": ["Bo"]},
                {"turn_index": 1, "heard_by_agent_ids": ["Ana"]},
            ]
        })
        backend = FakeBackend([invalid, valid])
        result = extract_conversation_events(transcript, "repair", backend)
        self.assertEqual(result.repair_count, 1)
        self.assertEqual(len(backend.calls), 2)

    def test_prestructured_event_can_later_be_semantically_enriched(self):
        transcript = "Ana: I believe the bridge is unsafe."
        access = {
            "turn_access": [
                {"turn_index": 0, "heard_by_agent_ids": []},
            ]
        }
        result = extract_conversation_events(
            transcript,
            "enrich",
            FakeBackend([json.dumps(access)]),
        )
        runtime = HCLV06Runtime()
        event = result.events[0]
        self.assertFalse(runtime.ingest_prestructured_event(event))

        semantic = json.dumps({
            "belief_evidence": [{
                "subject_agent_id": "Ana",
                "proposition_key": "bridge_unsafe",
                "signal": "AFFIRM",
                "evidence_kind": "SELF_REPORT",
                "supersedes_proposition_key": None,
                "evidence_text": "I believe the bridge is unsafe.",
            }],
            "challenge_relations": [],
        })
        enriched = runtime.ingest_event(event, FakeBackend([semantic]))
        self.assertFalse(enriched.duplicate)
        self.assertEqual(
            runtime.belief_estimate("Ana", "bridge_unsafe").status.value,
            "AFFIRMED",
        )


if __name__ == "__main__":
    unittest.main()
