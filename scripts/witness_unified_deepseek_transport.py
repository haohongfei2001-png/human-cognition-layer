"""Isolated HTTP witness, not an external model run or extraction evaluation."""
import argparse
import asyncio
from copy import deepcopy
from dataclasses import replace
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import tempfile
import time

from hcl import HCL,affect_request
from hcl.kernel.types import Principal,thaw
from hcl.memory import codec
from hcl.memory.store import StateStore
from hcl.models.deepseek_contracts import DeepSeekBatchAuthorization,RESERVATION_NANOYUAN
from hcl.models.deepseek_gateway import DeepSeekCandidateGateway
from hcl.models.deepseek_transport import DeepSeekHTTPTransport
from hcl.runtime.deepseek_ledger import CNYBatchLedger
from scripts import witness_unified_causal_affect as fixture
from tests.test_unified_deepseek_transport import LoopbackHTTP,FakeCredentials,completion


def execute(mode,*,stream=False,repair=False,unknown=False):
    with tempfile.TemporaryDirectory() as directory:
        root=Path(directory);store=StateStore.sqlite(root/"state.sqlite",revision=True)
        owner=Principal("synthetic","owner");store.create_session("s",owner)
        handle=store.put_source("s",owner,"valve",fixture.SOURCE)
        request=affect_request("http-candidate","Why does B change their reaction and coping after the report?",(handle,),"s",owner,
            budget=replace(fixture.budget(),max_mock_calls=0,max_feedback=1))
        snapshot=store.snapshot("s",owner,(handle,));candidate=fixture.candidate(snapshot,request.question,mode)
        good=completion(candidate,snapshot.source_versions);responses=[None] if unknown else [good]
        if repair:
            bad=deepcopy(candidate);bad["models"][0]["episodes"][0]["computed_score"]=42
            responses=[completion(bad,snapshot.source_versions),good]
        now=int(time.time())
        grant=DeepSeekBatchAuthorization("synthetic-witness-batch",str(root/"cny.sqlite"),str(store.path),
            (sha256(codec.dumps(request)).hexdigest(),),now-1,now+600,"CNY","HCL_CORE_DEEPSEEK_DIRECT","SYNTHETIC_ONLY")
        batch=CNYBatchLedger.create(grant)
        gateway=DeepSeekCandidateGateway(store,authorization=grant,transport=DeepSeekHTTPTransport(FakeCredentials()))
        gateway.register_authorization(request);client=HCL(store,principal=owner,gateway=gateway)
        async def run():
            async with LoopbackHTTP(responses) as server:
                if stream:
                    events=[e async for e in client.stream(request)];result=events[-1].result
                else:result=await client.run(request)
                return result,len(server.requests)
        result,count=asyncio.run(run())
        proof=[p for p in store.inferences("s",owner) if p.result_id in result.execution_receipt.get("result_ids",())]
        if unknown:
            assert result.status=="SEND_UNKNOWN" and not result.answer
            assert batch.audit()["held_nanoyuan"]==RESERVATION_NANOYUAN
        else:
            assert result.status=="COMPLETED",result.diagnostics
            assert len(proof)==1 and result.usage["local_evaluations"]>0
            assert "Character-conditional but-for attribution" in result.answer
            replay=client.run_sync(request)
            assert replay.answer==result.answer and codec.dumps(replay.claim_records)==codec.dumps(result.claim_records)
        record=dict(status=result.status,loopback_http_exchanges=count,synthetic_usage=thaw(result.usage),
            answer_sha256=sha256(result.answer.encode()).hexdigest(),
            episodes=[] if not proof else [dict(attribution=thaw(e["derived"]["profiles"][0]["attribution"]),
                coping=thaw(e["derived"]["coping"])) for e in proof[0].values["models"][0]["episodes"]])
        gateway.close();batch.close();store.close();return record


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
    assert records["repair"]["loopback_http_exchanges"]==2
    root=Path(__file__).resolve().parents[1]
    return dict(head=subprocess.check_output(["git","rev-parse","HEAD"],cwd=root,text=True).strip(),
        runtime_sha256=sha256(codec.canonical({str(p.relative_to(root)):sha256(p.read_bytes()).hexdigest()
            for p in sorted((root/"hcl").rglob("*.py"))}).encode()).hexdigest(),
        readiness="INTEGRATED_OFFLINE",provider_calls=0,provider_spend_cny="0",provider_spend_usd="0",sealed_reads=0,
        boundary="ISOLATED_LOOPBACK_HTTP_SYNTHETIC_CANDIDATES_AND_USAGE_NOT_LIVE_EXTRACTION",checks=records)


if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--output",required=True);args=parser.parse_args()
    result=witness();Path(args.output).write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps(dict(head=result["head"],status="PASS",provider_calls=0,mode="LOOPBACK_ONLY")))
