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
            backend = FakeBackend(json_outputs=["not-json"])
            with self.assertRaises(SchemaValidationError):
                runtime.propose_patch("e1", backend)
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
            backend = FakeBackend(json_outputs=[json.dumps(payload)])
            with self.assertRaises(SchemaValidationError):
                runtime.propose_patch("e1", backend)
            self.assertEqual(runtime.store.state_version, 0)
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
