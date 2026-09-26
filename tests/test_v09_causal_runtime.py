import unittest
from dataclasses import replace
from hcl.v04.model import EventRecord
from hcl.v06 import SYSTEM_VIEWER
from hcl.v09 import CausalModel, StructuralRule, HCLV09Runtime, SCOPE


def model(rules=None):
    return CausalModel(
        "m",
        "s",
        ("U", "X", "Y"),
        ("U",),
        tuple(
            rules
            or (
                StructuralRule("X", "U", "X = U"),
                StructuralRule("Y", "X ^ U", "Y = X ^ U"),
            )
        ),
    )


def source(**kwargs):
    return EventRecord(
        event_id="s",
        source_id="public-formal-fixture",
        raw_text="Declared model: X = U; Y = X ^ U",
        valid_time="2026-01-02T00:00:00+00:00",
        recorded_at="2026-01-03T00:00:00+00:00",
        actor_id="author",
        metadata={"causal_model_scope": SCOPE, "reader_only": True},
        **kwargs
    )


class CausalRuntimeTests(unittest.TestCase):
    def test_factual_abduction_shared_context_after_intervention(self):
        # Observing X=1 identifies U=1. Replacing X must not erase that fact.
        result = model().counterfactual(
            "Y", observations={"X": 1}, interventions={"X": 0}
        )
        self.assertEqual(result["value"], 1)
        self.assertEqual(result["traces"][0]["factual"]["Y"], 0)
        self.assertEqual(result["traces"][0]["exogenous"], {"U": 1})
        self.assertEqual(result["scope"], "CONDITIONAL_ON_DECLARED_MODEL")

    def test_intervention_is_not_observation(self):
        observed = model().counterfactual("Y", observations={"X": 0})
        intervened = model().counterfactual("Y", interventions={"X": 0})
        self.assertEqual(observed["possible_values"], [0])
        self.assertEqual(intervened["possible_values"], [0, 1])
        self.assertEqual(intervened["status"], "SYSTEM_INSUFFICIENT")
        self.assertIsNone(intervened["value"])

    def test_inconsistent_facts_not_arbitrary_answer(self):
        r = model().counterfactual(
            "Y", observations={"X": 1, "Y": 1}, interventions={"X": 0}
        )
        self.assertEqual(r["status"], "INCONSISTENT_OBSERVATIONS")
        self.assertEqual(r["traces"], [])

    def test_joint_intervention_cuts_both_incoming_equations(self):
        r = model().counterfactual(
            "Y", observations={"X": 1}, interventions={"X": 0, "Y": 0}
        )
        self.assertEqual(r["value"], 0)

    def test_no_probability_assigned_to_possible_world_counts(self):
        m = CausalModel(
            "logic",
            "s",
            ("A", "B", "C"),
            ("A", "B"),
            (StructuralRule("C", "A or B", "A or B"),),
        )
        r = m.counterfactual("C")
        self.assertEqual(r["possible_values"], [0, 1])
        self.assertNotIn("probability", r)
        self.assertEqual(r["world_count"], 4)

    def test_all_supported_operations_against_independent_truth_table(self):
        m = CausalModel(
            "logic",
            "s",
            ("A", "B", "C"),
            ("A", "B"),
            (StructuralRule("C", "(A and not B) or (B ^ A)", "logic"),),
        )
        expected = {(0, 0): 0, (0, 1): 1, (1, 0): 1, (1, 1): 0}
        for (a, b), answer in expected.items():
            self.assertEqual(m.world({"A": a, "B": b})["C"], answer)

    def test_cyclic_incomplete_duplicate_and_undeclared_models_rejected(self):
        for rules in [
            (StructuralRule("X", "Y", "x"), StructuralRule("Y", "X", "y")),
            (StructuralRule("X", "U", "x"),),
            (StructuralRule("X", "Z", "x"), StructuralRule("Y", "X", "y")),
            (StructuralRule("X", "U", "x"), StructuralRule("X", "U", "x")),
        ]:
            with self.assertRaises(ValueError):
                model(rules)

    def test_expression_never_executes_programs_or_accepts_numeric_truthiness(self):
        for text in [
            '__import__("os")',
            "A.attr",
            "A[0]",
            "A+1",
            "A == 1",
            "True",
            "2",
            "lambda: 0",
            "[A for A in B]",
        ]:
            with self.assertRaises(ValueError):
                StructuralRule("Y", text, "quote")

    def test_caps_bool_assignment_and_missing_roots_fail_closed(self):
        for kwargs in [
            {"observations": {"U": True}},
            {"interventions": {"Z": 0}},
            {"observations": {"U": 2}},
        ]:
            with self.assertRaises(ValueError):
                model().counterfactual("Y", **kwargs)
        with self.assertRaises(ValueError):
            model().world({})
        roots = tuple("U" + str(i) for i in range(9))
        with self.assertRaises(ValueError):
            CausalModel("large", "s", roots, roots, ())

    def test_source_quote_scope_and_atomic_registration(self):
        rt = HCLV09Runtime()
        rt.ingest_event(source())
        bad = model(
            (
                StructuralRule("X", "U", "absent quote"),
                StructuralRule("Y", "X ^ U", "Y = X ^ U"),
            )
        )
        with self.assertRaises(ValueError):
            rt.ingest_model(bad)
        self.assertEqual(rt.answer_context("m")["models"], [])
        self.assertTrue(rt.ingest_model(model()))
        self.assertFalse(rt.ingest_model(model()))
        with self.assertRaises(ValueError):
            rt.ingest_model(
                replace(
                    model(),
                    rules=(
                        StructuralRule("X", "not U", "X = U"),
                        StructuralRule("Y", "X ^ U", "Y = X ^ U"),
                    ),
                )
            )
        rt2 = HCLV09Runtime()
        rt2.ingest_event(replace(source(), metadata={}))
        with self.assertRaises(ValueError):
            rt2.ingest_model(model())

    def test_private_model_and_bitemporal_cutoffs_do_not_leak(self):
        rt = HCLV09Runtime()
        rt.ingest_event(source())
        rt.ingest_model(model())
        for kwargs in [
            {"viewer_agent_id": "character"},
            {"event_time": "2026-01-01T00:00:00+00:00"},
            {"knowledge_cutoff": "2026-01-02T00:00:00+00:00"},
        ]:
            r = rt.counterfactual(
                "m", "Y", observations={"X": 1}, interventions={"X": 0}, **kwargs
            )
            self.assertEqual(r["status"], "SYSTEM_INSUFFICIENT")
            self.assertEqual(r["traces"], [])
        self.assertEqual(
            rt.counterfactual(
                "m",
                "Y",
                observations={"X": 1},
                interventions={"X": 0},
                viewer_agent_id=SYSTEM_VIEWER,
            )["value"],
            1,
        )

    def test_queries_never_mutate_model_or_source_history(self):
        rt = HCLV09Runtime()
        rt.ingest_event(source())
        rt.ingest_model(model())
        before = rt.answer_context("m")
        rt.counterfactual("m", "Y", interventions={"U": 1, "X": 0})
        self.assertEqual(rt.answer_context("m"), before)
        self.assertEqual(len(rt.perspectives.events), 1)


if __name__ == "__main__":
    unittest.main()
