from __future__ import annotations

import ast
import inspect
import unittest

from hcl.v03 import answer_loop


class GenericAnswerLoopSemanticRepairTests(unittest.TestCase):
    def test_draft_has_state_grounding_and_exact_output_contract(self):
        text = answer_loop.DRAFT_SYSTEM
        self.assertIn("structured HCL state is authoritative cognitive context", text)
        self.assertIn("observed or knows", text)
        self.assertIn("do not negate", text)
        self.assertIn("exact output form", text)
        self.assertIn("add no explanation", text)

    def test_checker_has_semantic_monotonicity_contract(self):
        text = answer_loop.CHECK_SYSTEM
        self.assertIn("Judge state faithfulness before style", text)
        self.assertIn("INFORMATION_ACCESS", text)
        self.assertIn("directly established observed/knows evidence", text)
        self.assertIn("GRANULARITY", text)
        self.assertIn("Do not request revision merely because", text)

    def test_revision_preserves_supported_semantics(self):
        text = answer_loop.REVISION_SYSTEM
        self.assertIn("HCL state outranks checker prose", text)
        self.assertIn("Never flip a directly supported answer", text)
        self.assertIn("observed/knows", text)
        self.assertIn("exact-output", text)

    def test_no_known_fixture_specific_literals_in_repair_prompts(self):
        combined = "\n".join([
            answer_loop.DRAFT_SYSTEM,
            answer_loop.CHECK_SYSTEM,
            answer_loop.REVISION_SYSTEM,
        ])
        forbidden = [
            "io01_full_binary_direct_access",
            "io02_full_binary_missing_access",
            "Priya",
            "Damon",
            "4821",
        ]
        for token in forbidden:
            self.assertNotIn(token, combined)

    def test_state_builder_default_budget_remains_8192(self):
        sig = inspect.signature(answer_loop.HCLAnswerLoop.__init__)
        self.assertEqual(sig.parameters["state_max_tokens"].default, 8192)

    def test_state_retry_budget_remains_three(self):
        source = inspect.getsource(answer_loop.HCLAnswerLoop.build_state)
        tree = ast.parse(source)
        calls = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "range"
        ]
        literals = [
            node.args[0].value
            for node in calls
            if len(node.args) == 1
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, int)
        ]
        self.assertIn(3, literals)


if __name__ == "__main__":
    unittest.main()
