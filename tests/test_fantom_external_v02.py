from __future__ import annotations

import json
import unittest
from pathlib import Path

import pandas as pd

from scripts.aggregate_fantom_external_v02 import (
    summarize_binary_like,
    summarize_fact,
)
from scripts.run_fantom_external_v02 import (
    CONTROL_SYSTEM,
    belief_orientation,
    build_prompt,
    build_question_map,
    parse_binary,
    parse_mc,
    token_f1,
)

ROOT = Path(__file__).resolve().parents[1]
SELECTION_V02 = ROOT / "eval/fantom/selection_v02.json"
SELECTION_V01 = ROOT / "eval/fantom/selection_v01.json"


class FantomExternalV02Tests(unittest.TestCase):
    def test_selection_is_48_conversation_disjoint_and_v01_disjoint(self):
        v02 = json.loads(SELECTION_V02.read_text(encoding="utf-8"))
        selected = v02["selected"]
        self.assertEqual(len(selected), 48)
        self.assertEqual(len({x["question_id"] for x in selected}), 48)
        self.assertEqual(len({x["conversation_id"] for x in selected}), 48)
        self.assertTrue(v02["selection"]["conversation_disjoint"])
        self.assertEqual(v02["selection"]["v01_conversation_overlap"], 0)
        self.assertEqual(v02["selection"]["context_type"], "full")

        v01 = json.loads(SELECTION_V01.read_text(encoding="utf-8"))
        old = {x["conversation_id"] for x in v01["selected"]}
        new = {x["conversation_id"] for x in selected}
        self.assertFalse(old & new)

        expected = {
            "belief_inaccessible_first": 8,
            "belief_inaccessible_second": 8,
            "answerability_full_inaccessible_binary": 8,
            "info_accessibility_full_inaccessible_binary": 8,
            "belief_accessible_first": 4,
            "belief_accessible_second": 4,
            "fact_control": 8,
        }
        actual = {
            key: sum(x["stratum"] == key for x in selected)
            for key in expected
        }
        self.assertEqual(actual, expected)

    def test_frozen_belief_orientation_matches_v02_manifest(self):
        data = json.loads(SELECTION_V02.read_text(encoding="utf-8"))
        beliefs = [x for x in data["selected"] if x["family"] == "belief_mc"]
        self.assertEqual(len(beliefs), 24)
        for item in beliefs:
            self.assertEqual(
                belief_orientation(item["question_id"]),
                item["correct_option"],
            )

    def test_runner_uses_full_context_not_short_context(self):
        row = {
            "set_id": "synthetic-0-0",
            "short_context": "SHORT_SENTINEL",
            "full_context": "FULL_SENTINEL",
            "factQA": {
                "question": "What happened?",
                "correct_answer": "nothing",
                "question_type": "fact",
            },
            "beliefQAs": [],
            "answerabilityQAs_binary": [],
            "infoAccessibilityQAs_binary": [],
        }
        records = build_question_map(pd.DataFrame([row]))
        self.assertEqual(len(records), 1)
        record = next(iter(records.values()))
        self.assertEqual(record["context"], "FULL_SENTINEL")
        self.assertNotEqual(record["context"], "SHORT_SENTINEL")

    def test_mc_and_binary_parsers_remain_deterministic(self):
        self.assertEqual(parse_mc("[A]"), "A")
        self.assertEqual(parse_mc("Answer: (b)"), "B")
        self.assertIsNone(parse_mc("[A] or [B]"))
        self.assertEqual(parse_binary("yes"), "yes")
        self.assertEqual(parse_binary("false"), "no")
        self.assertIsNone(parse_binary("I think yes"))

    def test_fact_token_f1_unchanged(self):
        self.assertEqual(token_f1("red ball", "red ball"), 1.0)
        self.assertAlmostEqual(token_f1("red ball", "red"), 2 / 3)
        self.assertEqual(token_f1("red ball", "blue cube"), 0.0)

    def test_common_prompt_header_and_neutral_control_system(self):
        record = {
            "question_id": "synthetic",
            "family": "fact",
            "context": "FULL_CONTEXT",
            "question": "What happened?",
            "correct_answer": "nothing",
        }
        prompt = build_prompt(
            record,
            {
                "question_id": "synthetic",
                "family": "fact",
                "stratum": "fact_control",
            },
        )
        self.assertEqual(prompt.count("This is a theory-of-mind test."), 1)
        self.assertIn("FULL_CONTEXT", prompt)
        self.assertNotIn("theory-of-mind", CONTROL_SYSTEM.lower())

    def test_binary_aggregation(self):
        items = [
            {
                "control": {"correct": False},
                "treatment": {"correct": True},
                "paired_outcome": "improved",
            },
            {
                "control": {"correct": True},
                "treatment": {"correct": False},
                "paired_outcome": "worsened",
            },
            {
                "control": {"correct": False},
                "treatment": {"correct": True},
                "paired_outcome": "improved",
            },
        ]
        summary = summarize_binary_like(items)
        self.assertEqual(summary["improved"], 2)
        self.assertEqual(summary["worsened"], 1)
        self.assertEqual(summary["net_paired_gain"], 1)

    def test_fact_aggregation(self):
        items = [
            {
                "control": {"token_f1": 0.5},
                "treatment": {"token_f1": 0.75},
            },
            {
                "control": {"token_f1": 1.0},
                "treatment": {"token_f1": 0.5},
            },
        ]
        summary = summarize_fact(items)
        self.assertAlmostEqual(summary["control_mean_token_f1"], 0.75)
        self.assertAlmostEqual(summary["treatment_mean_token_f1"], 0.625)
        self.assertAlmostEqual(summary["paired_mean_delta"], -0.125)


if __name__ == "__main__":
    unittest.main()
