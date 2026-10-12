"""Actual 189/190-file M09 executions, then current retrieval/continued execution.

Only exact Python runtime members are projected; no providers, grants, evaluation
packages or sealed content are copied. The old baseline retains the historical 189-file PR436 runtime; the qualified
190-file baseline is the verified identical-tree main merge of the repaired PR.
"""
import inspect
from unittest.mock import patch
from hcl import HCL, RetrievalQuery
from hcl.kernel.types import HCLFailure
from hcl.memory import codec
from hcl.memory.migrations.revision_upgrade import RevisionCutover, M09_RELATIONSHIP_CODE_HASH
from hcl.memory.query_store import QueryStore
from hcl.models.gateway import OfflineModelPort, ModelGateway
from hcl.operators.local_model import LocalModelOperator
from hcl.runtime.recovery import RecoveryManager
from scripts import witness_unified_relationship as witness
from tests import test_unified_s3_relationship_upgrade as previous

RELATIONSHIP_PROGRAM = (
    "affect_candidate=affect_propose\n"
    + inspect.getsource(witness.add_relationships) + "\n"
    + inspect.getsource(witness.propose).replace("def propose(", "def relationship_propose(")
    + r'''
relationship_requests={}
if schema in (3,4):
 r_handle=store.put_source(session,owner,'relationships',"Across home and work B changes choices as the passage changes. Safety and duty may have stable priorities. Directed ability, goodwill and reliability differ. Source-declared likelihood and independence assumptions are hypotheses. Role obligations and source reports may conflict.")
 r_question='Compare these declared longitudinal mechanisms.'
 for r_mode in ('stable','relationship','null_prior','budget'):
  r_candidate=relationship_propose(store.snapshot(session,owner,(r_handle,)),r_question,r_mode)
  r_candidate['models'][0]['mental']['source_id']='relationships'
  for actor in r_candidate['models'][0]['mental']['agents']:actor['source_id']='relationships'
  for r_name,r_seam in [('completed',None),('returned','return_persisted'),('unknown','send_started'),('computed','execution_computed'),('committed','execution_effects_committed')]:
   r_key=r_mode+'-'+r_name
   r_request=TaskRequest('relationship-'+r_key,r_question,(r_handle,),session,owner,
    budget=ExecutionBudget(max_mock_calls=1,max_feedback=0,max_local_evaluations=1 if r_mode=='budget' else 16000,max_request_bytes=1048576,max_output_bytes=1048576,max_total_output_bytes=16777216,max_context_tokens=1048576,max_visible_output_tokens=1048576),
    issue=ExecutionIssue('root',goals=(Issue(r_key,'relationship.evaluate'),)))
   r_port=OfflineModelPort(json.dumps(r_candidate));r_client=HCL(store,principal=owner,gateway=ModelGateway(store,r_port));r_crashed=False
   def stop_relationship(stage):
    global r_crashed
    if stage==r_seam and not r_crashed:r_crashed=True;raise GraphCrash()
   try:
    with patch.object(store,'_checkpoint',stop_relationship):r_result=r_client.run_sync(r_request)
   except GraphCrash:pass
   if r_seam:assert r_crashed,r_key
   else:assert r_result.status==('PARTIAL' if r_mode=='budget' else 'COMPLETED'),r_result.diagnostics
   relationship_requests[r_key]=dict(request=codec.dumps(r_request).decode(),attempts=r_port.attempts,expected='PARTIAL' if r_mode=='budget' else 'COMPLETED')
'''
)
INSERTION = previous.INSERTION
assert previous.OLD_PROGRAM.count(INSERTION) == 1
OLD_PROGRAM=previous.OLD_PROGRAM.replace(INSERTION,RELATIONSHIP_PROGRAM+'\n'+INSERTION).replace(
    "'affect_requests':affect_requests", "'affect_requests':affect_requests,'relationship_requests':relationship_requests")


class M09RuntimeUpgradeTests(previous.M08RuntimeUpgradeTests):
    baseline="52c3ba6c54efee2b8196edc3c5360e915d695242"
    code_hash=M09_RELATIONSHIP_CODE_HASH
    file_count=189

    def test_real_relationship_states_and_retrieval_of_old_originals(self):
        self.old_program=OLD_PROGRAM
        for schema in (3,4):
            source,old,process=self.old(schema,str(schema))
            store=RevisionCutover.upgrade(source,self.root/('new'+str(schema)),self.owner).open_store()
            try:
                for name,metadata in old['relationship_requests'].items():
                    with self.subTest(schema=schema,name=name):
                        request=codec.loads(metadata['request'].encode())
                        port=OfflineModelPort('NO_NEW_SEND')
                        client=HCL(store,principal=self.owner,gateway=ModelGateway(store,port))
                        if name.endswith('unknown'):
                            with self.assertRaises(HCLFailure) as caught:
                                RecoveryManager(store).resume_execution(request,expected_owner_id=old['owner_id'])
                            self.assertEqual(caught.exception.diagnostic.code,'UNKNOWN_SEND_NO_RESUME')
                            result=client.run_sync(request)
                            self.assertIsNone(result.usage['mock_calls'])
                            self.assertEqual(result.usage['held_mock_calls'],1)
                            self.assertFalse(result.answer or result.claim_records)
                        else:
                            cached=name.endswith('completed')
                            if cached:
                                task=store._db.execute('SELECT * FROM tasks WHERE request_id=?',(request.request_id,)).fetchone()
                                original=store._get_object(task['result_hash'])
                            else:
                                RecoveryManager(store).resume_execution(request,expected_owner_id=old['owner_id'])
                            if name.endswith('returned'):
                                result=client.run_sync(request)
                            else:
                                with patch.object(LocalModelOperator,'run',side_effect=AssertionError('no recomputation')):
                                    result=client.run_sync(request)
                            self.assertEqual(result.status,metadata['expected'],result.diagnostics)
                            self.assertEqual(result.usage['mock_calls'],1)
                            if cached:
                                self.assertEqual((result.answer,result.claim_records),(original.answer,original.claim_records))
                                self.assertEqual(store._get_object(task['result_hash']),original)
                        self.assertEqual(port.attempts,0)
                query=RetrievalQuery(dict(support='ability reliability',challenge='conflict',alternative='stable priorities'),source_scope=('relationships',))
                snapshot=QueryStore(store).search(old['session'],self.owner,query)
                self.assertTrue(snapshot.query_views['0']['packet']['segments'])
                self.assertFalse(self.command(process,action='write')['ok'])
                store.set_readers(old['session'],self.owner,'relationships',{'bob'})
                with self.assertRaises(HCLFailure):
                    QueryStore(store).search(old['session'],self.owner,query)
            finally:
                store.close()


class QualifiedM09RuntimeUpgradeTests(M09RuntimeUpgradeTests):
    """Repeat the full controlled-boundary suite on the real qualified M09 head.

    Keep the old 189-file suite intact: both exact runtime identities can be
    migrated, but only current eligibility determines whether results deliver.
    """
    baseline = "d30e8cbba5e51d7c2b8191c21cb8969370880408"
    from hcl.memory.migrations.revision_upgrade import M09_QUALIFIED_CODE_HASH as code_hash
    file_count = 190
