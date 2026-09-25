"""Independent, provider-free intention/goal semantic regressions."""

from __future__ import annotations

import unittest

from hcl.v04.model import EventRecord
from hcl.v06.belief import BeliefEvidenceKind as Provenance
from hcl.v07 import GoalStatus, HCLV07Runtime, IntentionEvidenceEvent, IntentionSignal


def event(index: int, actor: str | None, text: str, *, observers=(), reader_only=False) -> EventRecord:
    stamp = f"2026-01-01T00:00:{index:02d}+00:00"
    return EventRecord(
        event_id=f"event-{index}", valid_time=stamp, recorded_at=stamp,
        source_id="synthetic-narrative", actor_id=actor,
        observer_ids=tuple(observers), raw_text=text,
        metadata={"reader_only": reader_only} if reader_only else {},
    )


def evidence(source: EventRecord, signal: IntentionSignal, goal: str, *,
             subject="Mira", provenance=Provenance.SELF_REPORT,
             supersedes=None) -> IntentionEvidenceEvent:
    return IntentionEvidenceEvent(
        evidence_id=f"{source.event_id}:{signal.value}:{goal}",
        source_event_id=source.event_id, subject_agent_id=subject,
        goal_key=goal, signal=signal, provenance=provenance,
        valid_time=source.valid_time, system_record_time=source.recorded_at,
        evidence_text=source.raw_text, supersedes_goal_key=supersedes,
    )


class IntentionRuntimeTests(unittest.TestCase):
    def test_action_and_motivation_hypothesis_do_not_create_certain_goal(self):
        runtime = HCLV07Runtime()
        action = event(1, "Mira", "Mira walked to the clinic.", observers=("Noah",))
        runtime.ingest_event(action)
        runtime.ingest_intention_evidence(evidence(
            action, IntentionSignal.OBSERVED_ACTION, "seek-care",
            provenance=Provenance.OBSERVED_ACTION,
        ))
        runtime.ingest_intention_evidence(evidence(
            action, IntentionSignal.INFERRED_MOTIVATION, "seek-care",
            provenance=Provenance.OBSERVED_ACTION,
        ))
        estimate, = runtime.goal_estimates("Mira")
        self.assertEqual(estimate.status, GoalStatus.SYSTEM_INSUFFICIENT)
        self.assertEqual(len(estimate.action_evidence_ids), 1)
        self.assertEqual(len(estimate.inferred_motivation_ids), 1)

    def test_explicit_goal_completion_and_action_change(self):
        runtime = HCLV07Runtime()
        stated = event(1, "Mira", "I aim to finish the mural.")
        detour = event(2, "Mira", "Mira went to buy brushes.")
        done = event(3, "Mira", "I finished the mural.")
        for source in (stated, detour, done):
            runtime.ingest_event(source)
        runtime.ingest_intention_evidence(evidence(stated, IntentionSignal.EXPLICIT_GOAL, "mural"))
        runtime.ingest_intention_evidence(evidence(detour, IntentionSignal.OBSERVED_ACTION, "mural", provenance=Provenance.OBSERVED_ACTION))
        self.assertEqual(runtime.goal_estimates("Mira")[0].status, GoalStatus.ACTIVE)
        runtime.ingest_intention_evidence(evidence(done, IntentionSignal.EXPLICIT_COMPLETION, "mural"))
        self.assertEqual(runtime.goal_estimates("Mira")[0].status, GoalStatus.COMPLETED)

    def test_revision_requires_direct_evidence_and_preserves_old_goal(self):
        runtime = HCLV07Runtime()
        old = event(1, "Mira", "I plan to take the train.")
        changed = event(2, "Mira", "I will cycle instead of taking the train.")
        runtime.ingest_event(old)
        runtime.ingest_event(changed)
        with self.assertRaises(ValueError):
            runtime.ingest_intention_evidence(evidence(changed, IntentionSignal.EXPLICIT_REVISION, "cycle", supersedes="train"))
        runtime.ingest_intention_evidence(evidence(old, IntentionSignal.EXPLICIT_INTENTION, "train"))
        with self.assertRaises(ValueError):
            evidence(changed, IntentionSignal.EXPLICIT_REVISION, "cycle", provenance=Provenance.THIRD_PARTY_REPORT, supersedes="train")
        runtime.ingest_intention_evidence(evidence(changed, IntentionSignal.EXPLICIT_REVISION, "cycle", supersedes="train"))
        estimates = {x.goal_key: x for x in runtime.goal_estimates("Mira")}
        self.assertEqual(estimates["train"].status, GoalStatus.REVISED)
        self.assertEqual(estimates["train"].revised_by_goal_key, "cycle")
        self.assertEqual(estimates["cycle"].status, GoalStatus.ACTIVE)

    def test_third_party_attribution_and_character_uncertainty_are_distinct(self):
        runtime = HCLV07Runtime()
        report = event(1, "Noah", "Mira probably wants a promotion.", observers=("Mira",))
        uncertainty = event(2, "Mira", "I am not sure what I want next.", observers=("Noah",))
        runtime.ingest_event(report)
        runtime.ingest_event(uncertainty)
        runtime.ingest_intention_evidence(evidence(
            report, IntentionSignal.THIRD_PARTY_ATTRIBUTION, "promotion",
            provenance=Provenance.THIRD_PARTY_REPORT,
        ))
        self.assertEqual(runtime.goal_estimates("Mira")[0].status, GoalStatus.SYSTEM_INSUFFICIENT)
        runtime.ingest_intention_evidence(evidence(uncertainty, IntentionSignal.CHARACTER_UNCERTAIN, "promotion"))
        self.assertEqual(runtime.goal_estimates("Mira")[0].status, GoalStatus.CHARACTER_UNCERTAIN)

    def test_counterevidence_makes_stated_goal_unresolved_without_abandoning_it(self):
        runtime = HCLV07Runtime()
        stated = event(1, "Mira", "I want to publish the book.")
        obstacle = event(2, "Noah", "The publisher withdrew its offer.", observers=("Mira",))
        runtime.ingest_event(stated)
        runtime.ingest_event(obstacle)
        runtime.ingest_intention_evidence(evidence(stated, IntentionSignal.EXPLICIT_GOAL, "book"))
        runtime.ingest_intention_evidence(evidence(
            obstacle, IntentionSignal.COUNTEREVIDENCE, "book",
            provenance=Provenance.THIRD_PARTY_REPORT,
        ))
        estimate, = runtime.goal_estimates("Mira")
        self.assertEqual(estimate.status, GoalStatus.UNRESOLVED)
        self.assertNotEqual(estimate.status, GoalStatus.ABANDONED)

    def test_first_and_bounded_second_order_views_do_not_leak_private_goal(self):
        runtime = HCLV07Runtime()
        private = event(1, "Mira", "I intend to apply for the grant.")
        public = event(2, "Mira", "I am reviewing the form.", observers=("Noah",))
        runtime.ingest_event(private)
        runtime.ingest_event(public)
        runtime.ingest_intention_evidence(evidence(private, IntentionSignal.EXPLICIT_INTENTION, "grant"))
        self.assertEqual(runtime.goal_estimates("Mira")[0].status, GoalStatus.ACTIVE)
        self.assertEqual(runtime.goal_estimates("Mira", observer_agent_id="Noah"), ())
        context = runtime.answer_context("Mira", observer_agent_id="Noah")
        self.assertEqual(context["intention_evidence"], [])
        self.assertEqual(context["goal_estimates"], [])

    def test_reader_only_narrator_evidence_stays_out_of_character_view(self):
        runtime = HCLV07Runtime()
        narrator = event(1, None, "Mira secretly intended to leave.", reader_only=True)
        runtime.ingest_event(narrator)
        runtime.ingest_intention_evidence(evidence(
            narrator, IntentionSignal.EXPLICIT_INTENTION, "leave",
            provenance=Provenance.NARRATOR_ASSERTION,
        ))
        self.assertEqual(runtime.goal_estimates("Mira")[0].status, GoalStatus.ACTIVE)
        self.assertEqual(runtime.goal_estimates("Mira", observer_agent_id=None), ())

    def test_source_id_alone_cannot_launder_invented_intention_text(self):
        runtime = HCLV07Runtime()
        source = event(1, "Mira", "I walked past the station.")
        runtime.ingest_event(source)
        invented = IntentionEvidenceEvent(
            evidence_id="invented", source_event_id=source.event_id,
            subject_agent_id="Mira", goal_key="travel", signal=IntentionSignal.EXPLICIT_INTENTION,
            provenance=Provenance.SELF_REPORT, valid_time=source.valid_time,
            system_record_time=source.recorded_at,
            evidence_text="I intend to travel tomorrow.",
        )
        with self.assertRaisesRegex(ValueError, "exact source excerpt"):
            runtime.ingest_intention_evidence(invented)
        self.assertEqual(runtime.goal_estimates("Mira"), ())


if __name__ == "__main__":
    unittest.main()
