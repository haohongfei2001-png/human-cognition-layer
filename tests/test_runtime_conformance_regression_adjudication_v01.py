from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "adjudication",
    ROOT / "scripts/run_runtime_conformance_regression_adjudication_v01.py",
)
assert SPEC and SPEC.loader
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)


class RegressionAdjudicationTests(unittest.TestCase):
    def test_summary_requires_four_plus_four_completed_runs(self):
        rows = []
        for rep in range(1, 5):
            rows.append({
                "kind": "state_fidelity",
                "fixture_id": mod.STATE_ID,
                "repetition": rep,
                "completed": True,
                "raw_evaluation": {
                    "passed": False,
                    "failures": ["missing_bridge"],
                },
            })
            rows.append({
                "kind": "answer_checker",
                "fixture_id": mod.CHECKER_ID,
                "repetition": rep,
                "completed": True,
                "first_verdict": {"status": "REVISE"},
                "first_violation_types": ["PREMATURE_COLLAPSE"],
                "final_verdict": {"status": "PASS"},
            })

        s = mod.summarize(rows)
        self.assertEqual(s["run_count"], 8)
        self.assertEqual(s["state_completed"], 4)
        self.assertEqual(s["checker_completed"], 4)
        self.assertEqual(s["raw_state_pass_count"], 0)
        self.assertEqual(s["checker_revise_count"], 4)
        self.assertEqual(s["checker_final_pass_count"], 4)
        self.assertTrue(s["adjudication_ready"])

    def test_runtime_failure_blocks_ready(self):
        rows = []
        for rep in range(1, 5):
            rows.append({
                "kind": "state_fidelity",
                "fixture_id": mod.STATE_ID,
                "repetition": rep,
                "completed": rep != 1,
                "raw_evaluation": {"passed": False},
            })
            rows.append({
                "kind": "answer_checker",
                "fixture_id": mod.CHECKER_ID,
                "repetition": rep,
                "completed": True,
                "first_verdict": {"status": "REVISE"},
                "first_violation_types": ["PREMATURE_COLLAPSE"],
                "final_verdict": {"status": "PASS"},
            })
        self.assertFalse(mod.summarize(rows)["adjudication_ready"])


if __name__ == "__main__":
    unittest.main()
