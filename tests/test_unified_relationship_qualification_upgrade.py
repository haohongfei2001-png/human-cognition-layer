"""Real historical M09 results retain their bytes, not outdated eligibility.

Only disposable synthetic schema3/4 stores and the exact 189-file old runtime
are used. A RETURNED candidate has no accepted effect and can be recomputed;
completed/computed/committed unsafe numerical effects must fail current delivery.
"""

from dataclasses import replace
import asyncio
import json
import unittest
from hcl import HCL
from hcl.memory import codec
from hcl.memory.store import StateStore
from hcl.memory.migrations.revision_upgrade import (
    RevisionCutover,
    M09_RELATIONSHIP_CODE_HASH,
)
from hcl.models.gateway import ModelGateway, OfflineModelPort
from hcl.runtime.recovery import RecoveryManager
from scripts.witness_unified_relationship_qualification import SOURCE, propose
from tests import test_unified_s23_upgrade as base

OLD_PROGRAM = r"""
import sys,json
from pathlib import Path
from hcl import HCL,ExecutionBudget,ExecutionIssue
from hcl.kernel.types import Principal,Issue,TaskRequest
from hcl.memory import codec
from hcl.memory.store import StateStore
from hcl.memory.migrations.namespace import MigrationNamespace
from hcl.memory.migrations.legacy import LegacySnapshot,LegacySource
from hcl.memory.migrations.revision_upgrade import RevisionCutover
from hcl.memory.migrations.control import version_bundle
from hcl.models.gateway import ModelGateway,OfflineModelPort
root=Path(sys.argv[1]);schema=int(sys.argv[2]);owner=Principal('tenant','alice')
if schema==4:
 ns=MigrationNamespace.import_snapshot(root/'imported',LegacySnapshot((LegacySource('bootstrap',1,'SYNTHETIC_BOOTSTRAP'),)),namespace_id='old-qualification',owner=owner)
 store=RevisionCutover.upgrade(ns.path,root/'old4',owner).open_store();session=store._db.execute('SELECT session_id FROM sessions').fetchone()[0]
else:
 store=StateStore.sqlite(root/'old.sqlite',revision=True);session='s';store.create_session(session,owner)
print(json.dumps(dict(path=str(store.path),session=session,bundle=version_bundle(schema=schema),owner_id=store.owner_id)),flush=True)
class Crash(BaseException):pass
handle=None
for line in sys.stdin:
 c=json.loads(line)
 if c['action']=='close':break
 try:
  if c['action']=='write':
   store.put_source(session,owner,'late','SYNTHETIC_LATE');reply=dict(ok=True)
  else:
   if handle is None:handle=store.put_source(session,owner,'records',c['text'])
   request=TaskRequest(c['id'],c['question'],(handle,),session,owner,
    budget=ExecutionBudget(max_mock_calls=1,max_feedback=0,max_local_evaluations=16000,max_request_bytes=1048576,max_context_tokens=1048576,max_output_bytes=4194304,max_total_output_bytes=16777216,max_visible_output_tokens=1048576),
    issue=ExecutionIssue('root',goals=(Issue(c['id'],'relationship.evaluate'),)))
   original=store._checkpoint
   def fail(stage):
    if stage==c['seam']:raise Crash()
   store._checkpoint=fail;port=OfflineModelPort(json.dumps(c['candidate']));result=None
   try:result=HCL(store,principal=owner,gateway=ModelGateway(store,port)).run_sync(request)
   except Crash:pass
   finally:store._checkpoint=original
   rows=[dict(r) for r in store._db.execute('SELECT * FROM inferences')]
   reply=dict(ok=True,request=codec.dumps(request).decode(),result=None if result is None else codec.dumps(result).decode(),attempts=port.attempts,
    inferences=rows,objects={r['object_hash']:(store.object_root/r['object_hash']).read_text() for r in rows})
  print(json.dumps(reply),flush=True)
 except Exception as e:print(json.dumps(dict(ok=False,error=type(e).__name__,message=str(e))),flush=True)
store.close()
"""


class HistoricalQualificationUpgradeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        class Projection(base.RuntimeUpgradeTests):
            baseline = "52c3ba6c54efee2b8196edc3c5360e915d695242"
            code_hash = M09_RELATIONSHIP_CODE_HASH
            file_count = 189
            old_program = OLD_PROGRAM

        cls.old_fixture = Projection
        cls.old_fixture.setUpClass()

    @classmethod
    def tearDownClass(cls):
        cls.old_fixture.tearDownClass()

    def test_real_old_states_are_currently_qualified_without_rewriting_history(self):
        fixture = self.old_fixture()
        fixture.setUp()
        self.addCleanup(fixture.tearDown)
        owner = fixture.owner
        generator = StateStore()
        generator.create_session("inputs", owner)
        handle = generator.put_source("inputs", owner, "records", SOURCE)
        question = "Which qualified commitment evidence changes the declared relationship model?"
        candidates = {
            mode: propose(
                generator.snapshot("inputs", owner, (handle,)), question, mode
            )
            for mode in ("not-fulfilled", "fulfilled", "unknown")
        }
        for schema in (3, 4):
            source, metadata, process = fixture.old(schema, "old-" + str(schema))
            old = []
            for mode, candidate in candidates.items():
                for seam in (
                    None,
                    "return_persisted",
                    "execution_computed",
                    "execution_effects_committed",
                ):
                    key = mode + "-" + str(seam)
                    row = fixture.command(
                        process,
                        action="run",
                        id=key,
                        question=question,
                        text=SOURCE,
                        candidate=candidate,
                        seam=seam,
                    )
                    self.assertTrue(row["ok"], row)
                    self.assertEqual(row["attempts"], 1)
                    if seam is None:
                        result = codec.loads(row["result"].encode())
                        self.assertEqual(result.status, "COMPLETED", result.diagnostics)
                    old.append((mode, seam, row))
            target = RevisionCutover.upgrade(
                source, fixture.root / ("new-" + str(schema)), owner
            )
            store = target.open_store()
            try:
                for mode, seam, row in old:
                    with self.subTest(schema=schema, mode=mode, seam=seam):
                        request = codec.loads(row["request"].encode())
                        before = {
                            r["result_id"]: dict(r)
                            for r in store._db.execute("SELECT * FROM inferences")
                        }
                        task = dict(
                            store._db.execute(
                                "SELECT * FROM tasks WHERE request_id=?",
                                (request.request_id,),
                            ).fetchone()
                        )
                        if seam:
                            RecoveryManager(store).resume_execution(
                                request, expected_owner_id=metadata["owner_id"]
                            )
                        port = OfflineModelPort("NO_RESEND")
                        client = HCL(
                            store, principal=owner, gateway=ModelGateway(store, port)
                        )
                        result = client.run_sync(request)
                        if mode == "unknown" and seam != "return_persisted":
                            self.assertFalse(result.answer or result.claim_records)
                            self.assertIn(
                                "RELATIONSHIP_RESULT_MISMATCH",
                                [d.code for d in result.diagnostics],
                            )
                        else:
                            self.assertEqual(
                                result.status,
                                "PARTIAL" if mode == "unknown" else "COMPLETED",
                                result.diagnostics,
                            )
                        self.assertEqual(result.usage["mock_calls"], 1)
                        self.assertEqual(port.attempts, 0)
                        # A fresh connection and stream must apply the same
                        # eligibility; completed historical bytes stay intact.
                        store.close()
                        store = target.open_store()
                        replay_port = OfflineModelPort("NO_RESEND")
                        replay_client = HCL(
                            store,
                            principal=owner,
                            gateway=ModelGateway(store, replay_port),
                        )

                        async def collect():
                            return [
                                event async for event in replay_client.stream(request)
                            ]

                        replay = asyncio.run(collect())[-1].result
                        self.assertEqual(
                            (
                                replay.status,
                                replay.answer,
                                replay.claim_records,
                                dict(replay.usage),
                            ),
                            (
                                result.status,
                                result.answer,
                                result.claim_records,
                                dict(result.usage),
                            ),
                        )
                        self.assertEqual(replay_port.attempts, 0)
                        for rid, record in before.items():
                            self.assertEqual(
                                dict(
                                    store._db.execute(
                                        "SELECT * FROM inferences WHERE result_id=?",
                                        (rid,),
                                    ).fetchone()
                                ),
                                record,
                            )
                        for digest, body in row["objects"].items():
                            self.assertEqual(
                                (store.object_root / digest).read_text(), body
                            )
                        if seam is None:
                            self.assertEqual(
                                dict(
                                    store._db.execute(
                                        "SELECT * FROM tasks WHERE request_id=?",
                                        (request.request_id,),
                                    ).fetchone()
                                ),
                                task,
                            )
                            self.assertEqual(
                                codec.dumps(
                                    store._get_object(task["result_hash"])
                                ).decode(),
                                row["result"],
                            )
                old_request = codec.loads(
                    next(
                        row["request"]
                        for mode, seam, row in old
                        if mode == "unknown" and seam is None
                    ).encode()
                )
                fresh_request = replace(
                    old_request, request_id="fresh-qualified-request"
                )
                port = OfflineModelPort(json.dumps(candidates["unknown"]))
                fresh = HCL(
                    store, principal=owner, gateway=ModelGateway(store, port)
                ).run_sync(fresh_request)
                self.assertEqual(fresh.status, "PARTIAL", fresh.diagnostics)
                self.assertEqual(port.attempts, 1)
                actual = next(
                    i
                    for i in store.inferences(metadata["session"], owner)
                    if i.result_id in fresh.execution_receipt["result_ids"]
                )
                history = actual.values["models"][0]["relationships"][0]["history"][0]
                self.assertEqual(history["qualification"], "UNRESOLVED")
                self.assertEqual(history["weights"]["supportive"], "1/2")
                store.set_readers(metadata["session"], owner, "records", {"other"})
                port = OfflineModelPort("NO_RESEND")
                denied = HCL(
                    store, principal=owner, gateway=ModelGateway(store, port)
                ).run_sync(fresh_request)
                self.assertEqual(denied.status, "DENIED")
                self.assertFalse(denied.answer or denied.claim_records)
                self.assertEqual(port.attempts, 0)
                self.assertFalse(fixture.command(process, action="write")["ok"])
            finally:
                store.close()
