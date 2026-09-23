from __future__ import annotations

import copy
import json
import unittest

from scripts.validate_v04_perspective_safe_action_v01 import FIXTURE, preflight, validate_fixture, visible_case


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


if __name__ == "__main__":
    unittest.main()
