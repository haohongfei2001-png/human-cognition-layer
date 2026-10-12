"""Independent finite invariants of the shared residual/matrix mechanism."""

from copy import deepcopy
from itertools import product
from unittest.mock import patch
import unittest

import hcl.operators.abduction as a


class AbductionContracts(unittest.TestCase):
    def test_relation_preserves_sets_types_unknown_and_correlated_factors(self):
        observation = dict(values=[True])
        for status, values, expected in [
            ("COMPUTED", [True], "EXPLAINED"),
            ("COMPUTED", [False], "CONTRADICTED"),
            ("COMPUTED", [False, True], "COMPATIBLE_UNDERSPECIFIED"),
            ("COMPUTED", [1], "CONTRADICTED"),
            ("UNCOMPUTED", [True], "UNCOMPUTED"),
            ("UNMODELED", [], "UNMODELED"),
            ("COMPUTED", [], "UNCOMPUTED"),
        ]:
            self.assertEqual(
                a.compare_prediction(dict(status=status, values=values), observation),
                expected,
            )
        rows = [dict(factor_id="first", relation="EXPLAINED")] * 20
        self.assertEqual(a.factor_profile(rows)["explained"], ("first",))
        rows.append(dict(factor_id="first", relation="CONTRADICTED"))
        profile = a.factor_profile(rows)
        self.assertEqual(profile["explained"], ())
        self.assertEqual(profile["contradicted"], ("first",))

    def test_pareto_does_not_erase_unique_uncommon_evidence_or_reward_unknown(self):
        def column(explained, contradicted, unknown=(), complexity=1):
            return dict(
                profile=dict(
                    explained=explained,
                    contradicted=contradicted,
                    unmodeled=unknown,
                    underspecified=(),
                ),
                complexity=complexity,
                work=1,
            )

        columns = dict(
            common=column(("c1", "c2"), ("rare",)),
            uncommon=column(("rare",), ("c1", "c2"), complexity=100),
            unknown=column((), (), ("c1", "c2", "rare"), 0),
        )
        self.assertEqual(set(a.pareto_frontier(columns)), set(columns))
        columns["renamed-common"] = deepcopy(columns["common"])
        self.assertEqual(set(a.pareto_frontier(columns)), set(columns))

    def test_bounded_boolean_edits_generalize_to_truth_tables_and_do_not_mutate(self):
        contexts = {
            str(i): dict(features=dict(zip(("received", "seen"), bits)))
            for i, bits in enumerate(product((False, True), repeat=2))
        }
        program = dict(
            id="p",
            adapter="mental-scene-1",
            latent={},
            observe=[
                dict(
                    event_id="e",
                    actor="a",
                    channel="seen_by",
                    when={"feature": "received"},
                )
            ],
            transition=[],
            constraint=[],
            predict=[],
        )
        grammar = dict(
            observation_features=["received", "seen"],
            latent_domains={},
            max_expression_size=40,
        )
        residuals = [dict(observation_id="o" + k, context_id=k) for k in contexts]
        original = deepcopy(program)
        programs = [
            p for p, _ in a.mechanism_edits(program, grammar, residuals, contexts)
        ]
        functions = {
            tuple(
                a.evaluate_expression(p["observe"][0]["when"], c["features"], {})
                for c in contexts.values()
            )
            for p in programs
        }
        self.assertIn((False, True, True, True), functions)  # OR, independent table
        self.assertIn((False, False, False, True), functions)  # AND
        self.assertIn((True, True, False, False), functions)  # NOT(received)
        self.assertEqual(program, original)
        self.assertEqual(list(a.mechanism_edits(program, grammar, [], contexts)), [])
        grammar["max_expression_size"] = 2
        self.assertTrue(
            all(
                a.expression_size(p["observe"][0]["when"]) <= 2
                for p, _ in a.mechanism_edits(program, grammar, residuals, contexts)
            )
        )

    def test_candidate_generation_streams_before_four_program_beam_limit(self):
        # This is a scheduler-cost oracle, not domain capability evidence.
        programs = [
            dict(
                id=f"p{i}",
                adapter="mental-scene-1",
                latent={"variant": i},
                observe=[
                    dict(
                        event_id=f"e{b}",
                        actor="a",
                        channel="seen_by",
                        when={"const": False},
                    )
                    for b in range(16)
                ],
                transition=[],
                constraint=[],
                predict=[],
            )
            for i in range(8)
        ]
        contexts = [
            dict(id="c", features={f"feature{n}": bool(n % 2) for n in range(32)})
        ]
        observations = [
            dict(
                id="o",
                context_id="c",
                query_id="q",
                values=[True],
                factor_id="f",
                provenance_group="f",
            )
        ]
        grammar = dict(
            observation_features=list(contexts[0]["features"]),
            latent_domains={},
            max_expression_size=128,
        )

        def evaluate(program, context, remaining):
            return dict(
                status="COMPUTED",
                work=1,
                actual_results=[],
                predictions={
                    "q": dict(status="COMPUTED", values=[False], result_refs=[])
                },
            )

        with patch.object(a, "program_hash", wraps=a.program_hash) as hashing:
            result = a.discover(
                programs,
                observations,
                contexts,
                [],
                grammar,
                evaluate,
                max_evaluations=100,
                max_rounds=1,
                new_per_round=4,
            )
        self.assertEqual(len(result["programs"]), 12)
        self.assertLess(hashing.call_count, 30)
        self.assertIn("NEW_PROGRAM_BEAM_BOUND", result["frontier"])
