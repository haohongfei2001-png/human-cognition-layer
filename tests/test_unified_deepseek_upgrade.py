"""Execute exact PR453 main before side-copy; preserve simulated/old bytes."""
from dataclasses import asdict, replace
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from hcl import HCL
from hcl.kernel.types import Principal,HCLFailure
from hcl.memory import codec
from hcl.memory.store import StateStore
from hcl.memory.migrations.revision_upgrade import RevisionCutover,DEEPSEEK_HOST_PREDECESSOR_CODE_HASH
from hcl.models.gateway import ModelGateway,OfflineModelPort
from hcl.operators.local_model import LocalModelOperator
from hcl.runtime.answer import AnswerAssembler
from hcl.runtime.context import ContextCompiler
from hcl.runtime.recovery import RecoveryManager
from scripts import witness_unified_causal_affect as affect
from tests import test_unified_s23_upgrade as fixtures
from tests import test_unified_causal_affect_upgrade as earlier
from tests import test_unified_controlled_candidate_upgrade as previous

BASELINE="660c43593b7642f39ede95e5ae9c2f4855966ae5"
TREE="b94a906f06e6a738fdd96062bdc9d51a3dc575e8"


def datasets():
    rows=previous.datasets()
    with tempfile.TemporaryDirectory() as root:
        store=StateStore.sqlite(Path(root)/"state.sqlite",revision=True)
        owner=Principal("synthetic","owner");store.create_session("s",owner)
        handle=store.put_source("s",owner,"controlled-valve",affect.SOURCE)
        request=affect.request(store,owner,"s","controlled")
        request=replace(request,source_handles=(handle,),budget=replace(request.budget,max_mock_calls=0,max_feedback=1))
        rows.append(dict(name="controlled-v2",source_id="controlled-valve",source=affect.SOURCE,question=request.question,
            goal="affect.evaluate",purpose="affect_compile_v2",budget=asdict(request.budget),
            candidate=affect.candidate(store.snapshot("s",owner,(handle,)),request.question),expected="COMPLETED"))
        store.close()
    return rows


def program():
    body=earlier.OLD_PROGRAM.replace("DATASET_LITERAL",repr(datasets()))
    body=body.replace("  port=OfflineModelPort(json.dumps(data['candidate']))", """  port=OfflineModelPort(json.dumps(data['candidate']))
  gateway=ModelGateway(store,port)
  if data['name']=='controlled-v2':
   from hcl.models.candidate_contracts import CandidateAuthorization
   from hcl.models.candidate_protocol import DisconnectedChatTransport,ENVELOPE
   from hcl.models.controlled_candidates import ControlledCandidateGateway
   wire=json.dumps(dict(id='old-synthetic-return',object='chat.completion',model='old-host-model',
    choices=[dict(index=0,finish_reason='stop',message=dict(role='assistant',content=json.dumps(dict(schema=ENVELOPE,source_input_versions=dict(snapshot.source_versions),candidate=data['candidate']))))],
    usage=dict(prompt_tokens=1200,completion_tokens=3000,total_tokens=4200,prompt_tokens_details=dict(cached_tokens=200))))
   gateway=ControlledCandidateGateway(store,provider='old-host',model='old-host-model',transport=DisconnectedChatTransport([wire]))
   grant=CandidateAuthorization.for_request(request,authorization_id='old-synthetic-'+name,provider='old-host',model='old-host-model',max_calls=2,max_cost_nanos=10**9,max_input_tokens=1048576,max_output_tokens=262144,rate_version='old-fixture-rate',input_nanos_per_token=20,cached_input_nanos_per_token=10,output_nanos_per_token=80)
   gateway.register_authorization(request,grant)""")
    body=body.replace("gateway=ModelGateway(store,port)).run_sync(request)","gateway=gateway).run_sync(request)")
    body=body.replace("    result_claims=codec.dumps(result.claim_records).decode() if result else None,answer=result.answer if result else None)","""    result_claims=codec.dumps(result.claim_records).decode() if result else None,answer=result.answer if result else None,
    usage=codec.dumps(result.usage).decode() if result else None,
    calls={r['call_id']:{slot:codec.dumps(store._get_object(r[slot])).decode() if r[slot] else None for slot in ('request_hash','response_hash')} for r in store._db.execute('SELECT * FROM calls WHERE task_key=?',(task['task_key'],))})""")
    return body


class DeepSeekPredecessorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        assert subprocess.check_output(["git","rev-parse",BASELINE+"^{tree}"],cwd=fixtures.ROOT,text=True).strip()==TREE
        class Frozen(fixtures.RuntimeUpgradeTests):
            baseline=BASELINE
            code_hash=DEEPSEEK_HOST_PREDECESSOR_CODE_HASH
            file_count=249
            old_program=program()
            def old(self,schema=3,name="old"):
                path=self.root/(name+"-program.py");path.write_text(self.old_program)
                original=self.old_program
                self.old_program="exec(compile(open("+repr(str(path))+").read(),'<synthetic-old-runtime>','exec'))"
                try:return super().old(schema,name)
                finally:self.old_program=original
        cls.runtime=Frozen;Frozen.setUpClass()

    @classmethod
    def tearDownClass(cls):cls.runtime.tearDownClass()

    def test_pr453_simulated_cny_separation_old_cognition_bytes_recovery_acl(self):
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
                            for call in store._db.execute("SELECT * FROM calls WHERE task_key=?",(row["task"]["task_key"],)):
                                for slot,wire in row["calls"][call["call_id"]].items():
                                    self.assertEqual(codec.dumps(store._get_object(call[slot])).decode() if call[slot] else None,wire)
                            port=OfflineModelPort("NO_NEW_SEND");client=HCL(store,principal=fixture.owner,gateway=ModelGateway(store,port))
                            if name.startswith("controlled-v2-"):
                                from hcl.models.controlled_candidates import ControlledCandidateGateway
                                from hcl.models.candidate_protocol import DisconnectedChatTransport
                                transport=DisconnectedChatTransport([None])
                                client=HCL(store,principal=fixture.owner,gateway=ControlledCandidateGateway(
                                    store,provider="old-host",model="old-host-model",transport=transport))
                            state=name.rsplit("-",1)[1]
                            if state=="unknown":
                                with self.assertRaises(HCLFailure) as caught:RecoveryManager(store).resume_execution(request,expected_owner_id=old["owner_id"])
                                self.assertEqual(caught.exception.diagnostic.code,"UNKNOWN_SEND_NO_RESUME")
                                result=client.run_sync(request);self.assertFalse(result.answer or result.claim_records)
                            else:
                                if state!="completed":RecoveryManager(store).resume_execution(request,expected_owner_id=old["owner_id"])
                                if state=="returned":result=client.run_sync(request)
                                else:
                                    with patch.object(LocalModelOperator,"run",side_effect=AssertionError("accepted old computation must not repeat")):result=client.run_sync(request)
                                self.assertEqual(result.status,row["expected"],result.diagnostics)
                                if state=="completed":
                                    self.assertEqual(result.answer,row["answer"])
                                    self.assertEqual(codec.dumps(result.claim_records).decode(),row["result_claims"])
                                    self.assertEqual(codec.dumps(result.usage).decode(),row["usage"])
                                self.assertNotIn("currency",result.usage)
                                for key,wire in row["proofs"].items():
                                    proof=next(r for r in store.inferences(old["session"],fixture.owner) if r.result_id==key)
                                    self.assertEqual(codec.dumps(proof).decode(),wire)
                                    self.assertEqual(codec.dumps(AnswerAssembler()._claim(proof)).decode(),row["claims"][key])
                            self.assertEqual(port.attempts,0)
                            if name.startswith("controlled-v2-"):self.assertEqual(transport.requests,[])
                    for source_id in {r["source_id"] for r in old["requests"].values()}:
                        store.set_readers(old["session"],fixture.owner,source_id,{"bob"})
                    for name,row in old["requests"].items():
                        if name.endswith("-completed"):
                            result=HCL(store,principal=fixture.owner).run_sync(codec.loads(row["request"].encode()))
                            self.assertEqual(result.status,"DENIED");self.assertFalse(result.answer or result.claim_records)
                finally:store.close()
            finally:fixture.doCleanups();fixture.tearDown()
