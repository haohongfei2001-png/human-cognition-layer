from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from scripts.qualify_v06_perspective_belief_cq00 import (
    FANTOM_TARGETS,
    historical_fantom_conversations,
    inventory_dyntom,
    inventory_fantom,
)


class V06PerspectiveBeliefCQ00Tests(unittest.TestCase):
    def test_historical_fantom_exposure_is_exactly_80_conversations(self):
        self.assertEqual(len(historical_fantom_conversations()), 80)

    def test_fantom_selection_is_eight_disjoint_unconsumed_conversations(self):
        rows = []
        next_id = 1000

        for _ in range(FANTOM_TARGETS["belief_inaccessible_first"] + 2):
            rows.append({
                "set_id": f"{next_id}-0-0",
                "beliefQAs": [{
                    "question": "q",
                    "missed_info_accessibility": "inaccessible",
                    "tom_type": "first",
                }],
            })
            next_id += 1

        for _ in range(FANTOM_TARGETS["belief_inaccessible_second"] + 2):
            rows.append({
                "set_id": f"{next_id}-0-0",
                "beliefQAs": [{
                    "question": "q",
                    "missed_info_accessibility": "inaccessible",
                    "tom_type": "second",
                }],
            })
            next_id += 1

        for _ in range(FANTOM_TARGETS["answerability_full_inaccessible_binary"] + 2):
            rows.append({
                "set_id": f"{next_id}-0-0",
                "answerabilityQAs_binary": [{"question": "q", "correct_answer": "no"}],
            })
            next_id += 1

        for _ in range(FANTOM_TARGETS["info_accessibility_full_inaccessible_binary"] + 2):
            rows.append({
                "set_id": f"{next_id}-0-0",
                "infoAccessibilityQAs_binary": [{"question": "q", "correct_answer": "no"}],
            })
            next_id += 1

        result = inventory_fantom(pd.DataFrame(rows))
        selected = result["selected_development_conversations"]
        ids = [x["conversation_id"] for x in selected]
        self.assertEqual(len(selected), 8)
        self.assertEqual(len(set(ids)), 8)
        self.assertEqual(result["historical_consumed_conversations"], 80)

    def test_dyntom_reserves_four_audit_and_eight_development_trials(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            data = root / "data" / "script" / "data"
            data.mkdir(parents=True)

            for i in range(20):
                trial = data / f"trial{i + 2000}"
                trial.mkdir()
                (trial / "story.json").write_text(
                    json.dumps({
                        "main character": "A",
                        "scenario numbers": 3,
                        "story": {"scenario 1": "x", "scenario 2": "y", "scenario 3": "z"},
                        "sketch": {"hidden": True},
                    }),
                    encoding="utf-8",
                )
                (trial / "question_new.json").write_text(
                    json.dumps({
                        "a": {
                            "question": "What is the belief of A in scenario 1?",
                            "true answer": "a",
                            "options": ["a. x", "b. y"],
                            "question type": "type_a",
                        },
                        "d": {
                            "question": "How does the belief of A change across the scenarios?",
                            "true answer": "a",
                            "options": ["a. x", "b. y"],
                            "question type": "type_d",
                        },
                    }),
                    encoding="utf-8",
                )

            result = inventory_dyntom(root)
            audit = {x["trial_id"] for x in result["narrative_sufficiency_audit_trials"]}
            dev = {x["trial_id"] for x in result["development_trials_reserved_after_audit"]}
            self.assertEqual(len(audit), 4)
            self.assertEqual(len(dev), 8)
            self.assertFalse(audit & dev)
            self.assertEqual(result["provider_calls"], 0)


if __name__ == "__main__":
    unittest.main()
