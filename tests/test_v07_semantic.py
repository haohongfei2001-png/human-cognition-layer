"""Provider-free event-local semantic extraction and fail-closed repair."""

from __future__ import annotations

import json
import unittest

from hcl.v04.model import EventRecord
from hcl.v07 import GoalStatus, HCLV07Runtime, V07ExtractionError, extract_intention_evidence


def event(index: int, actor: str, text: str) -> EventRecord:
    stamp = f"2026-01-01T00:00:{index:02d}+00:00"
    return EventRecord(f"e{index}", stamp, text, "synthetic", recorded_at=stamp, actor_id=actor)


class FakeBackend:
    def __init__(self, *outputs):
        self.outputs = list(outputs)
        self.inputs = []

    def complete_json(self, messages, *, max_tokens, temperature=0.0):
        self.inputs.append(messages)
        if not self.outputs:
            raise AssertionError("unexpected provider call")
        return self.outputs.pop(0)


def row(subject, goal, signal, provenance, quote, prior=None):
    return {
        "subject_agent_id": subject, "goal_key": goal, "signal": signal,
        "provenance": provenance, "evidence_text": quote,
        "supersedes_goal_key": prior,
    }


class V07SemanticTests(unittest.TestCase):
    def test_explicit_goal_and_revision_are_source_anchored(self):
        runtime = HCLV07Runtime()
        first = event(1, "Mira", "I plan to take the train.")
        revised = event(2, "Mira", "I will cycle instead of taking the train.")
        one = FakeBackend(json.dumps({"intention_evidence": [
            row("Mira", "train", "EXPLICIT_INTENTION", "SELF_REPORT", first.raw_text)
        ]}))
        two = FakeBackend(json.dumps({"intention_evidence": [
            row("Mira", "cycle", "EXPLICIT_REVISION", "SELF_REPORT", revised.raw_text, "train")
        ]}))
        runtime.ingest_semantic_event(first, one)
        runtime.ingest_semantic_event(revised, two)
        goals = {x.goal_key: x for x in runtime.goal_estimates("Mira")}
        self.assertEqual(goals["train"].status, GoalStatus.REVISED)
        self.assertEqual(goals["cycle"].status, GoalStatus.ACTIVE)
        self.assertIn("train", two.inputs[0][1]["content"])
        self.assertNotIn("benchmark", two.inputs[0][1]["content"])

    def test_ungrounded_quote_repairs_once_to_empty(self):
        source = event(1, "Mira", "Mira walked past the station.")
        invalid = json.dumps({"intention_evidence": [
            row("Mira", "travel", "EXPLICIT_INTENTION", "SELF_REPORT", "I intend to travel.")
        ]})
        backend = FakeBackend(invalid, '{"intention_evidence": []}')
        result = extract_intention_evidence(source, backend)
        self.assertEqual(result.evidence, ())
        self.assertEqual(result.repair_count, 1)
        self.assertEqual(len(backend.inputs), 2)

    def test_persistent_ungrounded_extraction_fails_without_goal_state(self):
        runtime = HCLV07Runtime()
        source = event(1, "Mira", "Mira walked past the station.")
        invalid = json.dumps({"intention_evidence": [
            row("Mira", "travel", "EXPLICIT_INTENTION", "SELF_REPORT", "I intend to travel.")
        ]})
        with self.assertRaises(V07ExtractionError):
            runtime.ingest_semantic_event(source, FakeBackend(invalid, invalid))
        self.assertEqual(runtime.perspectives.events, ())
        self.assertEqual(runtime.goal_estimates("Mira"), ())

    def test_observed_action_remains_noncommittal_about_goal(self):
        runtime = HCLV07Runtime()
        source = event(1, "Mira", "Mira went to the clinic.")
        backend = FakeBackend(json.dumps({"intention_evidence": [
            row("Mira", "seek-care", "OBSERVED_ACTION", "OBSERVED_ACTION", source.raw_text)
        ]}))
        runtime.ingest_semantic_event(source, backend)
        goal, = runtime.goal_estimates("Mira")
        self.assertEqual(goal.status, GoalStatus.SYSTEM_INSUFFICIENT)
        runtime.ingest_semantic_event(source, backend)
        self.assertEqual(len(backend.inputs), 1)

    def test_reader_only_narrator_can_report_action_without_proving_intention(self):
        stamp = "2026-01-01T00:00:01+00:00"
        source = EventRecord(
            "narrated-action", stamp, "Mira carried the parcel to the station.",
            "narrator", recorded_at=stamp, metadata={"reader_only": True},
        )
        runtime = HCLV07Runtime()
        backend = FakeBackend(json.dumps({"intention_evidence": [
            row("Mira", "deliver-parcel", "OBSERVED_ACTION", "NARRATOR_ASSERTION", source.raw_text)
        ]}))
        runtime.ingest_semantic_event(source, backend)
        goal, = runtime.goal_estimates("Mira")
        self.assertEqual(goal.status, GoalStatus.SYSTEM_INSUFFICIENT)
        self.assertEqual(len(goal.action_evidence_ids), 1)

    def test_narrated_action_requires_reader_only_source(self):
        source = event(1, "Noah", "Mira carried the parcel to the station.")
        invalid = json.dumps({"intention_evidence": [
            row("Mira", "deliver-parcel", "OBSERVED_ACTION", "NARRATOR_ASSERTION", source.raw_text)
        ]})
        with self.assertRaises(V07ExtractionError):
            extract_intention_evidence(source, FakeBackend(invalid, invalid))


if __name__ == "__main__":
    unittest.main()
