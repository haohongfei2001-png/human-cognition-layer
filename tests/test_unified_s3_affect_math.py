"""Independent numeric consequences and actual M05 feedback, not emotion fixtures."""

from dataclasses import replace
from fractions import Fraction
import unittest
from hcl.operators.agency import Action, PlanModel, solve_action_values
from hcl.operators.affect import (
    appraise,
    control,
    generate_affect_hypotheses,
    update_coping,
)


class AffectMathTests(unittest.TestCase):
    def graph(self, feasible=True):
        states = ("bad", "neutral", "good")
        actions = tuple(
            Action(
                name,
                "0",
                states,
                states if feasible or name == "wait" else (),
                {s: s if name == "wait" else target for s in states},
                {s: s for s in states},
            )
            for name, target in [
                ("wait", "neutral"),
                ("repair", "good"),
                ("avoid", "bad"),
            ]
        )
        return PlanModel(
            states, (), {"bad": "-3", "neutral": "0", "good": "5"}, actions
        )

    def test_same_event_opposite_goals_and_no_fabricated_expectation(self):
        good = appraise(
            {"bad": "-3", "neutral": "0", "good": "5"}, ["neutral"], ["bad"]
        )
        other = appraise(
            {"bad": "3", "neutral": "0", "good": "-5"}, ["neutral"], ["bad"]
        )
        self.assertEqual(good["change_direction"], ("NEGATIVE",))
        self.assertEqual(other["change_direction"], ("POSITIVE",))
        self.assertEqual(good["expectation_gap_direction"], ("UNCOMPUTED",))
        expected = appraise(
            {"bad": "-3", "neutral": "0", "good": "5"},
            ["neutral"],
            ["bad"],
            expected_states=["good"],
        )
        self.assertEqual(expected["state_change"]["lower"], "-3")
        self.assertEqual(expected["expectation_gap"]["lower"], "-8")
        ambiguous = appraise(
            {"bad": "-3", "neutral": "0", "good": "5"}, ["neutral"], ["bad", "good"]
        )
        self.assertEqual(ambiguous["desirability"], ("NEGATIVE", "ZERO", "POSITIVE"))
        self.assertEqual(
            ambiguous["current_value"]["status"], "UNWEIGHTED_POSSIBILITIES"
        )

    def test_control_requires_feasibility_not_just_positive_computed_q(self):
        for feasible in (True, False):
            graph = self.graph(feasible)
            actual = solve_action_values(graph, {"bad": "1"}, 1, actual_state="bad")
            self.assertEqual(actual["q"]["repair"], "5")
            result = control(graph.utilities, {"bad": actual}, actual_states=["bad"])
            self.assertEqual("repair" in result["robust_improvement"], feasible)
            self.assertEqual(
                result["actions"]["repair"]["actual_world_feasibility"]["bad"], feasible
            )

    def test_actual_appraisal_changes_goal_priorities_and_m05_action_values(self):
        graph = self.graph()
        utilities = {
            "safety": dict(graph.utilities),
            "duty": {s: str(-Fraction(v)) for s, v in graph.utilities.items()},
        }
        actual = {
            s: solve_action_values(graph, {s: "1"}, 1, actual_state=s)
            for s in graph.states
        }

        def profiles(current):
            return [
                dict(
                    goal_id=g,
                    appraisal=appraise(u, ["neutral"], [current]),
                    control=control(u, {current: actual[current]}),
                )
                for g, u in utilities.items()
            ]

        condition = dict(
            goal_id="safety", dimension="change_direction", value="NEGATIVE"
        )
        model = dict(
            adjustments=[
                dict(
                    id="threat-focus",
                    conditions=[condition],
                    multipliers={"safety": "3", "duty": "1"},
                )
            ]
        )
        outcomes = []
        for current in ("bad", "good"):
            # Fix the planning belief: only the computed appraisal input changes.
            result = update_coping(
                model, profiles(current), utilities, {"safety": "1/2", "duty": "1/2"}
            )
            branch = result["branches"][0]
            value = solve_action_values(
                replace(graph, utilities=branch["utilities"]), {"bad": "1"}, 1
            )
            outcomes.append(value["q"])
            self.assertTrue(branch["hypothetical"])
        self.assertEqual(outcomes[0]["repair"], "5/2")
        self.assertEqual(outcomes[0]["avoid"], "-3/2")
        self.assertEqual(set(outcomes[1].values()), {"0"})
        severed = update_coping(
            dict(adjustments=[]),
            profiles("bad"),
            utilities,
            {"safety": "1/2", "duty": "1/2"},
        )
        self.assertEqual(set(severed["branches"][0]["utilities"].values()), {"0"})

    def test_competing_semantic_mappings_keep_unknown_and_do_not_read_expressions(self):
        profile = dict(
            goal_id="g",
            appraisal=appraise({"bad": "-1", "good": "1"}, ["good"], ["bad", "good"]),
            control=dict(status="UNCOMPUTED"),
        )
        mappings = [
            dict(
                id="loss",
                label="sadness-candidate",
                conditions=[
                    dict(goal_id="g", dimension="change_direction", value="NEGATIVE")
                ],
            ),
            dict(
                id="hope",
                label="hope-candidate",
                conditions=[dict(goal_id="g", dimension="control", value="IMPROVABLE")],
            ),
        ]
        results = generate_affect_hypotheses([profile], mappings)
        self.assertEqual([r["status"] for r in results], ["POSSIBLE", "POSSIBLE"])
        self.assertTrue(all("HYPOTHESIS" in r["scope"] for r in results))

    def test_random_exact_appraisal_and_feedback_against_direct_fraction_oracle(self):
        import random

        rng = random.Random(8301)
        for _ in range(80):
            utility = {s: str(rng.randint(-12, 12)) for s in ("bad", "neutral", "good")}
            other = {s: str(rng.randint(-12, 12)) for s in utility}
            left = rng.randint(1, 9)
            weights = {
                "bad": str(Fraction(left, 10)),
                "good": str(Fraction(10 - left, 10)),
            }
            computed = appraise(
                utility,
                ["neutral"],
                ["bad", "good"],
                current_weights=weights,
                expected_states=["good"],
            )
            exact = Fraction(weights["bad"]) * int(utility["bad"]) + Fraction(
                weights["good"]
            ) * int(utility["good"])
            self.assertEqual(Fraction(computed["current_value"]["lower"]), exact)
            self.assertEqual(
                Fraction(computed["state_change"]["lower"]),
                exact - int(utility["neutral"]),
            )
            self.assertEqual(
                Fraction(computed["expectation_gap"]["lower"]),
                exact - int(utility["good"]),
            )
            profile = dict(
                goal_id="first", appraisal=computed, control=dict(status="UNCOMPUTED")
            )
            model = dict(
                adjustments=[
                    dict(
                        id="conditional",
                        conditions=[
                            dict(
                                goal_id="first",
                                dimension="change_direction",
                                value="NEGATIVE",
                            )
                        ],
                        multipliers={"first": "2", "second": "1"},
                    )
                ]
            )
            updated = update_coping(
                model,
                [profile],
                {"first": utility, "second": other},
                {"first": "1/2", "second": "1/2"},
            )
            ratio = (
                Fraction(2, 3)
                if exact - int(utility["neutral"]) < 0
                else Fraction(1, 2)
            )
            expected = {
                s: ratio * int(utility[s]) + (1 - ratio) * int(other[s])
                for s in utility
            }
            branch = updated["branches"][0]
            self.assertEqual(
                {s: Fraction(v) for s, v in branch["utilities"].items()}, expected
            )
            graph = replace(self.graph(), utilities=branch["utilities"])
            planning = solve_action_values(graph, {"bad": "1"}, 1)
            self.assertEqual(Fraction(planning["q"]["repair"]), expected["good"])
            self.assertEqual(Fraction(planning["q"]["wait"]), expected["bad"])

    def test_exact_alias_comparison_rejects_color_indistinguishable_cycles(self):
        from copy import deepcopy
        from hcl.operators.affect import compare_goal_models

        states = list("abcdef")
        six = dict(
            states=states,
            terminal=[],
            utilities={s: "0" for s in states},
            bindings={s: [] for s in states},
            actions={
                "go": dict(
                    cost="0",
                    enabled=states,
                    feasible=states,
                    transitions=dict(zip(states, states[1:] + states[:1])),
                    observations={s: "same" for s in states},
                )
            },
        )
        two = deepcopy(six)
        two["actions"]["go"]["transitions"] = dict(zip(states, list("bcaefd")))
        self.assertEqual(
            compare_goal_models(six, two, max_work=100)["status"], "DIFFERENT"
        )
        for bound in range(10):
            result = compare_goal_models(six, two, max_work=bound)
            self.assertLessEqual(result["work"], bound)
            self.assertIn(result["status"], ("DIFFERENT", "UNRESOLVED"))
            self.assertFalse(result["state_aliases"])
        alias = deepcopy(six)
        rename = {s: "alias-" + s for s in states}
        alias.update(
            states=list(rename.values()),
            utilities={rename[s]: v for s, v in six["utilities"].items()},
            bindings={rename[s]: [] for s in states},
        )
        a = alias["actions"]["go"]
        a.update(
            enabled=list(rename.values()),
            feasible=list(rename.values()),
            transitions={
                rename[s]: rename[t]
                for s, t in six["actions"]["go"]["transitions"].items()
            },
            observations={rename[s]: "renamed-class" for s in states},
        )
        result = compare_goal_models(six, alias, max_work=100)
        self.assertEqual(result["status"], "EQUIVALENT")
        self.assertEqual(len(set(result["state_aliases"].values())), 6)
        # Splitting an observation class is a real model change.
        a["observations"][rename["a"]] = "new-information"
        self.assertEqual(
            compare_goal_models(six, alias, max_work=100)["status"], "DIFFERENT"
        )


if __name__ == "__main__":
    unittest.main()
