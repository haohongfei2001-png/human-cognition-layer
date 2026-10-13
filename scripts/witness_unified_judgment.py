"""Offline finite M14 computation witness; candidates never supply decisions."""
import argparse
from dataclasses import replace
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import tempfile

import hcl
from hcl import HCL, ExecutionBudget, ExecutionIssue
from hcl.kernel.types import Principal, TaskRequest, Issue, thaw
from hcl.memory.store import StateStore
from hcl.models.gateway import ModelGateway, OfflineModelPort
from hcl.semantics.segments import segment_snapshot

SCENE = "宁负责通知演出风险。青告知宁场地存在风险。宁承诺在期限前完成核验，核验尚未完成。保护观众可减少伤害，但会损失便利。"
PRINCIPLES = "The analyst conditionally proposes care and convenience weights. A known risk creates a duty to protect; a conflicting liberty principle is disputed. The meeting is on Tuesday."
QUESTION = "应如何行动？请区分知情、机会、承诺与规范争议。"


def atom(name):
    return dict(op="atom", name=name)


def propose(snapshot, question):
    segments=segment_snapshot(snapshot,question)
    refs={side:[s.segment_id for s in segments if s.kind=="SOURCE" and s.source_id==side] for side in ("scene","principles")}
    allrefs=refs["scene"]+refs["principles"]
    r=refs["scene"]; n=refs["principles"]
    states=["risk","clear","protected","ignored"]
    actions=[dict(id=key,cost="0",enabled=["risk","clear"],feasible=["risk","clear"],
                  transitions={s:target if s in ("risk","clear") else s for s in states},observations={s:s for s in states})
             for key,target in [("protect","protected"),("ignore","ignored")]]
    mental=dict(id="notice",source_id="scene",frame_kind="SOURCE_DISCOURSE",assumptions=["interpretation"],
        active_assumptions=["interpretation","receipt"],unmodeled_segments=n,
        agents=[dict(id=a,label=a,source_id="scene",segment_ids=r) for a in ("ning","qing")],
        variables=[dict(id="risk",initial=True,observed_by=["qing"],segment_ids=r),dict(id="done",initial=False,observed_by=["ning","qing"],segment_ids=r)],
        events=[dict(id="notice",at=1,kind="message",effects={"risk":True},seen_by=[],received_by=["ning"],understood_by=["ning"],trusted_by=["ning"],assumptions=["receipt"],segment_ids=r)],
        queries=[dict(id="knows-risk",at=2,formula=dict(op="believes",agent="ning",arg=atom("risk")),segment_ids=r),
                 dict(id="qing-risk",at=2,formula=dict(op="believes",agent="qing",arg=atom("risk")),segment_ids=r)],
        plans=[dict(id="choice",actor="ning",at=2,graph=dict(states=states,terminal=["protected","ignored"],utilities=dict(risk="0",clear="0",protected="1",ignored="2"),actions=actions,horizon=1),
                    bindings=[dict(state="risk",when=atom("risk")),dict(state="clear",when=dict(op="not",arg=atom("risk")))],weights=None,policy=None,segment_ids=r)],causal=[])
    interaction=dict(through=2,max_ack_depth=2,utterances=[dict(id="offer",at=0,speaker="ning",audience=["qing"],version="v1",literal={},deliveries=[],segment_ids=r)],
        acts=[],games=[],commitments=[dict(id="verify",offer_id="offer",speaker="ning",recipient="qing",version="v1",condition=True,outcome=atom("done"),deadline=2,requires_acceptance=False,
            acceptance="QUALIFIED_ACT",activation="LATCHED",withdrawal="NO_RELEASE",segment_ids=r)])
    literals=[dict(id=key,atom=meaning,negative=neg,kind="CLAIM",segment_ids=allrefs if key=="known" else n)
              for key,meaning,neg in [("known","knowledge",False),("duty","duty",False),("not-duty","duty",True),("meeting","meeting",False),("responsible","responsible",False)]]
    argument=dict(id="norms",source_id="principles",frame_kind="SOURCE_DISCOURSE",assumptions=["norm-reconstruction"],active_assumptions=["norm-reconstruction","priority"],unmodeled_segments=[],literals=literals,
        premises=[dict(id=key,literal=literal,ordinary=ordinary,assumptions=[],segment_ids=allrefs if key=="fact-known" else n)
                  for key,literal,ordinary in [("fact-known","known",False),("liberty","not-duty",True),("meeting","meeting",False)]],
        rules=[dict(id="care-duty",premises=["known"],conclusion="duty",strict=False,assumptions=["priority"],segment_ids=n),
               dict(id="responsibility",premises=["known","duty"],conclusion="responsible",strict=False,assumptions=[],segment_ids=n)],
        priorities=[dict(better="care-duty",worse="liberty",segment_ids=n)],
        queries=[dict(id=key,literal=literal,preferred=False,critical_candidates=[],segment_ids=n) for key,literal in [("duty","duty"),("responsibility","responsible"),("meeting","meeting")]])
    facts=[dict(id="knowledge",kind="MENTAL_QUERY",role="KNOWLEDGE",reference=dict(query_id="knows-risk"),segment_ids=r),
           dict(id="control",kind="OPPORTUNITY",role="CONTROL",reference=dict(plan_id="choice",action_id="protect",view="WORLD"),segment_ids=r),
           dict(id="promise",kind="COMMITMENT",role="COMMITMENT",reference=dict(commitment_id="verify",at=2,status="BREACHED"),segment_ids=r)]
    dimensions=[dict(id=key,label=key,state_values={"risk":"0","clear":"0","protected":a,"ignored":b},action_costs={"protect":"0","ignore":"0"},segment_ids=n)
                for key,a,b in [("care","10","0"),("convenience","0","8")]]
    framework=dict(id="balanced",label="care with liberty dissent",origin=dict(kind="ANALYST_CONDITIONAL",declarer="analyst",at=0,frame_kind="SOURCE_DISCOURSE",segment_ids=n),
                   decision_rule="EXPECTED",weights=dict(care="1/4",convenience="3/4"),
                   norms=[dict(id="protect-known-risk",label="protection duty",permitted_actions=["protect"],guard_fact_ids=["knowledge","control"],argument_query_id="duty",segment_ids=n)],
                   assumptions=["principle"],active_assumptions=["principle"],segment_ids=n)
    decision=dict(id="notification",plan_id="choice",dimensions=dimensions,scenarios=[],frameworks=[framework],
                  responsibility_queries=[dict(query_id="responsibility",factor_ids=["knowledge","control","promise"],segment_ids=allrefs)],segment_ids=allrefs)
    return dict(schema="hcl-judgment-candidates-1",models=[dict(mental=mental,interaction=interaction,argument=argument,facts=facts,
        fact_bindings=[dict(premise_id="fact-known",fact_id="knowledge",expected=True,segment_ids=allrefs)],decisions=[decision])])

def witness():
    owner = Principal("synthetic-witness", "owner")
    rows = []
    with tempfile.TemporaryDirectory() as directory:
        store = StateStore.sqlite(Path(directory) / "state.sqlite", revision=True)
        store.create_session("s", owner, {"bob"})
        handles = (store.put_source("s", owner, "scene", SCENE),
                   store.put_source("s", owner, "principles", PRINCIPLES))
        try:
            for mode in ("known-duty", "no-receipt", "priority-reversed", "unknown-weights", "disputed", "withdrawn", "budget"):
                request = TaskRequest(mode, QUESTION, handles, "s", owner,
                    budget=ExecutionBudget(max_mock_calls=1, max_feedback=0,
                        max_local_evaluations=15 if mode == "budget" else 100000,
                        max_request_bytes=1048576, max_context_tokens=1048576,
                        max_output_bytes=1048576, max_total_output_bytes=8000000,
                        max_visible_output_tokens=1048576),
                    issue=ExecutionIssue("root", goals=(Issue(mode, "judgment.evaluate"),)))
                candidate = propose(store.snapshot("s", owner, handles), QUESTION)
                model = candidate["models"][0]
                frame = model["decisions"][0]["frameworks"][0]
                if mode == "no-receipt":
                    for key in ("received_by", "understood_by", "trusted_by"):
                        model["mental"]["events"][0][key] = []
                elif mode == "priority-reversed":
                    model["argument"]["priorities"][0].update(better="liberty", worse="care-duty")
                elif mode == "unknown-weights":
                    frame.update(weights=None, decision_rule="PARETO", norms=[])
                elif mode == "disputed":
                    model["argument"]["priorities"] = []
                elif mode == "withdrawn":
                    frame["active_assumptions"] = []
                port = OfflineModelPort(json.dumps(candidate, ensure_ascii=False))
                result = HCL(store, principal=owner, gateway=ModelGateway(store, port)).run_sync(request)
                assert result.status == "PARTIAL", result.diagnostics
                actual = next(r for r in store.inferences("s", owner)
                              if r.result_id in result.execution_receipt["result_ids"])
                decisions = actual.values["models"][0]["decisions"]
                if mode in ("known-duty", "no-receipt", "priority-reversed"):
                    assert decisions[0]["robust_across_frameworks"] == (("protect",) if mode == "known-duty" else ("ignore",))
                else:
                    assert all(not d["robust_across_frameworks"] for d in decisions)
                replay_port = OfflineModelPort("NO_NEW_SEND")
                replay = HCL(store, principal=owner, gateway=ModelGateway(store, replay_port)).run_sync(request)
                assert replay.answer == result.answer and replay_port.attempts == 0
                rows.append(dict(case=mode, status=result.status, usage=thaw(result.usage),
                    actual=thaw(actual.values), answer=result.answer,
                    claim_fields=[f.field for c in result.claim_records for f in c.used_result_fields],
                    unresolved=thaw(result.unresolved_issues), offline_attempts=port.attempts,
                    replay_new_attempts=0))
            store.set_readers("s", owner, "principles", {"bob"})
            denied = HCL(store, principal=owner).run_sync(request)
            assert denied.status == "DENIED" and not denied.answer and not denied.claim_records
            rows.append(dict(case="current-secondary-source-acl", status=denied.status, answer_absent=True))
        finally:
            store.close()
    root = Path(hcl.__file__).resolve().parents[1]
    return dict(schema="hcl-unified-conditional-judgment-witness-1",
        checked_commit=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip(),
        runtime_hashes={str(p.relative_to(root)): sha256(p.read_bytes()).hexdigest()
                        for p in sorted((root / "hcl").rglob("*.py"))},
        rows=rows, provider_calls=0, provider_spend_usd=0, sealed_content_reads=0,
        evidence_scope="INTEGRATED_OFFLINE_PARTIAL_SOURCE_BOUND_FINITE_SINGLE_STEP_JUDGMENT",
        not_established=["OPEN_EXTRACTION_ACCURACY", "CANDIDATE_COMPLETENESS", "USER_AUTHENTICATED_PRINCIPLE_ADOPTION",
            "MORAL_TRUTH", "PRIVATE_INTENTION_OR_BLAME", "UNRESTRICTED_CONCEPTUAL_SENSITIVITY", "MULTI_STEP_POLICY_JUDGMENT",
            "FULL_M14", "FULL_T17", "FULL_T18", "FULL_T19", "FULL_S3", "FULL_S4", "LIVE_EFFECT"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    args.output.write_text(json.dumps(witness(), ensure_ascii=False, sort_keys=True, indent=2) + "\n")
