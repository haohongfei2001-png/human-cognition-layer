"""Preserve real S4 argument checkpoints across exact side-copy migration."""

import json
from unittest.mock import patch
from hcl import HCL
from hcl.kernel.types import HCLFailure
from hcl.memory import codec
from hcl.memory.migrations.revision_upgrade import (
    RevisionCutover,
    S4_ARGUMENT_CODE_HASH,
)
from hcl.models.gateway import OfflineModelPort, ModelGateway
from hcl.operators.local_model import LocalModelOperator
from hcl.runtime.recovery import RecoveryManager
from tests import test_unified_s4_upgrade as previous

ARGUMENT_PROGRAM = r"""
argument_requests={}
if schema in (3,4):
 a_handle=store.put_source(session,owner,'argument-source','There is an a-report. Under the proposed rule, a supports b.')
 a_question='Is the b argument accepted under the proposed rule?'
 a_segments=segment_snapshot(store.snapshot(session,owner,(a_handle,)),a_question)
 a_sources=[s.segment_id for s in a_segments if s.kind=='SOURCE']; a_queries=[s.segment_id for s in a_segments if s.kind=='QUESTION']
 a_model=dict(id='argument',source_id='argument-source',frame_kind='HYPOTHETICAL',assumptions=[],active_assumptions=[],unmodeled_segments=[],
  literals=[dict(id=k,atom=k,negative=False,kind='CLAIM',segment_ids=a_sources) for k in ('a','b')],
  premises=[dict(id='report',literal='a',ordinary=False,assumptions=[],segment_ids=a_sources)],
  rules=[dict(id='inference',premises=['a'],conclusion='b',strict=False,assumptions=[],segment_ids=a_sources)],priorities=[],
  queries=[dict(id='query',literal='b',preferred=False,critical_candidates=[],segment_ids=a_queries)])
 a_candidate=dict(schema='hcl-argument-candidates-1',models=[a_model])
 for a_name,a_seam in [('completed',None),('returned','return_persisted'),('unknown','send_started'),('computed','execution_computed'),('committed','execution_effects_committed')]:
  a_request=TaskRequest('argument-'+a_name,a_question,(a_handle,),session,owner,budget=ExecutionBudget(max_mock_calls=4,max_output_bytes=65536,max_total_output_bytes=524288),issue=ExecutionIssue('root',goals=(Issue('argument-'+a_name,'argument.evaluate'),)))
  a_port=OfflineModelPort(json.dumps(a_candidate));a_client=HCL(store,principal=owner,gateway=ModelGateway(store,a_port));a_crashed=False
  def stop_argument(stage):
   global a_crashed
   if stage==a_seam and not a_crashed:a_crashed=True;raise GraphCrash()
  try:
   with patch.object(store,'_checkpoint',stop_argument):a_result=a_client.run_sync(a_request)
  except GraphCrash:pass
  if a_seam:assert a_crashed,a_name
  else:assert a_result.status=='COMPLETED',a_result.diagnostics
  argument_requests[a_name]=dict(request=codec.dumps(a_request).decode(),attempts=a_port.attempts)
"""
INSERTION = previous.previous.INSERTION
assert previous.OLD_PROGRAM.count(INSERTION) == 1
OLD_PROGRAM = previous.OLD_PROGRAM.replace(
    INSERTION, ARGUMENT_PROGRAM + "\n" + INSERTION
).replace(
    "'mental_requests':mental_requests",
    "'mental_requests':mental_requests,'argument_requests':argument_requests",
)


class S4RuntimeUpgradeTests(previous.S3RuntimeUpgradeTests):
    baseline = "b24c826a10e299ff9c3d713dc0dcdd0ff2d65dd3"
    code_hash = S4_ARGUMENT_CODE_HASH
    file_count = 176

    def test_real_argument_completed_returned_unknown_and_checkpoint_recovery(self):
        self.old_program = OLD_PROGRAM
        for schema in (3, 4):
            with self.subTest(schema=schema):
                source, old, process = self.old(schema, str(schema))
                store = RevisionCutover.upgrade(
                    source, self.root / ("new" + str(schema)), self.owner
                ).open_store()
                try:
                    for name, metadata in old["argument_requests"].items():
                        request = codec.loads(metadata["request"].encode())
                        self.assertEqual(
                            codec.dumps(request).decode(), metadata["request"]
                        )
                        port = OfflineModelPort()
                        client = HCL(
                            store,
                            principal=self.owner,
                            gateway=ModelGateway(store, port),
                        )
                        if name == "completed":
                            result = client.run_sync(request)
                            self.assertTrue(result.execution_receipt["replayed"])
                        elif name == "unknown":
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
                        else:
                            RecoveryManager(store).resume_execution(
                                request, expected_owner_id=old["owner_id"]
                            )
                            if name in ("computed", "committed"):
                                with patch.object(
                                    LocalModelOperator,
                                    "run",
                                    side_effect=AssertionError("no recomputation"),
                                ):
                                    result = client.run_sync(request)
                            else:
                                result = client.run_sync(request)
                        if name != "unknown":
                            self.assertEqual(
                                result.status, "COMPLETED", result.diagnostics
                            )
                            self.assertIn("grounded accepted=True", result.answer)
                            self.assertIn("finite acyclic proofs", result.answer)
                            self.assertEqual(result.usage["mock_calls"], 1)
                        self.assertEqual(port.attempts, 0)
                    self.assertFalse(self.command(process, action="write")["ok"])
                    store.set_readers(
                        old["session"], self.owner, "argument-source", {"bob"}
                    )
                    request = codec.loads(
                        old["argument_requests"]["completed"]["request"].encode()
                    )
                    denied = HCL(store, principal=self.owner).run_sync(request)
                    self.assertEqual(denied.status, "DENIED")
                    self.assertFalse(denied.answer)
                finally:
                    store.close()
