"""Independent affect provenance, mixed-state and perspective regressions."""

from dataclasses import replace
import json
import unittest
from hcl.v04.model import EventRecord
from hcl.v06 import SYSTEM_VIEWER
from hcl.v06.belief import BeliefEvidenceKind as P
from hcl.v07 import IntentionEvidenceEvent, IntentionSignal
from hcl.v08 import (
    AffectEvidenceEvent,
    AffectKind as K,
    AppraisalDimension as D,
    EvidenceStrength as S,
    HCLV08Runtime,
    V08ExtractionError,
)


def event(i, actor, text, *, observers=(), reader_only=False):
    t = f"2026-01-01T00:00:{i:02d}+00:00"
    return EventRecord(
        event_id=f"e{i}",
        valid_time=t,
        recorded_at=t,
        source_id="independent-synthetic",
        actor_id=actor,
        observer_ids=tuple(observers),
        raw_text=text,
        metadata={"reader_only": True} if reader_only else {},
    )


def evidence(
    source,
    kind=K.EMOTION,
    value="relief",
    *,
    strength=S.DIRECT,
    provenance=P.SELF_REPORT,
    subject="Mira",
    episode="trip",
    eid=None,
    **fields,
):
    return AffectEvidenceEvent(
        evidence_id=eid or f"{source.event_id}:{value}",
        source_event_id=source.event_id,
        subject_agent_id=subject,
        episode_key=episode,
        kind=kind,
        strength=strength,
        value=value,
        provenance=provenance,
        valid_time=source.valid_time,
        system_record_time=source.recorded_at,
        evidence_text=source.raw_text,
        **fields,
    )


class Backend:
    def __init__(self, *outputs):
        self.outputs = list(outputs)
        self.inputs = []

    def complete_json(self, messages, *, max_tokens, temperature=0):
        self.inputs.append(messages)
        return self.outputs.pop(0)


def row(**overrides):
    d = {
        "subject_agent_id": "Mira",
        "episode_key": "trip",
        "kind": "EMOTION",
        "strength": "DIRECT",
        "value": "relief",
        "provenance": "SELF_REPORT",
        "evidence_text": "I feel relieved.",
        "dimension": None,
        "goal_key": None,
        "supersedes_evidence_id": None,
    }
    d.update(overrides)
    return d


def output(*rows):
    return json.dumps({"affect_evidence": list(rows)})


class AffectRuntimeTests(unittest.TestCase):
    def test_expression_and_success_do_not_establish_private_emotion(self):
        r = HCLV08Runtime()
        e = event(1, "Mira", "Mira smiled after winning the award.")
        r.ingest_event(e)
        r.ingest_affect_evidence(
            evidence(
                e,
                K.EXPRESSION,
                "smile",
                strength=S.INFERRED,
                provenance=P.OBSERVED_ACTION,
            )
        )
        self.assertEqual(
            r.answer_context("Mira")["emotion_status"], "SYSTEM_INSUFFICIENT"
        )
        r.ingest_affect_evidence(
            evidence(
                e,
                K.EMOTION,
                "possible relief",
                strength=S.INFERRED,
                provenance=P.OBSERVED_ACTION,
            )
        )
        c = r.answer_context("Mira")
        self.assertEqual(c["emotion_status"], "HYPOTHESIS_ONLY")
        self.assertFalse(any(x["strength"] == "DIRECT" for x in c["current_evidence"]))
        with self.assertRaises(ValueError):
            evidence(e, provenance=P.OBSERVED_ACTION)

    def test_mixed_emotions_survive_action_change_and_explicit_revision(self):
        r = HCLV08Runtime()
        a = event(1, "Mira", "I feel relieved but still worried.")
        b = event(2, "Mira", "Mira laughed.")
        c = event(3, "Mira", "I am no longer worried; I feel calm.")
        for e in (a, b, c):
            r.ingest_event(e)
        old = evidence(a, value="worry")
        r.ingest_affect_evidence(old)
        r.ingest_affect_evidence(evidence(a, value="relief"))
        r.ingest_affect_evidence(
            evidence(
                b,
                K.EXPRESSION,
                "laugh",
                strength=S.INFERRED,
                provenance=P.OBSERVED_ACTION,
            )
        )
        self.assertEqual(
            len(
                [
                    x
                    for x in r.answer_context("Mira")["current_evidence"]
                    if x["kind"] == "EMOTION"
                ]
            ),
            2,
        )
        r.ingest_affect_evidence(
            evidence(c, value="calm", supersedes_evidence_id=old.evidence_id)
        )
        now = r.answer_context("Mira")
        self.assertEqual(
            {x["value"] for x in now["current_evidence"] if x["kind"] == "EMOTION"},
            {"relief", "calm"},
        )
        self.assertEqual(now["historical_evidence"][0]["value"], "worry")
        past = r.answer_context("Mira", event_time=a.valid_time)
        self.assertEqual(
            {x["value"] for x in past["current_evidence"]}, {"worry", "relief"}
        )

    def test_attribution_and_character_uncertainty_are_separate(self):
        r = HCLV08Runtime()
        a = event(1, "Noah", "I think Mira feels proud.", observers=("Mira",))
        b = event(2, "Mira", "I cannot tell what I feel.", observers=("Noah",))
        for e in (a, b):
            r.ingest_event(e)
        r.ingest_affect_evidence(
            evidence(
                a, value="pride", strength=S.ATTRIBUTED, provenance=P.THIRD_PARTY_REPORT
            )
        )
        self.assertEqual(
            r.answer_context("Mira")["emotion_status"], "SYSTEM_INSUFFICIENT"
        )
        r.ingest_affect_evidence(
            evidence(b, K.CHARACTER_UNCERTAIN, "uncertain feelings")
        )
        self.assertEqual(
            r.answer_context("Mira")["emotion_status"], "CHARACTER_UNCERTAIN"
        )
        with self.assertRaises(ValueError):
            evidence(a, provenance=P.THIRD_PARTY_REPORT)

    def test_narrator_private_report_and_bounded_second_order_do_not_leak(self):
        r = HCLV08Runtime()
        n = event(1, None, "Mira privately felt disappointed.", reader_only=True)
        public = event(2, "Mira", "I feel relieved.", observers=("Noah", "Iris"))
        for e in (n, public):
            r.ingest_event(e)
        r.ingest_affect_evidence(
            evidence(n, value="disappointment", provenance=P.NARRATOR_ASSERTION)
        )
        r.ingest_affect_evidence(evidence(public))
        self.assertEqual(len(r.answer_context("Mira")["current_evidence"]), 2)
        self.assertEqual(
            [
                x["value"]
                for x in r.answer_context("Mira", observer_agent_id="Mira")[
                    "current_evidence"
                ]
            ],
            ["relief"],
        )
        self.assertEqual(
            [
                x["value"]
                for x in r.answer_context("Mira", observer_agent_id="Noah")[
                    "current_evidence"
                ]
            ],
            ["relief"],
        )
        self.assertEqual(
            r.answer_context("Mira", observer_agent_id="Absent")["emotion_status"],
            "SYSTEM_INSUFFICIENT",
        )

    def test_appraisal_goal_link_is_auditable_without_emotion_mapping(self):
        r = HCLV08Runtime()
        g = event(1, "Mira", "I aim to arrive before noon.")
        a = event(
            2, "Mira", "The delay prevents arrival before noon.", observers=("Noah",)
        )
        r.ingest_event(g)
        r.ingest_event(a)
        claim = evidence(
            a,
            K.APPRAISAL,
            "goal obstructed",
            dimension=D.GOAL_CONGRUENCE,
            goal_key="arrival",
        )
        with self.assertRaises(ValueError):
            r.ingest_affect_evidence(claim)
        r.intentions.ingest_intention_evidence(
            IntentionEvidenceEvent(
                evidence_id="goal1",
                source_event_id=g.event_id,
                subject_agent_id="Mira",
                goal_key="arrival",
                signal=IntentionSignal.EXPLICIT_GOAL,
                provenance=P.SELF_REPORT,
                valid_time=g.valid_time,
                system_record_time=g.recorded_at,
                evidence_text=g.raw_text,
            )
        )
        r.ingest_affect_evidence(claim)
        self.assertEqual(
            r.answer_context("Mira")["emotion_status"], "SYSTEM_INSUFFICIENT"
        )
        self.assertEqual(
            r.answer_context("Mira")["current_evidence"][0]["goal_key"], "arrival"
        )
        second = r.answer_context("Mira", observer_agent_id="Noah")
        self.assertEqual(second["current_evidence"][0]["goal_key"], None)
        self.assertEqual(second["visible_goal_context"], [])
        b = Backend(output())
        r.ingest_semantic_event(event(3, "Noah", "Noah listened."), b)
        extraction_source = json.loads(b.inputs[0][1]["content"])
        self.assertIsNone(extraction_source["prior_direct_evidence"][0]["goal_key"])
        self.assertEqual(extraction_source["known_goal_keys"], [])

    def test_source_binding_chronology_and_explicit_revision_fail_closed(self):
        r = HCLV08Runtime()
        a = event(1, "Mira", "I feel worried.")
        b = event(2, "Noah", "Mira seems calm.")
        r.ingest_event(a)
        r.ingest_event(b)
        old = evidence(a, value="worry")
        r.ingest_affect_evidence(old)
        for bad in (
            replace(old, evidence_id="badquote", evidence_text="I feel joyful."),
            replace(old, evidence_id="badtime", valid_time=b.valid_time),
            evidence(b, value="calm"),
            replace(old, evidence_id="cross", subject_agent_id="Noah"),
            replace(old, evidence_id="future", supersedes_evidence_id=old.evidence_id),
        ):
            with self.assertRaises(ValueError):
                r.ingest_affect_evidence(bad)
        with self.assertRaises(ValueError):
            evidence(
                b,
                value="calm",
                strength=S.ATTRIBUTED,
                provenance=P.THIRD_PARTY_REPORT,
                supersedes_evidence_id=old.evidence_id,
            )
        self.assertTrue(r.ingest_affect_evidence(old))
        with self.assertRaises(ValueError):
            r.ingest_affect_evidence(replace(old, value="different"))

    def test_hidden_prior_revision_pointer_is_removed_from_answer(self):
        r = HCLV08Runtime()
        a = event(1, "Mira", "I feel worried.")
        b = event(2, "Mira", "I am calm now, no longer worried.", observers=("Noah",))
        for e in (a, b):
            r.ingest_event(e)
        old = evidence(a, value="worry")
        r.ingest_affect_evidence(old)
        r.ingest_affect_evidence(
            evidence(b, value="calm", supersedes_evidence_id=old.evidence_id)
        )
        c = r.answer_context("Mira", observer_agent_id="Noah")
        self.assertEqual(c["current_evidence"][0]["supersedes_evidence_id"], None)
        self.assertEqual(c["historical_evidence"], [])

    def test_semantic_extraction_repairs_exact_quote_and_replays_idempotently(self):
        e = event(1, "Mira", "I feel relieved.")
        b = Backend(output(row(evidence_text="made up")), output(row()))
        r = HCLV08Runtime()
        result = r.ingest_semantic_event(e, b)
        self.assertEqual(result.repair_count, 1)
        self.assertEqual(len(r._evidence), 1)
        self.assertIs(r.ingest_semantic_event(e, b), result)
        self.assertEqual(len(b.inputs), 2)
        material = json.dumps(b.inputs)
        self.assertNotIn("Highlighted participant", material)
        self.assertNotIn("gold", b.inputs[0][1]["content"])
        with self.assertRaises(ValueError):
            r.ingest_semantic_event(replace(e, raw_text="Different source."), b)

    def test_persistent_semantic_failure_keeps_source_without_false_claim(self):
        e = event(1, "Mira", "I feel relieved.")
        b = Backend(
            output(row(evidence_text="made up")),
            output(row(provenance="THIRD_PARTY_REPORT")),
        )
        r = HCLV08Runtime()
        with self.assertRaises(V08ExtractionError):
            r.ingest_semantic_event(e, b)
        self.assertEqual(len(r.intentions.perspectives.events), 1)
        self.assertEqual(r._evidence, {})

    def test_semantic_prior_context_excludes_future_and_private_other_sources(self):
        r = HCLV08Runtime()
        future = event(5, "Mira", "I feel relieved.")
        private = event(1, "Mira", "I feel worried.")
        next_e = event(3, "Noah", "Noah paused.")
        for e in (future, private):
            r.ingest_event(e)
            r.ingest_affect_evidence(
                evidence(e, value="relief" if e is future else "worry")
            )
        b = Backend(output())
        r.ingest_semantic_event(next_e, b)
        source = json.loads(b.inputs[0][1]["content"])
        self.assertEqual(source["prior_direct_evidence"], [])

    def test_batch_does_not_partially_commit_invalid_revision(self):
        e = event(1, "Mira", "I feel relieved.")
        b = Backend(
            output(row(), row(value="calm", supersedes_evidence_id="unknown")),
            output(row(), row(value="calm", supersedes_evidence_id="unknown")),
        )
        r = HCLV08Runtime()
        with self.assertRaises(V08ExtractionError):
            r.ingest_semantic_event(e, b)
        self.assertEqual(r._evidence, {})


if __name__ == "__main__":
    unittest.main()
