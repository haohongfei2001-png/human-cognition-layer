"""Provider-free checks for the external paired efficacy boundary."""

import json
import unittest

from scripts.longmemeval_cdg_v01 import (
    GenericMemory,
    IngestionReceipt,
    ProtocolError,
    answer_packet,
    arm_messages,
)
from scripts.qualify_longmemeval_knowledge_update_v01 import (
    events_from_state_view,
    history_digest,
    state_input_view,
)


def sample_row():
    return {
        "question_id": "synthetic_abs", "question_type": "knowledge-update",
        "question": "What is the current delivery day?", "answer": "Tuesday",
        "answer_session_ids": ["later"],
        "haystack_session_ids": ["later", "earlier"],
        "haystack_dates": ["2025/01/08 (Wed) 12:00", "2025/01/01 (Wed) 12:00"],
        "haystack_sessions": [
            [{"role": "user", "content": "Delivery day is Tuesday", "has_answer": True}],
            [{"role": "user", "content": "Delivery used to be Monday"}],
        ],
    }


class FakeBackend:
    def __init__(self, outputs):
        self.outputs = iter(outputs)
        self.calls = 0

    def complete_json(self, messages, *, max_tokens, temperature):
        self.calls += 1
        assert "answer_session_ids" not in json.dumps(messages)
        assert '"question"' not in json.dumps(messages)
        return json.dumps(next(self.outputs))


class CDGProviderFreeTests(unittest.TestCase):
    def test_oracle_release_requires_both_ingests_and_scrubs_labels(self):
        row = sample_row()
        view = state_input_view(row)
        events = events_from_state_view(view, id_prefix="synthetic")
        self.assertEqual(len(events), 2)
        self.assertEqual(view["history"][0]["session_id"], "earlier")
        with self.assertRaisesRegex(ProtocolError, "G ingestion"):
            answer_packet(row, IngestionReceipt(history_digest(view), 2, 1, 2))
        packet = answer_packet(row, IngestionReceipt(history_digest(view), 2, 2, 2))
        self.assertEqual([x["session_id"] for x in packet["evidence"]], ["later"])
        self.assertNotIn("has_answer", json.dumps(packet))
        self.assertNotIn('"answer"', json.dumps(packet))
        c = arm_messages(packet)
        d = arm_messages(packet, {"records": ["derived"]})
        self.assertEqual(c, d[:2])
        self.assertIn("derived", d[2]["content"])

    def test_generic_budget_compacts_without_discarding_update(self):
        backend = FakeBackend([
            {"upserts": [{"entity": "user", "attribute": "delivery day", "value": "Monday", "note": "a" * 220}]},
            {"upserts": [{"entity": "user", "attribute": "delivery day", "value": "Tuesday", "note": "b" * 220}]},
        ])
        memory = GenericMemory(backend, state_char_limit=300)
        event = {"event_id": "e1", "valid_time": "2025-01-01T00:00:00+00:00",
                 "recorded_at": "2025-01-01T00:00:01+00:00", "source_id": "user",
                 "actor_id": "user", "observer_ids": [], "recipient_ids": ["assistant"],
                 "raw_text": "Delivery day is Monday", "metadata": {}}
        memory.ingest(event)
        event = dict(event, event_id="e2", valid_time="2025-01-02T00:00:00+00:00",
                     raw_text="Delivery day is Tuesday")
        memory.ingest(event)
        self.assertEqual(memory.processed_events, 2)
        self.assertEqual(memory.state["records"][0]["value"], "Tuesday")
        self.assertLessEqual(len(json.dumps(memory.state, ensure_ascii=False, sort_keys=True, separators=(",", ":"))), 300)

    def test_generic_terminal_budget_failure_is_not_silent(self):
        backend = FakeBackend([{ "upserts": [{"entity": "e", "attribute": "a",
                                               "value": "x" * 900, "note": "source"}]}])
        memory = GenericMemory(backend, state_char_limit=300)
        event = {"event_id": "e1", "valid_time": "2025-01-01T00:00:00+00:00",
                 "recorded_at": "2025-01-01T00:00:01+00:00", "source_id": "user",
                 "actor_id": "user", "observer_ids": [], "recipient_ids": [],
                 "raw_text": "A long field", "metadata": {}}
        with self.assertRaisesRegex(ProtocolError, "active generic records"):
            memory.ingest(event)
        self.assertEqual(memory.processed_events, 0)
        self.assertEqual(memory.state, {"records": []})


if __name__ == "__main__":
    unittest.main()
