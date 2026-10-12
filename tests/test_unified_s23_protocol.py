"""Frozen executable protocol, diagnostics, authority and resource contracts."""

from dataclasses import replace
import asyncio
import inspect
import json
import unittest
from unittest.mock import patch

from hcl import HCL, ExecutionIssue
from hcl.kernel.execution import LocalModel, ModelIssue, ExecutionCheckpoint, PROTOCOL
from hcl.kernel.types import HCLFailure, Issue
from hcl.memory import codec
from hcl.models.gateway import ModelGateway, OfflineModelPort, AuthorizedContext, CallSpec
from hcl.operators.local_model import LocalModelOperator
from hcl.runtime.recovery import RecoveryManager
from tests import test_unified_s23 as graph_fixtures


class ProtocolTests(graph_fixtures.ExecutionGraphTests):
    def test_three_argument_operator_performs_real_finite_computation(self):
        self.assertEqual(
            list(inspect.signature(LocalModelOperator.run).parameters),
            ["self", "snapshot", "issue", "allowance"],
        )
        snapshot = self.store.snapshot("s", self.owner, (self.handle,))
        model = LocalModel(
            "m",
            "finite-interpretation-1",
            {"source_id": "source"},
            snapshot.source_versions,
            ("finite-assumption",),
            ("unexplained-observation",),
            ("opaque-event",),
        )
        issue = ModelIssue("m", "logic.check_interpretation", "source", model)
        result = LocalModelOperator().run(snapshot, issue, self.budget)
        self.assertEqual(result.effects, ("append_inference",))
        self.assertTrue(result.candidate_delta.new_inferences[0].values["is_countermodel"])
        self.assertEqual(self.store.inferences("s", self.owner), ())
        self.assertEqual(codec.loads(codec.dumps(model)), model)
        self.assertIn("LOCAL_MODEL_FIT_RESIDUALS", result.issues)
        self.assertIn("UNMODELED_OBSERVATIONS", result.issues)
        self.assertEqual(
            result.candidate_delta.new_inferences[0].values["local_model"]["fit_residuals"],
            ("unexplained-observation",),
        )
        self.assertEqual(model.fit_residuals, ("unexplained-observation",))
        self.assertEqual(model.unmodeled_observations, ("opaque-event",))
        with self.assertRaises(TypeError):
            model.ast["source_id"] = "other"

    def test_executable_code_and_unknown_dialects_are_rejected_as_data(self):
        snapshot = self.store.snapshot("s", self.owner, (self.handle,))
        with self.assertRaises(ValueError):
            LocalModel("m", "python", {"code": "import os"}, snapshot.source_versions)
        model = LocalModel(
            "m",
            "finite-interpretation-1",
            {"source_id": "source", "exec": "private-path"},
            snapshot.source_versions,
        )
        with self.assertRaises(HCLFailure) as caught:
            LocalModelOperator().run(
                snapshot, ModelIssue("m", "logic.check_interpretation", "source", model), self.budget
            )
        self.assertEqual(caught.exception.diagnostic.code, "LOCAL_MODEL_AST")
        self.assertNotIn("private-path", str(caught.exception))

    def test_operator_effect_mismatch_never_commits(self):
        original = LocalModelOperator.run

        def bad(op, snapshot, issue, allowance):
            return replace(original(op, snapshot, issue, allowance), effects=("overwrite_source",))

        with patch.object(LocalModelOperator, "run", bad):
            result, _ = self.run_request()
        self.assertEqual(result.status, "FAILED")
        self.assertEqual(self.store.inferences("s", self.owner), ())
        self.assertEqual(result.claim_records, ())
        self.assertFalse(result.answer)

    def test_run_stream_share_verified_projection_and_no_early_claims(self):
        request = self.semantic_request()
        port = OfflineModelPort(json.dumps(self.candidate()))
        client = HCL(self.store, principal=self.owner, gateway=ModelGateway(self.store, port))

        async def stream():
            return [event async for event in client.stream(request)]

        events = asyncio.run(stream())
        self.assertEqual([e.kind for e in events], ["status", "result"])
        self.assertIsNone(events[0].result)
        replay = client.run_sync(request)
        self.assertEqual(events[-1].result.answer, replay.answer)
        self.assertEqual(events[-1].result.claim_records, replay.claim_records)
        self.assertEqual(port.attempts, 1)

    def test_complete_raw_audit_separate_from_context_and_denied_after_revoke(self):
        request = self.semantic_request()
        result, port = self.run_request(request, ("{", json.dumps(self.candidate())))
        self.assertEqual(result.status, "COMPLETED")
        audit = RecoveryManager(self.store).execution_audit(request)
        self.assertEqual(audit["calls"][0]["response"], "{")
        self.assertTrue(
            any(cp.nodes["reason:compile"].get("raw_return") == "{" for cp in audit["checkpoints"])
        )
        checkpoint = audit["checkpoints"][0]
        with self.assertRaises(TypeError):
            checkpoint.nodes["reason:compile"]["state"] = "DONE"
        self.store.set_readers("s", self.owner, "source", {"bob"})
        with self.assertRaises(HCLFailure) as caught:
            RecoveryManager(self.store).execution_audit(request)
        self.assertEqual(caught.exception.status, "DENIED")

    def test_budget_expansion_and_unbound_per_step_context_cannot_send(self):
        request = self.semantic_request()
        # An unrelated valid ordinary lease is not a graph step authority.
        from hcl.runtime.budget import TaskBudgetLedger

        snapshot = self.store.snapshot("s", self.owner, (self.handle,))
        ledger = TaskBudgetLedger(self.store)
        lease, _ = ledger.bind(request, snapshot)
        from hcl.runtime.context import ContextCompiler

        port = OfflineModelPort(json.dumps(self.candidate()))
        gateway = ModelGateway(self.store, port)
        chunk = ContextCompiler().chunks(
            snapshot, request.question, "semantic_compile", request.budget, port.describe()
        )[0]
        with self.assertRaises(HCLFailure):
            asyncio.run(
                gateway.generate(
                    AuthorizedContext(snapshot, request.question, "semantic_compile", None, chunk),
                    CallSpec(request.request_id, request.budget, lease, "invented"),
                )
            )
        self.assertEqual(port.attempts, 0)

    def test_confidence_only_invalid_candidate_change_is_not_progress(self):
        candidate = self.candidate()
        candidate["confidence"] = 0.7
        other = dict(candidate, confidence=0.99)
        result, port = self.run_request(
            self.semantic_request(),
            (json.dumps(candidate), json.dumps(other), json.dumps(self.candidate())),
        )
        self.assertEqual(port.attempts, 2)
        self.assertIn("NO_PROGRESS", result.unresolved_issues)

    def test_invalid_nested_goal_unicode_and_types_return_safe_diagnostics(self):
        for goal in (Issue([], "source.report"), Issue("g", []), Issue("\ud800", "source.report")):
            with self.subTest(goal=repr(goal)):
                result, _ = self.run_request(self.request((goal,)))
                self.assertEqual(result.status, "INVALID_REQUEST")
                self.assertFalse(result.answer)

    def test_delivery_budget_refusal_keeps_verified_external_result(self):
        request = self.request(budget=replace(self.budget, max_output_bytes=2))
        result, _ = self.run_request(request)
        self.assertEqual(result.status, "BUDGET_EXHAUSTED")
        self.assertEqual(result.diagnostics[0].code, "DELIVERY_CAPACITY")
        self.assertEqual(len(self.store.inferences("s", self.owner)), 1)
        self.assertFalse(result.answer)

    def test_effect_result_identity_and_foreign_snapshot_never_commit(self):
        original = LocalModelOperator.run
        for mutation in ("refs", "session", "principal"):

            def bad(op, snapshot, issue, allowance):
                value = original(op, snapshot, issue, allowance)
                if mutation == "refs":
                    return replace(value, result_refs=("invented-result",))
                delta = value.candidate_delta
                if mutation == "session":
                    delta = replace(delta, session_id="other-session")
                else:
                    delta = replace(delta, principal=replace(self.owner, subject_id="bob"))
                return replace(value, candidate_delta=delta)

            with self.subTest(mutation=mutation), patch.object(LocalModelOperator, "run", bad):
                result, _ = self.run_request(replace(self.request(), request_id=mutation))
                self.assertEqual(result.status, "FAILED")
                self.assertFalse(result.answer)
                self.assertEqual(result.claim_records, ())
                self.assertEqual(self.store.inferences("s", self.owner), ())

    def test_compact_projection_tampering_cannot_supply_a_new_answer(self):
        from hcl.kernel.execution import ProjectedResultField
        from hcl.kernel.types import AnswerContract
        from hcl.runtime.answer import AnswerAssembler

        result, _ = self.run_request(self.semantic_request(), (json.dumps(self.candidate()),))
        stored = self.store.inferences("s", self.owner)
        claim = result.claim_records[0]
        index = next(i for i, f in enumerate(claim.used_result_fields) if type(f) is ProjectedResultField)
        field = claim.used_result_fields[index]
        for changed in (
            replace(field, path=("999",)),
            replace(field, selection=("id",)),
            replace(field, value={"label": "False"}),
        ):
            fields = list(claim.used_result_fields)
            fields[index] = changed
            altered = replace(claim, used_result_fields=tuple(fields))
            contract = AnswerContract(result.answer, (altered,), "ACTUAL_RESULT_FIELDS", "NOT_CERTIFIED")
            with self.assertRaises(HCLFailure) as caught:
                AnswerAssembler().validate_compact(contract, stored)
            self.assertEqual(caught.exception.diagnostic.code, "COMPACT_RESULT_MISMATCH")

    def test_nonfinite_and_deep_candidate_returns_are_bounded_repairs(self):
        for i, raw in enumerate(('{"value":NaN}', "[" * 1100 + "0" + "]" * 1100)):
            request = replace(self.semantic_request(), request_id="bad-json-" + str(i))
            result, port = self.run_request(request, (raw, json.dumps(self.candidate())))
            self.assertEqual(result.status, "COMPLETED", result.diagnostics)
            self.assertEqual(port.attempts, 2)
            audit = RecoveryManager(self.store).execution_audit(request)
            self.assertEqual(audit["calls"][0]["response"], raw)

    def test_audit_rechecks_after_leaving_content_wal_snapshot(self):
        from hcl.memory.store import StateStore

        request = self.semantic_request()
        self.run_request(request, (json.dumps(self.candidate()),))
        peer = StateStore.sqlite(self.path)
        original = self.store._get_object
        revoked = False

        def read(digest):
            nonlocal revoked
            value = original(digest)
            if type(value) is ExecutionCheckpoint and not revoked:
                revoked = True
                peer.set_readers("s", self.owner, "source", {"bob"})
            return value

        try:
            with patch.object(self.store, "_get_object", read), self.assertRaises(HCLFailure) as caught:
                RecoveryManager(self.store).execution_audit(request)
            self.assertTrue(revoked)
            self.assertEqual(caught.exception.status, "DENIED")
        finally:
            peer.close()


def load_tests(loader, tests, pattern):
    return unittest.TestSuite(
        ProtocolTests(name) for name in ProtocolTests.__dict__ if name.startswith("test_")
    )
