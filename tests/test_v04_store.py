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


if __name__ == "__main__":
    unittest.main()
