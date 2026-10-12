"""Attributable interrupted writes in disposable synthetic governed stores."""
from hashlib import sha256
import json
from pathlib import Path
import os
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from hcl.kernel.types import Principal, HCLFailure
from hcl.memory import codec
from hcl.memory.store import StateStore
from hcl.memory.retention_objects import pending


class Crash(BaseException):
    pass


class RetainedObjectTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "state.sqlite"
        self.store = StateStore.sqlite(self.path, revision=True)
        self.addCleanup(self.store.close)
        self.owner = Principal("t", "a")
        self.store.create_session("s", self.owner)
        self.a = self.store.put_source("s", self.owner, "A", "SOURCE_A_CANARY")
        self.b = self.store.put_source("s", self.owner, "B", "Independent original.")

    def orphan(self, handle, text):
        snapshot = self.store.snapshot("s", self.owner, (handle,))
        with self.assertRaises(Crash):
            with self.store._transaction(True):
                self.store._put_content(text, session_id="s", context=snapshot)
                raise Crash()
        return sha256(codec.dumps(text)).hexdigest()

    def test_committed_sources_leave_no_staging_metadata(self):
        self.assertEqual(pending(self.store), ())

    def test_cross_session_context_is_rejected_before_any_payload_write(self):
        self.store.create_session("other", self.owner)
        source = self.store.put_source("other", self.owner, "other-source", "Foreign session original")
        foreign = self.store.snapshot("other", self.owner, (source,))
        before = {path.name for path in self.store.object_root.iterdir()}
        with self.assertRaises(HCLFailure) as error:
            with self.store._transaction(True):
                self.store._put_content("CROSS_SESSION_PRIVATE_CANARY", session_id="s", context=foreign)
        self.assertEqual(error.exception.diagnostic.code, "RETENTION_SESSION_MISMATCH")
        self.assertEqual({path.name for path in self.store.object_root.iterdir()}, before)
        self.assertFalse(pending(self.store))

    def test_before_event_crash_retains_private_object_attribution(self):
        digest = self.orphan(self.a, "UNCOMMITTED_PRIVATE_CANARY")
        self.assertTrue((self.store.object_root / digest).is_file())
        rows = pending(self.store)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["object_hash"], digest)
        self.assertNotIn("PRIVATE_CANARY", rows[0]["path"].read_text())
        plan = self.store.plan_source_erasure("s", self.owner, "A", expected_version=1)
        self.assertIn(digest, plan["objects_to_unlink"])
        self.assertEqual(plan["staged_objects"][0]["nonce"], rows[0]["nonce"])
        self.assertTrue((self.store.object_root / digest).is_file())  # plan is read-only

    def test_same_cas_independent_staged_reference_survives_the_plan(self):
        digest = self.orphan(self.a, "SHARED_PENDING_BYTES")
        self.assertEqual(self.orphan(self.b, "SHARED_PENDING_BYTES"), digest)
        plan = self.store.plan_source_erasure("s", self.owner, "A", expected_version=1)
        self.assertNotIn(digest, plan["objects_to_unlink"])
        self.assertEqual(plan["shared_objects_retained"], 1)

    def test_corrupt_journal_never_becomes_erasable_scope(self):
        self.orphan(self.a, "SYNTHETIC_PENDING")
        row = pending(self.store)[0]
        value = json.loads(row["path"].read_text())
        value["object_hash"] = "0" * 64
        row["path"].write_text(json.dumps(value))
        with self.assertRaises(HCLFailure) as error:
            self.store.plan_source_erasure("s", self.owner, "A", expected_version=1)
        self.assertEqual(error.exception.diagnostic.code, "STATE_CORRUPT")

    def test_real_process_exit_preserves_attributable_orphan(self):
        program = r'''
import os,sys
from hcl.memory.store import StateStore
from hcl.kernel.types import Principal
store=StateStore.sqlite(sys.argv[1])
def die(stage):
 if stage=='object_persisted':os._exit(71)
store._checkpoint=die
store.put_source('s',Principal('t','a'),'A','PROCESS_CRASH_PRIVATE_CANARY')
'''
        result = subprocess.run([sys.executable, "-c", program, str(self.path)],
                                cwd=Path(__file__).resolve().parents[1],
                                env={"PATH": os.defpath, "PYTHONPATH": str(Path(__file__).resolve().parents[1]),
                                     "PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1"},
                                capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 71, result.stderr.decode())
        self.assertEqual(len(pending(self.store)), 1)
        plan = self.store.plan_source_erasure("s", self.owner, "A", expected_version=1)
        self.store.begin_source_erasure("s", self.owner, "A", expected_version=1,
                                       plan_hash=plan["plan_hash"], erasure_id="d" * 32)
        self.assertEqual(self.store.resume_source_erasure("s", self.owner, "d" * 32)["status"],
                         "LOCAL_REFERENCE_ERASURE_COMPLETE")
        for path in Path(self.tmp.name).rglob("*"):
            if path.is_file():
                self.assertNotIn(b"PROCESS_CRASH_PRIVATE_CANARY", path.read_bytes())

    def test_every_precommit_fsync_failure_retains_safe_recoverable_lineage(self):
        original = os.fsync
        for position in range(1, 9):
            fixture = RetainedObjectTests("test_committed_sources_leave_no_staging_metadata")
            fixture.setUp()
            self.addCleanup(fixture.doCleanups)
            calls = 0
            def fail(fd):
                nonlocal calls
                calls += 1
                if calls == position:
                    raise OSError("PRIVATE_FSYNC_PATH_CANARY")
                return original(fd)
            with self.subTest(position=position):
                with patch("hcl.memory.retention_objects.os.fsync", side_effect=fail), self.assertRaises(HCLFailure) as error:
                    fixture.store.put_source("s", fixture.owner, "A", "FSYNC_PRIVATE_CANARY")
                self.assertEqual(error.exception.diagnostic.code, "STORAGE_FAILURE")
                self.assertNotIn("PRIVATE_FSYNC", str(error.exception))
                plan = fixture.store.plan_source_erasure("s", fixture.owner, "A", expected_version=1)
                fixture.store.begin_source_erasure("s", fixture.owner, "A", expected_version=1,
                    plan_hash=plan["plan_hash"], erasure_id="e" * 32)
                self.assertEqual(fixture.store.resume_source_erasure("s", fixture.owner, "e" * 32)["status"],
                                 "LOCAL_REFERENCE_ERASURE_COMPLETE")
                for path in Path(fixture.tmp.name).rglob("*"):
                    if path.is_file():
                        self.assertNotIn(b"FSYNC_PRIVATE_CANARY", path.read_bytes())

    def test_torn_unpublished_journal_never_strands_source_erasure(self):
        original = Path.open
        class TornWrite:
            def __init__(self, stream): self.stream = stream
            def __enter__(self): return self
            def __exit__(self, *args): return self.stream.__exit__(*args)
            def write(self, body):
                self.stream.write(body[:10])
                self.stream.flush()
                raise OSError("PRIVATE_METADATA_WRITE_CANARY")
        def broken(path, *args, **kwargs):
            stream = original(path, *args, **kwargs)
            return TornWrite(stream) if path.suffix == ".pending" else stream
        with patch.object(Path, "open", broken), self.assertRaises(HCLFailure):
            self.store.put_source("s", self.owner, "A", "UNWRITTEN_PRIVATE_CANARY")
        self.assertFalse(pending(self.store))
        plan = self.store.plan_source_erasure("s", self.owner, "A", expected_version=1)
        self.store.begin_source_erasure("s", self.owner, "A", expected_version=1,
                                       plan_hash=plan["plan_hash"], erasure_id="f" * 32)
        self.assertEqual(self.store.resume_source_erasure("s", self.owner, "f" * 32)["status"],
                         "LOCAL_REFERENCE_ERASURE_COMPLETE")


if __name__ == "__main__":
    unittest.main()
