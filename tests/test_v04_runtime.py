from __future__ import annotations

import json
import unittest

from hcl.v04 import CognitionStore, EventRecord, HCLV04Runtime
from hcl.v04.schema import SchemaValidationError


T0 = "2026-01-01T10:00:00+00:00"


class FakeBackend:
    def __init__(self, *, json_outputs=None, text_outputs=None):
        self.json_outputs = list(json_outputs or [])
        self.text_outputs = list(text_outputs or [])
        self.json_calls = []
        self.text_calls = []

    def complete_json(self, messages, *, max_tokens, temperature=0.0):
        self.json_calls.append(messages)
        if not self.json_outputs:
            raise AssertionError("unexpected complete_json call")
        return self.json_outputs.pop(0)

    def complete(self, messages, *, max_tokens, temperature=0.0):
        self.text_calls.append(messages)
        if not self.text_outputs:
            raise AssertionError("unexpected complete call")
        return self.text_outputs.pop(0)


class V04RuntimeTests(unittest.TestCase):
    def test_invalid_semantic_json_does_not_mutate_derived_state(self):
        runtime = HCLV04Runtime(CognitionStore())
        try:
            runtime.append_event(
                EventRecord(
                    event_id="e1",
                    valid_time=T0,
                    raw_text="Alice receives P",
                    source_id="source",
                    actor_id="source",
                    recipient_ids=("alice",),
                )
            )
            backend = FakeBackend(json_outputs=["not-json", "still-not-json"])
            with self.assertRaises(SchemaValidationError):
                runtime.propose_patch("e1", backend)
            self.assertEqual(len(backend.json_calls), 2)
            self.assertEqual(runtime.store.state_version, 0)
            self.assertEqual(
                runtime.build_view(None, None, None, "q").relevant_assertions,
                (),
            )
        finally:
            runtime.store.close()

    def test_schema_invalid_semantic_patch_is_rejected(self):
        runtime = HCLV04Runtime(CognitionStore())
        try:
            runtime.append_event(
                EventRecord(
                    event_id="e1",
                    valid_time=T0,
                    raw_text="Alice receives P",
                    source_id="source",
                    actor_id="source",
                    recipient_ids=("alice",),
                )
            )
            payload = {
                "propositions": [],
                "assertions": [
                    {
                        "assertion_type": "NOT_A_REAL_TYPE",
                        "valid_time": T0,
                    }
                ],
            }
            backend = FakeBackend(
                json_outputs=[json.dumps(payload), json.dumps(payload)]
            )
            with self.assertRaises(SchemaValidationError):
                runtime.propose_patch("e1", backend)
            self.assertEqual(len(backend.json_calls), 2)
            self.assertEqual(runtime.store.state_version, 0)
        finally:
            runtime.store.close()

    def test_ingest_repairs_invalid_exposure_once(self):
        runtime = HCLV04Runtime(CognitionStore())
        try:
            event = EventRecord(
                event_id="e1",
                valid_time=T0,
                raw_text="Bob receives the correction; Alice does not receive it.",
                source_id="source",
                actor_id="source",
                recipient_ids=("bob",),
                metadata={"scene_fact": True},
            )
            invalid = {
                "propositions": [
                    {
                        "proposition_id": "p1",
                        "canonical_text": "the correction",
                        "source_event_ids": ["e1"],
                    }
                ],
                "assertions": [
                    {
                        "assertion_id": "bad_exp",
                        "assertion_type": "INFORMATION_EXPOSURE",
                        "subject_agent_id": "alice",
                        "proposition_id": "p1",
                        "valid_time": T0,
                        "evidence_event_ids": ["e1"],
                        "depends_on_assertion_ids": [],
                        "status": "ACTIVE",
                        "support_level": "DIRECT_SUPPORT",
                    }
                ],
            }
            repaired = {
                "propositions": [
                    {
                        "proposition_id": "p1",
                        "canonical_text": "the correction",
                        "source_event_ids": ["e1"],
                    }
                ],
                "assertions": [
                    {
                        "assertion_id": "bob_exp",
                        "assertion_type": "INFORMATION_EXPOSURE",
                        "subject_agent_id": "bob",
                        "proposition_id": "p1",
                        "valid_time": T0,
                        "evidence_event_ids": ["e1"],
                        "depends_on_assertion_ids": [],
                        "status": "ACTIVE",
                        "support_level": "DIRECT_SUPPORT",
                    }
                ],
            }
            backend = FakeBackend(
                json_outputs=[json.dumps(invalid), json.dumps(repaired)]
            )
            result = runtime.ingest_event(event, backend)
            self.assertEqual(result.semantic_repair_count, 1)
            self.assertIsNotNone(result.rejected_patch)
            self.assertIn("no evidence path", result.repair_reason)
            alice = runtime.build_view("alice", None, None, "q")
            bob = runtime.build_view("bob", None, None, "q")
            self.assertEqual(alice.relevant_assertions, ())
            self.assertEqual(len(bob.relevant_assertions), 1)
        finally:
            runtime.store.close()

    def test_belief_counterevidence_is_not_accepted_as_belief(self):
        runtime = HCLV04Runtime(CognitionStore())
        try:
            runtime.append_event(
                EventRecord(
                    event_id="e1",
                    valid_time=T0,
                    raw_text="Alice explicitly rejects P.",
                    source_id="alice",
                    actor_id="alice",
                    observer_ids=("alice",),
                )
            )
            invalid = {
                "propositions": [
                    {
                        "proposition_id": "p1",
                        "canonical_text": "P",
                        "source_event_ids": ["e1"],
                    }
                ],
                "assertions": [
                    {
                        "assertion_id": "b1",
                        "assertion_type": "BELIEF_ESTIMATE",
                        "subject_agent_id": "alice",
                        "proposition_id": "p1",
                        "valid_time": T0,
                        "evidence_event_ids": ["e1"],
                        "depends_on_assertion_ids": [],
                        "status": "ACTIVE",
                        "support_level": "COUNTEREVIDENCE",
                    }
                ],
            }
            repaired = {"propositions": invalid["propositions"], "assertions": []}
            backend = FakeBackend(
                json_outputs=[json.dumps(invalid), json.dumps(repaired)]
            )
            patch = runtime.propose_patch("e1", backend)
            self.assertEqual(len(backend.json_calls), 2)
            self.assertEqual(patch.assertions, ())
        finally:
            runtime.store.close()

    def test_pass_with_violations_is_not_accepted(self):
        runtime = HCLV04Runtime(CognitionStore())
        try:
            backend = FakeBackend(
                text_outputs=["draft", "revised"],
                json_outputs=[
                    json.dumps(
                        {
                            "status": "PASS",
                            "violations": ["STATE_GROUNDING"],
                            "reason": "bad state use",
                        }
                    ),
                    json.dumps(
                        {"status": "PASS", "violations": [], "reason": ""}
                    ),
                ],
            )
            result = runtime.respond("q", backend)
            self.assertEqual(result.answer, "revised")
            self.assertTrue(result.verified)
            self.assertEqual(result.answer_version, 2)
        finally:
            runtime.store.close()

    def test_final_check_is_bound_to_actual_returned_answer(self):
        runtime = HCLV04Runtime(CognitionStore())
        try:
            backend = FakeBackend(
                text_outputs=["draft answer", "final revision"],
                json_outputs=[
                    json.dumps(
                        {
                            "status": "REVISE",
                            "violations": ["FACT_CONTRADICTION"],
                            "reason": "revise",
                        }
                    ),
                    json.dumps(
                        {"status": "PASS", "violations": [], "reason": ""}
                    ),
                ],
            )
            result = runtime.respond("q", backend)
            self.assertEqual(result.answer, "final revision")
            self.assertTrue(result.verified)
            last_checker_user = backend.json_calls[-1][-1]["content"]
            checker_payload = json.loads(last_checker_user)
            self.assertEqual(
                checker_payload["candidate_answer"],
                "final revision",
            )
        finally:
            runtime.store.close()


if __name__ == "__main__":
    unittest.main()
