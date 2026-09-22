from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "state_conflict",
    ROOT / "scripts/run_fresh_target_state_conflict_audit_v01.py",
)
assert SPEC and SPEC.loader
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)


class StateConflictAuditTests(unittest.TestCase):
    def test_probe_requires_same_item_to_contain_both_terms(self):
        state = {
            "agents": {
                "Lena": {
                    "observed": ["The east gate is open."],
                    "knows": [],
                }
            }
        }
        probe = mod.probe_state(mod.TARGET_ID, state)
        self.assertTrue(probe["target_agent_found"])
        self.assertTrue(probe["observed_support"])
        self.assertTrue(probe["state_supports_gold"])

    def test_probe_does_not_promote_split_unrelated_terms(self):
        state = {
            "agents": {
                "Lena": {
                    "observed": ["She saw the east gate.", "Another door is open."],
                    "knows": [],
                }
            }
        }
        probe = mod.probe_state(mod.TARGET_ID, state)
        self.assertFalse(probe["state_supports_gold"])

    def test_summary_requires_24_rows(self):
        rows = []
        for fixture_id in [mod.TARGET_ID, mod.CONTROL_AB_ID, mod.CONTROL_EPI_ID]:
            for rep in range(1, 9):
                rows.append({
                    "fixture_id": fixture_id,
                    "repetition": rep,
                    "completed": True,
                    "mode": "EPISTEMIC",
                    "uncertainty_level": "low",
                    "state_sha256": f"{fixture_id}-{rep}",
                    "probe": {
                        "target_agent_found": True,
                        "state_supports_gold": True,
                    },
                })
        s = mod.summarize(rows)
        self.assertEqual(s["run_count"], 24)
        self.assertTrue(s["audit_complete"])


if __name__ == "__main__":
    unittest.main()
