from __future__ import annotations

import inspect
import unittest

from hcl.v03 import answer_loop


class RuntimeStatePromptConformanceTests(unittest.TestCase):
    def test_runtime_state_prompt_contains_direct_communication_rule(self):
        text = answer_loop.STATE_SYSTEM
        self.assertIn("Direct communication is an evidence path", text)
        self.assertIn("do not invent a separate truth, reliability, or trust blocker", text)
        self.assertIn("put the communicated proposition itself in knows", text)
        self.assertIn("do not downgrade it to only knowing that the source said it", text)

    def test_runtime_state_prompt_preserves_misinformation_divergence(self):
        text = answer_loop.STATE_SYSTEM
        self.assertIn("explicitly supplies misinformation", text)
        self.assertIn("preserve world truth separately", text)
        self.assertIn("communicated false proposition in believes", text)

    def test_runtime_state_prompt_forbids_logical_only_skepticism(self):
        text = answer_loop.STATE_SYSTEM
        self.assertIn("merely logically possible lying or error", text)
        self.assertIn("Do not manufacture uncertainty", text)

    def test_no_known_diagnostic_literals_in_runtime_prompt(self):
        text = answer_loop.STATE_SYSTEM
        for token in (
            "sf07_exact_positive_signal",
            "Lena",
            "east gate",
            "alarm operator",
        ):
            self.assertNotIn(token, text)

    def test_state_builder_budget_and_retry_unchanged(self):
        sig = inspect.signature(answer_loop.HCLAnswerLoop.__init__)
        self.assertEqual(sig.parameters["state_max_tokens"].default, 8192)
        source = inspect.getsource(answer_loop.HCLAnswerLoop.build_state)
        self.assertIn("for attempt in range(3)", source)


if __name__ == "__main__":
    unittest.main()
