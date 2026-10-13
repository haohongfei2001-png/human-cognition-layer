"""Real persistent reading protocol tests; no literary competency claim."""

import asyncio
from dataclasses import asdict, replace
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from hcl import HCL, ExecutionBudget, ExecutionIssue
from hcl.kernel.types import HCLFailure, Issue, Principal, TaskRequest
from hcl.memory.store import StateStore
from hcl.models.gateway import ModelGateway, OfflineModelPort
from hcl.runtime.execution import ExecutionRunner
from hcl.runtime.reading_coordinator import ReadingCoordinator, initial_state
from hcl.runtime.reading_fragments import partition, validate
from hcl.runtime.recovery import RecoveryManager


class Crash(BaseException):
    pass


class ReadingCoordinatorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "state.sqlite"
        self.owner = Principal("tenant", "alice")
        self.store = StateStore.sqlite(self.path, revision=True)
        self.store.create_session("s", self.owner, frozenset({"bob"}))
        self.handle = self.store.put_source("s", self.owner, "book", "a" * 2800)
        self.request = TaskRequest(
            "read",
            "Read supplied original.",
            (self.handle,),
            "s",
            self.owner,
            budget=ExecutionBudget(
                max_mock_calls=10,
                max_request_bytes=7500,
                max_context_tokens=7500,
                max_output_bytes=10000,
                max_visible_output_tokens=10000,
                max_total_output_bytes=200000,
            ),
            issue=ExecutionIssue(
                "root", goals=(Issue("reading", "model.respond", "book"),)
            ),
        )

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    @staticmethod
    def validator(snapshot, chunk, raw, budget):
        if raw != "candidate":
            raise HCLFailure(
                "INVALID_REQUEST",
                "literature_compile",
                "INVALID_READING_FRAGMENT",
                "candidate",
                "The reading proposal is invalid.",
            )

    def runner(self, responses=None, resume=False):
        port = OfflineModelPort("candidate", responses=responses)
        client = HCL(
            self.store, principal=self.owner, gateway=ModelGateway(self.store, port)
        )
        runner = ExecutionRunner(client._engine)
        runner.request = self.request
        snapshot = self.store.snapshot("s", self.owner, self.request.source_handles)
        if resume:
            lease, checkpoint, replay = runner.ledger.open(self.request, snapshot, None)
            runner.lease = lease
            runner._restore(checkpoint)
        else:
            plan = partition(
                runner.context,
                snapshot,
                self.request.question,
                "semantic_compile",
                self.request.budget,
                port.describe(),
            )
            runner.nodes = runner.planner.expand(self.request.issue.goals)
            node = runner.nodes["reading:respond"]
            node["reading"] = initial_state(plan)
            runner.snapshots = {"reading": snapshot}
            runner.counters = dict(
                steps=0,
                local_reserved=0,
                local_observed=0,
                local_unknown=False,
                feedback=0,
                semantic_profile=asdict(runner.engine._semantic.profile),
                model_capabilities=asdict(port.describe()),
            )
            runner.lease, _, _ = runner.ledger.open(
                self.request, snapshot, runner._checkpoint()
            )
        node = runner.nodes["reading:respond"]
        return runner, node, ReadingCoordinator(runner, self.validator), port

    def step(self, runner, node, coordinator):
        runner._tick(self.request, node)
        done = asyncio.run(coordinator.advance(self.request, node))
        node["state"] = "DONE" if done else "PENDING"
        runner._save()
        return done

    def reopen(self, old_owner):
        self.store.close()
        self.store = StateStore.sqlite(self.path)
        RecoveryManager(self.store).resume_execution(
            self.request, expected_owner_id=old_owner
        )

    def test_sequential_packets_validate_partition_once_and_each_step_is_counted(self):
        runner, node, coordinator, port = self.runner()
        count = len(node["reading"]["records"])
        self.assertGreaterEqual(count, 3)
        with patch("hcl.runtime.reading_fragments.validate", wraps=validate) as checks:
            while not self.step(runner, node, coordinator):
                pass
            rows = coordinator.candidates(self.request, node)
            self.assertEqual(checks.call_count, 1)
        self.assertEqual(len(rows), count)
        self.assertEqual(port.attempts, count)
        self.assertEqual(runner.counters["steps"], count)
        self.assertEqual(
            "".join(s.text for c, raw in rows for s in c.segments), "a" * 2800
        )
        self.assertNotIn("raw_return", node)
        self.assertEqual(runner.ledger.usage(runner.lease)["held_mock_calls"], count)

    def test_second_return_persisted_crash_reuses_return_then_only_sends_remaining(
        self,
    ):
        runner, node, coordinator, port = self.runner()
        self.step(runner, node, coordinator)
        old_owner = self.store.owner_id

        def fault(stage):
            if stage == "return_persisted":
                raise Crash()

        with patch.object(self.store, "_checkpoint", fault), self.assertRaises(Crash):
            self.step(runner, node, coordinator)
        self.assertEqual(port.attempts, 2)
        self.reopen(old_owner)
        runner, node, coordinator, port2 = self.runner(resume=True)
        while not self.step(runner, node, coordinator):
            pass
        count = len(node["reading"]["records"])
        self.assertEqual(port2.attempts, count - 2)
        self.assertEqual(len(coordinator.candidates(self.request, node)), count)
        self.assertEqual(runner.ledger.usage(runner.lease)["mock_calls"], count)

    def test_fragment_repair_does_not_resend_completed_prefix_or_change_original_call(
        self,
    ):
        runner, node, coordinator, port = self.runner(
            ("candidate", "{", *("candidate" for _ in range(20)))
        )
        self.step(runner, node, coordinator)
        with self.assertRaises(HCLFailure):
            self.step(runner, node, coordinator)
        first_id = node["reading"]["records"][0]["call_id"]
        bad = node["reading"]["records"][1]["call_id"]
        self.assertTrue(
            coordinator.repair(
                node,
                dict(
                    kind="REPRESENTATION_REPAIR",
                    code="INVALID_READING_FRAGMENT",
                    field="candidate",
                ),
            )
        )
        while not self.step(runner, node, coordinator):
            pass
        self.assertEqual(node["reading"]["records"][0]["call_id"], first_id)
        self.assertNotEqual(node["reading"]["records"][1]["call_id"], bad)
        self.assertEqual(port.attempts, len(node["reading"]["records"]) + 1)
        old = runner.ledger.tasks.call(runner.lease, bad)
        self.assertEqual(self.store._get_object(old["response_hash"]), "{")
        self.assertIn("READING_COMPILE_REJECTED", old["validation_code"])

    def test_second_unknown_cannot_resume_or_send_third(self):
        runner, node, coordinator, port = self.runner()
        self.step(runner, node, coordinator)
        old_owner = self.store.owner_id

        def fault(stage):
            if stage == "send_started":
                raise Crash()

        with patch.object(self.store, "_checkpoint", fault), self.assertRaises(Crash):
            self.step(runner, node, coordinator)
        self.store.close()
        self.store = StateStore.sqlite(self.path)
        with self.assertRaises(HCLFailure) as caught:
            RecoveryManager(self.store).resume_execution(
                self.request, expected_owner_id=old_owner
            )
        self.assertEqual(caught.exception.diagnostic.code, "UNKNOWN_SEND_NO_RESUME")
        self.assertEqual(port.attempts, 1)
        with self.store._transaction() as db:
            calls = list(db.execute("SELECT * FROM calls"))
        self.assertEqual(len(calls), 2)
        self.assertEqual({r["state"] for r in calls}, {"RETURNED", "UNKNOWN"})

    def test_late_change_or_revoke_never_sends_next_packet(self):
        for revoke in (False, True):
            with self.subTest(revoke=revoke):
                runner, node, coordinator, port = self.runner()
                self.step(runner, node, coordinator)
                peer = StateStore.sqlite(self.path)
                try:
                    if revoke:
                        peer.set_readers("s", self.owner, "book", frozenset({"bob"}))
                    else:
                        peer.put_source("s", self.owner, "book", "changed")
                    with self.assertRaises(HCLFailure):
                        self.step(runner, node, coordinator)
                    self.assertEqual(port.attempts, 1)
                finally:
                    peer.close()
            # Separate task/input for the next independent schedule.
            if not revoke:
                self.handle = self.store.put_source("s", self.owner, "book", "a" * 2800)
                self.request = replace(
                    self.request,
                    request_id="read-revoke",
                    source_handles=(self.handle,),
                )

    def test_limits_are_original_shared_task_and_no_hidden_fragment_loop(self):
        self.request = replace(
            self.request,
            budget=replace(self.request.budget, max_steps=1, max_mock_calls=1),
        )
        runner, node, coordinator, port = self.runner()
        self.assertFalse(self.step(runner, node, coordinator))
        with self.assertRaises(HCLFailure) as caught:
            self.step(runner, node, coordinator)
        self.assertEqual(caught.exception.diagnostic.code, "EXECUTION_STEP_BUDGET")
        self.assertEqual(port.attempts, 1)


if __name__ == "__main__":
    unittest.main()
