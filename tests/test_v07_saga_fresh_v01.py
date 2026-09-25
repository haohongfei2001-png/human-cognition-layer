"""Provider-free fresh selection, state firewall and strong G control checks."""

from __future__ import annotations

import json
import unittest

from scripts.prepare_v07_saga_dev_v01 import sha, story_text
from scripts.run_v07_saga_fresh_v01 import construct_states, evaluate_one


class FakeSemanticBackend:
    def __init__(self):
        self.inputs = []

    def complete_json(self, messages, *, max_tokens, temperature=0.0):
        self.inputs.append(messages)
        return '{"intention_evidence": []}'


class FakeAnswerBackend:
    def __init__(self, output):
        self.output = output
        self.inputs = []

    def complete_json(self, messages, *, max_tokens, temperature=0.0):
        self.inputs.append(messages)
        return self.output


class FreshSAGATests(unittest.TestCase):
    def test_g_and_d_build_from_full_story_before_target_release(self):
        story = "\n".join([
            "Mira wanted to finish the mural.", "Mira bought paint.",
            "Rain began outside.", "Mira covered the canvas.",
            "She returned the next day.",
        ])
        semantic = FakeSemanticBackend()
        generic, specialized, audit = construct_states(story, "synthetic", semantic)
        self.assertEqual(generic["event_count"], 5)
        self.assertEqual(audit["source_events"], 5)
        self.assertEqual(len(specialized.perspectives.events), 5)
        self.assertEqual([x["event_text"] for x in generic["timeline"]], story.split("\n"))
        material = json.dumps(semantic.inputs)
        self.assertNotIn("Highlighted participant", material)
        self.assertNotIn("source_tier", material)
        self.assertNotIn("original_goal", material)

    def test_same_story_and_task_reach_four_answer_arms(self):
        row = {f"story_line{i}": text for i, text in enumerate([
            "Mira wanted to finish the mural.", "Mira bought paint.",
            "Rain began outside.", "Mira covered the canvas.",
            "She returned the next day.",
        ], start=1)}
        story = story_text(row)
        item = {
            "instance_id": "synthetic", "story_id": "story-synthetic", "participant": "Mira",
            "story_sha256": sha(story), "source_tier": "explicit_goal",
        }
        output = json.dumps({
            "evidence_class": "EXPLICIT", "candidate_goal": "finish mural",
            "supporting_quote": row["story_line1"],
        })
        backends = {"SEMANTIC": FakeSemanticBackend()}
        backends.update({arm: FakeAnswerBackend(output) for arm in "CPGD"})
        result = evaluate_one(item, row, backends)
        self.assertEqual(set(result["arms"]), set("CPGD"))
        for arm in "CPGD":
            prompt = backends[arm].inputs[0][1]["content"]
            self.assertIn("Mira wanted to finish the mural.", prompt)
            self.assertIn("Highlighted participant: Mira", prompt)
            self.assertTrue(result["arms"][arm]["source_tier_agreement"])
        self.assertEqual(result["state_audit"]["semantic_evidence_count"], 0)


if __name__ == "__main__":
    unittest.main()
