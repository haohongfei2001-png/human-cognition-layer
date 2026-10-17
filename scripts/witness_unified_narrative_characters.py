"""Provider-free actual M09-to-M11 consumption, including late counterevidence."""
import argparse
import asyncio
from copy import deepcopy
from dataclasses import replace
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import tempfile
from hcl import HCL, ExecutionBudget, ExecutionIssue
from hcl.kernel.types import Principal, TaskRequest, Issue, thaw
from hcl.memory.store import StateStore
from hcl.models.gateway import ModelGateway, OfflineModelPort
from hcl.runtime.context import ContextCompiler
from scripts.witness_unified_relationship import SOURCE, propose as relationship_propose


def propose(snapshot, question, chunk, mode="stable"):
    task=relationship_propose(snapshot,question,"counterevidence" if mode=="counterevidence" else "stable")
    refs=[s.segment_id for s in chunk.segments]
    def bind(value):
        if isinstance(value,dict):
            for key,item in value.items():
                if key=="segment_ids":value[key]=refs
                else:bind(item)
        elif isinstance(value,list):
            for item in value:bind(item)
    bind(task)
    if mode=="duplicate":
        repeat=deepcopy(task["models"][0]["observations"][-1]);repeat.update(id="repeat",context_id="repeat")
        task["models"][0]["observations"].append(repeat)
    episodes=task["models"][0]["affect"]["episodes"]
    frame=dict(fragment=chunk.ordinal,id="reading")
    events=[dict(id=e["id"],frame=frame,description="Declared conditional episode",assumptions=[],segment_ids=refs) for e in episodes]
    if mode=="unrelated":events.append(dict(id="unrelated",frame=frame,description="Unrelated paragraph",assumptions=[],segment_ids=refs))
    return dict(schema="hcl-literature-fragment-2",assumptions=[],active_assumptions=[],
        frames=[dict(id="reading",parent=None,kind="INTERPRETATION",narrator="analyst",focalizer="b",segment_ids=refs)],
        events=events,mentions=[],orders=[],queries=[],motifs=[],variants=[],comparisons=[],analogies=[],unmodeled_segments=[],
        character_arcs=[dict(id="conditional-b",source_id="records",actor="b",assumptions=[],
            bindings=[dict(episode_id=e["id"],event=dict(fragment=chunk.ordinal,id=e["id"]),at=e["at"]) for e in episodes],task=task)])


def witness():
    rows=[];owner=Principal("synthetic-witness","owner")
    with tempfile.TemporaryDirectory() as directory:
        store=StateStore.sqlite(Path(directory)/"state.sqlite",revision=True)
        store.create_session("s",owner,{"other"})
        handle=store.put_source("s",owner,"records",SOURCE)
        budget=ExecutionBudget(max_mock_calls=1,max_feedback=0,max_output_bytes=1048576,max_total_output_bytes=16777216,
            max_visible_output_tokens=1048576,max_context_tokens=1048576,max_request_bytes=1048576,max_local_evaluations=100000,max_steps=64)
        snapshot=store.snapshot("s",owner,(handle,))
        try:
            for mode in ("stable","counterevidence","unrelated","duplicate","frontier"):
                request=TaskRequest(mode,"Compare the conditional character arc.",(handle,),"s",owner,
                    budget=replace(budget,max_local_evaluations=8) if mode=="frontier" else budget,
                    issue=ExecutionIssue("root",goals=(Issue(mode,"literature.analyze"),)))
                chunks=ContextCompiler().chunks(snapshot,request.question,"literature_compile",budget,OfflineModelPort().describe())
                assert len(chunks)==1
                candidate=propose(snapshot,request.question,chunks[0],mode)
                port=OfflineModelPort(json.dumps(candidate));client=HCL(store,principal=owner,gateway=ModelGateway(store,port))
                async def collect():return [e async for e in client.stream(request)]
                result=asyncio.run(collect())[-1].result
                assert result.status=="PARTIAL",result.diagnostics
                proof=next(r for r in store.inferences("s",owner) if r.result_id in result.execution_receipt["result_ids"])
                actual=thaw(proof.values["character_arcs"][0])
                assert "character_arcs" in {f.field for c in result.claim_records for f in c.used_result_fields}
                assert "Packet-local character reading" in result.answer
                attempts=port.attempts;replay=client.run_sync(request)
                assert replay.answer==result.answer and port.attempts==attempts
                assert result.usage["local_evaluations"]<=request.budget.max_local_evaluations
                rows.append(dict(case=mode,status=result.status,actual=actual,answer=result.answer,
                    claim_fields=sorted({f.field for c in result.claim_records for f in c.used_result_fields}),
                    replay_new_attempts=port.attempts-attempts,usage=dict(result.usage)))
            stable,late,unrelated,duplicate,frontier=[r["actual"]["values"]["models"][0] for r in rows]
            assert stable["prediction_matrix"]==late["prediction_matrix"]
            assert stable["longitudinal"]["pareto_explored"]!=late["longitudinal"]["pareto_explored"]
            assert any(t["change_points"] for t in late["preferred_forecasts"])
            assert stable==unrelated
            assert stable["longitudinal"]["evidence_factor_ids"]==duplicate["longitudinal"]["evidence_factor_ids"]
            assert frontier["longitudinal"]["global_comparison"]=="NOT_ESTABLISHED"
        finally:store.close()
    root=Path(__file__).resolve().parents[1]
    return dict(schema="hcl-narrative-character-witness-1",checked_commit=subprocess.check_output(["git","rev-parse","HEAD"],cwd=root,text=True).strip(),
        runtime_hashes={str(p.relative_to(root)):sha256(p.read_bytes()).hexdigest() for p in sorted((root/"hcl").rglob("*.py"))},rows=rows,
        provider_calls=0,provider_spend_usd=0,sealed_content_reads=0,
        evidence_scope="EXPLICIT_PACKET_LOCAL_SYNTHETIC_V2_CANDIDATES_ACTUAL_M09_M11_CONSUMPTION",
        not_established=["AUTOMATIC_V2_EXTRACTION","CROSS_PACKET_CHARACTER_ASSEMBLY","CROSS_SOURCE_IDENTITY","PRIVATE_CHARACTER_TRUTH","AESTHETIC_JUDGMENT","FULL_M09","FULL_M11","FULL_S4","LIVE_EFFECT"])


if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--output",required=True,type=Path);args=parser.parse_args()
    args.output.write_text(json.dumps(witness(),ensure_ascii=False,sort_keys=True,indent=2)+"\n")
