"""Real WAL side-copy, terminal writer fencing, crash recovery and old ledger."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path
import json
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from hcl.kernel.dependencies import IndexQuery
from hcl.kernel.types import BudgetSlice, HCLFailure, Principal, TaskRequest, TaskResult
from hcl.memory import codec
from hcl.memory.migrations.legacy import LegacySnapshot, LegacySource
from hcl.memory.migrations.namespace import MigrationNamespace
from hcl.memory.migrations.revision_upgrade import RevisionCutover
from hcl.memory.store import StateStore
from hcl.runtime.budget import TaskBudgetLedger


class Crash(BaseException):
    pass


class RevisionUpgradeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.owner = Principal("tenant", "alice")
        self.source = self.root / "old.sqlite"
        self.old = StateStore.sqlite(self.source)
        self.old.create_session("session", self.owner, {"bob"})
        self.handle = self.old.put_source("session", self.owner, "source", "ORIGINAL_SOURCE_CANARY")
        self.request = TaskRequest("completed", "report", (self.handle,), "session", self.owner)
        snapshot = self.old.snapshot("session", self.owner, (self.handle,))
        ledger = TaskBudgetLedger(self.old)
        lease, _ = ledger.bind(self.request, snapshot)
        self.result = TaskResult("old answer", (), "COMPLETED", (), {}, {"mock_calls": 0}, snapshot.revision)
        ledger.finish(lease, snapshot, snapshot.source_versions, self.result)
        self.unknown = replace(self.request, request_id="unknown", budget=BudgetSlice(max_mock_calls=1))
        lease, _ = ledger.bind(self.unknown, snapshot)
        ledger.reserve(
            lease, snapshot, self.unknown.question, self.unknown.budget, "response", "old serialized request"
        )
        ledger.transition(lease, "response", "RESERVED", "SEND_STARTED", snapshot=snapshot)
        self.old_owner = self.old.owner_id
        self.original = {
            table: [dict(row) for row in self.old._db.execute(f"SELECT * FROM {table}")]
            for table in ("sessions", "sources", "inferences", "tasks", "calls", "events")
        }

    def tearDown(self):
        self.old.close()
        self.tmp.cleanup()

    def upgrade(self):
        return RevisionCutover.upgrade(self.source, self.root / "new", self.owner)

    def assert_old_fenced(self):
        with self.assertRaises(HCLFailure):
            self.old.snapshot("session", self.owner, (self.handle,))
        with self.assertRaises(ValueError):
            StateStore.sqlite(self.source)
        self.assertEqual(self.old._db.execute("PRAGMA user_version").fetchone()[0], 91)

    def test_exact_rows_objects_and_unknown_hold_survive_reopen_and_recovery(self):
        target = self.upgrade()
        self.assert_old_fenced()
        with self.assertRaises(HCLFailure):
            self.old.put_source("session", self.owner, "late", "cannot write")
        current = target.open_store()
        try:
            self.assertEqual(current._schema, 3)
            for table, rows in self.original.items():
                self.assertEqual([dict(row) for row in current._db.execute(f"SELECT * FROM {table}")], rows)
                self.assertEqual([dict(row) for row in self.old._db.execute(f"SELECT * FROM {table}")], rows)
            ledger = TaskBudgetLedger(current)
            self.assertEqual(ledger.resume(self.request).answer, "old answer")
            ledger.validate_cached_delivery(self.request)
            with self.assertRaises(HCLFailure) as caught:
                ledger.resume(self.unknown)
            self.assertIsNone(caught.exception.resource_usage["mock_calls"])
            self.assertEqual(caught.exception.resource_usage["held_mock_calls"], 1)
            self.assertEqual(ledger.recover_abandoned(self.owner, "session", "unknown", self.old_owner), 1)
            with self.assertRaises(HCLFailure) as caught:
                ledger.resume(self.unknown)
            self.assertEqual(caught.exception.diagnostic.code, "TASK_INTERRUPTED_NO_RESEND")
            self.assertIsNone(caught.exception.resource_usage["mock_calls"])
            self.assertEqual(
                current.query_snapshot("session", self.owner, (), (IndexQuery({}),)).query_views["0"][
                    "pending"
                ],
                (("source", 1, "UNCOMPILED"),),
            )
            self.assertEqual(target.audit(self.owner)["calls"][0]["state"], "UNKNOWN")
            self.assertEqual(self.upgrade().path, target.path)  # preserves later recovery events
        finally:
            current.close()

    def test_prepared_crash_leaves_only_old_writer_and_rebuilds_changed_prefix(self):
        def fault(stage):
            if stage == "prepared":
                raise Crash()

        with patch.object(RevisionCutover, "_checkpoint", side_effect=fault), self.assertRaises(Crash):
            self.upgrade()
        self.assertFalse((self.root / "new").exists())
        self.assertEqual(self.old._schema, 1)
        self.old.put_source("session", self.owner, "later", "committed before fence")
        target = self.upgrade()
        self.assert_old_fenced()
        current = target.open_store()
        try:
            self.assertEqual(current.current_handles("session", self.owner, ("later",))[0].version, 1)
        finally:
            current.close()

    def test_every_post_fence_crash_recovers_identical_target_without_releasing_hold(self):
        # Independent stores per seam avoid treating an already published copy
        # as a simulation of an earlier interrupted phase.
        for stage in ("source_fenced", "target_activated_unpublished", "published"):
            with self.subTest(stage=stage), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "old.sqlite"
                old = StateStore.sqlite(path)
                old.create_session("s", self.owner)
                handle = old.put_source("s", self.owner, "x", "x")
                request = TaskRequest(
                    "r", "q", (handle,), "s", self.owner, budget=BudgetSlice(max_mock_calls=1)
                )
                snapshot = old.snapshot("s", self.owner, (handle,))
                ledger = TaskBudgetLedger(old)
                lease, _ = ledger.bind(request, snapshot)
                ledger.reserve(lease, snapshot, "q", request.budget, "call", "wire")
                ledger.transition(lease, "call", "RESERVED", "SEND_STARTED", snapshot=snapshot)

                def fault(value):
                    if value == stage:
                        raise Crash()

                try:
                    with patch.object(RevisionCutover, "_checkpoint", side_effect=fault), self.assertRaises(
                        Crash
                    ):
                        RevisionCutover.upgrade(path, Path(directory) / "new", self.owner)
                    with self.assertRaises(HCLFailure):
                        old.snapshot("s", self.owner, (handle,))
                    target = RevisionCutover.upgrade(path, Path(directory) / "new", self.owner)
                    again = RevisionCutover.upgrade(path, Path(directory) / "new", self.owner)
                    self.assertEqual(target.audit(self.owner), again.audit(self.owner))
                    self.assertEqual(target.audit(self.owner)["calls"][0]["state"], "SEND_STARTED")
                    self.assertIsNone(target.audit(self.owner)["calls"][0]["attempted"])
                finally:
                    old.close()

    def test_different_destination_cannot_clone_a_second_live_owner(self):
        target = self.upgrade()
        with self.assertRaises(ValueError):
            RevisionCutover.upgrade(self.source, self.root / "second", self.owner)
        self.assertFalse((self.root / "second").exists())
        self.assertEqual(target.audit(self.owner)["calls"][0]["state"], "SEND_STARTED")

    def test_concurrent_same_destination_is_idempotent_and_distinct_destinations_conflict(self):
        with ThreadPoolExecutor(max_workers=2) as pool:
            targets = list(pool.map(lambda _: self.upgrade(), range(2)))
        self.assertEqual(targets[0].path, targets[1].path)
        self.assertEqual(targets[0].audit(self.owner), targets[1].audit(self.owner))
        self.assert_old_fenced()

    def test_rollback_is_terminal_and_readonly_uses_current_acl_not_old_acl(self):
        target = self.upgrade()
        current = target.open_store()
        try:
            self.assertIn(
                "ORIGINAL_SOURCE_CANARY",
                (
                    codec.canonical(codec.thaw(target.legacy_view(self.owner)))
                    if hasattr(codec, "thaw")
                    else str(target.legacy_view(self.owner))
                ),
            )
            current.set_readers("session", self.owner, "source", {"bob"})
            with self.assertRaises(HCLFailure):
                target.legacy_view(self.owner)
            target.rollback(self.owner)
            with self.assertRaises(HCLFailure):
                current.snapshot("session", self.owner, (self.handle,))
            with self.assertRaises(HCLFailure):
                target.legacy_view(self.owner)
            with self.assertRaises(ValueError):
                target.rollback(self.owner)
            self.assertEqual(target.audit(self.owner)["calls"][0]["state"], "SEND_STARTED")
            self.assert_old_fenced()
        finally:
            current.close()

    def test_missing_control_or_unknown_bundle_cannot_be_repaired_or_downgraded(self):
        target = self.upgrade()
        db = sqlite3.connect(target.path)
        db.execute("DROP TABLE revision_control")
        db.commit()
        db.close()
        with self.assertRaises((ValueError, sqlite3.Error, HCLFailure)):
            target.open_store()
        self.assert_old_fenced()

    def test_tampered_projection_and_object_fail_before_source_fence(self):
        self.old._db.execute("UPDATE calls SET attempted=0 WHERE state='SEND_STARTED'")
        with self.assertRaises(HCLFailure):
            self.upgrade()
        self.assertEqual(self.old._db.execute("PRAGMA user_version").fetchone()[0], 1)
        self.assertFalse((self.root / "new").exists())

    def test_unauthorized_owner_cannot_copy_or_fence_store(self):
        for principal in (Principal("foreign", "alice"), Principal("tenant", "bob")):
            with self.subTest(principal=principal), self.assertRaises(HCLFailure):
                RevisionCutover.upgrade(self.source, self.root / "new", principal)
        self.assertFalse((self.root / ".new.cutover.json").exists())
        self.assertEqual(self.old._db.execute("PRAGMA user_version").fetchone()[0], 1)

    def test_controlled_namespace_package_and_quarantine_acl_survive_upgrade(self):
        old = MigrationNamespace.import_snapshot(
            self.root / "imported",
            LegacySnapshot((LegacySource("s", 1, "old"), LegacySource("s", 2, "ambiguous"))),
            namespace_id="namespace",
            owner=self.owner,
            readers={"s": ("bob",)},
        )
        target = RevisionCutover.upgrade(old.path, self.root / "controlled-new", self.owner)
        current = target.open_store()
        try:
            self.assertEqual(current._schema, 4)
            self.assertIsNotNone(current._namespace_generation)
            with self.assertRaises(HCLFailure):
                target.legacy_view(self.owner)
            with self.assertRaises(HCLFailure):
                old.legacy_view(self.owner)
            target.rollback(self.owner)
            with self.assertRaises(HCLFailure):
                target.legacy_view(self.owner)
            self.assertEqual(target.audit(self.owner)["mode"], "READ_ONLY")
        finally:
            current.close()

    def test_two_concurrent_destinations_cannot_publish_two_writers(self):
        from threading import Barrier

        barrier = Barrier(2)

        def attempt(name):
            barrier.wait(timeout=5)
            try:
                return RevisionCutover.upgrade(self.source, self.root / name, self.owner)
            except ValueError:
                return None

        with ThreadPoolExecutor(max_workers=2) as pool:
            targets = list(pool.map(attempt, ("new-a", "new-b")))
        self.assertEqual(sum(target is not None for target in targets), 1)
        self.assertEqual(sum((self.root / name).exists() for name in ("new-a", "new-b")), 1)
        self.assert_old_fenced()

    def test_corrupt_original_object_cannot_be_copied_as_certified_history(self):
        digest = self.old._db.execute("SELECT object_hash FROM sources").fetchone()[0]
        root = self.source.with_name(self.source.name + ".objects")
        (root / digest).write_bytes(b"CORRUPTED_SOURCE_OBJECT")
        with self.assertRaises(HCLFailure) as caught:
            self.upgrade()
        self.assertEqual(caught.exception.diagnostic.code, "STATE_CORRUPT")
        self.assertEqual(self.old._db.execute("PRAGMA user_version").fetchone()[0], 1)
        self.assertFalse((self.root / "new").exists())

    def test_fsync_and_publication_failure_are_safe_and_recoverable(self):
        with patch(
            "hcl.memory.migrations.revision_upgrade.os.fsync", side_effect=OSError("PRIVATE_DISK_PATH")
        ), self.assertRaises(HCLFailure) as caught:
            self.upgrade()
        self.assertEqual(caught.exception.diagnostic.code, "STORAGE_FAILURE")
        self.assertNotIn("PRIVATE_DISK_PATH", str(caught.exception))
        self.assertEqual(self.old._db.execute("PRAGMA user_version").fetchone()[0], 1)
        import os

        original_rename = os.rename

        def publication_failure(source, destination):
            if Path(destination) == self.root / "new":
                raise OSError("PRIVATE_RENAME_PATH")
            return original_rename(source, destination)

        with patch(
            "hcl.memory.migrations.revision_upgrade.os.rename", side_effect=publication_failure
        ), self.assertRaises(HCLFailure) as caught:
            self.upgrade()
        self.assertEqual(caught.exception.diagnostic.code, "STORAGE_FAILURE")
        self.assertNotIn("PRIVATE_RENAME_PATH", str(caught.exception))
        self.assert_old_fenced()
        target = self.upgrade()
        self.assertEqual(target.audit(self.owner)["calls"][0]["state"], "SEND_STARTED")

    def test_readonly_legacy_view_rechecks_outside_old_wal_snapshot(self):
        target = self.upgrade()
        current = target.open_store()
        original = target._read_authorization
        calls = 0

        def checked(db, principal):
            nonlocal calls
            original(db, principal)
            calls += 1
            if calls == 1:
                current.set_readers("session", self.owner, "source", {"bob"})

        try:
            with patch.object(target, "_read_authorization", side_effect=checked), self.assertRaises(
                HCLFailure
            ) as caught:
                target.legacy_view(self.owner)
            self.assertEqual(caught.exception.status, "DENIED")
            self.assertEqual(calls, 1)  # fresh second check rejects before increment
            self.assertNotIn("ORIGINAL_SOURCE_CANARY", str(caught.exception))
        finally:
            current.close()

    def test_activated_unpublished_database_is_not_an_executable_namespace(self):
        def fault(stage):
            if stage == "target_activated_unpublished":
                raise Crash()

        with patch.object(RevisionCutover, "_checkpoint", side_effect=fault), self.assertRaises(Crash):
            self.upgrade()
        with self.assertRaises((ValueError, HCLFailure)):
            StateStore.sqlite(self.root / ".new.unpublished" / "state.sqlite")
        target = self.upgrade()
        current = target.open_store()
        try:
            self.assertEqual(current.current_handles("session", self.owner, ("source",)), (self.handle,))
        finally:
            current.close()

    def test_post_fence_same_target_recovery_is_serialized_through_publication(self):
        from threading import Barrier, Lock
        import time

        self.upgrade()
        start = Barrier(2)
        lock = Lock()
        concurrent = maximum = 0

        def phase(stage):
            nonlocal concurrent, maximum
            if stage == "source_fenced":
                with lock:
                    concurrent += 1
                    maximum = max(maximum, concurrent)
                time.sleep(0.1)
                with lock:
                    concurrent -= 1

        def recover(_):
            start.wait(timeout=5)
            return self.upgrade()

        with patch.object(RevisionCutover, "_checkpoint", side_effect=phase), ThreadPoolExecutor(
            max_workers=2
        ) as pool:
            results = list(pool.map(recover, range(2)))
        self.assertEqual(maximum, 1)
        self.assertEqual(results[0].audit(self.owner), results[1].audit(self.owner))

    def test_early_stage_marker_fsync_failure_does_not_strand_recovery(self):
        import os

        original = os.fsync
        count = 0

        def fault(descriptor):
            nonlocal count
            count += 1
            if count == 3:
                raise OSError("STAGE_MARKER_IO_FAILURE")
            return original(descriptor)

        with patch("hcl.memory.migrations.revision_upgrade.os.fsync", side_effect=fault), self.assertRaises(
            HCLFailure
        ):
            self.upgrade()
        self.assertEqual(self.old._db.execute("PRAGMA user_version").fetchone()[0], 1)
        self.old.put_source("session", self.owner, "still-writer", "old store remains sole writer")
        target = self.upgrade()
        current = target.open_store()
        try:
            self.assertEqual(current.current_handles("session", self.owner, ("still-writer",))[0].version, 1)
        finally:
            current.close()
