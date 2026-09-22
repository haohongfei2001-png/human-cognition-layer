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
        choices=[SimpleNamespace(message=SimpleNamespace(content=text))]
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

    def complete_json(self, messages, *, max_tokens, temperature=0.0):
        self.json_calls += 1
        return self.outputs.pop(0)

    def complete(self, messages, *, max_tokens, temperature=0.0):
        raise AssertionError("state generation must prefer complete_json")


class StateJSONReliabilityRepairV02Tests(unittest.TestCase):
    def test_state_json_disables_thinking_and_keeps_json_mode(self):
        backend = backend_with([VALID_STATE])
        got = backend.complete_json(
            [{"role": "system", "content": "Return JSON only."}],
            max_tokens=8192,
            temperature=0.0,
        )
        self.assertEqual(got, VALID_STATE)
        call = backend.client.chat.completions.calls[0]
        self.assertEqual(call["response_format"], {"type": "json_object"})
        self.assertEqual(
            call["extra_body"],
            {"thinking": {"type": "disabled"}},
        )
        self.assertEqual(call["max_tokens"], 8192)
        self.assertEqual(call["model"], "deepseek-flash")
        self.assertEqual(call["seed"], 42)

    def test_ordinary_complete_does_not_get_state_only_overrides(self):
        backend = backend_with(["plain text"])
        got = backend.complete(
            [{"role": "user", "content": "hello"}],
            max_tokens=4096,
            temperature=0.0,
        )
        self.assertEqual(got, "plain text")
        call = backend.client.chat.completions.calls[0]
        self.assertNotIn("response_format", call)
        self.assertNotIn("extra_body", call)

    def test_state_json_empty_retry_preserves_thinking_disabled(self):
        backend = backend_with(["", "   ", VALID_STATE])
        got = backend.complete_json(
            [{"role": "system", "content": "Return JSON only."}],
            max_tokens=8192,
        )
        self.assertEqual(got, VALID_STATE)
        self.assertEqual(len(backend.client.chat.completions.calls), 3)
        for call in backend.client.chat.completions.calls:
            self.assertEqual(call["response_format"], {"type": "json_object"})
            self.assertEqual(
                call["extra_body"],
                {"thinking": {"type": "disabled"}},
            )

    def test_hcl_state_defaults_and_retry_budget_remain_frozen(self):
        backend = StructuredBackend(["not json", "still not json", "no object"])
        loop = HCLAnswerLoop(backend)
        self.assertEqual(loop.state_max_tokens, 8192)
        with self.assertRaisesRegex(RuntimeError, "no valid JSON after 3 attempts"):
            loop.build_state("synthetic input")
        self.assertEqual(backend.json_calls, 3)


if __name__ == "__main__":
    unittest.main()
