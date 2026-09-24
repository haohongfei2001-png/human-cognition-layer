"""Provider-free guards for routed semantic extraction v0.2."""

from __future__ import annotations

import json
import unittest

from scripts.run_v05_routed_semantic_extraction_v02 import (
    MeteredBackend,
    extract_rows,
    load_and_validate,
    revision_key,
    score_rows,
    self_key,
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


def model_payload(self_stances=(), revision_relations=()):
    return json.dumps(
        {
            "self_stances": list(self_stances),
            "revision_relations": list(revision_relations),
        }
    )


class RoutedExtractionV02Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        (
            cls.fixture,
            cls.gold,
            cls.fixture_sha,
            cls.gold_sha,
        ) = load_and_validate(
            "eval/v05/routed_semantic_extraction_v02_fixture.json",
            "eval/v05/routed_semantic_extraction_v02_gold.json",
        )

    def test_shape_and_gold_separation(self):
        self.assertEqual(len(self.fixture["streams"]), 3)
        self.assertEqual(
            sum(len(s["events"]) for s in self.fixture["streams"]), 36
        )
        self.assertEqual(
            sum(len(x["self_stances"]) for x in self.gold["rows"].values()),
            19,
        )
        self.assertEqual(
            sum(
                len(x["revision_relations"])
                for x in self.gold["rows"].values()
            ),
            14,
        )
        text = json.dumps(self.fixture, sort_keys=True)
        self.assertNotIn('"risk_class"', text)
        self.assertNotIn('"self_stances"', text)
        self.assertNotIn('"revision_relations"', text)

    def test_v02_is_text_and_id_disjoint_from_consumed_v01(self):
        old = json.loads(
            open(
                "eval/v05/semantic_extraction_v01_fixture.json",
                encoding="utf-8",
            ).read()
        )
        old_ids = {
            e["event_id"]
            for s in old["streams"]
            for e in s["events"]
        }
        old_texts = {
            e["raw_text"]
            for s in old["streams"]
            for e in s["events"]
        }
        new_ids = {
            e["event_id"]
            for s in self.fixture["streams"]
            for e in s["events"]
        }
        new_texts = {
            e["raw_text"]
            for s in self.fixture["streams"]
            for e in s["events"]
        }
        self.assertTrue(old_ids.isdisjoint(new_ids))
        self.assertTrue(old_texts.isdisjoint(new_texts))

    def test_gold_model_payload_routes_revision_subject_deterministically(self):
        stream = self.fixture["streams"][0]
        event = next(e for e in stream["events"] if e["event_id"] == "r1-e07")
        truth = self.gold["rows"]["r1-e07"]
        backend = MeteredBackend(
            FakeBackend(
                [
                    model_payload(
                        truth["self_stances"],
                        truth["revision_relations"],
                    )
                ]
            )
        )
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
        routed = rows[0]["routed_stance_events"]
        self.assertEqual(len(routed), 1)
        self.assertEqual(routed[0]["subject_agent_id"], "ivo")
        self.assertEqual(routed[0]["signal"], "REVISION_EXPOSURE")

    def test_self_report_reference_with_no_audience_can_score_false_relation(self):
        stream = self.fixture["streams"][0]
        event = next(e for e in stream["events"] if e["event_id"] == "r1-e08")
        truth = self.gold["rows"]["r1-e08"]
        false_revision = {
            "issue_key": "delivery_channel",
            "new_value_key": "PORTAL",
            "prior_value_key": "EMAIL",
        }
        backend = MeteredBackend(
            FakeBackend(
                [
                    model_payload(
                        truth["self_stances"],
                        [false_revision],
                    )
                ]
            )
        )
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
        scored = score_rows(rows, self.gold)
        self.assertEqual(scored["exact_events"], 0)
        self.assertEqual(scored["revision_fp"], 1)
        self.assertEqual(rows[0]["routed_stance_events"][0]["signal"], "UNRESOLVED")

    def test_gold_and_risk_never_enter_model_prompt(self):
        stream = self.fixture["streams"][1]
        event = stream["events"][1]
        truth = self.gold["rows"][event["event_id"]]
        fake = FakeBackend(
            [
                model_payload(
                    truth["self_stances"],
                    truth["revision_relations"],
                )
            ]
        )
        backend = MeteredBackend(fake)
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
        extract_rows(mini, backend)
        prompt = "\n".join(
            str(m["content"]) for m in fake.calls[0]
        )
        self.assertNotIn(truth["risk_class"], prompt)
        self.assertNotIn("risk_class", prompt)
        self.assertNotIn("expected_self_stances", prompt)

    def test_scoring_is_posthoc(self):
        event_id = "r3-e12"
        truth = self.gold["rows"][event_id]
        row = {
            "stream": "r3",
            "event_id": event_id,
            "predicted_self_stances": truth["self_stances"],
            "predicted_revision_relations": truth["revision_relations"],
            "routed_stance_events": [],
            "repair_count": 0,
            "repair_reason": None,
            "extraction_error": None,
            "elapsed_seconds": 0.1,
        }
        before = json.loads(json.dumps(row))
        scored = score_rows([row], self.gold)
        self.assertEqual(row, before)
        self.assertEqual(scored["exact_events"], 1)
        self.assertEqual(scored["self_fp"], 0)
        self.assertEqual(scored["revision_fp"], 0)

    def test_key_helpers_are_order_stable(self):
        self.assertEqual(
            self_key(
                {
                    "issue_key": "i",
                    "signal": "AFFIRM",
                    "value_key": "v",
                }
            ),
            ("i", "AFFIRM", "v"),
        )
        self.assertEqual(
            revision_key(
                {
                    "issue_key": "i",
                    "new_value_key": "n",
                    "prior_value_key": "p",
                }
            ),
            ("i", "n", "p"),
        )


if __name__ == "__main__":
    unittest.main()
