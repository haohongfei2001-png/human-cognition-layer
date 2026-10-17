"""Original synthetic finite M03/M06/M08/M05 witness; no live provider or extraction claim."""

from copy import deepcopy
from dataclasses import replace
from hashlib import sha256
from pathlib import Path
import argparse
import asyncio
import json
import subprocess
import tempfile

from hcl import HCL, ExecutionBudget, ExecutionIssue
from hcl.kernel.types import Principal, TaskRequest, Issue, thaw
from hcl.memory import codec
from hcl.memory.store import StateStore
from hcl.models.gateway import OfflineModelPort, ModelGateway
from hcl.semantics.segments import segment_snapshot

SOURCE = (
    "Original finite thought experiment. A operates a valve; B cares about safety and completing a hazardous duty. "
    "Initially both know the passage is open. B initially believes A's valve setting is active and no external fault is present. "
    "At time 1 the valve becomes inactive and an external fault occurs; only A sees this. "
    "At time 2 both see the closed passage. At time 3 a report of the inactive valve and external fault is offered. "
    "Alternative reception hypotheses specify B receiving, understanding and accepting it, missing it, not understanding it, or not believing it. "
    "The character-accessible structural hypothesis is loss = action or external. A competing hypothesis is loss = external. "
    "Availability of each theory is represented separately from observations of its variables. "
    "These finite structures, bridges, consequence functions and emotion mappings are proposed experimental inputs, not verified extraction. "
    "The safety consequences are open 3, closed -3, success 5, harm -5, waiting -1; duty has opposite consequences. "
    "Crossing open reaches success, crossing closed reaches harm; waiting reaches waiting. "
    "A coping hypothesis gives safety one quarter and duty three quarters, multiplying safety by nine only under negative safety and conditional valve contribution. "
    "This is a revisable candidate interpretation, not a psychological law, intention, blame or an enacted coping action."
)


def candidate(snapshot, question, mode="received"):
    refs = [s.segment_id for s in segment_snapshot(snapshot, question) if s.kind == "SOURCE"]
    source = next(iter(snapshot.source_versions))
    agents = [dict(id=a, label=a.upper(), source_id=source, segment_ids=refs) for a in ("a", "b")]
    variables = [dict(id=k, initial=v, observed_by=seen, segment_ids=refs) for k,v,seen in (
        ("open",True,["a","b"]), ("action",True,["a","b"]),
        ("external",False,["a","b"]), ("theory",True,["a","b"]))]
    def event(identity, at, kind, effects, seen=(), received=(), understood=(), trusted=()):
        return dict(id=identity,at=at,kind=kind,effects=effects,seen_by=list(seen),
                    received_by=list(received),understood_by=list(understood),trusted_by=list(trusted),
                    assumptions=[],segment_ids=refs)
    accepted = "a" if mode == "unreceived" else "b"
    events = [event("actual-cause-change",1,"change",dict(action=False,external=True),seen=["a"]),
              event("damage",2,"change",dict(open=False),seen=["a","b"]),
              event("cause-report",3 if mode != "late" else 4,"message",dict(action=False,external=True),
                    received=[accepted], understood=[] if mode=="ununderstood" else [accepted],
                    trusted=[] if mode in ("untrusted","ununderstood") else [accepted])]
    graph = dict(states=["open","closed","success","harm","waiting"],
                 terminal=["success","harm","waiting"],
                 utilities=dict(open="0",closed="0",success="1",harm="-1",waiting="0"),
                 horizon=1,actions=[])
    for identity,targets in (("cross",dict(open="success",closed="harm")),
                             ("wait",dict(open="waiting",closed="waiting"))):
        graph["actions"].append(dict(id=identity,cost="0",enabled=["open","closed"],feasible=["open","closed"],
            transitions={s:targets.get(s,s) for s in graph["states"]},
            observations={s:"same" for s in graph["states"]}))
    def plan(identity,at,actor="b"):
        return dict(id=identity,actor=actor,at=at,graph=deepcopy(graph),
                    bindings=[dict(state="open",when=dict(op="atom",name="open")),
                              dict(state="closed",when=dict(op="not",arg=dict(op="atom",name="open")))],
                    weights=dict(closed="1"),policy=None,segment_ids=refs)
    causal = dict(id="valve-causal",model=dict(id="valve",source_event_id="damage",variables=["action","external","loss"],
                    exogenous=["action","external"],rules=[dict(target="loss",expression="action or external",evidence_text="loss = action or external")]),
                  target="loss",observations=dict(action=0,external=1,loss=1),interventions=dict(action=0),segment_ids=refs)
    mental = dict(id="valve-scene",source_id=source,frame_kind="HYPOTHETICAL",assumptions=[],active_assumptions=[],unmodeled_segments=[],
                  agents=agents,variables=variables,events=events,queries=[],plans=[plan("before-news",2),plan("after-news",3)],causal=[causal])
    safety=dict(open="3",closed="-3",success="5",harm="-5",waiting="-1")
    goals=[dict(id="safety",label="safety",utilities=safety,segment_ids=refs),
           dict(id="duty",label="hazardous duty",utilities={s:str(-int(v)) for s,v in safety.items()},segment_ids=refs)]
    condition=dict(goal_id="safety",dimension="attribution",attribution_id="valve-loss",value="CONTRIBUTES")
    negative=dict(goal_id="safety",dimension="desirability",value="NEGATIVE")
    bridge=dict(id="valve-loss",goal_id="safety",actor="b",at=2,event_id="damage",contributor="a",cause_variable="action",actual_value=1,contrast_value=0,outcome_value=1,
                observations={k:dict(atom=a,positive=positive) for k,a,positive in (("action","action",True),("external","external",True),("loss","open",False))},
                structures=[dict(causal_id="valve-causal",available_when=dict(theory=True),segment_ids=refs)],
                max_world_evaluations=4096,segment_ids=refs)
    mappings=[dict(id="other-contribution",label="other-contribution distress candidate",conditions=[negative,condition],requires_previous=[],segment_ids=refs),
              dict(id="cause-absent",label="situational-loss candidate",conditions=[negative,dict(condition,value="CAUSE_NOT_ACTUAL")],requires_previous=[],segment_ids=refs)]
    coping=[dict(id="focus",kind="PROBLEM_FOCUSED",priorities=dict(safety="1/4",duty="3/4"),horizon=1,action_ids=["cross","wait"],observation_overrides={},segment_ids=refs,
                 adjustments=[dict(id="valve-attention",conditions=[negative,condition],multipliers=dict(safety="9",duty="1"),segment_ids=refs)])]
    episode=dict(id="initial",episode_id="loss",actor="b",before=0,at=2,plan_id="before-news",previous_weights=dict(open="1"),current_weights=dict(closed="1"),forecast_action="cross",
                 goals=goals,mappings=mappings,coping=coping,attributions=[bridge],previous_id=None,revision_kind="INITIAL",segment_ids=refs)
    updated=deepcopy(episode);updated.update(id="updated",at=3,plan_id="after-news",previous_id="initial",revision_kind="NEW_INFORMATION")
    updated["attributions"][0]["at"]=3
    model=dict(mental=mental,episodes=[episode,updated],channels=[])
    if mode == "analyst":
        causal["observations"]=dict(action=1,external=0,loss=1)
        causal["interventions"]=dict(external=0)
        events[-1]["received_by"]=[];events[-1]["understood_by"]=[];events[-1]["trusted_by"]=[]
        updated["revision_kind"]="ANALYST_REINTERPRETATION"
    if mode in ("unknown","competing","inconsistent","frontier","structure_unavailable","gate_unknown","disconnected_m06","disconnected_m05"):
        events[-1]["received_by"]=[];events[-1]["understood_by"]=[];events[-1]["trusted_by"]=[]
    if mode == "unknown":
        variables[1].update(initial=None,observed_by=[])
        variables[2].update(initial=None,observed_by=[])
    if mode == "structure_unavailable":variables[3]["initial"]=False
    if mode == "gate_unknown":variables[3].update(initial=None,observed_by=[])
    if mode == "inconsistent":variables[2]["initial"]=True;variables[1]["initial"]=False
    if mode == "competing":
        second=deepcopy(causal);second["id"]="external-causal";second["model"].update(id="external",rules=[dict(target="loss",expression="external",evidence_text="loss = external")])
        mental["causal"].append(second)
        # Leave external unobserved in the bridge so both structures have an
        # admissible factual explanation of the same observed damage.
        for ep in model["episodes"]:
            ep["attributions"][0]["observations"].pop("external")
            ep["attributions"][0]["structures"].append(dict(causal_id="external-causal",available_when=dict(theory=True),segment_ids=refs))
    if mode == "inconsistent":
        for ep in model["episodes"]:
            ep["attributions"][0]["observations"]["loss"]["positive"]=True
    for ep in model["episodes"]:
        if mode in ("frontier","disconnected_m06"):ep["attributions"][0]["max_world_evaluations"]=0
        if mode == "disconnected_m05":ep["coping"][0]["adjustments"]=[]
    return dict(schema="hcl-affect-candidates-2",models=[model])


def budget():
    return ExecutionBudget(max_mock_calls=1,max_local_evaluations=4096,max_output_bytes=1048576,
                           max_request_bytes=1048576,max_total_output_bytes=16777216,
                           max_context_tokens=1048576,max_visible_output_tokens=1048576)


def request(store, owner, session, mode):
    handle=store.put_source(session,owner,"valve",SOURCE)
    return TaskRequest("causal-affect-"+mode,"How does the received cause information change conditional appraisal and coping?",(handle,),session,owner,
                       budget=budget(),issue=ExecutionIssue("root",goals=(Issue("affect","affect.evaluate"),)))


def execute(mode="received", *, stream=False):
    with tempfile.TemporaryDirectory() as root:
        store=StateStore.sqlite(Path(root)/"state.sqlite",revision=True)
        owner=Principal("witness","owner");store.create_session("s",owner,{"other"})
        req=request(store,owner,"s",mode)
        proposed=candidate(store.snapshot("s",owner,req.source_handles),req.question,mode)
        port=OfflineModelPort(json.dumps(proposed));client=HCL(store,principal=owner,gateway=ModelGateway(store,port))
        if stream:
            async def collect():
                return [e async for e in client.stream(req)]
            events=asyncio.run(collect())
            result=events[-1].result
        else:result=client.run_sync(req)
        inferences=[r for r in store.inferences("s",owner) if r.result_id in result.execution_receipt.get("result_ids",())]
        if not inferences:raise AssertionError((mode,result.status,result.diagnostics))
        inference=inferences[-1]
        replay_port=OfflineModelPort("NO RESEND")
        replay=HCL(store,principal=owner,gateway=ModelGateway(store,replay_port)).run_sync(req)
        assert result.answer == replay.answer and codec.dumps(result.claim_records) == codec.dumps(replay.claim_records)
        assert replay_port.attempts == 0
        store.set_readers("s",owner,"valve",{"other"})
        denied=client.run_sync(req);assert denied.status=="DENIED" and not denied.claim_records
        store.close()
        return result,thaw(inference.values),port.attempts


def witness():
    modes=("received","unreceived","ununderstood","untrusted","late","analyst","unknown","competing","frontier","structure_unavailable","gate_unknown","inconsistent","disconnected_m06","disconnected_m05")
    records={}
    for mode in modes:
        result,values,attempts=execute(mode)
        episodes=values["models"][0]["episodes"]
        records[mode]=dict(status=result.status,attempts=attempts,episodes=[dict(
            attribution=e["derived"]["profiles"][0]["attribution"],hypotheses=e["derived"]["hypotheses"],
            coping=e["derived"]["coping"],reappraisal=e["derived"]["reappraisal"]) for e in episodes])
    before,after=records["received"]["episodes"]
    assert before["attribution"]["candidates"][0]["possibilities"]==["CONTRIBUTES"]
    assert after["attribution"]["candidates"][0]["possibilities"]==["CAUSE_NOT_ACTUAL"]
    assert before["coping"][0]["branches"][0]["computation"]["best_actions"]==["wait"]
    assert after["coping"][0]["branches"][0]["computation"]["best_actions"]==["cross"]
    for mode in ("unreceived","ununderstood","untrusted","late","analyst"):
        assert records[mode]["episodes"][1]["attribution"]["candidates"][0]["possibilities"]==["CONTRIBUTES"]
    for mode in ("unknown","competing","frontier","structure_unavailable","gate_unknown","inconsistent","disconnected_m06"):
        assert len(records[mode]["episodes"][0]["coping"][0]["branches"])==2,mode
    assert records["disconnected_m05"]["episodes"][0]["coping"][0]["branches"][0]["computation"]["best_actions"]==["cross"]
    streamed,stream_values,_=execute("received",stream=True)
    assert stream_values["models"][0]["episodes"][1]["derived"]["coping"][0]["branches"][0]["computation"]["best_actions"]==["cross"]
    root=Path(__file__).resolve().parents[1]
    return dict(head=subprocess.check_output(["git","rev-parse","HEAD"],cwd=root,text=True).strip(),
                runtime_sha256=sha256(codec.canonical({str(p.relative_to(root)):sha256(p.read_bytes()).hexdigest() for p in sorted((root/"hcl").rglob("*.py"))}).encode()).hexdigest(),
                boundary="INTEGRATED_OFFLINE_EXPLICIT_SOURCE_MODELS_NOT_AUTOMATIC_EXTRACTION_OR_FULL_M08",
                provider_calls=0,spend=0,sealed_reads=0,stream_status=streamed.status,checks=records)


if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--output",required=True);args=parser.parse_args()
    result=witness();Path(args.output).write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps(dict(head=result["head"],modes=len(result["checks"]),status="PASS")))
