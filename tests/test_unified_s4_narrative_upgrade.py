"""Real reviewed 202-file governance predecessor, never a fabricated code pin.

Only newly created temporary synthetic namespaces are erased in these tests.
The historical predecessor is a remote-readable Python-only source snapshot.
The qualified successor is bound to the same-runtime published main identity;
neither source identity changes original assertions or runtime hashes.
"""

import json
import sqlite3
import unittest
from unittest.mock import patch

from hcl import HCL
from hcl.kernel.types import HCLFailure
from hcl.memory import codec
from hcl.memory.governance import TABLES, verify_inventory
from hcl.memory.migrations.revision_upgrade import (
    RevisionCutover,
    M10_GOVERNANCE_CODE_HASH,
)
from tests import test_unified_s23_upgrade as fixtures

OLD_PROGRAM = r"""
import json,sys
from pathlib import Path
from dataclasses import replace
from hcl import HCL
from hcl.kernel.types import Principal,TaskRequest,BudgetSlice,Issue
from hcl.memory import codec
from hcl.memory.store import StateStore
from hcl.memory.migrations.namespace import MigrationNamespace
from hcl.memory.migrations.types import LegacySnapshot,LegacySource,LegacyRecord
from hcl.memory.migrations.compile import source_key
from hcl.memory.migrations.revision_upgrade import RevisionCutover
from hcl.memory.migrations.control import version_bundle
from hcl.models.gateway import ModelGateway,OfflineModelPort
from hcl.runtime.budget import TaskBudgetLedger
from hcl.memory.retention_objects import pending
root=Path(sys.argv[1]);schema=int(sys.argv[2]);owner=Principal('tenant','alice')
if schema==4:
 imported=MigrationNamespace.import_snapshot(root/'imported',LegacySnapshot((LegacySource('A',1,'PRIVATE_A_SYNTHETIC_CANARY'),LegacySource('B',1,'INDEPENDENT_B_ORIGINAL')), (LegacyRecord('unknown','SYSTEM_INTERPRETATION',{'raw':'UNKNOWN_SYNTHETIC_RETAINED'}),)),namespace_id='legacy',owner=owner)
 receipt=imported.receipt(owner);session=receipt['session_id']
 ids={name:receipt['source_mapping'][source_key(name,1)]['source_id'] for name in ('A','B')}
 ns=RevisionCutover.upgrade(imported.path,root/'old4',owner);store=ns.open_store()
 store.prepare_legacy_capsules(session,owner)
else:
 store=StateStore.sqlite(root/'old.sqlite',revision=True);session='s';store.create_session(session,owner,{'bob'})
 ids={'A':'A','B':'B'}
 for name,text in [('A','PRIVATE_A_SYNTHETIC_CANARY'),('B','INDEPENDENT_B_ORIGINAL')]:store.put_source(session,owner,ids[name],text)
c=store.put_source(session,owner,'C','LATER_ERASURE_C_ORIGINAL')
handles={name:store.current_handles(session,owner,(source,))[0] for name,source in ids.items()}
requests={}
for name,handle in handles.items():
 request=TaskRequest('report-'+name,'Read this source.',(handle,),session,owner,budget=BudgetSlice(max_mock_calls=1),issue=Issue('answer','model.respond'))
 result=HCL(store,principal=owner,gateway=ModelGateway(store,OfflineModelPort('SHARED_INDEPENDENT_RETURN'))).run_sync(request)
 assert result.status=='COMPLETED',result.diagnostics
 requests[name]=codec.dumps(request).decode()
ledger=TaskBudgetLedger(store);snapshot=store.snapshot(session,owner,(handles['A'],))
unknown=replace(codec.loads(requests['A'].encode()),request_id='unknown-A')
lease,_=ledger.bind(unknown,snapshot);ledger.reserve(lease,snapshot,unknown.question,unknown.budget,'response','PRIVATE_A_SYNTHETIC_CONTEXT')
ledger.transition(lease,'response','RESERVED','SEND_STARTED',snapshot=snapshot)
ledger.recover_abandoned(owner,session,unknown.request_id,store.owner_id)
requests['unknown']=codec.dumps(unknown).decode()
plan=store.plan_source_erasure(session,owner,ids['A'],expected_version=1)
store.begin_source_erasure(session,owner,ids['A'],expected_version=1,plan_hash=plan['plan_hash'],erasure_id='a'*32)
receipt=store.resume_source_erasure(session,owner,'a'*32)
assert receipt['database_scrubbed'],receipt
# These exact frozen runtimes closed a raw database descriptor during cleanup,
# invalidating their traditional POSIX locks. Retire that connection before any
# other process opens the store; do not patch the predecessor bytes or pins.
path=store.path
store.close()
store=StateStore.sqlite(path)
assert store.source_erasure_receipt(session,owner,'a'*32)==receipt
b_view=None if schema==3 else codec.dumps(store.legacy_source_view(session,owner,(ids['B'],))).decode()
assert not pending(store)
print(json.dumps(dict(path=str(store.path),session=session,ids=ids,requests=requests,bundle=version_bundle(schema=schema),
    salt=store._revision_control['governance_salt'],b_view=b_view,receipt=receipt,owner_id=store.owner_id)),flush=True)
for line in sys.stdin:
 command=json.loads(line)
 try:
  action=command['action']
  if action=='close':break
  if action=='write':store.put_source(session,owner,'late','late')
  if action=='staging':
   context=store.snapshot(session,owner,(c,))
   with store._transaction(True):
    store._put_content('STAGED_SYNTHETIC_C',session_id=session,context=context)
  if action=='erase-pending':
   p=store.plan_source_erasure(session,owner,'C',expected_version=1)
   store.begin_source_erasure(session,owner,'C',expected_version=1,plan_hash=p['plan_hash'],erasure_id='c'*32)
  if action=='finish':
   finished=store.resume_source_erasure(session,owner,'c'*32)
   store.close()
   store=StateStore.sqlite(path)
   assert store.source_erasure_receipt(session,owner,'c'*32)==finished
  print(json.dumps({'ok':True}),flush=True)
 except Exception as error:print(json.dumps({'ok':False,'error':type(error).__name__}),flush=True)
store.close()
"""


class GovernedNarrativeUpgradeTests(unittest.TestCase):
    baseline = "5f797274a12d29295b90f1ecb9c3b61372463445"
    code_hash = M10_GOVERNANCE_CODE_HASH
    file_count = 202
    @classmethod
    def setUpClass(cls):
        class OldGovernance(fixtures.RuntimeUpgradeTests):
            baseline = cls.baseline
            code_hash = cls.code_hash
            file_count = cls.file_count
            old_program = OLD_PROGRAM

        cls.old_fixture = OldGovernance
        cls.old_fixture.setUpClass()

    @classmethod
    def tearDownClass(cls):
        cls.old_fixture.tearDownClass()

    def fixture(self):
        f = self.old_fixture()
        f.setUp()
        self.addCleanup(f.tearDown)
        return f

    @staticmethod
    def rows(db):
        return {
            name: sorted(
                (dict(row) for row in db.execute("SELECT * FROM " + name)),
                key=codec.canonical,
            )
            for name in (
                *sorted(TABLES),
                "events",
                "calls",
                "tasks",
                "sources",
                "inferences",
                "sessions",
            )
        }

    def test_real_governed_relationship_checkpoint_family(self):
        # Reuse the complete existing behavioral assertions, but actually create
        # every object in the exact 202-file governed predecessor interpreter.
        # No current-code fixture or rewritten old identity substitutes for it.
        from tests import test_unified_s4_retrieval_upgrade as previous

        f = self.fixture()
        previous.M09RuntimeUpgradeTests.test_real_relationship_states_and_retrieval_of_old_originals(
            f
        )

    def test_real_governed_schemas_preserve_erasure_unknown_accounting_and_independent_cas(
        self,
    ):
        f = self.fixture()
        for schema in (3, 4):
            source, old, process = f.old(schema, str(schema))
            with sqlite3.connect(source) as db:
                db.row_factory = sqlite3.Row
                before = self.rows(db)
            target = RevisionCutover.upgrade(
                source, f.root / ("new" + str(schema)), f.owner
            )
            store = target.open_store()
            self.addCleanup(store.close)
            self.assertEqual(store._revision_control["governance_salt"], old["salt"])
            self.assertEqual(self.rows(store._db), before)
            verify_inventory(store._db)
            for key in ("A", "unknown"):
                result = HCL(store, principal=f.owner).run_sync(
                    codec.loads(old["requests"][key].encode())
                )
                self.assertEqual(result.status, "DENIED", result.diagnostics)
                self.assertEqual(result.diagnostics[0].code, "CONTENT_ERASED")
                self.assertFalse(result.answer)
                self.assertEqual(result.usage["held_mock_calls"], 1)
                if key == "unknown":
                    self.assertIsNone(result.usage["mock_calls"])
            b = HCL(store, principal=f.owner).run_sync(
                codec.loads(old["requests"]["B"].encode())
            )
            self.assertEqual(b.status, "COMPLETED", b.diagnostics)
            self.assertIn("SHARED_INDEPENDENT_RETURN", b.answer)
            self.assertEqual(b.usage["replay_new_mock_calls"], 0)
            if schema == 4:
                self.assertEqual(
                    codec.dumps(
                        store.legacy_source_view(
                            old["session"], f.owner, (old["ids"]["B"],)
                        )
                    ).decode(),
                    old["b_view"],
                )
            store.rebuild_projections()
            verify_inventory(store._db)
            self.assertEqual(self.rows(store._db), before)
            self.assertFalse(f.command(process, action="write")["ok"])
            RevisionCutover.upgrade(source, target.directory, f.owner)
            # A later independent erasure must compose after the inherited A baseline.
            p = store.plan_source_erasure(
                old["session"], f.owner, "C", expected_version=1
            )
            store.begin_source_erasure(
                old["session"],
                f.owner,
                "C",
                expected_version=1,
                plan_hash=p["plan_hash"],
                erasure_id="c" * 32,
            )
            receipt = store.resume_source_erasure(old["session"], f.owner, "c" * 32)
            self.assertIn("PREDECESSOR_COPY_RETAINED", receipt["limitations"])
            RevisionCutover.upgrade(source, target.directory, f.owner)
            self.assertEqual(
                HCL(store, principal=f.owner)
                .run_sync(codec.loads(old["requests"]["B"].encode()))
                .status,
                "COMPLETED",
            )

    def test_each_cutover_checkpoint_recovers_without_regenerating_governance(self):
        class Crash(BaseException):
            pass

        f = self.fixture()
        for index, seam in enumerate(
            ("prepared", "source_fenced", "target_activated_unpublished", "published")
        ):
            source, old, _ = f.old(4, "crash" + str(index))
            directory = f.root / ("successor" + str(index))

            def fault(at):
                if at == seam:
                    raise Crash()

            with patch.object(
                RevisionCutover, "_checkpoint", side_effect=fault
            ), self.assertRaises(Crash):
                RevisionCutover.upgrade(source, directory, f.owner)
            target = RevisionCutover.upgrade(source, directory, f.owner)
            store = target.open_store()
            self.addCleanup(store.close)
            self.assertEqual(store._revision_control["governance_salt"], old["salt"])
            verify_inventory(store._db)
            self.assertEqual(
                codec.dumps(
                    store.legacy_source_view(
                        old["session"], f.owner, (old["ids"]["B"],)
                    )
                ).decode(),
                old["b_view"],
            )
            self.assertEqual(
                store.source_erasure_receipt(old["session"], f.owner, "a" * 32),
                old["receipt"],
            )
            RevisionCutover.upgrade(source, directory, f.owner)

    def test_recorded_erasure_cannot_be_reverted_to_inherited_source_checkpoint(self):
        # Independent review's coherent stale-prefix counterexample. All files
        # here are temporary synthetic fixtures; no real originals are restored.
        from hashlib import sha256
        import shutil
        from hcl.memory.erasure import _rebuild_annotations
        from hcl.memory.migrations.revision_upgrade import _history

        f = self.fixture()
        source, old, _ = f.old(3, "stale-prefix")
        target = RevisionCutover.upgrade(source, f.root / "stale-target", f.owner)
        store = target.open_store()
        original = {
            r["seq"]: dict(r) for r in store._db.execute("SELECT * FROM events")
        }
        annotations = {
            r["seq"]: json.loads(r["annotation"])
            for r in store._db.execute("SELECT * FROM retention_events")
        }
        original_c = dict(
            store._db.execute("SELECT * FROM sources WHERE source_id='C'").fetchone()
        )
        plan = store.plan_source_erasure(
            old["session"], f.owner, "C", expected_version=1
        )
        store.begin_source_erasure(
            old["session"],
            f.owner,
            "C",
            expected_version=1,
            plan_hash=plan["plan_hash"],
            erasure_id="c" * 32,
        )
        receipt = store.resume_source_erasure(old["session"], f.owner, "c" * 32)
        self.assertTrue(receipt["database_scrubbed"])
        changes = json.loads(
            store._db.execute(
                "SELECT targets FROM erasures WHERE erasure_id=?", ("c" * 32,)
            ).fetchone()[0]
        )["event_changes"]
        self.assertTrue(changes)
        store.close()
        with sqlite3.connect(target.path) as db:
            db.row_factory = sqlite3.Row
            current_annotations = {
                r["seq"]: json.loads(r["annotation"])
                for r in db.execute("SELECT * FROM retention_events")
            }
            for change in changes:
                row = original[change["seq"]]
                db.execute(
                    "UPDATE events SET kind=?,payload=? WHERE seq=?",
                    (row["kind"], row["payload"], row["seq"]),
                )
                current_annotations[row["seq"]] = annotations[row["seq"]]
            heads = {}
            for row in list(db.execute("SELECT * FROM events ORDER BY seq")):
                previous = heads.get(row["session_id"], "")
                digest = sha256(
                    codec.canonical(
                        [
                            row["session_id"],
                            row["revision"],
                            row["kind"],
                            row["payload"],
                            previous,
                        ]
                    ).encode()
                ).hexdigest()
                heads[row["session_id"]] = digest
                db.execute(
                    "UPDATE events SET previous_hash=?,event_hash=? WHERE seq=?",
                    (previous, digest, row["seq"]),
                )
            fields = list(original_c)
            db.execute(
                "INSERT INTO sources("
                + ",".join(fields)
                + ") VALUES("
                + ",".join("?" for _ in fields)
                + ")",
                [original_c[k] for k in fields],
            )
            _rebuild_annotations(db, current_annotations)
            verify_inventory(db)
        for path in source.with_name(source.name + ".objects").iterdir():
            if path.is_file():
                shutil.copyfile(
                    path,
                    target.path.with_name(target.path.name + ".objects") / path.name,
                )
        with sqlite3.connect(target.path) as db:
            db.row_factory = sqlite3.Row
            # All generic integrity checks pass: this is the additional semantic
            # authorization obligation, not a broken hash-chain negative test.
            _history(db, target.path.with_name(target.path.name + ".objects"))
            self.assertEqual(
                db.execute(
                    "SELECT count(*) FROM sources WHERE source_id='C'"
                ).fetchone()[0],
                1,
            )
        with self.assertRaises(HCLFailure) as caught:
            RevisionCutover.upgrade(source, target.directory, f.owner)
        self.assertEqual(caught.exception.diagnostic.code, "STATE_CORRUPT")

    def test_pending_staging_or_cleanup_is_explicit_precondition_not_dropped(self):
        f = self.fixture()
        for mode, code in [
            ("staging", "GOVERNANCE_STAGING_UNRESOLVED"),
            ("erase-pending", "GOVERNANCE_CLEANUP_UNRESOLVED"),
        ]:
            source, _, process = f.old(3, mode)
            self.assertTrue(f.command(process, action=mode)["ok"])
            with self.assertRaises(HCLFailure) as caught:
                RevisionCutover.upgrade(source, f.root / ("blocked-" + mode), f.owner)
            self.assertEqual(caught.exception.diagnostic.code, code)
            self.assertEqual(caught.exception.status, "DEFERRED")
            self.assertTrue(f.command(process, action="write")["ok"])
            if mode == "erase-pending":
                self.assertTrue(f.command(process, action="finish")["ok"])
                # Independently observe the durable receipt before cutover;
                # never turn an unresolved old cleanup into a permitted upgrade.
                db = sqlite3.connect(source)
                try:
                    receipt = json.loads(db.execute(
                        "SELECT receipt FROM erasures WHERE erasure_id=?", ("c" * 32,)
                    ).fetchone()[0])
                    self.assertTrue(receipt["database_scrubbed"])
                    self.assertNotIn("DATABASE_SCRUB_PENDING", receipt["limitations"])
                finally:
                    db.close()
                RevisionCutover.upgrade(source, f.root / ("blocked-" + mode), f.owner)

    def test_recovery_rejects_rekeyed_unpublished_successor_even_with_valid_control_binding(
        self,
    ):
        from hashlib import sha256

        class Crash(BaseException):
            pass

        f = self.fixture()
        source, old, _ = f.old(3, "rekey")
        directory = f.root / "new-rekey"

        def fault(stage):
            if stage == "target_activated_unpublished":
                raise Crash()

        with patch.object(
            RevisionCutover, "_checkpoint", side_effect=fault
        ), self.assertRaises(Crash):
            RevisionCutover.upgrade(source, directory, f.owner)
        target = RevisionCutover(source, directory)
        with sqlite3.connect(target.stage / "state.sqlite") as db:
            db.row_factory = sqlite3.Row
            row = dict(db.execute("SELECT * FROM revision_control").fetchone())
            salt = "0" * 64
            binding = sha256(
                codec.canonical(
                    [
                        row["governance_protocol"],
                        salt,
                        row["upgrade_id"],
                        row["source_path"],
                        row["target_path"],
                    ]
                ).encode()
            ).hexdigest()
            db.execute(
                "UPDATE revision_control SET governance_salt=?,governance_binding=?",
                (salt, binding),
            )
        with self.assertRaises(ValueError):
            RevisionCutover.upgrade(source, directory, f.owner)
        self.assertFalse(directory.exists())


if __name__ == "__main__":
    unittest.main()


class QualifiedGovernedNarrativeUpgradeTests(GovernedNarrativeUpgradeTests):
    """Every original assertion on the exact M09-qualified governance successor."""
    baseline = "b6ea0534f64ef6a02b9aac6414c09d0465561bdd"
    from hcl.memory.migrations.revision_upgrade import M10_QUALIFIED_GOVERNANCE_CODE_HASH as code_hash
    file_count = 203
