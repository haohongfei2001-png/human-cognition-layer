"""Synthetic counterexample partition repair, real M12/M13/M14 and host adoption."""
from copy import deepcopy
from scripts.witness_unified_concept_judgment import propose as base_propose, term
SCENE = "宁承诺在期限前核验演出风险但未完成；青向宁说明风险且宁理解并相信；保护能减少伤害但损失便利；旧承诺沿用原概念，新请求为standard、zoe、signed。"
PRINCIPLES = "Conditional care priority outweighs disputed liberty when a known risk is in scope; utility weights are care 1/4 and convenience 3/4; old scope is repeated pairs (a,a),(b,b); revised positive requests are (standard,a,signed),(standard,b,signed),(emergency,c,waiver),(emergency,d,waiver), negatives are (standard,e,waiver),(emergency,f,signed); finite partition repairs are proposals without adoption."


def propose(snapshot, question):
    data=base_propose(snapshot,question)
    data["schema"]="hcl-judgment-candidates-3"
    version=data["concepts"]["versions"][1]
    criterion=version["criteria"][0]
    def example(key,parts):
        return dict(id=key,term=term("request",*(term(s) for s in parts)),assumptions=["reading"],segment_ids=criterion["segment_ids"])
    criterion["positive"]=[example("p"+str(i),parts) for i,parts in enumerate([
        ("standard","a","signed"),("standard","b","signed"),("emergency","c","waiver"),("emergency","d","waiver")])]
    criterion["negative"]=[example("n"+str(i),parts) for i,parts in enumerate([
        ("standard","e","waiver"),("emergency","f","signed")])]
    data["concepts"]["cases"][0]["term"]=term("request",term("standard"),term("zoe"),term("signed"))
    data["repairs"]=[dict(id="repair-scope",version_id="revised",choice_id="meaning",segment_ids=criterion["segment_ids"])]
    return data


def witness():
    import json
    from pathlib import Path
    import tempfile
    from hashlib import sha256
    import subprocess
    from dataclasses import replace
    import hcl
    from hcl import HCL,ExecutionBudget,ExecutionIssue,ConceptAdoptionIssue,ConceptFollowIssue,ConceptBinding
    from hcl.kernel.types import Principal,TaskRequest,Issue,thaw
    from hcl.memory.store import StateStore
    from hcl.models.gateway import ModelGateway,OfflineModelPort
    from hcl.runtime.execution_ledger import ExecutionLedger
    from hcl.operators.concept_judgment import decision_key
    owner=Principal("synthetic-repair-witness","owner")
    rows=[]
    with tempfile.TemporaryDirectory() as directory:
        store=StateStore.sqlite(Path(directory)/"state.sqlite",revision=True)
        store.create_session("s",owner,{"reader"})
        handles=(store.put_source("s",owner,"scene",SCENE),store.put_source("s",owner,"principles",PRINCIPLES))
        budget=ExecutionBudget(max_mock_calls=1,max_feedback=0,max_local_evaluations=100000,
            max_request_bytes=1048576,max_context_tokens=1048576,max_output_bytes=1048576,
            max_total_output_bytes=8000000,max_visible_output_tokens=1048576)
        question="反例如何改变概念与保护义务，哪些修复仍可辩护？"
        request=TaskRequest("repairs",question,handles,"s",owner,budget=budget,
            issue=ExecutionIssue("root",goals=(Issue("repair","judgment.evaluate"),)))
        def results(result,req):
            return ExecutionLedger(store).delivery_inferences(req,tuple(result.execution_receipt.get("result_ids",())))
        def run_issue(name,goal):
            req=replace(request,request_id=name,source_handles=(),budget=replace(budget,max_mock_calls=0),
                issue=ExecutionIssue("root",goals=(goal,)))
            return HCL(store,principal=owner).run_sync(req),req
        try:
            candidate=propose(store.snapshot("s",owner,handles),question)
            port=OfflineModelPort(json.dumps(candidate,ensure_ascii=False))
            original=HCL(store,principal=owner,gateway=ModelGateway(store,port)).run_sync(request)
            assert original.status=="PARTIAL",original.diagnostics
            proof=results(original,request)[0]
            values=thaw(proof.values);repair=values["repairs"][0]
            assert values["complete"] and repair["complete"] and len(repair["candidates"])==14
            assert sum(len(c["equivalent_partitions"]) for c in repair["candidates"])==15
            assert sum(c["consistent"] for c in repair["candidates"])==4
            assert len(repair["minimum_consistent_candidate_ids"])==1 and not repair["adopted"]
            assert store._db.execute("SELECT count(*) FROM inferences WHERE result_id LIKE 'concept-adoption:%'").fetchone()[0]==0
            rows.append(dict(case="counterexample-repairs",actual=values,status=original.status,usage=thaw(original.usage),
                answer=original.answer,claim_fields=[f.field for c in original.claim_records for f in c.used_result_fields]))
            a,ar=run_issue("A",ConceptAdoptionIssue("a",stream_id="institution",support_result_ids=(proof.result_id,),version_labels=("original",)))
            assert a.status=="COMPLETED",a.diagnostics
            head=results(a,ar)[0].result_id
            for name in ("B","C"):
                result,req=run_issue(name,ConceptFollowIssue(name,base_result_id=proof.result_id,bindings=(ConceptBinding("meaning","institution"),)))
                assert result.status=="PARTIAL",result.diagnostics
            before={r["request_id"]:dict(r) for r in store._db.execute("SELECT * FROM tasks WHERE request_id IN ('B','C')")}
            label=next(c["version_label"] for c in repair["candidates"] if c["id"] in repair["minimum_consistent_candidate_ids"])
            d,dr=run_issue("D",ConceptAdoptionIssue("d",stream_id="institution",support_result_ids=(proof.result_id,),version_labels=(label,),expected_head=head))
            assert d.status=="PARTIAL",d.diagnostics
            successors=[r for r in results(d,dr) if r.kind=="CONDITIONAL_PERSISTENT_CONCEPT_REPAIR_JUDGMENT"]
            assert len(successors)==2 and d.usage["mock_calls"]==0
            key=decision_key("scene","notice","notification")
            assert all(r.values["branches"][0]["decision_projection"][key]["recommended"]==("protect",) for r in successors)
            assert before=={r["request_id"]:dict(r) for r in store._db.execute("SELECT * FROM tasks WHERE request_id IN ('B','C')")}
            rows.append(dict(case="explicit-adoption-two-successors",selected=label,actual=[thaw(r.values) for r in successors],
                status=d.status,usage=thaw(d.usage),answer=d.answer,old_task_bytes_unchanged=True))
            for mode in ("budget","conflict","tied"):
                data=deepcopy(candidate)
                if mode=="conflict":
                    criterion=data["concepts"]["versions"][1]["criteria"][0]
                    criterion["negative"].append(dict(deepcopy(criterion["positive"][0]),id="contradiction"))
                elif mode=="tied":
                    criterion=data["concepts"]["versions"][1]["criteria"][0]
                    def triple(letters):
                        return term("request",*(dict(kind="TERM",sort="Slot"+str(i),symbol=str(i)+x,arguments=[]) for i,x in enumerate(letters)))
                    def example(key,letters):
                        return dict(id=key,term=triple(letters),assumptions=["reading"],segment_ids=criterion["segment_ids"])
                    criterion["positive"]=[example(str(i),letters) for i,letters in enumerate(("aaa","abb","bab"))]
                    criterion["negative"]=[example("n","aba")]
                    data["concepts"]["cases"][0]["term"]=triple("baa")
                req=replace(request,request_id=mode,budget=replace(budget,max_local_evaluations=100 if mode=="budget" else 100000))
                p=OfflineModelPort(json.dumps(data,ensure_ascii=False))
                result=HCL(store,principal=owner,gateway=ModelGateway(store,p)).run_sync(req)
                assert result.status=="PARTIAL",result.diagnostics
                actual=thaw(results(result,req)[0].values)
                if mode=="budget":assert not actual["complete"] and not actual["robust_recommended"]
                elif mode=="conflict":assert actual["repairs"][0]["status"]=="NO_REPAIR_IN_FINITE_LANGUAGE"
                else:assert len(actual["repairs"][0]["minimum_consistent_candidate_ids"])==2
                rows.append(dict(case=mode,actual=actual,usage=thaw(result.usage)))
            port=OfflineModelPort("NO_NEW_SEND")
            replay=HCL(store,principal=owner,gateway=ModelGateway(store,port)).run_sync(request)
            assert (replay.answer,replay.claim_records)==(original.answer,original.claim_records) and port.attempts==0
            store.set_readers("s",owner,"principles",{"reader"})
            denied=HCL(store,principal=owner).run_sync(dr)
            assert denied.status=="DENIED" and not denied.answer
            rows.append(dict(case="fresh-acl-and-old-replay",old_answer_claim_bytes_unchanged=True,replay_new_attempts=0,status=denied.status))
        finally:store.close()
    root=Path(hcl.__file__).resolve().parents[1]
    return dict(schema="hcl-counterexample-concept-repair-witness-1",
        checked_commit=subprocess.check_output(["git","rev-parse","HEAD"],cwd=root,text=True).strip(),
        runtime_hashes={str(p.relative_to(root)):sha256(p.read_bytes()).hexdigest() for p in sorted((root/"hcl").rglob("*.py"))},
        rows=rows,provider_calls=0,provider_spend_usd=0,sealed_content_reads=0,
        evidence_scope="INTEGRATED_OFFLINE_PARTIAL_FINITE_COUNTEREXAMPLE_CONCEPT_REPAIR",
        not_established=["OPEN_SEMANTIC_EXTRACTION","GENERAL_CONCEPT_DISCOVERY","GLOBAL_REPAIR_OPTIMALITY",
            "AUTOMATIC_ADOPTION","MORAL_TRUTH","FULL_M12_M13_M14","FULL_S4","LIVE_EFFECT"])


if __name__=="__main__":
    import argparse,json
    from pathlib import Path
    parser=argparse.ArgumentParser();parser.add_argument("--output",required=True,type=Path)
    args=parser.parse_args();args.output.write_text(json.dumps(witness(),ensure_ascii=False,sort_keys=True,indent=2)+"\n")
