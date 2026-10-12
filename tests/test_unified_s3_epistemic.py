"""Actual finite event/world computation, independent of language fixtures."""

from dataclasses import replace
from itertools import product
import unittest

from hcl.operators.epistemic import (
    EpistemicModel,
    EventModel,
    EpistemicLimits,
    query_belief,
    remaining_states,
    update_perspectives,
)


def atom(name="open"):
    return dict(op="atom", name=name)


def neg(arg):
    return dict(op="not", arg=arg)


def belief(agent, arg):
    return dict(op="believes", agent=agent, arg=arg)


def initial():
    return EpistemicModel(
        ("open",),
        ("alice", "bob"),
        {"w": {"open": True}},
        {agent: {"w": ["w"]} for agent in ("alice", "bob")},
        ("w",),
    )


def closure(seen_by_alice=False):
    return EventModel(
        "closure",
        {
            "close": {"pre": True, "post": {"open": False}},
            "skip": {"pre": True, "post": {}},
        },
        {
            "alice": {
                "close": ["close" if seen_by_alice else "skip"],
                "skip": ["skip"],
            },
            "bob": {"close": ["close"], "skip": ["skip"]},
        },
        ("close",),
        ("declared-visibility", "persistence-unless-update"),
    )


class EpistemicComputationTests(unittest.TestCase):
    def test_unseen_transition_produces_wrong_belief_without_a_belief_answer_input(
        self,
    ):
        old = initial()
        updated, receipt = update_perspectives(old, closure())
        self.assertEqual(receipt["status"], "APPLIED")
        self.assertEqual(query_belief(updated, atom())["possible_values"], [False])
        self.assertEqual(
            query_belief(updated, belief("alice", atom()))["possible_values"], [True]
        )
        self.assertEqual(
            query_belief(updated, belief("bob", neg(atom())))["possible_values"], [True]
        )
        self.assertEqual(
            query_belief(updated, belief("bob", belief("alice", atom())))[
                "possible_values"
            ],
            [True],
        )
        self.assertEqual(query_belief(old, atom())["possible_values"], [True])
        self.assertEqual(old.history, ())

    def test_only_observation_channel_changes_belief_and_preserves_actual_world(self):
        unseen, _ = update_perspectives(initial(), closure())
        seen, _ = update_perspectives(initial(), closure(True))
        self.assertEqual(
            query_belief(unseen, atom())["possible_values"],
            query_belief(seen, atom())["possible_values"],
        )
        self.assertEqual(
            query_belief(unseen, belief("alice", atom()))["possible_values"], [True]
        )
        self.assertEqual(
            query_belief(seen, belief("alice", atom()))["possible_values"], [False]
        )

    def test_trusted_received_message_revises_only_receiving_agents_view(self):
        before, _ = update_perspectives(initial(), closure())
        for receives, understands, trusts in product((False, True), repeat=3):
            accepted = receives and understands and trusts
            event = EventModel(
                "message",
                {
                    "actual": {"pre": True, "post": {}},
                    "accepted": {"pre": True, "post": {"open": False}},
                    "skip": {"pre": True, "post": {}},
                },
                {
                    "alice": {
                        "actual": ["accepted" if accepted else "skip"],
                        "accepted": ["accepted"],
                        "skip": ["skip"],
                    },
                    "bob": {"actual": ["skip"], "accepted": ["skip"], "skip": ["skip"]},
                },
                ("actual",),
                ("declared-reception-comprehension-trust",),
            )
            after, _ = update_perspectives(before, event)
            self.assertEqual(
                query_belief(after, belief("alice", atom()))["possible_values"],
                [not accepted],
            )
            self.assertEqual(
                query_belief(after, belief("bob", belief("alice", atom())))[
                    "possible_values"
                ],
                [True],
            )
            self.assertEqual(
                query_belief(before, belief("alice", atom()))["possible_values"], [True]
            )

    def test_outer_negation_is_not_inner_negation_and_empty_views_do_not_explode(self):
        model = EpistemicModel(
            ("open",),
            ("a",),
            {"x": {"open": True}, "y": {"open": False}},
            {"a": {"x": ["x", "y"], "y": []}},
            ("x",),
        )
        self.assertEqual(
            query_belief(model, neg(belief("a", atom())))["possible_values"], [True]
        )
        self.assertEqual(
            query_belief(model, belief("a", neg(atom())))["possible_values"], [False]
        )
        empty = replace(model, designated=("y",))
        self.assertEqual(
            query_belief(empty, belief("a", atom()))["possible_values"], [False, True]
        )
        self.assertEqual(remaining_states(empty, ("a",))["status"], "INCONSISTENT_VIEW")

    def test_nested_depth_world_and_work_bounds_never_emit_partial_certainty(self):
        model = initial()
        result = query_belief(
            model,
            belief("alice", belief("bob", atom())),
            replace(EpistemicLimits(), max_depth=1),
        )
        self.assertEqual(result["status"], "FRONTIER_UNEXPLORED")
        self.assertEqual(result["possible_values"], [False, True])
        for limits in (
            replace(EpistemicLimits(), max_worlds=1),
            replace(EpistemicLimits(), max_evaluations=1),
            replace(EpistemicLimits(), max_edges=1),
        ):
            updated, receipt = update_perspectives(model, closure(), limits)
            self.assertIsNone(updated)
            self.assertEqual(receipt["status"], "FRONTIER_UNEXPLORED")
        self.assertEqual(query_belief(model, atom())["possible_values"], [True])

    def test_modal_evaluation_matches_independent_boolean_oracle_on_all_small_relations(
        self,
    ):
        for bits in product((False, True), repeat=4):
            edges = {"x": [], "y": []}
            for enabled, (source, target) in zip(bits, product(("x", "y"), repeat=2)):
                if enabled:
                    edges[source].append(target)
            model = EpistemicModel(
                ("open",),
                ("a",),
                {"x": {"open": True}, "y": {"open": False}},
                {"a": edges},
                ("x",),
            )
            # Oracle directly enumerates one/two-hop destinations without the
            # production query evaluator or product-update code.
            first = edges["x"]
            expected = [False, True] if not first else [all(v == "x" for v in first)]
            self.assertEqual(
                query_belief(model, belief("a", atom()))["possible_values"], expected
            )
            expected_values = []
            for target in first:
                expected_values.append(
                    None if not edges[target] else all(v == "x" for v in edges[target])
                )
            nested = (
                [False, True]
                if not expected_values
                or (False not in expected_values and None in expected_values)
                else [all(expected_values)]
            )
            self.assertEqual(
                query_belief(model, belief("a", belief("a", atom())))[
                    "possible_values"
                ],
                nested,
            )

    def test_postconditions_are_simultaneous_and_invalid_effects_are_not_executable(
        self,
    ):
        model = EpistemicModel(
            ("p", "q"),
            ("a",),
            {"w": {"p": True, "q": False}},
            {"a": {"w": ["w"]}},
            ("w",),
        )
        event = EventModel(
            "swap",
            {"e": {"pre": True, "post": {"p": atom("q"), "q": atom("p")}}},
            {"a": {"e": ["e"]}},
            ("e",),
        )
        updated, _ = update_perspectives(model, event)
        self.assertEqual(
            dict(updated.worlds[updated.designated[0]]), {"p": False, "q": True}
        )
        with self.assertRaises(ValueError):
            update_perspectives(
                model,
                replace(
                    event,
                    variants={
                        "e": {"pre": True, "post": {"p": {"op": "exec", "code": "bad"}}}
                    },
                ),
            )

    def test_exact_bisimulation_preserves_nested_queries_and_repeated_event_capacity(
        self,
    ):
        raw, _ = update_perspectives(initial(), closure(), minimize=False)
        compact, _ = update_perspectives(initial(), closure())
        formulas = [atom(), neg(atom())]
        for depth in range(3):
            formulas += [
                belief(agent, formula)
                for agent in ("alice", "bob")
                for formula in tuple(formulas)
            ]
        for formula in formulas:
            self.assertEqual(
                query_belief(raw, formula)["possible_values"],
                query_belief(compact, formula)["possible_values"],
            )
        for i in range(20):
            compact, receipt = update_perspectives(
                compact, replace(closure(), event_id="closure-" + str(i))
            )
            self.assertEqual(receipt["status"], "APPLIED")
            self.assertLessEqual(len(compact.worlds), 4)
        self.assertEqual(
            query_belief(compact, belief("alice", atom()))["possible_values"], [True]
        )
        self.assertEqual(
            query_belief(compact, belief("bob", neg(atom())))["possible_values"], [True]
        )

    def test_query_and_remaining_view_share_explicit_profile_limits(self):
        model, _ = update_perspectives(initial(), closure())
        for limits in (EpistemicLimits(max_worlds=1), EpistemicLimits(max_edges=1)):
            result = query_belief(model, True, limits)
            self.assertEqual(result["status"], "FRONTIER_UNEXPLORED")
            remaining = remaining_states(model, ("alice",), limits)
            self.assertEqual(remaining["status"], "FRONTIER_UNEXPLORED")
            self.assertEqual(remaining["values"], ())
        result = remaining_states(model, ("alice",), EpistemicLimits(max_evaluations=1))
        self.assertEqual(result["status"], "FRONTIER_UNEXPLORED")
        self.assertEqual(result["evaluations"], 1)
