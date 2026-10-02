"""One separately authorized exact planning diagnostic; no Base or answer phase."""
import hashlib,json,os,subprocess
from dataclasses import asdict
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from hcl.cognition import CallAllowance,UniversalHCL
from hcl.cognition.capability_catalog import CATALOG
from hcl.cognition.universal_entry import PLANNER_POLICY
from hcl.cognition.deepseek_metered import DeepSeekMeteredPort
from scripts.serious_eval_contract import runtime_digest
from scripts.universal_development_protocol import CASES,digest
from scripts.run_universal_development import save
from scripts.universal_launch_guard import verify_run_history

REQUEST_SHA='ac155023d233e7806ba3ab4e015cd3a5d16fe1d5a27ed999903a635c095ef5b8'
RESERVE='0.04293432'
AUTH='NEW_PLANNING_DIAGNOSTIC_2026_10_02_ONE_CALL_0_05'
PACKAGE=Path('reports/HCL_PLANNING_DIAGNOSTIC_PACKAGE.json')
GRANT=Path('.github/HCL_PLANNING_DIAGNOSTIC_GRANT.json')
MARKER=Path('.github/HCL_PLANNING_DIAGNOSTIC_TRIGGER.json')
TEMPLATE=Path('.github/frozen/hcl-planning-diagnostic-once.yml')
WORKFLOW=Path('.github/workflows/hcl-planning-diagnostic-once.yml')

def messages():
    return [dict(role='system',content=PLANNER_POLICY),dict(role='user',content=json.dumps(dict(
        question=CASES[0]['question'],sources=[],capability_inventory=[asdict(c)for c in CATALOG.values()]),ensure_ascii=False,sort_keys=True))]

def build_package():
    port=DeepSeekMeteredPort(SimpleNamespace(max_retries=0,base_url='https://api.deepseek.com',timeout=180))
    request,encoded=port.request('planning',messages())
    if digest(request)!=REQUEST_SHA or port.reservation_usd('planning',messages())!=RESERVE:
        raise ValueError('ORIGINAL_EXACT_REQUEST_AND_RESERVATION_REQUIRED')
    files=['scripts/run_planning_diagnostic.py','tests/test_planning_diagnostic.py',str(TEMPLATE),
        'scripts/universal_launch_guard.py','scripts/run_universal_development.py','scripts/universal_development_protocol.py',
        'scripts/universal_encrypted_result.py','.github/HCL_UNIVERSAL_DEVELOPMENT_RECIPIENT.pem']
    return dict(schema='hcl-one-planning-diagnostic-package-v1',request_sha256=REQUEST_SHA,request_bytes=len(encoded),
        runtime_sha256=runtime_digest(),case_id=CASES[0]['case_id'],model=request['model'],maximum_output_tokens=4096,
        thinking='enabled',reasoning_effort='high',maximum_calls=1,maximum_usd='0.05',reservation_usd=RESERVE,
        maximum_wait_seconds=180,sdk_retries=0,base_calls=0,answer_calls=0,grader_calls=0,
        source_run_id=37022979416,source_run_cause='UNRESOLVED_NOT_RETROACTIVELY_IDENTIFIED',
        final_confirmation_qualified=False,output_policy='ENCRYPTED_CONTENT_AND_ALLOWLIST_DIAGNOSTICS_ONLY',
        execution_files={p:hashlib.sha256(Path(p).read_bytes()).hexdigest()for p in files})

def require_grant(package,grant):
    if package!=build_package():raise ValueError('FROZEN_DIAGNOSTIC_PACKAGE_DRIFT')
    expected=dict(schema='hcl-one-planning-diagnostic-grant-v1',status='READY',authorization_ref=AUTH,
        package_sha256=digest(package),maximum_calls=1,maximum_usd='0.05',historical_budget_transfer=False,retries=0)
    if grant!=expected:raise ValueError('FRESH_EXACT_DIAGNOSTIC_GRANT_REQUIRED')

def verify_launch(run_id,attempt,history,event,parent=None,paths=None,marker=None):
    verify_run_history(run_id,attempt,history)
    package=json.loads(PACKAGE.read_text());grant=json.loads(GRANT.read_text());require_grant(package,grant)
    if event=='workflow_dispatch':return True
    expected=dict(schema='hcl-one-planning-diagnostic-marker-v1',authorization_ref=AUTH,
        package_sha256=digest(package),grant_sha256=digest(grant),executor_commit=parent)
    if event!='push' or not isinstance(parent,str)or len(parent)!=40 or any(c not in '0123456789abcdef'for c in parent)or paths!=[str(MARKER)]or marker!=expected:
        raise ValueError('ONE_EXACT_REVIEWED_DIAGNOSTIC_MARKER_REQUIRED')
    return True

def run(client,package,grant,directory):
    require_grant(package,grant)
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=False,mode=0o700)
    path=directory/'receipt.json'
    port=DeepSeekMeteredPort(client);request,_=port.request('planning',messages())
    receipt=dict(schema='hcl-one-planning-diagnostic-receipt-v1',package_sha256=digest(package),request_sha256=REQUEST_SHA,
        request=request,status='PREPARED_NOT_CALLED',authorization_ref=AUTH,maximum_calls=1,maximum_usd='0.05',
        cost_basis='USAGE_RATED_PEAK_NOT_INVOICE',actual_invoice_cost_usd=None,attempts=[],original_failure_cause='UNRESOLVED')
    save(path,receipt)
    def journal(snapshot):
        if len(snapshot['attempts'])>1 or Decimal(snapshot['reserved_usd'])>Decimal(RESERVE):raise ValueError('SINGLE_FROZEN_RESERVATION_EXCEEDED')
        receipt['attempts']=json.loads(json.dumps(snapshot['attempts']));receipt['reserved_usd']=snapshot['reserved_usd'];save(path,receipt)
    allowance=CallAllowance(1,'0.05',AUTH,journal=journal)
    try:
        raw=allowance.call(port,'planning',messages());receipt['response_content']=raw
        try:
            UniversalHCL()._validate_plan(raw)
            receipt.update(status='PLANNING_RETURNED_SCHEMA_VALID',plan_schema_valid=True)
        except Exception:
            receipt.update(status='PLANNING_RETURNED_SCHEMA_REJECTED',plan_schema_valid=False,failure_code='PLAN_SCHEMA_REJECTED')
    except Exception:
        receipt.update(status='FAILED_OR_UNKNOWN_NO_RETRY',failure_code=(allowance.attempts[-1].get('failure_code','METERED_BACKEND_OR_JOURNAL_FAILED')if allowance.attempts else 'PRE_ADMISSION_REJECTED'))
    finally:
        allowance.closed=True
        receipt.update(budget_state='CLOSED_NO_TRANSFER_NO_RETRY',remaining_authorized_calls=0,remaining_authorized_usd='0')
        save(path,receipt)
    return receipt

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--freeze',action='store_true');p.add_argument('--check-launch');p.add_argument('--execute',action='store_true');p.add_argument('--output',default='planning-diagnostic-private');a=p.parse_args()
    os.umask(0o077)
    if sum((a.freeze,bool(a.check_launch),a.execute))!=1:raise ValueError('EXACTLY_ONE_MODE')
    if a.freeze:save(PACKAGE,build_package())
    else:
        if os.environ.get('GITHUB_REF')!='refs/heads/main' or os.environ.get('GITHUB_RUN_ATTEMPT')!='1':raise ValueError('MAIN_ATTEMPT_ONE_REQUIRED')
        if WORKFLOW.read_bytes()!=TEMPLATE.read_bytes():raise ValueError('FROZEN_WORKFLOW_REQUIRED')
        package=json.loads(PACKAGE.read_text());grant=json.loads(GRANT.read_text());require_grant(package,grant)
        if a.check_launch:
            pages=json.loads(Path(a.check_launch).read_text());history=[r for page in pages for r in page['workflow_runs']]
            event=os.environ.get('GITHUB_EVENT_NAME');kwargs={}
            if event=='push':
                ancestry=subprocess.check_output(['git','rev-list','--parents','-n','1','HEAD'],text=True).split()
                if len(ancestry)!=2:raise ValueError('SINGLE_PARENT_REQUIRED')
                kwargs=dict(parent=ancestry[1],paths=subprocess.check_output(['git','diff-tree','--no-commit-id','--name-only','-r','HEAD'],text=True).splitlines(),marker=json.loads(MARKER.read_text()))
            verify_launch(os.environ['GITHUB_RUN_ID'],os.environ['GITHUB_RUN_ATTEMPT'],history,event,**kwargs)
            save(Path('/tmp/planning-diagnostic-admission.json'),dict(run_id=os.environ['GITHUB_RUN_ID'],head_sha=os.environ['GITHUB_SHA'],package_sha256=digest(package)))
            print('SINGLE_DIAGNOSTIC_ADMISSION_PASS')
        else:
            expected=dict(run_id=os.environ['GITHUB_RUN_ID'],head_sha=os.environ['GITHUB_SHA'],package_sha256=digest(package))
            if json.loads(Path('/tmp/planning-diagnostic-admission.json').read_text())!=expected:raise ValueError('EXACT_LAUNCH_ADMISSION_REQUIRED')
            import logging
            logging.disable(logging.CRITICAL);os.environ.pop('OPENAI_LOG',None)
            from openai import OpenAI
            key=os.environ.get('DEEPSEEK_API_KEY')
            if not key:raise ValueError('EXISTING_SERVER_SECRET_UNAVAILABLE')
            result=run(OpenAI(api_key=key,base_url='https://api.deepseek.com',max_retries=0,timeout=180),package,grant,a.output)
            print('DIAGNOSTIC_TERMINATED_NO_RETRY')
