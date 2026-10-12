"""Independent exhaustive path oracle for bounded longitudinal comparison."""

import itertools
import random
import unittest
from hcl.operators.relationships import longitudinal_search


class LongitudinalMathTests(unittest.TestCase):
    def test_segment_search_matches_full_enumeration_and_keeps_zero_change(self):
        rng = random.Random(9021)
        for _ in range(25):
            models = {k: {"complexity": rng.randint(1, 4)} for k in ("a", "b", "c")}
            observations = [
                dict(
                    id=str(i),
                    at=i,
                    factor_id="event-" + str(i // 2),
                    values=[rng.randrange(2)],
                )
                for i in range(5)
            ]
            matrix = {
                k: [
                    dict(status="COMPUTED", values=[rng.randrange(2)])
                    for _ in observations
                ]
                for k in models
            }
            result = longitudinal_search(
                matrix,
                observations,
                models,
                max_segments=3,
                max_work=10000,
                max_states=10000,
            )
            self.assertEqual(result["status"], "COMPLETE_WITHIN_DECLARED_LIBRARY")
            expected = {}
            for path in itertools.product(models, repeat=5):
                starts = [i for i in range(5) if i == 0 or path[i] != path[i - 1]]
                if len(starts) > 3:
                    continue
                flags = {}
                for i, obs in enumerate(observations):
                    flags.setdefault(obs["factor_id"], []).append(
                        matrix[path[i]][i]["values"] == obs["values"]
                    )
                expected[path] = dict(
                    explained={k for k, v in flags.items() if all(v)},
                    contradicted={k for k, v in flags.items() if not all(v)},
                    complexity=sum(models[path[i]]["complexity"] for i in starts)
                    + len(starts)
                    - 1,
                )
            self.assertEqual(
                {tuple(r["path"]) for r in result["trajectories"]}, set(expected)
            )

            def dominates(a, b):
                return (
                    a["explained"] >= b["explained"]
                    and a["contradicted"] <= b["contradicted"]
                    and a["complexity"] <= b["complexity"]
                    and a != b
                )

            retained = {
                p
                for p, b in expected.items()
                if not any(dominates(a, b) for q, a in expected.items() if q != p)
            }
            actual = {
                tuple(r["path"])
                for r in result["trajectories"]
                if r["trajectory_id"] in result["pareto_explored"]
            }
            self.assertEqual(actual, retained)
            for model in models:
                self.assertIn((model,) * 5, expected)

    def test_repeated_factor_does_not_get_extra_support_and_bounds_stay_open(self):
        models = {"stable": {"complexity": 1}, "other": {"complexity": 1}}
        observations = [
            dict(id=str(i), at=i, factor_id="same-evidence", values=[True])
            for i in range(6)
        ]
        matrix = {
            k: [dict(status="COMPUTED", values=[k == "stable"]) for _ in observations]
            for k in models
        }
        complete = longitudinal_search(
            matrix, observations, models, max_segments=1, max_work=100, max_states=100
        )
        self.assertEqual(complete["work"], 12)
        row = next(r for r in complete["trajectories"] if r["path"][0] == "stable")
        self.assertEqual(row["profile"]["explained"], ("same-evidence",))
        for allowance in range(0, 40):
            result = longitudinal_search(
                matrix,
                observations,
                models,
                max_segments=3,
                max_work=allowance,
                max_states=100,
            )
            self.assertLessEqual(result["work"], allowance)
            self.assertEqual(result["status"], "PARTIAL")
            self.assertEqual(result["global_comparison"], "NOT_ESTABLISHED")

    def test_conditional_relationship_updates_against_fraction_oracle(self):
        from fractions import Fraction
        from hcl.operators.relationships import relationship_history
        import random

        rng = random.Random(902)
        for _ in range(60):
            a = rng.randint(1, 8)
            prior = {
                "capable": str(Fraction(a, 10)),
                "limited": str(Fraction(10 - a, 10)),
            }
            factors = []
            exact = {k: Fraction(v) for k, v in prior.items()}
            for t in range(4):
                row = {k: str(Fraction(rng.randint(1, 9), 10)) for k in exact}
                factors.append(
                    dict(
                        at=t,
                        factor_id=str(t),
                        likelihoods=row,
                        qualification="ESTABLISHED_IN_CONDITIONAL_MODEL",
                    )
                )
                exact = {k: v * Fraction(row[k]) for k, v in exact.items()}
                total = sum(exact.values())
                exact = {k: v / total for k, v in exact.items()}
            result = relationship_history(tuple(prior), prior, factors, max_work=1000)
            self.assertEqual(
                {k: Fraction(v) for k, v in result["weights"].items()}, exact
            )
            repeated = relationship_history(
                tuple(prior), prior, [*factors, dict(factors[-1], at=5)], max_work=1000
            )
            self.assertEqual(repeated["weights"], result["weights"])
            self.assertEqual(
                repeated["history"][-1]["update"], "REPEATED_FACTOR_NOT_MULTIPLIED"
            )
            unknown = relationship_history(tuple(prior), None, factors, max_work=1000)
            self.assertIsNone(unknown["weights"])
            self.assertEqual(set(unknown["compatible_hypotheses"]), set(prior))

    def test_late_resolution_and_correlated_conflict_recompute_only_affected_factor(
        self,
    ):
        from hcl.operators.relationships import relationship_history

        prior = {"good": "1/2", "bad": "1/2"}
        a = dict(
            at=0,
            factor_id="a",
            likelihoods={"good": "3/4", "bad": "1/4"},
            qualification="UNRESOLVED",
        )
        b = dict(
            at=1,
            factor_id="b",
            likelihoods={"good": "1/2", "bad": "1/4"},
            qualification="ESTABLISHED_IN_CONDITIONAL_MODEL",
        )
        resolved = dict(a, at=2, qualification="ESTABLISHED_IN_CONDITIONAL_MODEL")
        conflict = dict(resolved, at=3, likelihoods={"good": "1/4", "bad": "3/4"})
        full = relationship_history(
            prior, prior, [a, b, resolved, conflict], max_work=100
        )
        self.assertEqual(full["history"][0]["weights"], prior)
        self.assertEqual(full["history"][2]["weights"], {"good": "6/7", "bad": "1/7"})
        self.assertEqual(full["weights"], {"good": "2/3", "bad": "1/3"})
        self.assertEqual(full["applied_factor_ids"], ("b",))
        self.assertEqual(full["frontier"], ("RELATIONSHIP_CORRELATED_FACTOR_CONFLICT",))
        for budget in range(full["work"] + 1):
            result = relationship_history(
                prior, prior, [a, b, resolved, conflict], max_work=budget
            )
            self.assertLessEqual(result["work"], budget)
            if budget < full["work"]:
                self.assertIn("RELATIONSHIP_UPDATE_FRONTIER", result["frontier"])

    def test_role_conflicts_and_reconciliation_use_actual_opportunities(self):
        from hcl.operators.relationships import role_reconciliation

        requirements = [
            dict(id="friend", condition_values=(True,), actions=["help", "call"]),
            dict(id="employee", condition_values=(True,), actions=["leave", "call"]),
        ]
        conflicted = role_reconciliation(requirements, ["help", "leave"], max_work=100)
        self.assertEqual(
            conflicted["branches"][0]["minimal_incompatible_role_sets"],
            (("friend", "employee"),),
        )
        self.assertEqual(
            conflicted["branches"][0]["feasible_reconciliation_actions"], ()
        )
        reconciled = role_reconciliation(
            requirements, ["help", "leave", "call"], max_work=100
        )
        self.assertEqual(
            reconciled["branches"][0]["minimal_incompatible_role_sets"], ()
        )
        self.assertEqual(
            reconciled["branches"][0]["feasible_reconciliation_actions"], ("call",)
        )
        requirements[1]["condition_values"] = (False, True)
        ambiguous = role_reconciliation(requirements, ["help", "leave"], max_work=100)
        self.assertEqual(len(ambiguous["branches"]), 2)
        for budget in range(ambiguous["work"]):
            limited = role_reconciliation(
                requirements, ["help", "leave"], max_work=budget
            )
            self.assertEqual(limited["status"], "PARTIAL")
            self.assertLessEqual(limited["work"], budget)
