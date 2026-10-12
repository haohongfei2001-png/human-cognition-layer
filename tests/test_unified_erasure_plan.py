"""Real read-only owner planning on disposable synthetic governed namespaces."""
from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from hcl.kernel.types import Principal, TaskRequest, HCLFailure
from hcl.memory.store import StateStore
from hcl.runtime.budget import TaskBudgetLedger


class ErasurePlanTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "state.sqlite"
        self.store = StateStore.sqlite(self.path, revision=True)
        self.addCleanup(self.store.close)
        self.owner = Principal("t", "a")
        self.store.create_session("s", self.owner, frozenset({"b"}))
        self.source = "PRIVATE_SOURCE_NAME_CANARY"
        self.handle = self.store.put_source("s", self.owner, self.source, "PRIVATE_TEXT_CANARY")

    def plan(self, **kwargs):
        return self.store.plan_source_erasure("s", kwargs.get("principal", self.owner), self.source,
                                             expected_version=kwargs.get("version", 1))

    def test_plan_is_content_free_read_only_and_restart_stable(self):
        before = self.store._db.total_changes
        with patch.object(self.store, "_get_object", side_effect=AssertionError("planning must not read private objects")):
            plan = self.plan()
        self.assertEqual(self.store._db.total_changes, before)
        self.assertEqual(plan["readiness"], "PLAN_ONLY_NO_ERASURE_PERFORMED")
        self.assertNotIn("PRIVATE_", json.dumps(plan))
        self.assertEqual(len(plan["objects_to_unlink"]), 2)
        peer = StateStore.sqlite(self.path)
        try:
            self.assertEqual(peer.plan_source_erasure("s", self.owner, self.source, expected_version=1), plan)
        finally:
            peer.close()
        self.assertEqual(self.store.snapshot("s", self.owner, (self.handle,)).immutable_views[self.source].text,
                         "PRIVATE_TEXT_CANARY")

    def test_current_owner_and_version_are_required_before_inventory(self):
        with patch("hcl.memory.governance.verify_inventory", side_effect=AssertionError("unauthorized inventory")):
            for principal in (Principal("t", "b"), Principal("foreign", "a")):
                with self.assertRaises(HCLFailure) as error:
                    self.plan(principal=principal)
                self.assertEqual(error.exception.status, "DENIED")
            with self.assertRaises(HCLFailure) as error:
                self.plan(version=2)
            self.assertEqual(error.exception.diagnostic.code, "ERASURE_SOURCE_VERSION_CHANGED")

    def test_same_cas_independent_reference_is_not_scheduled_for_unlink(self):
        self.store.create_session("other", self.owner)
        self.store.put_source("other", self.owner, self.source, "PRIVATE_TEXT_CANARY")
        plan = self.plan()
        self.assertEqual(plan["objects_to_unlink"], [])
        self.assertEqual(plan["shared_objects_retained"], 2)

    def test_unknown_transport_hold_is_visible_and_never_changed_by_planning(self):
        request = TaskRequest("call", "Synthetic question", (self.handle,), "s", self.owner)
        request = replace(request, budget=replace(request.budget, max_mock_calls=1))
        snapshot = self.store.snapshot("s", self.owner, (self.handle,))
        ledger = TaskBudgetLedger(self.store)
        lease, _ = ledger.bind(request, snapshot)
        ledger.reserve(lease, snapshot, request.question, request.budget, "response", "SYNTHETIC_WIRE")
        ledger.transition(lease, "response", "RESERVED", "SEND_STARTED", snapshot=snapshot)
        before = dict(self.store._db.execute("SELECT * FROM calls").fetchone())
        plan = self.plan()
        self.assertEqual(plan["accounting_to_preserve"], dict(held_calls=1, unknown_calls=1, observed_calls=0))
        self.assertEqual(dict(self.store._db.execute("SELECT * FROM calls").fetchone()), before)

    def test_record_or_reference_tampering_fails_closed(self):
        with self.store._transaction(True) as db:
            db.execute("UPDATE retention_refs SET object_hash=?", ("0" * 64,))
        with self.assertRaises(HCLFailure) as error:
            self.plan()
        self.assertEqual(error.exception.diagnostic.code, "STATE_CORRUPT")


if __name__ == "__main__":
    unittest.main()
