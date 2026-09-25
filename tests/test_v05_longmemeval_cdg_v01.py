"""Provider-free checks for the external paired efficacy boundary."""

import json
import unittest
from unittest.mock import patch

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
from scripts.preflight_v05_longmemeval_cdg_v01 import validate_manifest
from scripts.run_v05_longmemeval_cdg_v01 import run_one
from scripts.score_v05_longmemeval_cdg_v01 import score_one, validate_answers, JudgeError
from scripts.summarize_v05_longmemeval_cdg_v01 import exact_mcnemar_p, paired_bootstrap_interval


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


class FakeAnswerBackend:
    def __init__(self):
        self.messages = None

    def complete(self, messages, *, max_tokens, temperature):
        self.messages = messages
        return "Tuesday"


class FakeJudgeClient:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.prompts = []
        self.chat = self
        self.completions = self

    def create(self, **kwargs):
        self.prompts.append(kwargs)
        message = type("Message", (), {"content": next(self.responses)})()
        choice = type("Choice", (), {"message": message})()
        return type("Completion", (), {"choices": [choice]})()


class CDGProviderFreeTests(unittest.TestCase):
    def test_sealed_manifest_hashes_are_complete_and_disjoint(self):
        _, selected = validate_manifest()
        self.assertEqual(len(selected), 32)
        self.assertEqual(sum(x["question_id"].endswith("_abs") for x in selected), 2)

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
        self.assertGreaterEqual(memory.compacted_updates, 1)
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

    def test_generic_invalid_patch_has_one_bounded_repair(self):
        backend = FakeBackend([
            {"invalid": True},
            {"upserts": [{"entity": "user", "attribute": "day", "value": "Tuesday", "note": "explicit"}]},
        ])
        memory = GenericMemory(backend)
        event = {"event_id": "e1", "valid_time": "2025-01-01T00:00:00+00:00",
                 "recorded_at": "2025-01-01T00:00:01+00:00", "source_id": "user",
                 "actor_id": "user", "observer_ids": [], "recipient_ids": [],
                 "raw_text": "Tuesday", "metadata": {}}
        memory.ingest(event)
        self.assertEqual(memory.repair_calls, 1)
        self.assertEqual(memory.processed_events, 1)
        self.assertEqual(backend.calls, 2)

    def test_answers_share_evidence_after_both_ingests(self):
        row = sample_row()
        backends = {arm: FakeAnswerBackend() for arm in ("C", "D", "G")}
        def d_state(events, backend):
            self.assertIs(backend, backends["D"])
            return [{"d": "pre-question"}], {"events": len(events)}
        def g_state(events, backend):
            self.assertIs(backend, backends["G"])
            return {"records": []}, {"events": len(events)}
        with patch("scripts.run_v05_longmemeval_cdg_v01._state_from_d", side_effect=d_state), \
             patch("scripts.run_v05_longmemeval_cdg_v01._state_from_g", side_effect=g_state):
            checkpoints = []
            result = run_one(row, history_digest(state_input_view(row)), backends,
                             on_progress=lambda item: checkpoints.append(item))
        self.assertEqual(result["answers"], {"C": "Tuesday", "D": "Tuesday", "G": "Tuesday"})
        self.assertEqual(backends["C"].messages, backends["D"].messages[:2])
        self.assertEqual(backends["C"].messages, backends["G"].messages[:2])
        self.assertEqual([list(x["answers"]) for x in checkpoints],
                         [["C"], ["C", "D"], ["C", "D", "G"]])

    def test_scoring_uses_pinned_shape_and_flags_ambiguous_reply(self):
        client = FakeJudgeClient(["yes", "No", "maybe yes"])
        def prompt(task, question, answer, response, abstention=False):
            self.assertEqual(task, "knowledge-update")
            self.assertTrue(abstention)
            return f"{question}|{answer}|{response}"
        result = score_one("Q", "A", "sample_abs", {"C": "c", "D": "d", "G": "g"}, prompt, client)
        self.assertEqual([result[x]["label"] for x in ("C", "D", "G")], [True, False, True])
        self.assertTrue(result["G"]["ambiguous"])
        self.assertTrue(all(x["model"] == "gpt-4o-2024-08-06" and x["temperature"] == 0 for x in client.prompts))
        checkpoints = []
        score_one("Q", "A", "sample_abs", {"C": "c", "D": "d", "G": "g"},
                  prompt, FakeJudgeClient(["yes", "no", "yes"]),
                  on_progress=lambda arm, item: checkpoints.append((arm, item["raw_response"])))
        self.assertEqual([x[0] for x in checkpoints], ["C", "D", "G"])

    def test_incomplete_raw_answers_cannot_be_judged(self):
        with self.assertRaisesRegex(JudgeError, "not complete"):
            validate_answers({"format": "hcl-v05-longmemeval-cdg-answers-v01",
                              "status": "failed_partial_consumed"}, [])

    def test_paired_statistics_are_exact_and_deterministic(self):
        self.assertEqual(exact_mcnemar_p(0, 0), 1.0)
        self.assertEqual(exact_mcnemar_p(5, 0), 0.0625)
        self.assertEqual(exact_mcnemar_p(6, 0), 0.03125)
        first = paired_bootstrap_interval([1, 1, 0, -1])
        self.assertEqual(first, paired_bootstrap_interval([1, 1, 0, -1]))
        self.assertLessEqual(first[0], first[1])


if __name__ == "__main__":
    unittest.main()
