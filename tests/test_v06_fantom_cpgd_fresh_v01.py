"""Provider-free firewall and generic-state checks for the frozen fresh pilot."""

from __future__ import annotations

import json
from types import SimpleNamespace
import unittest

from hcl.v04.model import EventRecord
from hcl.v06.generic_state import GenericStructuredState
from scripts.prepare_v06_fantom_cpgd_fresh_v01 import excluded_conversations, sha
from scripts.run_v06_fantom_cpgd_fresh_v01 import COST_CAP_USD, OneCallDeepSeekBackend, _hard_cap_is_safe, evaluate_one


class FakeBackend:
    def __init__(self, *, text="no", json_response=None, log=None, name=""):
        self.text = text
        self.json_response = json_response
        self.log = log if log is not None else []
        self.name = name

    def complete(self, messages, *, max_tokens, temperature=0.0):
        self.log.append((self.name, "answer", messages, max_tokens, temperature))
        return self.text

    def complete_json(self, messages, *, max_tokens, temperature=0.0):
        self.log.append((self.name, "access", messages, max_tokens, temperature))
        return self.json_response


class FreshPilotTests(unittest.TestCase):
    def test_exclusions_cover_all_consumed_conversations(self):
        historical, development = excluded_conversations()
        self.assertEqual(len(historical), 80)
        self.assertEqual(len(development), 8)
        self.assertFalse(historical & development)
        self.assertEqual(development, {"119", "197", "240", "7", "220", "189", "208", "36"})

    def test_generic_state_retains_every_event_and_provenance(self):
        events = [
            EventRecord("one", "2026-01-01T00:00:00+00:00", "Mira spoke.", "source", actor_id="Mira", observer_ids=("Noah",)),
            EventRecord("two", "2026-01-01T00:00:01+00:00", "Noah replied.", "source", actor_id="Noah", observer_ids=("Mira",)),
        ]
        state = GenericStructuredState.from_events(events).as_dict()
        self.assertEqual(state["event_count"], 2)
        self.assertEqual([row["event_id"] for row in state["timeline"]], ["one", "two"])
        self.assertEqual(state["timeline"][0]["heard_by_agent_ids"], ["Noah"])
        self.assertEqual(state["timeline"][0]["provenance"], "DIRECT_UTTERANCE")
        with self.assertRaises(ValueError):
            GenericStructuredState.from_events(events + [events[0]])

    def test_question_and_gold_do_not_enter_state_construction(self):
        context = "Mira: I will return tomorrow.\nNoah: I heard you."
        question = "UNIQUE_SECRET_QUESTION: Can Mira tell?"
        record = {
            "set_id": "999-0-0", "family": "answerability_binary", "context": context,
            "question": question, "target": "UNIQUE_SECRET_TARGET", "correct_answer": "no",
        }
        manifest = {
            "conversation_id": "999", "set_id": "999-0-0",
            "family": "answerability_binary", "stratum": "answerability_full_inaccessible_binary",
            "question_id": "test-question", "context_sha256": sha(context), "question_sha256": sha(question),
        }
        log = []
        access = json.dumps({"turn_access": [
            {"turn_index": 0, "heard_by_agent_ids": ["Noah"]},
            {"turn_index": 1, "heard_by_agent_ids": ["Mira"]},
        ]})
        backends = {name: FakeBackend(log=log, name=name) for name in ("C", "P", "G", "D")}
        backends["ACCESS"] = FakeBackend(json_response=access, log=log, name="ACCESS")
        result = evaluate_one(manifest, record, backends)
        self.assertEqual(result["adapter"]["event_count"], 2)
        self.assertEqual([entry[0] for entry in log], ["ACCESS", "C", "P", "G", "D"])
        adapter_input = json.dumps(log[0][2])
        self.assertNotIn("UNIQUE_SECRET_QUESTION", adapter_input)
        self.assertNotIn("UNIQUE_SECRET_TARGET", adapter_input)
        self.assertTrue(all(result["arms"][arm]["correct"] for arm in ("C", "P", "G", "D")))

    def test_cost_caps_bound_all_components(self):
        self.assertTrue(_hard_cap_is_safe())
        self.assertEqual(COST_CAP_USD, 3.50)

    def test_text_and_json_transport_disable_thinking_with_one_request(self):
        calls = []
        def create(**kwargs):
            calls.append(kwargs)
            return SimpleNamespace(
                model="same-model",
                choices=[SimpleNamespace(message=SimpleNamespace(content="ok"))],
            )
        backend = OneCallDeepSeekBackend.__new__(OneCallDeepSeekBackend)
        backend.client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
        backend.calls = backend.input_chars = backend.output_chars = 0
        backend.provider_wall_seconds = 0.0
        backend.response_models = set()
        messages = [{"role": "user", "content": "hello"}]
        self.assertEqual(backend.complete(messages, max_tokens=64), "ok")
        self.assertEqual(backend.complete_json(messages, max_tokens=64), "ok")
        self.assertEqual(len(calls), 2)
        self.assertEqual(backend.metrics()["calls"], 2)
        self.assertTrue(all(call["extra_body"] == {"thinking": {"type": "disabled"}} for call in calls))
        self.assertEqual(calls[1]["response_format"], {"type": "json_object"})


if __name__ == "__main__":
    unittest.main()
