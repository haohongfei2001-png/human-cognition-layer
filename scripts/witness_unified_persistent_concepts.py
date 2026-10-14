"""Synthetic ordinary-entry cross-request adoption and actual local successors."""
from dataclasses import replace
from pathlib import Path
from hashlib import sha256
import json
import subprocess
import tempfile

import hcl
from hcl import HCL, ExecutionBudget, ExecutionIssue, ConceptAdoptionIssue, ConceptFollowIssue, ConceptBinding
from hcl.kernel.types import Principal, TaskRequest, Issue, thaw
from hcl.memory.store import StateStore
from hcl.models.gateway import ModelGateway, OfflineModelPort
from hcl.runtime.execution_ledger import ExecutionLedger
from hcl.operators.concept_judgment import decision_key
from scripts.witness_unified_concept_judgment import propose, SCENE, PRINCIPLES


def witness():
    owner=Principal("synthetic-persistent-concept-witness","owner")
    rows=[]
    with tempfile.TemporaryDirectory() as directory:
        store=StateStore.sqlite(Path(directory)/"state.sqlite",revision=True)
        try:
            store.create_session("s",owner,{"other"})
            handles=(store.put_source("s",owner,"scene",SCENE),store.put_source("s",owner,"principles",PRINCIPLES))
            request=TaskRequest("original","当前定义修订应改变哪些保护判断，哪些原承诺必须保持？",handles,"s",owner,
                budget=ExecutionBudget(max_mock_calls=1,max_feedback=0,max_local_evaluations=100000,
                    max_request_bytes=1048576,max_context_tokens=1048576,max_output_bytes=1048576,
                    max_total_output_bytes=8000000,max_visible_output_tokens=1048576),
                issue=ExecutionIssue("root",goals=(Issue("original","judgment.evaluate"),)))
            candidate=propose(store.snapshot("s",owner,handles),request.question)
            port=OfflineModelPort(json.dumps(candidate,ensure_ascii=False))
            original=HCL(store,principal=owner,gateway=ModelGateway(store,port)).run_sync(request)
            assert original.status=="PARTIAL",original.diagnostics
            base=ExecutionLedger(store).delivery_inferences(request,original.execution_receipt["result_ids"])[0]
            def run(name,goal):
                req=replace(request,request_id=name,source_handles=(),budget=replace(request.budget,max_mock_calls=0),
                            issue=ExecutionIssue("root",goals=(goal,)))
                return req,HCL(store,principal=owner).run_sync(req)
            def adoption(name,label,head=None,stream="institution"):
                return run(name,ConceptAdoptionIssue(name,stream_id=stream,support_result_ids=(base.result_id,),
                                                     version_labels=(label,),expected_head=head))
            a_req,a=adoption("A","original")
            assert a.status=="COMPLETED",a.diagnostics
            head=a.execution_receipt["result_ids"][0]
            prior={}
            for name in ("B","C"):
                req,result=run(name,ConceptFollowIssue(name,base_result_id=base.result_id,
                    bindings=(ConceptBinding("meaning","institution"),)))
                assert result.status=="PARTIAL",result.diagnostics
                actual=ExecutionLedger(store).delivery_inferences(req,result.execution_receipt["result_ids"])[0]
                prior[name]=(req,result,actual)
            before={row["request_id"]:dict(row) for row in store._db.execute("SELECT * FROM tasks WHERE request_id IN ('B','C')")}
            # Instrument only newly scheduled computation, not pure certificate
            # verification. No provider or alternate scheduler is patched in.
            import hcl.operators.persistent_concepts as algorithm
            compute=algorithm.compute_persistent
            executions=[]
            def counted(*args,**kwargs):
                executions.append(args[1].issue_id)
                return compute(*args,**kwargs)
            algorithm.compute_persistent=counted
            try:
                d_req,d=adoption("D","revised",head)
                unrelated_req,unrelated=adoption("unrelated","original",stream="other-institution")
            finally:
                algorithm.compute_persistent=compute
            assert d.status=="PARTIAL",d.diagnostics
            assert len(executions)==2,executions
            assert unrelated.status=="COMPLETED" and "concept_successors" not in unrelated.execution_receipt
            actuals=ExecutionLedger(store).delivery_inferences(d_req,d.execution_receipt["result_ids"])
            successors=[r for r in actuals if r.kind==algorithm.KIND]
            assert len(successors)==2
            key=decision_key("scene","notice","notification")
            old=prior["B"][2].values["branches"][0]
            assert old["decision_projection"][key]["recommended"]==("ignore",)
            for successor in successors:
                current=successor.values["branches"][0]
                assert current["decision_projection"][key]["recommended"]==("protect",)
                assert current["classifications"]["current"]["actual"]["status"]=="MEMBER"
                assert current["classifications"]["promise-scope"]==old["classifications"]["promise-scope"]
                for field in ("cognition","actual_interaction","opportunities"):
                    assert current["actual_judgment"]["models"][0][field]==old["actual_judgment"]["models"][0][field]
            after={row["request_id"]:dict(row) for row in store._db.execute("SELECT * FROM tasks WHERE request_id IN ('B','C')")}
            assert before==after
            stale=HCL(store,principal=owner).run_sync(prior["B"][0])
            assert stale.status=="STALE_STATE" and not stale.answer
            replay=HCL(store,principal=owner).run_sync(request)
            assert (original.answer,original.claim_records)==(replay.answer,replay.claim_records)
            assert d.usage["mock_calls"]==0 and unrelated.usage["mock_calls"]==0
            rows.append(dict(case="independent-A-B-C-D",original_v2_result_id=base.result_id,
                adopted_head=head,prior_selected=thaw(old),successors=[thaw(v.values) for v in successors],
                actual_new_solver_executions=executions,original_task_rows_unchanged=before==after,
                preserved_original_answer_and_claims=True,stale_follow_delivery=stale.status,
                revision_receipt=thaw(d.execution_receipt),revision_answer=d.answer,usage=thaw(d.usage),
                claim_fields=[f.field for c in d.claim_records for f in c.used_result_fields],
                unrelated_consumer_executions=0,offline_proposal_calls=port.attempts))
            store.set_readers("s",owner,"principles",{"other"})
            denied=HCL(store,principal=owner).run_sync(d_req)
            assert denied.status=="DENIED" and not denied.answer
            rows.append(dict(case="fresh-revocation",status=denied.status,answer_absent=True))
        finally:
            store.close()
    root=Path(hcl.__file__).resolve().parents[1]
    return dict(schema="hcl-persistent-concept-revision-witness-1",
        checked_commit=subprocess.check_output(["git","rev-parse","HEAD"],cwd=root,text=True).strip(),
        runtime_hashes={str(p.relative_to(root)):sha256(p.read_bytes()).hexdigest() for p in sorted((root/"hcl").rglob("*.py"))},
        rows=rows,provider_calls=0,provider_spend_usd=0,sealed_content_reads=0,
        evidence_scope="INTEGRATED_OFFLINE_PARTIAL_EXPLICIT_SAME_HOST_CROSS_REQUEST_REVISION",
        not_established=["OPEN_SEMANTIC_EXTRACTION","CROSS_SESSION_PRINCIPAL_ALIGNMENT","GENERAL_CYCLIC_REVISION",
            "AUTOMATIC_SEMANTIC_RECOMPILATION","ARBITRARY_CONCEPT_MENTAL_COMMITMENT_PREDICATES",
            "MULTISTEP_POLICIES","FULL_M12_M13_M14","FULL_S3_S4","LIVE_EFFECT"])


if __name__=="__main__":
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument("--output",required=True,type=Path)
    args=parser.parse_args();args.output.write_text(json.dumps(witness(),ensure_ascii=False,sort_keys=True,indent=2)+"\n")
