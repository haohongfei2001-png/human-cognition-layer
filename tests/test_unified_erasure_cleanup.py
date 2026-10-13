"""Physical cleanup tests use newly created, disposable synthetic files only."""
from pathlib import Path
import json
import sqlite3
import subprocess
import sys
import unittest
from unittest.mock import patch

from hcl import HCL
from hcl.kernel.types import HCLFailure
from hcl.memory.governance import verify_inventory
from hcl.memory.retention_objects import pending
from tests import test_unified_erasure_fence as fixture

Crash = fixture.Crash


class ErasureCleanupTests(unittest.TestCase):
    def setUp(self):
        self.f = fixture.ErasureFenceTests("test_nonowner_cannot_change_or_observe_erasure")
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        self.store = self.f.store

    def resume(self, store=None):
        return (store or self.store).resume_source_erasure("session", self.f.owner, "a" * 32)

    def test_source_all_versions_history_caches_and_task_objects_removed(self):
        old = self.f.handle
        result = HCL(self.store, principal=self.f.owner).run_sync(self.f.request())
        self.assertEqual(result.status, "COMPLETED")
        current = self.store.put_source("session", self.f.owner, self.f.source_id, "SECOND_ERASURE_CANARY")
        plan = self.store.plan_source_erasure("session", self.f.owner, self.f.source_id, expected_version=2)
        self.store.begin_source_erasure("session", self.f.owner, self.f.source_id, expected_version=2,
                                       plan_hash=plan["plan_hash"], erasure_id="a" * 32)
        self.assertTrue(all((self.store.object_root / digest).exists() for digest in plan["objects_to_unlink"]))
        receipt = self.resume()
        self.assertEqual(receipt["status"], "LOCAL_REFERENCE_ERASURE_COMPLETE")
        self.assertTrue(receipt["database_scrubbed"])
        self.assertTrue(all(not (self.store.object_root / digest).exists() for digest in plan["objects_to_unlink"]))
        # Raw byte inspection must not itself close a descriptor for a live
        # SQLite inode and invalidate the locks this regression is protecting.
        self.store.close()
        for path in Path(self.f.tmp.name).rglob("*"):
            if path.is_file():
                body = path.read_bytes()
                self.assertNotIn(b"ERASED_ORIGINAL_CANARY", body, str(path))
                self.assertNotIn(b"SECOND_ERASURE_CANARY", body, str(path))
                self.assertNotIn(self.f.source_id.encode(), body, str(path))
        peer = self.f.open()
        self.assertEqual(self.resume(peer), receipt)
        peer.rebuild_projections()
        self.assertEqual(peer.source_erasure_receipt("session", self.f.owner, "a" * 32), receipt)
        for handle in (old, current):
            with self.assertRaises(HCLFailure):
                peer.snapshot("session", self.f.owner, (handle,))
        self.assertEqual(peer.snapshot("session", self.f.owner, (self.f.other,)).immutable_views["independent"].text,
                         "INDEPENDENT_ORIGINAL_CANARY")

    def test_each_cleanup_crash_restarts_without_content_resurrection(self):
        self.f.begin()
        for stage in ("erasure_object_unlinked", "erasure_objects_directory_synced", "erasure_files_cleaned",
                      "erasure_database_vacuumed", "erasure_database_scrubbed"):
            with self.subTest(stage=stage):
                def crash(at):
                    if at == stage:
                        raise Crash()
                with patch.object(self.store, "_checkpoint", side_effect=crash), self.assertRaises(Crash):
                    self.resume()
                peer = self.f.open()
                with peer._transaction() as db:
                    verify_inventory(db)
                with self.assertRaises(HCLFailure):
                    peer.snapshot("session", self.f.owner, (self.f.handle,))
        self.assertEqual(self.resume()["status"], "LOCAL_REFERENCE_ERASURE_COMPLETE")

    def test_unlink_failure_has_safe_diagnostic_and_is_resumable(self):
        self.f.begin()
        with patch.object(Path, "unlink", side_effect=OSError("PRIVATE_PATH_CANARY")):
            with self.assertRaises(HCLFailure) as error:
                self.resume()
        self.assertEqual(error.exception.diagnostic.code, "STORAGE_FAILURE")
        self.assertNotIn("PRIVATE_PATH", str(error.exception))
        self.assertEqual(self.resume()["status"], "LOCAL_REFERENCE_ERASURE_COMPLETE")

    def test_open_wal_reader_prevents_false_database_scrub_completion(self):
        reader = sqlite3.connect(self.f.path, isolation_level=None)
        self.addCleanup(reader.close)
        reader.execute("BEGIN")
        reader.execute("SELECT * FROM sources").fetchall()
        self.f.begin()
        self.store._db.execute("PRAGMA busy_timeout=1")
        result = self.resume()
        self.assertEqual(result["status"], "PARTIAL_ERASURE_RETAINED_COPIES")
        self.assertFalse(result["database_scrubbed"])
        self.assertIn("DATABASE_SCRUB_PENDING", result["limitations"])
        reader.rollback()
        self.assertEqual(self.resume()["status"], "LOCAL_REFERENCE_ERASURE_COMPLETE")

    def test_cleanup_never_opens_a_raw_database_descriptor(self):
        self.f.begin()
        original = Path.open

        def guarded(path, *args, **kwargs):
            self.assertNotEqual(path, self.store.path,
                                "raw database close would invalidate SQLite's locks")
            return original(path, *args, **kwargs)

        with patch.object(Path, "open", guarded):
            self.assertTrue(self.resume()["database_scrubbed"])

    def test_cleanup_restores_full_sync_before_vacuum_and_checkpoint(self):
        self.f.begin()
        self.store._db.execute("PRAGMA synchronous=OFF")
        statements = []
        self.store._db.set_trace_callback(statements.append)
        try:
            self.assertTrue(self.resume()["database_scrubbed"])
        finally:
            self.store._db.set_trace_callback(None)
        full = statements.index("PRAGMA synchronous=FULL")
        self.assertLess(full, statements.index("VACUUM"))
        self.assertLess(full, statements.index("PRAGMA wal_checkpoint(TRUNCATE)"))
        self.assertEqual(self.store._db.execute("PRAGMA synchronous").fetchone()[0], 2)

    def test_peer_close_preserves_live_wal_and_subsequent_commits(self):
        self.f.begin()
        receipt = self.resume()
        self.assertTrue(receipt["database_scrubbed"])
        program = r"""
import json, sqlite3, sys
db = sqlite3.connect(sys.argv[1])
receipt = json.loads(db.execute('SELECT receipt FROM erasures WHERE erasure_id=?',
                               ('a' * 32,)).fetchone()[0])
sources = sorted(row[0] for row in db.execute('SELECT source_id FROM sources'))
integrity = db.execute('PRAGMA integrity_check').fetchone()[0]
db.close()
print(json.dumps(dict(receipt=receipt, sources=sources, integrity=integrity)))
"""

        def peer():
            return json.loads(subprocess.check_output(
                [sys.executable, "-B", "-c", program, str(self.f.path)],
                text=True, timeout=15,
            ))

        self.assertEqual(peer()["receipt"], receipt)
        self.assertTrue(self.f.path.with_name(self.f.path.name + "-wal").exists(),
                        "a peer must not unlink a live connection's WAL")
        self.store.put_source("session", self.f.owner, "after-cleanup", "SYNTHETIC_AFTER_CLEANUP")
        observed = peer()
        self.assertEqual(observed["receipt"], receipt)
        self.assertEqual(observed["sources"], ["after-cleanup", "independent"])
        self.assertEqual(observed["integrity"], "ok")

    def test_shared_cas_acquired_after_intent_preserves_independent_owner(self):
        self.f.begin()
        self.store.create_session("independent-session", self.f.owner)
        handle = self.store.put_source("independent-session", self.f.owner, self.f.source_id, "ERASED_ORIGINAL_CANARY")
        result = self.resume()
        self.assertEqual(result["newly_shared_objects_retained"], 2)
        self.assertEqual(result["status"], "LOCAL_REFERENCE_ERASURE_COMPLETE")
        self.assertEqual(self.store.snapshot("independent-session", self.f.owner, (handle,)).immutable_views[handle.source_id].text,
                         "ERASED_ORIGINAL_CANARY")
        with self.assertRaises(HCLFailure):
            self.store.snapshot("session", self.f.owner, (self.f.handle,))

    def test_unknown_orphan_is_preserved_and_blocks_complete_claim(self):
        unknown = self.store.object_root / ("f" * 64)
        unknown.write_text("UNATTRIBUTED_SYNTHETIC_CANARY")
        self.f.begin()
        result = self.resume()
        self.assertEqual(result["status"], "PARTIAL_ERASURE_RETAINED_COPIES")
        self.assertIn("UNATTRIBUTED_OBJECTS_RETAINED", result["limitations"])
        self.assertEqual(result["unknown_owned_objects"], 1)
        self.assertEqual(unknown.read_text(), "UNATTRIBUTED_SYNTHETIC_CANARY")

    def test_journalled_precommit_orphan_and_pending_fragment_are_removed(self):
        def crash(at):
            if at == "object_persisted":
                raise Crash()
        with patch.object(self.store, "_checkpoint", side_effect=crash), self.assertRaises(Crash):
            self.store.put_source("session", self.f.owner, self.f.source_id, "ORPHAN_SYNTHETIC_CANARY")
        journals = pending(self.store)
        self.assertEqual(len(journals), 1)
        fragment = self.store.object_root / (journals[0]["temporary_prefix"] + "crash")
        fragment.write_text("ORPHAN_SYNTHETIC_CANARY")
        self.f.begin()
        self.assertEqual(self.resume()["status"], "LOCAL_REFERENCE_ERASURE_COMPLETE")
        self.assertFalse(fragment.exists())
        self.assertFalse((self.store.object_root / journals[0]["object_hash"]).exists())
        self.assertFalse(pending(self.store))


if __name__ == "__main__":
    unittest.main()
