"""Backfill on actual isolated ledgers; no user data or destructive operations."""
from dataclasses import replace
from pathlib import Path
import tempfile
import unittest

from hcl import HCL, ExecutionBudget, ExecutionIssue, RetrievalIssue, RetrievalQuery
from hcl.kernel.types import Principal, TaskRequest, TaskResult
from hcl.memory.store import StateStore
from hcl.memory.retention_inventory import inventory
from hcl.runtime.budget import TaskBudgetLedger, task_key


class RetentionInventoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = StateStore.sqlite(Path(self.tmp.name) / "state.sqlite", revision=True)
        self.addCleanup(self.store.close)
        self.owner = Principal("t", "a")
        self.store.create_session("s", self.owner)

    def inspect(self):
        events = [dict(row) for row in self.store._db.execute("SELECT * FROM events ORDER BY seq")]
        return inventory(events, self.store._get_object,
                         object_size=lambda key: (self.store.object_root / key).stat().st_size)

    def test_same_cas_does_not_merge_independent_session_lineage(self):
        self.store.create_session("other", self.owner)
        for session in ("s", "other"):
            self.store.put_source(session, self.owner, "shared", "IDENTICAL_SYNTHETIC_BYTES")
        result = self.inspect()
        refs = [row for row in result["references"] if row["slot"] == "object_hash"]
        self.assertEqual(len(refs), 2)
        self.assertEqual(refs[0]["object_hash"], refs[1]["object_hash"])
        self.assertEqual(refs[0]["bindings"], frozenset({("s", "shared", 1)}))
        self.assertEqual(refs[1]["bindings"], frozenset({("other", "shared", 1)}))
        self.assertEqual(sum(row["disposable"] for row in result["references"]), 2)

    def test_actual_hcl_unselected_corpus_and_source_versions_are_retained(self):
        self.store.put_source("s", self.owner, "unread", "weather temperature.")
        self.store.put_source("s", self.owner, "selected", "witness event.")
        query = RetrievalQuery(dict(support="witness", challenge="witness", alternative="event"), max_hits_per_route=1)
        request = TaskRequest("retrieve", "What evidence?", (), "s", self.owner,
            budget=ExecutionBudget(max_mock_calls=0, max_output_bytes=65536),
            issue=ExecutionIssue("root", goals=(RetrievalIssue("read", query=query),)))
        result = HCL(self.store, principal=self.owner).run_sync(request)
        self.assertEqual(result.status, "COMPLETED", result.diagnostics)
        self.assertEqual(set(result.claim_records[0].used_result_fields[0].value["coverage"]["read_regions"][0]),
                         {"segment_id", "source_id", "version", "start", "end", "byte_start", "byte_end"})
        self.assertEqual(result.claim_records[0].used_result_fields[0].value["coverage"]["read_regions"][0]["source_id"], "selected")
        self.store.put_source("s", self.owner, "unread", "Revised weather temperature.")
        graph = self.inspect()
        owner = ("task", "s", task_key(self.owner, "s", "retrieve"))
        self.assertEqual(graph["owner_bindings"][owner], frozenset({("s", "unread", 1), ("s", "selected", 1)}))
        self.assertIn("LEGACY_SCOPED_QUERY_SUPERSET", graph["owner_quality"][owner])
        self.assertIn(("source", "s", "unread", 2), graph["owner_bindings"])

    def test_final_dependency_narrowing_cannot_drop_original_call_lineage(self):
        a = self.store.put_source("s", self.owner, "A", "FAILED_BRANCH_CANARY")
        b = self.store.put_source("s", self.owner, "B", "Independent material.")
        before = self.store.snapshot("s", self.owner, (a,))
        after = self.store.snapshot("s", self.owner, (b,))
        request = TaskRequest("mixed", "Synthetic protocol fixture", (a,), "s", self.owner)
        request = replace(request, budget=replace(request.budget, max_mock_calls=1))
        ledger = TaskBudgetLedger(self.store)
        lease, _ = ledger.bind(request, before)
        ledger.reserve(lease, before, request.question, request.budget, "call", "FAILED_BRANCH_CANARY")
        ledger.transition(lease, "call", "RESERVED", "SEND_STARTED", snapshot=before)
        ledger.transition(lease, "call", "SEND_STARTED", "RETURNED", response="OLD_RESPONSE_CANARY")
        # This is a ledger retention protocol fixture, not a cognition witness.
        ledger.finish(lease, after, {"B": 1}, TaskResult("B-only delivery", (), "COMPLETED", (), {}, {}, None))
        graph = self.inspect()
        refs = [row for row in graph["references"] if row["owner"] == ("task", "s", lease.task_key)]
        self.assertTrue(any(row["slot"] == "response_hash" for row in refs))
        for row in refs:
            self.assertEqual(row["bindings"], frozenset({("s", "A", 1), ("s", "B", 1)}))

    def test_corrupt_chain_and_content_bound_fail_before_backfill(self):
        self.store.put_source("s", self.owner, "A", "Synthetic.")
        events = [dict(row) for row in self.store._db.execute("SELECT * FROM events ORDER BY seq")]
        changed = [dict(row) for row in events]
        changed[-1]["payload"] += " "
        with self.assertRaisesRegex(ValueError, "event chain"):
            inventory(changed, self.store._get_object)
        with self.assertRaisesRegex(ValueError, "content object bound"):
            inventory(events, self.store._get_object, object_size=lambda _: 4 * 1024 * 1024 + 1)


if __name__ == "__main__":
    unittest.main()
