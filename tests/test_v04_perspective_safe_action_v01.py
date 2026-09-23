from __future__ import annotations

import copy
import json
import unittest

from scripts.validate_v04_perspective_safe_action_v01 import FIXTURE, preflight, validate_fixture, visible_case
from scripts.run_v04_perspective_safe_action_v01 import run_comparison


class FakeBackend:
    def complete_json(self, messages, *, max_tokens, temperature=0.0):
        payload = json.loads(messages[-1]["content"])
        if "new_events" in payload:
            return json.dumps({"candidates": [{
                "label": label, "status": "PLAUSIBLE", "support_event_ids": [],
                "counterevidence_event_ids": [], "unresolved_event_ids": [],
                "rationale": "Visible evidence does not establish acceptance.",
            } for label, _ in payload["target"]["candidate_definitions"]]})
        return json.dumps({"action_id": "SEND_CORRECTION", "rationale": "Use only visible recipient evidence."})


class PerspectiveSafeActionPreflightTests(unittest.TestCase):
    def test_frozen_fixture_is_grounded_and_model_view_hides_scoring_key(self):
        self.assertEqual(preflight()["case_count"], 6)
        data = json.loads(FIXTURE.read_text())
        for case in data["cases"]:
            visible = visible_case(case)
            self.assertNotIn("expected_action", visible)
            self.assertNotIn("forbidden_claims", visible)
            self.assertTrue(all("system" in event["observer_ids"] for event in visible["events"]))

    def test_missing_target_perspective_or_reordered_correction_fails_closed(self):
        data = json.loads(FIXTURE.read_text())
        missing_perspective = copy.deepcopy(data)
        missing_perspective["cases"][0]["events"][1]["observer_ids"] = []
        with self.assertRaisesRegex(ValueError, "system-visible provenance"):
            validate_fixture(missing_perspective)
        reordered = copy.deepcopy(data)
        reordered["cases"][0]["events"][1]["valid_time"] = reordered["cases"][0]["events"][0]["valid_time"]
        with self.assertRaisesRegex(ValueError, "chronology"):
            validate_fixture(reordered)

    def test_comparison_runs_all_arms_with_identical_visible_evidence_and_no_gold_leak(self):
        output = run_comparison(FakeBackend)
        self.assertEqual({arm: len(rows) for arm, rows in output["rows"].items()}, {"C": 6, "D": 6, "E": 6})
        self.assertEqual(output["arms"]["C"]["backend"]["calls"], 12)
        self.assertEqual(output["arms"]["D"]["backend"]["calls"], 23)
        self.assertEqual(output["arms"]["E"]["backend"]["calls"], 6)
        for calls in output["raw_synthetic_audit"].values():
            for call in calls:
                prompt = json.dumps(call["messages"])
                self.assertNotIn("expected_action", prompt)
                self.assertNotIn("forbidden_claims", prompt)
        self.assertEqual(output["semantic_audit_status"], "PENDING_MANUAL_REVIEW")


if __name__ == "__main__":
    unittest.main()
