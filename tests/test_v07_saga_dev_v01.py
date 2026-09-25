"""Provider-free source firewall and answer-shape checks for v0.7 development."""

from __future__ import annotations

import json
import unittest

from hcl.v06 import SYSTEM_VIEWER
from scripts.prepare_v07_saga_dev_v01 import sha, story_text
from scripts.run_v07_saga_dev_v01 import construct_state, evaluate_one, parse_answer


class FakeSemanticBackend:
    def __init__(self):
        self.inputs = []

    def complete_json(self, messages, *, max_tokens, temperature=0.0):
        self.inputs.append(messages)
        source = json.loads(messages[1]["content"])
        if source["raw_text"] == "Mira wanted to finish the mural.":
            return json.dumps({"intention_evidence": [{
                "subject_agent_id": "Mira", "goal_key": "finish-mural",
                "signal": "EXPLICIT_GOAL", "provenance": "NARRATOR_ASSERTION",
                "evidence_text": source["raw_text"], "supersedes_goal_key": None,
            }]})
        return '{"intention_evidence": []}'


class FakeAnswerBackend:
    def __init__(self, output):
        self.output = output

    def complete_json(self, messages, *, max_tokens, temperature=0.0):
        return self.output


class V07SAGADevelopmentTests(unittest.TestCase):
    def test_state_is_built_from_narrative_without_task_or_labels(self):
        story = "\n".join([
            "Mira wanted to finish the mural.",
            "Mira bought paint.",
            "Rain began outside.",
            "Mira covered the canvas.",
            "She returned the next day.",
        ])
        backend = FakeSemanticBackend()
        runtime, audit = construct_state(story, "synthetic", backend)
        self.assertEqual(audit["source_events"], 5)
        self.assertEqual(audit["semantic_evidence_count"], 1)
        self.assertEqual(len(backend.inputs), 5)
        inputs = json.dumps(backend.inputs)
        self.assertNotIn("highlighted", inputs.lower())
        self.assertNotIn("original_goal", inputs)
        reader = runtime.answer_context("Mira", observer_agent_id=SYSTEM_VIEWER)
        self.assertEqual(len(reader["goal_estimates"]), 1)
        self.assertEqual(reader["goal_estimates"][0]["status"], "ACTIVE")
        self.assertEqual(reader["perspective"]["target_information_view"]["event_ids"], [])

    def test_answer_requires_exact_source_quote(self):
        story = "Mira wanted to finish the mural."
        raw = json.dumps({
            "evidence_class": "EXPLICIT", "candidate_goal": "finish mural",
            "supporting_quote": story,
        })
        self.assertEqual(parse_answer(raw, story)["evidence_class"], "EXPLICIT")
        with self.assertRaisesRegex(ValueError, "exact source quote"):
            parse_answer(raw.replace(story, "Mira wanted to sell it."), story)

    def test_invalid_answer_is_preserved_for_audit_without_stopping_other_arms(self):
        row = {f"story_line{i}": text for i, text in enumerate([
            "Mira wanted to finish the mural.", "Mira bought paint.",
            "Rain began outside.", "Mira covered the canvas.",
            "She returned the next day.",
        ], start=1)}
        story = story_text(row)
        item = {
            "instance_id": "synthetic", "story_id": "synthetic-story", "participant": "Mira",
            "story_sha256": sha(story), "source_tier": "explicit_goal",
        }
        valid = json.dumps({
            "evidence_class": "EXPLICIT", "candidate_goal": "finish mural",
            "supporting_quote": row["story_line1"],
        })
        result = evaluate_one(item, row, {
            "SEMANTIC": FakeSemanticBackend(), "C": FakeAnswerBackend(valid),
            "P": FakeAnswerBackend('{"bad": true}'), "D": FakeAnswerBackend(valid),
        })
        self.assertIsNone(result["arms"]["P"]["answer"])
        self.assertEqual(result["arms"]["P"]["raw_response"], '{"bad": true}')
        self.assertIsNotNone(result["arms"]["P"]["invalid_reason"])
        self.assertTrue(result["arms"]["D"]["source_tier_agreement"])


if __name__ == "__main__":
    unittest.main()
