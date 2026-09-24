"""Provider-free guards for HCL v0.5 semantic extraction pilot."""

from __future__ import annotations

import json
import unittest

from scripts.run_v05_semantic_extraction_v01 import (
    MeteredBackend,
    event_from_mapping,
    extract_rows,
    load_and_validate,
    score_rows,
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


class V05SemanticExtractionPilotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        (
            cls.fixture,
            cls.gold,
            cls.fixture_sha,
            cls.gold_sha,
        ) = load_and_validate(
            "eval/v05/semantic_extraction_v01_fixture.json",
            "eval/v05/semantic_extraction_v01_gold.json",
        )

    def test_frozen_shape_gold_separation_and_trust_rules(self):
        self.assertEqual(len(self.fixture["streams"]), 3)
        self.assertEqual(
            sum(len(stream["events"]) for stream in self.fixture["streams"]),
            36,
        )
        self.assertEqual(
            sum(len(row["signals"]) for row in self.gold["rows"].values()),
            36,
        )
        text = json.dumps(self.fixture, sort_keys=True)
        self.assertNotIn('"risk_class"', text)
        self.assertNotIn('"signals"', text)
        self.assertEqual(len(self.fixture_sha), 64)
        self.assertEqual(len(self.gold_sha), 64)

    def test_gold_is_not_in_model_prompt_and_catalog_seed_is(self):
        stream = self.fixture["streams"][0]
        event = stream["events"][1]
        expected = self.gold["rows"][event["event_id"]]["signals"]
        backend = MeteredBackend(FakeBackend([json.dumps({"stance_events": expected})]))
        mini = {
            "format": self.fixture["format"],
            "streams": [
                {
                    "id": stream["id"],
                    "catalog_seed": stream["catalog_seed"],
                    "events": [event],
                }
            ],
        }
        rows = extract_rows(mini, backend)
        self.assertEqual(len(rows), 1)
        call = backend.backend.calls[0]
        prompt = "\n".join(str(message["content"]) for message in call)
        self.assertNotIn("risk_class", prompt)
        self.assertNotIn('"expected"', prompt)
        self.assertNotIn(self.gold["rows"][event["event_id"]]["risk_class"], prompt)
        user_payload = json.loads(call[-1]["content"])
        self.assertEqual(
            user_payload["known_issue_value_catalog"],
            stream["catalog_seed"],
        )

    def test_scoring_is_posthoc_and_does_not_mutate_prediction(self):
        event_id = "x1-e02"
        predicted = [
            {
                "stream": "x1",
                "event_id": event_id,
                "prediction": self.gold["rows"][event_id]["signals"],
                "repair_count": 0,
                "repair_reason": None,
                "extraction_error": None,
                "elapsed_seconds": 0.1,
            }
        ]
        before = json.loads(json.dumps(predicted))
        scored = score_rows(predicted, self.gold)
        self.assertEqual(predicted, before)
        self.assertEqual(scored["exact_events"], 1)
        self.assertEqual(scored["signal_fp"], 0)
        self.assertEqual(scored["signal_fn"], 0)

    def test_event_mapping_does_not_add_harness_annotations(self):
        raw = self.fixture["streams"][0]["events"][0]
        mapped = event_from_mapping(raw)
        self.assertEqual(mapped.event_id, raw["event_id"])
        self.assertEqual(mapped.metadata, raw.get("metadata") or {})


if __name__ == "__main__":
    unittest.main()
