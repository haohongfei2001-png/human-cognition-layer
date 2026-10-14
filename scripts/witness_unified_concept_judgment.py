"""Synthetic M12 -> actual M13/M14 version sensitivity and immutable terms."""
from copy import deepcopy
from hcl.semantics.segments import segment_snapshot
from scripts.witness_unified_judgment import propose as base_propose


def term(symbol, *arguments):
    return dict(kind="TERM", sort="case" if arguments else "entity", symbol=symbol, arguments=list(arguments))


def propose(snapshot, question):
    result = base_propose(snapshot, question)
    result["schema"] = "hcl-judgment-candidates-2"
    spans = {k: [s.segment_id for s in segment_snapshot(snapshot, question) if s.kind == "SOURCE" and s.source_id == k]
             for k in ("scene", "principles")}
    r, n = spans["scene"], spans["principles"]
    def example(key, a, b):
        return dict(id=key, term=term("pair", term(a), term(b)), assumptions=["reading"], segment_ids=n)
    criterion = dict(id="criterion", direction="BICONDITIONAL", assumptions=["reading"],
        positive=[example("aa", "a", "a"), example("bb", "b", "b")], negative=[], boundary=[], segment_ids=n)
    version = dict(id="original", concept_key="protected-case", scope="notice-role", purpose="Define the conditional scope of protection.",
        frame_kind="SOURCE_DISCOURSE", effective_at=0, assumptions=["reading"], active_assumptions=["reading"], criteria=[criterion], segment_ids=n)
    revised = deepcopy(version); revised.update(id="revised", effective_at=1)
    revised["criteria"][0]["positive"][1] = example("bc", "b", "c")
    case = dict(id="new-case", term=term("pair", term("c"), term("d")), assumptions=[], active_assumptions=[], segment_ids=r)
    use = dict(id="current", concept_key="protected-case", scope="notice-role", frame_kind="SOURCE_DISCOURSE",
        case_id="new-case", at=2, selector=dict(kind="CHOICE", id="meaning"), commitment=None, segment_ids=r+n)
    original_use = dict(use, id="promise-scope", at=0, selector=dict(kind="PINNED", id="original"), commitment=dict(id="verify", terms_version="v1"))
    result["concepts"] = dict(versions=[version,revised], cases=[case], uses=[use,original_use],
        choices=[dict(id="meaning", versions=["original","revised"], segment_ids=n)], constraints=[], unmodeled_segments=[])
    model = result["models"][0]
    argument = model["argument"]
    for suffix in ("current", "original"):
        argument["literals"].append(dict(id=suffix+"-category", atom=suffix+"-category", negative=False, kind="CLAIM", segment_ids=n))
        argument["premises"].append(dict(id="fact-"+suffix+"-category", literal=suffix+"-category", ordinary=False, assumptions=[], segment_ids=n))
    argument["rules"][0]["premises"].append("current-category")
    argument["literals"].append(dict(id="original-duty", atom="original-duty", negative=False, kind="CLAIM", segment_ids=n))
    argument["rules"].append(dict(id="original-duty", premises=["original-category"], conclusion="original-duty", strict=False, assumptions=[], segment_ids=n))
    argument["queries"].append(dict(id="original-duty", literal="original-duty", preferred=False, critical_candidates=[], segment_ids=n))
    model["decisions"][0]["frameworks"][0]["norms"].append(dict(id="original-scope", label="original commitment scope",
        permitted_actions=["protect"], guard_fact_ids=["promise"], argument_query_id="original-duty", segment_ids=r+n))
    argument["literals"].extend([
        dict(id="not-original-category", atom="original-category", negative=True, kind="CLAIM", segment_ids=n),
        dict(id="not-original-duty", atom="original-duty", negative=True, kind="CLAIM", segment_ids=n)])
    argument["premises"].append(dict(id="fact-not-original-category", literal="not-original-category", ordinary=False, assumptions=[], segment_ids=n))
    argument["rules"].append(dict(id="outside-original-duty", premises=["not-original-category"], conclusion="not-original-duty", strict=False, assumptions=[], segment_ids=n))
    model["concept_bindings"] = [dict(premise_id="fact-current-category", use_id="current", expected=True, segment_ids=n),
                                   dict(premise_id="fact-original-category", use_id="promise-scope", expected=True, segment_ids=r+n),
                                   dict(premise_id="fact-not-original-category", use_id="promise-scope", expected=False, segment_ids=r+n)]
    return result

from scripts.witness_unified_judgment import SCENE as BASE_SCENE, PRINCIPLES as BASE_PRINCIPLES
SCENE = BASE_SCENE + " 原承诺的保护范围沿用订立时的定义；当前待分类案例包含两个不同角色。改变现行定义不会重新协商旧承诺。"
PRINCIPLES = BASE_PRINCIPLES + " The original conditional definition covers repeating pairs, as in (a,a) and (b,b). The revised definition covers arbitrary pairs, as in (a,a) and (b,c). These are explicit biconditional hypotheses, not learned moral laws."


def witness():
    import json
    from pathlib import Path
    import tempfile
    from hashlib import sha256
    import subprocess
    from dataclasses import replace
    import hcl
    from hcl import HCL, ExecutionBudget, ExecutionIssue
    from hcl.kernel.types import Principal, TaskRequest, Issue, thaw
    from hcl.memory.store import StateStore
    from hcl.models.gateway import ModelGateway, OfflineModelPort
    owner=Principal("synthetic-concept-witness","owner")
    rows=[]
    with tempfile.TemporaryDirectory() as directory:
        store=StateStore.sqlite(Path(directory)/"state.sqlite",revision=True)
        store.create_session("s",owner,{"bob"})
        handles=(store.put_source("s",owner,"scene",SCENE),store.put_source("s",owner,"principles",PRINCIPLES))
        try:
            for mode in ("joint-version-choice","missing-case","typical-only","negative-counterexample","budget"):
                request=TaskRequest(mode,"不同概念定义如何改变当前保护义务，并保留旧承诺原义？",handles,"s",owner,
                    budget=ExecutionBudget(max_mock_calls=1,max_feedback=0,max_local_evaluations=50 if mode=="budget" else 100000,
                        max_request_bytes=1048576,max_context_tokens=1048576,max_output_bytes=1048576,max_total_output_bytes=8000000,max_visible_output_tokens=1048576),
                    issue=ExecutionIssue("root",goals=(Issue(mode,"judgment.evaluate"),)))
                candidate=propose(store.snapshot("s",owner,handles),request.question)
                if mode=="missing-case":candidate["concepts"]["cases"][0]["term"]=None
                elif mode=="typical-only":
                    for v in candidate["concepts"]["versions"]:v["criteria"][0]["direction"]="TYPICAL"
                elif mode=="negative-counterexample":
                    v=candidate["concepts"]["versions"][1];example=deepcopy(v["criteria"][0]["positive"][0])
                    example.update(id="challenge",term=deepcopy(candidate["concepts"]["cases"][0]["term"]))
                    v["criteria"][0]["negative"]=[example]
                port=OfflineModelPort(json.dumps(candidate,ensure_ascii=False))
                result=HCL(store,principal=owner,gateway=ModelGateway(store,port)).run_sync(request)
                assert result.status=="PARTIAL",result.diagnostics
                actual=next(r for r in store.inferences("s",owner) if r.result_id in result.execution_receipt["result_ids"])
                if mode=="joint-version-choice":
                    old,new=actual.values["branches"]
                    assert old["classifications"]["current"]["actual"]["status"]=="EXCLUDED"
                    assert new["classifications"]["current"]["actual"]["status"]=="MEMBER"
                    assert old["classifications"]["promise-scope"]==new["classifications"]["promise-scope"]
                    assert old["actual_judgment"]["models"][0]["actual_interaction"]==new["actual_judgment"]["models"][0]["actual_interaction"]
                if mode=="budget":assert not actual.values["complete"] and not actual.values["robust_recommended"]
                replay_port=OfflineModelPort("NO_NEW_SEND")
                replay=HCL(store,principal=owner,gateway=ModelGateway(store,replay_port)).run_sync(request)
                assert replay.answer==result.answer and replay_port.attempts==0
                rows.append(dict(case=mode,actual=thaw(actual.values),answer=result.answer,usage=thaw(result.usage),
                    claim_fields=[f.field for c in result.claim_records for f in c.used_result_fields],replay_new_attempts=0))
            store.set_readers("s",owner,"principles",{"bob"})
            result=HCL(store,principal=owner).run_sync(request)
            assert result.status=="DENIED" and not result.answer
            rows.append(dict(case="fresh-source-acl",status=result.status,answer_absent=True))
        finally:store.close()
    root=Path(hcl.__file__).resolve().parents[1]
    return dict(schema="hcl-concept-sensitive-judgment-witness-1",
        checked_commit=subprocess.check_output(["git","rev-parse","HEAD"],cwd=root,text=True).strip(),
        runtime_hashes={str(p.relative_to(root)):sha256(p.read_bytes()).hexdigest() for p in sorted((root/"hcl").rglob("*.py"))},
        rows=rows,provider_calls=0,provider_spend_usd=0,sealed_content_reads=0,
        evidence_scope="INTEGRATED_OFFLINE_PARTIAL_FINITE_CONCEPT_VERSION_PROPAGATION",
        not_established=["OPEN_SEMANTIC_EXTRACTION","GLOBAL_CONCEPT_REGISTRY","AUTOMATIC_CROSS_TASK_PROPAGATION",
            "GENERAL_CONCEPT_DISCOVERY","MORAL_TRUTH","FULL_M12_M13_M14","FULL_S4","LIVE_EFFECT"])


if __name__=="__main__":
    import argparse,json
    from pathlib import Path
    parser=argparse.ArgumentParser();parser.add_argument("--output",required=True,type=Path)
    args=parser.parse_args();args.output.write_text(json.dumps(witness(),ensure_ascii=False,sort_keys=True,indent=2)+"\n")
