from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "investigation",
    ROOT / "scripts/run_v02_interface_regression_investigation_v01.py",
)
assert SPEC and SPEC.loader
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)


def row(fixture_id: str, repetition: int, *, success: bool, mode: str = "EPISTEMIC"):
    return {
        "fixture_id": fixture_id,
        "repetition": repetition,
        "gold": "yes" if fixture_id == mod.TARGET_ID else "no",
        "completed": True,
        "parsed": "yes" if success else None,
        "parser_valid": success,
        "semantic_correct": success,
        "exact_format": success,
        "response_chars": 3 if success else 48,
        "state_mode": mode,
        "uncertainty": "medium",
        "state_sha256": f"hash-{fixture_id}-{repetition}",
        "first_check_status": "REVISE",
        "final_check_status": "PASS",
        "revision_performed": True,
        "second_revision_performed": False,
    }


def suite(target_success: int, control_success: int):
    rows = []
    for i in range(1, 9):
        rows.append(row(mod.TARGET_ID, i, success=i <= target_success))
        rows.append(row(mod.CONTROL_ID, i, success=i <= control_success))
    return rows


class InterfaceInvestigationTests(unittest.TestCase):
    def test_stable_target_regression(self):
        s = mod.summarize(suite(2, 8))
        self.assertEqual(s["interpretation"], "STABLE_IO01_REGRESSION")

    def test_isolated_stochastic_instability(self):
        s = mod.summarize(suite(5, 8))
        self.assertEqual(
            s["interpretation"],
            "ISOLATED_STOCHASTIC_INTERFACE_INSTABILITY",
        )

    def test_low_repeatability_original_failure(self):
        s = mod.summarize(suite(7, 8))
        self.assertEqual(s["interpretation"], "LOW_REPEATABILITY_ORIGINAL_FAILURE")

    def test_broad_instability_takes_precedence(self):
        s = mod.summarize(suite(8, 6))
        self.assertEqual(s["interpretation"], "BROAD_OUTPUT_INSTABILITY")

    def test_state_mode_drift_blocks_progression(self):
        rows = suite(8, 8)
        rows[0]["state_mode"] = "SIMPLE"
        s = mod.summarize(rows)
        self.assertEqual(s["interpretation"], "TARGET_STATE_MODE_DRIFT_BLOCK")

    def test_runtime_exception_blocks_progression(self):
        rows = suite(8, 8)
        rows[0] = {
            "fixture_id": mod.TARGET_ID,
            "repetition": 1,
            "gold": "yes",
            "completed": False,
            "runtime_exception_type": "RuntimeError",
        }
        s = mod.summarize(rows)
        self.assertEqual(s["interpretation"], "RUNTIME_EXCEPTION_BLOCK")


if __name__ == "__main__":
    unittest.main()
