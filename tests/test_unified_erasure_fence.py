"""Only disposable synthetic namespaces; no user or production data is erased."""
from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from hcl import HCL
from hcl.kernel.types import HCLFailure, Issue, Principal, TaskRequest
from hcl.memory.governance import verify_inventory
from hcl.memory.store import StateStore
from hcl.runtime.budget import TaskBudgetLedger
from hcl.runtime.execution_ledger import ExecutionLedger


class Crash(BaseException):
    pass


class ErasureFenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "state.sqlite"
        self.connections = []
        self.store = self.open()
        self.owner = Principal("tenant", "owner")
        self.store.create_session("session", self.owner, frozenset({"reader"}))
        self.source_id = "ERASED_SOURCE_CANARY"
        self.handle = self.store.put_source("session", self.owner, self.source_id, "ERASED_ORIGINAL_CANARY")
        self.other = self.store.put_source("session", self.owner, "independent", "INDEPENDENT_ORIGINAL_CANARY")

    def open(self):
        store = StateStore.sqlite(self.path, revision=not self.path.exists())
        self.addCleanup(store.close)
        return store

    def request(self, handle=None, key="task"):
        handle = handle or self.handle
        return TaskRequest(key, "Show the source", (handle,), "session", self.owner,
                           issue=Issue("report", "source.report", handle.source_id))

    def begin(self, *, store=None, plan=None):
        store = store or self.store
        plan = plan or store.plan_source_erasure("session", self.owner, self.source_id, expected_version=1)
        return store.begin_source_erasure("session", self.owner, self.source_id, expected_version=1,
                                         plan_hash=plan["plan_hash"], erasure_id="a" * 32)

    def test_erased_history_cannot_replay_export_rebuild_or_reingest(self):
        request = self.request()
        result = HCL(self.store, principal=self.owner).run_sync(request)
        self.assertEqual(result.status, "COMPLETED")
        other_request = self.request(self.other, "independent-task")
        other = HCL(self.store, principal=self.owner).run_sync(other_request)
        before_epoch = self.store.snapshot("session", self.owner, (self.handle,)).access_epoch
        receipt = self.begin()
        self.assertEqual(receipt["status"], "LOGICALLY_ERASED_PHYSICAL_PENDING")
        self.assertNotIn(self.source_id, json.dumps(receipt))
        self.assertNotIn("ERASED_ORIGINAL_CANARY", json.dumps(receipt))
        with self.store._transaction() as db:
            verify_inventory(db)
        events = "\n".join(row[0] for row in self.store._db.execute("SELECT payload FROM events"))
        self.assertNotIn(self.source_id, events)
        self.assertFalse(self.store._db.execute("SELECT * FROM sources WHERE source_id=?", (self.source_id,)).fetchall())
        self.store.rebuild_projections()
        peer = self.open()
        replay = HCL(peer, principal=self.owner).run_sync(request)
        self.assertEqual(replay.status, "DENIED")
        self.assertEqual(replay.diagnostics[0].code, "CONTENT_ERASED")
        self.assertEqual(replay.answer, "")
        self.assertFalse(replay.claim_records)
        for key in result.usage:
            self.assertEqual(replay.usage[key], result.usage[key], key)
        with self.assertRaises(HCLFailure):
            ExecutionLedger(peer).audit(request)
        with self.assertRaises(HCLFailure) as error:
            peer.put_source("session", self.owner, self.source_id, "LATE_RETURN_CANARY")
        self.assertEqual(error.exception.diagnostic.code, "CONTENT_ERASED")
        independent = HCL(peer, principal=self.owner).run_sync(other_request)
        self.assertEqual(independent.status, "COMPLETED")
        self.assertEqual(independent.answer, other.answer)
        self.assertTrue(independent.execution_receipt["replayed"])
        self.assertEqual(peer.snapshot("session", self.owner, (self.other,)).access_epoch, before_epoch)

    def test_unknown_hold_and_late_provider_return_remain_fenced(self):
        request = self.request(key="PRIVATE_REQUEST_NAME_CANARY")
        request = replace(request, issue=Issue("m", "model.respond"),
                          budget=replace(request.budget, max_mock_calls=1))
        snapshot = self.store.snapshot("session", self.owner, (self.handle,))
        ledger = TaskBudgetLedger(self.store)
        lease, _ = ledger.bind(request, snapshot)
        ledger.reserve(lease, snapshot, request.question, request.budget, "PRIVATE_CALL_CANARY", "ERASED_WIRE_CANARY")
        ledger.transition(lease, "PRIVATE_CALL_CANARY", "RESERVED", "SEND_STARTED", snapshot=snapshot)
        receipt = self.begin()
        self.assertEqual(receipt["accounting_preserved"], dict(held_calls=1, unknown_calls=1, observed_calls=0))
        original_count = len(list(self.store.object_root.iterdir()))
        with self.assertRaises(HCLFailure) as error:
            ledger.transition(lease, "PRIVATE_CALL_CANARY", "SEND_STARTED", "RETURNED", response="LATE_RETURN_CANARY")
        self.assertEqual(error.exception.diagnostic.code, "CONTENT_ERASED")
        self.assertIsNone(error.exception.resource_usage["mock_calls"])
        self.assertEqual(len(list(self.store.object_root.iterdir())), original_count)
        replay = HCL(self.open(), principal=self.owner).run_sync(request)
        self.assertEqual(replay.status, "DENIED")
        self.assertIsNone(replay.usage["mock_calls"])
        self.assertEqual(replay.usage["held_mock_calls"], 1)
        row = self.store._db.execute("SELECT * FROM calls").fetchone()
        self.assertEqual(row["state"], "SEND_STARTED")
        self.assertIsNone(row["attempted"])
        self.assertEqual(row["request_hash"], "")
        text = "\n".join(row[0] for row in self.store._db.execute("SELECT payload FROM events"))
        self.assertNotIn("PRIVATE_", text)
        self.store.rebuild_projections()

    def test_stale_plan_denied_before_mutation_and_crash_is_atomic(self):
        plan = self.store.plan_source_erasure("session", self.owner, self.source_id, expected_version=1)
        self.store.put_source("session", self.owner, "third", "Synthetic unrelated write")
        with self.assertRaises(HCLFailure) as error:
            self.begin(plan=plan)
        self.assertEqual(error.exception.diagnostic.code, "ERASURE_PLAN_CHANGED")
        for stage, published in (("erasure_logical_fence_persisted", False), ("erasure_logical_fence_committed", True)):
            with self.subTest(stage=stage):
                plan = self.store.plan_source_erasure("session", self.owner, self.source_id, expected_version=1)
                def crash(at):
                    if at == stage:
                        raise Crash()
                with patch.object(self.store, "_checkpoint", side_effect=crash), self.assertRaises(Crash):
                    self.begin(plan=plan)
                peer = self.open()
                self.assertEqual(bool(peer._db.execute("SELECT 1 FROM source_tombstones").fetchone()), published)
                with peer._transaction() as db:
                    verify_inventory(db)
                if published:
                    self.assertEqual(self.begin(store=peer, plan=plan)["status"], "LOGICALLY_ERASED_PHYSICAL_PENDING")
                else:
                    self.assertEqual(peer.snapshot("session", self.owner, (self.handle,)).immutable_views[self.source_id].text,
                                     "ERASED_ORIGINAL_CANARY")

    def test_nonowner_cannot_change_or_observe_erasure(self):
        plan = self.store.plan_source_erasure("session", self.owner, self.source_id, expected_version=1)
        for principal in (Principal("tenant", "reader"), Principal("foreign", "owner")):
            with self.assertRaises(HCLFailure):
                self.store.begin_source_erasure("session", principal, self.source_id, expected_version=1,
                                               plan_hash=plan["plan_hash"], erasure_id="a" * 32)
        self.assertFalse(self.store._db.execute("SELECT * FROM erasures").fetchall())

    def test_independent_historical_source_identity_survives_rechained_log(self):
        snapshot = self.store.historical_snapshot("session", self.owner, (self.other,), known_at=2)
        before = snapshot.query_dependencies
        self.fence = self.begin()
        self.store.validate_snapshot(snapshot)
        after = self.store.historical_snapshot("session", self.owner, (self.other,), known_at=2)
        self.assertEqual(after.query_dependencies, before)
        self.assertEqual(after.historical_sources, snapshot.historical_sources)
        self.store.resume_source_erasure("session", self.owner, "a" * 32)
        peer = self.open()
        peer.validate_snapshot(snapshot)
        self.assertEqual(peer.historical_snapshot("session", self.owner, (self.other,), known_at=2).query_dependencies, before)

    def test_erasure_during_cached_wal_read_returns_no_content_and_preserves_usage(self):
        import asyncio
        from hcl.kernel.types import TaskResult
        for stream in (False, True):
            # Each schedule has its own disposable store and its own source.
            child = ErasureFenceTests("test_nonowner_cannot_change_or_observe_erasure")
            child.setUp()
            self.addCleanup(child.doCleanups)
            first = HCL(child.store, principal=child.owner).run_sync(child.request())
            self.assertEqual(first.status, "COMPLETED")
            peer = child.open()
            peer._db.execute("PRAGMA busy_timeout=1")
            fired = False
            original = child.store._get_object
            def race(digest):
                nonlocal fired
                value = original(digest)
                if type(value) is TaskResult and not fired:
                    fired = True
                    child.begin(store=peer)
                    receipt = peer.resume_source_erasure("session", child.owner, "a" * 32)
                    self.assertIn("DATABASE_SCRUB_PENDING", receipt["limitations"])
                return value
            with patch.object(child.store, "_get_object", side_effect=race):
                if stream:
                    async def collect():
                        return [event async for event in HCL(child.store, principal=child.owner).stream(child.request())]
                    result = asyncio.run(collect())[-1].result
                else:
                    result = HCL(child.store, principal=child.owner).run_sync(child.request())
            self.assertTrue(fired)
            self.assertEqual(result.status, "DENIED")
            self.assertFalse(result.claim_records)
            self.assertEqual(result.answer, "")
            from hcl.memory import codec
            self.assertNotIn("ERASED_ORIGINAL_CANARY", codec.dumps(result).decode())
            self.assertNotIn(child.source_id, codec.dumps(result).decode())
            for key, value in first.usage.items():
                self.assertEqual(result.usage[key], value, key)
            self.assertEqual(peer.resume_source_erasure("session", child.owner, "a" * 32)["status"],
                             "LOCAL_REFERENCE_ERASURE_COMPLETE")

    def test_nested_query_evidence_retains_origin_outside_new_scan_scope(self):
        from tests import test_unified_s4_engine as arguments
        from hcl.kernel.dependencies import QueryDelta
        from hcl.kernel.retrieval import RetrievalQuery
        from hcl.memory.query_store import QueryStore
        from hcl.memory.governance import owner_key, read_owner
        from hcl.memory.lineage import source_token
        from hcl.memory.retention_objects import pending
        fixture = arguments.ArgumentExecutionTests()
        fixture.setUp()
        self.addCleanup(fixture.tearDown)
        result, _ = fixture.run_candidate()
        self.assertEqual(result.status, "COMPLETED")
        template = fixture.inference(result)  # Real M13 computation, unchanged proof values.
        store = fixture.store
        store.put_source("s", fixture.owner, "independent", "different source")
        query = RetrievalQuery(dict(support="zzzunknown", challenge="zzzunknown", alternative="zzzunknown"),
                               source_scope=("text",))
        snapshot = QueryStore(store).search("s", fixture.owner, query)
        self.assertFalse(snapshot.source_versions)
        def commit(snapshot, key):
            delta = QueryDelta("s", fixture.owner, snapshot.revision, snapshot.access_epoch,
                snapshot.rule_version, snapshot.source_versions, (replace(template, result_id=key),), snapshot.query_dependencies)
            store.commit(snapshot.revision, snapshot.source_versions, snapshot.access_epoch, delta)
        commit(snapshot, "first-retained-query")
        nested = replace(query, source_scope=("independent",), evidence_result_ids=("first-retained-query",))
        second = QueryStore(store).search("s", fixture.owner, nested)
        self.assertEqual(set(second.query_views["0"]["search_scope"]), {"independent"})
        commit(second, "nested-retained-query")
        salt = bytes.fromhex(store._revision_control["governance_salt"])
        expected_token = source_token(salt, "s", "text")
        owner = read_owner(store._db, owner_key(store._db, ("inference", "s", "nested-retained-query")))
        self.assertIn(["s", expected_token, 1], json.loads(owner["bindings"]))
        # The same lineage must exist before the checkpoint/event commits, not
        # just after the materialized reference successfully publishes.
        with self.assertRaises(Crash):
            with store._transaction(True):
                store._put_content("UNCOMMITTED_PROOF_CANARY", session_id="s", context=second)
                raise Crash()
        self.assertTrue(any(["s", expected_token, 1] in row["bindings"] for row in pending(store)))
        plan = store.plan_source_erasure("s", fixture.owner, "text", expected_version=1)
        self.assertIn(owner["owner_key"], plan["affected_owners"])
        store.begin_source_erasure("s", fixture.owner, "text", expected_version=1,
                                   plan_hash=plan["plan_hash"], erasure_id="c" * 32)
        self.assertIsNone(store._db.execute("SELECT 1 FROM inferences WHERE result_id='nested-retained-query'").fetchone())
        self.assertEqual(store.resume_source_erasure("s", fixture.owner, "c" * 32)["status"],
                         "LOCAL_REFERENCE_ERASURE_COMPLETE")

    def test_graph_erasure_at_compute_commit_and_delivery_keeps_accounting(self):
        import asyncio
        from tests import test_unified_s4_engine as arguments
        from hcl.models.gateway import ModelGateway, OfflineModelPort
        for seam in ("execution_computed", "execution_effects_committed", "task_finished"):
            for stream in (False, True):
                with self.subTest(seam=seam, stream=stream):
                    fixture = arguments.ArgumentExecutionTests()
                    fixture.setUp()
                    self.addCleanup(fixture.tearDown)
                    peer = StateStore.sqlite(fixture.path)
                    self.addCleanup(peer.close)
                    port = OfflineModelPort(json.dumps(fixture.candidate()))
                    client = HCL(fixture.store, principal=fixture.owner, gateway=ModelGateway(fixture.store, port))
                    fired = False
                    def erase(at):
                        nonlocal fired
                        if at == seam and not fired:
                            fired = True
                            plan = peer.plan_source_erasure("s", fixture.owner, "text", expected_version=1)
                            peer.begin_source_erasure("s", fixture.owner, "text", expected_version=1,
                                plan_hash=plan["plan_hash"], erasure_id="9" * 32)
                            peer.resume_source_erasure("s", fixture.owner, "9" * 32)
                    with patch.object(fixture.store, "_checkpoint", side_effect=erase):
                        if stream:
                            async def collect():
                                return [event async for event in client.stream(fixture.request)]
                            result = asyncio.run(collect())[-1].result
                        else:
                            result = client.run_sync(fixture.request)
                    self.assertTrue(fired)
                    self.assertEqual(result.status, "DENIED")
                    self.assertFalse(result.claim_records)
                    self.assertEqual(result.answer, "")
                    account = json.loads(peer._db.execute("SELECT usage FROM erased_tasks").fetchone()[0])
                    for key in ("mock_calls", "held_mock_calls", "observed_mock_calls", "observed_output_bytes",
                                "observed_local_evaluations", "held_local_evaluations"):
                        self.assertEqual(result.usage[key], account[key], key)
                    self.assertEqual(result.usage["mock_calls"], 1)
                    self.assertGreater(result.usage["observed_local_evaluations"], 0)
                    no_repeat = OfflineModelPort("must not be sent")
                    repeated = HCL(peer, principal=fixture.owner, gateway=ModelGateway(peer, no_repeat)).run_sync(fixture.request)
                    self.assertEqual(repeated.status, "DENIED")
                    self.assertEqual(repeated.usage["mock_calls"], 1)
                    self.assertEqual(no_repeat.attempts, 0)


if __name__ == "__main__":
    unittest.main()
