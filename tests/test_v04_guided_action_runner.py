"""The frozen action comparison must exercise all three arms without leaking gold."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from scripts.run_v04_hypothesis_guided_action_v01 import (
    run_direct,
    run_structured,
    validate_fixtures,
)


class ScriptedBackend:
    def __init__(self):
        self.calls = []

    def complete_json(self, messages, *, max_tokens, temperature=0.0):
        self.calls.append(messages)
        task = json.loads(messages[-1]["content"])
        if "current_state" in task:
            return json.dumps({"candidates": task["current_state"]["candidates"]})
        if "allowed_probes" in task:
            return json.dumps({
                "probe_id": task["allowed_probes"][0]["probe_id"],
                "rationale": "Tests the first allowed information path.",
                "targeted_hypotheses": [],
            })
        if "allowed_actions" in task:
            return json.dumps({
                "action_id": task["allowed_actions"][0]["action_id"],
                "rationale": "Uses the observed evidence.",
            })
        if "allowed_options" in task:
            key = "probe_id" if messages[0]["content"].startswith("Choose one allowed probe") else "action_id"
            return json.dumps({
                key: task["allowed_options"][0]["id"],
                "rationale": "Uses the visible event history.",
            })
        raise AssertionError(f"unexpected backend task keys: {sorted(task)}")


class GuidedActionRunnerTests(unittest.TestCase):
    def test_frozen_scenario_runs_all_arms_without_exposing_gold(self):
        fixtures = json.loads(
            Path("eval/v04/hypothesis_guided_action_v01.json").read_text()
        )
        validate_fixtures(fixtures)
        scenario = fixtures[0]
        rows = {}
        for arm in ("C", "D", "E"):
            backend = ScriptedBackend()
            rows[arm] = (
                run_direct(scenario, backend)
                if arm == "E"
                else run_structured(scenario, backend, persistent=arm == "D")
            )
            self.assertEqual(rows[arm]["scenario"], scenario["id"])
            self.assertIn(rows[arm]["probe_id"], dict(scenario["probes"]))
            self.assertIn(rows[arm]["action_id"], dict(scenario["actions"]))
            prompts = "\n".join(
                str(message["content"])
                for call in backend.calls
                for message in call
            )
            self.assertNotIn('"hidden_target"', prompts)
            self.assertNotIn('"correct_actions"', prompts)
            self.assertNotIn('"probe_responses"', prompts)
        self.assertIn("state_signature", rows["C"])
        self.assertIn("state_signature", rows["D"])
        self.assertNotIn("state_signature", rows["E"])


if __name__ == "__main__":
    unittest.main()
