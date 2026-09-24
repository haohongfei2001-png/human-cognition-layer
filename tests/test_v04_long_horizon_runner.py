"""Provider-free guards for the frozen long-horizon bounded-context runner."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from scripts.run_v04_long_horizon_bounded_context_v01 import (
    MeteredBackend,
    _event_retrieval_score,
    answer_label,
    compact_hcl_context,
    event_from_mapping,
    event_prompt_payload,
    load_and_validate,
    ordinary_query_context,
    run_c_stream,
    run_d_stream,
    run_e_stream,
    score_rows,
    update_ordinary_memory,
)


class FakeBackend:
    def __init__(self):
        self.calls = []

    def complete(self, messages, *, max_tokens, temperature=0.0):
        self.calls.append(("text", messages))
        return "Alice: Marin remains the working label until she explicitly changes stance."

    def complete_json(self, messages, *, max_tokens, temperature=0.0):
        self.calls.append(("json", messages))
        system = str(messages[0]["content"])
        if "semantic proposal stage of HCL v0.4" in system:
            return json.dumps({"propositions": [], "assertions": []})
        task = json.loads(messages[-1]["content"])
        return json.dumps({"label": task["allowed_labels"][0]})


class LongHorizonRunnerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        (
            cls.fixture,
            cls.gold,
            cls.fixture_sha,
            cls.gold_sha,
        ) = load_and_validate(
            "eval/v04/long_horizon_bounded_context_v01_fixture.json",
            "eval/v04/long_horizon_bounded_context_v01_gold.json",
        )

    def test_frozen_shape_and_gold_separation(self):
        self.assertEqual(len(self.fixture["streams"]), 3)
        self.assertEqual(
            sum(len(stream["events"]) for stream in self.fixture["streams"]),
            240,
        )
        self.assertEqual(
            sum(len(stream["queries"]) for stream in self.fixture["streams"]),
            18,
        )
        self.assertEqual(self.fixture["query_context_char_budget"], 8000)
        self.assertEqual(self.fixture["ordinary_memory_char_budget"], 6000)
        fixture_text = json.dumps(self.fixture, sort_keys=True)
        self.assertNotIn('"gold"', fixture_text)
        self.assertNotIn('"risk_class"', fixture_text)
        self.assertEqual(len(self.fixture_sha), 64)
        self.assertEqual(len(self.gold_sha), 64)

    def test_ordinary_memory_and_retrieval_stay_inside_query_budget(self):
        stream = self.fixture["streams"][0]
        query = stream["queries"][-1]
        memory = "m" * 5800
        payload, size = ordinary_query_context(
            memory,
            stream["events"],
            query,
            query_char_budget=self.fixture["query_context_char_budget"],
        )
        self.assertLessEqual(size, 8000)
        self.assertEqual(payload["ordinary_memory"], memory)
        self.assertTrue(payload["supporting_events"])

    def test_compact_hcl_projection_stays_inside_same_budget(self):
        stream = self.fixture["streams"][0]
        query = stream["queries"][-1]
        assertions = []
        evidence = []
        for index in range(40):
            relevant = index in {1, 2, 3, 4}
            assertions.append(
                {
                    "assertion_id": f"a{index}",
                    "assertion_type": (
                        "BELIEF_ESTIMATE" if relevant else "SOURCE_ASSERTION"
                    ),
                    "subject_agent_id": "alice" if relevant else None,
                    "proposition_id": f"p{index}",
                    "related_proposition_id": None,
                    "proposition_text": (
                        "Marina approved exhibit label"
                        if relevant
                        else f"unrelated cabinet marker {index}"
                    ),
                    "belief_stance": "AFFIRM" if relevant else None,
                    "support_level": "DIRECT_SUPPORT" if relevant else None,
                    "system_record_time": f"2026-09-01T10:{index:02d}:00+00:00",
                    "evidence_event_ids": [f"e{index}"],
                }
            )
            evidence.append(
                {
                    "event_id": f"e{index}",
                    "valid_time": f"2026-09-01T10:{index:02d}:00+00:00",
                    "recorded_at": f"2026-09-01T10:{index:02d}:01+00:00",
                    "source_id": "source",
                    "raw_text": (
                        "Marina approved exhibit label"
                        if relevant
                        else ("unrelated detail " * 20) + str(index)
                    ),
                }
            )
        context = {
            "state_version": 40,
            "relevant_assertions": assertions,
            "evidence": evidence,
            "unresolved_conflicts": [],
            "unsupported_conclusions": [],
        }
        payload, size = compact_hcl_context(
            context,
            query,
            query_char_budget=self.fixture["query_context_char_budget"],
        )
        self.assertLessEqual(size, 8000)
        self.assertTrue(
            any(
                row.get("subject_agent_id") == "alice"
                for row in payload["relevant_assertions"]
            )
        )

    def test_harness_only_annotations_never_reach_models_or_retrieval(self):
        stream = self.fixture["streams"][0]
        event = stream["events"][0]
        self.assertIn("track", event["metadata"])
        self.assertIn("sequence", event["metadata"])

        prompt_event = event_prompt_payload(event)
        mapped_event = event_from_mapping(event)
        self.assertNotIn("track", prompt_event["metadata"])
        self.assertNotIn("sequence", prompt_event["metadata"])
        self.assertNotIn("track", mapped_event.metadata)
        self.assertNotIn("sequence", mapped_event.metadata)

        scene_fact_event = next(
            row
            for candidate_stream in self.fixture["streams"]
            for row in candidate_stream["events"]
            if (row.get("metadata") or {}).get("scene_fact")
        )
        self.assertTrue(event_prompt_payload(scene_fact_event)["metadata"]["scene_fact"])
        self.assertTrue(event_from_mapping(scene_fact_event).metadata["scene_fact"])

        query = stream["queries"][0]
        altered = json.loads(json.dumps(event))
        altered["metadata"]["track"] = (
            "primary" if event["metadata"]["track"] != "primary" else "decoy"
        )
        altered["metadata"]["sequence"] = 999999
        self.assertEqual(
            _event_retrieval_score(event, query),
            _event_retrieval_score(altered, query),
        )

        fake = FakeBackend()
        backend = MeteredBackend(fake)
        update_ordinary_memory(
            backend,
            "",
            event,
            memory_char_budget=self.fixture["ordinary_memory_char_budget"],
        )
        prompts = "\n".join(
            str(message["content"])
            for _, call in fake.calls
            for message in call
        )
        self.assertNotIn('"track"', prompts)
        self.assertNotIn('"sequence"', prompts)

    def test_meter_records_provider_wall_time(self):
        fake = FakeBackend()
        backend = MeteredBackend(fake)
        query = self.fixture["streams"][0]["queries"][0]
        answer_label(
            backend,
            query,
            arm="E",
            dynamic_context={"ordinary_memory": "", "supporting_events": []},
        )
        metrics = backend.metrics()
        self.assertEqual(metrics["calls"], 1)
        self.assertGreaterEqual(metrics["provider_wall_seconds"], 0.0)

    def test_model_prompts_never_receive_gold_or_risk_class(self):
        fake = FakeBackend()
        backend = MeteredBackend(fake)
        stream = self.fixture["streams"][0]
        query = stream["queries"][0]
        memory, repairs = update_ordinary_memory(
            backend,
            "",
            stream["events"][0],
            memory_char_budget=self.fixture["ordinary_memory_char_budget"],
        )
        self.assertEqual(repairs, 0)
        self.assertTrue(memory)
        prediction = answer_label(
            backend,
            query,
            arm="E",
            dynamic_context={"ordinary_memory": memory, "supporting_events": []},
        )
        self.assertEqual(prediction, query["allowed_labels"][0])
        prompts = "\n".join(
            str(message["content"])
            for _, call in fake.calls
            for message in call
        )
        self.assertNotIn('"gold"', prompts)
        self.assertNotIn('"risk_class"', prompts)
        for row in self.gold["labels"].values():
            self.assertNotIn(row["risk_class"], prompts)

    def test_scored_rows_preserve_diagnostic_query_evidence(self):
        stream = self.fixture["streams"][0]

        c_backend = MeteredBackend(FakeBackend())
        c_rows = run_c_stream(stream, c_backend)
        self.assertEqual(len(c_rows), 6)
        self.assertTrue(all("query_context" in row for row in c_rows))

        d_backend = MeteredBackend(FakeBackend())
        d_rows = run_d_stream(
            stream,
            d_backend,
            query_char_budget=self.fixture["query_context_char_budget"],
        )
        self.assertEqual(len(d_rows), 6)
        self.assertTrue(all("query_context" in row for row in d_rows))
        self.assertTrue(all("persistent_state" in row for row in d_rows))
        self.assertTrue(all("state_chars" in row for row in d_rows))

        e_backend = MeteredBackend(FakeBackend())
        e_rows = run_e_stream(
            stream,
            e_backend,
            query_char_budget=self.fixture["query_context_char_budget"],
            memory_char_budget=self.fixture["ordinary_memory_char_budget"],
        )
        self.assertEqual(len(e_rows), 6)
        self.assertTrue(all("query_context" in row for row in e_rows))
        self.assertTrue(all("memory_chars" in row for row in e_rows))

        for rows in (c_rows, d_rows, e_rows):
            self.assertTrue(
                all("query_elapsed_seconds" in row for row in rows)
            )

    def test_scoring_is_posthoc_and_does_not_mutate_predictions(self):
        query_id = "s1-q1"
        rows = [
            {
                "stream": "s1",
                "query_id": query_id,
                "prediction": "MARIN",
                "query_context_chars": 123,
            }
        ]
        before = json.loads(json.dumps(rows))
        scored = score_rows(rows, self.gold)
        self.assertEqual(rows, before)
        self.assertEqual(scored["correct"], 1)
        self.assertEqual(scored["rows"][0]["gold"], "MARIN")


if __name__ == "__main__":
    unittest.main()
