"""Execute exact PR451 main runtime, then recover v1 affect and v3 literature bytes."""

from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import json
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from hcl import HCL, ExecutionBudget
from hcl.kernel.types import HCLFailure, Principal
from hcl.memory import codec
from hcl.memory.store import StateStore
from hcl.memory.migrations.revision_upgrade import RevisionCutover, CAUSAL_AFFECT_PREDECESSOR_CODE_HASH
from hcl.models.gateway import ModelGateway, OfflineModelPort
from hcl.operators.local_model import LocalModelOperator
from hcl.runtime.answer import AnswerAssembler
from hcl.runtime.context import ContextCompiler
from hcl.runtime.recovery import RecoveryManager
from scripts import witness_unified_causal_affect as affect
from scripts import witness_unified_cross_packet_characters as literature
from tests import test_unified_s23_upgrade as fixtures

BASELINE = "04174fc512cb3979c38d2ba398257e32dd46fee8"
TREE = "69eb56b723adad0e095615c93cddcb7b0699c731"

OLD_PROGRAM = r'''
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
datasets=DATASET_LITERAL
class Crash(BaseException):pass
requests={};contexts={}
for data in datasets:
 handle=store.put_source(session,owner,data['source_id'],data['source'])
 budget=ExecutionBudget(**data['budget'])
 base=TaskRequest('base-'+data['name'],data['question'],(handle,),session,owner,budget=budget,issue=ExecutionIssue('root',goals=(Issue('base',data['goal']),)))
 snapshot=store.snapshot(session,owner,(handle,))
 chunk=ContextCompiler().chunks(snapshot,base.question,data['purpose'],budget,OfflineModelPort().describe())[0]
 contexts[data['name']]=ContextCompiler().serialize(snapshot,base.question,chunk)
 for state,seam in [('completed',None),('returned','return_persisted'),('unknown','send_started'),('computed','execution_computed'),('committed','execution_effects_committed')]:
  name=data['name']+'-'+state
  request=replace(base,request_id=name,issue=ExecutionIssue('root',goals=(Issue(name,data['goal']),)));result=None;crashed=False
  def stop(stage):
   global crashed
   if stage==seam:crashed=True;raise Crash()
  port=OfflineModelPort(json.dumps(data['candidate']))
  try:
   with patch.object(store,'_checkpoint',stop):result=HCL(store,principal=owner,gateway=ModelGateway(store,port)).run_sync(request)
  except Crash:pass
  assert (seam is None or crashed),(name,result)
  task=dict(store._db.execute('SELECT * FROM tasks WHERE request_id=?',(name,)).fetchone())
  accepted=[]
  if state in ('computed','committed'):
   checkpoint=store._get_object(task['result_hash'])
   for node in checkpoint.nodes.values():
    if node.get('operation')=='compute' and node.get('result') is not None:accepted.extend(node['result'].candidate_delta.new_inferences)
  elif result:
   assert result.status==data['expected'],(name,result.diagnostics)
   accepted=[r for r in store.inferences(session,owner) if r.result_id in result.execution_receipt['result_ids']]
  requests[name]=dict(request=codec.dumps(request).decode(),task=task,expected=data['expected'],source_id=data['source_id'],purpose=data['purpose'],dataset=data['name'],
    proofs={r.result_id:codec.dumps(r).decode() for r in accepted},
    claims={r.result_id:codec.dumps(AnswerAssembler()._claim(r)).decode() for r in accepted},
    result_claims=codec.dumps(result.claim_records).decode() if result else None,answer=result.answer if result else None)
print(json.dumps(dict(contexts=contexts,path=str(store.path),session=session,owner_id=store.owner_id,requests=requests,bundle=version_bundle(schema=schema))),flush=True)
for line in sys.stdin:
 command=json.loads(line)
 if command['action']=='close':break
 try:
  store.put_source(session,owner,'late','LATE SYNTHETIC')
  print(json.dumps(dict(ok=True)),flush=True)
 except Exception as error:print(json.dumps(dict(ok=False,error=type(error).__name__)),flush=True)
store.close()
'''


def datasets():
    """Current synthetic inputs only; all accepted proofs come from old code."""
    with tempfile.TemporaryDirectory() as root:
        store=StateStore.sqlite(Path(root)/"s.sqlite",revision=True)
        owner=Principal("synthetic","owner");store.create_session("s",owner)
        request=affect.request(store,owner,"s","predecessor")
        old_affect=affect.candidate(store.snapshot("s",owner,request.source_handles),request.question)
        old_affect["schema"]="hcl-affect-candidates-1"
        for episode in old_affect["models"][0]["episodes"]:
            episode.pop("attributions")
            for mapping in episode["mappings"]:mapping["conditions"]=mapping["conditions"][:1]
            for coping in episode["coping"]:
                for adjustment in coping["adjustments"]:adjustment["conditions"]=adjustment["conditions"][:1]
        from dataclasses import asdict
        rows=[dict(name="affect-v1",source_id="valve",source=affect.SOURCE,question=request.question,
                   goal="affect.evaluate",purpose="affect_compile",budget=asdict(request.budget),candidate=old_affect,expected="COMPLETED")]
        handle=store.put_source("s",owner,"records",literature.SOURCE)
        snapshot=store.snapshot("s",owner,(handle,))
        budget=ExecutionBudget(max_mock_calls=1,max_feedback=0,max_output_bytes=1048576,max_total_output_bytes=16777216,
            max_visible_output_tokens=1048576,max_request_bytes=20000,max_context_tokens=20000,max_steps=64,max_local_evaluations=100000)
        chunks=ContextCompiler().chunks(snapshot,literature.QUESTION,"literature_compile",budget,OfflineModelPort().describe())
        assert len(chunks)==1
        old_literature=literature.proposals(snapshot,chunks,"regrouped")[0]
        rows.append(dict(name="literature-v3",source_id="records",source=literature.SOURCE,question=literature.QUESTION,
                         goal="literature.analyze",purpose="literature_compile",budget=asdict(budget),candidate=old_literature,expected="PARTIAL"))
        store.close()
        return rows


class CausalAffectPredecessorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        assert subprocess.check_output(["git","rev-parse",BASELINE+"^{tree}"],cwd=fixtures.ROOT,text=True).strip()==TREE
        class Frozen(fixtures.RuntimeUpgradeTests):
            baseline=BASELINE
            code_hash=CAUSAL_AFFECT_PREDECESSOR_CODE_HASH
            file_count=242
            old_program=OLD_PROGRAM.replace("DATASET_LITERAL",repr(datasets()))
        cls.runtime=Frozen;Frozen.setUpClass()

    @classmethod
    def tearDownClass(cls):cls.runtime.tearDownClass()

    def test_exact_pr451_all_seams_v1_and_v3_old_bytes_zero_resends_and_acl(self):
        for schema in (3,4):
            fixture=self.runtime();fixture.setUp()
            try:
                source,old,process=fixture.old(schema)
                store=RevisionCutover.upgrade(source,fixture.root/"new",fixture.owner).open_store()
                try:
                    self.assertFalse(fixture.command(process,action="write")["ok"])
                    for name,row in old["requests"].items():
                        with self.subTest(schema=schema,name=name):
                            request=codec.loads(row["request"].encode())
                            snapshot=store.snapshot(old["session"],fixture.owner,request.source_handles)
                            chunk=ContextCompiler().chunks(snapshot,request.question,row["purpose"],request.budget,OfflineModelPort().describe())[0]
                            self.assertEqual(ContextCompiler().serialize(snapshot,request.question,chunk),old["contexts"][row["dataset"]])
                            port=OfflineModelPort("NO_NEW_SEND");client=HCL(store,principal=fixture.owner,gateway=ModelGateway(store,port))
                            state=name.rsplit("-",1)[1]
                            if state=="unknown":
                                with self.assertRaises(HCLFailure) as caught:RecoveryManager(store).resume_execution(request,expected_owner_id=old["owner_id"])
                                self.assertEqual(caught.exception.diagnostic.code,"UNKNOWN_SEND_NO_RESUME")
                                result=client.run_sync(request);self.assertFalse(result.answer or result.claim_records)
                            else:
                                if state!="completed":RecoveryManager(store).resume_execution(request,expected_owner_id=old["owner_id"])
                                if state=="returned":result=client.run_sync(request)
                                else:
                                    with patch.object(LocalModelOperator,"run",side_effect=AssertionError("old committed/computed result must not recompute")):result=client.run_sync(request)
                                self.assertEqual(result.status,row["expected"],result.diagnostics)
                                if state=="completed":
                                    self.assertEqual(result.answer,row["answer"])
                                    self.assertEqual(codec.dumps(result.claim_records).decode(),row["result_claims"])
                                for key,wire in row["proofs"].items():
                                    proof=next(r for r in store.inferences(old["session"],fixture.owner) if r.result_id==key)
                                    self.assertEqual(codec.dumps(proof).decode(),wire)
                                    self.assertEqual(codec.dumps(AnswerAssembler()._claim(proof)).decode(),row["claims"][key])
                                    if row["dataset"]=="affect-v1":
                                        self.assertEqual(proof.values["operator_version"],"s3-finite-affect-1")
                                        self.assertEqual(proof.values["models"][0]["episodes"][0]["derived"]["profiles"][0]["attribution"],dict(status="NOT_MODELED"))
                                    else:self.assertIn("composition",proof.values["character_arcs"][0])
                            self.assertEqual(port.attempts,0)
                    for dataset in ("affect-v1","literature-v3"):
                        row=old["requests"][dataset+"-completed"]
                        store.set_readers(old["session"],fixture.owner,row["source_id"],{"bob"})
                        request=codec.loads(row["request"].encode());result=HCL(store,principal=fixture.owner).run_sync(request)
                        self.assertEqual(result.status,"DENIED");self.assertFalse(result.answer or result.claim_records)
                finally:store.close()
            finally:fixture.doCleanups();fixture.tearDown()
