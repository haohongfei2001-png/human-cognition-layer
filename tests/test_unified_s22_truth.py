"""Actual support propagation and revision, independent small assignment oracle."""

from dataclasses import replace
import itertools
import random
import unittest

from hcl.kernel.truth import DerivationRule, EvidenceRoot, TruthKernel, TruthProfile, TruthProgram


def minimal(environments):
    return {env for env in environments if not any(other < env for other in environments)}


def oracle(program):
    # Membership closure for each assignment; no environment propagation code.
    labels = {claim: set() for claim in program.claims}
    names = sorted(program.active_assumptions)
    for flags in itertools.product((False, True), repeat=len(names)):
        environment = frozenset(name for name, flag in zip(names, flags) if flag)
        if any(nogood <= environment for nogood in program.nogoods):
            continue
        live = {root.claim_id for root in program.roots if root.active and root.assumptions <= environment}
        changed = True
        while changed:
            before = set(live)
            for rule in program.rules:
                if rule.enabled and set(rule.premises) <= live and rule.assumptions <= environment:
                    live.add(rule.conclusion)
            changed = live != before
        for claim in live:
            labels[claim].add(environment)
    return {claim: minimal(environments) for claim, environments in labels.items()}


class TruthKernelTests(unittest.TestCase):
    def fixture(self):
        roots = (
            EvidenceRoot("ra", "a", {"trust-a"}),
            EvidenceRoot("rb", "b", {"trust-b"}),
            EvidenceRoot("ro", "other"),
        )
        rules = (
            DerivationRule("a-q", ("a",), "q"),
            DerivationRule("b-q", ("b",), "q"),
            DerivationRule("q-tail", ("q",), "tail"),
            DerivationRule("cycle-a", ("c1",), "c2"),
            DerivationRule("cycle-b", ("c2",), "c1"),
            DerivationRule("b-opposed", ("b",), "not-q"),
        )
        return TruthProgram(
            ("a", "b", "q", "tail", "c1", "c2", "other", "not-q"), roots, rules, {"trust-a", "trust-b"}
        )

    def test_and_or_minimal_environments_and_independent_root_paths(self):
        program = self.fixture()
        program = replace(
            program,
            claims=program.claims + ("and-result",),
            rules=program.rules + (DerivationRule("and", ("a", "b"), "and-result"),),
        )
        result = TruthKernel().run(program)
        self.assertEqual(result.environments("q"), (frozenset({"trust-a"}), frozenset({"trust-b"})))
        self.assertEqual(result.environments("and-result"), (frozenset({"trust-a", "trust-b"}),))
        self.assertEqual(len(result.supports["q"]), 2)
        self.assertEqual(result.supports["and-result"][0].roots, frozenset({"ra", "rb"}))

    def test_withdraw_one_or_both_supports_preserves_unrelated_hash(self):
        program = self.fixture()
        kernel = TruthKernel()
        initial = kernel.run(program)
        one = replace(
            program,
            roots=tuple(
                replace(root, active=False) if root.root_id == "ra" else root for root in program.roots
            ),
        )
        first = kernel.revise(program, initial, one)
        self.assertTrue(first.state.supports["tail"])
        self.assertEqual(len(first.state.supports["q"]), 1)
        self.assertEqual(first.state.semantic_hash("other"), initial.semantic_hash("other"))
        self.assertNotIn("other", first.state.recomputed_claims)
        both = replace(
            one,
            roots=tuple(replace(root, active=False) if root.root_id == "rb" else root for root in one.roots),
        )
        second = kernel.revise(one, first.state, both)
        self.assertFalse(second.state.supports["tail"])
        self.assertIn("tail", second.changed_claims)
        self.assertIn("other", second.retained_claims)
        self.assertEqual(second.state.supports, kernel.run(both).supports)

    def test_rootless_cycles_cannot_bootstrap_or_retain_a_withdrawn_root(self):
        program = self.fixture()
        kernel = TruthKernel()
        self.assertFalse(kernel.run(program).supports["c1"])
        rooted = replace(program, roots=program.roots + (EvidenceRoot("rc", "c1"),))
        prior = kernel.run(rooted)
        self.assertTrue(prior.supports["c2"])
        revised = kernel.revise(rooted, prior, program)
        self.assertFalse(revised.state.supports["c1"])
        self.assertFalse(revised.state.supports["c2"])

    def test_explicit_nogood_does_not_turn_report_conflict_into_explosion(self):
        program = self.fixture()
        kernel = TruthKernel()
        state = kernel.run(program)
        bits = state.support_bits("q", "not-q")
        self.assertTrue(bits["positive_support"] and bits["negative_support"])
        self.assertFalse(state.supports["c1"])
        restricted = replace(program, nogoods=(frozenset({"trust-a"}),))
        result = kernel.revise(program, state, restricted).state
        self.assertEqual(result.environments("q"), (frozenset({"trust-b"}),))
        self.assertEqual(result.supports, kernel.run(restricted).supports)

    def test_assumption_activation_and_rule_retirement_recompute_affected_closure(self):
        program = self.fixture()
        kernel = TruthKernel()
        inactive = replace(program, active_assumptions=frozenset())
        prior = kernel.run(inactive)
        self.assertFalse(prior.supports["q"])
        active = kernel.revise(inactive, prior, program)
        self.assertTrue(active.state.supports["tail"])
        retired = replace(program, rules=tuple(rule for rule in program.rules if rule.conclusion != "q"))
        result = kernel.revise(program, active.state, retired)
        self.assertFalse(result.state.supports["tail"])
        self.assertEqual(result.state.supports, kernel.run(retired).supports)

    def test_bounds_keep_unexplored_frontier_and_expanded_profile_recomputes(self):
        program = self.fixture()
        small = TruthKernel(TruthProfile(max_supports_per_claim=1))
        prior = small.run(program)
        self.assertTrue({"q", "tail"} <= prior.frontier)
        self.assertTrue(prior.support_bits("q", "not-q")["frontier_unexplored"])
        bigger = TruthKernel().revise(program, prior, program).state
        self.assertFalse(bigger.frontier)
        self.assertEqual(len(bigger.supports["q"]), 2)
        cutoff = TruthKernel(TruthProfile(max_work=1)).run(program)
        self.assertEqual(cutoff.work, 1)
        self.assertEqual(cutoff.frontier, frozenset(program.claims))

    def test_malformed_or_unrooted_axioms_are_refused(self):
        program = self.fixture()
        invalid = [
            replace(program, claims=("a", "a")),
            replace(program, rules=(DerivationRule("axiom", (), "q"),)),
            replace(program, rules=(DerivationRule("outside", ("missing",), "q"),)),
            replace(program, nogoods=(frozenset(),)),
            replace(program, roots=(EvidenceRoot("root", "outside"),)),
        ]
        for value in invalid:
            with self.subTest(value=value), self.assertRaises(ValueError):
                TruthKernel().run(value)

    def test_1920_unseen_assumption_assignments_match_independent_membership_oracle(self):
        generator = random.Random(4129)
        claims, assumptions = tuple("abcdef"), tuple("wxyz")
        for example in range(120):
            roots = tuple(
                EvidenceRoot(
                    f"root-{i}",
                    generator.choice(claims),
                    frozenset(generator.sample(assumptions, generator.randrange(3))),
                    generator.choice((False, True)),
                )
                for i in range(5)
            )
            rules = tuple(
                DerivationRule(
                    f"rule-{i}",
                    tuple(generator.sample(claims, generator.randrange(1, 4))),
                    generator.choice(claims),
                    frozenset(generator.sample(assumptions, generator.randrange(2))),
                )
                for i in range(8)
            )
            nogoods = (frozenset(generator.sample(assumptions, 2)),) if example % 3 == 0 else ()
            program = TruthProgram(claims, roots, rules, assumptions, nogoods)
            kernel = TruthKernel()
            state = kernel.run(program)
            self.assertFalse(state.frontier)
            self.assertEqual({claim: set(state.environments(claim)) for claim in claims}, oracle(program))
            changed = replace(program, roots=roots[1:])
            self.assertEqual(
                kernel.revise(program, state, changed).state.supports, kernel.run(changed).supports
            )
            reordered = replace(program, roots=tuple(reversed(roots)), rules=tuple(reversed(rules)))
            self.assertEqual(state.supports, kernel.run(reordered).supports)

    def test_derived_seed_inherits_original_root_environment_and_retraction(self):
        program = TruthProgram(
            ("report", "derived", "other"),
            (
                EvidenceRoot("original", "report", {"A"}),
                EvidenceRoot("seed", "derived", {"B"}, provenance_roots={"original"}),
                EvidenceRoot("independent", "other"),
            ),
            (),
            {"A", "B"},
        )
        kernel = TruthKernel()
        initial = kernel.run(program)
        self.assertEqual(initial.environments("derived"), (frozenset({"A", "B"}),))
        withdrawn = replace(program, active_assumptions=frozenset({"B"}))
        revised = kernel.revise(program, initial, withdrawn)
        self.assertFalse(revised.state.supports["derived"])
        self.assertEqual(revised.state.supports, kernel.run(withdrawn).supports)
        self.assertIn("other", revised.retained_claims)
        incompatible = replace(program, nogoods=(frozenset({"A", "B"}),))
        self.assertFalse(kernel.run(incompatible).supports["derived"])

    def test_512_derived_environment_and_retraction_combinations_match_separate_oracle(self):
        kernel = TruthKernel()
        previous_program = previous_state = None
        for active_bits, root_bits, nogood_bits in itertools.product(range(16), range(4), range(8)):
            active = frozenset(name for bit, name in enumerate("ABCD") if active_bits & (1 << bit))
            possible_nogoods = (frozenset({"A"}), frozenset({"A", "B"}), frozenset({"B", "C"}))
            nogoods = tuple(value for bit, value in enumerate(possible_nogoods) if nogood_bits & (1 << bit))
            program = TruthProgram(
                ("a", "b", "q", "other"),
                (
                    EvidenceRoot("ra", "a", {"A"}, bool(root_bits & 1)),
                    EvidenceRoot("rb", "b", {"B"}, bool(root_bits & 2)),
                    EvidenceRoot("seed", "q", {"C"}, provenance_roots={"ra", "rb"}),
                    EvidenceRoot("other", "other", {"D"}),
                ),
                (),
                active,
                nogoods,
            )
            expected = set()
            for flags in itertools.product((False, True), repeat=4):
                assignment = frozenset(name for name, enabled in zip("ABCD", flags) if enabled)
                if not assignment <= active or any(value <= assignment for value in nogoods):
                    continue
                if root_bits == 3 and {"A", "B", "C"} <= assignment:
                    expected.add(assignment)
            state = kernel.run(program)
            self.assertEqual(set(state.environments("q")), minimal(expected))
            if previous_program is not None:
                revised = kernel.revise(previous_program, previous_state, program).state
                self.assertEqual(revised.supports, state.supports)
            previous_program, previous_state = program, state
