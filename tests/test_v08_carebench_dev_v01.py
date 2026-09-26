"""Source-only release, answer quoting and bounded v0.8 runner regressions."""

import json
import unittest
from scripts.prepare_v08_carebench_dev_v01 import (
    SourceNarrative,
    sha,
    select_source_only,
)
from scripts.run_v08_carebench_dev_v01 import (
    evaluate_one,
    parse_answer,
    CAPS,
    COST_CAP_USD,
)


class Backend:
    def __init__(self, response):
        self.response = response
        self.inputs = []

    def complete_json(self, messages, *, max_tokens, temperature=0):
        self.inputs.append(messages)
        return self.response


class UtilityTests(unittest.TestCase):
    def test_three_arms_share_source_without_annotation_release(self):
        story = "I feel relieved but still worried. It matters to me that the delayed parcel arrives."
        source = SourceNarrative(sha("synthetic-key"), sha(story), story)
        output = json.dumps(
            {
                "emotions": [
                    {
                        "value": "relief and worry",
                        "strength": "DIRECT",
                        "quote": "I feel relieved but still worried.",
                        "time_scope": "reported episode",
                    }
                ],
                "appraisals": [],
                "uncertainty": "No unique additional feeling is established.",
            }
        )
        backends = {"SEMANTIC": Backend('{"affect_evidence":[]}')}
        backends.update({a: Backend(output) for a in "CPD"})
        result = evaluate_one({"case_id": "synthetic"}, source, backends)
        self.assertEqual(set(result["arms"]), set("CPD"))
        self.assertEqual(result["state_audit"]["source_reports"], 1)
        semantic_source = json.loads(backends["SEMANTIC"].inputs[0][1]["content"])
        self.assertEqual(semantic_source["raw_text"], story)
        for forbidden in (
            "task",
            "emotion_labels",
            "appraisal_ratings",
            "cognitive_questions",
            "personality_questionnaire",
            "participant_id",
            "demographics",
        ):
            self.assertNotIn(forbidden, semantic_source)
        for a in "CPD":
            prompt = backends[a].inputs[0][1]["content"]
            self.assertIn(story[:33], prompt)
            self.assertIn("Target: the first-person experiencer", prompt)
            self.assertIsNone(result["arms"][a]["invalid_reason"])

    def test_quote_validation_and_time_scope_cannot_be_skipped(self):
        base = {
            "emotions": [
                {
                    "value": "relief",
                    "strength": "DIRECT",
                    "quote": "I feel relieved.",
                    "time_scope": "reported moment",
                }
            ],
            "appraisals": [],
            "uncertainty": "",
        }
        self.assertEqual(parse_answer(json.dumps(base), "I feel relieved."), base)
        base["emotions"][0]["quote"] = "I feel proud."
        with self.assertRaises(ValueError):
            parse_answer(json.dumps(base), "I feel relieved.")
        base["emotions"][0]["quote"] = "I feel relieved."
        base["emotions"][0]["time_scope"] = ""
        with self.assertRaises(ValueError):
            parse_answer(json.dumps(base), "I feel relieved.")

    def test_missing_or_drifted_source_is_rejected_before_provider(self):
        with self.assertRaises(ValueError):
            select_source_only(b"{}")
        bound = (
            sum(x["input_chars"] for x in CAPS.values()) * 0.30
            + sum(x["output_chars"] for x in CAPS.values()) * 1.20
        ) / 1_000_000
        self.assertLessEqual(bound, COST_CAP_USD)
        self.assertEqual(sum(x["calls"] for x in CAPS.values()), 40)


if __name__ == "__main__":
    unittest.main()
