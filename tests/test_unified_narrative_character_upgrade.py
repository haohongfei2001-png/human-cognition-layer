"""Actual PR449 runtime produces old narrative claims and interrupted packets."""
import json
import subprocess
import unittest
from pathlib import Path
from hcl import HCL
from hcl.kernel.types import HCLFailure
from hcl.memory import codec
from hcl.memory.migrations.revision_upgrade import RevisionCutover, CHARACTER_ARC_PREDECESSOR_CODE_HASH
from hcl.models.gateway import ModelGateway, OfflineModelPort
from hcl.runtime.answer import AnswerAssembler
from hcl.runtime.recovery import RecoveryManager
from tests import test_unified_s23_upgrade as fixtures

BASELINE='04d23b02dcd3f0485dda4d5a0c6ee190ae3352a5'
TREE='0728463342d638af0904baf6fc2eed3714d6b1c9'
OLD_PROGRAM=r'''
import json,sys
from pathlib import Path
from dataclasses import replace
from unittest.mock import patch
from hcl import HCL,ExecutionBudget,ExecutionIssue
from hcl.kernel.types import Principal,TaskRequest,Issue
from hcl.memory import codec
from hcl.memory.store import StateStore
from hcl.memory.migrations.namespace import MigrationNamespace
from hcl.memory.migrations.types import LegacySnapshot,LegacySource
from hcl.memory.migrations.revision_upgrade import RevisionCutover
from hcl.memory.migrations.control import version_bundle
from hcl.models.gateway import ModelGateway,OfflineModelPort
from hcl.runtime.context import ContextCompiler
from hcl.runtime.answer import AnswerAssembler
root=Path(sys.argv[1]);schema=int(sys.argv[2]);owner=Principal('tenant','alice')
if schema==4:
 imported=MigrationNamespace.import_snapshot(root/'imported',LegacySnapshot((LegacySource('independent',1,'SYNTHETIC ORIGINAL'),)),namespace_id='legacy',owner=owner)
 session=imported.receipt(owner)['session_id'];store=RevisionCutover.upgrade(imported.path,root/'old4',owner).open_store()
else:
 store=StateStore.sqlite(root/'old.sqlite',revision=True);session='s';store.create_session(session,owner,{'bob'})
handle=store.put_source(session,owner,'book','She arrived. Earlier she left. Original synthetic witness.')
budget=ExecutionBudget(max_mock_calls=10,max_output_bytes=200000,max_visible_output_tokens=200000,max_total_output_bytes=1048576,max_request_bytes=12000,max_context_tokens=12000,max_steps=64)
base=TaskRequest('base','Compare story and presentation.',(handle,),session,owner,budget=budget,issue=ExecutionIssue('root',goals=(Issue('read','literature.analyze'),)))
snapshot=store.snapshot(session,owner,(handle,))
chunk=ContextCompiler().chunks(snapshot,base.question,'literature_compile',budget,OfflineModelPort().describe())[0]
refs=[s.segment_id for s in chunk.segments]
candidate=dict(schema='hcl-literature-fragment-1',assumptions=[],active_assumptions=[],frames=[],events=[],mentions=[],orders=[],queries=[],motifs=[dict(id='arrive',literal='arrived',segment_ids=refs)],variants=[],comparisons=[],analogies=[],unmodeled_segments=[])
class Crash(BaseException):pass
requests={}
for state,seam in [('completed',None),('returned','return_persisted'),('unknown','send_started'),('computed','execution_computed'),('committed','execution_effects_committed')]:
 request=replace(base,request_id=state,issue=ExecutionIssue('root',goals=(Issue(state,'literature.analyze'),)));result=None
 def stop(stage):
  if stage==seam:raise Crash()
 try:
  with patch.object(store,'_checkpoint',stop):result=HCL(store,principal=owner,gateway=ModelGateway(store,OfflineModelPort(json.dumps(candidate)))).run_sync(request)
 except Crash:pass
 task=dict(store._db.execute('SELECT * FROM tasks WHERE request_id=?',(state,)).fetchone())
 accepted=[]
 if state in ('computed','committed'):
  assert result is None, (state,result)
  checkpoint=store._get_object(task['result_hash'])
  for node in checkpoint.nodes.values():
   if node.get('operation')=='compute' and node.get('result') is not None:accepted.extend(node['result'].candidate_delta.new_inferences)
 elif result:
  assert result.status=='PARTIAL',result.diagnostics
  accepted=[r for r in store.inferences(session,owner) if r.result_id in result.execution_receipt['result_ids']]
 requests[state]=dict(request=codec.dumps(request).decode(),task=task,
  proofs={r.result_id:codec.dumps(r).decode() for r in accepted},
  claims={r.result_id:codec.dumps(AnswerAssembler()._claim(r)).decode() for r in accepted},
  result_claims=codec.dumps(result.claim_records).decode() if result else None,answer=result.answer if result else None)
print(json.dumps(dict(path=str(store.path),session=session,owner_id=store.owner_id,requests=requests,bundle=version_bundle(schema=schema))),flush=True)
for line in sys.stdin:
 command=json.loads(line)
 if command['action']=='close':break
 try:
  store.put_source(session,owner,'late','LATE SYNTHETIC')
  print(json.dumps(dict(ok=True)),flush=True)
 except Exception as error:print(json.dumps(dict(ok=False,error=type(error).__name__)),flush=True)
store.close()
'''


class CharacterPredecessorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        assert subprocess.check_output(['git','rev-parse',BASELINE+'^{tree}'],cwd=fixtures.ROOT,text=True).strip()==TREE
        class Frozen(fixtures.RuntimeUpgradeTests):
            baseline=BASELINE
            code_hash=CHARACTER_ARC_PREDECESSOR_CODE_HASH
            file_count=239
            old_program=OLD_PROGRAM
        cls.runtime=Frozen
        Frozen.setUpClass()

    @classmethod
    def tearDownClass(cls):cls.runtime.tearDownClass()

    def test_true_predecessor_all_seams_both_schemas_unchanged_and_zero_resends(self):
        for schema in (3,4):
            fixture=self.runtime();fixture.setUp()
            try:
                source,old,process=fixture.old(schema)
                target=RevisionCutover.upgrade(source,fixture.root/'new',fixture.owner)
                store=target.open_store()
                try:
                    self.assertFalse(fixture.command(process,action='write')['ok'])
                    for state,row in old['requests'].items():
                        request=codec.loads(row['request'].encode())
                        port=OfflineModelPort('NO_NEW_SEND')
                        if state=='unknown':
                            with self.assertRaises(HCLFailure):RecoveryManager(store).resume_execution(request,expected_owner_id=old['owner_id'])
                            result=HCL(store,principal=fixture.owner,gateway=ModelGateway(store,port)).run_sync(request)
                            self.assertFalse(result.answer or result.claim_records)
                        else:
                            if state!='completed':RecoveryManager(store).resume_execution(request,expected_owner_id=old['owner_id'])
                            result=HCL(store,principal=fixture.owner,gateway=ModelGateway(store,port)).run_sync(request)
                            self.assertEqual(result.status,'PARTIAL',result.diagnostics)
                            if state=='completed':
                                self.assertEqual(result.answer,row['answer'])
                                self.assertEqual(codec.dumps(result.claim_records).decode(),row['result_claims'])
                            for key,wire in row['proofs'].items():
                                proof=next(r for r in store.inferences(old['session'],fixture.owner) if r.result_id==key)
                                self.assertEqual(codec.dumps(proof).decode(),wire)
                                self.assertEqual(codec.dumps(AnswerAssembler()._claim(proof)).decode(),row['claims'][key])
                                self.assertNotIn('character_arcs',proof.values)
                        self.assertEqual(port.attempts,0)
                finally:store.close()
            finally:
                fixture.doCleanups();fixture.tearDown()
