"""Shared M04/M13 computes passage matrices, never fixture-supplied fit labels."""

from copy import deepcopy
from dataclasses import replace
import json
import unittest

from hcl.kernel.types import HCLFailure, thaw
from hcl.runtime.answer import AnswerAssembler
from hcl.operators.abduction import program_hash
from tests import test_unified_s4_literature as literary_fixtures


class NarrativeHypothesisTests(unittest.TestCase):
    def setUp(self):
        self.f = literary_fixtures.LiteratureExecutionTests()
        self.f.setUp()
        self.f.budget = replace(
            self.f.budget,
            max_local_evaluations=200,
            max_output_bytes=1048576,
            max_visible_output_tokens=1048576,
            max_total_output_bytes=16777216,
        )

    def tearDown(self):
        self.f.tearDown()

    def task(self, chunk, expected=True):
        refs = [s.segment_id for s in chunk.segments]
        model = dict(
            id="reading-model",
            source_id="book",
            frame_kind="INTERPRETATION",
            assumptions=[],
            active_assumptions=[],
            unmodeled_segments=[],
            literals=[
                dict(
                    id=key, atom=atom, negative=negative, kind="CLAIM", segment_ids=refs
                )
                for key, atom, negative in [
                    ("testimony", "testimony", False),
                    ("positive", "claim", False),
                    ("negative", "claim", True),
                ]
            ],
            premises=[
                dict(
                    id=key,
                    literal=literal,
                    ordinary=ordinary,
                    assumptions=[],
                    segment_ids=refs,
                )
                for key, literal, ordinary in [
                    ("report", "testimony", False),
                    ("counter", "negative", True),
                ]
            ],
            rules=[
                dict(
                    id="interpret-report",
                    premises=["testimony"],
                    conclusion="positive",
                    strict=False,
                    assumptions=[],
                    segment_ids=refs,
                )
            ],
            priorities=[],
            queries=[
                dict(
                    id="q",
                    literal="positive",
                    preferred=False,
                    critical_candidates=[],
                    segment_ids=refs,
                )
            ],
        )
        context = dict(
            id="passage",
            adapter="argument-model-1",
            template=dict(schema="hcl-argument-candidates-1", models=[model]),
            features={},
            feature_segments={},
            segment_ids=refs,
        )
        return dict(
            schema="hcl-discovery-candidates-1",
            contexts=[context],
            observations=[
                dict(
                    id="reported-outcome",
                    context_id="passage",
                    query_id="reading",
                    values=[dict(positive=expected, opposed=False)],
                    factor_id="passage-" + str(chunk.ordinal),
                    provenance_group="original-" + str(chunk.ordinal),
                    derived_from=[],
                    segment_ids=refs,
                )
            ],
            probes=[],
            programs=[
                dict(
                    id="defeasible",
                    adapter="argument-model-1",
                    latent={"strict": False},
                    observe=[],
                    transition=[
                        dict(
                            target=dict(kind="strict", rule_id="interpret-report"),
                            value={"latent": "strict"},
                        )
                    ],
                    constraint=[],
                    predict=[
                        dict(id="reading", field="argument.acceptance", record_id="q")
                    ],
                )
            ],
            grammar=dict(
                observation_features=[],
                latent_domains={"strict": [False, True]},
                max_expression_size=32,
            ),
            search=dict(max_rounds=1, beam=12, new_per_round=4, max_candidates=64),
            unmodeled_segments=[],
        )

    def test_single_passage_actual_shared_search_generates_and_recomputes_rule_edit(
        self,
    ):
        f = self.f
        data = f.simple()
        data["comparisons"] = [
            dict(id="rhetorical-function", task=self.task(f.parts()[0]))
        ]
        result, port = f.run_candidate([data])
        self.assertEqual(result.status, "PARTIAL", result.diagnostics)
        record = f.values()["comparisons"][0]
        values = record["values"]
        self.assertEqual(port.attempts, 1)
        self.assertEqual(len(values["edit_history"]), 1)
        self.assertEqual(values["edit_history"][0]["operation"], "replace_latent")
        matrix = {
            values["programs"][key]["latent"]["strict"]: col
            for key, col in values["prediction_matrix"].items()
        }
        self.assertEqual(matrix[False]["cells"][0]["relation"], "CONTRADICTED")
        self.assertEqual(matrix[True]["cells"][0]["relation"], "EXPLAINED")
        self.assertTrue(
            matrix[True]["actual_results"][0]["values"]["models"][0]["iterations"]
        )
        self.assertIn("Actually recomputed mechanism edits", result.answer)
        self.assertNotIn(
            "THEME_MECHANISM_COMPARISON_UNCOMPUTED", result.unresolved_issues
        )
        self.assertGreater(result.usage["local_evaluations"], 4)

    def test_late_passage_counterevidence_changes_pareto_set_and_preserves_earlier_cells(
        self,
    ):
        f = self.f
        chunks, base = f.long_candidates()
        base[0]["comparisons"] = [
            dict(id="rhetorical-function", task=self.task(chunks[0], True))
        ]
        result, _ = f.run_candidate(base, replace(f.request(), request_id="early-only"))
        self.assertEqual(result.status, "PARTIAL", result.diagnostics)
        before = thaw(f.values()["comparisons"][0]["values"])
        self.assertEqual(len(before["pareto_programs"]), 1)
        revised = deepcopy(base)
        revised[-1]["comparisons"] = [
            dict(id="rhetorical-function", task=self.task(chunks[-1], False))
        ]
        result, port = f.run_candidate(
            revised, replace(f.request(), request_id="late-counterevidence")
        )
        self.assertEqual(result.status, "PARTIAL", result.diagnostics)
        after = f.values()["comparisons"][0]["values"]
        self.assertEqual(len(after["pareto_programs"]), 2)
        self.assertEqual(port.attempts, len(chunks))
        for key, column in after["prediction_matrix"].items():
            self.assertEqual(
                column["cells"][0]["prediction"]["values"],
                tuple(
                    before["prediction_matrix"][key]["cells"][0]["prediction"]["values"]
                ),
            )
            self.assertEqual(len(column["cells"]), 2)
        # Same local context label in different fragments did not overwrite rows.
        self.assertEqual(len(after["context_bindings"]), 2)
        self.assertTrue(
            all(
                len(c["actual_results"]) == 2
                for c in after["prediction_matrix"].values()
            )
        )

    def test_inner_cycles_and_budget_frontiers_stay_visible_in_outer_claim(self):
        f = self.f
        data = f.simple()
        task = self.task(f.parts()[0])
        model = task["contexts"][0]["template"]["models"][0]
        model["rules"].append(
            dict(
                id="circular",
                premises=["positive"],
                conclusion="testimony",
                strict=True,
                assumptions=[],
                segment_ids=model["rules"][0]["segment_ids"],
            )
        )
        data["comparisons"] = [dict(id="scope", task=task)]
        result, _ = f.run_candidate([data])
        self.assertEqual(result.status, "PARTIAL", result.diagnostics)
        self.assertIn("CYCLIC_PROOF_FRAGMENT_EXCLUDED", result.unresolved_issues)
        self.assertIn("CYCLIC_PROOF_FRAGMENT_EXCLUDED", result.answer)
        small = replace(
            f.request(),
            request_id="budget",
            budget=replace(f.budget, max_local_evaluations=4),
        )
        result, _ = f.run_candidate([data], small)
        self.assertEqual(result.status, "PARTIAL", result.diagnostics)
        self.assertEqual(result.usage["local_evaluations"], 4)
        self.assertIn("PREDICTION_BUDGET_FRONTIER", result.unresolved_issues)

    def test_tampered_nested_matrix_or_scope_cannot_be_consumed(self):
        f = self.f
        data = f.simple()
        data["comparisons"] = [dict(id="comparison", task=self.task(f.parts()[0]))]
        result, _ = f.run_candidate([data])
        self.assertEqual(result.status, "PARTIAL", result.diagnostics)
        original = next(
            row
            for row in f.store.inferences("s", f.owner)
            if row.result_id in result.execution_receipt["result_ids"]
        )
        for mode in (
            "matrix",
            "input",
            "conditions",
            "source-bool",
            "source-float",
            "nested-source",
            "binding-type",
            "result_id",
        ):
            values = thaw(original.values)
            record = values["comparisons"][0]
            if mode == "matrix":
                next(iter(record["values"]["prediction_matrix"].values()))["cells"][0][
                    "relation"
                ] = "MADE_UP"
            elif mode == "input":
                record["input_identity"] = "0" * 64
            elif mode in ("source-bool", "source-float"):
                record["source_versions"]["book"] = (
                    True if mode == "source-bool" else 1.0
                )
            elif mode == "nested-source":
                record["values"]["source_versions"]["book"] = True
            elif mode == "result_id":
                record["result_id"] = "OTHER-RESULT"
            elif mode == "binding-type":
                next(iter(record["values"]["source_bindings"].values()))[
                    "version"
                ] = True
            else:
                record["values"]["context_bindings"] = {}
            with self.subTest(mode=mode), self.assertRaises(HCLFailure):
                AnswerAssembler().compact_claim(replace(original, values=values))


if __name__ == "__main__":
    unittest.main()
