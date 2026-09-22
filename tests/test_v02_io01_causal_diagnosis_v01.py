from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "causal_diag",
    ROOT / "scripts/run_v02_io01_causal_diagnosis_v01.py",
)
assert SPEC and SPEC.loader
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)


def target_row(rep, *, state_ok=True, draft_ok=True, candidate_ok=True, final_ok=True,
               first_status="PASS", final_status="PASS"):
    probe = {
        "target_agent_found": True,
        "observed_contains_target_token": state_ok,
        "knows_contains_target_token": False,
        "believes_contains_target_token": False,
        "explicit_facts_contains_target_token": state_ok,
        "summary_contains_target_token": state_ok,
        "state_supports_gold": state_ok,
    }
    draft = {"semantic_correct": draft_ok}
    candidate = {"semantic_correct": candidate_ok}
    final = {"semantic_correct": final_ok, "parser_valid": final_ok}
    first_check = {"status": first_status, "violation_types": []}
    final_check = {"status": final_status, "violation_types": []}
    return {
        "fixture_id": mod.TARGET_ID,
        "repetition": rep,
        "completed": True,
        "state_mode": "EPISTEMIC",
        "state_sha256": f"s{rep}",
        "state_probe": probe,
        "draft": draft,
        "first_check": first_check,
        "candidate": candidate,
        "final_check": final_check,
        "final": final,
        "signals": mod.derive_target_signals(
            probe, draft, first_check, candidate, final_check, final
        ),
    }


def control_row(rep, success=True):
    return {
        "fixture_id": mod.CONTROL_ID,
        "repetition": rep,
        "completed": True,
        "state_mode": "EPISTEMIC",
        "state_sha256": f"c{rep}",
        "final": {"semantic_correct": success, "parser_valid": success},
    }


def suite(target_factory, control_successes=8):
    rows = [target_factory(i) for i in range(1, 9)]
    rows += [control_row(i, i <= control_successes) for i in range(1, 9)]
    return rows


class CausalDiagnosisTests(unittest.TestCase):
    def test_state_dominant(self):
        rows = suite(lambda i: target_row(i, state_ok=i > 5, draft_ok=False, candidate_ok=False, final_ok=False))
        self.assertEqual(mod.summarize(rows)["interpretation"], "STATE_DOMINANT")

    def test_draft_dominant(self):
        rows = suite(lambda i: target_row(i, state_ok=True, draft_ok=i > 5, candidate_ok=False, final_ok=False, first_status="REVISE"))
        self.assertEqual(mod.summarize(rows)["interpretation"], "DRAFT_DOMINANT")

    def test_revision_dominant(self):
        rows = suite(lambda i: target_row(i, state_ok=True, draft_ok=True, candidate_ok=i > 5, final_ok=i > 5, first_status="REVISE"))
        self.assertEqual(mod.summarize(rows)["interpretation"], "REVISION_DOMINANT")

    def test_broad_instability_precedes_target_classification(self):
        rows = suite(lambda i: target_row(i), control_successes=6)
        self.assertEqual(mod.summarize(rows)["interpretation"], "BROAD_PIPELINE_INSTABILITY")

    def test_not_reproduced(self):
        rows = suite(lambda i: target_row(i))
        self.assertEqual(mod.summarize(rows)["interpretation"], "NOT_REPRODUCED_IN_CAUSAL_RUN")


if __name__ == "__main__":
    unittest.main()
