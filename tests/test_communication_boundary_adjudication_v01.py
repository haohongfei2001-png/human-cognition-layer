from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "boundary_adj",
    ROOT / "scripts/run_communication_boundary_adjudication_v01.py",
)
assert SPEC and SPEC.loader
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)


class CommunicationBoundaryAdjudicationTests(unittest.TestCase):
    def test_fixed_case_set_and_repeat_count(self):
        self.assertEqual(
            mod.CASE_IDS,
            [
                "cb02_direct_teacher",
                "cb06_unread_notice",
                "cb10_conflicting_sources",
            ],
        )
        self.assertEqual(mod.REPEATS, 4)

    def test_summary_complete_at_12_rows(self):
        rows = []
        for case_id in mod.CASE_IDS:
            for repetition in range(1, 5):
                rows.append({
                    "fixture_id": case_id,
                    "repetition": repetition,
                    "completed": True,
                    "mode": "EPISTEMIC",
                    "uncertainty_level": "low",
                    "state_sha256": f"{case_id}-{repetition}",
                })
        summary = mod.summarize(rows)
        self.assertEqual(summary["run_count"], 12)
        self.assertTrue(summary["audit_complete"])


if __name__ == "__main__":
    unittest.main()
