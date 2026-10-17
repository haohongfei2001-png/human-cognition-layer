"""Inert-by-default, exact one-use HCL core smoke host. No manual dispatch.

The new grant and marker are separate later owner-authorized commits. Existing
closed campaign files are never imported. Preparation/tests never read a real
credential or call a model. Public output is synthetic cognition plus bounded
mechanical usage; no key, balance amount, hidden reasoning, or raw HTTP body.
"""
import argparse
import asyncio
from contextlib import contextmanager
from hashlib import sha256
import json
import os
from pathlib import Path
import ssl
import sqlite3
import subprocess
import time
from urllib.request import Request,build_opener,ProxyHandler,HTTPSHandler,HTTPRedirectHandler

from hcl import HCL,affect_request,ExecutionBudget
from hcl.kernel.types import Principal,thaw
from hcl.memory import codec
from hcl.memory.store import StateStore
from hcl.models.candidate_protocol import strict_json
from hcl.models.deepseek_contracts import (
    MODEL,MODEL_VERSION,ENDPOINT,PRICING_URL,DeepSeekBatchAuthorization,
)
from hcl.models.deepseek_gateway import DeepSeekCandidateGateway
from hcl.models.deepseek_transport import DeepSeekHTTPTransport
from hcl.runtime.deepseek_ledger import CNYBatchLedger
from scripts.deepseek_core_smoke_case import CASES
from scripts import two_stage_price,two_stage_account

ROOT=Path(__file__).resolve().parents[1]
REPOSITORY="haohongfei2001-png/human-cognition-layer"
WORKFLOW=".github/workflows/hcl-deepseek-core-smoke-once.yml"
GRANT=".github/HCL_DEEPSEEK_CORE_SMOKE_GRANT.json"
MARKER=".github/HCL_DEEPSEEK_CORE_SMOKE_TRIGGER.json"
CAMPAIGN="hcl-core-deepseek-synthetic-v1"
TEMP=Path("/tmp/hcl-deepseek-core-smoke")
PRIVATE=ROOT/"hcl-deepseek-core-smoke-private"
PUBLIC=ROOT/"hcl-deepseek-core-smoke-public.json"
READER_PINS={'scripts/two_stage_price.py': '32c9747dc3411f4d090517f07fc60a524d327f9aecc49b5cf0a10dfcd50451b0', 'scripts/two_stage_account.py': '18bbb9085a3a0789115d2065d7aa498e485a547b477ada40aecdd4a67d58582b'}



def require(condition,code):
    if not condition:raise ValueError(code)


def exact_sha(value,length=40):
    require(type(value) is str and len(value)==length and all(c in "0123456789abcdef" for c in value),"EXACT_SHA_REQUIRED")


def hash_value(value):return sha256(codec.canonical(value).encode()).hexdigest()


def case_hash():return hash_value(CASES)


def load_json(path,maximum=1048576):
    require(not path.is_symlink() and path.is_file(),"REQUIRED_FILE_MISSING")
    raw=path.read_bytes();require(len(raw)<=maximum,"INPUT_FILE_CAPACITY")
    return strict_json(raw)


def environment_identity(environment):
    require(environment.get("GITHUB_REPOSITORY")==REPOSITORY
        and environment.get("GITHUB_REF")=="refs/heads/main"
        and environment.get("GITHUB_EVENT_NAME")=="push"
        and environment.get("GITHUB_RUN_ATTEMPT")=="1"
        and environment.get("GITHUB_WORKFLOW_REF")==REPOSITORY+"/"+WORKFLOW+"@refs/heads/main",
        "EXACT_NEW_MAIN_FIRST_PUSH_REQUIRED")
    run=environment.get("GITHUB_RUN_ID");head=environment.get("GITHUB_SHA")
    require(type(run) is str and run.isascii() and run.isdecimal() and int(run)>0,"EXACT_RUN_REQUIRED")
    exact_sha(head)
    return dict(run_id=run,head_sha=head)


def expected_grant(executor_commit):
    from hcl.memory.migrations.control import version_bundle
    return dict(schema="hcl-deepseek-core-smoke-grant-1",status="READY",campaign=CAMPAIGN,
        executor_commit=executor_commit,case_sha256=case_hash(),runtime_sha256=version_bundle(schema=3)["code_sha256"],
        reader_sha256=dict(READER_PINS),currency="CNY",authorized_cny="20.00",
        authorized_calls=2,max_semantic_repairs=1,model=MODEL,model_version=MODEL_VERSION,
        endpoint=ENDPOINT,account_scope="HCL_CORE_DEEPSEEK_DIRECT",source_policy="SYNTHETIC_ONLY",
        retries=0,historical_budget_transfer=False,publication="SYNTHETIC_RESULT_AND_MECHANICAL_USAGE_ONLY")
def validate_grant(grant):
    require(type(grant) is dict,"EXACT_NEW_GRANT_REQUIRED")
    expected=expected_grant(grant.get("executor_commit"))
    require(grant==expected and all(type(grant[k]) is type(v) for k,v in expected.items()),"EXACT_NEW_GRANT_REQUIRED")
    exact_sha(grant["executor_commit"])
    return grant


def git(root,args):
    process=subprocess.run(["git","-C",str(root),*args],stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True)
    require(process.returncode==0,"READ_ONLY_GIT_CHECK_FAILED")
    return process.stdout.strip()


def validate_commit_chain(root,grant,marker,identity,git_reader=git):
    require(not git_reader(root,["status","--porcelain","--untracked-files=no"]),"CLEAN_PUBLISHED_CODE_REQUIRED")
    marker_parents=git_reader(root,["rev-list","--parents","-n","1","HEAD"]).split()
    require(len(marker_parents)==2 and marker_parents[0]==identity["head_sha"],"SINGLE_PARENT_MARKER_REQUIRED")
    adopted=marker_parents[1];exact_sha(adopted)
    grant_parents=git_reader(root,["rev-list","--parents","-n","1",adopted]).split()
    require(grant_parents==[adopted,grant["executor_commit"]],"EXACT_EXECUTOR_GRANT_PARENT_REQUIRED")
    require(len({identity["head_sha"],adopted,grant["executor_commit"]})==3,"DISTINCT_COMMIT_CHAIN_REQUIRED")
    require(git_reader(root,["diff","--name-only",grant["executor_commit"],adopted]).splitlines()==[GRANT],"GRANT_ONLY_COMMIT_REQUIRED")
    require(git_reader(root,["diff","--name-only",adopted,identity["head_sha"]]).splitlines()==[MARKER],"MARKER_ONLY_COMMIT_REQUIRED")
    # This path must not have existed in the tested executor or the grant commit.
    require(not git_reader(root,["ls-tree",grant["executor_commit"],"--",MARKER])
        and not git_reader(root,["ls-tree",adopted,"--",MARKER]),"NEW_MARKER_REQUIRED")
    expected=dict(schema="hcl-deepseek-core-smoke-marker-1",campaign=CAMPAIGN,executor_commit=grant["executor_commit"],
                  grant_commit=adopted,grant_sha256=hash_value(grant),case_sha256=case_hash())
    require(marker==expected,"EXACT_BOUND_MARKER_REQUIRED")
    return dict(executor_commit=grant["executor_commit"],grant_commit=adopted,marker_commit=identity["head_sha"],
                grant_sha256=hash_value(grant),marker_sha256=hash_value(marker))


def validate_history(pages,identity):
    require(type(pages) is list and 1<=len(pages)<=1000,"COMPLETE_RUN_HISTORY_REQUIRED")
    require(all(type(p) is dict and set(p)=={"total_count","workflow_runs"} and type(p["total_count"]) is int
        and type(p["workflow_runs"]) is list for p in pages),"COMPLETE_RUN_HISTORY_REQUIRED")
    rows=[r for p in pages for r in p["workflow_runs"]]
    require(len(rows)==1 and all(p["total_count"]==len(rows) for p in pages),"PERMANENT_FIRST_RUN_ONLY")
    row=rows[0];require(type(row) is dict,"EXACT_HISTORY_ROW_REQUIRED")
    require(type(row.get("id")) is int and row["id"]==int(identity["run_id"])
        and type(row.get("workflow_id")) is int and row["workflow_id"]>0
        and type(row.get("run_attempt")) is int and row["run_attempt"]==1
        and row.get("head_branch")=="main" and row.get("path")==WORKFLOW
        and row.get("head_sha")==identity["head_sha"] and row.get("event")=="push",
        "EXACT_FIRST_RUN_IDENTITY_REQUIRED")
    return dict(workflow_id=row["workflow_id"],run_id=row["id"],history_sha256=hash_value(pages))


def exclusive_json(path,value):
    path.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
    require(not path.parent.is_symlink(),"SAFE_PRIVATE_DIRECTORY_REQUIRED")
    descriptor=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(descriptor,"wb") as stream:
        stream.write(codec.canonical(value).encode()+b"\n");stream.flush();os.fsync(stream.fileno())
    descriptor=os.open(path.parent,os.O_RDONLY)
    try:os.fsync(descriptor)
    finally:os.close(descriptor)


def preflight(root=ROOT,environment=None):
    environment=os.environ if environment is None else environment
    for name,digest in READER_PINS.items():
        require(sha256((root/name).read_bytes()).hexdigest()==digest,"EXACT_READ_ONLY_READER_REQUIRED")
    require(Path(two_stage_price.__file__).resolve()==(root/"scripts/two_stage_price.py").resolve()
        and Path(two_stage_account.__file__).resolve()==(root/"scripts/two_stage_account.py").resolve(),"IMPORTED_READER_PATH_REQUIRED")
    identity=environment_identity(environment);grant=validate_grant(load_json(root/GRANT,8192))
    marker=load_json(root/MARKER,8192);chain=validate_commit_chain(root,grant,marker,identity)
    require(environment.get("SECRET_PRESENT")=="true","EXISTING_SECRET_MISSING")
    return grant,identity,chain


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):return None


def opener():
    return build_opener(ProxyHandler({}),NoRedirect(),HTTPSHandler(context=ssl.create_default_context()))


def read_price(identity):
    try:
        with opener().open(Request(PRICING_URL,headers={"User-Agent":"HCL-core-price-check/1"}),timeout=20) as response:
            require(response.status==200 and response.geturl()==PRICING_URL,"OFFICIAL_PRICE_DESTINATION")
            raw=response.read(512001)
        rates=two_stage_price.parse_price(raw)
        parser=two_stage_price.Rows();parser.feed(raw.decode("utf-8"))
        context=next((row for row in parser.rows if row and row[0]=="上下文长度"),None)
        require(context is not None and len(context)>=2 and set(context[1:])=={"1M"},"CONTEXT_CEILING_CHANGED")
    except Exception:
        raise ValueError("OFFICIAL_PRICE_OR_CONTEXT_UNVERIFIED") from None
    return dict(**identity,checked_at=int(time.time()),currency=rates["currency"],model=rates["model"],version=rates["version"],
        input_nanoyuan_per_token=9000,cached_nanoyuan_per_token=300,output_nanoyuan_per_token=27000,
        source_url=PRICING_URL,source_sha256=sha256(raw).hexdigest())


class ExistingCoreCredentialProvider:
    """The existing Actions secret, borrowed only after permanent admission.

    No fallback names, saved files, logging, configuration or persistent access.
    """
    def __init__(self,admission):
        self._admission=admission

    @contextmanager
    def borrow_bearer(self,endpoint):
        require(endpoint in (ENDPOINT,two_stage_account.URL),"FIXED_CORE_ENDPOINT_REQUIRED")
        require(load_json(TEMP/"consumed.json",8192)==self._admission,"DURABLE_SAME_RUN_CONSUMPTION_REQUIRED")
        require(environment_identity(os.environ)=={k:self._admission[k] for k in ("run_id","head_sha")},"SAME_ADMITTED_RUN_REQUIRED")
        secret=os.environ.get("DEEPSEEK_API_KEY")
        require(type(secret) is str and 1<=len(secret)<=4096 and all(33<=ord(c)<=126 for c in secret),"EXISTING_SECRET_UNAVAILABLE")
        try:yield secret
        finally:del secret


def read_account(credentials,identity):
    try:
        with credentials.borrow_bearer(two_stage_account.URL) as secret:
            request=Request(two_stage_account.URL,headers={"Authorization":"Bearer "+secret,"Accept":"application/json"},method="GET")
            with opener().open(request,timeout=20) as response:
                require(response.status==200 and response.geturl()==two_stage_account.URL,"ACCOUNT_METADATA_UNVERIFIED")
                raw=response.read(64001)
            require(len(raw)<=64000,"ACCOUNT_METADATA_UNVERIFIED")
        # Duplicate keys/NaN must not overwrite contradictory currency metadata.
        summary=two_stage_account.summarize(strict_json(raw))
    except Exception as error:
        if type(error) is ValueError and error.args == ("EXISTING_SECRET_UNAVAILABLE",):
            raise ValueError("EXISTING_SECRET_UNAVAILABLE") from None
        raise ValueError("ACCOUNT_METADATA_UNVERIFIED") from None
    require(summary["currency"]=="CNY","ACCOUNT_CNY_REQUIRED")
    require(summary["available"] is True,"ACCOUNT_UNAVAILABLE")
    return dict(**identity,checked_at=int(time.time()),currency="CNY",available=True,model_calls=0)


def check_prechecks(price,account,identity):
    now=time.time()
    for row in (price,account):
        require(all(row.get(k)==v for k,v in identity.items()) and row.get("currency")=="CNY"
            and type(row.get("checked_at")) is int and 0<=now-row["checked_at"]<=600,"FRESH_SAME_RUN_CNY_REQUIRED")
    require(account.get("available") is True and account.get("model_calls")==0,"EXISTING_CNY_ACCOUNT_REQUIRED")
    require(price.get("model")==MODEL and price.get("version")==MODEL_VERSION
        and price.get("input_nanoyuan_per_token")==9000 and price.get("cached_nanoyuan_per_token")==300
        and price.get("output_nanoyuan_per_token")==27000,"KNOWN_PEAK_RATES_REQUIRED")


def prepare_requests(store,owner):
    budget=ExecutionBudget(max_mock_calls=0,max_feedback=1,max_output_bytes=262144,max_visible_output_tokens=16384,
        max_request_bytes=1048576,max_context_tokens=1048576,max_total_request_bytes=2097152,
        max_total_output_bytes=16777216,max_steps=64,max_local_evaluations=100000)
    requests=[]
    for case in CASES:
        handle=store.put_source("synthetic-smoke",owner,case["case_id"],case["source"])
        requests.append(affect_request(case["case_id"],case["question"],(handle,),"synthetic-smoke",owner,budget=budget))
    return tuple(requests)


async def execute():
    grant,identity,chain=preflight()
    history=validate_history(load_json(TEMP/"runs.json",16*1024*1024),identity)
    admission=dict(schema="hcl-deepseek-core-smoke-consumed-1",campaign=CAMPAIGN,**identity,**chain,
                   workflow_id=history["workflow_id"],history_sha256=history["history_sha256"])
    # Permanent cross-run guard is the exact marker chain + complete workflow
    # history. This exclusive fsynced file additionally prevents same-run repeat.
    exclusive_json(TEMP/"consumed.json",admission)
    require(not PRIVATE.exists(),"PRIVATE_RUN_ALREADY_EXISTS")
    PRIVATE.mkdir(mode=0o700)
    exclusive_json(TEMP/"stage-price.json",identity)
    price=read_price(identity)  # Still no credential read or model call.
    credentials=ExistingCoreCredentialProvider(admission)
    exclusive_json(TEMP/"stage-account.json",identity)
    account=read_account(credentials,identity);check_prechecks(price,account,identity)
    exclusive_json(PRIVATE/"readiness.json",dict(price=price,account=account))
    exclusive_json(TEMP/"stage-batch.json",identity)
    store=StateStore.sqlite(PRIVATE/"state.sqlite",revision=True)
    owner=Principal("synthetic","core-smoke");store.create_session("synthetic-smoke",owner)
    requests=prepare_requests(store,owner)
    verified=min(price["checked_at"],account["checked_at"])
    authorization=DeepSeekBatchAuthorization(CAMPAIGN+"-"+identity["run_id"],str(PRIVATE/"cny.sqlite"),str(store.path),
        tuple(sha256(codec.dumps(r)).hexdigest() for r in requests),verified,verified+600,"CNY","HCL_CORE_DEEPSEEK_DIRECT","SYNTHETIC_ONLY")
    batch=CNYBatchLedger.create(authorization)
    gateway=DeepSeekCandidateGateway(store,authorization=authorization,transport=DeepSeekHTTPTransport(credentials))
    for request in requests:gateway.register_authorization(request)
    client=HCL(store,principal=owner,gateway=gateway);results=[]
    try:
        for request in requests:
            check_prechecks(price,account,identity)
            audit=batch.audit()
            if audit["status"]!="ACTIVE" or audit["unresolved"] or audit["claimed_calls"]>=2:break
            result=await client.run(request)
            values=[p for p in store.inferences("synthetic-smoke",owner) if p.result_id in result.execution_receipt.get("result_ids",())]
            results.append(dict(case_id=request.request_id,status=result.status,answer=result.answer,
                answer_sha256=sha256(result.answer.encode()).hexdigest(),claim_count=len(result.claim_records),
                local_evaluations=result.usage.get("local_evaluations"),
                computed_result_kinds=[p.kind for p in values],computed_result_sha256=[sha256(codec.dumps(p)).hexdigest() for p in values],
                usage=thaw(result.usage),diagnostic_codes=[d.code for d in result.diagnostics]))
            if result.status!="COMPLETED":break
    finally:
        batch.stop("CLOSED")
        summary=dict(schema="hcl-deepseek-core-smoke-public-1",campaign=CAMPAIGN,**identity,executor_commit=grant["executor_commit"],
            source_case_sha256=case_hash(),currency="CNY",results=results,batch=batch.audit(),
            semantic_fidelity_verified=False,effect_confirmed=False,stage_complete=False,
            boundary="REAL_HOST_CANDIDATE_TO_EXISTING_COGNITION; NO_AUTOMATIC_GAIN_OR_STAGE_CLAIM")
        exclusive_json(PUBLIC,summary)
        gateway.close();batch.close();store.close()
    return summary


SAFE_FAILURES=frozenset({"EXACT_NEW_GRANT_REQUIRED","EXACT_NEW_MAIN_FIRST_PUSH_REQUIRED","EXISTING_SECRET_MISSING",
    "EXISTING_SECRET_UNAVAILABLE","PERMANENT_FIRST_RUN_ONLY","EXACT_FIRST_RUN_IDENTITY_REQUIRED",
    "EXACT_EXECUTOR_GRANT_PARENT_REQUIRED","GRANT_ONLY_COMMIT_REQUIRED","MARKER_ONLY_COMMIT_REQUIRED",
    "EXACT_BOUND_MARKER_REQUIRED","NEW_MARKER_REQUIRED","CLEAN_PUBLISHED_CODE_REQUIRED","REQUIRED_FILE_MISSING",
    "OFFICIAL_PRICE_OR_CONTEXT_UNVERIFIED","ACCOUNT_METADATA_UNVERIFIED","ACCOUNT_CNY_REQUIRED","ACCOUNT_UNAVAILABLE",
    "FRESH_SAME_RUN_CNY_REQUIRED","KNOWN_PEAK_RATES_REQUIRED","EXACT_READ_ONLY_READER_REQUIRED"})


def export_failure(error=None):
    """Always-step terminal accounting only. This function cannot send or reopen authority."""
    identity=environment_identity(os.environ)
    if PUBLIC.exists():
        result=load_json(PUBLIC)
        require(all(result.get(k)==v for k,v in identity.items()),"SAME_RUN_EXPORT_REQUIRED")
        return result
    code=str(error) if type(error) is ValueError and str(error) in SAFE_FAILURES else "EXECUTION_INTERRUPTED_OR_UNVERIFIED"
    phase="ADMISSION";batch_audit=None
    # After consumption, absent files are never proof that no send happened.
    # Only a current, allowlisted early gate failure or a validated zero-claim
    # ledger can establish zero. The always-step has no such early exception.
    consumed=(TEMP/"consumed.json").exists()
    early_admission_codes={"EXACT_NEW_GRANT_REQUIRED","EXACT_NEW_MAIN_FIRST_PUSH_REQUIRED",
        "EXISTING_SECRET_MISSING","PERMANENT_FIRST_RUN_ONLY","EXACT_FIRST_RUN_IDENTITY_REQUIRED",
        "EXACT_EXECUTOR_GRANT_PARENT_REQUIRED","GRANT_ONLY_COMMIT_REQUIRED","MARKER_ONLY_COMMIT_REQUIRED",
        "EXACT_BOUND_MARKER_REQUIRED","NEW_MARKER_REQUIRED","CLEAN_PUBLISHED_CODE_REQUIRED",
        "EXACT_READ_ONLY_READER_REQUIRED","REQUIRED_FILE_MISSING"}
    known_zero=not consumed and not PRIVATE.exists() and code in early_admission_codes
    for name,stage in (("price","PRICE"),("account","ACCOUNT"),("batch","BATCH")):
        path=TEMP/("stage-"+name+".json")
        if path.exists():
            require(load_json(path,8192)==identity,"SAME_RUN_STAGE_REQUIRED")
            phase=stage
    if phase=="BATCH":
        known_zero=False
    elif consumed and ((phase=="PRICE" and code=="OFFICIAL_PRICE_OR_CONTEXT_UNVERIFIED")
            or (phase=="ACCOUNT" and code in {"ACCOUNT_METADATA_UNVERIFIED","ACCOUNT_CNY_REQUIRED",
                "ACCOUNT_UNAVAILABLE","EXISTING_SECRET_UNAVAILABLE","FRESH_SAME_RUN_CNY_REQUIRED","KNOWN_PEAK_RATES_REQUIRED"})):
        known_zero=True
    path=PRIVATE/"cny.sqlite"
    if path.exists():
        known_zero=False
        try:
            require(not PRIVATE.is_symlink() and not path.is_symlink()
                and path.resolve()==path.absolute(),"SAFE_LEDGER_REQUIRED")
            db=sqlite3.connect(path.as_uri()+"?mode=ro",uri=True)
            try:authorization=codec.loads(db.execute("SELECT authorization FROM control").fetchone()[0])
            finally:db.close()
            require(type(authorization) is DeepSeekBatchAuthorization
                and authorization.batch_id==CAMPAIGN+"-"+identity["run_id"]
                and authorization.ledger_path==str(path.resolve())
                and authorization.state_store_path==str((PRIVATE/"state.sqlite").resolve()),"SAME_RUN_BATCH_REQUIRED")
            batch=CNYBatchLedger(authorization)
            try:batch.stop("CLOSED");batch_audit=batch.audit()
            finally:batch.close()
            known_zero=batch_audit["claimed_calls"]==0
        except Exception:
            batch_audit=None  # Never misreport a corrupt/unknown ledger as zero.
    result=dict(schema="hcl-deepseek-core-smoke-public-1",campaign=CAMPAIGN,**identity,stage=phase,
        failure_code=code,model_calls=0 if known_zero else None,model_calls_known_zero=known_zero,
        possible_model_send=not known_zero,batch=batch_audit,semantic_fidelity_verified=False,effect_confirmed=False,stage_complete=False)
    exclusive_json(PUBLIC,result)
    return result


def main():
    parser=argparse.ArgumentParser();parser.add_argument("--preflight",action="store_true");parser.add_argument("--execute",action="store_true");parser.add_argument("--export",action="store_true")
    args=parser.parse_args();require(sum((args.preflight,args.execute,args.export))==1,"EXACTLY_ONE_ACTION_REQUIRED")
    if args.export:
        export_failure();print("TERMINAL_MECHANICAL_EXPORT_ONLY; NO_MODEL_CALL")
        return
    if args.preflight:
        preflight();print("NEW_GRANT_AND_MARKER_VERIFIED; MODEL_CALLS=0; SECRET_PRESENT=true")
    else:
        summary=asyncio.run(execute())
        print(json.dumps(dict(status="STOPPED",claimed_calls=summary["batch"]["claimed_calls"],currency="CNY",
            held_nanoyuan=summary["batch"]["held_nanoyuan"],actual_billed_cny=None)))


if __name__=="__main__":
    try:main()
    except BaseException as error:
        # Only allowlisted internal codes; never arbitrary exception/body text.
        try:
            result=export_failure(error)
            print(json.dumps({key:result.get(key) for key in ("failure_code","stage","model_calls_known_zero","possible_model_send")}))
        except BaseException:
            print("TERMINAL_STATUS_UNAVAILABLE; DO_NOT_RETRY")
        raise SystemExit("HCL_DEEPSEEK_CORE_SMOKE_STOPPED_NO_AUTOMATIC_RETRY") from None
