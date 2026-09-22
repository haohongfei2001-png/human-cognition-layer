from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "fresh_causal",
    ROOT / "scripts/run_generic_answer_fresh_causal_diagnosis_v01.py",
)
assert SPEC and SPEC.loader
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)


def make_row(fixture_id: str, rep: int, *, state_ok=True, draft_ok=True, final_ok=True):
    first_stage = "NONE"
    if not state_ok:
        first_stage = "STATE"
    elif not draft_ok:
        first_stage = "DRAFT"
    elif not final_ok:
        first_stage = "FIRST_REVISION"
    return {
        "fixture_id": fixture_id,
        "repetition": rep,
        "completed": True,
        "state_probe": {
            "target_agent_found": True,
            "state_supports_gold": state_ok,
        },
        "draft": {"semantic_correct": draft_ok},
        "final": {
            "semantic_correct": final_ok,
            "parser_valid": final_ok,
        },
        "signals": {
            "first_inversion_stage": first_stage,
            "first_check_false_pass": False,
            "first_check_false_revise": False,
            "final_check_false_pass": False,
        },
    }


def suite(target_state=8, target_draft=8, target_final=8, control_ab=8, control_epi=8):
    rows = []
    for i in range(1, 9):
        rows.append(make_row(
            mod.TARGET_ID,
            i,
            state_ok=i <= target_state,
            draft_ok=i <= target_draft,
            final_ok=i <= target_final,
        ))
        rows.append(make_row(
            mod.CONTROL_AB_ID,
            i,
            state_ok=True,
            draft_ok=i <= control_ab,
            final_ok=i <= control_ab,
        ))
        rows.append(make_row(
            mod.CONTROL_EPISTEMIC_ID,
            i,
            state_ok=True,
            draft_ok=i <= control_epi,
            final_ok=i <= control_epi,
        ))
    return rows


class FreshCausalDiagnosisTests(unittest.TestCase):
    def test_target_state_dominant(self):
        self.assertEqual(
            mod.summarize(suite(target_state=2, target_draft=2, target_final=1))["interpretation"],
            "TARGET_STATE_DOMINANT",
        )

    def test_target_draft_dominant(self):
        self.assertEqual(
            mod.summarize(suite(target_state=8, target_draft=2, target_final=1))["interpretation"],
            "TARGET_DRAFT_DOMINANT",
        )

    def test_checker_revision_dominant(self):
        self.assertEqual(
            mod.summarize(suite(target_state=8, target_draft=8, target_final=1))["interpretation"],
            "TARGET_CHECKER_REVISION_DOMINANT",
        )

    def test_broad_instability_precedes_target(self):
        self.assertEqual(
            mod.summarize(suite(control_ab=6))["interpretation"],
            "BROAD_POSITIVE_PIPELINE_INSTABILITY",
        )

    def test_low_repeatability_target_failure(self):
        self.assertEqual(
            mod.summarize(suite(target_final=7))["interpretation"],
            "TARGET_FAILURE_LOW_REPEATABILITY",
        )


if __name__ == "__main__":
    unittest.main()
