from __future__ import annotations

import unittest

from hcl.v04 import (
    AssertionType,
    CognitiveAssertion,
    CognitionStore,
    EventRecord,
    Proposition,
    SemanticPatch,
)
from hcl.v04.model import utc_now_iso


T0 = "2026-01-01T10:00:00+00:00"
T1 = "2026-01-01T11:00:00+00:00"


def apply(store, patch):
    return store.apply_patch(store.state_version, patch)


class V04PerspectiveTests(unittest.TestCase):
    def test_private_exposure_is_not_visible_to_other_agent(self):
        store = CognitionStore()
        try:
            store.append_event(
                EventRecord(
                    event_id="e1",
                    valid_time=T0,
                    raw_text="Alice privately receives P",
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
                    propositions=(
                        Proposition("prop", "P", source_event_ids=("e1",)),
                    ),
                    assertions=(
                        CognitiveAssertion(
                            assertion_id="exp",
                            assertion_type=AssertionType.INFORMATION_EXPOSURE,
                            subject_agent_id="alice",
                            proposition_id="prop",
                            valid_time=T0,
                            system_record_time=utc_now_iso(),
                            evidence_event_ids=("e1",),
                        ),
                    ),
                ),
            )
            alice = store.build_view("alice", None, None, "q")
            bob = store.build_view("bob", None, None, "q")
            self.assertEqual(len(alice.relevant_assertions), 1)
            self.assertEqual(bob.relevant_assertions, ())
            self.assertTrue(alice.unsupported_conclusions)
        finally:
            store.close()

    def test_correction_not_received_does_not_change_agent_view(self):
        store = CognitionStore()
        try:
            store.append_event(
                EventRecord(
                    event_id="old",
                    valid_time=T0,
                    raw_text="Alice is told the meeting is at three.",
                    source_id="notice",
                    actor_id="notice",
                    recipient_ids=("alice",),
                )
            )
            apply(
                store,
                SemanticPatch(
                    patch_id="old_patch",
                    event_id="old",
                    semantic_version="v04.1",
                    propositions=(
                        Proposition("three", "meeting is at three", source_event_ids=("old",)),
                    ),
                    assertions=(
                        CognitiveAssertion(
                            assertion_id="alice_belief_three",
                            assertion_type=AssertionType.BELIEF_ESTIMATE,
                            subject_agent_id="alice",
                            proposition_id="three",
                            valid_time=T0,
                            system_record_time=utc_now_iso(),
                            evidence_event_ids=("old",),
                        ),
                    ),
                ),
            )
            store.append_event(
                EventRecord(
                    event_id="correction",
                    valid_time=T1,
                    raw_text="Bob receives a correction: meeting is at four.",
                    source_id="organizer",
                    actor_id="organizer",
                    recipient_ids=("bob",),
                )
            )
            apply(
                store,
                SemanticPatch(
                    patch_id="new_patch",
                    event_id="correction",
                    semantic_version="v04.1",
                    propositions=(
                        Proposition("four", "meeting is at four", source_event_ids=("correction",)),
                    ),
                    assertions=(
                        CognitiveAssertion(
                            assertion_id="fact_four",
                            assertion_type=AssertionType.SCENE_FACT,
                            proposition_id="four",
                            valid_time=T1,
                            system_record_time=utc_now_iso(),
                            evidence_event_ids=("correction",),
                        ),
                    ),
                ),
            )
            alice = store.build_view("alice", None, None, "meeting?")
            ids = {x["assertion_id"] for x in alice.relevant_assertions}
            self.assertIn("alice_belief_three", ids)
            self.assertNotIn("fact_four", ids)
        finally:
            store.close()

    def test_received_but_rejected_can_preserve_old_belief(self):
        store = CognitionStore()
        try:
            store.append_event(
                EventRecord(
                    event_id="e1",
                    valid_time=T0,
                    raw_text="Alice believes the meeting is at three.",
                    source_id="alice",
                    actor_id="alice",
                    observer_ids=("alice",),
                )
            )
            apply(
                store,
                SemanticPatch(
                    patch_id="p1",
                    event_id="e1",
                    semantic_version="v04.1",
                    propositions=(
                        Proposition("three", "meeting is at three", source_event_ids=("e1",)),
                    ),
                    assertions=(
                        CognitiveAssertion(
                            assertion_id="b3",
                            assertion_type=AssertionType.BELIEF_ESTIMATE,
                            subject_agent_id="alice",
                            proposition_id="three",
                            valid_time=T0,
                            system_record_time=utc_now_iso(),
                            evidence_event_ids=("e1",),
                        ),
                    ),
                ),
            )
            store.append_event(
                EventRecord(
                    event_id="e2",
                    valid_time=T1,
                    raw_text="Alice receives four but says she thinks it is a mistake.",
                    source_id="organizer",
                    actor_id="organizer",
                    recipient_ids=("alice",),
                )
            )
            apply(
                store,
                SemanticPatch(
                    patch_id="p2",
                    event_id="e2",
                    semantic_version="v04.1",
                    propositions=(
                        Proposition("four", "meeting is at four", source_event_ids=("e2",)),
                    ),
                    assertions=(
                        CognitiveAssertion(
                            assertion_id="exp4",
                            assertion_type=AssertionType.INFORMATION_EXPOSURE,
                            subject_agent_id="alice",
                            proposition_id="four",
                            valid_time=T1,
                            system_record_time=utc_now_iso(),
                            evidence_event_ids=("e2",),
                        ),
                        CognitiveAssertion(
                            assertion_id="b3_after",
                            assertion_type=AssertionType.BELIEF_ESTIMATE,
                            subject_agent_id="alice",
                            proposition_id="three",
                            valid_time=T1,
                            system_record_time=utc_now_iso(),
                            evidence_event_ids=("e2",),
                            depends_on_assertion_ids=("b3",),
                        ),
                    ),
                ),
            )
            view = store.build_view("alice", None, None, "meeting?")
            ids = {x["assertion_id"] for x in view.relevant_assertions}
            self.assertIn("exp4", ids)
            self.assertIn("b3_after", ids)
        finally:
            store.close()

    def test_hidden_background_change_does_not_change_viewer_context(self):
        def build(hidden_text):
            store = CognitionStore()
            store.append_event(
                EventRecord(
                    event_id="public",
                    valid_time=T0,
                    recorded_at="2026-01-01T10:01:00+00:00",
                    raw_text="Alice receives P.",
                    source_id="source",
                    actor_id="source",
                    recipient_ids=("alice",),
                )
            )
            apply(
                store,
                SemanticPatch(
                    patch_id="pub_patch",
                    event_id="public",
                    semantic_version="v04.1",
                    propositions=(
                        Proposition("p", "P", source_event_ids=("public",)),
                    ),
                    assertions=(
                        CognitiveAssertion(
                            assertion_id="exp",
                            assertion_type=AssertionType.INFORMATION_EXPOSURE,
                            subject_agent_id="alice",
                            proposition_id="p",
                            valid_time=T0,
                            system_record_time="2026-01-01T10:05:00+00:00",
                            evidence_event_ids=("public",),
                        ),
                    ),
                ),
            )
            store.append_event(
                EventRecord(
                    event_id="hidden",
                    valid_time=T1,
                    raw_text=hidden_text,
                    source_id="secret",
                    actor_id="secret",
                    recipient_ids=("bob",),
                )
            )
            apply(
                store,
                SemanticPatch(
                    patch_id="hidden_patch",
                    event_id="hidden",
                    semantic_version="v04.1",
                    propositions=(
                        Proposition("hidden_p", hidden_text, source_event_ids=("hidden",)),
                    ),
                    assertions=(
                        CognitiveAssertion(
                            assertion_id="hidden_fact",
                            assertion_type=AssertionType.SCENE_FACT,
                            proposition_id="hidden_p",
                            valid_time=T1,
                            system_record_time="2026-01-01T11:05:00+00:00",
                            evidence_event_ids=("hidden",),
                        ),
                    ),
                ),
            )
            view = store.build_view("alice", None, None, "q")
            store.close()
            return view

        one = build("secret world A")
        two = build("secret world B")
        self.assertEqual(one.relevant_assertions, two.relevant_assertions)
        self.assertEqual(one.evidence, two.evidence)


if __name__ == "__main__":
    unittest.main()
