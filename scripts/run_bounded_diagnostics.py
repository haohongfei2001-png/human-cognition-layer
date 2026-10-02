"""One separately reviewed synthetic diagnostic run; no historical grant reuse."""
from dataclasses import asdict
from datetime import datetime,timedelta,timezone
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import subprocess
import threading
import time
from types import SimpleNamespace

from hcl.cognition import UniversalHCL,CallAllowance
from hcl.cognition.capability_catalog import CATALOG
from hcl.cognition.deepseek_metered import MODEL,INPUT_RATE,OUTPUT_RATE,OUTPUT_MARGIN
from hcl.cognition.universal_entry import PLANNER_POLICY
from scripts.bounded_diagnostic_protocol import (AUTH,RUNTIME_COMMIT,RUNTIME_SHA256,EXPIRES_AT,CAP,MAX_CALLS,
    MAX_REQUEST_BYTES,MAX_WAIT_SECONDS,MAX_ELAPSED_SECONDS,PROBE_QUESTION,CASES)
from scripts.bounded_diagnostic_port import DiagnosticPort
from scripts.serious_eval_contract import runtime_digest
from scripts.run_universal_development import save
from scripts.universal_development_protocol import digest
from scripts.universal_launch_guard import verify_run_history
from scripts.development_universal_sensitivity_amendment import validate_current

PACKAGE=Path('reports/HCL_BOUNDED_DIAGNOSTIC_PACKAGE.json')
GRANT=Path('.github/HCL_BOUNDED_DIAGNOSTIC_GRANT.json')
TEMPLATE=Path('.github/frozen/hcl-bounded-diagnostics-once.yml')
WORKFLOW=Path('.github/workflows/hcl-bounded-diagnostics-once.yml')
MARKER=Path('.github/HCL_BOUNDED_DIAGNOSTIC_TRIGGER.json')
RECIPIENT=Path('.github/HCL_UNIVERSAL_DEVELOPMENT_RECIPIENT.pem')
HISTORICAL_GRANTS=(Path('.github/HCL_PLANNING_DIAGNOSTIC_GRANT.json'),Path('.github/HCL_UNIVERSAL_DEVELOPMENT_GRANT.json'))


def utcnow():return datetime.now(timezone.utc)
def deadline():return datetime.fromisoformat(EXPIRES_AT.replace('Z','+00:00'))

def require_time(now):
    if not isinstance(now,datetime)or now.tzinfo is None or now+timedelta(seconds=MAX_WAIT_SECONDS)>=deadline():
        raise ValueError('NEW_DIAGNOSTIC_AUTHORIZATION_EXPIRED_OR_TOO_LATE')


def probe_messages():
    return [dict(role='system',content=PLANNER_POLICY),dict(role='user',content=json.dumps(dict(
        question=PROBE_QUESTION,sources=[],capability_inventory=[asdict(c)for c in CATALOG.values()]),
        ensure_ascii=False,sort_keys=True))]


def build_package():
    validate_current()
    if runtime_digest()!=RUNTIME_SHA256:raise ValueError('CERTIFIED_RUNTIME_DRIFT')
    files=['scripts/bounded_diagnostic_protocol.py','scripts/bounded_diagnostic_port.py',
        'scripts/run_bounded_diagnostics.py','tests/test_bounded_diagnostics.py',str(TEMPLATE),
        'scripts/run_universal_development.py','scripts/universal_development_protocol.py',
        'scripts/universal_launch_guard.py','scripts/universal_encrypted_result.py',str(RECIPIENT)]
    for path in HISTORICAL_GRANTS:
        grant=json.loads(path.read_text())
        if grant['status']!='CLOSED_NO_TRANSFER_NO_RETRY'or grant['remaining_authorized_calls']!=0 or Decimal(grant['remaining_authorized_usd'])!=0:
            raise ValueError('HISTORICAL_GRANT_NOT_CLOSED')
    fake=SimpleNamespace(max_retries=0,base_url='https://api.deepseek.com',timeout=MAX_WAIT_SECONDS)
    probes={}
    for limit in (4096,8192):
        port=DiagnosticPort(fake,planning_tokens=limit);request,encoded=port.request('planning',probe_messages())
        probes[str(limit)]=dict(request_sha256=digest(request),request_bytes=len(encoded),reservation_usd=port.reservation_usd('planning',probe_messages()))
    max_call=((2*MAX_REQUEST_BYTES+2048)*INPUT_RATE+(8192+OUTPUT_MARGIN)*OUTPUT_RATE)/1000000
    first_call=((2*MAX_REQUEST_BYTES+2048)*INPUT_RATE+(4096+OUTPUT_MARGIN)*OUTPUT_RATE)/1000000
    return dict(schema='hcl-bounded-synthetic-diagnostic-package-v1',authorization_ref=AUTH,
        certified_runtime_commit=RUNTIME_COMMIT,runtime_sha256=RUNTIME_SHA256,expires_at=EXPIRES_AT,
        approved_maximum_usd=str(CAP),approved_maximum_calls=MAX_CALLS,scheduled_maximum_calls=8,
        maximum_schedule_reservation_usd=str(first_call+7*max_call),maximum_authorized_reservation_usd=str(first_call+11*max_call),
        max_request_utf8_bytes=MAX_REQUEST_BYTES,phase_tokens=dict(probe=4096,conditional_probe=8192,planning=[4096,8192],answer=8192),
        model=MODEL,model_snapshot='RETURNED_ALIAS_NOT_PHYSICAL_SNAPSHOT_CERTIFICATION',thinking='enabled',reasoning_effort='high',
        rates_usd_per_million=dict(input=str(INPUT_RATE),output=str(OUTPUT_RATE)),pricing_verified_utc='2026-10-02',
        pricing_source='https://api-docs.deepseek.com/quick_start/pricing/',cost_basis='USAGE_RATED_PEAK_NOT_INVOICE',
        request_bound='2_UTF8_SERIALIZED_REQUEST_BYTES_PLUS_2048',output_margin=OUTPUT_MARGIN,
        maximum_wait_seconds=MAX_WAIT_SECONDS,maximum_elapsed_seconds=MAX_ELAPSED_SECONDS,sdk_retries=0,
        probe_requests=probes,probe_question_sha256=digest(PROBE_QUESTION),case_inputs_sha256=digest(CASES),
        cases=[dict(case_id=c['case_id'],input_sha256=digest(c))for c in CASES],
        schedule='ONE_4096_PROBE_THEN_ONLY_VALIDATED_LENGTH_MAY_ADMIT_ONE_8192_DIFFERENTIAL_THEN_THREE_HCL_FLOWS',
        progression='VALID_PLAN_REQUIRED_NO_TRANSPORT_OR_SCHEMA_RETRY_NO_PROMPT_REPAIR',
        source_kind='NEW_AUTHORED_SYNTHETIC_NO_REAL_PRIVATE_DATA',efficacy='NOT_AN_EFFICACY_COMPARISON',
        base_calls=0,grader_calls=0,external_lookup_calls=0,historical_budget_transfer=False,hcla_budget_transfer=False,
        final_confirmation_qualified=False,longmemeval='SEALED_NOT_ACCESSED',
        output_policy='ENCRYPTED_CONTENT_AND_ALLOWLIST_SCALARS_NO_PROVIDER_REASONING_TEXT_OR_RAW_ERRORS',
        execution_files={p:hashlib.sha256(Path(p).read_bytes()).hexdigest()for p in files},
        historical_grant_sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in HISTORICAL_GRANTS})


def expected_grant(package,*,status='READY'):
    return dict(schema='hcl-bounded-synthetic-diagnostic-grant-v1',status=status,authorization_ref=AUTH,
        package_sha256=digest(package),maximum_usd=str(CAP),maximum_calls=MAX_CALLS,expires_at=EXPIRES_AT,
        historical_budget_transfer=False,hcla_budget_transfer=False,retries=0)


def require_grant(package,grant,now):
    require_time(now)
    if package!=build_package():raise ValueError('FROZEN_DIAGNOSTIC_PACKAGE_DRIFT')
    if grant!=expected_grant(package):raise ValueError('EXACT_NEW_REVIEWED_GRANT_REQUIRED')


class Ledger:
    def __init__(self,directory,package,grant,clock):
        self.clock=clock;self.started=time.monotonic();self.lock=threading.Lock();self.closed=False
        self.directory=Path(directory);self.directory.mkdir(parents=True,exist_ok=False,mode=0o700)
        self.path=self.directory/'receipt.json'
        self.value=dict(schema='hcl-bounded-synthetic-diagnostic-receipt-v1',package_sha256=digest(package),
            authorization_ref=AUTH,maximum_usd=str(CAP),maximum_calls=MAX_CALLS,expires_at=EXPIRES_AT,
            status='RUNNING',calls=[],results=[],reserved_usd='0',invoice_cost_usd=None,
            cost_basis='USAGE_RATED_PEAK_NOT_INVOICE',historical_budget_transfer=False,hcla_budget_transfer=False,
            original_historical_failure_cause='UNRESOLVED_NOT_RETROACTIVELY_IDENTIFIED')
        save(self.path,self.value)

    def persist(self):
        try:save(self.path,self.value)
        except Exception:
            self.closed=True
            raise

    def admit(self):
        if self.closed:raise ValueError('CLOSED_NO_TRANSFER_NO_RETRY')
        require_time(self.clock())
        if time.monotonic()-self.started+MAX_WAIT_SECONDS>=MAX_ELAPSED_SECONDS:raise ValueError('BATCH_DEADLINE_EXPIRED')

    def record(self,stage,snapshot,requests,responses,diagnostics):
        with self.lock:
            for attempt in snapshot['attempts']:
                phase=attempt['phase'];identity=stage+':'+phase
                matches=[r for r in self.value['calls']if r['call_id']==identity]
                request=requests[phase];request_hash=digest(request)
                if not matches:
                    self.admit();reserve=Decimal(attempt['reserved_usd'])
                    if len(self.value['calls'])>=MAX_CALLS:raise ValueError('CALL_CAP_EXHAUSTED')
                    if not reserve.is_finite()or reserve<0 or Decimal(self.value['reserved_usd'])+reserve>CAP:raise ValueError('USD_CAP_EXHAUSTED')
                    row=dict(call_id=identity,ordinal=len(self.value['calls'])+1,stage=stage,phase=phase,
                        request=request,request_sha256=request_hash)
                    self.value['calls'].append(row);self.value['reserved_usd']=str(Decimal(self.value['reserved_usd'])+reserve)
                else:
                    row=matches[0]
                    if row['request_sha256']!=request_hash or row['reserved_usd']!=attempt['reserved_usd']:
                        raise ValueError('RESERVED_REQUEST_IDENTITY_CHANGED')
                row.update(attempt)
                if phase in responses:row['response_content']=responses[phase]
                if phase in diagnostics:row['response_diagnostics']=diagnostics[phase]
            self.persist()

    def before_send(self,stage,phase):
        with self.lock:
            self.admit();rows=[r for r in self.value['calls']if r['call_id']==stage+':'+phase]
            if len(rows)!=1 or rows[0].get('invocation_status')!='NOT_INVOKED':raise ValueError('UNIQUE_DURABLE_RESERVATION_REQUIRED')
            rows[0].update(provider_call=True,invocation_status='INVOKED_OR_SEND_UNKNOWN')
            self.persist()

    def close(self,status):
        with self.lock:
            self.closed=True
            self.value.update(status=status,budget_state='CLOSED_NO_TRANSFER_NO_RETRY',remaining_authorized_usd='0',remaining_authorized_calls=0)
            self.persist()


class RecordedPort:
    provider_free=False
    cost_basis='USAGE_RATED_PEAK_NOT_INVOICE'
    def __init__(self,client,ledger,stage,planning_tokens):
        self.inner=DiagnosticPort(client,planning_tokens=planning_tokens)
        self.ledger=ledger;self.stage=stage;self.requests={};self.responses={};self.diagnostics={}
    def reservation_usd(self,phase,messages):
        value=self.inner.reservation_usd(phase,messages);request,_=self.inner.request(phase,messages)
        self.requests[phase]=request;return value
    def complete(self,phase,messages):
        self.ledger.before_send(self.stage,phase)
        try:
            result=self.inner.complete(phase,messages);self.responses[phase]=result['text'];return result
        finally:self.diagnostics[phase]=dict(self.inner.diagnostics)
    def journal(self,snapshot):self.ledger.record(self.stage,snapshot,self.requests,self.responses,self.diagnostics)


def run(client,package,grant,directory,*,clock=utcnow):
    require_grant(package,grant,clock());ledger=Ledger(directory,package,grant,clock)
    try:
        selected=None
        for tokens in (4096,8192):
            stage='probe_'+str(tokens);port=RecordedPort(client,ledger,stage,tokens)
            allowance=CallAllowance(1,CAP,AUTH,journal=port.journal)
            raw=None
            try:raw=allowance.call(port,'planning',probe_messages())
            except Exception:pass
            finally:allowance.closed=True
            if raw is not None:
                try:UniversalHCL()._validate_plan(raw)
                except Exception:
                    ledger.value['results'].append(dict(stage=stage,status='PLAN_SCHEMA_REJECTED_NO_RETRY'))
                    ledger.close('PLANNING_SCHEMA_REJECTED_NO_FULL_FLOW');return ledger.value
                selected=tokens;ledger.value['results'].append(dict(stage=stage,status='PLAN_SCHEMA_VALID',planning_tokens=tokens));break
            row=ledger.value['calls'][-1]if ledger.value['calls']else {}
            data=row.get('response_diagnostics',{})
            controlled=(not ledger.closed and tokens==4096 and row.get('call_id')==stage+':planning' and
                row.get('failure_code')=='INCOMPLETE_ANSWER_NO_RETRY' and data.get('choice_count')==1 and
                data.get('finish_reasons')==['length'] and isinstance(data.get('usage'),dict))
            ledger.value['results'].append(dict(stage=stage,status='INCOMPLETE_OR_FAILED',
                conditional_output_limit_differential_admitted=controlled))
            save(ledger.path,ledger.value)
            if not controlled:
                ledger.close('PLANNING_FAILED_NO_FULL_FLOW');return ledger.value
        if selected is None:
            ledger.close('PLANNING_FAILED_NO_FULL_FLOW');return ledger.value
        ledger.value['selected_planning_tokens']=selected
        for case in CASES:
            session=UniversalHCL()
            for sid,text in case['sources'].items():session.put_source(sid,text)
            port=RecordedPort(client,ledger,case['case_id'],selected)
            allowance=CallAllowance(2,CAP,AUTH,journal=port.journal)
            result=session.answer(case['question'],planner_backend=port,answer_backend=port,allowance=allowance)
            allowance.closed=True
            ledger.value['results'].append(dict(stage=case['case_id'],orchestration=result))
            save(ledger.path,ledger.value)
            if result['status']!='ANSWERED_WITH_EXPLICIT_LIMITS':
                ledger.close('FULL_FLOW_FAILED_NO_RETRY');return ledger.value
        ledger.close('COMPLETED_SYNTHETIC_FUNCTIONAL_DIAGNOSTIC')
    except Exception:
        ledger.close('FAILED_OR_UNKNOWN_NO_RETRY')
    return ledger.value


def verify_launch(run_id,attempt,runs,event,parent,paths,marker,package,grant,now):
    require_grant(package,grant,now);verify_run_history(run_id,attempt,runs)
    expected=dict(schema='hcl-bounded-diagnostic-single-launch-marker-v1',authorization_ref=AUTH,
        package_sha256=digest(package),grant_sha256=digest(grant),executor_commit=parent)
    if event!='push'or not isinstance(parent,str)or len(parent)!=40 or any(c not in '0123456789abcdef'for c in parent)or paths!=[str(MARKER)]or marker!=expected:
        raise ValueError('EXACT_REVIEWED_EXECUTOR_MARKER_ONLY_REQUIRED')
    return True


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--freeze',action='store_true');p.add_argument('--check-launch');p.add_argument('--execute',action='store_true');p.add_argument('--output',default='bounded-diagnostic-private');a=p.parse_args()
    os.umask(0o077)
    if sum((a.freeze,bool(a.check_launch),a.execute))!=1:raise ValueError('EXACTLY_ONE_MODE_REQUIRED')
    if a.freeze:
        package=build_package();save(PACKAGE,package);save(GRANT,expected_grant(package,status='PREPARED_REVIEW_REQUIRED'))
    else:
        if os.environ.get('GITHUB_REF')!='refs/heads/main'or os.environ.get('GITHUB_RUN_ATTEMPT')!='1':raise ValueError('MAIN_ATTEMPT_ONE_REQUIRED')
        if WORKFLOW.read_bytes()!=TEMPLATE.read_bytes():raise ValueError('FROZEN_WORKFLOW_REQUIRED')
        package=json.loads(PACKAGE.read_text());grant=json.loads(GRANT.read_text());require_grant(package,grant,utcnow())
        admission=Path('/tmp/bounded-diagnostic-admission.json')
        expected=dict(run_id=os.environ['GITHUB_RUN_ID'],head_sha=os.environ['GITHUB_SHA'],package_sha256=digest(package),grant_sha256=digest(grant))
        if a.check_launch:
            pages=json.loads(Path(a.check_launch).read_text());history=[r for page in pages for r in page['workflow_runs']]
            ancestry=subprocess.check_output(['git','rev-list','--parents','-n','1','HEAD'],text=True).split()
            if len(ancestry)!=2:raise ValueError('SINGLE_PARENT_REQUIRED')
            verify_launch(os.environ['GITHUB_RUN_ID'],os.environ['GITHUB_RUN_ATTEMPT'],history,os.environ.get('GITHUB_EVENT_NAME'),ancestry[1],
                subprocess.check_output(['git','diff-tree','--no-commit-id','--name-only','-r','HEAD'],text=True).splitlines(),
                json.loads(MARKER.read_text()),package,grant,utcnow())
            save(admission,expected);print('ONE_NEW_BOUNDED_DIAGNOSTIC_ADMISSION_PASS')
        else:
            if json.loads(admission.read_text())!=expected:raise ValueError('EXACT_RUN_ADMISSION_REQUIRED')
            import logging
            logging.disable(logging.CRITICAL);os.environ.pop('OPENAI_LOG',None)
            from openai import OpenAI
            key=os.environ.get('DEEPSEEK_API_KEY')
            if not key:raise ValueError('EXISTING_SERVER_SECRET_UNAVAILABLE')
            run(OpenAI(api_key=key,base_url='https://api.deepseek.com',max_retries=0,timeout=MAX_WAIT_SECONDS),package,grant,a.output)
            print('BOUNDED_DIAGNOSTIC_TERMINATED_NO_RETRY')
