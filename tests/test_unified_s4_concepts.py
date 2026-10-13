"""Actual HCL structural execution from source-bound synthetic proposals."""

import asyncio
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from hcl import HCL, ExecutionIssue, ExecutionBudget
from hcl.kernel.types import Issue, Principal, TaskRequest, HCLFailure, thaw
from hcl.memory.store import StateStore
from hcl.models.gateway import ModelGateway, OfflineModelPort
from hcl.runtime.answer import AnswerAssembler
from hcl.runtime.recovery import RecoveryManager
from hcl.semantics.segments import segment_snapshot
from tests import test_unified_s4_structure_mapping as pure


class Crash(BaseException):
    pass


class ConceptExecutionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "state.sqlite"
        self.owner = Principal("tenant", "alice")
        self.store = StateStore.sqlite(self.path, revision=True)
        self.store.create_session("s", self.owner, {"bob"})
        self.handles = (
            self.store.put_source(
                "s", self.owner, "base", "A helps B. B helps C. A helps C."
            ),
            self.store.put_source(
                "s", self.owner, "target", "X helps Y. Y helps Z. X does not help Z."
            ),
        )
        self.request = TaskRequest(
            "analogy",
            "Compare the explicitly proposed structures.",
            self.handles,
            "s",
            self.owner,
            budget=ExecutionBudget(
                max_mock_calls=1,
                max_feedback=0,
                max_local_evaluations=100000,
                max_request_bytes=1048576,
                max_context_tokens=1048576,
                max_output_bytes=1048576,
                max_total_output_bytes=8000000,
                max_visible_output_tokens=1048576,
            ),
            issue=ExecutionIssue("root", goals=(Issue("compare", "analogy.compare"),)),
        )
        self.n = 0

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def candidate(self):
        snap = self.store.snapshot("s", self.owner, self.handles)
        segments = segment_snapshot(snap, self.request.question)
        anchors = {
            side: [
                s.segment_id
                for s in segments
                if s.kind == "SOURCE" and s.source_id == side
            ]
            for side in ("base", "target")
        }
        base = pure.domain(
            "abc",
            [
                pure.fact("ab", "R", pure.e("a"), pure.e("b")),
                pure.fact("bc", "R", pure.e("b"), pure.e("c")),
                pure.fact("ac", "R", pure.e("a"), pure.e("c")),
            ],
        )
        target = pure.domain(
            "xyz",
            [
                pure.fact("xy", "R", pure.e("x"), pure.e("y")),
                pure.fact("yz", "R", pure.e("y"), pure.e("z")),
                pure.fact("not-xz", "R", pure.e("x"), pure.e("z"), negated=True),
            ],
        )
        for side, domain in (("base", base), ("target", target)):
            for name, rows in domain.items():
                for row in rows:
                    row["segment_ids"] = anchors[side]
                    if name == "facts":
                        row["assumptions"] = []
        model = dict(
            id="comparison",
            assumptions=["semantic-compatibility"],
            active_assumptions=["semantic-compatibility"],
            base=base,
            target=target,
            compatibilities=[
                dict(
                    base="R",
                    target="R",
                    assumptions=["semantic-compatibility"],
                    segment_ids=anchors["base"] + anchors["target"],
                )
            ],
            max_mappings=16,
            unmodeled_segments=[],
        )
        return dict(schema="hcl-structural-candidates-1", models=[model], inductions=[])

    def run_candidate(self, candidate=None, *, request=None, stream=False):
        port = OfflineModelPort(json.dumps(candidate or self.candidate()))
        client = HCL(
            self.store, principal=self.owner, gateway=ModelGateway(self.store, port)
        )
        request = request or self.request
        if stream:

            async def run():
                return [event async for event in client.stream(request)]

            result = asyncio.run(run())[-1].result
        else:
            result = client.run_sync(request)
        self.last = result
        return result, port

    def result(self):
        ids = self.last.execution_receipt["result_ids"]
        return next(
            r for r in self.store.inferences("s", self.owner) if r.result_id in ids
        )

    def full_mapping(self):
        return next(
            r
            for r in self.result().values["models"][0]["actual"]["mappings"]
            if dict(r["entities"]) == dict(a="x", b="y", c="z")
        )

    @staticmethod
    def replace_domain(model, side, domain):
        anchors = model[side]["facts"][0]["segment_ids"]
        for group, rows in domain.items():
            for row in rows:
                row["segment_ids"] = anchors
                if group == "facts":
                    row["assumptions"] = []
        model[side] = domain

    def test_shared_dag_delivery_codec_and_restart_do_not_expand_exponentially(self):
        from hcl.memory import codec

        data = self.candidate()
        model = data["models"][0]
        for side, name in (("base", "a"), ("target", "x")):
            self.replace_domain(model, side, pure.fact_chain(16, 4, name))
        model["compatibilities"].append(
            dict(model["compatibilities"][0], base="H", target="H")
        )
        for stream in (False, True):
            request = replace(self.request, request_id="dag" + str(stream))
            result, port = self.run_candidate(data, request=request, stream=stream)
            self.assertEqual(result.status, "COMPLETED", result.diagnostics)
            self.assertEqual(port.attempts, 1)
            actual = self.result()
            self.assertLess(len(codec.dumps(actual)), 120000)
            self.assertLess(len(codec.dumps(result)), 150000)
            mapping = actual.values["models"][0]["actual"]["mappings"][0]
            self.assertEqual(len(mapping["projected_expression_nodes"]), 16)
            tampered = thaw(actual.values)
            tampered["models"][0]["actual"]["mappings"][0][
                "projected_expression_nodes"
            ].clear()
            with self.assertRaises(HCLFailure):
                AnswerAssembler().compact_claim(replace(actual, values=tampered))
            self.store.close()
            self.store = StateStore.sqlite(self.path)
            replay, port = self.run_candidate(data, request=request, stream=stream)
            self.assertEqual(replay.answer, result.answer)
            self.assertEqual(port.attempts, 0)

    def test_prefix_ordering_consumes_projected_support_not_only_matched_facts(self):
        from hcl.operators.concepts import compute_concepts

        data = self.candidate()
        model = data["models"][0]
        for side, names in (("base", "ab"), ("target", "xy")):
            a, b = names
            self.replace_domain(
                model,
                side,
                pure.domain(
                    names,
                    [
                        pure.fact(a + b, "R", pure.e(a), pure.e(b)),
                        pure.fact(b + a, "R", pure.e(b), pure.e(a)),
                    ],
                ),
            )
            assumption = "extra-" + side
            model["assumptions"].append(assumption)
            model["active_assumptions"].append(assumption)
            model[side]["facts"][1]["assumptions"] = [assumption]
        required = {
            "structural:comparison:assumption:extra-" + side
            for side in ("base", "target")
        }
        for stream in (False, True):
            result, _ = self.run_candidate(
                data,
                request=replace(
                    self.request,
                    request_id="prefix" + str(stream),
                    budget=replace(self.request.budget, max_local_evaluations=28),
                ),
                stream=stream,
            )
            self.assertEqual(result.status, "PARTIAL", result.diagnostics)
            rows = self.result().values["models"][0]["actual"]["mappings"]
            row = next(r for r in rows if r["supported_relations"] > len(r["facts"]))
            self.assertLessEqual(
                required, set(row["metric_conditions"]["supported_relations"])
            )
            self.assertLessEqual(required, set(row["ordering_assumption_environments"]))
            for a in required:
                self.assertIn(a, result.answer)
            actual = self.result()
            changed = thaw(actual.values)
            for r in changed["models"][0]["actual"]["mappings"]:
                r["metric_conditions"]["supported_relations"] = []
            with self.assertRaises(HCLFailure):
                AnswerAssembler().compact_claim(replace(actual, values=changed))
        # Higher-order projected support must obey the same rule on every
        # bounded search prefix, not just the fully closed maximal mapping.
        for side in ("base", "target"):
            domain = model[side]
            anchor = domain["facts"][0]["segment_ids"]
            domain["predicates"].append(
                dict(pure.predicate("H", "FACT"), segment_ids=anchor)
            )
            domain["facts"] += [
                dict(
                    pure.fact("h" + str(i), "H", pure.f(row["id"])),
                    segment_ids=anchor,
                    assumptions=row["assumptions"],
                )
                for i, row in enumerate(domain["facts"][:])
            ]
        model["compatibilities"].append(
            dict(model["compatibilities"][0], base="H", target="H")
        )
        result, _ = self.run_candidate(
            data, request=replace(self.request, request_id="higher")
        )
        program = self.result().values["inputs"]["program"]
        checked_prefix = False
        for budget in range(15, 180):
            value = compute_concepts(program, budget)
            for row in value["models"][0]["actual"]["mappings"]:
                for metric in (
                    "supported_relations",
                    "higher_order_links",
                    "explicit_counterexamples",
                ):
                    contributing = [
                        p
                        for p in row["predictions"]
                        if p["metric_contributions"][metric]
                    ]
                    self.assertEqual(
                        row[metric],
                        sum(p["metric_contributions"][metric] for p in contributing),
                    )
                    # This fixture has no negative target, so each prediction's
                    # qualified support is exactly the metric contributor.
                    expected = {
                        a for p in contributing for a in p["assumption_environments"]
                    }
                    self.assertEqual(set(row["metric_conditions"][metric]), expected)
                checked_prefix |= row["higher_order_links"] > 0 and row[
                    "supported_relations"
                ] > len(row["facts"])
        self.assertTrue(checked_prefix)

    def test_attribute_secondary_metric_uses_only_selected_compatibility(self):
        data = self.candidate()
        model = data["models"][0]
        ps = [
            pure.predicate("R", "ENTITY:thing", "ENTITY:thing"),
            pure.predicate("A", "ENTITY:thing", kind="ATTRIBUTE"),
            pure.predicate("B", "ENTITY:thing", kind="ATTRIBUTE"),
            pure.predicate("H", "FACT"),
        ]
        for side, names, symbol in (("base", "ab", "A"), ("target", "xy", "B")):
            a, b = names
            self.replace_domain(
                model,
                side,
                pure.domain(
                    names,
                    [
                        pure.fact("r", "R", pure.e(a), pure.e(b)),
                        pure.fact("first", symbol, pure.e(a)),
                        pure.fact(
                            "second", symbol, pure.e(b), negated=side == "target"
                        ),
                        pure.fact("higher", "H", pure.f("first")),
                    ],
                    deepcopy(ps),
                ),
            )
        model["assumptions"] += ["selected", "unused", "negative"]
        model["active_assumptions"] = model["assumptions"][:]
        model["target"]["facts"][2]["assumptions"] = ["negative"]
        template = model["compatibilities"][0]
        model["compatibilities"] += [
            dict(template, base="H", target="H"),
            dict(template, base="A", target="A", assumptions=["unused"]),
            dict(template, base="A", target="B", assumptions=["selected"]),
        ]
        result, _ = self.run_candidate(data)
        self.assertEqual(result.status, "COMPLETED", result.diagnostics)
        row = next(
            r
            for r in self.result().values["models"][0]["actual"]["mappings"]
            if dict(r["entities"]) == dict(a="x", b="y") and "H" in r["predicates"]
        )
        self.assertEqual(row["explicit_counterexamples"], 0)
        self.assertEqual(row["metric_conditions"]["explicit_counterexamples"], ())
        self.assertEqual(row["attribute_mismatches"], 1)
        conditions = row["metric_conditions"]["attribute_mismatches"]
        for name in ("selected", "negative"):
            self.assertIn("structural:comparison:assumption:" + name, conditions)
        self.assertNotIn("structural:comparison:assumption:unused", conditions)
        self.assertIn(
            "structural:comparison:target:second",
            result.claim_records[0].counterevidence,
        )

    def test_source_certificate_types_and_premise_keys_cannot_change(self):
        self.run_candidate()
        actual = self.result()
        for source_versions in (
            {"foreign": 1},
            {"base": True, "target": 1},
            {"base": 2, "target": 1},
            {},
            [["base", 1], ["target", 1]],
        ):
            values = thaw(actual.values)
            values["source_versions"] = source_versions
            with self.subTest(versions=source_versions), self.assertRaises(HCLFailure):
                AnswerAssembler().compact_claim(replace(actual, values=values))
        for keys in (
            ("foreign",),
            (),
            ("base", "target", "target"),
            ["base", "target"],
        ):
            with self.subTest(keys=keys), self.assertRaises(HCLFailure):
                AnswerAssembler().compact_claim(replace(actual, premise_ids=keys))
        values = thaw(actual.values)
        values["inputs"]["program"]["source_versions"]["base"] = True
        values["source_versions"]["base"] = True
        with self.assertRaises(HCLFailure):
            AnswerAssembler().compact_claim(replace(actual, values=values))

    def test_actual_role_mapping_and_counterexample_consumed_run_stream(self):
        for stream in (False, True):
            result, port = self.run_candidate(
                request=replace(self.request, request_id=str(stream)), stream=stream
            )
            self.assertEqual(result.status, "COMPLETED", result.diagnostics)
            self.assertEqual(port.attempts, 1)
            self.assertIn("TARGET_REFUTED", result.answer)
            self.assertIn("not-xz", result.answer)
            prediction = next(
                p for p in self.full_mapping()["predictions"] if p["base_fact"] == "ac"
            )
            self.assertEqual(prediction["status"], "TARGET_REFUTED")
            self.assertIn(
                "structural:comparison:assumption:semantic-compatibility",
                prediction["assumption_environments"],
            )
            self.assertTrue(prediction["evidence_segment_ids"])
            self.assertEqual(
                result.claim_records[0].epistemic_status,
                "CONDITIONAL_STRUCTURE_NOT_TARGET_TRUTH",
            )
            self.assertIn(
                "structural:comparison:target:not-xz",
                result.claim_records[0].counterevidence,
            )

    def test_target_counterevidence_change_changes_actual_prediction_not_old_result(
        self,
    ):
        first, _ = self.run_candidate()
        old = self.result()
        data = self.candidate()
        data["models"][0]["target"]["facts"][-1]["negated"] = False
        second, _ = self.run_candidate(
            data, request=replace(self.request, request_id="positive")
        )
        self.assertEqual(second.status, "COMPLETED", second.diagnostics)
        prediction = next(
            p for p in self.full_mapping()["predictions"] if p["base_fact"] == "ac"
        )
        self.assertEqual(prediction["status"], "TARGET_SUPPORTED")
        self.assertIn(old, self.store.inferences("s", self.owner))
        self.assertNotEqual(first.answer, second.answer)

    def test_withdrawn_target_evidence_is_unresolved_not_refuted(self):
        data = self.candidate()
        model = data["models"][0]
        model["assumptions"].append("target-report")
        model["target"]["facts"][-1]["assumptions"] = ["target-report"]
        result, _ = self.run_candidate(data)
        self.assertEqual(result.status, "PARTIAL", result.diagnostics)
        prediction = next(
            p for p in self.full_mapping()["predictions"] if p["base_fact"] == "ac"
        )
        self.assertEqual(prediction["status"], "TARGET_UNDETERMINED")
        self.assertIn(
            "STRUCTURAL_ASSUMPTION_OR_DEPENDENCY_WITHDRAWN", result.unresolved_issues
        )
        self.assertNotIn(
            "structural:comparison:target:not-xz",
            result.claim_records[0].counterevidence,
        )

    def test_anchor_or_computed_answer_injection_rejected(self):
        for mutation in ("question", "answer", "duplicate", "compatibility"):
            data = self.candidate()
            model = data["models"][0]
            if mutation == "question":
                from hcl.semantics.segments import question_segments

                model["base"]["facts"][0]["segment_ids"] = [
                    question_segments(self.request.question)[0].segment_id
                ]
            elif mutation == "answer":
                model["mappings"] = [dict(a="x")]
            elif mutation == "duplicate":
                model["base"]["facts"].append(
                    dict(model["base"]["facts"][0], id="other")
                )
            else:
                model["compatibilities"][0]["target"] = "unknown"
            result, _ = self.run_candidate(
                data, request=replace(self.request, request_id=mutation)
            )
            self.assertEqual(result.status, "INVALID_REQUEST", result.diagnostics)
            self.assertFalse(result.claim_records)

    def test_partial_budget_keeps_known_work_and_never_claims_maximality(self):
        for budget in (1, 10, 30, 60):
            result, _ = self.run_candidate(
                request=replace(
                    self.request,
                    request_id=str(budget),
                    budget=replace(self.request.budget, max_local_evaluations=budget),
                )
            )
            self.assertIn(result.status, ("PARTIAL", "COMPLETED"), result.diagnostics)
            self.assertLessEqual(result.usage["local_evaluations"], budget)
            if result.status == "PARTIAL":
                self.assertIn("FRONTIER", result.answer)

    def test_tampered_mapping_conditions_or_counterexample_cannot_be_consumed(self):
        result, _ = self.run_candidate()
        actual = self.result()
        for field in ("status", "conditions", "evidence", "work"):
            values = thaw(actual.values)
            mapping = next(
                r
                for r in values["models"][0]["actual"]["mappings"]
                if r["entities"] == dict(a="x", b="y", c="z")
            )
            prediction = next(
                p for p in mapping["predictions"] if p["base_fact"] == "ac"
            )
            if field == "status":
                prediction["status"] = "TARGET_SUPPORTED"
            elif field == "conditions":
                prediction["assumption_environments"] = []
            elif field == "evidence":
                prediction["evidence_segment_ids"] = []
            else:
                values["local_evaluations"] += 1
            with self.assertRaises(HCLFailure):
                AnswerAssembler().compact_claim(replace(actual, values=values))

    def test_checkpoint_resume_never_resends_return_or_recomputes_accepted_effect(self):
        for seam in (
            "return_persisted",
            "execution_computed",
            "execution_effects_committed",
        ):
            data = self.candidate()
            request = replace(
                self.request,
                request_id=seam,
                issue=ExecutionIssue("root", goals=(Issue(seam, "analogy.compare"),)),
            )
            owner = self.store.owner_id
            fired = False

            def stop(stage):
                nonlocal fired
                if stage == seam and not fired:
                    fired = True
                    raise Crash()

            with patch.object(
                self.store, "_checkpoint", side_effect=stop
            ), self.assertRaises(Crash):
                self.run_candidate(data, request=request)
            self.assertTrue(fired)
            self.store.close()
            self.store = StateStore.sqlite(self.path)
            RecoveryManager(self.store).resume_execution(
                request, expected_owner_id=owner
            )
            from hcl.operators.local_model import LocalModelOperator

            if seam == "return_persisted":
                result, port = self.run_candidate(data, request=request)
            else:
                with patch.object(
                    LocalModelOperator,
                    "run",
                    side_effect=AssertionError("accepted operation cannot recompute"),
                ):
                    result, port = self.run_candidate(data, request=request)
            self.assertEqual(result.status, "COMPLETED", result.diagnostics)
            self.assertEqual(port.attempts, 0)

    def test_unknown_send_and_cached_acl_never_deliver(self):
        candidate = self.candidate()
        result, _ = self.run_candidate(candidate)
        self.store.set_readers("s", self.owner, "target", {"bob"})
        replay, port = self.run_candidate(candidate)
        self.assertEqual(replay.status, "DENIED")
        self.assertFalse(replay.answer or replay.claim_records)
        self.assertEqual(port.attempts, 0)
        self.store.set_readers("s", self.owner, "target", {"alice"})
        request = replace(self.request, request_id="unknown")

        def stop(stage):
            if stage == "send_started":
                raise Crash()

        with patch.object(
            self.store, "_checkpoint", side_effect=stop
        ), self.assertRaises(Crash):
            self.run_candidate(request=request)
        owner = self.store.owner_id
        self.store.close()
        self.store = StateStore.sqlite(self.path)
        with self.assertRaises(HCLFailure):
            RecoveryManager(self.store).resume_execution(
                request, expected_owner_id=owner
            )
        replay, port = self.run_candidate(request=request)
        self.assertIsNone(replay.usage["mock_calls"])
        self.assertEqual(replay.usage["held_mock_calls"], 1)
        self.assertEqual(port.attempts, 0)


if __name__ == "__main__":
    unittest.main()
