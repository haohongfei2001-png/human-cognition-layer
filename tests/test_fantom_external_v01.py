from __future__ import annotations

import json
import unittest
from pathlib import Path

from scripts.aggregate_fantom_external_v01 import (
    summarize_binary_like,
    summarize_fact,
)
from scripts.run_fantom_external_v01 import (
    CONTROL_SYSTEM,
    belief_orientation,
    build_prompt,
    parse_binary,
    parse_mc,
    token_f1,
)

ROOT = Path(__file__).resolve().parents[1]
SELECTION = ROOT / "eval/fantom/selection_v01.json"


class FantomExternalV01Tests(unittest.TestCase):
    def test_selection_is_exactly_32_and_conversation_disjoint(self):
        data = json.loads(SELECTION.read_text(encoding="utf-8"))
        selected = data["selected"]
        self.assertEqual(len(selected), 32)
        self.assertEqual(len({x["question_id"] for x in selected}), 32)
        self.assertEqual(len({x["conversation_id"] for x in selected}), 32)
        self.assertTrue(data["selection"]["conversation_disjoint"])

        expected = {
            "belief_inaccessible_first": 4,
            "belief_inaccessible_second": 4,
            "answerability_inaccessible_binary": 4,
            "info_accessibility_inaccessible_binary": 4,
            "belief_accessible_first": 4,
            "belief_accessible_second": 4,
            "fact_control": 8,
        }
        actual = {
            key: sum(x["stratum"] == key for x in selected)
            for key in expected
        }
        self.assertEqual(actual, expected)

    def test_frozen_belief_orientation_matches_manifest(self):
        data = json.loads(SELECTION.read_text(encoding="utf-8"))
        beliefs = [x for x in data["selected"] if x["family"] == "belief_mc"]
        self.assertEqual(len(beliefs), 16)
        for item in beliefs:
            self.assertEqual(
                belief_orientation(item["question_id"]),
                item["correct_option"],
            )

    def test_mc_parser_is_deterministic_and_rejects_ambiguity(self):
        self.assertEqual(parse_mc("[A]"), "A")
        self.assertEqual(parse_mc(" [b] "), "B")
        self.assertEqual(parse_mc("A."), "A")
        self.assertEqual(parse_mc("Answer: (b)"), "B")
        self.assertIsNone(parse_mc("[A] or [B]"))
        self.assertIsNone(parse_mc("I cannot tell"))

    def test_binary_parser_requires_leading_verdict(self):
        self.assertEqual(parse_binary("yes"), "yes")
        self.assertEqual(parse_binary("True."), "yes")
        self.assertEqual(parse_binary("Answer: no"), "no")
        self.assertEqual(parse_binary("false because..."), "no")
        self.assertIsNone(parse_binary("I think yes"))
        self.assertIsNone(parse_binary("unknown"))

    def test_fact_token_f1_matches_simple_counter_overlap(self):
        self.assertEqual(token_f1("red ball", "red ball"), 1.0)
        self.assertEqual(token_f1("red ball", "blue cube"), 0.0)
        self.assertAlmostEqual(token_f1("red ball", "red"), 2 / 3)
        self.assertEqual(token_f1("", ""), 1.0)
        self.assertEqual(token_f1("", "x"), 0.0)

    def test_common_task_header_occurs_once_in_control_user_prompt(self):
        record = {
            "question_id": "synthetic",
            "family": "fact",
            "context": "Alice said hello.",
            "question": "What did Alice say?",
            "correct_answer": "hello",
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
        self.assertNotIn("theory-of-mind", CONTROL_SYSTEM.lower())
        self.assertNotIn("correct_answer", prompt)

    def test_binary_pair_aggregation(self):
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
                "control": {"correct": True},
                "treatment": {"correct": True},
                "paired_outcome": "both_correct",
            },
            {
                "control": {"correct": False},
                "treatment": {"correct": True},
                "paired_outcome": "improved",
            },
        ]
        summary = summarize_binary_like(items)
        self.assertEqual(summary["n"], 4)
        self.assertEqual(summary["control_correct"], 2)
        self.assertEqual(summary["treatment_correct"], 3)
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
        self.assertEqual(summary["n"], 2)
        self.assertAlmostEqual(summary["control_mean_token_f1"], 0.75)
        self.assertAlmostEqual(summary["treatment_mean_token_f1"], 0.625)
        self.assertAlmostEqual(summary["paired_mean_delta"], -0.125)


if __name__ == "__main__":
    unittest.main()
