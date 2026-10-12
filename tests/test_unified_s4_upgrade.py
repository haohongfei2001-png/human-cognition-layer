"""Real published 173-file S3 runtime migration, including cognitive checkpoints."""

import json
from unittest.mock import patch
from hcl import HCL
from hcl.kernel.types import HCLFailure
from hcl.memory import codec
from hcl.memory.migrations.revision_upgrade import RevisionCutover, S3_FINITE_CODE_HASH
from hcl.models.gateway import OfflineModelPort, ModelGateway
from hcl.operators.local_model import LocalModelOperator
from hcl.runtime.recovery import RecoveryManager
from tests import test_unified_s3_upgrade as previous

MENTAL_PROGRAM = r"""
mental_requests={}
if schema in (3,4):
 m_handle=store.put_source(session,owner,'mental-source','A and B see the open passage. A leaves. B closes it.')
 m_question='What does A believe about the passage?'
 m_segments=segment_snapshot(store.snapshot(session,owner,(m_handle,)),m_question)
 m_sources=[s.segment_id for s in m_segments if s.kind=='SOURCE']
 m_questions=[s.segment_id for s in m_segments if s.kind=='QUESTION']
 m_model=dict(id='passage',source_id='mental-source',frame_kind='SOURCE_DISCOURSE',assumptions=['persistence'],
  active_assumptions=['persistence','visibility'],unmodeled_segments=[],
  agents=[dict(id=key,label=key,source_id='mental-source',segment_ids=m_sources) for key in ('A','B')],
  variables=[dict(id='open',initial=True,observed_by=['A','B'],segment_ids=m_sources)],
  events=[dict(id='closed',at=1,kind='change',effects={'open':False},seen_by=['B'],received_by=[],understood_by=[],trusted_by=[],assumptions=['visibility'],segment_ids=m_sources)],
  queries=[dict(id='belief-A',at=1,formula=dict(op='believes',agent='A',arg=dict(op='atom',name='open')),segment_ids=m_questions)],plans=[],causal=[])
 m_candidate=dict(schema='hcl-mental-scene-candidates-1',models=[m_model])
 for m_name,m_seam in [('completed',None),('returned','return_persisted'),('unknown','send_started'),('computed','execution_computed'),('committed','execution_effects_committed')]:
  m_request=TaskRequest('mental-'+m_name,m_question,(m_handle,),session,owner,budget=ExecutionBudget(max_mock_calls=4,max_output_bytes=65536,max_total_output_bytes=524288),issue=ExecutionIssue('root',goals=(Issue('mental-'+m_name,'mental.simulate'),)))
  m_port=OfflineModelPort(json.dumps(m_candidate));m_client=HCL(store,principal=owner,gateway=ModelGateway(store,m_port))
  m_crashed=False
  def stop_mental(stage):
   global m_crashed
   if stage==m_seam and not m_crashed:m_crashed=True;raise GraphCrash()
  try:
   with patch.object(store,'_checkpoint',stop_mental):m_result=m_client.run_sync(m_request)
  except GraphCrash:pass
  if m_seam:assert m_crashed,m_name
  else:assert m_result.status=='COMPLETED',m_result.diagnostics
  mental_requests[m_name]=dict(request=codec.dumps(m_request).decode(),attempts=m_port.attempts)
"""
assert previous.OLD_PROGRAM.count(previous.INSERTION) == 1
OLD_PROGRAM = previous.OLD_PROGRAM.replace(
    previous.INSERTION, MENTAL_PROGRAM + "\n" + previous.INSERTION
).replace(
    "'graphs':graphs,'shapes':shapes",
    "'graphs':graphs,'shapes':shapes,'mental_requests':mental_requests",
)


class S3RuntimeUpgradeTests(previous.S23RuntimeUpgradeTests):
    baseline = "8e25a2c91dba20aea2f0128069b9ca7df69a724b"
    code_hash = S3_FINITE_CODE_HASH
    file_count = 173

    def test_real_mental_model_replay_and_each_recovery_without_new_send(self):
        self.old_program = OLD_PROGRAM
        for schema in (3, 4):
            with self.subTest(schema=schema):
                source, old, process = self.old(schema, str(schema))
                target = RevisionCutover.upgrade(
                    source, self.root / ("new" + str(schema)), self.owner
                )
                store = target.open_store()
                try:
                    for name, metadata in old["mental_requests"].items():
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
                            self.assertFalse(result.answer)
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
                            self.assertIn("possible=(True,)", result.answer)
                            self.assertEqual(result.usage["mock_calls"], 1)
                        self.assertEqual(port.attempts, 0)
                    self.assertFalse(self.command(process, action="write")["ok"])
                    store.set_readers(
                        old["session"], self.owner, "mental-source", {"bob"}
                    )
                    completed = codec.loads(
                        old["mental_requests"]["completed"]["request"].encode()
                    )
                    denied = HCL(store, principal=self.owner).run_sync(completed)
                    self.assertEqual(denied.status, "DENIED")
                    self.assertFalse(denied.answer)
                finally:
                    store.close()
