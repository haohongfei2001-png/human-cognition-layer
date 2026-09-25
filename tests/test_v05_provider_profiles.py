"""Provider-free guards for cross-model transport profiles."""

from __future__ import annotations

import inspect
import unittest
from types import SimpleNamespace

from hcl.v04.provider_profiles import (
    DEEPSEEK_FLASH_CAPABILITIES,
    GENERIC_OPENAI_COMPATIBLE_CAPABILITIES,
    QWEN_OPENAI_COMPATIBLE_CAPABILITIES,
    capabilities_for_profile,
    provider_profile_names,
)
from hcl.v04.backends import OpenAICompatibleBackend
from scripts.run_v04_long_horizon_bounded_context_v01 import make_real_backend


class ProviderProfileTests(unittest.TestCase):
    def test_profiles_are_explicit_and_bounded(self):
        self.assertEqual(
            provider_profile_names(),
            ("deepseek_flash", "generic_openai", "qwen_openai"),
        )

    def test_deepseek_preserves_frozen_non_thinking_request_profile(self):
        p = DEEPSEEK_FLASH_CAPABILITIES
        self.assertTrue(p.json_object_mode)
        self.assertTrue(p.seed)
        self.assertEqual(
            p.json_extra_body,
            {"thinking": {"type": "disabled"}},
        )

    def test_deepseek_extra_body_applies_to_text_and_json_requests(self):
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

        self.assertEqual(
            fake.calls[0]["extra_body"],
            {"thinking": {"type": "disabled"}},
        )
        self.assertEqual(
            fake.calls[1]["extra_body"],
            {"thinking": {"type": "disabled"}},
        )
        self.assertNotIn("response_format", fake.calls[0])
        self.assertEqual(
            fake.calls[1]["response_format"],
            {"type": "json_object"},
        )

    def test_generic_profile_never_inherits_deepseek_extra_body(self):
        p = GENERIC_OPENAI_COMPATIBLE_CAPABILITIES
        self.assertTrue(p.json_object_mode)
        self.assertFalse(p.seed)
        self.assertEqual(p.json_extra_body, {})

    def test_qwen_profile_never_inherits_deepseek_extra_body_or_seed_assumption(self):
        p = QWEN_OPENAI_COMPATIBLE_CAPABILITIES
        self.assertTrue(p.json_object_mode)
        self.assertFalse(p.seed)
        self.assertEqual(p.json_extra_body, {})

    def test_lookup_is_fail_closed(self):
        self.assertIs(
            capabilities_for_profile("deepseek_flash"),
            DEEPSEEK_FLASH_CAPABILITIES,
        )
        self.assertIs(
            capabilities_for_profile("QWEN_OPENAI"),
            QWEN_OPENAI_COMPATIBLE_CAPABILITIES,
        )
        with self.assertRaises(ValueError):
            capabilities_for_profile("mystery-provider")

    def test_historical_runner_default_remains_deepseek(self):
        sig = inspect.signature(make_real_backend)
        self.assertEqual(
            sig.parameters["provider_profile"].default,
            "deepseek_flash",
        )


if __name__ == "__main__":
    unittest.main()
