"""Real persistent interruption, explicit ownership transfer and no resend."""

from dataclasses import replace
import json
import unittest
from unittest.mock import patch

from hcl import HCL
from hcl.kernel.types import HCLFailure
from hcl.memory.store import StateStore
from hcl.models.gateway import ModelGateway, OfflineModelPort
from hcl.runtime.recovery import RecoveryManager
from tests import test_unified_s23 as graph_fixtures


class Crash(BaseException):
    pass


class ExecutionRecoveryTests(graph_fixtures.ExecutionGraphTests):
    # Only tests in this class, without rerunning imported superclass contracts.
    def _crash_and_reopen(self, seam, request, response):
        port = OfflineModelPort(response)
        client = HCL(self.store, principal=self.owner, gateway=ModelGateway(self.store, port))
        owner_id = self.store.owner_id
        crashed = False

        def fault(stage):
            nonlocal crashed
            if stage == seam and not crashed:
                crashed = True
                raise Crash()

        with patch.object(self.store, "_checkpoint", fault), self.assertRaises(Crash):
            client.run_sync(request)
        self.store.close()
        self.store = StateStore.sqlite(self.path)
        return owner_id, port

    def test_known_return_after_crash_is_recompiled_without_any_new_send(self):
        request = self.semantic_request()
        old_owner, first = self._crash_and_reopen("return_persisted", request, json.dumps(self.candidate()))
        before, port = self.run_request(request)
        self.assertEqual(before.diagnostics[0].code, "TASK_IN_PROGRESS")
        self.assertEqual(port.attempts, 0)
        token = RecoveryManager(self.store).resume_execution(request, expected_owner_id=old_owner)
        self.assertEqual(token.owner_id, self.store.owner_id)
        result, port = self.run_request(request)
        self.assertEqual(result.status, "COMPLETED", result.diagnostics)
        self.assertEqual(first.attempts, 1)
        self.assertEqual(port.attempts, 0)
        self.assertEqual(result.usage["mock_calls"], 1)

    def test_computed_and_committed_crash_points_reuse_exact_effects(self):
        for seam in ("execution_computed", "execution_effects_committed"):
            with self.subTest(seam=seam):
                request = replace(self.request(), request_id=seam)
                old_owner, _ = self._crash_and_reopen(seam, request, "unused")
                RecoveryManager(self.store).resume_execution(request, expected_owner_id=old_owner)
                result, port = self.run_request(request)
                self.assertEqual(result.status, "COMPLETED", result.diagnostics)
                self.assertEqual(port.attempts, 0)
                self.assertEqual(result.usage["local_evaluations"], 2)
        self.assertEqual(len(self.store.inferences("s", self.owner)), 2)

    def test_unknown_send_cannot_be_renamed_into_a_fresh_call(self):
        request = self.semantic_request()
        old_owner, first = self._crash_and_reopen("send_started", request, json.dumps(self.candidate()))
        with self.assertRaises(HCLFailure) as caught:
            RecoveryManager(self.store).resume_execution(request, expected_owner_id=old_owner)
        self.assertEqual(caught.exception.diagnostic.code, "UNKNOWN_SEND_NO_RESUME")
        result, port = self.run_request(request)
        self.assertEqual(result.diagnostics[0].code, "TASK_INTERRUPTED_NO_RESEND")
        self.assertIsNone(result.usage["mock_calls"])
        self.assertEqual(result.usage["held_mock_calls"], 1)
        self.assertEqual(first.attempts + port.attempts, 0)

    def test_reserved_no_send_keeps_hold_and_does_not_silently_replace_attempt(self):
        request = self.semantic_request()
        old_owner, first = self._crash_and_reopen("call_reserved", request, json.dumps(self.candidate()))
        RecoveryManager(self.store).resume_execution(request, expected_owner_id=old_owner)
        result, port = self.run_request(request)
        self.assertEqual(result.status, "FAILED")
        self.assertEqual(result.usage["mock_calls"], 0)
        self.assertEqual(result.usage["held_mock_calls"], 1)
        self.assertEqual(first.attempts + port.attempts, 0)

    def test_invalid_return_recovery_still_applies_original_byte_and_token_limits(self):
        request = replace(self.semantic_request(), budget=replace(self.budget, max_visible_output_tokens=1))
        old_owner, _ = self._crash_and_reopen("return_persisted", request, json.dumps(self.candidate()))
        RecoveryManager(self.store).resume_execution(request, expected_owner_id=old_owner)
        result, port = self.run_request(request)
        self.assertEqual(result.status, "BUDGET_EXHAUSTED")
        self.assertEqual(port.attempts, 0)
        self.assertEqual(result.usage["mock_calls"], 1)

    def test_foreign_recovery_and_old_owner_lease_cannot_continue(self):
        request = self.request()
        old_owner, _ = self._crash_and_reopen("execution_computed", request, "unused")
        recovery = RecoveryManager(self.store)
        with self.assertRaises(HCLFailure):
            recovery.resume_execution(request, expected_owner_id="other-owner")
        recovery.resume_execution(request, expected_owner_id=old_owner)
        with self.assertRaises(HCLFailure):
            recovery.resume_execution(request, expected_owner_id=old_owner)
        result, _ = self.run_request(request)
        self.assertEqual(result.status, "COMPLETED")

    def test_recovery_does_not_resurrect_revoked_source(self):
        request = self.request()
        old_owner, _ = self._crash_and_reopen("execution_computed", request, "unused")
        self.store.set_readers("s", self.owner, "source", frozenset({"bob"}))
        with self.assertRaises(HCLFailure) as caught:
            RecoveryManager(self.store).resume_execution(request, expected_owner_id=old_owner)
        self.assertEqual(caught.exception.status, "DENIED")
        result, port = self.run_request(request)
        self.assertEqual(result.status, "DENIED")
        self.assertEqual(result.claim_records, ())
        self.assertEqual(port.attempts, 0)

    def test_recovery_cannot_silently_change_model_capabilities(self):
        request = self.semantic_request()
        old_owner, _ = self._crash_and_reopen("return_persisted", request, json.dumps(self.candidate()))
        RecoveryManager(self.store).resume_execution(request, expected_owner_id=old_owner)
        changed = OfflineModelPort(context_tokens=65536)
        result = HCL(self.store, principal=self.owner, gateway=ModelGateway(self.store, changed)).run_sync(
            request
        )
        self.assertEqual(result.diagnostics[0].code, "EXECUTION_PROFILE_CHANGED")
        self.assertEqual(changed.attempts, 0)
        self.assertEqual(result.usage["held_mock_calls"], 1)
        self.assertFalse(result.answer)
        # A failed profile change did not consume the task or change its binding.
        self.store.close()
        self.store = StateStore.sqlite(self.path)
        with self.store._transaction() as db:
            current_owner = db.execute("SELECT owner_id FROM tasks").fetchone()[0]
        RecoveryManager(self.store).resume_execution(request, expected_owner_id=current_owner)
        result, port = self.run_request(request)
        self.assertEqual(result.status, "COMPLETED", result.diagnostics)
        self.assertEqual(port.attempts, 0)

    def test_recovery_binds_solver_profile_and_preserves_unknown_local_hold(self):
        from hcl.semantics.frames import SemanticProfile
        from hcl.operators.local_model import LocalModelOperator

        request = self.request()
        old_owner = self.store.owner_id
        with patch.object(LocalModelOperator, "run", side_effect=Crash()), self.assertRaises(Crash):
            self.run_request(request)
        self.store.close()
        self.store = StateStore.sqlite(self.path)
        RecoveryManager(self.store).resume_execution(request, expected_owner_id=old_owner)
        port = OfflineModelPort()
        changed = replace(SemanticProfile(), solver_timeout_ms=101)
        result = HCL(
            self.store,
            principal=self.owner,
            gateway=ModelGateway(self.store, port),
            semantic_profile=changed,
        ).run_sync(request)
        self.assertEqual(result.diagnostics[0].code, "EXECUTION_PROFILE_CHANGED")
        self.assertEqual(port.attempts, 0)
        # Explicitly recover the claimed lease, then retain the uncertain first
        # local computation alongside the successful second local reservation.
        current_owner = self.store.owner_id
        self.store.close()
        self.store = StateStore.sqlite(self.path)
        RecoveryManager(self.store).resume_execution(request, expected_owner_id=current_owner)
        result, port = self.run_request(request)
        self.assertEqual(result.status, "COMPLETED", result.diagnostics)
        self.assertIsNone(result.usage["local_evaluations"])
        self.assertEqual(result.usage["observed_local_evaluations"], 2)
        self.assertEqual(result.usage["held_local_evaluations"], 4)
        self.assertEqual(port.attempts, 0)


def load_tests(loader, tests, pattern):
    # Explicitly enumerate new methods. Base is a fixture only.
    return unittest.TestSuite(
        ExecutionRecoveryTests(name) for name in ExecutionRecoveryTests.__dict__ if name.startswith("test_")
    )
