"""Actual scoped retrieval, remote counterevidence and downstream formal results.

The semantic candidates are explicitly supplied experimental interpretations.
Lexical/vector/recorded-graph retrieval is computed; open extraction, semantic
recall, erasure and complete M10/T27 research are not established by this file.
"""
import argparse
from dataclasses import replace
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import tempfile

from hcl import HCL, ExecutionBudget, ExecutionIssue, RetrievalIssue, RetrievalQuery
from hcl.kernel.types import Principal, TaskRequest, thaw
from hcl.memory import codec
from hcl.memory.query_store import QueryStore
from hcl.memory.store import StateStore
from hcl.models.gateway import ModelGateway, OfflineModelPort
from hcl.semantics.segments import question_segments


def propose(snapshot, question, mode):
    segments = snapshot.query_views["0"]["packet"]["segments"]
    source = [row["segment_id"] for row in segments]
    primary = [row["segment_id"] for row in segments if row["source_id"] == "source"]
    query = [row.segment_id for row in question_segments(question)]
    p = dict(op="atom",predicate="notified",args=[dict(entity="ada")])
    q = dict(op="atom",predicate="attends",args=[dict(entity="ada")])
    premises = [dict(op="implies",left=p,right=q)]
    if mode != "missing_condition":
        premises.append(p)
    if mode == "counterevidence":
        premises.append(dict(op="not",arg=q))
    def meaning(ast, key, refs):
        return dict(id=key,natural_reading="Declared experimental source interpretation",ast=ast,
                    frame="reported",segment_ids=refs,origin="INTERPRETATION")
    return dict(schema="hcl-semantic-candidates-1",
                frames=[dict(id="reported",kind="SOURCE_DISCOURSE",parent=None,segment_ids=source)],
                entities=[dict(id="ada",label="Ada",source_id="source",segment_ids=primary)],
                predicates=[dict(id=key,label=key,arity=1,segment_ids=source+query) for key in ("notified","attends")],
                readings=[dict(id="conditional",frame="reported",assumptions=[],
                               premises=[meaning(ast,"premise-"+str(i),source) for i,ast in enumerate(premises)],
                               query=meaning(q,"question",query),unparsed_segments=[],
                               alignment=dict(judgment="SUPPORTED",explanation="Supplied hypothesis; not verified extraction."))])


def witness():
    rows = []
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder)/"state.sqlite"
        store = StateStore.sqlite(path,revision=True)
        owner = Principal("witness","reader")
        store.create_session("s",owner,frozenset({"other"}))
        try:
            material="If Ada is notified she attends.\n"+"Background weather detail.\n"*4000+"Ada is notified.\n"
            store.put_source("s",owner,"source",material)
            query=RetrievalQuery(dict(support="Ada notified attends",challenge="not attend denial",alternative="alternative cause"),max_hits_per_route=4)
            question="Does the attendance conclusion follow under this experimental interpretation?"
            request=TaskRequest("initial",question,(),"s",owner,
                                budget=ExecutionBudget(max_mock_calls=1,max_feedback=0,max_request_bytes=16384,max_context_tokens=16384,max_output_bytes=131072,max_visible_output_tokens=131072,max_total_output_bytes=524288),
                                issue=ExecutionIssue("root",goals=(RetrievalIssue("reason",kind="logic.compare_semantic_readings",query=query),)))
            for mode, expected in (("supported","True"),("missing_condition","Uncertain"),("counterevidence",None)):
                if mode=="counterevidence":
                    store.put_source("s",owner,"denial","A denial: Ada does not attend.\n")
                snapshot=QueryStore(store).search("s",owner,query)
                candidate=propose(snapshot,question,mode)
                port=OfflineModelPort(json.dumps(candidate))
                current=replace(request,request_id=mode)
                client=HCL(store,principal=owner,gateway=ModelGateway(store,port))
                result=client.run_sync(current)
                assert result.status == ("PARTIAL" if mode=="counterevidence" else "COMPLETED"),result.diagnostics
                fields={field.field:field.value for claim in result.claim_records for field in claim.used_result_fields}
                assert fields["label"]==expected
                assert len(port.contexts[0].encode())<16384 and "Background weather detail" not in port.contexts[0]
                replay=client.run_sync(current)
                assert replay.answer==result.answer and port.attempts==1
                rows.append(dict(case=mode,status=result.status,answer=result.answer,
                                 claims=codec.encode(result.claim_records),usage=thaw(result.usage),
                                 original_characters=len(material),context_bytes=len(port.contexts[0].encode()),
                                 result_ids=result.execution_receipt["result_ids"],retrieval=thaw(fields["retrieval"])))
            limited=replace(request,request_id="closure-frontier",budget=replace(request.budget,max_mock_calls=0),
                            issue=ExecutionIssue("root",goals=(RetrievalIssue("retrieve",query=replace(query,max_characters=10)),)))
            result=HCL(store,principal=owner).run_sync(limited)
            assert result.status=="PARTIAL" and "RETRIEVAL_CLOSURE_FRONTIER" in result.unresolved_issues
            rows.append(dict(case="bounded_frontier",status=result.status,usage=thaw(result.usage),answer=result.answer))
            store.rebuild_projections()
            store.close();store=StateStore.sqlite(path)
            replay=HCL(store,principal=owner).run_sync(limited)
            assert replay.answer==result.answer
            store.set_readers("s",owner,"source",frozenset({"other"}))
            denied=HCL(store,principal=owner).run_sync(current)
            assert denied.status=="DENIED" and not denied.answer and not denied.claim_records
            rows.append(dict(case="current_acl_after_restart",status=denied.status,usage=thaw(denied.usage)))
        finally:
            store.close()
    root=Path(__file__).resolve().parents[1]
    return dict(schema="hcl-unified-retrieval-witness-1",
                checked_commit=subprocess.check_output(["git","rev-parse","HEAD"],cwd=root,text=True).strip(),
                runtime_hashes={str(path.relative_to(root)):sha256(path.read_bytes()).hexdigest() for path in sorted((root/"hcl").rglob("*.py"))},
                rows=rows,provider_calls=0,provider_spend_usd=0,sealed_content_reads=0,
                evidence_scope="BOUNDED_AUTHORIZED_RETRIEVAL_AND_CONDITIONAL_FORMAL_CONSUMPTION",
                not_established=["OPEN_EXTRACTION","SEMANTIC_RECALL","CHAPTER_EVENT_TOPIC_PERSPECTIVE_ALIGNMENT","WHOLE_BOOK_UNDERSTANDING","PRIVACY_ERASURE","FULL_M10","FULL_T27","FULL_S4","LIVE_EFFECT"])


if __name__ == "__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--output",required=True,type=Path);args=parser.parse_args()
    args.output.write_text(json.dumps(witness(),ensure_ascii=False,sort_keys=True,indent=2)+"\n")
