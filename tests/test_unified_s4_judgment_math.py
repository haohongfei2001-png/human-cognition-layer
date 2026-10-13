"""Independent small finite oracles for joint outcome and normative choices."""

from fractions import Fraction
from itertools import product
import unittest

from hcl.operators.judgment import JudgmentWork, joint_outcomes, compare_framework


def outcomes(vectors):
    return [dict(action_id=a, feasible=True, scenarios=[dict(scenario_id=str(i), vector={d: str(v) for d, v in row.items()})
                                                       for i, row in enumerate(rows)]) for a, rows in vectors.items()]


def framework(weights=None, rule="PARETO", norms=()):
    return dict(weights=weights, decision_rule=rule, norms=list(norms))


class JudgmentMathematicsTests(unittest.TestCase):
    def solve(self, vectors, weights=None, rule="PARETO", norms=(), states=None):
        dimensions = [dict(id=d) for d in next(iter(vectors.values()))[0]]
        return compare_framework(framework(weights, rule, norms), outcomes(vectors), states or {}, dimensions, JudgmentWork(100000))

    def test_joint_maximin_never_manufactures_independent_worst_vector(self):
        result = self.solve(dict(A=[dict(care=10, freedom=0), dict(care=0, freedom=10)],
                                 B=[dict(care=4, freedom=4), dict(care=4, freedom=4)]),
                            dict(care="1/2", freedom="1/2"), "MAXIMIN")
        self.assertEqual(result["worst_scores"], dict(A="5", B="4"))
        self.assertEqual(result["recommended"], ["A"])
        self.assertEqual(result["comparisons"][0]["minimum_weighted_difference"], "1")

    def test_unknown_weights_keep_real_tradeoffs_and_exact_boundary_ties(self):
        vectors = dict(X=[dict(x=10,y=0)], Y=[dict(x=6,y=6)], Z=[dict(x=0,y=10)])
        self.assertEqual(self.solve(vectors)["pareto"], ["X", "Y", "Z"])
        self.assertEqual(self.solve(vectors)["recommended"], [])
        for x, expected in [("0", ["Z"]), ("2/5", ["Y", "Z"]), ("1/2", ["Y"]), ("3/5", ["X", "Y"]), ("1", ["X"])]:
            result = self.solve(vectors, dict(x=x, y=str(1-Fraction(x))), "EXPECTED")
            self.assertEqual(result["recommended"], expected)

    def test_fraction_expectation_is_computed_from_same_action_transition(self):
        graph = dict(terminal=["a1", "a2", "b1", "b2"], actions=[
            dict(id="A", enabled=["s1", "s2"], feasible=["s1", "s2"], transitions=dict(s1="a1",s2="a2")),
            dict(id="B", enabled=["s1", "s2"], feasible=["s1", "s2"], transitions=dict(s1="b1",s2="b2"))])
        dims = [dict(id="u", state_values=dict(a1="8",a2="-1",b1="2",b2="3"), action_costs=dict(A="0",B="0"))]
        actual = joint_outcomes(graph,dims,[dict(id="p",distribution=dict(s1="1/3",s2="2/3"))],["s1","s2"],["s1","s2"],JudgmentWork(100))
        result = compare_framework(framework(dict(u="1"),"EXPECTED"), actual, {}, dims, JudgmentWork(100))
        self.assertEqual(result["scenario_scores"], dict(A=dict(p="2"),B=dict(p="8/3")))
        self.assertEqual(result["recommended"], ["B"])

    def test_hard_and_unknown_constraints_are_not_compensated_by_rewards(self):
        vectors = dict(A=[dict(x=100)], B=[dict(x=-5)])
        norm=dict(id="right",permitted_actions=["B"])
        for state,status in [("ACTIVE","PROHIBITED"),("UNRESOLVED","PERMISSION_UNRESOLVED")]:
            result=self.solve(vectors,dict(x="1"),"EXPECTED",[norm],dict(right=state))
            self.assertEqual(result["recommended"],["B"])
            self.assertEqual(result["eligibility"][0]["status"],status)
        result=self.solve(vectors,dict(x="1"),"EXPECTED",[dict(id="ban",permitted_actions=[])],dict(ban="ACTIVE"))
        self.assertEqual(result["recommended"],[])
        self.assertEqual(result["recommendation_basis"],"NO_DEFINITELY_PERMITTED_ACTION")

    def test_pareto_matches_independent_exhaustive_oracle_including_negative_values(self):
        for values in product((-1, 0, 1), repeat=6):
            points=dict(zip(("a","b","c"),(values[:2],values[2:4],values[4:])))
            expected=sorted(a for a,p in points.items() if not any(
                b!=a and all(y>=x for x,y in zip(p,q)) and any(y>x for x,y in zip(p,q))
                for b,q in points.items()))
            result=self.solve({a:[dict(x=p[0],y=p[1])] for a,p in points.items()})
            self.assertEqual(result["pareto"],expected)

    def test_explicit_zero_weight_and_all_ties_are_preserved(self):
        result=self.solve(dict(a=[dict(x=-100,y=2)],b=[dict(x=100,y=2)]),dict(x="0",y="1"),"EXPECTED")
        self.assertEqual(result["recommended"],["a","b"])

    def test_maximin_tie_does_not_recommend_a_dominated_option(self):
        result=self.solve(dict(a=[dict(x=1),dict(x=2)],b=[dict(x=1),dict(x=3)]),dict(x="1"),"MAXIMIN")
        self.assertEqual(result["pareto"],["b"])
        self.assertEqual(result["recommended"],["b"])

    def test_budget_cannot_return_a_fake_complete_frontier(self):
        with self.assertRaises(OverflowError):
            compare_framework(framework(),outcomes(dict(a=[dict(x=1)],b=[dict(x=2)])),{},[dict(id="x")],JudgmentWork(1))


if __name__ == "__main__":
    unittest.main()
