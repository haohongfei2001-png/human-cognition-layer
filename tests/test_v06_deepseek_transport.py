"""Provider-free request-shape tests for the v0.6 DeepSeek transport repair."""

from __future__ import annotations

import unittest
from types import SimpleNamespace

from hcl.v04.backends import OpenAICompatibleBackend
from hcl.v04.provider_profiles import DEEPSEEK_FLASH_CAPABILITIES


class DeepSeekTransportRepairTests(unittest.TestCase):
    def test_non_thinking_extra_body_applies_to_text_and_json_requests(self):
        class FakeCompletions:
            def __init__(self):
                self.calls = []

            def create(self, **kwargs):
                self.calls.append(kwargs)
                return SimpleNamespace(
                    choices=[
                        SimpleNamespace(
                            message=SimpleNamespace(content="ok")
                        )
                    ]
                )

        fake = FakeCompletions()
        backend = OpenAICompatibleBackend(
            api_key="x",
            base_url="https://example.invalid",
            model="deepseek-flash",
            capabilities=DEEPSEEK_FLASH_CAPABILITIES,
        )
        backend.client = SimpleNamespace(
            chat=SimpleNamespace(completions=fake)
        )

        self.assertEqual(
            backend.complete([{"role": "user", "content": "x"}], max_tokens=8),
            "ok",
        )
        self.assertEqual(
            backend.complete_json([{"role": "user", "content": "x"}], max_tokens=8),
            "ok",
        )

        expected = {"thinking": {"type": "disabled"}}
        self.assertEqual(fake.calls[0]["extra_body"], expected)
        self.assertEqual(fake.calls[1]["extra_body"], expected)
        self.assertNotIn("response_format", fake.calls[0])
        self.assertEqual(
            fake.calls[1]["response_format"],
            {"type": "json_object"},
        )


if __name__ == "__main__":
    unittest.main()
