"""Execute the exact published M08 runtime before controlled current migration."""

import inspect
from unittest.mock import patch
from hcl import HCL
from hcl.kernel.types import HCLFailure
from hcl.memory import codec
from hcl.memory.migrations.revision_upgrade import (
    RevisionCutover,
    M08_AFFECT_CODE_HASH,
)
from hcl.models.gateway import OfflineModelPort, ModelGateway
from hcl.operators.local_model import LocalModelOperator
from hcl.runtime.recovery import RecoveryManager
from scripts import witness_unified_affect as witness
from tests import test_unified_s3_affect_upgrade as previous

# Current fixture supplies explicit synthetic inputs to an actual old runtime.
# Only the historical 185-file Python runtime allowlist is materialized.
AFFECT_PROGRAM = (
    "from copy import deepcopy\nmental_candidate=propose\n"
    + inspect.getsource(witness.propose).replace("def propose(", "def affect_propose(")
    + r"""
affect_requests={}
if schema in (3,4):
 a_handle=store.put_source(session,owner,'appraisals',"A and B know the passage is safe. B sees closure. Conditional safety and duty goals conflict; candidate coping reweights goals. A later report may reopen the passage or revised goal consequences may change appraisal.")
 a_question='What follows under the proposed appraisal models?'
 for a_mode in ('mixed','unknown','informed','goal_revision'):
  a_candidate=affect_propose(store.snapshot(session,owner,(a_handle,)),a_question,a_mode)
  a_candidate['models'][0]['mental']['source_id']='appraisals'
  for a_actor in a_candidate['models'][0]['mental']['agents']:a_actor['source_id']='appraisals'
  for a_name,a_seam in [('completed',None),('returned','return_persisted'),('unknown','send_started'),('computed','execution_computed'),('committed','execution_effects_committed')]:
   a_key=a_mode+'-'+a_name
   a_request=TaskRequest('affect-'+a_key,a_question,(a_handle,),session,owner,
    budget=ExecutionBudget(max_mock_calls=1,max_local_evaluations=4096,max_request_bytes=1048576,max_output_bytes=1048576,max_total_output_bytes=16777216,max_context_tokens=1048576,max_visible_output_tokens=1048576),
    issue=ExecutionIssue('root',goals=(Issue(a_key,'affect.evaluate'),)))
   a_port=OfflineModelPort(json.dumps(a_candidate));a_client=HCL(store,principal=owner,gateway=ModelGateway(store,a_port));a_crashed=False
   def stop_affect(stage):
    global a_crashed
    if stage==a_seam and not a_crashed:a_crashed=True;raise GraphCrash()
   try:
    with patch.object(store,'_checkpoint',stop_affect):a_result=a_client.run_sync(a_request)
   except GraphCrash:pass
   if a_seam:assert a_crashed,a_key
   else:assert a_result.status==('PARTIAL' if a_mode=='unknown' else 'COMPLETED'),a_result.diagnostics
   affect_requests[a_key]=dict(request=codec.dumps(a_request).decode(),attempts=a_port.attempts,expected='PARTIAL' if a_mode=='unknown' else 'COMPLETED')
"""
)
INSERTION = previous.INSERTION
assert previous.OLD_PROGRAM.count(INSERTION) == 1
OLD_PROGRAM = previous.OLD_PROGRAM.replace(
    INSERTION, AFFECT_PROGRAM + "\n" + INSERTION
).replace(
    "'interaction_requests':interaction_requests",
    "'interaction_requests':interaction_requests,'affect_requests':affect_requests",
)


class M08RuntimeUpgradeTests(previous.M07RuntimeUpgradeTests):
    baseline = "0c7e9b866bc2aa82cc98420af82458059ec47f70"
    code_hash = M08_AFFECT_CODE_HASH
    file_count = 185

    def test_real_affect_completed_partial_and_checkpoint_recovery(self):
        self.old_program = OLD_PROGRAM
        for schema in (3, 4):
            source, old, process = self.old(schema, str(schema))
            store = RevisionCutover.upgrade(
                source, self.root / ("new" + str(schema)), self.owner
            ).open_store()
            try:
                for name, metadata in old["affect_requests"].items():
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
                            if name.startswith("unknown-"):
                                self.assertIn(
                                    "COPING_PROBABILITY_UNSPECIFIED", result.answer
                                )
                            if name.startswith("goal_revision"):
                                self.assertIn("REVISED", result.answer)
                        self.assertEqual(port.attempts, 0)
                self.assertFalse(self.command(process, action="write")["ok"])
                store.set_readers(old["session"], self.owner, "appraisals", {"bob"})
                request = codec.loads(
                    old["affect_requests"]["mixed-completed"]["request"].encode()
                )
                result = HCL(store, principal=self.owner).run_sync(request)
                self.assertEqual(result.status, "DENIED")
                self.assertFalse(result.answer or result.claim_records)
            finally:
                store.close()
