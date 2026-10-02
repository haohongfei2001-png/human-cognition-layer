"""Separately reviewed sub-run with immutable prior charges inside one aggregate cap."""
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import subprocess
from types import SimpleNamespace

from hcl.cognition import UniversalHCL,CallAllowance
from scripts import run_bounded_diagnostics as previous
from scripts.bounded_diagnostic_protocol import RUNTIME_COMMIT,RUNTIME_SHA256,MAX_WAIT_SECONDS,CASES
from scripts.output_limit_protocol import (AUTH,CAMPAIGN_AUTH,EXPIRES_AT,PRIOR_RUN,PRIOR_RECEIPT_SHA,PRIOR_CALLS,
    PRIOR_HELD,AGGREGATE_CAP,AGGREGATE_CALLS,MAX_SUBRUN_CALLS,MAX_REQUEST_BYTES,FROZEN_REQUEST,FROZEN_REQUEST_SHA,PRIOR_CLOSURE,PRIOR_GRANT)
from scripts.output_limit_port import OutputLimitPort
from scripts.run_universal_development import save
from scripts.universal_development_protocol import digest
from scripts.universal_launch_guard import verify_run_history

PACKAGE=Path('reports/HCL_OUTPUT_LIMIT_CONTINUATION_PACKAGE.json')
GRANT=Path('.github/HCL_OUTPUT_LIMIT_CONTINUATION_GRANT.json')
TEMPLATE=Path('.github/frozen/hcl-output-limit-continuation-once.yml')
WORKFLOW=Path('.github/workflows/hcl-output-limit-continuation-once.yml')
MARKER=Path('.github/HCL_OUTPUT_LIMIT_CONTINUATION_TRIGGER.json')


def previous_charges():
    report=json.loads(PRIOR_CLOSURE.read_text());grant=json.loads(PRIOR_GRANT.read_text())
    if (report['run_id']!=PRIOR_RUN or report['receipt_sha256']!=PRIOR_RECEIPT_SHA or report['calls']!=PRIOR_CALLS or
        Decimal(report['reserved_usd'])!=PRIOR_HELD or len(report['calls_detail'])!=PRIOR_CALLS or
        sum(Decimal(c['reserved_usd'])for c in report['calls_detail'])!=PRIOR_HELD or
        grant['status']!='CLOSED_NO_TRANSFER_NO_RETRY'or grant['run_id']!=PRIOR_RUN or
        grant['remaining_authorized_calls']!=0 or Decimal(grant['remaining_authorized_usd'])!=0):
        raise ValueError('EXACT_CLOSED_PREVIOUS_RECEIPT_AND_CHARGES_REQUIRED')
    return dict(run_id=PRIOR_RUN,receipt_sha256=PRIOR_RECEIPT_SHA,calls=PRIOR_CALLS,reserved_usd=str(PRIOR_HELD),
        closure_sha256=hashlib.sha256(PRIOR_CLOSURE.read_bytes()).hexdigest(),grant_sha256=hashlib.sha256(PRIOR_GRANT.read_bytes()).hexdigest())


def frozen_request():
    request=json.loads(FROZEN_REQUEST.read_text())
    if digest(request)!=FROZEN_REQUEST_SHA or request['max_tokens']!=4096:
        raise ValueError('EXACT_PREVIOUS_FAILED_REQUEST_REQUIRED')
    return request


def source_session():
    value=json.loads(frozen_request()['messages'][-1]['content'])
    if value['question']!=CASES[1]['question'] or {r['source_id']:r['text']for r in value['sources']}!=CASES[1]['sources']:
        raise ValueError('PREVIOUS_PUBLIC_SYNTHETIC_CASE_REQUIRED')
    session=UniversalHCL()
    for source in value['sources']:
        if source['version']!=1:raise ValueError('FROZEN_SOURCE_VERSION_REQUIRED')
        session.put_source(source['source_id'],source['text'])
        # Preserve the prior real ingestion snapshot, not a newly invented event time.
        session.sources[source['source_id']]=dict(source)
    return session,value['question']


def build_package():
    prior=previous_charges();base=previous.build_package();request=frozen_request()
    port_client=SimpleNamespace(max_retries=0,base_url='https://api.deepseek.com',timeout=MAX_WAIT_SECONDS)
    probes={}
    for tokens in (8192,16384):
        port=OutputLimitPort(port_client,planning_tokens=tokens)
        new,encoded=port.request('planning',request['messages'])
        assert {k:v for k,v in new.items()if k!='max_tokens'}=={k:v for k,v in request.items()if k!='max_tokens'}
        probes[str(tokens)]=dict(request_sha256=digest(new),request_bytes=len(encoded),reservation_usd=port.reservation_usd('planning',request['messages']))
    normal=((2*MAX_REQUEST_BYTES+2048)*previous.INPUT_RATE+(8192+previous.OUTPUT_MARGIN)*previous.OUTPUT_RATE)/1000000
    larger=((2*MAX_REQUEST_BYTES+2048)*previous.INPUT_RATE+(16384+previous.OUTPUT_MARGIN)*previous.OUTPUT_RATE)/1000000
    worst=3*normal+2*larger
    files=sorted(set(base['execution_files'])|{str(FROZEN_REQUEST),'scripts/output_limit_protocol.py','scripts/output_limit_port.py',
        'scripts/run_output_limit_continuation.py','tests/test_output_limit_continuation.py',str(TEMPLATE)})
    return dict(schema='hcl-output-limit-continuation-package-v1',authorization_ref=AUTH,campaign_authorization_ref=CAMPAIGN_AUTH,
        aggregate_maximum_usd=str(AGGREGATE_CAP),aggregate_maximum_calls=AGGREGATE_CALLS,prior_charges=prior,
        remaining_campaign_usd=str(AGGREGATE_CAP-PRIOR_HELD),remaining_campaign_calls=AGGREGATE_CALLS-PRIOR_CALLS,
        subrun_maximum_calls=MAX_SUBRUN_CALLS,subrun_worst_reservation_usd=str(worst),aggregate_worst_reservation_usd=str(PRIOR_HELD+worst),
        expires_at=EXPIRES_AT,runtime_commit=RUNTIME_COMMIT,runtime_sha256=RUNTIME_SHA256,
        previous_package_sha256=digest(base),previous_failed_request_sha256=FROZEN_REQUEST_SHA,
        source_planning_requests=probes,g05_ordinary_input_sha256=digest(CASES[-1]),
        max_request_utf8_bytes=MAX_REQUEST_BYTES,phase_tokens=dict(initial_planning=8192,conditional_planning=16384,answer=8192),
        model=previous.MODEL,thinking='enabled',reasoning_effort='high',
        rates_usd_per_million=dict(input=str(previous.INPUT_RATE),output=str(previous.OUTPUT_RATE)),
        output_margin=previous.OUTPUT_MARGIN,maximum_wait_seconds=MAX_WAIT_SECONDS,maximum_elapsed_seconds=previous.MAX_ELAPSED_SECONDS,
        schedule='EXACT_FAILED_SOURCE_FLOW_AT_8192_THEN_ONLY_VALIDATED_PLANNING_LENGTH_MAY_ADMIT_ONE_16384_DIFFERENTIAL_THEN_G05_AT_SELECTED_LIMIT',
        metadata_cost_scope='SEPARATE_DIAGNOSTIC_PORT_VALIDATION_UP_TO_16384_TOKENS_INCLUDES_REASONING_ONCE',
        raw_errors_or_reasoning_text_retained=False,base_calls=0,grader_calls=0,retries=0,
        previous_reservations_recycled=False,closed_subrun_reopened=False,hcla_budget_transfer=False,
        efficacy='NOT_AN_EFFICACY_COMPARISON',final_confirmation_qualified=False,
        execution_files={p:hashlib.sha256(Path(p).read_bytes()).hexdigest()for p in files})


def expected_grant(package,*,status='READY'):
    return dict(schema='hcl-output-limit-continuation-grant-v1',status=status,authorization_ref=AUTH,
        campaign_authorization_ref=CAMPAIGN_AUTH,package_sha256=digest(package),
        aggregate_maximum_usd=str(AGGREGATE_CAP),aggregate_maximum_calls=AGGREGATE_CALLS,
        prior_calls=PRIOR_CALLS,prior_reserved_usd=str(PRIOR_HELD),prior_receipt_sha256=PRIOR_RECEIPT_SHA,
        subrun_maximum_calls=MAX_SUBRUN_CALLS,expires_at=EXPIRES_AT,closed_subrun_reopened=False,
        previous_reservations_recycled=False,hcla_budget_transfer=False,retries=0)


def require_grant(package,grant,now):
    previous.require_time(now)
    if package!=build_package():raise ValueError('FROZEN_AGGREGATE_PACKAGE_DRIFT')
    if grant!=expected_grant(package):raise ValueError('EXACT_AGGREGATE_CONTINUATION_GRANT_REQUIRED')


class Ledger(previous.Ledger):
    def __init__(self,directory,package,grant,clock):
        super().__init__(directory,package,grant,clock)
        self.value.update(schema='hcl-output-limit-continuation-receipt-v1',authorization_ref=AUTH,
            campaign_authorization_ref=CAMPAIGN_AUTH,prior_charges=package['prior_charges'],
            aggregate_maximum_usd=str(AGGREGATE_CAP),aggregate_maximum_calls=AGGREGATE_CALLS,
            aggregate_reserved_usd=str(PRIOR_HELD),aggregate_calls=PRIOR_CALLS,subrun_maximum_calls=MAX_SUBRUN_CALLS)
        self.persist()

    def close(self,status):
        self.value.update(aggregate_remaining_calls=AGGREGATE_CALLS-PRIOR_CALLS-len(self.value['calls']),
            aggregate_remaining_usd=str(AGGREGATE_CAP-PRIOR_HELD-Decimal(self.value['reserved_usd'])))
        super().close(status)

    def record(self,stage,snapshot,requests,responses,diagnostics):
        with self.lock:
            for attempt in snapshot['attempts']:
                phase=attempt['phase'];identity=stage+':'+phase;request=requests[phase];request_hash=digest(request)
                rows=[r for r in self.value['calls']if r['call_id']==identity]
                if not rows:
                    self.admit();reserve=Decimal(attempt['reserved_usd'])
                    if len(self.value['calls'])>=MAX_SUBRUN_CALLS or PRIOR_CALLS+len(self.value['calls'])>=AGGREGATE_CALLS:
                        raise ValueError('AGGREGATE_CALL_CAP_EXHAUSTED')
                    if not reserve.is_finite()or reserve<0 or PRIOR_HELD+Decimal(self.value['reserved_usd'])+reserve>AGGREGATE_CAP:
                        raise ValueError('AGGREGATE_USD_CAP_EXHAUSTED')
                    row=dict(call_id=identity,ordinal=len(self.value['calls'])+1,aggregate_ordinal=PRIOR_CALLS+len(self.value['calls'])+1,
                        stage=stage,phase=phase,request=request,request_sha256=request_hash)
                    self.value['calls'].append(row);self.value['reserved_usd']=str(Decimal(self.value['reserved_usd'])+reserve)
                else:
                    row=rows[0]
                    if row['request_sha256']!=request_hash or row['reserved_usd']!=attempt['reserved_usd']:raise ValueError('RESERVED_REQUEST_IDENTITY_CHANGED')
                    if attempt.get('invocation_status')=='NOT_INVOKED'and row.get('invocation_status')!='NOT_INVOKED':
                        raise ValueError('INVOKED_CALL_ID_CANNOT_BE_REARMED')
                row.update(attempt)
                if phase in responses:row['response_content']=responses[phase]
                if phase in diagnostics:
                    data=diagnostics[phase];row['response_diagnostics']=data
                    # Production's generic failure allowlist is frozen at 8192.
                    # This separately frozen port validates its own full 16384 bound.
                    if data.get('usage_valid')is True:
                        counts=data['usage'];rated=(counts['prompt_tokens']*previous.INPUT_RATE+counts['completion_tokens']*previous.OUTPUT_RATE)/1000000
                        if rated>Decimal(row['reserved_usd']):raise ValueError('DIAGNOSTIC_USAGE_EXCEEDS_RESERVATION')
                        row.update(usage=counts,actual_usd=str(rated),usage_source='FROZEN_DIAGNOSTIC_PORT_COMPLETE_OUTPUT_BOUND')
                        if row.get('status')!='RETURNED':row['invocation_status']='RESPONSE_RETURNED_REJECTED'
            self.value.update(aggregate_calls=PRIOR_CALLS+len(self.value['calls']),aggregate_reserved_usd=str(PRIOR_HELD+Decimal(self.value['reserved_usd'])))
            self.persist()


class RecordedPort(previous.RecordedPort):
    def __init__(self,client,ledger,stage,planning_tokens):
        self.inner=OutputLimitPort(client,planning_tokens=planning_tokens)
        self.ledger=ledger;self.stage=stage;self.requests={};self.responses={};self.diagnostics={}


def run(client,package,grant,directory,*,clock=previous.utcnow):
    require_grant(package,grant,clock());ledger=Ledger(directory,package,grant,clock)
    try:
        selected=None
        for tokens in (8192,16384):
            stage='source_flow_'+str(tokens);session,question=source_session()
            port=RecordedPort(client,ledger,stage,tokens);allowance=CallAllowance(2,AGGREGATE_CAP,AUTH,journal=port.journal)
            result=session.answer(question,planner_backend=port,answer_backend=port,allowance=allowance);allowance.closed=True
            ledger.value['results'].append(dict(stage=stage,orchestration=result));ledger.persist()
            if result['status']=='ANSWERED_WITH_EXPLICIT_LIMITS':selected=tokens;break
            row=ledger.value['calls'][-1]if ledger.value['calls']else {};data=row.get('response_diagnostics',{})
            controlled=(not ledger.closed and tokens==8192 and row.get('call_id')==stage+':planning'and
                row.get('failure_code')=='INCOMPLETE_ANSWER_NO_RETRY'and data.get('choice_count')==1 and
                data.get('finish_reasons')==['length']and data.get('usage_valid')is True)
            ledger.value['results'][-1]['conditional_output_limit_differential_admitted']=controlled;ledger.persist()
            if not controlled:ledger.close('SOURCE_FLOW_FAILED_NO_FURTHER_CALL');return ledger.value
        if selected is None:ledger.close('SOURCE_FLOW_FAILED_NO_FURTHER_CALL');return ledger.value
        case=CASES[-1];session=UniversalHCL()
        for sid,text in case['sources'].items():session.put_source(sid,text)
        port=RecordedPort(client,ledger,'g05_flow',selected);allowance=CallAllowance(2,AGGREGATE_CAP,AUTH,journal=port.journal)
        result=session.answer(case['question'],planner_backend=port,answer_backend=port,allowance=allowance);allowance.closed=True
        ledger.value['selected_planning_tokens']=selected;ledger.value['results'].append(dict(stage='g05_flow',orchestration=result))
        ledger.close('COMPLETED_OUTPUT_LIMIT_FUNCTIONAL_DIAGNOSTIC'if result['status']=='ANSWERED_WITH_EXPLICIT_LIMITS'else 'G05_FLOW_FAILED_NO_FURTHER_CALL')
    except Exception:ledger.close('FAILED_OR_UNKNOWN_NO_RETRY')
    return ledger.value


def verify_launch(run_id,attempt,runs,event,parent,paths,marker,package,grant,now):
    require_grant(package,grant,now);verify_run_history(run_id,attempt,runs)
    expected=dict(schema='hcl-output-limit-single-launch-marker-v1',authorization_ref=AUTH,
        package_sha256=digest(package),grant_sha256=digest(grant),executor_commit=parent)
    if event!='push'or not isinstance(parent,str)or len(parent)!=40 or any(c not in '0123456789abcdef'for c in parent)or paths!=[str(MARKER)]or marker!=expected:
        raise ValueError('EXACT_REVIEWED_EXECUTOR_MARKER_ONLY_REQUIRED')
    return True


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--freeze',action='store_true');p.add_argument('--check-launch');p.add_argument('--execute',action='store_true');p.add_argument('--output',default='output-limit-private');a=p.parse_args();os.umask(0o077)
    if sum((a.freeze,bool(a.check_launch),a.execute))!=1:raise ValueError('EXACTLY_ONE_MODE_REQUIRED')
    if a.freeze:
        package=build_package();save(PACKAGE,package);save(GRANT,expected_grant(package,status='PREPARED_REVIEW_REQUIRED'))
    else:
        if os.environ.get('GITHUB_REF')!='refs/heads/main'or os.environ.get('GITHUB_RUN_ATTEMPT')!='1':raise ValueError('MAIN_ATTEMPT_ONE_REQUIRED')
        if WORKFLOW.read_bytes()!=TEMPLATE.read_bytes():raise ValueError('FROZEN_WORKFLOW_REQUIRED')
        package=json.loads(PACKAGE.read_text());grant=json.loads(GRANT.read_text());require_grant(package,grant,previous.utcnow())
        expected=dict(run_id=os.environ['GITHUB_RUN_ID'],head_sha=os.environ['GITHUB_SHA'],package_sha256=digest(package),grant_sha256=digest(grant))
        admission=Path('/tmp/output-limit-admission.json')
        if a.check_launch:
            history=[r for page in json.loads(Path(a.check_launch).read_text())for r in page['workflow_runs']]
            ancestry=subprocess.check_output(['git','rev-list','--parents','-n','1','HEAD'],text=True).split()
            if len(ancestry)!=2:raise ValueError('SINGLE_PARENT_REQUIRED')
            verify_launch(os.environ['GITHUB_RUN_ID'],os.environ['GITHUB_RUN_ATTEMPT'],history,os.environ.get('GITHUB_EVENT_NAME'),ancestry[1],
                subprocess.check_output(['git','diff-tree','--no-commit-id','--name-only','-r','HEAD'],text=True).splitlines(),json.loads(MARKER.read_text()),package,grant,previous.utcnow())
            save(admission,expected);print('AGGREGATE_BOUND_OUTPUT_LIMIT_ADMISSION_PASS')
        else:
            if json.loads(admission.read_text())!=expected:raise ValueError('EXACT_RUN_ADMISSION_REQUIRED')
            import logging
            logging.disable(logging.CRITICAL);os.environ.pop('OPENAI_LOG',None)
            from openai import OpenAI
            key=os.environ.get('DEEPSEEK_API_KEY')
            if not key:raise ValueError('EXISTING_SERVER_SECRET_UNAVAILABLE')
            run(OpenAI(api_key=key,base_url='https://api.deepseek.com',max_retries=0,timeout=MAX_WAIT_SECONDS),package,grant,a.output)
            print('OUTPUT_LIMIT_DIAGNOSTIC_TERMINATED_NO_RETRY')
