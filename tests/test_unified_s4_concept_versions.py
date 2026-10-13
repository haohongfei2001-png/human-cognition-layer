"""Source-qualified generalization versions through the actual execution graph."""

from copy import deepcopy
from dataclasses import replace
import unittest
from hcl.kernel.types import HCLFailure, thaw
from hcl.runtime.answer import AnswerAssembler
from tests import test_unified_s4_concepts as runtime
from tests import test_unified_s4_concept_induction as pure
from tests import test_unified_s4_narrative_analogies as narrative


class ConceptVersionTests(unittest.TestCase):
    def fixture(self):
        f = runtime.ConceptExecutionTests()
        f.setUp()
        self.addCleanup(f.tearDown)
        original = f.candidate()["models"][0]
        base = original["base"]["facts"][0]["segment_ids"]
        target = original["target"]["facts"][0]["segment_ids"]

        def case(name, a, b, spans):
            return dict(
                id=name,
                term=pure.term("pair", pure.term(a), pure.term(b)),
                assumptions=["reading"],
                segment_ids=spans,
            )

        proposal = dict(
            id="sameness",
            concept_key="same-role",
            purpose="Distinguish relational repetition from mixed pairs.",
            assumptions=["reading"],
            active_assumptions=["reading"],
            positive=[case("aa", "a", "a", base), case("bb", "b", "b", base)],
            negative=[case("ab", "a", "b", target)],
            unmodeled_segments=[],
        )
        return f, dict(
            schema="hcl-structural-candidates-1", models=[], inductions=[proposal]
        )

    def test_actual_generalization_boundary_and_immutable_versions(self):
        f, candidate = self.fixture()
        first, _ = f.run_candidate(candidate)
        self.assertEqual(first.status, "COMPLETED", first.diagnostics)
        original = f.result()
        old = original.values["inductions"][0]
        self.assertEqual(old["actual"]["status"], "CONSISTENT_WITH_DECLARED_EXAMPLES")
        self.assertIn("reading", first.answer)
        proposal = candidate["inductions"][0]
        extra = deepcopy(proposal["negative"][0])
        extra.update(id="cc", term=pure.term("pair", pure.term("c"), pure.term("c")))
        proposal["negative"].append(extra)
        revised, _ = f.run_candidate(
            candidate, request=replace(f.request, request_id="counterexample")
        )
        self.assertEqual(revised.status, "PARTIAL", revised.diagnostics)
        new = f.result().values["inductions"][0]
        self.assertEqual(old["concept_id"], new["concept_id"])
        self.assertNotEqual(old["version_id"], new["version_id"])
        self.assertEqual(new["actual"]["counterexample_ids"], ("cc",))
        self.assertIn(
            "CONCEPT_GENERALIZATION_HAS_COUNTEREXAMPLES", revised.unresolved_issues
        )
        self.assertIn(original, f.store.inferences("s", f.owner))
        replay, port = f.run_candidate(candidate)
        self.assertEqual(replay.answer, first.answer)
        self.assertEqual(port.attempts, 0)

    def test_withdrawal_and_tiny_budgets_keep_pattern_and_coverage_unresolved(self):
        f, candidate = self.fixture()
        candidate["inductions"][0]["active_assumptions"] = []
        result, _ = f.run_candidate(candidate)
        self.assertEqual(result.status, "PARTIAL", result.diagnostics)
        self.assertIsNone(f.result().values["inductions"][0]["actual"])
        self.assertIn("INDUCTION_NO_ACTIVE_POSITIVES", result.unresolved_issues)
        candidate["inductions"][0]["active_assumptions"] = ["reading"]
        for budget in (1, 2, 4, 8, 16):
            result, _ = f.run_candidate(
                candidate,
                request=replace(
                    f.request,
                    request_id=str(budget),
                    budget=replace(f.request.budget, max_local_evaluations=budget),
                ),
            )
            self.assertIn(result.status, ("PARTIAL", "COMPLETED"), result.diagnostics)
            self.assertLessEqual(result.usage["local_evaluations"], budget)
            self.assertIn(
                "concept:sameness:assumption:reading",
                result.claim_records[0].support_envs,
            )

    def test_version_or_example_condition_tamper_fails_delivery(self):
        f, candidate = self.fixture()
        f.run_candidate(candidate)
        result = f.result()
        for field in ("version", "conditions", "pattern"):
            values = thaw(result.values)
            concept = values["inductions"][0]
            if field == "version":
                concept["version_id"] = "old-version"
            elif field == "conditions":
                concept["actual"]["examples"][0]["assumption_environments"] = []
            else:
                concept["actual"]["pattern"]["arguments"][1][
                    "id"
                ] = "independent-variable"
            with self.assertRaises(HCLFailure):
                AnswerAssembler().compact_claim(replace(result, values=values))

    def test_narrative_consumes_actual_induced_version_and_source_counterexample(self):
        n = narrative.NarrativeAnalogyTests()
        f, candidate = n.fixture()
        self.addCleanup(n.doCleanups)
        induction_fixture, task = self.fixture()
        # Source text, ids, versions, and query are the same synthetic originals;
        # each compiler still performs its own actual snapshot anchor validation.
        task["inductions"][0]["negative"][0]["term"] = pure.term(
            "pair", pure.term("c"), pure.term("c")
        )
        candidate["analogies"][0]["task"] = task
        result, _ = f.run_candidate(candidate, stream=True)
        self.assertEqual(result.status, "PARTIAL", result.diagnostics)
        self.assertIn("REFUTED_BY_DECLARED_COUNTEREXAMPLE", result.answer)
        self.assertIn(
            "CONCEPT_GENERALIZATION_HAS_COUNTEREXAMPLES", result.unresolved_issues
        )
        self.assertIn(
            "concept:sameness:example:ab", result.claim_records[0].counterevidence
        )
        self.assertTrue(
            f.result().values["analogies"][0]["values"]["inductions"][0]["actual"][
                "pattern"
            ]
        )


if __name__ == "__main__":
    unittest.main()
