"""Real HTTP bytes over isolated loopback. Zero external calls or credentials.

Only the connection is redirected by the test harness; production request
serialization, TLS configuration, HTTP framing, timeout and accounting code run.
These fixture candidates never count as live model extraction evidence.
"""
import asyncio
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import replace
from hashlib import sha256
import json
from pathlib import Path
import socket
import ssl
import tempfile
import time
import unittest
from unittest.mock import patch

from hcl import HCL, affect_request
from hcl.kernel.types import Principal, HCLFailure
from hcl.memory import codec
from hcl.memory.store import StateStore
from hcl.models.deepseek_contracts import *
from hcl.models.deepseek_gateway import DeepSeekCandidateGateway
from hcl.models.deepseek_protocol import parse_return, request_body
from hcl.models.deepseek_transport import DeepSeekHTTPTransport, DeepSeekTransportFailure
from hcl.models.candidate_protocol import ENVELOPE
from hcl.runtime.deepseek_ledger import CNYBatchLedger
from hcl.runtime.recovery import RecoveryManager
from scripts import witness_unified_causal_affect as fixture


class FakeCredentials:
    @contextmanager
    def borrow_bearer(self, endpoint):
        assert endpoint == ENDPOINT
        yield "synthetic-test-key-not-a-credential"


def completion(candidate, versions, **changes):
    data = dict(id="synthetic-deepseek-completion",object="chat.completion",model=MODEL_VERSION,
        choices=[dict(index=0,finish_reason="stop",message=dict(role="assistant",content=json.dumps(dict(
            schema=ENVELOPE,source_input_versions=dict(versions),candidate=candidate))))],
        usage=dict(prompt_tokens=1200,completion_tokens=3000,total_tokens=4200,
            prompt_cache_hit_tokens=200,prompt_cache_miss_tokens=1000,
            prompt_tokens_details=dict(cached_tokens=200),completion_tokens_details=dict(reasoning_tokens=0)))
    data.update(changes)
    return json.dumps(data).encode()


class LoopbackHTTP:
    def __init__(self, responses):
        self.responses, self.requests, self.handlers = list(responses), [], set()

    async def __aenter__(self):
        self.server = await asyncio.start_server(self.handle,"127.0.0.1",0)
        self.port = self.server.sockets[0].getsockname()[1]
        original = asyncio.open_connection
        async def connect(host, port, **kwargs):
            assert (host,port) == ("api.deepseek.com",443), "unexpected destination"
            assert kwargs["server_hostname"] == "api.deepseek.com"
            assert kwargs["ssl"].check_hostname and kwargs["ssl"].verify_mode == ssl.CERT_REQUIRED
            return await original("127.0.0.1",self.port,limit=kwargs["limit"])
        self.patch = patch("asyncio.open_connection",side_effect=connect)
        self.patch.start()
        # Deny all non-loopback socket egress, including accidental alternate APIs.
        original_connect = socket.socket.connect
        def socket_connect(sock, address):
            if isinstance(address,tuple) and address[0] not in ("127.0.0.1","::1"):
                raise AssertionError("external network forbidden")
            return original_connect(sock,address)
        self.socket_patch = patch.object(socket.socket,"connect",socket_connect)
        self.socket_patch.start()
        return self

    async def __aexit__(self,*args):
        self.patch.stop();self.socket_patch.stop()
        self.server.close();await self.server.wait_closed()
        for task in tuple(self.handlers):task.cancel()
        await asyncio.gather(*self.handlers,return_exceptions=True)

    async def handle(self,reader,writer):
        self.handlers.add(asyncio.current_task())
        try:
            head = await reader.readuntil(b"\r\n\r\n")
            fields = dict(line.split(b": ",1) for line in head.split(b"\r\n")[1:-2])
            body = await reader.readexactly(int(fields[b"Content-Length"]))
            self.requests.append((head,body))
            value = self.responses.pop(0)
            if callable(value):
                await value(writer)
                return
            if value is None:return
            if isinstance(value,tuple):
                code,payload=value
            else:code,payload=200,value
            writer.write((f"HTTP/1.1 {code} Test\r\nContent-Type: application/json\r\nContent-Length: {len(payload)}\r\n\r\n").encode()+payload)
            await writer.drain()
        except (ConnectionError,asyncio.IncompleteReadError):pass
        finally:
            writer.close()
            self.handlers.discard(asyncio.current_task())


class DeepSeekHTTPTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.store=StateStore.sqlite(self.root/"state.sqlite",revision=True);self.addCleanup(self.store.close)
        self.owner=Principal("synthetic","owner");self.store.create_session("s",self.owner,{"other"})
        handle=self.store.put_source("s",self.owner,"valve",fixture.SOURCE)
        self.request=affect_request("ordinary","Why does B change their reaction and coping after the report?",(handle,),"s",self.owner,
            budget=replace(fixture.budget(),max_mock_calls=0,max_feedback=1))
        self.snapshot=self.store.snapshot("s",self.owner,(handle,))
        self.candidate=fixture.candidate(self.snapshot,self.request.question)
        self.second=replace(self.request,request_id="second")
        now=int(time.time())
        self.grant=DeepSeekBatchAuthorization("synthetic-new-batch",str(self.root/"cny.sqlite"),str(self.store.path),
            tuple(sha256(codec.dumps(r)).hexdigest() for r in (self.request,self.second)),now-1,now+600,"CNY","HCL_CORE_DEEPSEEK_DIRECT","SYNTHETIC_ONLY")
        self.batch=CNYBatchLedger.create(self.grant);self.addCleanup(self.batch.close)

    def gateway(self,**kwargs):
        gateway=DeepSeekCandidateGateway(self.store,authorization=self.grant,transport=DeepSeekHTTPTransport(FakeCredentials(),**kwargs))
        self.addCleanup(gateway.close)
        gateway.register_authorization(self.request);gateway.register_authorization(self.second)
        return gateway

    def run_case(self,responses,request=None,**kwargs):
        gateway=self.gateway(**kwargs)
        async def run():
            async with LoopbackHTTP(responses) as server:
                result=await HCL(self.store,principal=self.owner,gateway=gateway).run(request or self.request)
                return result,server.requests
        result,requests=asyncio.run(run())
        return result,gateway,requests

    def test_real_sender_bytes_actual_cognition_answer_and_native_cny(self):
        result,gateway,requests=self.run_case([completion(self.candidate,self.snapshot.source_versions)])
        self.assertEqual(result.status,"COMPLETED",result.diagnostics)
        self.assertIn("Character-conditional but-for attribution",result.answer)
        self.assertIn("CONTRIBUTES",result.answer);self.assertIn("CAUSE_NOT_ACTUAL",result.answer)
        head,raw=requests[0];body=json.loads(raw)
        self.assertIn(b"POST /chat/completions HTTP/1.1",head)
        self.assertEqual(set(body),{"model","messages","response_format","max_tokens","thinking","reasoning_effort","temperature","tool_choice","stream"})
        self.assertEqual(body["max_tokens"],16384);self.assertEqual(body["thinking"],{"type":"disabled"})
        self.assertEqual(body["tool_choice"],"none");self.assertFalse(body["stream"])
        self.assertEqual(result.usage["mock_calls"],0);self.assertEqual(result.usage["provider_calls"],1)
        self.assertEqual(result.usage["observed_usage_cost_upper_nanoyuan"],90060000)
        self.assertIsNone(result.usage["actual_billed_cny"])
        self.assertNotIn("simulated_cost_unknown",result.usage)
        self.assertEqual(gateway.batch_usage()["claimed_calls"],1)
        self.assertEqual(RESERVATION_NANOYUAN,9880416000)
        self.assertLess(2*RESERVATION_NANOYUAN,20000000000)
        replay=HCL(self.store,principal=self.owner,gateway=gateway).run_sync(self.request)
        self.assertEqual(replay.answer,result.answer);self.assertEqual(codec.dumps(replay.claim_records),codec.dumps(result.claim_records))

    def test_one_semantic_repair_consumes_whole_shared_batch(self):
        bad=deepcopy(self.candidate);bad["models"][0]["episodes"][0]["computed_score"]=42
        result,gateway,requests=self.run_case([completion(bad,self.snapshot.source_versions),completion(self.candidate,self.snapshot.source_versions)])
        self.assertEqual(result.status,"COMPLETED",result.diagnostics)
        self.assertEqual(len(requests),2);self.assertEqual(gateway.batch_usage()["claimed_calls"],2)
        self.assertIn("repair_obligation",json.loads(json.loads(requests[1][1])["messages"][1]["content"]))
        second=HCL(self.store,principal=self.owner,gateway=gateway).run_sync(self.second)
        self.assertEqual(second.status,"BUDGET_EXHAUSTED")
        self.assertEqual(gateway.batch_usage()["claimed_calls"],2)

    def test_two_tasks_share_two_calls_not_two_each(self):
        gateway=self.gateway()
        async def run():
            async with LoopbackHTTP([completion(self.candidate,self.snapshot.source_versions)]*2) as server:
                client=HCL(self.store,principal=self.owner,gateway=gateway)
                a=await client.run(self.request);b=await client.run(self.second)
                return a,b,len(server.requests)
        a,b,count=asyncio.run(run())
        self.assertEqual((a.status,b.status,count),("COMPLETED","COMPLETED",2))
        self.assertEqual(gateway.batch_usage()["claimed_calls"],2)

    def test_http_errors_redirect_disconnect_do_not_retry_and_hold_full(self):
        for value in [(c,b"never persist this error body") for c in (301,302,307,308,401,402,429,500,503)]+[None]:
            with self.subTest(value=value):
                # New explicit synthetic batch per case, no reuse/reset.
                self.tearDown();self.doCleanups();self.setUp()
                result,gateway,requests=self.run_case([value])
                self.assertEqual(result.status,"SEND_UNKNOWN",result.diagnostics)
                self.assertEqual(len(requests),1)
                self.assertEqual(gateway.batch_usage()["held_nanoyuan"],RESERVATION_NANOYUAN)
                self.assertEqual(gateway.batch_usage()["status"],"BLOCKED")
                second=HCL(self.store,principal=self.owner,gateway=gateway).run_sync(self.second)
                self.assertFalse(second.answer);self.assertEqual(gateway.batch_usage()["claimed_calls"],1)

    def test_usage_identity_length_cache_reasoning_and_duplicate_keys_fail_closed(self):
        good=json.loads(completion(self.candidate,self.snapshot.source_versions))
        cases=[]
        for field,value in (("usage",None),("model","deepseek-flash"),("id",None)):
            item=deepcopy(good);item[field]=value;cases.append(json.dumps(item).encode())
        for mutate in (
            lambda d:d["choices"][0].update(finish_reason="length"),
            lambda d:d["usage"].update(prompt_cache_miss_tokens=900),
            lambda d:d["usage"]["prompt_tokens_details"].update(cached_tokens=0),
            lambda d:d["usage"].update(prompt_tokens=True),
            lambda d:d["usage"].update(completion_tokens=OUTPUT_TOKENS+1,total_tokens=1200+OUTPUT_TOKENS+1),
            lambda d:d["usage"]["completion_tokens_details"].update(reasoning_tokens=1),
            lambda d:d["choices"][0]["message"].update(reasoning_content="never-store-private-reasoning"),
        ):
            item=deepcopy(good);mutate(item);cases.append(json.dumps(item).encode())
        cases.append(completion(self.candidate,self.snapshot.source_versions).replace(b'"object":',b'"id":"duplicate","object":',1))
        for raw in cases:
            receipt=parse_return(raw,MAX_VISIBLE_BYTES)
            self.assertIsNotNone(receipt.validation_code)
            self.assertNotIn("never-store-private-reasoning",codec.dumps(receipt).decode())
        result,gateway,_=self.run_case([cases[0]])
        self.assertEqual(result.status,"FAILED");self.assertEqual(gateway.batch_usage()["held_nanoyuan"],RESERVATION_NANOYUAN)
        self.assertEqual(gateway.batch_usage()["claimed_calls"],1)

    def test_slow_header_body_absolute_timeout_and_response_capacity(self):
        async def slow_header(w):
            for part in (b"HTTP/1.1 200 OK\r\n",b"Content-Type: application/json\r\n",b"\r\n"):
                w.write(part);await w.drain();await asyncio.sleep(.06)
        async def slow_body(w):
            w.write(b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: 100\r\n\r\n")
            for _ in range(100):
                w.write(b" ");await w.drain();await asyncio.sleep(.02)
        async def too_large(w):
            w.write(b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: 9999999\r\n\r\n");await w.drain()
        for response in (slow_header,slow_body,too_large):
            self.doCleanups();self.setUp()
            started=time.monotonic()
            result,gateway,requests=self.run_case([response],connect_timeout=.05,absolute_timeout=.1)
            self.assertLess(time.monotonic()-started,2)
            self.assertEqual(result.status,"SEND_UNKNOWN");self.assertEqual(len(requests),1)
            self.assertEqual(gateway.batch_usage()["held_nanoyuan"],RESERVATION_NANOYUAN)

    def test_revocation_cross_connection_and_acl_at_last_send_gate(self):
        for kind in ("grant","acl"):
            self.doCleanups();self.setUp()
            gateway=self.gateway()
            original=self.store._checkpoint
            def checkpoint(stage):
                if stage=="call_reserved":
                    if kind=="grant":self.batch.stop("REVOKED")
                    else:self.store.set_readers("s",self.owner,"valve",{"other"})
                return original(stage)
            async def run():
                async with LoopbackHTTP([]) as server:
                    with patch.object(self.store,"_checkpoint",side_effect=checkpoint):
                        result=await HCL(self.store,principal=self.owner,gateway=gateway).run(self.request)
                    return result,len(server.requests)
            result,count=asyncio.run(run())
            self.assertEqual(count,0);self.assertFalse(result.answer)
            self.assertEqual(gateway.batch_usage()["held_nanoyuan"],RESERVATION_NANOYUAN)

    def test_crash_seams_reopen_no_reset_no_resend(self):
        for seam in ("cny_claim_reserved","call_reserved","send_started","response_received","cny_task_return_persisted"):
            self.doCleanups();self.setUp()
            gateway=self.gateway()
            class Crash(BaseException):pass
            async def run():
                async with LoopbackHTTP([completion(self.candidate,self.snapshot.source_versions)]) as server:
                    with patch.object(self.store,"_checkpoint",side_effect=lambda stage: (_ for _ in ()).throw(Crash()) if stage==seam else None):
                        with self.assertRaises(Crash):
                            await HCL(self.store,principal=self.owner,gateway=gateway).run(self.request)
                    return len(server.requests)
            count=asyncio.run(run());audit=self.batch.audit()
            self.assertEqual(audit["claimed_calls"],1);self.assertEqual(audit["held_nanoyuan"],RESERVATION_NANOYUAN)
            reopened=CNYBatchLedger(self.grant);self.addCleanup(reopened.close)
            self.assertEqual(reopened.audit(),audit)
            with self.assertRaises(HCLFailure):reopened.reserve("f"*64,self.grant.task_fingerprints[1])
            with self.assertRaises(FileExistsError):CNYBatchLedger.create(self.grant)
            self.assertLessEqual(count,1)

    def test_cross_connection_concurrent_claims_only_one_wins(self):
        from concurrent.futures import ThreadPoolExecutor
        import threading
        barrier=threading.Barrier(2)
        def claim(i):
            ledger=CNYBatchLedger(self.grant)
            try:
                barrier.wait()
                ledger.reserve(str(i)*64,self.grant.task_fingerprints[i])
                return True
            except HCLFailure:return False
            finally:ledger.close()
        with ThreadPoolExecutor(2) as pool:results=list(pool.map(claim,(0,1)))
        self.assertEqual(sorted(results),[False,True]);self.assertEqual(self.batch.audit()["claimed_calls"],1)

    def test_chunked_framing_success_and_malformed_framing_fail_closed(self):
        raw=completion(self.candidate,self.snapshot.source_versions)
        async def chunked(w):
            w.write(b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nTransfer-Encoding: chunked\r\n\r\n")
            for part in (raw[:20],raw[20:]):w.write((hex(len(part))[2:]+"\r\n").encode()+part+b"\r\n")
            w.write(b"0\r\n\r\n");await w.drain()
        result,_,_=self.run_case([chunked]);self.assertEqual(result.status,"COMPLETED",result.diagnostics)
        headers=[
            b"Content-Length: 2\r\nContent-Length: 2", b"Content-Encoding: gzip\r\nContent-Length: 2",
            b"Content-Length: 2\r\nTransfer-Encoding: chunked", b"Content-Length: 999",
            b"X-Fill: "+b"x"*17000,
        ]
        for header in headers:
            self.doCleanups();self.setUp()
            async def send(w,head=header):
                w.write(b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n"+head+b"\r\n\r\n{}");await w.drain()
            result,gateway,requests=self.run_case([send])
            self.assertEqual(result.status,"SEND_UNKNOWN");self.assertEqual(len(requests),1)
            self.assertEqual(gateway.batch_usage()["held_nanoyuan"],RESERVATION_NANOYUAN)

    def test_synchronous_gate_and_credential_delay_cannot_send_after_deadline(self):
        for seam in ("credential","gate"):
            self.doCleanups();self.setUp()
            gateway=self.gateway(connect_timeout=.05,absolute_timeout=.1)
            @contextmanager
            def borrow(endpoint):
                if seam=="credential":time.sleep(.15)
                yield "synthetic-test-key"
            def checkpoint(stage):
                if seam=="gate" and stage=="send_started":time.sleep(.15)
            async def run():
                async with LoopbackHTTP([]) as server:
                    with patch.object(gateway._transport._credentials,"borrow_bearer",borrow),patch.object(self.store,"_checkpoint",checkpoint):
                        result=await HCL(self.store,principal=self.owner,gateway=gateway).run(self.request)
                    return result,len(server.requests)
            result,count=asyncio.run(run())
            self.assertEqual(count,0);self.assertFalse(result.answer)
            self.assertEqual(gateway.batch_usage()["held_nanoyuan"],RESERVATION_NANOYUAN)

    def test_connection_timeout_and_cancellation_never_retry(self):
        gateway=self.gateway(connect_timeout=.02,absolute_timeout=.05)
        async def slow_connect(*args,**kwargs):await asyncio.sleep(1)
        with patch("asyncio.open_connection",side_effect=slow_connect):
            result=HCL(self.store,principal=self.owner,gateway=gateway).run_sync(self.request)
        self.assertEqual(result.status,"SEND_UNKNOWN");self.assertEqual(self.batch.audit()["claimed_calls"],1)
        self.doCleanups();self.setUp();gateway=self.gateway()
        async def hang(w):await asyncio.sleep(20)
        async def run():
            async with LoopbackHTTP([hang]) as server:
                task=asyncio.create_task(HCL(self.store,principal=self.owner,gateway=gateway).run(self.request))
                while not server.requests:await asyncio.sleep(.005)
                task.cancel()
                with self.assertRaises(asyncio.CancelledError):await task
                return len(server.requests)
        self.assertEqual(asyncio.run(run()),1)
        self.assertEqual(self.batch.audit()["held_nanoyuan"],RESERVATION_NANOYUAN)
        self.assertEqual(self.batch.audit()["status"],"BLOCKED")

    def test_sidecar_corruption_and_schema_mismatch_fail_closed(self):
        for corruption in ("negative_usage","false_cost","state","hash","schema"):
            self.doCleanups();self.setUp()
            _,gateway,_=self.run_case([completion(self.candidate,self.snapshot.source_versions)])
            db=self.batch._db
            if corruption in ("negative_usage","false_cost"):
                row=db.execute("SELECT receipt FROM claims").fetchone()
                receipt=codec.loads(row[0])
                receipt=replace(receipt,input_tokens=-1) if corruption=="negative_usage" else replace(receipt,usage_cost_upper_nanoyuan=1)
                db.execute("UPDATE claims SET receipt=?",(codec.dumps(receipt),))
            elif corruption=="state":
                receipt=codec.loads(db.execute("SELECT receipt FROM claims").fetchone()[0])
                db.execute("UPDATE claims SET receipt=?",(codec.dumps(replace(receipt,validation_code="DEEPSEEK_FINISH_REJECTED")),))
            elif corruption=="hash":db.execute("UPDATE claims SET claim_id='bad'")
            else:db.execute("ALTER TABLE claims ADD COLUMN unexpected TEXT")
            with self.assertRaises(HCLFailure):self.batch.reserve("f"*64,self.grant.task_fingerprints[1])

    def test_known_native_return_and_computation_recover_without_new_authority_or_send(self):
        for seam in ("return_persisted","execution_computed","execution_effects_committed"):
            self.doCleanups();self.setUp();gateway=self.gateway()
            class Crash(BaseException):pass
            async def run():
                async with LoopbackHTTP([completion(self.candidate,self.snapshot.source_versions)]) as server:
                    with patch.object(self.store,"_checkpoint",side_effect=lambda s: (_ for _ in ()).throw(Crash()) if s==seam else None):
                        with self.assertRaises(Crash):await HCL(self.store,principal=self.owner,gateway=gateway).run(self.request)
                    return len(server.requests)
            self.assertEqual(asyncio.run(run()),1)
            old_owner=self.store.owner_id;self.store.close()
            self.store=StateStore.sqlite(self.root/"state.sqlite");self.addCleanup(self.store.close)
            replacement=DeepSeekCandidateGateway(self.store,authorization=self.grant,transport=DeepSeekHTTPTransport(FakeCredentials()))
            self.addCleanup(replacement.close)
            RecoveryManager(self.store).resume_execution(self.request,expected_owner_id=old_owner)
            with patch.object(DeepSeekHTTPTransport,"send",side_effect=AssertionError("recovery cannot send")):
                result=HCL(self.store,principal=self.owner,gateway=replacement).run_sync(self.request)
            self.assertEqual(result.status,"COMPLETED",result.diagnostics)
            self.assertEqual(self.batch.audit()["claimed_calls"],1)
            self.assertEqual(result.usage["observed_usage_cost_upper_nanoyuan"],90060000)

    def test_expiry_during_final_acl_gate_prevents_dispatch(self):
        claim="e"*64;self.batch.reserve(claim,self.grant.task_fingerprints[0])
        clock=[self.grant.expires_at-1]
        with patch("hcl.runtime.deepseek_ledger.time.time",side_effect=lambda:clock[0]):
            def authorize():clock[0]=self.grant.expires_at+1
            with self.assertRaises(HCLFailure):self.batch.dispatch(claim,authorize)
        self.assertEqual(self.batch.audit()["states"],("RESERVED",))
        self.assertEqual(self.batch.audit()["held_nanoyuan"],RESERVATION_NANOYUAN)

    def test_task_output_budget_below_wire_and_expired_tariff_refused(self):
        gateway=self.gateway()
        small=replace(self.request,budget=replace(self.request.budget,max_visible_output_tokens=1000))
        with self.assertRaises(HCLFailure):gateway.register_authorization(small)
        with patch("hcl.runtime.deepseek_ledger.time.time",return_value=self.grant.expires_at+1):
            with self.assertRaises(HCLFailure):self.batch.reserve("f"*64,self.grant.task_fingerprints[0])
        self.assertEqual(self.batch.audit()["claimed_calls"],0)

    def test_missing_expired_foreign_currency_and_closed_grants_cannot_send(self):
        with self.assertRaises(ValueError):replace(self.grant,account_currency="USD")
        with self.assertRaises(ValueError):replace(self.grant,model="deepseek-flash")
        with self.assertRaises(HCLFailure):CNYBatchLedger(replace(self.grant,ledger_path=str(self.root/"missing.sqlite")))
        self.batch.stop("CLOSED")
        with self.assertRaises(HCLFailure):self.gateway()
        self.assertEqual(self.batch.audit()["status"],"CLOSED")


if __name__=="__main__":unittest.main()
