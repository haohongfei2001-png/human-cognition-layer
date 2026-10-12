"""Independent complete-labelling oracle and real structured proof changes."""

from itertools import product
import unittest
from hcl.operators.argumentation import (
    Literal,
    Premise,
    Rule,
    Theory,
    grounded,
    preferred_extensions,
    evaluate_arguments,
    claim_acceptance,
    critical_retractions,
)


class ArgumentationComputationTests(unittest.TestCase):
    def test_all_530_small_graphs_match_independent_complete_labelling_oracle(self):
        count = 0
        for size in (1, 2, 3):
            nodes = tuple(str(i) for i in range(size))
            possible = tuple(product(nodes, repeat=2))
            for flags in product((False, True), repeat=len(possible)):
                edges = tuple(pair for pair, flag in zip(possible, flags) if flag)
                complete = []
                for colors in product(("IN", "OUT", "UNDEC"), repeat=size):
                    labels = dict(zip(nodes, colors))
                    valid = True
                    for node in nodes:
                        incoming = [labels[a] for a, b in edges if b == node]
                        expected = (
                            "OUT"
                            if "IN" in incoming
                            else "IN" if all(v == "OUT" for v in incoming) else "UNDEC"
                        )
                        if labels[node] != expected:
                            valid = False
                            break
                    if valid:
                        complete.append(
                            {node for node in nodes if labels[node] == "IN"}
                        )
                least = next(
                    group
                    for group in complete
                    if all(group <= other for other in complete)
                )
                actual = grounded(nodes, edges)
                self.assertEqual(actual["status"], "COMPLETE")
                self.assertEqual(set(actual["grounded"]), least)
                expected_preferred = sorted(
                    tuple(sorted(group))
                    for group in complete
                    if not any(group < other for other in complete)
                )
                actual_preferred = preferred_extensions(nodes, edges)
                self.assertEqual(actual_preferred["status"], "COMPLETE")
                self.assertEqual(
                    list(actual_preferred["preferred"]), expected_preferred
                )
                count += 1
        self.assertEqual(count, 530)

    def test_grounded_is_not_skeptical_preferred(self):
        nodes = ("A", "B", "C", "D")
        edges = (("A", "B"), ("B", "A"), ("A", "C"), ("B", "C"), ("C", "D"))
        self.assertEqual(grounded(nodes, edges)["grounded"], ())
        extensions = preferred_extensions(nodes, edges)
        self.assertEqual(extensions["preferred"], (("A", "D"), ("B", "D")))
        self.assertEqual(
            preferred_extensions(nodes, edges, max_work=1)["status"],
            "FRONTIER_UNEXPLORED",
        )
        self.assertEqual(
            preferred_extensions(nodes, edges, max_work=1)["preferred"], ()
        )

    def test_attack_on_subargument_defeats_its_superarguments(self):
        p, q, r = Literal("p"), Literal("q"), Literal("r")
        theory = Theory(
            (Premise("p", p), Premise("not-p", Literal("p", True), ordinary=False)),
            (Rule("p-q", (p,), q, strict=True), Rule("q-r", (q,), r, strict=True)),
        )
        result = evaluate_arguments(theory)
        self.assertEqual(claim_acceptance(result, p), (False, True))
        self.assertEqual(claim_acceptance(result, q), (False, False))
        self.assertEqual(claim_acceptance(result, r), (False, False))
        targets = {
            result["arguments"][attack["target"]].conclusion
            for attack in result["attacks"]
            if attack["kind"] == "UNDERMINING"
        }
        self.assertEqual(targets, {p, q, r})

    def test_priority_changes_defeat_not_the_fact_or_original_attack(self):
        p = Literal("p")
        n = Literal("p", True)
        bare = Theory((Premise("p", p), Premise("n", n)), ())
        undecided = evaluate_arguments(bare)
        self.assertEqual(claim_acceptance(undecided, p), (False, False))
        preferred = evaluate_arguments(Theory(bare.premises, (), (("p", "n"),)))
        self.assertEqual(claim_acceptance(preferred, p), (True, False))
        self.assertEqual(len(preferred["attacks"]), len(undecided["attacks"]))
        self.assertEqual(len(preferred["defeats"]), 1)
        self.assertEqual(bare.priorities, ())

    def test_undercutting_defeats_rule_even_when_rule_has_priority(self):
        p, q = Literal("p"), Literal("q")
        undercut = Literal("r", True, kind="RULE_APPLICABLE")
        theory = Theory(
            (Premise("p", p, ordinary=False), Premise("u", undercut)),
            (Rule("r", (p,), q),),
            (("r", "u"),),
        )
        result = evaluate_arguments(theory)
        self.assertEqual(claim_acceptance(result, q), (False, False))
        attacks = [a for a in result["attacks"] if a["kind"] == "UNDERCUTTING"]
        self.assertTrue(attacks)
        self.assertTrue(all(not a["blocked_by_priority"] for a in attacks))

    def test_rootless_cycle_and_retracted_assumption_cannot_create_acceptance(self):
        p, q = Literal("p"), Literal("q")
        rules = (Rule("p-q", (p,), q), Rule("q-p", (q,), p))
        self.assertFalse(evaluate_arguments(Theory((), rules))["arguments"])
        theory = Theory((Premise("p", p, assumptions={"A"}),), rules)
        self.assertFalse(evaluate_arguments(theory)["arguments"])
        result = evaluate_arguments(
            Theory(theory.premises, rules, active_assumptions={"A"})
        )
        self.assertEqual(claim_acceptance(result, q), (True, False))
        self.assertIn("q-p", result["excluded_circular_rules"])

    def test_scope_noninterference_and_budget_frontier_do_not_guess_positions(self):
        p = Literal("p")
        other = Literal("p", True, scope="other")
        theory = Theory((Premise("p", p), Premise("other", other)), ())
        result = evaluate_arguments(theory)
        self.assertEqual(result["attacks"], ())
        self.assertEqual(claim_acceptance(result, p), (True, False))
        incomplete = evaluate_arguments(theory, max_work=1)
        self.assertEqual(incomplete["status"], "FRONTIER_UNEXPLORED")
        self.assertEqual(incomplete["labels"], {})
        self.assertLessEqual(incomplete["work"], 1)

    def test_actual_two_support_retractions_prove_minimum_disagreement(self):
        p, r, q, irrelevant = map(Literal, ("p", "r", "q", "unrelated"))
        theory = Theory(
            (Premise("p", p), Premise("r", r), Premise("u", irrelevant)),
            (Rule("pq", (p,), q), Rule("rq", (r,), q)),
        )
        before = evaluate_arguments(theory)
        self.assertEqual(claim_acceptance(before, q), (True, False))
        result = critical_retractions(theory, q, ("p", "r", "u"))
        self.assertEqual(result["edits"], ("p", "r"))
        self.assertEqual(result["minimum_cardinality"], 2)
        self.assertEqual(result["before"], (True, False))
        self.assertEqual(result["after"], (False, False))
        self.assertEqual(claim_acceptance(evaluate_arguments(theory), q), (True, False))

    def test_strict_conflict_is_reported_without_explosion_or_erasing_evidence(self):
        p = Literal("p")
        q = Literal("q")
        theory = Theory(
            (
                Premise("p", p, ordinary=False),
                Premise("not-p", Literal("p", True), ordinary=False),
            ),
            (),
        )
        result = evaluate_arguments(theory)
        self.assertEqual(result["theory_consistency"], "INCONSISTENT_STRICT_CORE")
        self.assertEqual(len(result["strict_conflicts"]), 1)
        self.assertEqual(claim_acceptance(result, p), (True, True))
        self.assertEqual(claim_acceptance(result, q), (False, False))

    def test_graph_generators_duplicates_and_preferred_maximality_obey_bound(self):
        expected = grounded(("a", "b"), (("a", "b"),))
        self.assertEqual(
            grounded(iter(("a", "b")), iter((("a", "b"), ("a", "b"))))["labels"],
            expected["labels"],
        )
        all_clear = preferred_extensions(
            tuple(str(i) for i in range(8)), (), max_work=500
        )
        self.assertEqual(all_clear["status"], "FRONTIER_UNEXPLORED")
        self.assertLessEqual(all_clear["work"], 500)
        self.assertEqual(all_clear["preferred"], ())
        for names, edges in [
            (("a", "a"), ()),
            (("a",), (("a", "missing"),)),
            (("a",), (("a",),)),
        ]:
            with self.assertRaises(ValueError):
                grounded(names, edges)
            with self.assertRaises(ValueError):
                preferred_extensions(names, edges)
