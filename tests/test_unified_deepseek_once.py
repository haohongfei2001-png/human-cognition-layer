"""New one-use guard tests. Local synthetic Git and loopback; never real secrets."""
import asyncio
from copy import deepcopy
from contextlib import contextmanager,ExitStack
from dataclasses import replace
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sqlite3
import tempfile
import time
import unittest
from unittest.mock import patch

from hcl.memory import codec
from hcl.memory.store import StateStore
from hcl.kernel.types import Principal
from scripts import deepseek_core_smoke_once as once
from scripts import deepseek_core_smoke_lifecycle as lifecycle
from scripts import witness_unified_causal_affect as fixture
from tests.test_unified_deepseek_transport import LoopbackHTTP,completion


class OnceGuardTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        self.identity=dict(run_id="123",head_sha="c"*40)
        self.environment=dict(GITHUB_REPOSITORY=once.REPOSITORY,GITHUB_REF="refs/heads/main",GITHUB_EVENT_NAME="push",
            GITHUB_RUN_ATTEMPT="1",GITHUB_WORKFLOW_REF=once.REPOSITORY+"/"+once.WORKFLOW+"@refs/heads/main",
            GITHUB_RUN_ID="123",GITHUB_SHA="c"*40,SECRET_PRESENT="true",DEEPSEEK_API_KEY="synthetic-test-only")
        self.pages=[dict(total_count=1,workflow_runs=[dict(id=123,workflow_id=456,run_attempt=1,head_branch="main",
            path=once.WORKFLOW,head_sha="c"*40,event="push")])]

    def test_default_closed_no_marker_no_credential_or_network(self):
        # Preparation is an explicit fixture, not an invariant that forbids the
        # authorized grant/marker/closure lifecycle forever in provider-free CI.
        (self.root/once.GRANT).parent.mkdir(parents=True)
        (self.root/once.GRANT).write_text(json.dumps(lifecycle.UNISSUED))
        closed=once.load_json(self.root/once.GRANT)
        self.assertFalse((self.root/once.MARKER).exists())
        original_load=once.load_json
        def load(path,*args):
            return closed if path==once.ROOT/once.GRANT else original_load(path,*args)
        with patch.dict(os.environ,self.environment,clear=True),patch.object(once,"load_json",side_effect=load),\
                patch.object(once.ExistingCoreCredentialProvider,"borrow_bearer",side_effect=AssertionError("no key access")) as credential,\
                patch.object(once,"opener",side_effect=AssertionError("no network")) as network,\
                patch.object(once.DeepSeekHTTPTransport,"send",side_effect=AssertionError("no model")) as sender:
            with self.assertRaisesRegex(ValueError,"EXACT_NEW_GRANT_REQUIRED"):once.preflight()
        credential.assert_not_called();network.assert_not_called();sender.assert_not_called()

    def test_current_repository_has_exact_versioned_lifecycle(self):
        with patch.object(once.ExistingCoreCredentialProvider,"borrow_bearer",side_effect=AssertionError("no key")),\
                patch.object(once,"opener",side_effect=AssertionError("no network")):
            self.assertIn(lifecycle.validate_repository(once.ROOT),
                {"PREPARATION","GRANT_COMMITTED","MARKER_COMMITTED","CLOSED_CONSUMED","CLOSED_BLOCKED","CLOSED_CANCELLED"})

    def test_historical_runtime_projection_matches_live_grant_before_issuance(self):
        head=lifecycle.text(once.ROOT,"rev-parse","HEAD")
        grant=lifecycle.document(once.ROOT,head,once.GRANT)
        if grant["status"]=="CLOSED_UNISSUED":
            self.assertEqual(lifecycle.historical_grant(once.ROOT,head),once.expected_grant(head))
        else:
            # Later runtime/case changes must not be used to rewrite history.
            original=lifecycle.historical_grant(once.ROOT,grant["executor_commit"])
            self.assertEqual(original,{k:grant[k] for k in original} | {"status":"READY"})

    def _lifecycle_repo(self,name="fixture"):
        root=self.root/name;root.mkdir()
        def git(*args):return subprocess.check_output(["git","-C",str(root),*args],text=True,stderr=subprocess.DEVNULL).strip()
        def commit(message):
            git("add",".");git("commit","-m",message)
            return git("rev-parse","HEAD")
        def write(path,value):
            target=root/path;target.parent.mkdir(parents=True,exist_ok=True)
            target.write_text(json.dumps(value))
        git("init");git("config","user.name","Synthetic Test");git("config","user.email","test@example.invalid")
        checked=lifecycle.text(once.ROOT,"rev-parse","HEAD")
        current=lifecycle.document(once.ROOT,checked,lifecycle.GRANT)
        historical=current.get("executor_commit",checked)
        for path in (lifecycle.CASE,*lifecycle.READERS):
            target=root/path;target.parent.mkdir(parents=True,exist_ok=True)
            target.write_bytes(lifecycle.git(once.ROOT,"show",historical+":"+path))
        runtime=b"# Historical synthetic runtime, hashed but never executed.\n"
        (root/"hcl").mkdir();(root/"hcl/runtime.py").write_bytes(runtime)
        write(once.GRANT,lifecycle.UNISSUED);executor=commit("executor")
        grant=dict(schema="hcl-deepseek-core-smoke-grant-1",status="READY",campaign="hcl-core-deepseek-synthetic-v1",
            executor_commit=executor,case_sha256=lifecycle.CASE_HASH,
            runtime_sha256=once.hash_value({"runtime.py":sha256(runtime).hexdigest()}),reader_sha256=dict(lifecycle.READERS),
            currency="CNY",authorized_cny="20.00",authorized_calls=2,max_semantic_repairs=1,
            model="deepseek-v4-pro",model_version="DeepSeek-V4-Pro-0813",endpoint="https://api.deepseek.com/chat/completions",
            account_scope="HCL_CORE_DEEPSEEK_DIRECT",source_policy="SYNTHETIC_ONLY",retries=0,
            historical_budget_transfer=False,publication="SYNTHETIC_RESULT_AND_MECHANICAL_USAGE_ONLY")
        return root,git,commit,write,executor,grant

    def _lifecycle_to_marker(self,name="fixture"):
        root,git,commit,write,executor,grant=self._lifecycle_repo(name)
        self.assertEqual(lifecycle.validate_repository(root),"PREPARATION")
        write(once.GRANT,grant);adopted=commit("grant")
        self.assertEqual(lifecycle.validate_repository(root),"GRANT_COMMITTED")
        marker=dict(schema="hcl-deepseek-core-smoke-marker-1",campaign=lifecycle.CAMPAIGN,executor_commit=executor,
            grant_commit=adopted,grant_sha256=once.hash_value(grant),case_sha256=lifecycle.CASE_HASH)
        write(once.MARKER,marker);marker_head=commit("marker")
        self.assertEqual(lifecycle.validate_repository(root),"MARKER_COMMITTED")
        return root,git,commit,write,grant,marker,marker_head

    def test_lifecycle_all_phases_close_then_allow_ordinary_runtime_update(self):
        for status in ("CLOSED_CONSUMED","CLOSED_BLOCKED"):
            root,git,commit,write,grant,marker,marker_head=self._lifecycle_to_marker(status)
            closure=dict(schema="hcl-deepseek-core-smoke-closure-1",marker_commit=marker_head,run_id="123",receipt_sha256="a"*64)
            write(once.GRANT,dict(grant,status=status,closure=closure));commit("terminal grant only")
            self.assertEqual(lifecycle.validate_repository(root),status)
            (root/"hcl/runtime.py").write_text("# New ordinary runtime after the closed experiment.\n")
            (root/lifecycle.CASE).write_text("# Future source module is not historical grant evidence.\n")
            commit("normal later development")
            self.assertEqual(lifecycle.validate_repository(root),status)
            # The execution validator is not expanded by the audit's states.
            with self.assertRaises(ValueError):once.validate_grant(lifecycle.document(root,git("rev-parse","HEAD"),once.GRANT))

    def test_lifecycle_rejects_arbitrary_ready_wrong_parent_and_extra_changes(self):
        for mutation in ("budget","executor","runtime","case","extra_file","bool_calls"):
            root,git,commit,write,executor,grant=self._lifecycle_repo(mutation)
            if mutation=="extra_file":(root/"unreviewed.txt").write_text("synthetic")
            else:
                key,value={"budget":("authorized_cny","20.01"),"executor":("executor_commit","a"*40),
                    "runtime":("runtime_sha256","a"*64),"case":("case_sha256","a"*64),"bool_calls":("authorized_calls",True)}[mutation]
                grant[key]=value
            write(once.GRANT,grant);commit("invalid grant")
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):lifecycle.validate_repository(root)

    def test_lifecycle_rejects_wrong_marker_close_reset_and_change_then_revert(self):
        for mutation in ("marker_hash","closure_extra","closure_receipt","close_extra_file","marker_revert","grant_revert","reset"):
            root,git,commit,write,grant,marker,marker_head=self._lifecycle_to_marker(mutation)
            if mutation=="marker_hash":
                write(once.MARKER,dict(marker,grant_sha256="b"*64));commit("wrong marker")
            else:
                closure=dict(schema="hcl-deepseek-core-smoke-closure-1",marker_commit=marker_head,run_id="123",receipt_sha256="a"*64)
                if mutation=="closure_extra":closure["extra"]=True
                if mutation=="closure_receipt":closure["receipt_sha256"]="unknown"
                if mutation=="close_extra_file":(root/"other.txt").write_text("synthetic")
                terminal=dict(grant,status="CLOSED_CONSUMED",closure=closure)
                write(once.GRANT,terminal);commit("closure")
                if mutation in ("marker_revert","grant_revert"):
                    path,value=(once.MARKER,marker) if mutation=="marker_revert" else (once.GRANT,terminal)
                    write(path,dict(value,extra=True));commit("changed protected path")
                    write(path,value);commit("reverted protected path")
                if mutation=="reset":
                    (root/once.MARKER).unlink();write(once.GRANT,lifecycle.UNISSUED);commit("forbidden reset")
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):lifecycle.validate_repository(root)

    def test_lifecycle_cannot_reset_grant_without_ever_sending(self):
        root,git,commit,write,executor,grant=self._lifecycle_repo()
        write(once.GRANT,grant);commit("grant")
        write(once.GRANT,lifecycle.UNISSUED);commit("forbidden reset before marker")
        with self.assertRaises(ValueError):lifecycle.validate_repository(root)

    def test_lifecycle_pretrigger_cancel_is_terminal_and_never_accepts_marker(self):
        root,git,commit,write,executor,grant=self._lifecycle_repo()
        write(once.GRANT,grant);adopted=commit("grant")
        closure=dict(schema="hcl-deepseek-core-smoke-closure-1",grant_commit=adopted,reason="CANCELLED_BEFORE_TRIGGER")
        terminal=dict(grant,status="CLOSED_CANCELLED",closure=closure)
        write(once.GRANT,terminal);commit("cancel before marker")
        self.assertEqual(lifecycle.validate_repository(root),"CLOSED_CANCELLED")
        (root/"hcl/runtime.py").write_text("# ordinary development\n");commit("later code")
        self.assertEqual(lifecycle.validate_repository(root),"CLOSED_CANCELLED")
        with self.assertRaises(ValueError):once.validate_grant(terminal)
        write(once.MARKER,dict(schema="hcl-deepseek-core-smoke-marker-1",campaign=lifecycle.CAMPAIGN,
            executor_commit=executor,grant_commit=adopted,grant_sha256=once.hash_value(grant),case_sha256=lifecycle.CASE_HASH))
        commit("forbidden marker after cancel")
        with self.assertRaises(ValueError):lifecycle.validate_repository(root)

    def test_identity_and_complete_history_reject_replay_and_forgery(self):
        self.assertEqual(once.environment_identity(self.environment),self.identity)
        once.validate_history(self.pages,self.identity)
        for name,value in (("GITHUB_REPOSITORY","other/repo"),("GITHUB_REF","refs/heads/topic"),("GITHUB_EVENT_NAME","workflow_dispatch"),
            ("GITHUB_RUN_ATTEMPT","2"),("GITHUB_WORKFLOW_REF","other"),("GITHUB_RUN_ID","１２３")):
            with self.subTest(name=name),self.assertRaises(ValueError):once.environment_identity(dict(self.environment,**{name:value}))
        for pages in ([],[dict(total_count=2,workflow_runs=self.pages[0]["workflow_runs"])],self.pages+self.pages,
            [dict(total_count=1,workflow_runs=[])],[dict(total_count=True,workflow_runs=self.pages[0]["workflow_runs"])]):
            with self.assertRaises(ValueError):once.validate_history(pages,self.identity)
        for name,value in (("id",124),("workflow_id",True),("run_attempt",2),("path","old.yml"),("head_sha","d"*40),("event","workflow_dispatch"),("head_branch","topic")):
            pages=deepcopy(self.pages);pages[0]["workflow_runs"][0][name]=value
            with self.subTest(name=name),self.assertRaises(ValueError):once.validate_history(pages,self.identity)

    def test_new_grant_is_exact_currency_budget_model_case_runtime_and_reader_bound(self):
        grant=once.expected_grant("a"*40);once.validate_grant(grant)
        for name,value in (("status","CLOSED"),("authorized_calls",True),("authorized_calls",3),("authorized_cny","20.01"),
            ("currency","USD"),("model","deepseek-flash"),("case_sha256","b"*64),("runtime_sha256","b"*64),
            ("historical_budget_transfer",True),("retries",1),("reader_sha256",{})):
            with self.subTest(name=name),self.assertRaises(ValueError):once.validate_grant(dict(grant,**{name:value}))

    def test_real_git_exact_three_commit_chain_and_permanent_first_run(self):
        def git(*args):return subprocess.check_output(["git","-C",str(self.root),*args],text=True,stderr=subprocess.DEVNULL).strip()
        git("init");git("config","user.name","Synthetic Test");git("config","user.email","test@example.invalid")
        (self.root/".github").mkdir();(self.root/once.GRANT).write_text('{"status":"CLOSED_UNISSUED"}')
        git("add",".");git("commit","-m","executor");executor=git("rev-parse","HEAD")
        grant=once.expected_grant(executor);(self.root/once.GRANT).write_text(json.dumps(grant))
        git("add",".");git("commit","-m","grant");adopted=git("rev-parse","HEAD")
        marker=dict(schema="hcl-deepseek-core-smoke-marker-1",campaign=once.CAMPAIGN,executor_commit=executor,
            grant_commit=adopted,grant_sha256=once.hash_value(grant),case_sha256=once.case_hash())
        (self.root/once.MARKER).write_text(json.dumps(marker));git("add",".");git("commit","-m","marker")
        identity=dict(self.identity,head_sha=git("rev-parse","HEAD"))
        chain=once.validate_commit_chain(self.root,grant,marker,identity)
        self.assertEqual(chain["executor_commit"],executor)
        # New marker edit is a later descendant, not a new grant-parent event.
        (self.root/once.MARKER).write_text(json.dumps(dict(marker,extra=True)));git("add",".");git("commit","-m","second trigger")
        with self.assertRaises(ValueError):once.validate_commit_chain(self.root,grant,marker,dict(identity,head_sha=git("rev-parse","HEAD")))

    def test_exclusive_durable_consumption_never_overwrites(self):
        path=self.root/"private"/"consumed.json";once.exclusive_json(path,self.identity)
        before=path.read_bytes()
        with self.assertRaises(FileExistsError):once.exclusive_json(path,dict(self.identity,run_id="other"))
        self.assertEqual(path.read_bytes(),before)

    def test_price_account_freshness_unknown_usd_and_old_evidence_rejected(self):
        now=int(time.time());price=dict(self.identity,checked_at=now,currency="CNY",model=once.MODEL,version=once.MODEL_VERSION,
            input_nanoyuan_per_token=9000,cached_nanoyuan_per_token=300,output_nanoyuan_per_token=27000)
        account=dict(self.identity,checked_at=now,currency="CNY",available=True,model_calls=0)
        once.check_prechecks(price,account,self.identity)
        for row in (dict(account,currency="USD"),dict(account,checked_at=now-601),dict(account,checked_at=now+1),dict(account,available=False),dict(account,run_id="124")):
            with self.assertRaises(ValueError):once.check_prechecks(price,row,self.identity)
        with self.assertRaises(ValueError):once.check_prechecks(dict(price,input_nanoyuan_per_token=4500),account,self.identity)

    def test_account_raw_json_currency_capacity_and_destination_fail_closed(self):
        class Credentials:
            @contextmanager
            def borrow_bearer(self,endpoint):
                self_endpoint=endpoint
                if self_endpoint!=once.two_stage_account.URL:raise AssertionError("wrong endpoint")
                yield "synthetic-test-only"
        class Response:
            status=200
            def __init__(self,raw,url=once.two_stage_account.URL):self.raw,self.url=raw,url
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def geturl(self):return self.url
            def read(self,limit):return self.raw[:limit]
        class Opener:
            def __init__(self,response):self.response=response
            def open(self,request,timeout):
                if request.full_url!=once.two_stage_account.URL or request.get_method()!="GET" or timeout!=20:
                    raise AssertionError("fixed read-only account query required")
                return self.response
        valid=b'{"is_available":true,"balance_infos":[{"currency":"CNY","total_balance":"synthetic-private-amount"}]}'
        with patch.object(once,"opener",return_value=Opener(Response(valid))):
            result=once.read_account(Credentials(),self.identity)
        self.assertEqual(result["currency"],"CNY");self.assertEqual(result["model_calls"],0)
        self.assertNotIn("balance",json.dumps(result));self.assertNotIn("synthetic-private-amount",json.dumps(result))
        invalid=[
            b'{"is_available":true,"balance_infos":[{"currency":"USD"}],"balance_infos":[{"currency":"CNY"}]}',
            b'{"is_available":true,"balance_infos":[{"currency":"CNY","currency":"USD"}]}',
            b'{"is_available":true,"balance_infos":[{"currency":"CNY","amount":NaN}]}',
            b'{"is_available":true,"balance_infos":[{"currency":"USD"}]}',
            b'{"is_available":true,"balance_infos":[{"currency":"USD"},{"currency":"CNY"}]}',
            b'{"is_available":false,"balance_infos":[{"currency":"CNY"}]}',b" "*64001,
        ]
        for raw in invalid:
            with self.subTest(raw=raw[:100]),patch.object(once,"opener",return_value=Opener(Response(raw))):
                with self.assertRaises(ValueError):once.read_account(Credentials(),self.identity)
        with patch.object(once,"opener",return_value=Opener(Response(valid,"https://other.invalid"))):
            with self.assertRaises(ValueError):once.read_account(Credentials(),self.identity)

    def _export_context(self):
        stack=ExitStack();self.addCleanup(stack.close)
        stack.enter_context(patch.object(once,"TEMP",self.root/"temporary"))
        stack.enter_context(patch.object(once,"PRIVATE",self.root/"private"))
        stack.enter_context(patch.object(once,"PUBLIC",self.root/"public.json"))
        stack.enter_context(patch.dict(os.environ,self.environment,clear=True))
        return stack

    def test_export_early_failure_is_sanitized_known_zero(self):
        self._export_context()
        result=once.export_failure(ValueError("EXISTING_SECRET_MISSING"))
        self.assertTrue(result["model_calls_known_zero"]);self.assertEqual(result["model_calls"],0)
        self.assertEqual(result["stage"],"ADMISSION");self.assertEqual(result["failure_code"],"EXISTING_SECRET_MISSING")
        once.PUBLIC.unlink()
        once.exclusive_json(once.TEMP/"consumed.json",self.identity)
        once.exclusive_json(once.TEMP/"stage-price.json",self.identity)
        result=once.export_failure(ValueError("OFFICIAL_PRICE_OR_CONTEXT_UNVERIFIED"))
        self.assertTrue(result["model_calls_known_zero"]);self.assertEqual(result["stage"],"PRICE")
        once.PUBLIC.unlink()
        once.exclusive_json(once.TEMP/"stage-account.json",self.identity)
        result=once.export_failure(ValueError("ACCOUNT_CNY_REQUIRED"))
        self.assertTrue(result["model_calls_known_zero"]);self.assertEqual(result["stage"],"ACCOUNT")
        once.PUBLIC.unlink()
        result=once.export_failure(RuntimeError("secret-raw-provider-body"))
        self.assertFalse(result["model_calls_known_zero"]);self.assertIsNone(result["model_calls"])
        self.assertNotIn("secret-raw-provider-body",once.PUBLIC.read_text())

    def test_export_missing_stages_or_batch_database_never_means_zero(self):
        self._export_context()
        result=once.export_failure()
        self.assertTrue(result["possible_model_send"]);self.assertIsNone(result["model_calls"])
        once.PUBLIC.unlink()
        once.exclusive_json(once.TEMP/"consumed.json",self.identity)
        result=once.export_failure()
        self.assertTrue(result["possible_model_send"]);self.assertFalse(result["model_calls_known_zero"])
        once.PUBLIC.unlink();once.exclusive_json(once.TEMP/"stage-batch.json",self.identity)
        result=once.export_failure(ValueError("ACCOUNT_CNY_REQUIRED"))
        self.assertEqual(result["stage"],"BATCH");self.assertTrue(result["possible_model_send"])
        self.assertIsNone(result["model_calls"])

    def test_export_validates_same_run_ledger_paths_and_retains_unknown(self):
        self._export_context();once.PRIVATE.mkdir()
        once.exclusive_json(once.TEMP/"consumed.json",self.identity)
        once.exclusive_json(once.TEMP/"stage-batch.json",self.identity)
        now=int(time.time())
        grant=once.DeepSeekBatchAuthorization(once.CAMPAIGN+"-123",str(once.PRIVATE/"cny.sqlite"),str(once.PRIVATE/"state.sqlite"),
            ("a"*64,),now,now+600,"CNY","HCL_CORE_DEEPSEEK_DIRECT","SYNTHETIC_ONLY")
        batch=once.CNYBatchLedger.create(grant);batch.close()
        result=once.export_failure();self.assertTrue(result["model_calls_known_zero"])
        self.assertEqual(result["batch"]["status"],"CLOSED")
        once.PUBLIC.unlink()
        foreign=replace(grant,ledger_path=str(self.root/"foreign.sqlite"))
        other=once.CNYBatchLedger.create(foreign)
        with sqlite3.connect(once.PRIVATE/"cny.sqlite") as db:
            db.execute("UPDATE control SET authorization=?",(codec.dumps(foreign),))
        result=once.export_failure();self.assertTrue(result["possible_model_send"])
        self.assertIsNone(result["batch"]);self.assertEqual(other.audit()["status"],"ACTIVE");other.close()
        once.PUBLIC.unlink();(once.PRIVATE/"cny.sqlite").unlink()
        result=once.export_failure();self.assertTrue(result["possible_model_send"])

    def test_export_send_started_keeps_full_hold_and_never_sends(self):
        self._export_context();once.PRIVATE.mkdir()
        once.exclusive_json(once.TEMP/"consumed.json",self.identity)
        once.exclusive_json(once.TEMP/"stage-batch.json",self.identity)
        now=int(time.time())
        grant=once.DeepSeekBatchAuthorization(once.CAMPAIGN+"-123",str(once.PRIVATE/"cny.sqlite"),str(once.PRIVATE/"state.sqlite"),
            ("a"*64,),now,now+600,"CNY","HCL_CORE_DEEPSEEK_DIRECT","SYNTHETIC_ONLY")
        batch=once.CNYBatchLedger.create(grant);batch.reserve("b"*64,"a"*64);batch.dispatch("b"*64,lambda:None);batch.close()
        with patch.object(once.ExistingCoreCredentialProvider,"borrow_bearer",side_effect=AssertionError("export cannot borrow")):
            result=once.export_failure()
        self.assertIsNone(result["model_calls"]);self.assertTrue(result["possible_model_send"])
        self.assertEqual(result["batch"]["held_nanoyuan"],9880416000)
        self.assertEqual(result["batch"]["states"],("SEND_STARTED",));self.assertTrue(result["batch"]["unresolved"])
        self.assertEqual(result["batch"]["status"],"CLOSED")

    def test_existing_credential_cannot_be_borrowed_without_same_run_consumption(self):
        admission=dict(self.identity)
        with patch.object(once,"TEMP",self.root),patch.dict(os.environ,self.environment,clear=True):
            provider=once.ExistingCoreCredentialProvider(admission)
            with self.assertRaises(ValueError):
                with provider.borrow_bearer(once.ENDPOINT):pass
            once.exclusive_json(self.root/"consumed.json",admission)
            with provider.borrow_bearer(once.ENDPOINT) as value:self.assertEqual(value,"synthetic-test-only")
            with self.assertRaises(ValueError):
                with provider.borrow_bearer("https://other.invalid"):pass
            with patch.dict(os.environ,{"GITHUB_RUN_ID":"124"}):
                with self.assertRaises(ValueError):
                    with provider.borrow_bearer(once.ENDPOINT):pass

    def test_workflow_is_push_only_readonly_closed_no_private_upload(self):
        raw=(once.ROOT/once.WORKFLOW).read_text()
        self.assertNotIn("workflow_dispatch",raw);self.assertNotIn("pull_request",raw)
        self.assertIn("contents: read",raw);self.assertIn("actions: read",raw)
        self.assertNotIn(": write",raw)
        self.assertIn("persist-credentials: false",raw);self.assertIn("--paginate --slurp",raw)
        self.assertIn("path: hcl-deepseek-core-smoke-public.json",raw)
        self.assertNotIn("path: hcl-deepseek-core-smoke-private",raw)

    def test_complete_new_runner_uses_real_http_and_shared_two_call_budget(self):
        self._loopback_runner(False)

    def test_runner_repair_consumes_second_call_and_skips_second_case(self):
        self._loopback_runner(True)

    def _loopback_runner(self,repair):
        temp=self.root/"temporary";private=self.root/"private";public=self.root/"public.json"
        temp.mkdir();(temp/"runs.json").write_text(json.dumps(self.pages))
        grant=once.expected_grant("a"*40)
        chain=dict(executor_commit="a"*40,grant_commit="b"*40,marker_commit="c"*40,grant_sha256=once.hash_value(grant),marker_sha256="d"*64)
        now=int(time.time());price=dict(self.identity,checked_at=now,currency="CNY",model=once.MODEL,version=once.MODEL_VERSION,
            input_nanoyuan_per_token=9000,cached_nanoyuan_per_token=300,output_nanoyuan_per_token=27000)
        account=dict(self.identity,checked_at=now,currency="CNY",available=True,model_calls=0)
        async def run():
            async def response(writer):
                self.assertTrue((temp/"consumed.json").exists())
                db=StateStore.sqlite(private/"state.sqlite")
                try:
                    owner=Principal("synthetic","core-smoke")
                    row=db._db.execute("SELECT * FROM tasks WHERE state='ACTIVE'").fetchone()
                    request=db._get_object(row["request_hash"])
                    snapshot=db.snapshot("synthetic-smoke",owner,request.source_handles)
                    candidate=fixture.candidate(snapshot,request.question,"unreceived" if request.request_id=="missed-report" else "received")
                    if repair and len(server.requests)==1:candidate["models"][0]["episodes"][0]["computed_score"]=42
                    raw=completion(candidate,snapshot.source_versions,id="synthetic-"+str(len(server.requests)))
                    writer.write((f"HTTP/1.1 200 OK\\r\\nContent-Type: application/json\\r\\nContent-Length: {len(raw)}\\r\\n\\r\\n").encode().replace(b"\\r\\n",b"\r\n")+raw)
                    await writer.drain()
                finally:db.close()
            async with LoopbackHTTP([response,response]) as server:
                with patch.object(once,"TEMP",temp),patch.object(once,"PRIVATE",private),patch.object(once,"PUBLIC",public),\
                    patch.dict(os.environ,self.environment,clear=True),patch.object(once,"preflight",return_value=(grant,self.identity,chain)),\
                    patch.object(once,"read_price",return_value=price),patch.object(once,"read_account",return_value=account):
                    summary=await once.execute()
                    with self.assertRaises(FileExistsError):await once.execute()
                return summary,server.requests
        summary,requests=asyncio.run(run())
        self.assertEqual(len(requests),2)
        self.assertEqual(summary["batch"]["claimed_calls"],2);self.assertEqual(summary["batch"]["status"],"CLOSED")
        self.assertEqual(len(summary["results"]),1 if repair else 2)
        self.assertTrue(all(row["status"]=="COMPLETED" for row in summary["results"]),summary)
        self.assertFalse(summary["semantic_fidelity_verified"] or summary["effect_confirmed"] or summary["stage_complete"])
        self.assertNotIn("synthetic-test-only",public.read_text())
        self.assertNotIn("reasoning_content",public.read_text())


if __name__=="__main__":unittest.main()
