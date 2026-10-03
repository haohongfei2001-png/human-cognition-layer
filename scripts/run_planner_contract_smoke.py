"""Two-call interface smoke inside the existing aggregate campaign; no retry."""
from dataclasses import asdict
from decimal import Decimal
import hashlib,json,os,subprocess
from pathlib import Path
from types import SimpleNamespace

from hcl.cognition import UniversalHCL,CallAllowance
from hcl.cognition.capability_catalog import CATALOG
from hcl.cognition.universal_entry import PLANNER_POLICY
from scripts import run_bounded_diagnostics as common
from scripts.output_limit_port import OutputLimitPort
from scripts.run_output_limit_continuation import RecordedPort
from scripts.run_universal_development import save
from scripts.universal_development_protocol import digest
from scripts.universal_launch_guard import verify_run_history
from scripts.serious_eval_contract import runtime_digest
from scripts.development_planner_contracts_amendment import validate_current

CAMPAIGN_AUTH='OWNER_CONFIRMED_2026_10_02_I02_NEW_1_USD_12_CALLS'
AUTH=CAMPAIGN_AUTH+'_PLANNER_CONTRACT_SMOKE'
RUNTIME_COMMIT='e0c9cb89fcb1fd1c584944d7cf772432867cebc3'
RUNTIME_SHA='3932cdda69549f66311fdeedd7d8182b6ecb232e1b4cb1a533e589b74df1b628'
EXPIRES_AT='2026-10-03T08:00:00Z'
PRIOR_RECEIPT_SHA='5de9228f032deac21b2e93d407028c2a5f614575413125cf2626fc93a79deff9'
PRIOR_CALLS=9;PRIOR_HELD=Decimal('0.51528576');CAP=Decimal('1.00');MAX_CALLS=12;NEW_CALLS=2
REQUEST=Path('.github/frozen/hcl-planner-contract-smoke-request.json')
REQUEST_SHA='b8d2e0f68e9ceabb8a92d47a9bbebba182e3769fb61c561ae341bb69e6f32ab6'
PRIOR=Path('reports/HCL_OUTPUT_LIMIT_CONTINUATION_CLOSURE.json')
PRIOR_GRANT=Path('.github/HCL_OUTPUT_LIMIT_CONTINUATION_GRANT.json')
PACKAGE=Path('reports/HCL_PLANNER_CONTRACT_SMOKE_PACKAGE.json')
GRANT=Path('.github/HCL_PLANNER_CONTRACT_SMOKE_GRANT.json')
TEMPLATE=Path('.github/frozen/hcl-planner-contract-smoke-once.yml')
WORKFLOW=Path('.github/workflows/hcl-planner-contract-smoke-once.yml')
MARKER=Path('.github/HCL_PLANNER_CONTRACT_SMOKE_TRIGGER.json')


def prior_charges():
    r=json.loads(PRIOR.read_text());g=json.loads(PRIOR_GRANT.read_text())
    if (r['receipt_sha256']!=PRIOR_RECEIPT_SHA or r['aggregate_calls']!=PRIOR_CALLS or
        Decimal(r['aggregate_reserved_usd'])!=PRIOR_HELD or
        r['prior_charges']['calls']+r['calls']!=PRIOR_CALLS or
        Decimal(r['prior_charges']['reserved_usd'])+sum(Decimal(c['reserved_usd'])for c in r['calls_detail'])!=PRIOR_HELD or
        g['status']!='CLOSED_NO_TRANSFER_NO_RETRY'or g['remaining_authorized_calls']!=0 or Decimal(g['remaining_authorized_usd'])!=0):
        raise ValueError('ALL_NINE_PRIOR_CALLS_AND_FULL_HOLDS_REQUIRED')
    return dict(calls=PRIOR_CALLS,reserved_usd=str(PRIOR_HELD),receipt_sha256=PRIOR_RECEIPT_SHA,
        closure_sha256=hashlib.sha256(PRIOR.read_bytes()).hexdigest(),grant_sha256=hashlib.sha256(PRIOR_GRANT.read_bytes()).hexdigest())


def frozen_request():
    request=json.loads(REQUEST.read_text())
    if digest(request)!=REQUEST_SHA or request['max_tokens']!=16384:raise ValueError('EXACT_NEW_CONTRACT_REQUEST_REQUIRED')
    payload=json.loads(request['messages'][-1]['content'])
    if request['messages'][0]['content']!=PLANNER_POLICY or payload['capability_inventory']!=json.loads(json.dumps([asdict(c)for c in CATALOG.values()])):
        raise ValueError('CURRENT_POLICY_AND_INVENTORY_REQUIRED')
    return request


def session_from_snapshot():
    payload=json.loads(frozen_request()['messages'][-1]['content']);session=UniversalHCL()
    for source in payload['sources']:
        if source['version']!=1:raise ValueError('FROZEN_SOURCE_VERSION_REQUIRED')
        session.put_source(source['source_id'],source['text']);session.sources[source['source_id']]=dict(source)
    return session,payload['question']


def build_package():
    validate_current()
    if runtime_digest()!=RUNTIME_SHA:raise ValueError('CERTIFIED_CONTRACT_RUNTIME_REQUIRED')
    prior=prior_charges();request=frozen_request()
    client=SimpleNamespace(base_url='https://api.deepseek.com',max_retries=0,timeout=180)
    port=OutputLimitPort(client,planning_tokens=16384);actual,encoded=port.request('planning',request['messages'])
    if actual!=request:raise ValueError('FROZEN_TRANSPORT_CONFIGURATION_REQUIRED')
    planning=Decimal(port.reservation_usd('planning',request['messages']))
    answer=((2*36000+2048)*common.INPUT_RATE+(8192+common.OUTPUT_MARGIN)*common.OUTPUT_RATE)/1000000
    files=['scripts/run_planner_contract_smoke.py','tests/test_planner_contract_smoke.py',str(REQUEST),str(TEMPLATE),
        'scripts/output_limit_port.py','scripts/output_limit_protocol.py','scripts/run_output_limit_continuation.py',
        'scripts/bounded_diagnostic_port.py','scripts/bounded_diagnostic_protocol.py','scripts/run_bounded_diagnostics.py',
        'scripts/run_universal_development.py','scripts/universal_development_protocol.py','scripts/universal_launch_guard.py',
        'scripts/universal_encrypted_result.py','.github/HCL_UNIVERSAL_DEVELOPMENT_RECIPIENT.pem']
    return dict(schema='hcl-planner-contract-smoke-package-v1',authorization_ref=AUTH,campaign_authorization_ref=CAMPAIGN_AUTH,
        prior_charges=prior,aggregate_maximum_calls=MAX_CALLS,aggregate_maximum_usd=str(CAP),subrun_maximum_calls=NEW_CALLS,
        maximum_new_reservation_usd=str(planning+answer),maximum_aggregate_reservation_usd=str(PRIOR_HELD+planning+answer),
        planning_reservation_usd=str(planning),maximum_answer_reservation_usd=str(answer),request_sha256=REQUEST_SHA,
        complete_planning_request_utf8_bytes=len(encoded),maximum_complete_request_utf8_bytes=36000,
        expires_at=EXPIRES_AT,runtime_commit=RUNTIME_COMMIT,runtime_sha256=RUNTIME_SHA,
        model=common.MODEL,thinking='enabled',reasoning_effort='high',planning_tokens=16384,answer_tokens=8192,
        rates_usd_per_million=dict(input=str(common.INPUT_RATE),output=str(common.OUTPUT_RATE)),output_margin=32,
        maximum_wait_seconds=180,maximum_elapsed_seconds=1800,retries=0,differential_calls=0,base_calls=0,grader_calls=0,
        purpose='FUNCTIONAL_INTERFACE_VALIDATION_ON_UNCHANGED_EXPOSED_SYNTHETIC_INPUT_NOT_EFFICACY',
        forced_capability_selection=False,negative_selection_is_terminal_result=True,
        previous_grants_reopened=False,previous_reservations_recycled=False,hcla_budget_transfer=False,
        execution_files={p:hashlib.sha256(Path(p).read_bytes()).hexdigest()for p in files})


def expected_grant(package,*,status='READY'):
    return dict(schema='hcl-planner-contract-smoke-grant-v1',status=status,authorization_ref=AUTH,
        campaign_authorization_ref=CAMPAIGN_AUTH,package_sha256=digest(package),aggregate_maximum_calls=MAX_CALLS,
        aggregate_maximum_usd=str(CAP),prior_calls=PRIOR_CALLS,prior_reserved_usd=str(PRIOR_HELD),prior_receipt_sha256=PRIOR_RECEIPT_SHA,
        subrun_maximum_calls=NEW_CALLS,expires_at=EXPIRES_AT,retries=0,previous_grants_reopened=False,hcla_budget_transfer=False)


def require_grant(package,grant,now):
    common.require_time(now)
    if package!=build_package():raise ValueError('FROZEN_CONTRACT_SMOKE_PACKAGE_DRIFT')
    if grant!=expected_grant(package):raise ValueError('EXACT_REVIEWED_AGGREGATE_SMOKE_GRANT_REQUIRED')


class Ledger(common.Ledger):
    def __init__(self,directory,package,grant,clock):
        super().__init__(directory,package,grant,clock);self.maximum_new=Decimal(package['maximum_new_reservation_usd'])
        self.value.update(schema='hcl-planner-contract-smoke-receipt-v1',authorization_ref=AUTH,campaign_authorization_ref=CAMPAIGN_AUTH,
            prior_charges=package['prior_charges'],subrun_maximum_calls=NEW_CALLS,aggregate_calls=PRIOR_CALLS,aggregate_reserved_usd=str(PRIOR_HELD))
        self.persist()
    def record(self,stage,snapshot,requests,responses,diagnostics):
        with self.lock:
            for attempt in snapshot['attempts']:
                phase=attempt['phase'];request=requests[phase];request_hash=digest(request)
                if stage!='contract_smoke'or phase not in ('planning','answer'):raise ValueError('ONE_FROZEN_FLOW_REQUIRED')
                if phase=='planning'and request_hash!=REQUEST_SHA:raise ValueError('EXACT_FROZEN_PLANNING_REQUEST_REQUIRED')
                rows=[r for r in self.value['calls']if r['phase']==phase]
                if not rows:
                    self.admit();reserve=Decimal(attempt['reserved_usd']);current=Decimal(self.value['reserved_usd'])
                    if len(self.value['calls'])>=NEW_CALLS or PRIOR_CALLS+len(self.value['calls'])>=MAX_CALLS:raise ValueError('AGGREGATE_CALL_CAP_EXHAUSTED')
                    if not reserve.is_finite()or reserve<0 or current+reserve>self.maximum_new or PRIOR_HELD+current+reserve>CAP:
                        raise ValueError('AGGREGATE_USD_CAP_EXHAUSTED')
                    row=dict(call_id=stage+':'+phase,phase=phase,stage=stage,ordinal=len(self.value['calls'])+1,
                        aggregate_ordinal=PRIOR_CALLS+len(self.value['calls'])+1,request=request,request_sha256=request_hash)
                    self.value['calls'].append(row);self.value['reserved_usd']=str(current+reserve)
                else:
                    row=rows[0]
                    if row['request_sha256']!=request_hash or row['reserved_usd']!=attempt['reserved_usd']:raise ValueError('RESERVED_REQUEST_CHANGED')
                    if attempt.get('invocation_status')=='NOT_INVOKED'and row.get('invocation_status')!='NOT_INVOKED':raise ValueError('INVOKED_CALL_ID_CANNOT_BE_REARMED')
                row.update(attempt)
                if phase in responses:row['response_content']=responses[phase]
                if phase in diagnostics:
                    data=diagnostics[phase];row['response_diagnostics']=data
                    if data.get('usage_valid')is True:
                        counts=data['usage'];rated=(counts['prompt_tokens']*common.INPUT_RATE+counts['completion_tokens']*common.OUTPUT_RATE)/1000000
                        if rated>Decimal(row['reserved_usd']):raise ValueError('DIAGNOSTIC_USAGE_EXCEEDS_RESERVATION')
                        row.update(usage=counts,actual_usd=str(rated),usage_source='FROZEN_DIAGNOSTIC_PORT_COMPLETE_OUTPUT_BOUND')
                        if row.get('status')!='RETURNED':row['invocation_status']='RESPONSE_RETURNED_REJECTED'
            self.value.update(aggregate_calls=PRIOR_CALLS+len(self.value['calls']),aggregate_reserved_usd=str(PRIOR_HELD+Decimal(self.value['reserved_usd'])))
            self.persist()
    def close(self,status):
        self.value.update(aggregate_remaining_calls=MAX_CALLS-PRIOR_CALLS-len(self.value['calls']),
            aggregate_remaining_usd=str(CAP-PRIOR_HELD-Decimal(self.value['reserved_usd'])))
        super().close(status)


def run(client,package,grant,directory,*,clock=common.utcnow):
    require_grant(package,grant,clock());ledger=Ledger(directory,package,grant,clock)
    try:
        session,question=session_from_snapshot();port=RecordedPort(client,ledger,'contract_smoke',16384)
        allowance=CallAllowance(2,CAP,AUTH,journal=port.journal)
        result=session.answer(question,planner_backend=port,answer_backend=port,allowance=allowance);allowance.closed=True
        ledger.value.update(orchestration=result,selected_capabilities=[o['capability']for o in result.get('plan',{}).get('operations',[])],
            executed_capabilities=[o['capability']for o in result['operations']if o['executed']],
            g05_preparation_executed=any(o['capability']=='G05'and o['executed']for o in result['operations']),
            efficacy_verified=False,model_selection_generalization_verified=False)
        ledger.close('COMPLETED_SELECTION_RECORDED_NO_RETRY'if result['status']=='ANSWERED_WITH_EXPLICIT_LIMITS'else 'FAILED_OR_UNSUPPORTED_NO_RETRY')
    except Exception:ledger.close('FAILED_OR_UNKNOWN_NO_RETRY')
    return ledger.value


def verify_launch(run_id,attempt,runs,event,parent,paths,marker,package,grant,now):
    require_grant(package,grant,now);verify_run_history(run_id,attempt,runs)
    expected=dict(schema='hcl-planner-contract-smoke-marker-v1',authorization_ref=AUTH,package_sha256=digest(package),grant_sha256=digest(grant),executor_commit=parent)
    if event!='push'or not isinstance(parent,str)or len(parent)!=40 or any(c not in '0123456789abcdef'for c in parent)or paths!=[str(MARKER)]or marker!=expected:
        raise ValueError('EXACT_REVIEWED_EXECUTOR_MARKER_ONLY_REQUIRED')
    return True


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--freeze',action='store_true');p.add_argument('--check-launch');p.add_argument('--execute',action='store_true');p.add_argument('--output',default='planner-contract-smoke-private');a=p.parse_args();os.umask(0o077)
    if sum((a.freeze,bool(a.check_launch),a.execute))!=1:raise ValueError('EXACTLY_ONE_MODE_REQUIRED')
    if a.freeze:
        package=build_package();save(PACKAGE,package);save(GRANT,expected_grant(package,status='PREPARED_REVIEW_REQUIRED'))
    else:
        if os.environ.get('GITHUB_REF')!='refs/heads/main'or os.environ.get('GITHUB_RUN_ATTEMPT')!='1':raise ValueError('MAIN_ATTEMPT_ONE_REQUIRED')
        if WORKFLOW.read_bytes()!=TEMPLATE.read_bytes():raise ValueError('FROZEN_WORKFLOW_REQUIRED')
        package=json.loads(PACKAGE.read_text());grant=json.loads(GRANT.read_text());require_grant(package,grant,common.utcnow())
        expected=dict(run_id=os.environ['GITHUB_RUN_ID'],head_sha=os.environ['GITHUB_SHA'],package_sha256=digest(package),grant_sha256=digest(grant))
        admission=Path('/tmp/planner-contract-smoke-admission.json')
        if a.check_launch:
            history=[r for page in json.loads(Path(a.check_launch).read_text())for r in page['workflow_runs']]
            ancestry=subprocess.check_output(['git','rev-list','--parents','-n','1','HEAD'],text=True).split()
            if len(ancestry)!=2:raise ValueError('SINGLE_PARENT_REQUIRED')
            verify_launch(os.environ['GITHUB_RUN_ID'],os.environ['GITHUB_RUN_ATTEMPT'],history,os.environ.get('GITHUB_EVENT_NAME'),ancestry[1],
                subprocess.check_output(['git','diff-tree','--no-commit-id','--name-only','-r','HEAD'],text=True).splitlines(),json.loads(MARKER.read_text()),package,grant,common.utcnow())
            save(admission,expected);print('AGGREGATE_TWO_CALL_SMOKE_ADMISSION_PASS')
        else:
            if json.loads(admission.read_text())!=expected:raise ValueError('EXACT_RUN_ADMISSION_REQUIRED')
            import logging
            logging.disable(logging.CRITICAL);os.environ.pop('OPENAI_LOG',None)
            from openai import OpenAI
            key=os.environ.get('DEEPSEEK_API_KEY')
            if not key:raise ValueError('EXISTING_SERVER_SECRET_UNAVAILABLE')
            run(OpenAI(api_key=key,base_url='https://api.deepseek.com',max_retries=0,timeout=180),package,grant,a.output)
            print('PLANNER_CONTRACT_SMOKE_TERMINATED_NO_RETRY')
