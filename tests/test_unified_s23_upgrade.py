"""Real exact S2.2 runtime fixture, current behavior after controlled side-copy.

Only its 162 explicitly inventoried hcl/*.py files are materialized. No tests,
evaluation packages, credentials or sealed inputs are read from the old tree.
"""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from hashlib import sha256
from pathlib import Path
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from hcl import HCL
from hcl.kernel.types import HCLFailure, Principal, TaskRequest, TaskResult
from hcl.memory import codec
from hcl.memory.migrations.control import version_bundle
from hcl.memory.migrations.revision_upgrade import RevisionCutover, S22_CODE_HASH
from hcl.memory.store import StateStore
from hcl.models.gateway import ModelGateway, OfflineModelPort
from hcl.runtime.budget import TaskBudgetLedger

BASELINE = "8643a82cf909890879fb413f56a7ebe74a44334f"
ROOT = Path(__file__).resolve().parents[1]
OLD_PROGRAM = r"""
import json,sys
from pathlib import Path
from dataclasses import replace
from hcl import HCL
from hcl.kernel.types import Principal,TaskRequest,BudgetSlice
from hcl.memory import codec
from hcl.memory.store import StateStore
from hcl.memory.migrations.namespace import MigrationNamespace
from hcl.memory.migrations.legacy import LegacySnapshot,LegacySource
from hcl.memory.migrations.revision_upgrade import RevisionCutover
from hcl.memory.migrations.control import version_bundle
from hcl.runtime.budget import TaskBudgetLedger
root=Path(sys.argv[1]); schema=int(sys.argv[2]); owner=Principal('tenant','alice')
if schema in (2,4):
 ns=MigrationNamespace.import_snapshot(root/'imported',LegacySnapshot((LegacySource('source',1,'ORIGINAL_SOURCE'),LegacySource('private',1,'BOB_ONLY_QUARANTINE'),LegacySource('private',2,'BOB_ONLY_QUARANTINE_v2'))),namespace_id='legacy',owner=owner,readers={'source':('alice',),'private':('bob',)})
 if schema==4: ns=RevisionCutover.upgrade(ns.path,root/'old4',owner)
 store=ns.open_store(); session=store._db.execute('SELECT session_id FROM sessions').fetchone()[0]
 source_id=store._db.execute('SELECT source_id FROM sources').fetchone()[0]
 handle=store.current_handles(session,owner,(source_id,))[0]
else:
 store=StateStore.sqlite(root/'old.sqlite',revision=True);session='s';store.create_session(session,owner,{'bob'})
 handle=store.put_source(session,owner,'source','ORIGINAL_SOURCE')
request=TaskRequest('completed','report',(handle,),session,owner)
result=HCL(store,principal=owner).run_sync(request)
assert result.status=='COMPLETED'
revision_request=None
if schema in (3,4):
 from hcl.kernel.dependencies import RevisionIssue
 from hcl.models.gateway import OfflineModelPort,ModelGateway
 from hcl.semantics.segments import segment_snapshot
 from hcl.semantics.revision import KINDS
 revision_request=replace(request,request_id='revision-completed',issue=RevisionIssue('revision'),budget=BudgetSlice(max_mock_calls=1,max_output_bytes=262144,max_request_bytes=262144))
 snap=store.revision_snapshot(session,owner,(handle,))
 anchors=[s.segment_id for s in segment_snapshot(snap,revision_request.question) if s.kind=='SOURCE']
 source={k:[] for k in KINDS};source.update(source_id=handle.source_id,nogoods=[],unparsed_segments=[])
 def ref(name):return [handle.source_id,name]
 def add(category,name,**fields):source[category].append(dict(id=name,segment_ids=anchors,**fields))
 add('frames','f',kind='SOURCE_DISCOURSE',parent=None)
 add('entities','person',label='person')
 add('perspectives','view',agent=None,nested=[],at=ref('t'),observation_model='source-report',belief_model='NOT_COMPUTED')
 add('scopes','scope',frame=ref('f'),perspective=ref('view'),at=ref('t'))
 add('points','t',axis='EVENT',scope=ref('scope'),agent=None)
 for name,negative in [('q',False),('not-q',True)]:add('claims',name,predicate='p',arguments=[ref('person')],negated=negative,scope=ref('scope'),index=None)
 add('roots','report',claim=ref('q'),assumptions=[],event_end=ref('t'),access=[],origin='DIRECT_REPORT')
 candidate=dict(schema='hcl-revision-candidates-1',sources=[source],query=dict(positive=ref('q'),negative=ref('not-q')))
 answer=HCL(store,principal=owner,gateway=ModelGateway(store,OfflineModelPort(json.dumps(candidate)))).run_sync(revision_request)
 assert answer.status=='COMPLETED',answer.diagnostics
ledger=TaskBudgetLedger(store);snap=store.snapshot(session,owner,(handle,))
for name in ('reserved','sending','unknown'):
 r=replace(request,request_id=name,budget=BudgetSlice(max_mock_calls=1))
 lease,_=ledger.bind(r,snap);ledger.reserve(lease,snap,r.question,r.budget,'response','old exact serialized context')
 if name!='reserved': ledger.transition(lease,'response','RESERVED','SEND_STARTED',snapshot=snap)
 if name=='unknown': ledger.recover_abandoned(owner,session,name,store.owner_id)
print(json.dumps({'path':str(store.path),'session':session,'owner_id':store.owner_id,'request':codec.dumps(request).decode(),
                  'revision_request':None if revision_request is None else codec.dumps(revision_request).decode(),'bundle':version_bundle(schema=schema)}),flush=True)
for line in sys.stdin:
 command=json.loads(line)
 try:
  if command['action']=='snapshot': store.snapshot(session,owner,(handle,))
  elif command['action']=='write': store.put_source(session,owner,'late','late')
  elif command['action']=='open': StateStore.sqlite(command['path'])
  elif command['action']=='close': break
  print(json.dumps({'ok':True}),flush=True)
 except Exception as error: print(json.dumps({'ok':False,'error':type(error).__name__}),flush=True)
store.close()
"""


class Crash(BaseException):
    pass


class RuntimeUpgradeTests(unittest.TestCase):
    baseline = BASELINE
    code_hash = S22_CODE_HASH
    file_count = 162
    old_program = OLD_PROGRAM

    @classmethod
    def setUpClass(cls):
        cls.projection = tempfile.TemporaryDirectory()
        root = Path(cls.projection.name)
        raw = subprocess.check_output(["git", "ls-tree", "-rz", cls.baseline, "hcl"], cwd=ROOT)
        inventory = {}
        for row in raw.split(b"\0"):
            if not row:
                continue
            meta, path = row.split(b"\t")
            name = path.decode()
            if not name.endswith(".py"):
                continue
            mode, kind, digest = meta.decode().split()
            if (
                kind != "blob"
                or mode != "100644"
                or not name.startswith("hcl/")
                or ".." in Path(name).parts
            ):
                raise AssertionError("unexpected baseline runtime member")
            body = subprocess.check_output(["git", "cat-file", "blob", digest], cwd=ROOT)
            inventory[name[4:]] = sha256(body).hexdigest()
            target = root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(body)
        if (
            len(inventory) != cls.file_count
            or sha256(codec.canonical(inventory).encode()).hexdigest() != cls.code_hash
        ):
            raise AssertionError("exact predecessor runtime inventory mismatch")
        cls.runtime = root

    @classmethod
    def tearDownClass(cls):
        cls.projection.cleanup()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.owner = Principal("tenant", "alice")
        self.processes = []

    def tearDown(self):
        for process in self.processes:
            if process.poll() is None:
                process.stdin.write('{"action":"close"}\n')
                process.stdin.flush()
                process.communicate(timeout=10)
        self.tmp.cleanup()

    def old(self, schema=3, name="old"):
        directory = self.root / name
        directory.mkdir()
        env = {
            "PATH": os.defpath,
            "PYTHONPATH": str(self.runtime),
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONNOUSERSITE": "1",
        }
        process = subprocess.Popen(
            [sys.executable, "-u", "-c", self.old_program, str(directory), str(schema)],
            cwd=self.runtime,
            env=env,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self.processes.append(process)
        line = process.stdout.readline()
        if not line:
            raise AssertionError(process.communicate(timeout=5)[1])
        metadata = json.loads(line)
        self.assertEqual(metadata["bundle"]["code_sha256"], self.code_hash)
        return Path(metadata["path"]), metadata, process

    @staticmethod
    def command(process, **data):
        process.stdin.write(json.dumps(data) + "\n")
        process.stdin.flush()
        return json.loads(process.stdout.readline())

    def test_real_old_3_and_4_wire_events_calls_and_fenced_open_writers(self):
        for schema in (3, 4):
            with self.subTest(schema=schema):
                source, old, process = self.old(schema, str(schema))
                db = sqlite3.connect(source)
                db.row_factory = sqlite3.Row
                original = {
                    table: [dict(row) for row in db.execute("SELECT * FROM " + table)]
                    for table in ("sessions", "sources", "inferences", "tasks", "calls", "events")
                }
                old_control = dict(db.execute("SELECT * FROM revision_control").fetchone())
                db.close()
                objects = {
                    p.name: p.read_bytes() for p in source.with_name(source.name + ".objects").iterdir()
                }
                with self.assertRaises(ValueError):
                    StateStore.sqlite(source)
                target = RevisionCutover.upgrade(source, self.root / ("new" + str(schema)), self.owner)
                current = target.open_store()
                try:
                    self.assertEqual(current._schema, schema)
                    for table, rows in original.items():
                        self.assertEqual(
                            [dict(row) for row in current._db.execute("SELECT * FROM " + table)], rows
                        )
                    for name, body in objects.items():
                        self.assertEqual((current.object_root / name).read_bytes(), body)
                    request = codec.loads(old["request"].encode())
                    self.assertEqual(codec.dumps(request), old["request"].encode())
                    port = OfflineModelPort()
                    replay = HCL(
                        current, principal=self.owner, gateway=ModelGateway(current, port)
                    ).run_sync(request)
                    self.assertEqual(replay.status, "COMPLETED")
                    self.assertTrue(replay.execution_receipt["replayed"])
                    self.assertEqual(port.attempts, 0)
                    revision_request = codec.loads(old["revision_request"].encode())
                    self.assertEqual(codec.dumps(revision_request), old["revision_request"].encode())
                    revision_replay = HCL(
                        current, principal=self.owner, gateway=ModelGateway(current, port)
                    ).run_sync(revision_request)
                    self.assertEqual(revision_replay.status, "COMPLETED")
                    self.assertEqual(port.attempts, 0)
                    if schema == 4:
                        with self.assertRaises(HCLFailure):
                            target.legacy_view(self.owner)
                    mismatch = HCL(current, principal=self.owner).run_sync(
                        replace(request, question="changed")
                    )
                    self.assertEqual(mismatch.diagnostics[0].code, "REQUEST_FINGERPRINT_MISMATCH")
                    calls = list(
                        current._db.execute("SELECT * FROM calls WHERE state IN ('SEND_STARTED','UNKNOWN')")
                    )
                    self.assertEqual(len(calls), 2)
                    self.assertTrue(
                        all(
                            row["attempted"] is None and row["owner_id"] == old["owner_id"] for row in calls
                        )
                    )
                    self.assertEqual(
                        TaskBudgetLedger(current).recover_abandoned(
                            self.owner, old["session"], "sending", old["owner_id"]
                        ),
                        1,
                    )
                    for action in ("snapshot", "write"):
                        self.assertFalse(self.command(process, action=action)["ok"])
                    self.assertFalse(self.command(process, action="open", path=str(target.path))["ok"])
                    db = sqlite3.connect(source)
                    db.row_factory = sqlite3.Row
                    self.assertEqual(
                        dict(db.execute("SELECT * FROM revision_control").fetchone()),
                        {**old_control, "mode": "TERMINAL_SOURCE"},
                    )
                    self.assertEqual(db.execute("PRAGMA user_version").fetchone()[0], 91)
                    db.close()
                    target.rollback(self.owner)
                    with self.assertRaises(HCLFailure):
                        current.snapshot(old["session"], self.owner, request.source_handles)
                finally:
                    current.close()

    def test_real_old_schema2_created_during_s22_also_upgrades(self):
        source, old, _ = self.old(2)
        with self.assertRaises(ValueError):
            StateStore.sqlite(source)
        target = RevisionCutover.upgrade(source, self.root / "new", self.owner)
        store = target.open_store()
        try:
            self.assertEqual(store._schema, 4)
            request = codec.loads(old["request"].encode())
            self.assertEqual(HCL(store, principal=self.owner).run_sync(request).status, "COMPLETED")
        finally:
            store.close()

    def test_every_3_and_4_post_fence_crash_recovers_one_final_path(self):
        for schema in (3, 4):
            for seam in ("source_fenced", "target_activated_unpublished", "published"):
                with self.subTest(schema=schema, seam=seam):
                    source, _, _ = self.old(schema, str(schema) + seam)
                    directory = self.root / ("new" + str(schema) + seam)

                    def fault(stage):
                        if stage == seam:
                            raise Crash()

                    with patch.object(RevisionCutover, "_checkpoint", side_effect=fault), self.assertRaises(
                        Crash
                    ):
                        RevisionCutover.upgrade(source, directory, self.owner)
                    if seam == "target_activated_unpublished":
                        with self.assertRaises((ValueError, HCLFailure)):
                            StateStore.sqlite(
                                directory.with_name("." + directory.name + ".unpublished") / "state.sqlite"
                            )
                    target = RevisionCutover.upgrade(source, directory, self.owner)
                    self.assertEqual(
                        RevisionCutover.upgrade(source, directory, self.owner).audit(self.owner),
                        target.audit(self.owner),
                    )
                    self.assertTrue(
                        any(row["state"] == "SEND_STARTED" for row in target.audit(self.owner)["calls"])
                    )

    def test_same_target_concurrent_recovery_and_foreign_target_rejection(self):
        for schema in (3, 4):
            source, _, _ = self.old(schema, str(schema))
            with ThreadPoolExecutor(max_workers=3) as pool:
                targets = list(
                    pool.map(
                        lambda _: RevisionCutover.upgrade(
                            source, self.root / ("new" + str(schema)), self.owner
                        ),
                        range(3),
                    )
                )
            self.assertEqual(len({str(t.path) for t in targets}), 1)
            with self.assertRaises(ValueError):
                RevisionCutover.upgrade(source, self.root / ("another" + str(schema)), self.owner)

    def test_bad_bundle_and_readonly_predecessor_never_fence(self):
        for mutation in ("hash", "index", "readonly", "path", "missing"):
            source, _, _ = self.old(3, mutation)
            db = sqlite3.connect(source)
            if mutation in ("hash", "index"):
                bundle = json.loads(db.execute("SELECT versions FROM revision_control").fetchone()[0])
                if mutation == "hash":
                    bundle["code_sha256"] = "0" * 64
                else:
                    bundle["indexes"] = {"revision": 2}
                db.execute("UPDATE revision_control SET versions=?", (json.dumps(bundle),))
            elif mutation == "readonly":
                db.execute("UPDATE revision_control SET mode='READ_ONLY'")
            elif mutation == "path":
                db.execute("UPDATE revision_control SET target_path='foreign'")
            else:
                db.execute("DROP TABLE revision_control")
            db.commit()
            db.close()
            with self.assertRaises((ValueError, HCLFailure)):
                RevisionCutover.upgrade(source, self.root / ("new" + mutation), self.owner)
            db = sqlite3.connect(source)
            self.assertEqual(db.execute("PRAGMA user_version").fetchone()[0], 3)
            db.close()
