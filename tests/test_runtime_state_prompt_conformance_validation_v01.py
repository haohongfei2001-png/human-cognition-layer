from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "eval/state_fidelity/communication_boundary_fresh_v01.json"
SPEC = importlib.util.spec_from_file_location(
    "comm_boundary",
    ROOT / "scripts/run_runtime_state_prompt_conformance_v01.py",
)
assert SPEC and SPEC.loader
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)


class CommunicationBoundaryValidationTests(unittest.TestCase):
    def test_fixture_shape(self):
        rows = json.loads(FIXTURES.read_text(encoding="utf-8"))["cases"]
        self.assertEqual(len(rows), 10)
        self.assertEqual(len({x["id"] for x in rows}), 10)
        self.assertEqual(sum(not x["require_missing_bridge"] for x in rows[:4]), 4)

    def test_summary_requires_10_of_10(self):
        rows = [
            {"id": f"x{i}", "completed": True, "passed": True}
            for i in range(10)
        ]
        self.assertTrue(mod.summarize(rows)["pass_gate"])
        rows[2]["passed"] = False
        self.assertFalse(mod.summarize(rows)["pass_gate"])


if __name__ == "__main__":
    unittest.main()
