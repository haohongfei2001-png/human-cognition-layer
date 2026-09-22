from __future__ import annotations

import json
from types import SimpleNamespace
import unittest

from hcl.v03.answer_loop import HCLAnswerLoop
from hcl.v03.backends import OpenAICompatibleBackend


VALID_STATE = json.dumps({
    "mode": "SIMPLE",
    "explicit_facts": ["synthetic"],
    "agents": {},
    "hypotheses": [],
    "missing_bridges": [],
    "uncertainty": {"level": "low", "reason": "direct"},
    "decision_relevant_summary": "synthetic",
})


def response(text: str):
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content=text)
            )
        ]
    )


class FakeCompletions:
    def __init__(self, outputs):
        self.outputs = list(outputs)
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return response(self.outputs.pop(0))


class FakeClient:
    def __init__(self, outputs):
        self.chat = SimpleNamespace(completions=FakeCompletions(outputs))


def backend_with(outputs):
    backend = object.__new__(OpenAICompatibleBackend)
    backend.client = FakeClient(outputs)
    backend.model = "deepseek-flash"
    backend.seed = 42
    return backend


class StructuredBackend:
    def __init__(self, outputs):
        self.outputs = list(outputs)
        self.json_calls = 0
        self.text_calls = 0

    def complete_json(self, messages, *, max_tokens, temperature=0.0):
        self.json_calls += 1
        return self.outputs.pop(0)

    def complete(self, messages, *, max_tokens, temperature=0.0):
        self.text_calls += 1
        raise AssertionError("state generation must prefer complete_json")


class LegacyBackend:
    def __init__(self, output):
        self.output = output
        self.calls = 0

    def complete(self, messages, *, max_tokens, temperature=0.0):
        self.calls += 1
        return self.output


class StateJSONReliabilityRepairTests(unittest.TestCase):
    def test_complete_json_sends_json_object_response_format(self):
        backend = backend_with([VALID_STATE])
        got = backend.complete_json(
            [{"role": "system", "content": "Return JSON only."}],
            max_tokens=8192,
            temperature=0.0,
        )
        self.assertEqual(got, VALID_STATE)
        call = backend.client.chat.completions.calls[0]
        self.assertEqual(call["response_format"], {"type": "json_object"})
        self.assertEqual(call["model"], "deepseek-flash")
        self.assertEqual(call["seed"], 42)

    def test_ordinary_complete_does_not_enable_json_mode(self):
        backend = backend_with(["plain text"])
        got = backend.complete(
            [{"role": "user", "content": "hello"}],
            max_tokens=10,
            temperature=0.0,
        )
        self.assertEqual(got, "plain text")
        call = backend.client.chat.completions.calls[0]
        self.assertNotIn("response_format", call)

    def test_json_mode_preserves_bounded_nonempty_retry(self):
        backend = backend_with(["", "   ", VALID_STATE])
        got = backend.complete_json(
            [{"role": "system", "content": "Return JSON only."}],
            max_tokens=8192,
        )
        self.assertEqual(got, VALID_STATE)
        self.assertEqual(len(backend.client.chat.completions.calls), 3)
        self.assertTrue(
            all(
                call["response_format"] == {"type": "json_object"}
                for call in backend.client.chat.completions.calls
            )
        )

    def test_build_state_prefers_structured_capability(self):
        backend = StructuredBackend([VALID_STATE])
        state = HCLAnswerLoop(backend).build_state("synthetic input")
        self.assertEqual(state["mode"], "SIMPLE")
        self.assertEqual(backend.json_calls, 1)
        self.assertEqual(backend.text_calls, 0)

    def test_build_state_keeps_legacy_backend_compatibility(self):
        backend = LegacyBackend(VALID_STATE)
        state = HCLAnswerLoop(backend).build_state("synthetic input")
        self.assertEqual(state["mode"], "SIMPLE")
        self.assertEqual(backend.calls, 1)

    def test_hcl_level_retry_budget_remains_three(self):
        backend = StructuredBackend(["not json", "still not json", "no object"])
        with self.assertRaisesRegex(RuntimeError, "no valid JSON after 3 attempts"):
            HCLAnswerLoop(backend).build_state("synthetic input")
        self.assertEqual(backend.json_calls, 3)
        self.assertEqual(backend.text_calls, 0)


if __name__ == "__main__":
    unittest.main()
