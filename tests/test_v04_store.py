from __future__ import annotations

import unittest

from hcl.v04 import (
    AssertionType,
    BeliefStance,
    CognitiveAssertion,
    CognitionStore,
    EventRecord,
    Proposition,
    SemanticPatch,
)
from hcl.v04.model import utc_now_iso
from hcl.v04.schema import SchemaValidationError


T0 = "2026-01-01T10:00:00+00:00"


def event(event_id: str, text: str = "source says P") -> EventRecord:
    return EventRecord(
        event_id=event_id,
        valid_time=T0,
        raw_text=text,
        source_id="source",
        actor_id="source",
        observer_ids=("source",),
    )


class V04StoreTests(unittest.TestCase):
    def setUp(self):
        self.store = CognitionStore()
        self.store.append_event(event("e1"))

    def tearDown(self):
        self.store.close()

    def test_source_assertion_remains_distinct_from_scene_fact(self):
        patch = SemanticPatch(
            patch_id="patch1",
            event_id="e1",
            semantic_version="v04.1",
            propositions=(
                Proposition(
                    proposition_id="p1",
                    canonical_text="P",
                    source_event_ids=("e1",),
                ),
            ),
            assertions=(
                CognitiveAssertion(
                    assertion_id="a1",
                    assertion_type=AssertionType.SOURCE_ASSERTION,
                    proposition_id="p1",
                    valid_time=T0,
                    system_record_time=utc_now_iso(),
                    evidence_event_ids=("e1",),
                ),
            ),
        )
        self.store.apply_patch(0, patch)
        view = self.store.build_view(None, None, None, "what is known?")
        kinds = {x["assertion_type"] for x in view.relevant_assertions}
        self.assertIn("SOURCE_ASSERTION", kinds)
        self.assertNotIn("SCENE_FACT", kinds)

    def test_invalid_patch_is_atomic(self):
        bad = SemanticPatch(
            patch_id="bad",
            event_id="e1",
            semantic_version="v04.1",
            propositions=(),
            assertions=(
                CognitiveAssertion(
                    assertion_id="a_bad",
                    assertion_type=AssertionType.BELIEF_ESTIMATE,
                    belief_stance=BeliefStance.AFFIRM,
                    subject_agent_id="alice",
                    proposition_id="missing",
                    valid_time=T0,
                    system_record_time=utc_now_iso(),
                    evidence_event_ids=("e1",),
                ),
            ),
        )
        with self.assertRaises(SchemaValidationError):
            self.store.apply_patch(0, bad)
        self.assertEqual(self.store.state_version, 0)
        self.assertEqual(
            self.store.build_view(None, None, None, "q").relevant_assertions,
            (),
        )

    def test_duplicate_patch_is_idempotent(self):
        patch = SemanticPatch(
            patch_id="patch1",
            event_id="e1",
            semantic_version="v04.1",
        )
        first = self.store.apply_patch(0, patch)
        second = self.store.apply_patch(first.state_version, patch)
        self.assertFalse(first.duplicate)
        self.assertTrue(second.duplicate)
        self.assertEqual(first.state_version, second.state_version)
        self.assertEqual(self.store.state_version, first.state_version)

    def test_rebuild_replays_active_patches_deterministically(self):
        patch = SemanticPatch(
            patch_id="patch1",
            event_id="e1",
            semantic_version="v04.1",
            propositions=(
                Proposition(
                    proposition_id="p1",
                    canonical_text="P",
                    source_event_ids=("e1",),
                ),
            ),
            assertions=(
                CognitiveAssertion(
                    assertion_id="a1",
                    assertion_type=AssertionType.SOURCE_ASSERTION,
                    proposition_id="p1",
                    valid_time=T0,
                    system_record_time=utc_now_iso(),
                    evidence_event_ids=("e1",),
                ),
            ),
        )
        receipt = self.store.apply_patch(0, patch)
        before = receipt.checksum
        rebuilt = self.store.rebuild()
        self.assertEqual(before, rebuilt.checksum)
        self.assertEqual(rebuilt.active_patch_count, 1)
        self.assertEqual(rebuilt.rebuilt_assertion_count, 1)

    def test_received_revision_makes_prior_belief_stale_without_new_stance(self):
        first = SemanticPatch(
            patch_id="initial",
            event_id="e1",
            semantic_version="v04.1",
            propositions=(
                Proposition(
                    proposition_id="p_old",
                    canonical_text="The approved label is Marin",
                    source_event_ids=("e1",),
                ),
            ),
            assertions=(
                CognitiveAssertion(
                    assertion_id="source_old",
                    assertion_type=AssertionType.SOURCE_ASSERTION,
                    proposition_id="p_old",
                    valid_time=T0,
                    system_record_time=T0,
                    evidence_event_ids=("e1",),
                ),
                CognitiveAssertion(
                    assertion_id="belief_old",
                    assertion_type=AssertionType.BELIEF_ESTIMATE,
                    subject_agent_id="alice",
                    proposition_id="p_old",
                    belief_stance=BeliefStance.AFFIRM,
                    valid_time=T0,
                    system_record_time=T0,
                    evidence_event_ids=("e1",),
                ),
            ),
        )
        self.store.apply_patch(0, first)

        t1 = "2026-01-01T11:00:00+00:00"
        self.store.append_event(
            EventRecord(
                event_id="e2",
                valid_time=t1,
                recorded_at=t1,
                raw_text="Correction: the approved label is Marina",
                source_id="source",
                actor_id="source",
                recipient_ids=("alice",),
            )
        )
        correction = SemanticPatch(
            patch_id="correction",
            event_id="e2",
            semantic_version="v04.1",
            propositions=(
                Proposition(
                    proposition_id="p_new",
                    canonical_text="The approved label is Marina",
                    source_event_ids=("e2",),
                ),
            ),
            assertions=(
                CognitiveAssertion(
                    assertion_id="revision",
                    assertion_type=AssertionType.PROPOSITION_REVISION,
                    proposition_id="p_new",
                    related_proposition_id="p_old",
                    valid_time=t1,
                    system_record_time=t1,
                    evidence_event_ids=("e2",),
                ),
                CognitiveAssertion(
                    assertion_id="exposure_new",
                    assertion_type=AssertionType.INFORMATION_EXPOSURE,
                    subject_agent_id="alice",
                    proposition_id="p_new",
                    valid_time=t1,
                    system_record_time=t1,
                    evidence_event_ids=("e2",),
                ),
            ),
        )
        self.store.apply_patch(1, correction)

        current = self.store.build_view(None, None, None, "What does Alice believe now?")
        belief_old = next(
            item
            for item in current.relevant_assertions
            if item["assertion_id"] == "belief_old"
        )
        self.assertEqual(
            belief_old["projection_status"],
            "STALE_AFTER_REVISION_EXPOSURE",
        )
        conflicts = [
            item
            for item in current.unresolved_conflicts
            if item.get("conflict_type") == "REVISION_STANCE_UNRESOLVED"
        ]
        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0]["prior_proposition_id"], "p_old")
        self.assertEqual(conflicts[0]["revision_proposition_id"], "p_new")
        self.assertTrue(
            any(
                "received revision does not establish acceptance" in item.lower()
                for item in current.unsupported_conclusions
            )
        )

        before_correction = self.store.build_view(
            None, T0, None, "What did Alice believe before the correction?"
        )
        historical_belief = next(
            item
            for item in before_correction.relevant_assertions
            if item["assertion_id"] == "belief_old"
        )
        self.assertNotIn("projection_status", historical_belief)
        self.assertFalse(
            any(
                item.get("conflict_type") == "REVISION_STANCE_UNRESOLVED"
                for item in before_correction.unresolved_conflicts
            )
        )

    def test_later_explicit_stance_resolves_revision_uncertainty(self):
        self.test_received_revision_makes_prior_belief_stale_without_new_stance()

        t2 = "2026-01-01T12:00:00+00:00"
        self.store.append_event(
            EventRecord(
                event_id="e3",
                valid_time=t2,
                recorded_at=t2,
                raw_text="Alice confirms that she accepts Marina",
                source_id="alice",
                actor_id="alice",
                observer_ids=("alice",),
            )
        )
        accepted = SemanticPatch(
            patch_id="accepted",
            event_id="e3",
            semantic_version="v04.1",
            assertions=(
                CognitiveAssertion(
                    assertion_id="belief_new",
                    assertion_type=AssertionType.BELIEF_ESTIMATE,
                    subject_agent_id="alice",
                    proposition_id="p_new",
                    belief_stance=BeliefStance.AFFIRM,
                    valid_time=t2,
                    system_record_time=t2,
                    evidence_event_ids=("e3",),
                ),
            ),
        )
        self.store.apply_patch(2, accepted)
        current = self.store.build_view(None, None, None, "What does Alice believe now?")
        self.assertFalse(
            any(
                item.get("conflict_type") == "REVISION_STANCE_UNRESOLVED"
                for item in current.unresolved_conflicts
            )
        )
        belief_new = next(
            item
            for item in current.relevant_assertions
            if item["assertion_id"] == "belief_new"
        )
        self.assertEqual(belief_new["belief_stance"], "AFFIRM")

    def test_revision_requires_existing_related_proposition(self):
        patch = SemanticPatch(
            patch_id="bad_revision",
            event_id="e1",
            semantic_version="v04.1",
            propositions=(
                Proposition(
                    proposition_id="p_new",
                    canonical_text="Replacement",
                    source_event_ids=("e1",),
                ),
            ),
            assertions=(
                CognitiveAssertion(
                    assertion_id="bad_revision_assertion",
                    assertion_type=AssertionType.PROPOSITION_REVISION,
                    proposition_id="p_new",
                    related_proposition_id="missing_old",
                    valid_time=T0,
                    system_record_time=T0,
                    evidence_event_ids=("e1",),
                ),
            ),
        )
        with self.assertRaises(SchemaValidationError):
            self.store.apply_patch(0, patch)

    def test_invalidating_prior_patch_cascades_to_revision_and_rebuilds(self):
        self.test_received_revision_makes_prior_belief_stale_without_new_stance()
        receipt = self.store.invalidate(
            ["initial"],
            "prior semantic interpretation was withdrawn",
        )
        self.assertIn("revision", receipt.invalidated_assertion_ids)
        rebuilt = self.store.rebuild()
        self.assertGreaterEqual(rebuilt.active_patch_count, 1)
        current = self.store.build_view(None, None, None, "current")
        self.assertFalse(
            any(
                item["assertion_type"] == "PROPOSITION_REVISION"
                for item in current.relevant_assertions
            )
        )

    def test_revision_target_cannot_be_invented_in_same_patch(self):
        patch = SemanticPatch(
            patch_id="invented_revision_pair",
            event_id="e1",
            semantic_version="v04.1",
            propositions=(
                Proposition(
                    proposition_id="invented_old",
                    canonical_text="Old value invented by this patch",
                    source_event_ids=("e1",),
                ),
                Proposition(
                    proposition_id="invented_new",
                    canonical_text="New value",
                    source_event_ids=("e1",),
                ),
            ),
            assertions=(
                CognitiveAssertion(
                    assertion_id="invented_revision",
                    assertion_type=AssertionType.PROPOSITION_REVISION,
                    proposition_id="invented_new",
                    related_proposition_id="invented_old",
                    valid_time=T0,
                    system_record_time=T0,
                    evidence_event_ids=("e1",),
                ),
            ),
        )
        with self.assertRaisesRegex(
            SchemaValidationError,
            "revision target must be an existing prior proposition",
        ):
            self.store.apply_patch(0, patch)

    def test_exposure_before_revision_relation_does_not_stale_prior_belief(self):
        initial = SemanticPatch(
            patch_id="initial_pair",
            event_id="e1",
            semantic_version="v04.1",
            propositions=(
                Proposition(
                    proposition_id="p_old",
                    canonical_text="Old value",
                    source_event_ids=("e1",),
                ),
                Proposition(
                    proposition_id="p_new",
                    canonical_text="New value",
                    source_event_ids=("e1",),
                ),
            ),
            assertions=(
                CognitiveAssertion(
                    assertion_id="belief_old",
                    assertion_type=AssertionType.BELIEF_ESTIMATE,
                    subject_agent_id="alice",
                    proposition_id="p_old",
                    belief_stance=BeliefStance.AFFIRM,
                    valid_time=T0,
                    system_record_time=T0,
                    evidence_event_ids=("e1",),
                ),
            ),
        )
        self.store.apply_patch(0, initial)

        early_record = "2026-01-01T10:15:00+00:00"
        self.store.append_event(
            EventRecord(
                event_id="early_exposure",
                valid_time=T0,
                recorded_at=early_record,
                raw_text="Alice hears the phrase New value",
                source_id="source",
                actor_id="source",
                recipient_ids=("alice",),
            )
        )
        self.store.apply_patch(
            1,
            SemanticPatch(
                patch_id="early_exposure_patch",
                event_id="early_exposure",
                semantic_version="v04.1",
                assertions=(
                    CognitiveAssertion(
                        assertion_id="early_exposure_assertion",
                        assertion_type=AssertionType.INFORMATION_EXPOSURE,
                        subject_agent_id="alice",
                        proposition_id="p_new",
                        valid_time=T0,
                        system_record_time=early_record,
                        evidence_event_ids=("early_exposure",),
                    ),
                ),
            ),
        )

        t1 = "2026-01-01T11:00:00+00:00"
        self.store.append_event(
            EventRecord(
                event_id="later_revision",
                valid_time=t1,
                recorded_at=t1,
                raw_text="A source now identifies New value as a correction of Old value",
                source_id="source",
                actor_id="source",
            )
        )
        self.store.apply_patch(
            2,
            SemanticPatch(
                patch_id="later_revision_patch",
                event_id="later_revision",
                semantic_version="v04.1",
                assertions=(
                    CognitiveAssertion(
                        assertion_id="later_revision_assertion",
                        assertion_type=AssertionType.PROPOSITION_REVISION,
                        proposition_id="p_new",
                        related_proposition_id="p_old",
                        valid_time=t1,
                        system_record_time=t1,
                        evidence_event_ids=("later_revision",),
                    ),
                ),
            ),
        )

        current = self.store.build_view(None, None, None, "current")
        belief_old = next(
            item
            for item in current.relevant_assertions
            if item["assertion_id"] == "belief_old"
        )
        self.assertNotIn("projection_status", belief_old)
        self.assertFalse(
            any(
                item.get("conflict_type") == "REVISION_STANCE_UNRESOLVED"
                for item in current.unresolved_conflicts
            )
        )

    def test_same_valid_time_uses_record_time_for_post_exposure_stance(self):
        initial = SemanticPatch(
            patch_id="initial_old",
            event_id="e1",
            semantic_version="v04.1",
            propositions=(
                Proposition(
                    proposition_id="p_old",
                    canonical_text="Old value",
                    source_event_ids=("e1",),
                ),
                Proposition(
                    proposition_id="p_new",
                    canonical_text="New value",
                    source_event_ids=("e1",),
                ),
            ),
            assertions=(
                CognitiveAssertion(
                    assertion_id="belief_old",
                    assertion_type=AssertionType.BELIEF_ESTIMATE,
                    subject_agent_id="alice",
                    proposition_id="p_old",
                    belief_stance=BeliefStance.AFFIRM,
                    valid_time=T0,
                    system_record_time=T0,
                    evidence_event_ids=("e1",),
                ),
            ),
        )
        self.store.apply_patch(0, initial)

        same_valid = "2026-01-01T11:00:00+00:00"
        stance_record = "2026-01-01T10:30:00+00:00"
        self.store.append_event(
            EventRecord(
                event_id="pre_recorded_stance",
                valid_time=same_valid,
                recorded_at=stance_record,
                raw_text="Earlier system record suggests Alice accepts New value",
                source_id="source",
                actor_id="source",
            )
        )
        self.store.apply_patch(
            1,
            SemanticPatch(
                patch_id="pre_recorded_stance_patch",
                event_id="pre_recorded_stance",
                semantic_version="v04.1",
                assertions=(
                    CognitiveAssertion(
                        assertion_id="belief_new_pre",
                        assertion_type=AssertionType.BELIEF_ESTIMATE,
                        subject_agent_id="alice",
                        proposition_id="p_new",
                        belief_stance=BeliefStance.AFFIRM,
                        valid_time=same_valid,
                        system_record_time=stance_record,
                        evidence_event_ids=("pre_recorded_stance",),
                    ),
                ),
            ),
        )

        exposure_record = "2026-01-01T11:30:00+00:00"
        self.store.append_event(
            EventRecord(
                event_id="revision_exposure",
                valid_time=same_valid,
                recorded_at=exposure_record,
                raw_text="Correction delivered to Alice: New value replaces Old value",
                source_id="source",
                actor_id="source",
                recipient_ids=("alice",),
            )
        )
        self.store.apply_patch(
            2,
            SemanticPatch(
                patch_id="revision_exposure_patch",
                event_id="revision_exposure",
                semantic_version="v04.1",
                assertions=(
                    CognitiveAssertion(
                        assertion_id="revision_same_time",
                        assertion_type=AssertionType.PROPOSITION_REVISION,
                        proposition_id="p_new",
                        related_proposition_id="p_old",
                        valid_time=same_valid,
                        system_record_time=exposure_record,
                        evidence_event_ids=("revision_exposure",),
                    ),
                    CognitiveAssertion(
                        assertion_id="exposure_same_time",
                        assertion_type=AssertionType.INFORMATION_EXPOSURE,
                        subject_agent_id="alice",
                        proposition_id="p_new",
                        valid_time=same_valid,
                        system_record_time=exposure_record,
                        evidence_event_ids=("revision_exposure",),
                    ),
                ),
            ),
        )

        current = self.store.build_view(None, None, None, "current")
        self.assertTrue(
            any(
                item.get("conflict_type") == "REVISION_STANCE_UNRESOLVED"
                for item in current.unresolved_conflicts
            )
        )


if __name__ == "__main__":
    unittest.main()
