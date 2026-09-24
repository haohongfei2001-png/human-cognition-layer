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
    def test_answer_prompt_does_not_treat_exposure_as_belief_revision(self):
        from hcl.v04.runtime import ANSWER_SYSTEM
        self.assertIn(
            "SOURCE_ASSERTION or\nINFORMATION_EXPOSURE alone does not supersede",
            ANSWER_SYSTEM,
        )
        self.assertIn(
            "supported BELIEF_ESTIMATE is the current best estimate",
            ANSWER_SYSTEM,
        )

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
                        "assertion_id": "scene",
                        "assertion_type": "SCENE_FACT",
                        "subject_agent_id": None,
                        "proposition_id": "p1",
                        "valid_time": T0,
                        "evidence_event_ids": ["e1"],
                        "depends_on_assertion_ids": [],
                        "status": "ACTIVE",
                        "support_level": "DIRECT_SUPPORT",
                        "belief_stance": None,
                    },
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
                        "belief_stance": None,
                    },
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
                        "belief_stance": None,
                    }
                ],
            }
            repaired = {
                "propositions": invalid["propositions"],
                "assertions": [],
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
            bob_rows = bob.relevant_assertions
            self.assertTrue(
                any(
                    x["assertion_type"] == "SCENE_FACT"
                    for x in bob_rows
                )
            )
            self.assertTrue(
                any(
                    x["assertion_type"] == "INFORMATION_EXPOSURE"
                    and x["subject_agent_id"] == "bob"
                    for x in bob_rows
                )
            )
            system_rows = runtime.build_view(
                None, None, None, "q"
            ).relevant_assertions
            self.assertTrue(
                any(x["assertion_type"] == "SCENE_FACT" for x in system_rows)
            )
            self.assertTrue(
                any(
                    x["assertion_type"] == "INFORMATION_EXPOSURE"
                    and x["subject_agent_id"] == "bob"
                    for x in system_rows
                )
            )
            self.assertFalse(
                any(
                    x["assertion_type"] == "INFORMATION_EXPOSURE"
                    and x["subject_agent_id"] == "alice"
                    for x in system_rows
                )
            )
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
                        "belief_stance": "AFFIRM",
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

    def test_repeated_invalid_belief_repair_fails_closed_without_crashing_ingest(self):
        runtime = HCLV04Runtime(CognitionStore())
        try:
            event = EventRecord(
                event_id="e1",
                valid_time=T0,
                raw_text="Alice explicitly rejects P.",
                source_id="alice",
                actor_id="alice",
                observer_ids=("alice",),
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
                        "assertion_id": "bad_belief",
                        "assertion_type": "BELIEF_ESTIMATE",
                        "subject_agent_id": "alice",
                        "proposition_id": "p1",
                        "valid_time": T0,
                        "evidence_event_ids": ["e1"],
                        "depends_on_assertion_ids": [],
                        "status": "ACTIVE",
                        "support_level": "COUNTEREVIDENCE",
                        "belief_stance": "AFFIRM",
                    }
                ],
            }
            backend = FakeBackend(
                json_outputs=[json.dumps(invalid), json.dumps(invalid)]
            )
            result = runtime.ingest_event(event, backend)

            self.assertEqual(len(backend.json_calls), 2)
            self.assertEqual(result.semantic_repair_count, 2)
            self.assertIn("deterministic fail-closed salvage", result.repair_reason)
            self.assertIn("COUNTEREVIDENCE", result.repair_reason)
            self.assertEqual(result.committed_patch.assertions, ())
            self.assertEqual(runtime.store.state_version, 1)
            self.assertEqual(
                runtime.build_view(None, None, None, "q").relevant_assertions,
                (),
            )
            self.assertEqual(runtime.store.get_event("e1").raw_text, event.raw_text)
        finally:
            runtime.store.close()

    def test_explicit_deny_belief_stance_is_preserved(self):
        runtime = HCLV04Runtime(CognitionStore())
        try:
            runtime.append_event(
                EventRecord(
                    event_id="e1",
                    valid_time=T0,
                    raw_text="Alice says she thinks P is wrong.",
                    source_id="alice",
                    actor_id="alice",
                    observer_ids=("alice",),
                )
            )
            payload = {
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
                        "support_level": "DIRECT_SUPPORT",
                        "belief_stance": "DENY",
                    }
                ],
            }
            backend = FakeBackend(json_outputs=[json.dumps(payload)])
            patch = runtime.propose_patch("e1", backend)
            self.assertEqual(patch.assertions[0].belief_stance.value, "DENY")
        finally:
            runtime.store.close()

    def test_semantic_record_time_defaults_to_event_record_time(self):
        runtime = HCLV04Runtime(CognitionStore())
        try:
            recorded_at = "2026-01-01T10:01:00+00:00"
            runtime.append_event(
                EventRecord(
                    event_id="e1",
                    valid_time=T0,
                    recorded_at=recorded_at,
                    raw_text="Alice says she believes P.",
                    source_id="alice",
                    actor_id="alice",
                    observer_ids=("alice",),
                )
            )
            payload = {
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
                        "support_level": "DIRECT_SUPPORT",
                        "belief_stance": "AFFIRM",
                    }
                ],
            }
            backend = FakeBackend(json_outputs=[json.dumps(payload)])
            patch = runtime.propose_patch("e1", backend)
            self.assertEqual(
                patch.assertions[0].system_record_time,
                recorded_at,
            )
        finally:
            runtime.store.close()

    def test_model_ids_are_aliases_not_storage_identity(self):
        runtime = HCLV04Runtime(CognitionStore())
        try:
            e1 = EventRecord(
                event_id="e1",
                valid_time=T0,
                recorded_at="2026-01-01T10:01:00+00:00",
                raw_text="Alice says P.",
                source_id="alice",
                actor_id="alice",
                observer_ids=("alice",),
            )
            e2 = EventRecord(
                event_id="e2",
                valid_time="2026-01-01T11:00:00+00:00",
                recorded_at="2026-01-01T11:01:00+00:00",
                raw_text="Alice repeats P.",
                source_id="alice",
                actor_id="alice",
                observer_ids=("alice",),
            )
            runtime.append_event(e1)
            runtime.append_event(e2)

            def payload(valid_time):
                return {
                    "propositions": [
                        {
                            "proposition_id": "model_prop",
                            "canonical_text": "P",
                            "source_event_ids": [],
                        }
                    ],
                    "assertions": [
                        {
                            "assertion_id": "same",
                            "assertion_type": "BELIEF_ESTIMATE",
                            "subject_agent_id": "alice",
                            "proposition_id": "model_prop",
                            "valid_time": valid_time,
                            "evidence_event_ids": [],
                            "depends_on_assertion_ids": [],
                            "status": "ACTIVE",
                            "support_level": "DIRECT_SUPPORT",
                            "belief_stance": "AFFIRM",
                        }
                    ],
                }

            b1 = FakeBackend(json_outputs=[json.dumps(payload(T0))])
            b2 = FakeBackend(
                json_outputs=[
                    json.dumps(payload("2026-01-01T11:00:00+00:00"))
                ]
            )
            p1 = runtime.propose_patch("e1", b1)
            p2 = runtime.propose_patch("e2", b2)

            self.assertNotEqual(
                p1.assertions[0].assertion_id,
                p2.assertions[0].assertion_id,
            )
            self.assertEqual(
                p1.propositions[0].proposition_id,
                p2.propositions[0].proposition_id,
            )
            self.assertNotEqual(p1.assertions[0].assertion_id, "same")
            self.assertNotEqual(p1.propositions[0].proposition_id, "model_prop")
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
