"""Disconnected Chat Completions protocol -> real existing cognition -> answer.

Explicit source-bound candidate fixtures. No API, extraction or live evidence.
"""
import argparse
import asyncio
from dataclasses import replace
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import tempfile

from hcl import HCL, affect_request
from hcl.kernel.types import Principal, thaw
from hcl.memory import codec
from hcl.memory.store import StateStore
from hcl.models.candidate_contracts import CandidateAuthorization, MODE
from hcl.models.candidate_protocol import DisconnectedChatTransport, ENVELOPE
from hcl.models.controlled_candidates import ControlledCandidateGateway
from scripts import witness_unified_causal_affect as source_fixture


def protocol_return(candidate, versions):
    return json.dumps(dict(id="disconnected-chat-completion", object="chat.completion", model="explicit-host-model",
        choices=[dict(index=0,finish_reason="stop",message=dict(role="assistant",content=json.dumps(dict(
            schema=ENVELOPE,source_input_versions=dict(versions),candidate=candidate))))],
        usage=dict(prompt_tokens=1200,completion_tokens=3000,total_tokens=4200,
                   prompt_tokens_details=dict(cached_tokens=200))))


def execute(mode, *, stream=False, repair=False, unknown=False):
    with tempfile.TemporaryDirectory() as root:
        store=StateStore.sqlite(Path(root)/"state.sqlite",revision=True)
        owner=Principal("synthetic","owner");store.create_session("s",owner)
        handle=store.put_source("s",owner,"valve",source_fixture.SOURCE)
        request=affect_request("candidate-"+mode,"Why does B change their reaction and coping after the report?",
                               (handle,),"s",owner,budget=replace(source_fixture.budget(),max_mock_calls=0,max_feedback=1))
        snapshot=store.snapshot("s",owner,(handle,))
        candidate=source_fixture.candidate(snapshot,request.question,mode)
        good=protocol_return(candidate,snapshot.source_versions)
        responses=[None] if unknown else [good]
        if repair:
            invalid=json.loads(json.dumps(candidate));invalid["models"][0]["episodes"][0]["computed_score"]=100
            responses=[protocol_return(invalid,snapshot.source_versions),good]
        transport=DisconnectedChatTransport(responses)
        gateway=ControlledCandidateGateway(store,provider="explicit-host-provider",model="explicit-host-model",transport=transport)
        grant=CandidateAuthorization.for_request(request,authorization_id="explicit-host-grant",provider="explicit-host-provider",
            model="explicit-host-model",max_calls=2,max_cost_nanos=10**9,max_input_tokens=1048576,max_output_tokens=262144,
            rate_version="synthetic-rate-1",input_nanos_per_token=20,cached_input_nanos_per_token=10,output_nanos_per_token=80)
        gateway.register_authorization(request,grant)
        client=HCL(store,principal=owner,gateway=gateway)
        if stream:
            async def collect():return [event async for event in client.stream(request)]
            result=asyncio.run(collect())[-1].result
        else:result=client.run_sync(request)
        proof=[p for p in store.inferences("s",owner) if p.result_id in result.execution_receipt.get("result_ids",())]
        if unknown:
            assert result.status=="SEND_UNKNOWN" and not result.answer
            assert result.usage["held_simulated_cost_nanos"]==grant.reservation_nanos
            replay=client.run_sync(request);assert not replay.answer and len(transport.requests)==1
        else:
            assert result.status=="COMPLETED",result.diagnostics
            assert len(proof)==1 and result.usage["local_evaluations"]>0
            assert "Character-conditional but-for attribution" in result.answer
            replay=client.run_sync(request)
            assert replay.answer==result.answer and codec.dumps(replay.claim_records)==codec.dumps(result.claim_records)
        record=dict(status=result.status,usage=thaw(result.usage),transport_calls=len(transport.requests),
                    answer_sha256=sha256(result.answer.encode()).hexdigest(),
                    episodes=[] if not proof else [dict(attribution=thaw(e["derived"]["profiles"][0]["attribution"]),
                        coping=thaw(e["derived"]["coping"])) for e in proof[0].values["models"][0]["episodes"]])
        store.close()
        return record


def witness():
    records={name:execute(mode,**flags) for name,mode,flags in (
        ("ordinary","received",{}),("unreceived","unreceived",{}),
        ("stream","received",dict(stream=True)),("repair","received",dict(repair=True)),
        ("unknown","received",dict(unknown=True)))}
    before,after=records["ordinary"]["episodes"]
    assert before["attribution"]["candidates"][0]["possibilities"]==["CONTRIBUTES"]
    assert after["attribution"]["candidates"][0]["possibilities"]==["CAUSE_NOT_ACTUAL"]
    assert before["coping"][0]["branches"][0]["computation"]["best_actions"]==["wait"]
    assert after["coping"][0]["branches"][0]["computation"]["best_actions"]==["cross"]
    assert records["unreceived"]["episodes"][1]["attribution"]["candidates"][0]["possibilities"]==["CONTRIBUTES"]
    assert records["stream"]["answer_sha256"]==records["ordinary"]["answer_sha256"]
    assert records["repair"]["transport_calls"]==2
    assert records["repair"]["usage"]["observed_simulated_cost_nanos"]==524000
    root=Path(__file__).resolve().parents[1]
    return dict(head=subprocess.check_output(["git","rev-parse","HEAD"],cwd=root,text=True).strip(),
        runtime_sha256=sha256(codec.canonical({str(p.relative_to(root)):sha256(p.read_bytes()).hexdigest()
                         for p in sorted((root/"hcl").rglob("*.py"))}).encode()).hexdigest(),
        readiness="INTEGRATED_OFFLINE",accounting_mode=MODE,provider_calls=0,provider_spend_usd="0",sealed_reads=0,
        boundary="DISCONNECTED_PROTOCOL_AND_REAL_LOCAL_COMPUTATION_NOT_LIVE_OR_AUTOMATIC_EXTRACTION",checks=records)


if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--output",required=True);args=parser.parse_args()
    result=witness();Path(args.output).write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps(dict(head=result["head"],status="PASS",mode=MODE)))
