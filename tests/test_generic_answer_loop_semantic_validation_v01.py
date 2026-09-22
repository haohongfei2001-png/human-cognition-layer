from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "eval/answer_loop/semantic_faithfulness_fresh_v01.json"
SPEC = importlib.util.spec_from_file_location(
    "semantic_validation",
    ROOT / "scripts/run_generic_answer_loop_semantic_repair_v01.py",
)
assert SPEC and SPEC.loader
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)


class SemanticFaithfulnessValidationTests(unittest.TestCase):
    def test_fixture_shape_and_balance(self):
        suite = json.loads(FIXTURES.read_text(encoding="utf-8"))
        rows = suite["cases"]
        self.assertEqual(len(rows), 12)
        self.assertEqual(len({x["id"] for x in rows}), 12)
        directions = [x["direction"] for x in rows]
        self.assertGreaterEqual(directions.count("DIRECT_POSITIVE"), 5)
        self.assertGreaterEqual(directions.count("DIRECT_NEGATIVE"), 4)
        self.assertEqual(directions.count("EXPLICIT_TRANSFER"), 2)
        self.assertTrue(all(x["requires_exact"] for x in rows))

    def test_summary_pass_requires_every_case(self):
        rows = []
        for i in range(12):
            rows.append({
                "id": f"x{i}",
                "direction": "DIRECT_POSITIVE",
                "format": "binary",
                "gold": "yes",
                "requires_exact": True,
                "completed": True,
                "semantic_correct": True,
                "parser_valid": True,
                "exact_format": True,
            })
        self.assertTrue(mod.summarize(rows)["pass_gate"])
        rows[3]["semantic_correct"] = False
        self.assertFalse(mod.summarize(rows)["pass_gate"])

    def test_runtime_exception_blocks_pass(self):
        rows = []
        for i in range(12):
            if i == 0:
                rows.append({
                    "id": "x0",
                    "direction": "DIRECT_POSITIVE",
                    "format": "binary",
                    "gold": "yes",
                    "requires_exact": True,
                    "completed": False,
                    "runtime_exception_type": "RuntimeError",
                })
            else:
                rows.append({
                    "id": f"x{i}",
                    "direction": "DIRECT_POSITIVE",
                    "format": "binary",
                    "gold": "yes",
                    "requires_exact": True,
                    "completed": True,
                    "semantic_correct": True,
                    "parser_valid": True,
                    "exact_format": True,
                })
        self.assertFalse(mod.summarize(rows)["pass_gate"])


if __name__ == "__main__":
    unittest.main()
