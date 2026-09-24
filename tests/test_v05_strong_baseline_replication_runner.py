"""Provider-free guards for the final HCL v0.5 strong-baseline replication."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from scripts.run_v04_long_horizon_bounded_context_v01 import MeteredBackend
from scripts.run_v05_strong_baseline_replication_v01 import (
    GENERIC_STATE_SYSTEM,
    GENERIC_REPAIR_SYSTEM,
    GenericStateError,
    generic_state_prediction,
    load_and_validate,
    score_rows,
    update_generic_state,
    validate_generic_state,
)


class FakeBackend:
    def __init__(self, outputs):
        self.outputs = list(outputs)
        self.calls = []

    def complete_json(self, messages, *, max_tokens, temperature=0.0):
        self.calls.append(messages)
        if not self.outputs:
            raise AssertionError("unexpected backend call")
        return self.outputs.pop(0)


class StrongBaselineReplicationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        (
            cls.fixture,
            cls.gold,
            cls.fixture_sha,
            cls.gold_sha,
        ) = load_and_validate(
            "eval/v05/strong_baseline_replication_v01_fixture.json",
            "eval/v05/strong_baseline_replication_v01_gold.json",
        )

    def test_shape_fairness_and_gold_separation(self):
        self.assertEqual(len(self.fixture["streams"]), 4)
        self.assertEqual(
            sum(len(s["events"]) for s in self.fixture["streams"]), 384
        )
        self.assertEqual(
            sum(len(s["queries"]) for s in self.fixture["streams"]), 48
        )
        self.assertEqual(self.fixture["query_context_char_budget"], 8000)
        self.assertEqual(self.fixture["persistent_state_char_budget"], 6000)
        serialized = json.dumps(self.fixture, sort_keys=True)
        self.assertNotIn('"gold"', serialized)
        self.assertNotIn('"risk_class"', serialized)
        self.assertEqual(len(self.fixture_sha), 64)
        self.assertEqual(len(self.gold_sha), 64)

    def test_queries_are_chronological_with_multi_agent_multi_issue_coverage(self):
        for stream in self.fixture["streams"]:
            afters = [int(q["after_event"]) for q in stream["queries"]]
            self.assertEqual(afters, sorted(afters))
            self.assertEqual(
                {q["target_agent_id"] for q in stream["queries"]},
                set(stream["target_agents"]),
            )
            self.assertEqual(
                {q["target_issue_key"] for q in stream["queries"]},
                set(stream["queried_issues"]),
            )

    def test_concrete_rows_are_disjoint_from_consumed_packages(self):
        prior_paths = [
            "eval/v04/long_horizon_bounded_context_v02_fixture.json",
            "eval/v05/seeded_state_capability_v01_fixture.json",
            "eval/v05/semantic_extraction_v01_fixture.json",
            "eval/v05/routed_semantic_extraction_v02_fixture.json",
        ]
        old_ids = set()
        old_texts = set()
        for path in prior_paths:
            payload = json.loads(Path(path).read_text(encoding="utf-8"))
            for stream in payload["streams"]:
                for event in stream["events"]:
                    old_ids.add(event["event_id"])
                    old_texts.add(event["raw_text"])
        new_ids = {
            event["event_id"]
            for stream in self.fixture["streams"]
            for event in stream["events"]
        }
        new_texts = {
            event["raw_text"]
            for stream in self.fixture["streams"]
            for event in stream["events"]
        }
        self.assertFalse(old_ids & new_ids)
        self.assertFalse(old_texts & new_texts)

    def test_generic_prompt_contains_no_hcl_specific_mechanism(self):
        combined = GENERIC_STATE_SYSTEM + "\n" + GENERIC_REPAIR_SYSTEM
        for forbidden in (
            "REVISION_EXPOSURE",
            "BELIEF_ESTIMATE",
            "PROPOSITION_REVISION",
            "suspended_value",
            "CurrentStance",
            "HCL-specific transition",
        ):
            self.assertNotIn(forbidden, combined)

    def test_generic_state_receives_same_seeded_ontology(self):
        ontology = {
            "route": ["RED", "BLUE", "GREEN"],
            "mode": ["LOW", "MID", "HIGH"],
        }
        valid_state = {
            "agents": {
                "ari": {
                    "route": {
                        "current_label": "RED",
                        "rejected_values": [],
                        "history": [
                            {
                                "valid_time": "2026-01-01T10:00:00+00:00",
                                "label": "RED",
                                "note": "explicit acceptance",
                            }
                        ],
                    }
                }
            }
        }
        fake = FakeBackend([json.dumps(valid_state)])
        metered = MeteredBackend(fake)
        state, repaired = update_generic_state(
            metered,
            {"agents": {}},
            {
                "event_id": "e1",
                "valid_time": "2026-01-01T10:00:00+00:00",
                "recorded_at": "2026-01-01T10:00:01+00:00",
                "raw_text": "Ari says: I accept RED.",
                "source_id": "ari",
                "actor_id": "ari",
                "observer_ids": [],
                "recipient_ids": [],
                "metadata": {},
            },
            ontology,
            state_char_limit=6000,
        )
        self.assertEqual(repaired, 0)
        self.assertEqual(state, valid_state)
        payload = json.loads(fake.calls[0][-1]["content"])
        self.assertEqual(payload["frozen_issue_value_ontology"], ontology)

    def test_generic_state_historical_readout_does_not_use_current_label(self):
        state = {
            "agents": {
                "ari": {
                    "route": {
                        "current_label": "GREEN",
                        "rejected_values": [],
                        "history": [
                            {
                                "valid_time": "2026-01-01T10:00:00+00:00",
                                "label": "RED",
                                "note": "initial",
                            },
                            {
                                "valid_time": "2026-01-01T11:00:00+00:00",
                                "label": "BLUE",
                                "note": "changed",
                            },
                            {
                                "valid_time": "2026-01-01T12:00:00+00:00",
                                "label": "GREEN",
                                "note": "later",
                            },
                        ],
                    }
                }
            }
        }
        query = {
            "target_agent_id": "ari",
            "target_issue_key": "route",
            "allowed_labels": ["RED", "BLUE", "GREEN", "UNCERTAIN"],
            "event_time": "2026-01-01T11:30:00+00:00",
        }
        self.assertEqual(generic_state_prediction(state, query), "BLUE")
        current = dict(query)
        current.pop("event_time")
        self.assertEqual(generic_state_prediction(state, current), "GREEN")

    def test_generic_state_schema_fails_closed(self):
        ontology = {"route": ["RED", "BLUE", "GREEN"]}
        invalid = {
            "agents": {
                "ari": {
                    "route": {
                        "current_label": "PURPLE",
                        "rejected_values": [],
                        "history": [],
                    }
                }
            }
        }
        with self.assertRaises(GenericStateError):
            validate_generic_state(invalid, ontology, state_char_limit=6000)

    def test_generic_state_one_repair_then_success(self):
        ontology = {"route": ["RED", "BLUE", "GREEN"]}
        repaired = {
            "agents": {
                "ari": {
                    "route": {
                        "current_label": "RED",
                        "rejected_values": [],
                        "history": [
                            {
                                "valid_time": "2026-01-01T10:00:00+00:00",
                                "label": "RED",
                                "note": "accepted",
                            }
                        ],
                    }
                }
            }
        }
        fake = FakeBackend(
            [
                json.dumps({"agents": {"ari": {"route": {"current_label": "BAD"}}}}),
                json.dumps(repaired),
            ]
        )
        metered = MeteredBackend(fake)
        state, repair_count = update_generic_state(
            metered,
            {"agents": {}},
            {
                "event_id": "e1",
                "valid_time": "2026-01-01T10:00:00+00:00",
                "recorded_at": "2026-01-01T10:00:01+00:00",
                "raw_text": "Ari says: I accept RED.",
                "source_id": "ari",
                "actor_id": "ari",
                "observer_ids": [],
                "recipient_ids": [],
                "metadata": {},
            },
            ontology,
            state_char_limit=6000,
        )
        self.assertEqual(repair_count, 1)
        self.assertEqual(state, repaired)
        self.assertEqual(metered.calls, 2)

    def test_scoring_is_posthoc(self):
        query_id = next(iter(self.gold["labels"]))
        rows = [
            {
                "query_id": query_id,
                "prediction": self.gold["labels"][query_id]["gold"],
            }
        ]
        before = json.loads(json.dumps(rows))
        scored = score_rows(rows, self.gold)
        self.assertEqual(rows, before)
        self.assertEqual(scored["correct"], 1)

    def test_every_stream_has_eight_or_more_named_agents(self):
        for stream in self.fixture["streams"]:
            agents = set()
            for event in stream["events"]:
                if event.get("actor_id"):
                    agents.add(event["actor_id"])
                agents.update(event.get("recipient_ids") or [])
                agents.update(event.get("observer_ids") or [])
            self.assertGreaterEqual(len(agents), 8)


if __name__ == "__main__":
    unittest.main()
