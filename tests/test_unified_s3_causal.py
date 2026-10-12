"""Hand-enumerated observation/do/withdrawal contrasts through the pure adapter."""

import unittest
from hcl.v09.runtime import CausalModel, StructuralRule
from hcl.operators.causal import evaluate_counterfactual


class CausalComputationTests(unittest.TestCase):
    def setUp(self):
        self.model = CausalModel(
            "m",
            "event",
            ("U", "X", "Y"),
            ("U",),
            (
                StructuralRule("X", "U", "X follows U"),
                StructuralRule("Y", "X ^ U", "Y is X xor U"),
            ),
        )

    def test_observation_intervention_and_withdrawal_are_three_different_computations(
        self,
    ):
        observation = evaluate_counterfactual(self.model, "Y", observations={"X": 0})
        intervention = evaluate_counterfactual(self.model, "Y", interventions={"X": 0})
        counterfactual = evaluate_counterfactual(
            self.model, "Y", observations={"X": 1}, interventions={"X": 0}
        )
        self.assertEqual(observation["possible_values"], [0])
        self.assertEqual(intervention["possible_values"], [0, 1])
        self.assertEqual(counterfactual["possible_values"], [1])
        self.assertEqual(counterfactual["traces"][0]["exogenous"], {"U": 1})
        withdrawn = evaluate_counterfactual(self.model, "Y")
        self.assertEqual(withdrawn["possible_values"], [0])
        self.assertEqual(withdrawn["world_count"], 2)
        self.assertNotEqual(
            withdrawn["possible_values"], intervention["possible_values"]
        )

    def test_all_boolean_interventions_match_independent_hand_table(self):
        for observed in ({}, {"X": 0}, {"X": 1}):
            for intervention in ({}, {"X": 0}, {"X": 1}, {"Y": 0}, {"Y": 1}):
                expected = []
                for u in (0, 1):
                    factual = {"U": u, "X": u, "Y": 0}
                    if any(factual[k] != v for k, v in observed.items()):
                        continue
                    x = intervention.get("X", u)
                    y = intervention.get("Y", x ^ u)
                    expected.append(y)
                actual = evaluate_counterfactual(
                    self.model, "Y", observations=observed, interventions=intervention
                )
                self.assertEqual(actual["possible_values"], sorted(set(expected)))

    def test_inconsistent_observation_and_budget_frontier_do_not_become_false(self):
        result = evaluate_counterfactual(self.model, "Y", observations={"X": 0, "Y": 1})
        self.assertEqual(result["status"], "INCONSISTENT_OBSERVATIONS")
        self.assertIsNone(result["value"])
        result = evaluate_counterfactual(self.model, "Y", max_world_evaluations=3)
        self.assertEqual(result["status"], "FRONTIER_UNEXPLORED")
        self.assertEqual(result["traces"], [])
