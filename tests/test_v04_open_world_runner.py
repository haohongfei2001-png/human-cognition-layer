"""The frozen open-world comparison must keep gold out of all model prompts."""

import json
import unittest

from scripts.run_v04_hypothesis_guided_action_v01 import run_direct, run_structured
from scripts.run_v04_open_world_hypothesis_v01 import FIXTURES, validate_fixtures


class ScriptedBackend:
    def __init__(self):
        self.calls = []

    def complete_json(self, messages, *, max_tokens, temperature=0.0):
        self.calls.append(messages)
        task = json.loads(messages[-1]["content"])
        if "current_state" in task:
            return json.dumps({"candidates": task["current_state"]["candidates"]})
        if "allowed_probes" in task:
            return json.dumps({"probe_id": task["allowed_probes"][0]["probe_id"], "rationale": "Explore a visible alternative.", "targeted_hypotheses": []})
        if "allowed_actions" in task:
            return json.dumps({"action_id": task["allowed_actions"][0]["action_id"], "rationale": "Use the observed response."})
        if "allowed_options" in task:
            probe = messages[0]["content"].startswith("Choose one allowed probe")
            return json.dumps({("probe_id" if probe else "action_id"): task["allowed_options"][0]["id"], "rationale": "Use visible events."})
        raise AssertionError(f"unexpected task keys: {sorted(task)}")


class OpenWorldRunnerTests(unittest.TestCase):
    def test_frozen_digest_and_all_three_arms_preserve_hidden_state(self):
        raw = FIXTURES.read_bytes()
        fixtures = validate_fixtures(raw)
        self.assertEqual(len(fixtures), 6)
        self.assertIn("OTHER_UNKNOWN", {row["hidden_target"] for row in fixtures})
        for scenario in fixtures[:2]:
            for arm in ("C", "D", "E"):
                backend = ScriptedBackend()
                row = run_direct(scenario, backend) if arm == "E" else run_structured(scenario, backend, persistent=arm == "D")
                self.assertIn(row["action_id"], dict(scenario["actions"]))
                prompts = "\n".join(str(message["content"]) for call in backend.calls for message in call)
                for forbidden in ('"hidden_target"', '"correct_actions"', '"probe_responses"'):
                    self.assertNotIn(forbidden, prompts)
                self.assertIn("OTHER_UNKNOWN", prompts)

    def test_fixture_edits_cannot_be_scored_as_fresh(self):
        with self.assertRaisesRegex(ValueError, "digest mismatch"):
            validate_fixtures(FIXTURES.read_bytes() + b" ")


if __name__ == "__main__":
    unittest.main()
