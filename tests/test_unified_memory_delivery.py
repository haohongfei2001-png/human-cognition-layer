"""Real SQLite read-boundary races; synthetic typed values are not solver proof."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from hcl.kernel.dependencies import IndexQuery
from hcl.kernel.retrieval import RetrievalQuery
from hcl.kernel.types import Delta, HCLFailure, InferenceResult, Principal, RULE_VERSION, TaskRequest
from hcl.memory.store import StateStore
from hcl.runtime.execution_ledger import ExecutionLedger


class MemoryDeliveryTests(unittest.TestCase):
    def fixture(self, result_source="A"):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        path = Path(temporary.name) / "state.sqlite"
        store = StateStore.sqlite(path, revision=True)
        self.addCleanup(store.close)
        owner = Principal("t", "owner")
        store.create_session("s", owner, frozenset({"other"}))
        handles = {key: store.put_source("s", owner, key, key + "_RAW_CANARY") for key in ("A", "B")}
        snapshot = store.snapshot("s", owner, (handles[result_source],))
        result = InferenceResult("result", "delivery-fixture", {"text": result_source + "_INFERENCE_CANARY"},
                                 (), (), (), RULE_VERSION, "INDEX_ONLY")
        delta = Delta("s", owner, snapshot.revision, snapshot.access_epoch, RULE_VERSION,
                      snapshot.source_versions, (result,))
        store.commit(snapshot.revision, snapshot.source_versions, snapshot.access_epoch, delta)
        peer = StateStore.sqlite(path)
        self.addCleanup(peer.close)
        return store, peer, owner, handles, result

    @staticmethod
    def read(store, owner, handle, kind):
        if kind == "snapshot":
            return store.snapshot("s", owner, (handle,))
        if kind == "historical_snapshot":
            return store.historical_snapshot("s", owner, (handle,), known_at=2)
        if kind == "query_snapshot":
            return store.query_snapshot("s", owner, (handle,), (IndexQuery({}, source_scope=(handle.source_id,)),))
        if kind == "revision_snapshot":
            return store.revision_snapshot("s", owner, (handle,), known_at=2)
        if kind == "search_snapshot":
            return store.search_snapshot("s", owner, RetrievalQuery(dict(support="CANARY", challenge="CANARY", alternative="CANARY"),
                                                                    source_scope=(handle.source_id,)))
        if kind == "inferences":
            return store.inferences("s", owner)
        if kind == "delivery_inferences":
            return ExecutionLedger(store).delivery_inferences(TaskRequest("read", "Read", (handle,), "s", owner), ("result",))
        raise AssertionError(kind)

    def test_all_content_read_exits_recheck_erasure_and_acl_after_old_wal(self):
        for kind in ("snapshot", "historical_snapshot", "query_snapshot", "revision_snapshot", "search_snapshot",
                     "inferences", "delivery_inferences"):
            for action in ("erase", "revoke"):
                with self.subTest(kind=kind, action=action):
                    store, peer, owner, handles, _ = self.fixture()
                    original, fired = store._get_object, False
                    def race(digest):
                        nonlocal fired
                        value = original(digest)
                        eligible = (type(value) is InferenceResult if "inferences" in kind else
                                    type(value) is dict and value.get("text") == "A_RAW_CANARY")
                        if eligible and not fired:
                            fired = True
                            if action == "erase":
                                plan = peer.plan_source_erasure("s", owner, "A", expected_version=1)
                                peer.begin_source_erasure("s", owner, "A", expected_version=1,
                                    plan_hash=plan["plan_hash"], erasure_id="1" * 32)
                            else:
                                peer.set_readers("s", owner, "A", {"other"})
                        return value
                    with patch.object(store, "_get_object", side_effect=race), self.assertRaises(HCLFailure) as error:
                        self.read(store, owner, handles["A"], kind)
                    self.assertTrue(fired)
                    self.assertIn(error.exception.status, ("DENIED", "STALE_STATE"))
                    self.assertNotIn("CANARY", error.exception.diagnostic.message)

    def test_independent_inference_and_original_remain_readable_during_erasure(self):
        for kind in ("snapshot", "historical_snapshot", "query_snapshot", "search_snapshot", "inferences", "delivery_inferences"):
            with self.subTest(kind=kind):
                store, peer, owner, handles, expected = self.fixture("B")
                original, fired = store._get_object, False
                def race(digest):
                    nonlocal fired
                    value = original(digest)
                    eligible = (type(value) is InferenceResult if "inferences" in kind else
                                type(value) is dict and value.get("text") == "B_RAW_CANARY")
                    if eligible and not fired:
                        fired = True
                        plan = peer.plan_source_erasure("s", owner, "A", expected_version=1)
                        peer.begin_source_erasure("s", owner, "A", expected_version=1,
                            plan_hash=plan["plan_hash"], erasure_id="2" * 32)
                    return value
                with patch.object(store, "_get_object", side_effect=race):
                    result = self.read(store, owner, handles["B"], kind)
                self.assertTrue(fired)
                if "inferences" in kind:
                    self.assertEqual(result, (expected,))
                else:
                    self.assertEqual(result.immutable_views["B"].text, "B_RAW_CANARY")


if __name__ == "__main__":
    unittest.main()
