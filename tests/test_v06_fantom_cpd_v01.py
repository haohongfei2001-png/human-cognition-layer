"""Provider-free tests for the bounded v0.6 FANToM C/P/D utility harness."""

from __future__ import annotations

import json
import unittest

import pandas as pd

from scripts.prepare_v06_fantom_cpd_v01 import candidates_for_row
from scripts.run_v06_fantom_cpd_v01 import build_task, evaluate_one, score_response


class FakeBackend:
    def __init__(self, *, text_outputs=(), json_outputs=()):
        self.text_outputs = list(text_outputs)
        self.json_outputs = list(json_outputs)
        self.calls = []

    def complete(self, messages, *, max_tokens, temperature=0.0):
        self.calls.append(("text", messages))
        if not self.text_outputs:
            raise AssertionError("unexpected text call")
        return self.text_outputs.pop(0)

    def complete_json(self, messages, *, max_tokens, temperature=0.0):
        self.calls.append(("json", messages))
        if not self.json_outputs:
            raise AssertionError("unexpected json call")
        return self.json_outputs.pop(0)


class V06FantomCPDTests(unittest.TestCase):
    def test_binary_selection_targets_real_inaccessible_no_case(self):
        row = pd.Series({
            "set_id": "9-0-0",
            "answerabilityQAs_binary": [
                {"question": "Does Ana know?", "correct_answer": "yes"},
                {"question": "Does Bo know?", "correct_answer": "no"},
                {"question": "Does Ghost know?", "correct_answer": "no:long"},
            ],
        })
        out = candidates_for_row(row, "answerability_full_inaccessible_binary")
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["family"], "answerability_binary")

    def test_belief_task_orientation_and_scoring(self):
        record = {
            "family": "belief_mc",
            "question": "What does Ana believe?",
            "correct_answer": "red",
            "wrong_answer": "blue",
        }
        manifest = {
            "family": "belief_mc",
            "correct_option": "B",
        }
        task = build_task(record, manifest)
        self.assertIn("[A] blue", task)
        self.assertIn("[B] red", task)
        self.assertTrue(
            score_response("[B]", record=record, manifest=manifest)["correct"]
        )

    def test_d_adapter_never_receives_question_or_gold(self):
        context = "\n".join([
            "Ana: The code is 4312.",
            "Bo: I have to leave.",
            "Ana: The backup code is 7788.",
            "Bo: I am back.",
        ])
        record = {
            "family": "answerability_binary",
            "context": context,
            "question": "Does Bo know the backup code?",
            "target": "What is the backup code?",
            "correct_answer": "no",
            "set_id": "12-0-0",
        }
        manifest = {
            "question_id": "qid",
            "conversation_id": "12",
            "set_id": "12-0-0",
            "stratum": "answerability_full_inaccessible_binary",
            "family": "answerability_binary",
        }
        access = json.dumps({
            "turn_access": [
                {"turn_index": 0, "heard_by_agent_ids": ["Bo"]},
                {"turn_index": 1, "heard_by_agent_ids": ["Ana"]},
                {"turn_index": 2, "heard_by_agent_ids": []},
                {"turn_index": 3, "heard_by_agent_ids": ["Ana"]},
            ]
        })
        c = FakeBackend(text_outputs=["yes"])
        p = FakeBackend(text_outputs=["no"])
        adapter = FakeBackend(json_outputs=[access])
        d = FakeBackend(text_outputs=["no"])

        result = evaluate_one(
            manifest=manifest,
            record=record,
            c_backend=c,
            p_backend=p,
            d_adapter_backend=adapter,
            d_answer_backend=d,
        )
        self.assertFalse(result["arms"]["C"]["correct"])
        self.assertTrue(result["arms"]["P"]["correct"])
        self.assertTrue(result["arms"]["D"]["correct"])

        adapter_payload = adapter.calls[0][1][1]["content"]
        self.assertNotIn(record["question"], adapter_payload)
        self.assertNotIn(record["target"], adapter_payload)
        self.assertNotIn(record["correct_answer"], adapter_payload)

    def test_d_answer_does_not_receive_omniscient_full_context_string(self):
        context = "Ana: secret one.\nBo: hello."
        record = {
            "family": "info_accessibility_binary",
            "context": context,
            "question": "Does Bo know this information?",
            "information_question": "What is the secret?",
            "information_answer": "secret one",
            "correct_answer": "no",
            "set_id": "1-0-0",
        }
        manifest = {
            "question_id": "qid2",
            "conversation_id": "1",
            "set_id": "1-0-0",
            "stratum": "info_accessibility_full_inaccessible_binary",
            "family": "info_accessibility_binary",
        }
        access = json.dumps({
            "turn_access": [
                {"turn_index": 0, "heard_by_agent_ids": []},
                {"turn_index": 1, "heard_by_agent_ids": ["Ana"]},
            ]
        })
        d = FakeBackend(text_outputs=["no"])
        evaluate_one(
            manifest=manifest,
            record=record,
            c_backend=FakeBackend(text_outputs=["no"]),
            p_backend=FakeBackend(text_outputs=["no"]),
            d_adapter_backend=FakeBackend(json_outputs=[access]),
            d_answer_backend=d,
        )
        d_user = d.calls[0][1][1]["content"]
        self.assertNotIn("Conversation:\n" + context, d_user)
        payload = json.loads(d_user)
        self.assertIn("hcl_perspective_state", payload)
        self.assertIn("task", payload)


if __name__ == "__main__":
    unittest.main()
