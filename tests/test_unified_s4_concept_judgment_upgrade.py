"""Real shipped 217-file predecessor creates old M12/M13/M14 states unchanged."""
import inspect
from unittest.mock import patch

from hcl import HCL
from hcl.kernel.types import HCLFailure
from hcl.memory import codec
from hcl.memory.migrations.revision_upgrade import RevisionCutover, CONCEPT_JUDGMENT_PREDECESSOR_CODE_HASH
from hcl.models.gateway import ModelGateway, OfflineModelPort
from hcl.operators.local_model import LocalModelOperator
from hcl.runtime.answer import AnswerAssembler
from hcl.runtime.recovery import RecoveryManager
from scripts import witness_unified_judgment as judgment
from tests import test_unified_s4_judgment_upgrade as previous

JUDGMENT_PROGRAM = (inspect.getsource(judgment.atom)
    + inspect.getsource(judgment.propose).replace("def propose(", "def propose_judgment(")
    + "SCENE=" + repr(judgment.SCENE) + "\nPRINCIPLES=" + repr(judgment.PRINCIPLES) + "\n"
    + r'''
judgment_handles=(store.put_source(session,owner,'scene',SCENE),store.put_source(session,owner,'principles',PRINCIPLES))
for name,seam in [('completed',None),('returned','return_persisted'),('unknown','send_started'),('computed','execution_computed'),('committed','execution_effects_committed')]:
 key='judgment-'+name
 request=TaskRequest(key,'How should Ning act under these conditional principles?',judgment_handles,session,owner,
  budget=ExecutionBudget(max_mock_calls=1,max_feedback=0,max_local_evaluations=100000,max_request_bytes=1048576,max_context_tokens=1048576,max_output_bytes=1048576,max_total_output_bytes=8000000,max_visible_output_tokens=1048576),
  issue=ExecutionIssue('root',goals=(Issue(key,'judgment.evaluate'),)))
 snap=store.snapshot(session,owner,judgment_handles)
 candidate=propose_judgment(snap,request.question)
 port=OfflineModelPort(json.dumps(candidate));client=HCL(store,principal=owner,gateway=ModelGateway(store,port));crashed=False
 def stop_judgment(stage):
  global crashed
  if stage==seam and not crashed:crashed=True;raise DomainCrash()
 try:
  with patch.object(store,'_checkpoint',stop_judgment):result=client.run_sync(request)
 except DomainCrash:pass
 if seam:assert crashed,key
 else:assert result.status=='PARTIAL',(key,result.diagnostics)
 domain_requests[key]=dict(request=codec.dumps(request).decode(),expected='PARTIAL',owner_id=store.owner_id)
''')
OLD_PROGRAM = previous.OLD_PROGRAM.replace(previous.INSERTION, JUDGMENT_PROGRAM + "\n" + previous.INSERTION)


class ConceptJudgmentPredecessorTests(previous.JudgmentPredecessorUpgradeTests):
    baseline = "96984da44e132b6b7f1184436755c6641df4584b"
    code_hash = CONCEPT_JUDGMENT_PREDECESSOR_CODE_HASH
    file_count = 217

    def test_old_m12_m13_m14_all_checkpoints_and_exact_v1_claims(self):
        f=self.fixture();f.old_program=OLD_PROGRAM
        for schema in (3,4):
            source,old,process=f.old(schema,'concept-predecessor'+str(schema))
            store=RevisionCutover.upgrade(source,f.root/('concept-successor'+str(schema)),f.owner).open_store()
            self.addCleanup(store.close)
            for name,metadata in old['domain_requests'].items():
                with self.subTest(schema=schema,checkpoint=name):
                    request=codec.loads(metadata['request'].encode())
                    port=OfflineModelPort('NO_NEW_SEND');client=HCL(store,principal=f.owner,gateway=ModelGateway(store,port))
                    if name.endswith('unknown'):
                        with self.assertRaises(HCLFailure):RecoveryManager(store).resume_execution(request,expected_owner_id=metadata['owner_id'])
                        result=client.run_sync(request)
                        self.assertIsNone(result.usage['mock_calls']);self.assertEqual(result.usage['held_mock_calls'],1)
                        self.assertFalse(result.answer)
                    else:
                        if name.endswith('completed'):
                            task=store._db.execute('SELECT * FROM tasks WHERE request_id=?',(request.request_id,)).fetchone()
                            original=store._get_object(task['result_hash'])
                        else:RecoveryManager(store).resume_execution(request,expected_owner_id=metadata['owner_id'])
                        if name.endswith('returned'):result=client.run_sync(request)
                        else:
                            with patch.object(LocalModelOperator,'run',side_effect=AssertionError('accepted effect cannot recompute')):
                                result=client.run_sync(request)
                        self.assertEqual(result.status,metadata['expected'],result.diagnostics)
                        if name.endswith('completed'):
                            self.assertEqual((result.answer,result.claim_records),(original.answer,original.claim_records))
                            self.assertEqual(store._get_object(task['result_hash']),original)
                        for inference in store.inferences(old['session'],f.owner):
                            if inference.result_id in result.execution_receipt['result_ids']:
                                AnswerAssembler().compact_claim(inference)
                    self.assertEqual(port.attempts,0)
            self.assertFalse(f.command(process,action='write')['ok'])
            store.set_readers(old['session'],f.owner,'principles',{'bob'})
            for name,metadata in old['domain_requests'].items():
                if name.startswith('judgment-'):
                    denied=HCL(store,principal=f.owner).run_sync(codec.loads(metadata['request'].encode()))
                    self.assertEqual(denied.status,'DENIED');self.assertFalse(denied.answer)
