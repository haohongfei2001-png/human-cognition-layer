"""Provider-free freshness and fairness guards for long-horizon v0.2."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from scripts.run_v04_long_horizon_bounded_context_v01 import (
    MeteredBackend,
    event_from_mapping,
    event_prompt_payload,
    ordinary_query_context,
    run_c_stream,
    run_d_stream,
    run_e_stream,
    score_rows,
)
from scripts.run_v04_long_horizon_bounded_context_v02 import load_and_validate_v02


class FakeBackend:
    def __init__(self):
        self.calls = []

    def complete(self, messages, *, max_tokens, temperature=0.0):
        self.calls.append(("text", messages))
        return "Compact ordinary memory: preserve explicit perspective and stance evidence."

    def complete_json(self, messages, *, max_tokens, temperature=0.0):
        self.calls.append(("json", messages))
        system = str(messages[0]["content"])
        if "semantic proposal stage of HCL v0.4" in system:
            return json.dumps({"propositions": [], "assertions": []})
        task = json.loads(messages[-1]["content"])
        return json.dumps({"label": task["allowed_labels"][0]})


class LongHorizonV02Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        (
            cls.fixture,
            cls.gold,
            cls.fixture_sha,
            cls.gold_sha,
        ) = load_and_validate_v02(
            "eval/v04/long_horizon_bounded_context_v02_fixture.json",
            "eval/v04/long_horizon_bounded_context_v02_gold.json",
        )
        cls.v01 = json.loads(
            Path("eval/v04/long_horizon_bounded_context_v01_fixture.json").read_text(
                encoding="utf-8"
            )
        )

    def test_fresh_package_shape_and_gold_separation(self):
        self.assertEqual(len(self.fixture["streams"]), 3)
        self.assertEqual(
            sum(len(stream["events"]) for stream in self.fixture["streams"]), 240
        )
        self.assertEqual(
            sum(len(stream["queries"]) for stream in self.fixture["streams"]), 18
        )
        self.assertEqual(self.fixture["query_context_char_budget"], 8000)
        self.assertEqual(self.fixture["ordinary_memory_char_budget"], 6000)
        serialized = json.dumps(self.fixture, ensure_ascii=False, sort_keys=True)
        self.assertNotIn('"gold"', serialized)
        self.assertNotIn('"risk_class"', serialized)
        self.assertEqual(len(self.fixture_sha), 64)
        self.assertEqual(len(self.gold_sha), 64)

    def test_v02_identifiers_and_primary_text_are_independent_of_v01(self):
        v01_event_ids = {
            event["event_id"]
            for stream in self.v01["streams"]
            for event in stream["events"]
        }
        v02_event_ids = {
            event["event_id"]
            for stream in self.fixture["streams"]
            for event in stream["events"]
        }
        self.assertTrue(v01_event_ids.isdisjoint(v02_event_ids))

        v01_query_ids = {
            query["query_id"]
            for stream in self.v01["streams"]
            for query in stream["queries"]
        }
        v02_query_ids = {
            query["query_id"]
            for stream in self.fixture["streams"]
            for query in stream["queries"]
        }
        self.assertTrue(v01_query_ids.isdisjoint(v02_query_ids))

        v01_primary = {
            event["raw_text"]
            for stream in self.v01["streams"]
            for event in stream["events"]
            if (event.get("metadata") or {}).get("track") == "primary"
        }
        v02_primary = {
            event["raw_text"]
            for stream in self.fixture["streams"]
            for event in stream["events"]
            if (event.get("metadata") or {}).get("track") == "primary"
        }
        self.assertTrue(v01_primary.isdisjoint(v02_primary))

    def test_harness_annotations_are_hidden_in_v02(self):
        event = self.fixture["streams"][0]["events"][0]
        self.assertIn("track", event["metadata"])
        self.assertIn("sequence", event["metadata"])
        prompt = event_prompt_payload(event)
        mapped = event_from_mapping(event)
        self.assertNotIn("track", prompt["metadata"])
        self.assertNotIn("sequence", prompt["metadata"])
        self.assertNotIn("track", mapped.metadata)
        self.assertNotIn("sequence", mapped.metadata)

    def test_ordinary_retrieval_respects_shared_budget(self):
        stream = self.fixture["streams"][0]
        query = stream["queries"][-1]
        payload, size = ordinary_query_context(
            "m" * 5800,
            stream["events"],
            query,
            query_char_budget=self.fixture["query_context_char_budget"],
        )
        self.assertLessEqual(size, 8000)
        self.assertTrue(payload["supporting_events"])
        serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        self.assertNotIn('"track"', serialized)
        self.assertNotIn('"sequence"', serialized)

    def test_provider_free_all_arms_preserve_diagnostic_evidence(self):
        stream = self.fixture["streams"][0]

        c_rows = run_c_stream(stream, MeteredBackend(FakeBackend()))
        d_rows = run_d_stream(
            stream,
            MeteredBackend(FakeBackend()),
            query_char_budget=self.fixture["query_context_char_budget"],
        )
        e_rows = run_e_stream(
            stream,
            MeteredBackend(FakeBackend()),
            query_char_budget=self.fixture["query_context_char_budget"],
            memory_char_budget=self.fixture["ordinary_memory_char_budget"],
        )

        self.assertEqual(len(c_rows), 6)
        self.assertEqual(len(d_rows), 6)
        self.assertEqual(len(e_rows), 6)
        self.assertTrue(all("query_context" in row for row in c_rows))
        self.assertTrue(all("query_context" in row for row in d_rows))
        self.assertTrue(all("persistent_state" in row for row in d_rows))
        self.assertTrue(all("state_chars" in row for row in d_rows))
        self.assertTrue(all("query_context" in row for row in e_rows))
        self.assertTrue(all("memory_chars" in row for row in e_rows))
        for rows in (c_rows, d_rows, e_rows):
            self.assertTrue(all("query_elapsed_seconds" in row for row in rows))

    def test_scoring_is_posthoc(self):
        query_id = "s4-q1"
        rows = [{
            "stream": "s4",
            "query_id": query_id,
            "prediction": "NORTH",
            "query_context_chars": 100,
        }]
        before = json.loads(json.dumps(rows))
        scored = score_rows(rows, self.gold)
        self.assertEqual(rows, before)
        self.assertEqual(scored["correct"], 1)
        self.assertEqual(scored["rows"][0]["gold"], "NORTH")


if __name__ == "__main__":
    unittest.main()
