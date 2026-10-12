"""Independent hand-computable belief/goal/action model changes."""

from dataclasses import replace
from fractions import Fraction
from itertools import product
import unittest

from hcl.operators.agency import Action, PlanModel, solve_action_values, mixed_policy
from hcl.operators.epistemic import remaining_states, update_perspectives
from tests.test_unified_s3_epistemic import initial, closure


def route_model():
    states = ("open", "closed", "detour", "success", "failure")
    identity = {s: s for s in states}
    observation = {s: s for s in states}
    direct = Action(
        "direct",
        "1",
        ("open", "closed"),
        ("open",),
        dict(identity, open="success", closed="failure"),
        observation,
    )
    detour = Action(
        "detour-start",
        "1",
        ("open", "closed"),
        ("open", "closed"),
        dict(identity, open="detour", closed="detour"),
        observation,
    )
    finish = Action(
        "finish",
        "2",
        ("detour",),
        ("detour",),
        dict(identity, detour="success"),
        observation,
    )
    return PlanModel(
        states,
        ("success", "failure"),
        {s: "6" if s == "success" else "0" for s in states},
        (direct, detour, finish),
    )


class PlanningComputationTests(unittest.TestCase):
    def test_actual_epistemic_result_changes_q_without_changing_goal_or_cost(self):
        model = route_model()
        unknown, _ = update_perspectives(initial(), closure())
        informed, _ = update_perspectives(initial(), closure(True))
        results = []
        for mental in (unknown, informed):
            physical = remaining_states(mental, ("alice",))["values"]
            # One distinct remaining state has probability one; no uniform
            # probabilities are invented for multiple alternative states.
            possible = {"open" if row["open"] else "closed" for row in physical}
            self.assertEqual(len(possible), 1)
            results.append(
                solve_action_values(
                    model, {next(iter(possible)): "1"}, 2, actual_state="closed"
                )
            )
        self.assertEqual(results[0]["q"], {"direct": "5", "detour-start": "3"})
        self.assertEqual(results[1]["q"], {"direct": "-1", "detour-start": "3"})
        self.assertEqual(results[0]["best_actions"], ["direct"])
        self.assertEqual(results[1]["best_actions"], ["detour-start"])
        self.assertTrue(results[0]["subjective_feasibility"]["direct"])
        self.assertFalse(results[0]["world_feasibility"]["direct"])
        self.assertEqual(model.actions[0].cost, "1")
        self.assertEqual(model.utilities["success"], "6")

    def test_information_action_value_depends_on_actual_observation_channel(self):
        states = ("L", "R", "success", "failure")
        identity = {s: s for s in states}
        utility = {s: "6" if s == "success" else "0" for s in states}
        guess_left = Action(
            "left",
            "0",
            ("L", "R"),
            ("L",),
            dict(identity, L="success", R="failure"),
            identity,
        )
        guess_right = Action(
            "right",
            "0",
            ("L", "R"),
            ("R",),
            dict(identity, L="failure", R="success"),
            identity,
        )
        peek = Action("peek", "1", ("L", "R"), ("L", "R"), identity, identity)
        model = PlanModel(
            states, ("success", "failure"), utility, (guess_left, guess_right, peek)
        )
        belief = {"L": "1/2", "R": "1/2"}
        result = solve_action_values(model, belief, 2)
        self.assertEqual(result["q"], {"left": "3", "right": "3", "peek": "5"})
        self.assertEqual(result["best_actions"], ["peek"])
        blinded = replace(
            model,
            actions=(
                guess_left,
                guess_right,
                replace(peek, observations={s: "same" for s in states}),
            ),
        )
        result = solve_action_values(blinded, belief, 2)
        self.assertEqual(result["q"]["peek"], "2")
        self.assertEqual(result["best_actions"], ["left", "right"])

    def test_finite_dp_matches_independent_sequence_enumeration(self):
        for target_a, target_b, cost_a, cost_b, horizon in product(
            ("s", "goal"), ("s", "goal"), ("1", "2"), ("1", "2"), (1, 2, 3)
        ):
            states = ("s", "goal")
            actions = tuple(
                Action(
                    name,
                    cost,
                    ("s",),
                    ("s",),
                    {"s": target, "goal": "goal"},
                    {"s": "s", "goal": "goal"},
                )
                for name, cost, target in (
                    ("a", cost_a, target_a),
                    ("b", cost_b, target_b),
                )
            )
            model = PlanModel(states, ("goal",), {"s": "0", "goal": "7"}, actions)
            actual = solve_action_values(model, {"s": "1"}, horizon)["q"]
            for first in (0, 1):
                values = []
                for continuation in product((0, 1), repeat=horizon - 1):
                    state = "s"
                    paid = 0
                    for selected in (first, *continuation):
                        if state == "goal":
                            break
                        action = actions[selected]
                        paid += int(action.cost)
                        state = action.transitions[state]
                    values.append((7 if state == "goal" else 0) - paid)
                self.assertEqual(
                    Fraction(actual[actions[first].action_id]), max(values)
                )

    def test_declared_mixture_can_predict_habitual_nonoptimal_action(self):
        q = solve_action_values(route_model(), {"closed": "1"}, 2)["q"]
        habitual = mixed_policy(
            q,
            beta="1",
            rational_weight="0",
            habit_weight="1",
            error_weight="0",
            habit={"direct": "1", "detour-start": "0"},
        )
        self.assertEqual(
            habitual["probabilities"], {"direct": 1.0, "detour-start": 0.0}
        )
        rational = mixed_policy(
            q,
            beta="1",
            rational_weight="1",
            habit_weight="0",
            error_weight="0",
            habit={"direct": "1", "detour-start": "0"},
        )
        self.assertGreater(rational["probabilities"]["detour-start"], 0.98)
        self.assertAlmostEqual(sum(rational["probabilities"].values()), 1)

    def test_budget_and_invalid_probability_do_not_fabricate_q(self):
        result = solve_action_values(route_model(), {"open": "1"}, 2, max_expansions=1)
        self.assertEqual(result["status"], "FRONTIER_UNEXPLORED")
        self.assertEqual(result["q"], {})
        for weights in (
            {"open": "2"},
            {"open": 0.5, "closed": 0.5},
            {"open": "-1", "closed": "2"},
        ):
            with self.assertRaises(ValueError):
                solve_action_values(route_model(), weights, 2)
