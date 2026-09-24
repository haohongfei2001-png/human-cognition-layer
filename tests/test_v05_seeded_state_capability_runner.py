"""Provider-free guards for HCL v0.5 seeded state capability pilot."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from scripts.run_v04_long_horizon_bounded_context_v01 import MeteredBackend
from scripts.run_v05_seeded_state_capability_v01 import (
    MEMORY_SYSTEM,
    ordinary_query_context,
    run_d_stream,
    score_rows,
    update_memory,
    validate_fixture,
)


class FakeBackend:
    def __init__(self, json_outputs=None, text_outputs=None):
        self.json_outputs = list(json_outputs or [])
        self.text_outputs = list(text_outputs or [])
        self.json_calls = []
        self.text_calls = []

    def complete_json(self, messages, *, max_tokens, temperature=0.0):
        self.json_calls.append(messages)
        if not self.json_outputs:
            raise AssertionError("unexpected json call")
        return self.json_outputs.pop(0)

    def complete(self, messages, *, max_tokens, temperature=0.0):
        self.text_calls.append(messages)
        if not self.text_outputs:
            raise AssertionError("unexpected text call")
        return self.text_outputs.pop(0)


class SeededStateCapabilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = json.loads(
            Path("eval/v05/seeded_state_capability_v01_fixture.json").read_text()
        )
        cls.gold = json.loads(
            Path("eval/v05/seeded_state_capability_v01_gold.json").read_text()
        )

    def test_frozen_shape_and_gold_separation(self):
        validate_fixture(self.fixture, self.gold)
        self.assertEqual(len(self.fixture["streams"]), 3)
        self.assertEqual(
            sum(len(s["events"]) for s in self.fixture["streams"]), 216
        )
        self.assertEqual(
            sum(len(s["queries"]) for s in self.fixture["streams"]), 24
        )
        serialized = json.dumps(self.fixture, sort_keys=True)
        self.assertNotIn('"gold"', serialized)
        self.assertNotIn('"risk_class"', serialized)

    def test_fresh_primary_texts_are_disjoint_from_consumed_v04_v02(self):
        prior = json.loads(
            Path(
                "eval/v04/long_horizon_bounded_context_v02_fixture.json"
            ).read_text()
        )
        old_texts = {
            event["raw_text"]
            for stream in prior["streams"]
            for event in stream["events"]
        }
        new_texts = {
            event["raw_text"]
            for stream in self.fixture["streams"]
            for event in stream["events"]
        }
        self.assertFalse(old_texts & new_texts)

    def test_d_uses_seeded_catalog_and_no_query_model_call(self):
        mini = {
            "ontology_seed": {
                "route_assignment": ["RED", "BLUE", "GREEN"],
                "noise_issue": ["LOW", "MID", "HIGH"],
            },
            "target_agent_id": "ari",
            "target_issue_key": "route_assignment",
            "events": [
                {
                    "event_id": "m-e1",
                    "valid_time": "2026-01-01T10:00:00+00:00",
                    "recorded_at": "2026-01-01T10:00:01+00:00",
                    "raw_text": "Source tells Ari: RED is the route.",
                    "source_id": "source",
                    "actor_id": "source",
                    "observer_ids": [],
                    "recipient_ids": ["ari"],
                    "metadata": {},
                },
                {
                    "event_id": "m-e2",
                    "valid_time": "2026-01-01T10:01:00+00:00",
                    "recorded_at": "2026-01-01T10:01:01+00:00",
                    "raw_text": "Ari says: I accept RED as the route.",
                    "source_id": "ari",
                    "actor_id": "ari",
                    "observer_ids": [],
                    "recipient_ids": [],
                    "metadata": {},
                },
            ],
            "queries": [
                {
                    "query_id": "m-q1",
                    "after_event": 2,
                    "target_agent_id": "ari",
                    "target_issue_key": "route_assignment",
                    "allowed_labels": ["RED", "BLUE", "GREEN", "UNCERTAIN"],
                    "question": "Which route does Ari believe?",
                }
            ],
        }
        fake = FakeBackend(
            json_outputs=[
                json.dumps(
                    {"self_stances": [], "revision_relations": []}
                ),
                json.dumps(
                    {
                        "self_stances": [
                            {
                                "issue_key": "route_assignment",
                                "signal": "AFFIRM",
                                "value_key": "RED",
                            }
                        ],
                        "revision_relations": [],
                    }
                ),
            ]
        )
        metered = MeteredBackend(fake)
        rows = run_d_stream(mini, metered)
        self.assertEqual(rows[0]["prediction"], "RED")
        self.assertEqual(metered.calls, 2)
        self.assertEqual(metered.json_calls, 2)
        prompt = json.loads(fake.json_calls[0][-1]["content"])
        self.assertEqual(
            prompt["known_issue_value_catalog"],
            mini["ontology_seed"],
        )

    def test_e_memory_is_free_form_but_receives_same_ontology(self):
        ontology = {
            "route_assignment": ["RED", "BLUE", "GREEN"],
            "noise_issue": ["LOW", "MID", "HIGH"],
        }
        event = {
            "event_id": "e1",
            "valid_time": "2026-01-01T10:00:00+00:00",
            "recorded_at": "2026-01-01T10:00:01+00:00",
            "raw_text": "Ari says: I accept RED as the route.",
            "source_id": "ari",
            "actor_id": "ari",
            "observer_ids": [],
            "recipient_ids": [],
            "metadata": {},
        }
        fake = FakeBackend(text_outputs=["Ari currently accepts RED."])
        metered = MeteredBackend(fake)
        memory, repaired = update_memory(
            metered,
            "",
            event,
            ontology,
            memory_char_budget=6000,
        )
        self.assertEqual(repaired, 0)
        self.assertIn("RED", memory)
        prompt = json.loads(fake.text_calls[0][-1]["content"])
        self.assertEqual(prompt["frozen_issue_value_ontology"], ontology)
        self.assertNotIn("PROPOSITION_REVISION", MEMORY_SYSTEM)
        self.assertNotIn("BELIEF_ESTIMATE", MEMORY_SYSTEM)

    def test_e_query_context_obeys_same_budget_and_carries_ontology(self):
        stream = self.fixture["streams"][0]
        query = stream["queries"][0]
        context, size = ordinary_query_context(
            "compact memory",
            stream["events"],
            query,
            stream["ontology_seed"],
            query_char_budget=self.fixture["query_context_char_budget"],
        )
        self.assertLessEqual(size, self.fixture["query_context_char_budget"])
        self.assertEqual(
            context["frozen_issue_value_ontology"],
            stream["ontology_seed"],
        )

    def test_scoring_is_posthoc(self):
        query_id = next(iter(self.gold["labels"]))
        prediction = self.gold["labels"][query_id]["gold"]
        rows = [{"query_id": query_id, "prediction": prediction}]
        before = json.loads(json.dumps(rows))
        scored = score_rows(rows, self.gold)
        self.assertEqual(rows, before)
        self.assertEqual(scored["correct"], 1)

    def test_query_allowed_labels_are_seeded_target_values_plus_uncertain(self):
        for stream in self.fixture["streams"]:
            values = stream["ontology_seed"][stream["target_issue_key"]]
            for query in stream["queries"]:
                self.assertEqual(
                    query["allowed_labels"],
                    values + ["UNCERTAIN"],
                )


if __name__ == "__main__":
    unittest.main()
