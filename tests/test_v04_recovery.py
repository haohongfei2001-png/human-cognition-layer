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


T0 = "2026-01-01T10:00:00+00:00"
T1 = "2026-01-01T11:00:00+00:00"
R0 = "2026-01-01T10:05:00+00:00"
R1 = "2026-01-01T11:05:00+00:00"


def apply(store, patch):
    return store.apply_patch(store.state_version, patch)


class V04RecoveryTests(unittest.TestCase):
    def test_local_invalidation_preserves_unrelated_state(self):
        store = CognitionStore()
        try:
            for event_id, agent in (("e1", "alice"), ("e2", "bob")):
                store.append_event(
                    EventRecord(
                        event_id=event_id,
                        valid_time=T0,
                        raw_text=f"{agent} receives information",
                        source_id="source",
                        actor_id="source",
                        recipient_ids=(agent,),
                    )
                )
            apply(
                store,
                SemanticPatch(
                    patch_id="p1",
                    event_id="e1",
                    semantic_version="v04.1",
                    propositions=(Proposition("pa", "A", source_event_ids=("e1",)),),
                    assertions=(
                        CognitiveAssertion(
                            assertion_id="aa",
                            assertion_type=AssertionType.INFORMATION_EXPOSURE,
                            subject_agent_id="alice",
                            proposition_id="pa",
                            valid_time=T0,
                            system_record_time=R0,
                            evidence_event_ids=("e1",),
                        ),
                    ),
                ),
            )
            apply(
                store,
                SemanticPatch(
                    patch_id="p2",
                    event_id="e2",
                    semantic_version="v04.1",
                    propositions=(Proposition("pb", "B", source_event_ids=("e2",)),),
                    assertions=(
                        CognitiveAssertion(
                            assertion_id="ab",
                            assertion_type=AssertionType.INFORMATION_EXPOSURE,
                            subject_agent_id="bob",
                            proposition_id="pb",
                            valid_time=T0,
                            system_record_time=R0,
                            evidence_event_ids=("e2",),
                        ),
                    ),
                ),
            )
            receipt = store.invalidate(["aa"], "bad parse")
            self.assertIn("aa", receipt.invalidated_assertion_ids)
            system_view = store.build_view(None, None, None, "q")
            ids = {x["assertion_id"] for x in system_view.relevant_assertions}
            self.assertNotIn("aa", ids)
            self.assertIn("ab", ids)
        finally:
            store.close()

    def test_invalidated_patch_is_not_reintroduced_by_rebuild(self):
        store = CognitionStore()
        try:
            store.append_event(
                EventRecord(
                    event_id="e1",
                    valid_time=T0,
                    raw_text="Alice receives P",
                    source_id="source",
                    actor_id="source",
                    recipient_ids=("alice",),
                )
            )
            apply(
                store,
                SemanticPatch(
                    patch_id="bad_patch",
                    event_id="e1",
                    semantic_version="v04.1",
                    propositions=(Proposition("p", "P", source_event_ids=("e1",)),),
                    assertions=(
                        CognitiveAssertion(
                            assertion_id="a",
                            assertion_type=AssertionType.INFORMATION_EXPOSURE,
                            subject_agent_id="alice",
                            proposition_id="p",
                            valid_time=T0,
                            system_record_time=R0,
                            evidence_event_ids=("e1",),
                        ),
                    ),
                ),
            )
            store.invalidate(["bad_patch"], "identity/timeline defect")
            rebuilt = store.rebuild()
            self.assertEqual(rebuilt.active_patch_count, 0)
            self.assertEqual(rebuilt.rebuilt_assertion_count, 0)
            self.assertEqual(
                store.build_view(None, None, None, "q").relevant_assertions,
                (),
            )
        finally:
            store.close()

    def test_later_system_discovery_does_not_rewrite_historical_cutoff(self):
        store = CognitionStore()
        try:
            store.append_event(
                EventRecord(
                    event_id="old",
                    valid_time=T0,
                    recorded_at=R0,
                    raw_text="Alice believes three.",
                    source_id="alice",
                    actor_id="alice",
                    observer_ids=("alice",),
                )
            )
            apply(
                store,
                SemanticPatch(
                    patch_id="old_patch",
                    event_id="old",
                    semantic_version="v04.1",
                    propositions=(Proposition("three", "three", source_event_ids=("old",)),),
                    assertions=(
                        CognitiveAssertion(
                            assertion_id="old_belief",
                            assertion_type=AssertionType.BELIEF_ESTIMATE,
                            belief_stance=BeliefStance.AFFIRM,
                            subject_agent_id="alice",
                            proposition_id="three",
                            valid_time=T0,
                            system_record_time=R0,
                            evidence_event_ids=("old",),
                        ),
                    ),
                ),
            )
            store.append_event(
                EventRecord(
                    event_id="later",
                    valid_time=T0,
                    recorded_at=R1,
                    raw_text="System later discovers the meeting was four.",
                    source_id="archive",
                    actor_id="archive",
                    observer_ids=("__system__",),
                )
            )
            apply(
                store,
                SemanticPatch(
                    patch_id="later_patch",
                    event_id="later",
                    semantic_version="v04.1",
                    propositions=(Proposition("four", "four", source_event_ids=("later",)),),
                    assertions=(
                        CognitiveAssertion(
                            assertion_id="later_fact",
                            assertion_type=AssertionType.SCENE_FACT,
                            proposition_id="four",
                            valid_time=T0,
                            system_record_time=R1,
                            evidence_event_ids=("later",),
                        ),
                    ),
                ),
            )
            historical = store.build_view(
                None,
                event_time=T0,
                knowledge_cutoff="2026-01-01T10:30:00+00:00",
                query="what was known then?",
            )
            ids = {x["assertion_id"] for x in historical.relevant_assertions}
            self.assertIn("old_belief", ids)
            self.assertNotIn("later_fact", ids)
        finally:
            store.close()

    def test_dependency_invalidation_cascades(self):
        store = CognitionStore()
        try:
            store.append_event(
                EventRecord(
                    event_id="e1",
                    valid_time=T0,
                    raw_text="Alice receives P and acts.",
                    source_id="source",
                    actor_id="source",
                    recipient_ids=("alice",),
                )
            )
            apply(
                store,
                SemanticPatch(
                    patch_id="p1",
                    event_id="e1",
                    semantic_version="v04.1",
                    propositions=(Proposition("p", "P", source_event_ids=("e1",)),),
                    assertions=(
                        CognitiveAssertion(
                            assertion_id="base",
                            assertion_type=AssertionType.INFORMATION_EXPOSURE,
                            subject_agent_id="alice",
                            proposition_id="p",
                            valid_time=T0,
                            system_record_time=R0,
                            evidence_event_ids=("e1",),
                        ),
                        CognitiveAssertion(
                            assertion_id="derived",
                            assertion_type=AssertionType.BELIEF_ESTIMATE,
                            belief_stance=BeliefStance.AFFIRM,
                            subject_agent_id="alice",
                            proposition_id="p",
                            valid_time=T0,
                            system_record_time=R0,
                            evidence_event_ids=("e1",),
                            depends_on_assertion_ids=("base",),
                        ),
                    ),
                ),
            )
            receipt = store.invalidate(["base"], "base invalid")
            self.assertEqual(
                set(receipt.invalidated_assertion_ids),
                {"base", "derived"},
            )
            store.rebuild()
            self.assertEqual(
                store.build_view(None, None, None, "current").relevant_assertions,
                (),
            )
        finally:
            store.close()

    def test_past_system_cutoff_survives_later_invalidation_and_rebuild(self):
        store = CognitionStore()
        try:
            store.append_event(
                EventRecord(
                    event_id="e1", valid_time=T0, recorded_at=R0,
                    raw_text="Alice was told P", source_id="source",
                    actor_id="source", recipient_ids=("alice",),
                )
            )
            apply(store, SemanticPatch(
                patch_id="p1", event_id="e1", semantic_version="v04.1",
                propositions=(Proposition("p", "P", source_event_ids=("e1",)),),
                assertions=(CognitiveAssertion(
                    assertion_id="a", assertion_type=AssertionType.INFORMATION_EXPOSURE,
                    subject_agent_id="alice", proposition_id="p", valid_time=T0,
                    system_record_time=R0, evidence_event_ids=("e1",),
                ),),
            ))
            cutoff = "2026-01-01T10:30:00+00:00"
            before = store.build_view("alice", T0, cutoff, "What had HCL recorded?")
            self.assertEqual([item["assertion_id"] for item in before.relevant_assertions], ["a"])
            self.assertEqual(before.relevant_assertions[0]["proposition_text"], "P")

            store.invalidate(["p1"], "later parser correction")
            self.assertEqual(store.build_view(None, T0, None, "current").relevant_assertions, ())
            self.assertEqual(
                store.build_view("alice", T0, cutoff, "What had HCL recorded?").relevant_assertions,
                before.relevant_assertions,
            )
            store.rebuild()
            self.assertEqual(store.build_view(None, T0, None, "current").relevant_assertions, ())
            self.assertEqual(
                store.build_view("alice", T0, cutoff, "What had HCL recorded?").relevant_assertions,
                before.relevant_assertions,
            )
            self.assertEqual(
                store.build_view(None, T0, "2030-01-01T00:00:00+00:00", "later").relevant_assertions,
                (),
            )
        finally:
            store.close()

    def test_reused_ids_do_not_relabel_or_hide_pre_correction_history(self):
        store = CognitionStore()
        try:
            for event_id, at, text in (("old", R0, "P"), ("new", R1, "Q")):
                store.append_event(EventRecord(
                    event_id=event_id, valid_time=T0, recorded_at=at,
                    raw_text=text, source_id="source", actor_id="source",
                    recipient_ids=("alice",),
                ))
            apply(store, SemanticPatch(
                patch_id="old_patch", event_id="old", semantic_version="v04.1",
                propositions=(Proposition("p", "P", source_event_ids=("old",)),),
                assertions=(CognitiveAssertion(
                    assertion_id="a", assertion_type=AssertionType.INFORMATION_EXPOSURE,
                    subject_agent_id="alice", proposition_id="p", valid_time=T0,
                    system_record_time=R0, evidence_event_ids=("old",),
                ),),
            ))
            store.invalidate(["old_patch"], "replace bad parse")
            store.rebuild()
            apply(store, SemanticPatch(
                patch_id="new_patch", event_id="new", semantic_version="v04.1",
                propositions=(Proposition("p", "Q", source_event_ids=("new",)),),
                assertions=(CognitiveAssertion(
                    assertion_id="a", assertion_type=AssertionType.INFORMATION_EXPOSURE,
                    subject_agent_id="alice", proposition_id="p", valid_time=T0,
                    system_record_time=R1, evidence_event_ids=("new",),
                ),),
            ))
            before = store.build_view("alice", T0, "2026-01-01T10:30:00+00:00", "before")
            after = store.build_view("alice", T0, "2030-01-01T00:00:00+00:00", "after")
            self.assertEqual(before.relevant_assertions[0]["proposition_text"], "P")
            self.assertEqual(after.relevant_assertions[0]["proposition_text"], "Q")
            self.assertEqual(len(after.relevant_assertions), 1)
        finally:
            store.close()

    def test_historical_view_does_not_leak_later_proposition_source(self):
        store = CognitionStore()
        try:
            store.append_event(EventRecord(
                event_id="old", valid_time=T0, recorded_at=R0,
                raw_text="Alice heard a claim", source_id="public",
                actor_id="source", recipient_ids=("alice",),
            ))
            store.append_event(EventRecord(
                event_id="later", valid_time=T0, recorded_at=R1,
                raw_text="Later archive identifies the content", source_id="archive",
                actor_id="archive", observer_ids=("__system__",),
            ))
            apply(store, SemanticPatch(
                patch_id="p1", event_id="old", semantic_version="v04.1",
                propositions=(Proposition("p", "private later content", source_event_ids=("later",)),),
                assertions=(CognitiveAssertion(
                    assertion_id="a", assertion_type=AssertionType.SOURCE_ASSERTION,
                    proposition_id="p", valid_time=T0, system_record_time=R0,
                    evidence_event_ids=("old",),
                ),),
            ))
            self.assertEqual(
                store.build_view(None, T0, "2026-01-01T10:30:00+00:00", "past").relevant_assertions,
                (),
            )
            self.assertEqual(store.build_view("alice", T0, None, "alice").relevant_assertions, ())
        finally:
            store.close()


if __name__ == "__main__":
    unittest.main()
