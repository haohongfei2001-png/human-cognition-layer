"""The narrative entry consumes actual M12 mappings and their counterexamples."""

from copy import deepcopy
from dataclasses import replace
import unittest

from hcl import ExecutionIssue
from hcl.kernel.types import Issue, HCLFailure, thaw
from hcl.runtime.answer import AnswerAssembler
from hcl.runtime.context import ContextCompiler
from hcl.models.gateway import OfflineModelPort
from tests import test_unified_s4_concepts as concept
from tests import test_unified_s4_literature as literature


class NarrativeAnalogyTests(unittest.TestCase):
    def fixture(self):
        f = concept.ConceptExecutionTests()
        f.setUp()
        self.addCleanup(f.tearDown)
        task = f.candidate()
        f.request = replace(
            f.request,
            issue=ExecutionIssue(
                "root", goals=(Issue("literary", "literature.analyze"),)
            ),
        )
        snapshot = f.store.snapshot("s", f.owner, f.handles)
        chunks = ContextCompiler().chunks(
            snapshot,
            f.request.question,
            "literature_compile",
            f.request.budget,
            OfflineModelPort().describe(),
        )
        self.assertEqual(len(chunks), 1)
        candidate = literature.LiteratureExecutionTests.candidate(chunks[0])
        candidate["analogies"] = [dict(id="conditional-reading", task=task)]
        candidate["unmodeled_segments"] = []
        return f, candidate

    def test_narrative_calls_mapping_and_delivers_scoped_counterevidence(self):
        for stream in (False, True):
            f, candidate = self.fixture()
            result, port = f.run_candidate(candidate, stream=stream)
            self.assertEqual(result.status, "PARTIAL", result.diagnostics)
            self.assertEqual(port.attempts, 1)
            self.assertIn("TARGET_REFUTED", result.answer)
            self.assertIn("semantic-compatibility", result.answer)
            self.assertNotIn("STRUCTURAL_MAPPING_UNCOMPUTED", result.unresolved_issues)
            self.assertIn(
                "STRUCTURAL_READINGS_REMAIN_CONDITIONAL", result.unresolved_issues
            )
            actual = f.result()
            nested = actual.values["analogies"][0]
            self.assertEqual(nested["kind"], "CONDITIONAL_STRUCTURAL_MAPPINGS")
            self.assertGreater(nested["resource_usage"]["local_evaluations"], 0)
            self.assertIn(
                "structural:comparison:target:not-xz",
                result.claim_records[0].counterevidence,
            )
            self.assertTrue(
                any(
                    field.field == "analogies" and getattr(field, "path", ())
                    for field in result.claim_records[0].used_result_fields
                )
            )
            self.assertEqual(
                actual.values["local_evaluations"],
                actual.values["batch_evaluations"]
                + nested["resource_usage"]["local_evaluations"],
            )

    def test_bound_source_predictions_change_without_becoming_originals(self):
        f, candidate = self.fixture()
        original = f.store.snapshot("s", f.owner, f.handles)
        first, _ = f.run_candidate(candidate)
        old = f.result()
        revised = deepcopy(candidate)
        revised["analogies"][0]["task"]["models"][0]["target"]["facts"][-1][
            "negated"
        ] = False
        second, _ = f.run_candidate(
            revised, request=replace(f.request, request_id="revised-reading")
        )
        self.assertIn("TARGET_SUPPORTED", second.answer)
        self.assertNotEqual(first.answer, second.answer)
        self.assertIn(old, f.store.inferences("s", f.owner))
        fresh = f.store.snapshot("s", f.owner, f.handles)
        self.assertEqual(dict(original.immutable_views), dict(fresh.immutable_views))

    def test_nested_conditions_scope_and_frontier_cannot_be_stripped(self):
        f, candidate = self.fixture()
        f.run_candidate(candidate)
        actual = f.result()
        for mode in (
            "conditions",
            "counterexample",
            "source",
            "source-bool",
            "source-float",
            "fragment-bool",
            "fragment",
            "local_id",
            "result_id",
            "omit",
        ):
            values = thaw(actual.values)
            nested = values["analogies"][0]
            if mode == "conditions":
                nested["assumption_environments"] = []
            elif mode == "counterexample":
                nested["counterevidence_ids"] = []
            elif mode == "source":
                nested["source_versions"]["target"] = 9
            elif mode in ("source-bool", "source-float"):
                nested["source_versions"]["target"] = (
                    True if mode == "source-bool" else 1.0
                )
            elif mode == "fragment-bool":
                nested["fragment"] = False
            elif mode in ("fragment", "local_id", "result_id"):
                nested[mode] = 999 if mode == "fragment" else "wrong-source-reading"
            else:
                values["analogies"] = []
            with self.assertRaises(HCLFailure):
                AnswerAssembler().compact_claim(replace(actual, values=values))
        result, _ = f.run_candidate(
            candidate,
            request=replace(
                f.request,
                request_id="small",
                budget=replace(f.request.budget, max_local_evaluations=3),
            ),
        )
        self.assertEqual(result.status, "PARTIAL", result.diagnostics)
        self.assertIn("FRONTIER", result.answer)
        self.assertLessEqual(result.usage["local_evaluations"], 3)


if __name__ == "__main__":
    unittest.main()
