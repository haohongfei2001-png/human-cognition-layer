"""Run actual PR452 code before additive protocol migration, not a reconstructed store."""
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from dataclasses import asdict

from hcl import HCL
from hcl.kernel.types import Principal, HCLFailure
from hcl.memory import codec
from hcl.memory.store import StateStore
from hcl.memory.migrations.revision_upgrade import RevisionCutover, CONTROLLED_CANDIDATE_PREDECESSOR_CODE_HASH
from hcl.models.gateway import ModelGateway, OfflineModelPort
from hcl.operators.local_model import LocalModelOperator
from hcl.runtime.answer import AnswerAssembler
from hcl.runtime.context import ContextCompiler
from hcl.runtime.recovery import RecoveryManager
from scripts import witness_unified_causal_affect as affect
from tests import test_unified_s23_upgrade as fixtures
from tests import test_unified_causal_affect_upgrade as previous

BASELINE="dbf18b4ab9843b2e75866297235870a727c58bae"
TREE="ab34de705c577976fc6b5b8eef25829c57d84a87"


def datasets():
    rows=previous.datasets()
    with tempfile.TemporaryDirectory() as root:
        store=StateStore.sqlite(Path(root)/"state.sqlite",revision=True)
        owner=Principal("synthetic","owner");store.create_session("s",owner)
        request=affect.request(store,owner,"s","predecessor-v2")
        from dataclasses import replace
        handle=store.put_source("s",owner,"causal-valve",affect.SOURCE)
        request=replace(request,source_handles=(handle,))
        rows.append(dict(name="affect-v2",source_id="causal-valve",source=affect.SOURCE,question=request.question,
                         goal="affect.evaluate",purpose="affect_compile",budget=asdict(request.budget),
                         candidate=affect.candidate(store.snapshot("s",owner,request.source_handles),request.question),expected="COMPLETED"))
        store.close()
    return rows


class ControlledCandidatePredecessorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        assert subprocess.check_output(["git","rev-parse",BASELINE+"^{tree}"],cwd=fixtures.ROOT,text=True).strip()==TREE
        class Frozen(fixtures.RuntimeUpgradeTests):
            baseline=BASELINE
            code_hash=CONTROLLED_CANDIDATE_PREDECESSOR_CODE_HASH
            file_count=244
            old_program=previous.OLD_PROGRAM.replace("DATASET_LITERAL",repr(datasets()))

            def old(self, schema=3, name="old"):
                # POSIX has a per-argument limit; a larger multi-dialect synthetic
                # script is still executed by exact old runtime, from our file.
                program=self.root / (name+"-program.py")
                program.write_text(self.old_program)
                original=self.old_program
                self.old_program="exec(compile(open("+repr(str(program))+").read(),'<synthetic-old-runtime>','exec'))"
                try:return super().old(schema,name)
                finally:self.old_program=original
        cls.runtime=Frozen;Frozen.setUpClass()

    @classmethod
    def tearDownClass(cls):cls.runtime.tearDownClass()

    def test_actual_pr452_v1_v2_literature_context_proof_answer_bytes_recovery_acl(self):
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
                                    with patch.object(LocalModelOperator,"run",side_effect=AssertionError("accepted old computation must not repeat")):result=client.run_sync(request)
                                self.assertEqual(result.status,row["expected"],result.diagnostics)
                                if state=="completed":
                                    self.assertEqual(result.answer,row["answer"])
                                    self.assertEqual(codec.dumps(result.claim_records).decode(),row["result_claims"])
                                self.assertNotIn("metered_transport_calls",result.usage)
                                for key,wire in row["proofs"].items():
                                    proof=next(r for r in store.inferences(old["session"],fixture.owner) if r.result_id==key)
                                    self.assertEqual(codec.dumps(proof).decode(),wire)
                                    self.assertEqual(codec.dumps(AnswerAssembler()._claim(proof)).decode(),row["claims"][key])
                            self.assertEqual(port.attempts,0)
                    for source_id in {row["source_id"] for row in old["requests"].values()}:
                        store.set_readers(old["session"],fixture.owner,source_id,{"bob"})
                    for name,row in old["requests"].items():
                        if name.endswith("-completed"):
                            result=HCL(store,principal=fixture.owner).run_sync(codec.loads(row["request"].encode()))
                            self.assertEqual(result.status,"DENIED");self.assertFalse(result.answer or result.claim_records)
                finally:store.close()
            finally:fixture.doCleanups();fixture.tearDown()
