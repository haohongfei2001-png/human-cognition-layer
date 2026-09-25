"""Provider-free tests for LongMemEval EQ-02 qualification."""

from __future__ import annotations

import json
import unittest

from scripts.qualify_longmemeval_knowledge_update_v01 import (
    events_from_state_view,
    selection_rank,
    state_input_view,
    assert_state_firewall,
)


class LongMemEvalQualificationTests(unittest.TestCase):
    def synthetic_row(self):
        return {
            "question_id": "q-sentinel",
            "question_type": "knowledge-update",
            "question": "QUESTION_SENTINEL_DO_NOT_INGEST",
            "answer": "ANSWER_SENTINEL_DO_NOT_INGEST",
            "question_date": "2023/05/22 (Mon) 12:00",
            "answer_session_ids": ["answer-secret"],
            "haystack_session_ids": ["s-old", "s-new"],
            "haystack_dates": [
                "2023/05/20 (Sat) 09:10",
                "2023/05/21 (Sun) 10:20",
            ],
            "haystack_sessions": [
                [
                    {
                        "role": "user",
                        "content": "I prefer tea.",
                        "has_answer": True,
                    },
                    {"role": "assistant", "content": "Noted."},
                ],
                [
                    {
                        "role": "user",
                        "content": "I now prefer coffee instead of tea.",
                        "has_answer": True,
                    },
                    {"role": "assistant", "content": "Updated."},
                ],
            ],
        }

    def test_state_view_strips_gold_question_and_evidence_labels(self):
        row = self.synthetic_row()
        view = state_input_view(row)
        assert_state_firewall(row, view)
        material = json.dumps(view, sort_keys=True)
        self.assertNotIn("QUESTION_SENTINEL", material)
        self.assertNotIn("ANSWER_SENTINEL", material)
        self.assertNotIn("has_answer", material)
        self.assertNotIn("answer-secret", material)

    def test_event_conversion_preserves_roles_and_time_order(self):
        view = state_input_view(self.synthetic_row())
        events = events_from_state_view(view, id_prefix="fixture")
        self.assertEqual(len(events), 4)
        self.assertEqual(
            [event["actor_id"] for event in events],
            [
                "longmemeval_user",
                "longmemeval_assistant",
                "longmemeval_user",
                "longmemeval_assistant",
            ],
        )
        self.assertTrue(events[0]["valid_time"] < events[2]["valid_time"])
        self.assertEqual(
            events[0]["recipient_ids"], ["longmemeval_assistant"]
        )
        self.assertEqual(events[1]["recipient_ids"], ["longmemeval_user"])

    def test_selection_rank_is_deterministic_and_qid_only(self):
        a = selection_rank("question-123")
        b = selection_rank("question-123")
        c = selection_rank("question-124")
        self.assertEqual(a, b)
        self.assertNotEqual(a, c)

    def test_non_monotonic_sessions_fail_closed(self):
        row = self.synthetic_row()
        row["haystack_dates"] = list(reversed(row["haystack_dates"]))
        with self.assertRaises(ValueError):
            state_input_view(row)


if __name__ == "__main__":
    unittest.main()
