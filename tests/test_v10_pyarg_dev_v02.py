"""Output-contract repair gates: no provider, no consumed-case cognition tuning."""

import json
import unittest
from unittest.mock import patch
from tests.test_v10_pyarg_dev_v01 import item
from scripts import run_v10_pyarg_dev_v01 as old
from scripts import run_v10_pyarg_dev_v02 as repair


class ContractRepairTests(unittest.TestCase):
    def test_all_arms_receive_explicit_top_level_contract_and_identical_inputs(self):
        x = item()
        self.assertEqual(old.inputs(x), repair.inputs(x))
        records = []

        class Backend:
            def complete_json(self, messages, **kwargs):
                records.append(messages)
                system = messages[0]["content"]
                if (
                    "exactly two TOP-LEVEL keys: labellings and reason" not in system
                    or "NEVER put reason inside a labelling" not in system
                ):
                    return json.dumps(
                        {
                            "labellings": [
                                {
                                    "IN": ["a", "c"],
                                    "OUT": ["b"],
                                    "UNDEC": [],
                                    "reason": "nested",
                                }
                            ]
                        }
                    )
                return json.dumps(
                    {
                        "labellings": [{"IN": ["a", "c"], "OUT": ["b"], "UNDEC": []}],
                        "reason": "Conditional graph result only.",
                    }
                )

        result = repair.evaluate_one(x, {a: Backend() for a in repair.CAPS})
        self.assertEqual(len(records), 3)
        self.assertTrue(
            all(
                a["invalid_reason"] is None and a["agrees_with_declared_graph"]
                for a in result["arms"].values()
            )
        )
        self.assertIn(
            "not facts about people, moral truth, or actual beliefs",
            records[0][0]["content"],
        )
        # The fake transport verifies contract placement, not language-model efficacy.

    def test_frozen_strict_parser_still_rejects_nested_explanations(self):
        good = {
            "labellings": [{"IN": ["a", "c"], "OUT": ["b"], "UNDEC": []}],
            "reason": "x",
        }
        self.assertEqual(
            old.parse_answer(json.dumps(good), ["a", "b", "c"]),
            repair.parse_answer(json.dumps(good), ["a", "b", "c"]),
        )
        good["labellings"][0]["reason"] = "x"
        with self.assertRaises(ValueError):
            repair.parse_answer(json.dumps(good), ["a", "b", "c"])
        del good["reason"]
        with self.assertRaises(ValueError):
            repair.parse_answer(json.dumps(good), ["a", "b", "c"])

    def test_no_local_or_reused_authorization_can_execute(self):
        with patch.object(repair, "verified_selection", return_value=[]), patch.object(
            repair, "validate", return_value={}
        ), patch(
            "sys.argv", ["runner", "--source-dir", "unused", "--execute"]
        ), patch.dict(
            repair.os.environ, {}, clear=True
        ):
            with self.assertRaisesRegex(RuntimeError, "first-attempt"):
                repair.main()
        env = {
            "GITHUB_ACTIONS": "true",
            "GITHUB_RUN_ATTEMPT": "1",
            "HCL_V10_PYARG_DEV_V02_RUN_ONCE_TOKEN": repair.TOKEN,
            "HCL_V10_PYARG_DEV_COST_AUTHORIZED_USD": "100",
        }
        with patch.object(repair, "verified_selection", return_value=[]), patch.object(
            repair, "validate", return_value={}
        ), patch(
            "sys.argv", ["runner", "--source-dir", "unused", "--execute"]
        ), patch.dict(
            repair.os.environ, env, clear=True
        ):
            with self.assertRaisesRegex(RuntimeError, "separate"):
                repair.main()


if __name__ == "__main__":
    unittest.main()
