"""Execute the exact published M07 runtime before controlled current migration."""

import inspect
from unittest.mock import patch
from hcl import HCL
from hcl.kernel.types import HCLFailure
from hcl.memory import codec
from hcl.memory.migrations.revision_upgrade import (
    RevisionCutover,
    M07_INTERACTION_CODE_HASH,
)
from hcl.models.gateway import OfflineModelPort, ModelGateway
from hcl.operators.local_model import LocalModelOperator
from hcl.runtime.recovery import RecoveryManager
from scripts import witness_unified_interaction as witness
from tests import test_unified_s3_interaction_upgrade as previous

# Current fixture supplies explicit synthetic inputs to an actual old runtime.
# Only the historical 182-file Python runtime allowlist is materialized.
INTERACTION_PROGRAM = (
    inspect.getsource(witness.propose)
    + r"""
interaction_requests={}
if schema in (3,4):
 i_handle=store.put_source(session,owner,'records',"A knows danger, B is uninformed. Proposed signal meanings, costs and utilities are conditional inputs. A offers a task; B interprets and A confirms the same terms.")
 i_question='What follows under the proposed interaction models?'
 for i_mode in ('strategic','prior_missing','acknowledgments'):
  i_candidate=propose(store.snapshot(session,owner,(i_handle,)),i_question,i_mode)
  for i_name,i_seam in [('completed',None),('returned','return_persisted'),('unknown','send_started'),('computed','execution_computed'),('committed','execution_effects_committed')]:
   i_key=i_mode+'-'+i_name
   i_request=TaskRequest('interaction-'+i_key,i_question,(i_handle,),session,owner,
    budget=ExecutionBudget(max_mock_calls=1,max_local_evaluations=4096,max_request_bytes=1048576,max_output_bytes=1048576,max_total_output_bytes=16777216,max_context_tokens=1048576,max_visible_output_tokens=1048576),
    issue=ExecutionIssue('root',goals=(Issue(i_key,'interaction.evaluate'),)))
   i_port=OfflineModelPort(json.dumps(i_candidate));i_client=HCL(store,principal=owner,gateway=ModelGateway(store,i_port));i_crashed=False
   def stop_interaction(stage):
    global i_crashed
    if stage==i_seam and not i_crashed:i_crashed=True;raise GraphCrash()
   try:
    with patch.object(store,'_checkpoint',stop_interaction):i_result=i_client.run_sync(i_request)
   except GraphCrash:pass
   if i_seam:assert i_crashed,i_key
   else:assert i_result.status==('PARTIAL' if i_mode=='prior_missing' else 'COMPLETED'),i_result.diagnostics
   interaction_requests[i_key]=dict(request=codec.dumps(i_request).decode(),attempts=i_port.attempts,expected='PARTIAL' if i_mode=='prior_missing' else 'COMPLETED')
"""
)
INSERTION = previous.previous.INSERTION
assert previous.OLD_PROGRAM.count(INSERTION) == 1
OLD_PROGRAM = previous.OLD_PROGRAM.replace(
    INSERTION, INTERACTION_PROGRAM + "\n" + INSERTION
).replace(
    "'discovery_requests':discovery_requests",
    "'discovery_requests':discovery_requests,'interaction_requests':interaction_requests",
)


class M07RuntimeUpgradeTests(previous.QualifiedM04UpgradeTests):
    baseline = "20f95f7110ddc5d24b597123e7892d7bbad35d7b"
    code_hash = M07_INTERACTION_CODE_HASH
    file_count = 182

    def test_real_interaction_completed_partial_and_checkpoint_recovery(self):
        self.old_program = OLD_PROGRAM
        for schema in (3, 4):
            source, old, process = self.old(schema, str(schema))
            store = RevisionCutover.upgrade(
                source, self.root / ("new" + str(schema)), self.owner
            ).open_store()
            try:
                for name, metadata in old["interaction_requests"].items():
                    with self.subTest(schema=schema, name=name):
                        request = codec.loads(metadata["request"].encode())
                        port = OfflineModelPort("NO_NEW_SEND")
                        client = HCL(
                            store,
                            principal=self.owner,
                            gateway=ModelGateway(store, port),
                        )
                        if name.endswith("unknown"):
                            with self.assertRaises(HCLFailure) as caught:
                                RecoveryManager(store).resume_execution(
                                    request, expected_owner_id=old["owner_id"]
                                )
                            self.assertEqual(
                                caught.exception.diagnostic.code,
                                "UNKNOWN_SEND_NO_RESUME",
                            )
                            result = client.run_sync(request)
                            self.assertIsNone(result.usage["mock_calls"])
                            self.assertEqual(result.usage["held_mock_calls"], 1)
                            self.assertFalse(result.answer or result.claim_records)
                        else:
                            cached = name.endswith("completed")
                            if cached:
                                task = store._db.execute(
                                    "SELECT * FROM tasks WHERE request_id=?",
                                    (request.request_id,),
                                ).fetchone()
                                original = store._get_object(task["result_hash"])
                            else:
                                RecoveryManager(store).resume_execution(
                                    request, expected_owner_id=old["owner_id"]
                                )
                            if name.endswith("returned"):
                                result = client.run_sync(request)
                            else:
                                with patch.object(
                                    LocalModelOperator,
                                    "run",
                                    side_effect=AssertionError("no recomputation"),
                                ):
                                    result = client.run_sync(request)
                            self.assertEqual(
                                result.status, metadata["expected"], result.diagnostics
                            )
                            self.assertEqual(result.usage["mock_calls"], 1)
                            if cached:
                                self.assertEqual(
                                    (result.answer, result.claim_records),
                                    (original.answer, original.claim_records),
                                )
                                self.assertEqual(
                                    store._get_object(task["result_hash"]), original
                                )
                            if name.startswith("acknowledgments"):
                                self.assertIn(
                                    "common knowledge is not established", result.answer
                                )
                            if name.startswith("prior_missing"):
                                self.assertIn("PRIOR", result.answer)
                        self.assertEqual(port.attempts, 0)
                self.assertFalse(self.command(process, action="write")["ok"])
                store.set_readers(old["session"], self.owner, "records", {"bob"})
                request = codec.loads(
                    old["interaction_requests"]["acknowledgments-completed"][
                        "request"
                    ].encode()
                )
                result = HCL(store, principal=self.owner).run_sync(request)
                self.assertEqual(result.status, "DENIED")
                self.assertFalse(result.answer or result.claim_records)
            finally:
                store.close()
