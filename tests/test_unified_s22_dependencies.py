"""Actual SQLite query dependencies at commit, dispatch, finish and replay."""

from dataclasses import replace
from hashlib import sha256
import json
from pathlib import Path
import tempfile
import unittest

from hcl.kernel.dependencies import (
    IndexQuery,
    QueryDelta,
    QuerySnapshot,
    pack_dependencies,
    query_projection,
    source_index_values,
    unpack_dependencies,
)
from hcl.kernel.types import (
    BudgetSlice,
    Delta,
    HCLFailure,
    InferenceResult,
    Principal,
    RULE_VERSION,
    TaskRequest,
    TaskResult,
)
from hcl.memory import codec
from hcl.memory.store import StateStore
from hcl.runtime.budget import TaskBudgetLedger


class PersistentQueryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.path = Path(self.temporary.name) / "state.sqlite"
        self.owner, self.other = Principal("tenant", "alice"), Principal("tenant", "bob")
        self.store = StateStore.sqlite(self.path, revision=True)
        self.store.create_session("session", self.owner, {"bob"})
        self.handle = self.store.put_source("session", self.owner, "origin", "No receipt has been reported.")
        self.query = IndexQuery({"kind": "receipt", "agent_id": "alice", "message_id": "m"})
        self.index(self.handle, ())

    def tearDown(self):
        self.store.close()
        self.temporary.cleanup()

    def index(self, handle, records, complete=True):
        snapshot = self.store.snapshot("session", self.owner, (handle,))
        values = source_index_values(handle.source_id, handle.version, records, complete=complete, program={})
        identity = sha256(codec.dumps([values, snapshot.revision])).hexdigest()
        result = InferenceResult(
            identity, "revision.source_index", values, (), (), (), RULE_VERSION, "CANDIDATE_ONLY"
        )
        delta = Delta(
            "session",
            self.owner,
            snapshot.revision,
            snapshot.access_epoch,
            RULE_VERSION,
            snapshot.source_versions,
            (result,),
        )
        self.store.commit(snapshot.revision, snapshot.source_versions, snapshot.access_epoch, delta)

    def snapshot(self):
        return self.store.query_snapshot("session", self.owner, (self.handle,), (self.query,))

    def result(self):
        return TaskResult("conditional no indexed receipt", (), "COMPLETED", (), {}, {"mock_calls": 0}, None)

    def request(self):
        return TaskRequest(
            "request",
            "Who received m?",
            (self.handle,),
            "session",
            self.owner,
            budget=BudgetSlice(max_mock_calls=1),
        )

    def assert_query_changed(self, action):
        with self.assertRaises(HCLFailure) as caught:
            action()
        self.assertEqual(caught.exception.diagnostic.code, "QUERY_DEPENDENCY_CHANGED")

    def test_query_and_new_codec_round_trip_preserve_old_contract_bytes(self):
        snapshot = self.snapshot()
        self.assertIs(type(snapshot), QuerySnapshot)
        self.assertTrue(snapshot.query_views["0"]["absence_eligible"])
        self.assertEqual(codec.loads(codec.dumps(snapshot)), snapshot)
        original = {"source": 1, "schema": 2}
        self.assertEqual(pack_dependencies(original), original)
        self.assertEqual(unpack_dependencies(original), (original, ()))
        self.assertEqual(
            unpack_dependencies(pack_dependencies(snapshot.source_versions, snapshot.query_dependencies)),
            (dict(snapshot.source_versions), snapshot.query_dependencies),
        )
        request = self.request()
        self.assertEqual(
            sha256(codec.dumps(request)).hexdigest(),
            sha256(codec.dumps(codec.loads(codec.dumps(request)))).hexdigest(),
        )
        for invalid in (
            {"schema": "future", "positive": {}, "queries": []},
            {"source": 1, "queries": []},
            {"schema": "hcl-query-dependencies-1", "positive": {}, "queries": []},
        ):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                unpack_dependencies(invalid)

    def test_new_uncompiled_source_invalidates_absence_before_extraction(self):
        snapshot = self.snapshot()
        self.store.put_source("session", self.owner, "new", "Alice received m.")
        current = self.snapshot()
        self.assertFalse(current.query_views["0"]["absence_eligible"])
        self.assertEqual(current.query_views["0"]["pending"], (("new", 1, "UNCOMPILED"),))
        self.assert_query_changed(lambda: self.store.validate_snapshot(snapshot))

    def test_compiled_unrelated_source_preserves_query_hash_but_relevant_source_changes_it(self):
        original = self.snapshot()
        unrelated = self.store.put_source("session", self.owner, "unrelated", "Bob received another message.")
        self.index(
            unrelated, ({"record_id": "u", "kind": "receipt", "agent_id": "bob", "message_id": "other"},)
        )
        self.assertEqual(self.snapshot().query_dependencies, original.query_dependencies)
        self.store.validate_snapshot(original)
        relevant = self.store.put_source("session", self.owner, "new", "Alice received m.")
        self.index(relevant, ({"record_id": "r", "kind": "receipt", "agent_id": "alice", "message_id": "m"},))
        self.assert_query_changed(lambda: self.store.validate_snapshot(original))
        self.assertEqual(self.snapshot().query_views["0"]["matches"][0]["source_id"], "new")
        self.assertFalse(self.snapshot().query_views["0"]["absence_eligible"])

    def test_private_pending_and_matching_rows_do_not_change_other_principal_query(self):
        before = self.store.query_snapshot("session", self.other, (), (self.query,))
        private = self.store.put_source("session", self.owner, "private", "PRIVATE_CANARY", readers={"alice"})
        after_pending = self.store.query_snapshot("session", self.other, (), (self.query,))
        self.index(
            private,
            (
                {
                    "record_id": "secret",
                    "kind": "receipt",
                    "agent_id": "alice",
                    "message_id": "m",
                    "payload": "PRIVATE_CANARY",
                },
            ),
        )
        after_index = self.store.query_snapshot("session", self.other, (), (self.query,))
        self.assertEqual(before.query_dependencies, after_pending.query_dependencies)
        self.assertEqual(before.query_dependencies, after_index.query_dependencies)
        self.assertNotIn("PRIVATE_CANARY", codec.dumps(after_index).decode())
        self.assertNotIn("private", codec.dumps(after_index).decode())
        with self.assertRaises(HCLFailure):
            self.store.query_snapshot("session", Principal("foreign", "bob"), (), (self.query,))

    def test_partial_compilation_never_establishes_negative_default(self):
        self.index(self.handle, (), complete=False)
        snapshot = self.snapshot()
        self.assertFalse(snapshot.query_views["0"]["absence_eligible"])
        self.assertEqual(snapshot.query_views["0"]["pending"][0][2], "PARTIAL_CANDIDATE_COVERAGE")

    def test_commit_inference_read_and_persistent_replay_all_validate_queries(self):
        snapshot = self.snapshot()
        ledger = TaskBudgetLedger(self.store)
        request = self.request()
        lease, _ = ledger.bind(request, snapshot)
        inference = InferenceResult(
            "answer", "test", {"conditional_absence": True}, (), (), (), RULE_VERSION, "INDEX_ONLY"
        )
        delta = QueryDelta(
            "session",
            self.owner,
            snapshot.revision,
            snapshot.access_epoch,
            RULE_VERSION,
            snapshot.source_versions,
            (inference,),
            snapshot.query_dependencies,
        )
        self.store.commit(snapshot.revision, snapshot.source_versions, snapshot.access_epoch, delta)
        ledger.finish(lease, snapshot, snapshot.source_versions, self.result())
        self.store.close()
        self.store = StateStore.sqlite(self.path)
        ledger = TaskBudgetLedger(self.store)
        self.assertEqual(ledger.resume(request).answer, self.result().answer)
        ledger.validate_cached_delivery(request)
        self.store.put_source("session", self.owner, "new", "Some new material.")
        for action in (
            lambda: self.store.commit(
                snapshot.revision,
                snapshot.source_versions,
                snapshot.access_epoch,
                replace(delta, new_inferences=()),
            ),
            lambda: self.store.inferences("session", self.owner),
            lambda: ledger.resume(request),
            lambda: ledger.validate_cached_delivery(request),
        ):
            self.assert_query_changed(action)

    def test_bind_reservation_transition_and_finish_fail_on_changed_query(self):
        snapshot = self.snapshot()
        ledger = TaskBudgetLedger(self.store)
        request = self.request()
        lease, _ = ledger.bind(request, snapshot)
        ledger.reserve(lease, snapshot, request.question, request.budget, "call", "serialized")
        self.store.put_source("session", self.owner, "new", "New pending record.")
        for action in (
            lambda: ledger.bind(replace(request, request_id="other"), snapshot),
            lambda: ledger.reserve(lease, snapshot, request.question, request.budget, "other", "serialized"),
            lambda: ledger.transition(lease, "call", "RESERVED", "SEND_STARTED", snapshot=snapshot),
            lambda: ledger.finish(lease, snapshot, snapshot.source_versions, self.result()),
        ):
            self.assert_query_changed(action)
        self.assertEqual(ledger.call(lease, "call")["state"], "RESERVED")

    def test_forged_snapshot_views_and_source_index_binding_rejected(self):
        snapshot = self.snapshot()
        with self.assertRaises(HCLFailure):
            self.store.validate_snapshot(replace(snapshot, query_views={"0": {"absence_eligible": True}}))
        values = source_index_values("foreign", 1, (), complete=True, program={})
        inference = InferenceResult(
            "fake", "revision.source_index", values, (), (), (), RULE_VERSION, "INDEX_ONLY"
        )
        delta = Delta(
            "session",
            self.owner,
            snapshot.revision,
            snapshot.access_epoch,
            RULE_VERSION,
            snapshot.source_versions,
            (inference,),
        )
        with self.assertRaises(HCLFailure):
            self.store.commit(snapshot.revision, snapshot.source_versions, snapshot.access_epoch, delta)

    def test_old_store_cannot_accept_query_envelope_without_explicit_cutover(self):
        other_path = Path(self.temporary.name) / "legacy.sqlite"
        old = StateStore.sqlite(other_path)
        try:
            old.create_session("session", self.owner)
            with self.assertRaises(HCLFailure) as caught:
                old.query_snapshot("session", self.owner, (), (self.query,))
            self.assertEqual(caught.exception.diagnostic.code, "REVISION_MIGRATION_REQUIRED")
            with self.assertRaises(ValueError):
                StateStore.sqlite(other_path, revision=True)
        finally:
            old.close()

    def test_projection_rebuild_preserves_query_tokens_and_task_dependencies(self):
        snapshot = self.snapshot()
        ledger = TaskBudgetLedger(self.store)
        lease, _ = ledger.bind(self.request(), snapshot)
        ledger.finish(lease, snapshot, snapshot.source_versions, self.result())
        before = [dict(row) for row in self.store._db.execute("SELECT * FROM events")]
        self.store.rebuild_projections()
        self.assertEqual(snapshot.query_dependencies, self.snapshot().query_dependencies)
        self.assertEqual([dict(row) for row in self.store._db.execute("SELECT * FROM events")], before)
        self.assertEqual(ledger.resume(self.request()).answer, self.result().answer)

    def test_fixed_cutoff_selects_version_before_time_and_survives_later_versions(self):
        cutoff = self.store.snapshot("session", self.owner, ()).revision
        query = IndexQuery({}, history=True, known_at=cutoff)
        historical = self.store.query_snapshot("session", self.owner, (), (query,))
        before = historical.query_views["0"]["source_history"][0]
        self.store.set_readers("session", self.owner, "origin", {"alice", "bob"})
        same = self.store.query_snapshot("session", self.owner, (), (query,))
        self.assertEqual(same.query_views["0"]["source_history"][0], before)
        self.handle = self.store.put_source("session", self.owner, "origin", "Corrected later version")
        current = self.store.query_snapshot("session", self.owner, (), (IndexQuery({}, history=True),))
        fixed = self.store.query_snapshot("session", self.owner, (), (query,))
        self.assertEqual(fixed.query_dependencies, historical.query_dependencies)
        self.assertEqual(current.query_views["0"]["source_history"][0]["source_version"], 2)
        self.assertEqual(current.query_views["0"]["pending"], (("origin", 2, "UNCOMPILED"),))
        self.assertFalse(current.query_views["0"]["absence_eligible"])
        self.assertEqual(fixed.query_views["0"]["source_history"][0]["source_version"], 1)

    def test_missing_old_ir_is_pending_and_can_be_compiled_from_exact_authorized_history(self):
        first = self.store.put_source("session", self.owner, "historical", "Original earlier source")
        cutoff = self.store.snapshot("session", self.owner, ()).revision
        self.store.put_source("session", self.owner, "historical", "Late correction")
        query = IndexQuery({}, ("historical",), True, cutoff)
        missing = self.store.query_snapshot("session", self.owner, (), (query,))
        self.assertEqual(missing.query_views["0"]["pending"], (("historical", 1, "UNCOMPILED"),))
        selected = self.store.historical_snapshot("session", self.owner, (first,), known_at=cutoff)
        self.assertEqual(selected.immutable_views["historical"].text, "Original earlier source")
        self.assertEqual(unpack_dependencies(self.store.snapshot_dependencies(selected))[0], {})
        values = source_index_values(
            "historical", 1, ({"record_id": "earlier", "kind": "receipt"},), complete=True, program={}
        )
        result = InferenceResult(
            "historical-index", "revision.source_index", values, (), (), (), RULE_VERSION, "CANDIDATE_ONLY"
        )
        delta = QueryDelta(
            "session",
            self.owner,
            selected.revision,
            selected.access_epoch,
            RULE_VERSION,
            {},
            (result,),
            selected.query_dependencies,
        )
        self.store.commit(selected.revision, {}, selected.access_epoch, delta)
        now = self.store.query_snapshot("session", self.owner, (), (query,))
        self.assertEqual(now.query_views["0"]["matches"][0]["record"]["record_id"], "earlier")
        self.assertFalse(now.query_views["0"]["pending"])
        self.assertGreater(now.query_views["0"]["matches"][0]["indexed_at"], cutoff)
        self.assertLessEqual(now.query_views["0"]["matches"][0]["recorded_at"], cutoff)
        ledger = TaskBudgetLedger(self.store)
        request = replace(self.request(), source_handles=(), request_id="historical-request")
        lease, _ = ledger.bind(request, now)
        ledger.finish(lease, now, {}, self.result())
        self.store.put_source("session", self.owner, "historical", "Even later correction")
        self.assertEqual(ledger.resume(request).answer, self.result().answer)
        ledger.validate_cached_delivery(request)
        self.store.set_readers("session", self.owner, "historical", {"bob"})
        with self.assertRaises(HCLFailure):
            ledger.resume(request)
        with self.assertRaises(HCLFailure):
            self.store.historical_snapshot("session", self.owner, (first,), known_at=cutoff)

    def test_same_version_different_historical_object_cannot_be_silently_selected(self):
        self.store._db.execute(
            "UPDATE events SET payload=replace(payload,'origin','forged') WHERE kind='sources'"
        )
        with self.assertRaises(HCLFailure):
            self.store.query_snapshot("session", self.owner, (), (IndexQuery({}, history=True),))
