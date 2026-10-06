"""Only owner-approved synthetic final content and bounded facts may be public."""
from decimal import Decimal
import hashlib,json,math,os
from pathlib import Path
from scripts import run_two_stage_once as r

STATUSES={'NOT_ATTEMPTED','ANSWER_ACCEPTED','FINAL_SCHEMA_OR_CITATIONS_REJECTED','BOUNDED_HCL_SCHEMA_SELECTION_OR_ADAPTER_FAILURE','REQUEST_BOUND_EXCEEDED_NO_TRUNCATION','INCOMPLETE_ANSWER_NO_RETRY','CONTENT_BOUND_EXCEEDED','UNKNOWN_FAILURE_STOP'}
CALL_STATUSES={'RESERVED_BEFORE_CALL','RETURNED','RETURNED_REJECTED','FAILED_OR_UNKNOWN'}
INVOCATIONS={'NOT_INVOKED','RETURNED','RESPONSE_RETURNED_REJECTED','INVOKED_OR_SEND_UNKNOWN'}
DELIVERY={'NOT_REACHED','RETURNED_UNVALIDATED','JSON_INVALID','SCHEMA_INVALID','ANSWER_BLANK','SOURCE_REVIEW_REJECTED','DELIVERED'}
def sha(value,length=64):
    if not isinstance(value,str)or len(value)!=length or any(c not in '0123456789abcdef'for c in value):raise ValueError('EXACT_HASH_REQUIRED')
    return value

def money(value):
    if not isinstance(value,str)or len(value)>40:raise ValueError('BOUNDED_MONEY_REQUIRED')
    number=Decimal(value)
    if not number.is_finite()or not 0<=number<=Decimal('14'):raise ValueError('BOUNDED_MONEY_REQUIRED')
    return str(number)

def duration(value):
    if type(value)not in(int,float)or not math.isfinite(value)or not 0<=value<=3000:raise ValueError('BOUNDED_DURATION_REQUIRED')
    return value


def export(receipt,package,grant,identity,secret):
    if(set(identity)!={'run_id','head_sha'}or not isinstance(identity['run_id'],str)or not identity['run_id'].isascii()or not identity['run_id'].isdecimal()or int(identity['run_id'])<=0):raise ValueError('RUN_ID_REQUIRED')
    sha(identity['head_sha'],40)
    if(package!=r.build_package()or grant!=r.expected_grant(package,True,grant.get('phase1_source_review_sha256'))or receipt.get('schema')!='hcl-two-stage-cny-private-receipt-v1' or receipt.get('stage')!=r.STAGE or receipt.get('currency')!='CNY' or receipt.get('usd_reference_only')is not True or receipt.get('package_sha256')!=r.digest(package)or receipt.get('authorization_ref')!=r.AUTH or secret!=dict(identity,existing_provider_secret='PRESENT')):raise ValueError('EXACT_AUTHORITY_AND_IDENTITY_REQUIRED')
    if receipt.get('status')not in{'COMPLETED_ONE_PASS','STOPPED_NO_RETRY'}or receipt.get('budget_state')!='CLOSED_NO_TRANSFER_NO_RETRY':raise ValueError('TERMINAL_RECEIPT_REQUIRED')
    calls=[]
    for row in receipt['calls']:
        case,arm,phase=row['call_id'].split(':')
        if(case,arm)not in r.ORDER or phase not in('planning','answer')or(arm=='Base'and phase!='answer'):raise ValueError('DECLARED_CALL_REQUIRED')
        if row['status']not in CALL_STATUSES or row['invocation_status']not in INVOCATIONS or type(row['provider_call'])is not bool:raise ValueError('KNOWN_CALL_STATE_REQUIRED')
        if type(row['request_bytes'])is not int or not 0<row['request_bytes']<=36000:raise ValueError('BOUNDED_REQUEST_REQUIRED')
        reserve=r.MAX_PLANNING_CNY if phase=='planning'else r.MAX_ANSWER_CNY
        if Decimal(money(row['reserved_cny']))!=reserve:raise ValueError('EXACT_PHASE_RESERVATION_REQUIRED')
        call=dict(call_id=row['call_id'],case_id=case,arm=arm,phase=phase,request_sha256=sha(row['request_sha256']),request_bytes=row['request_bytes'],reserved_cny=money(row['reserved_cny']),exact_request_reservation_cny=money(row['exact_request_reservation_cny']),status=row['status'],invocation_status=row['invocation_status'],provider_call=row['provider_call'])
        quoted=((2*row['request_bytes']+2048)*r.CNY_INPUT_RATE+((16384 if phase=='planning'else 8192)+32)*r.CNY_OUTPUT_RATE)/1000000
        if Decimal(call['exact_request_reservation_cny'])!=quoted or quoted>reserve:raise ValueError('QUOTE_EXCEEDS_RESERVATION')
        expected_request=package['requests'].get(row['call_id'])
        if expected_request and(row['request_sha256']!=expected_request['request_sha256']or row['request_bytes']!=expected_request['request_bytes']):raise ValueError('STATIC_REQUEST_IDENTITY_REQUIRED')
        if'sdk_seconds'in row:call['sdk_seconds']=duration(row['sdk_seconds'])
        if'failure_code'in row:
            if row['failure_code']not in r.KNOWN_RETURN_FAILURES|{'UNKNOWN_SEND_USAGE_COST_OR_IDENTITY_STOP'}:raise ValueError('SAFE_FAILURE_REQUIRED')
            call['failure_code']=row['failure_code']
        if'usage'in row:
            counts=row['usage'];limit=16384+32 if phase=='planning'else 8192+32
            if(set(counts)!={'prompt_tokens','completion_tokens'}or any(type(v)is not int or v<=0 for v in counts.values())or counts['prompt_tokens']>2*row['request_bytes']+2048 or counts['completion_tokens']>limit):raise ValueError('BOUNDED_USAGE_REQUIRED')
            rated=(counts['prompt_tokens']*r.CNY_INPUT_RATE+counts['completion_tokens']*r.CNY_OUTPUT_RATE)/1000000
            if Decimal(money(row['usage_rated_cny']))!=rated or rated>reserve:raise ValueError('EXACT_USAGE_COST_REQUIRED')
            call.update(usage=dict(counts),usage_rated_cny=str(rated))
        calls.append(call)
    if len(calls)>r.MAX_CALLS or len({c['call_id']for c in calls})!=len(calls):raise ValueError('ONE_BOUNDED_CALL_EACH_REQUIRED')
    reserved=sum(Decimal(c['reserved_cny'])for c in calls)
    if Decimal(money(receipt['reserved_cny']))!=reserved or reserved>r.MAX_SCHEDULE_CNY or reserved>r.CAP_CNY:raise ValueError('EXACT_AGGREGATE_LEDGER_REQUIRED')
    if[(a['case_id'],a['arm'])for a in receipt['arms']]!=r.ORDER:raise ValueError('ALL_DECLARED_ARMS_REQUIRED')
    arms=[]
    for row in receipt['arms']:
        if row['status']not in STATUSES or type(row['citations_accepted'])is not bool:raise ValueError('KNOWN_ARM_STATUS_REQUIRED')
        final=row.get('final_text')
        if final is not None and(not isinstance(final,str)or len(final)>64000):raise ValueError('BOUNDED_FINAL_TEXT_REQUIRED')
        digest=sha(row['final_answer_sha256'])if row['final_answer_sha256']is not None else None
        if (hashlib.sha256(final.encode()).hexdigest()if final is not None else None)!=digest:raise ValueError('UNCHANGED_FINAL_TEXT_HASH_REQUIRED')
        fields=r.final_fields(final)
        if row['final_fields']!=fields:raise ValueError('UNCHANGED_FINAL_FIELDS_REQUIRED')
        out=dict(case_id=row['case_id'],arm=row['arm'],status=row['status'],final_text=final,final_fields=fields,final_answer_sha256=digest,citations_accepted=row['citations_accepted'])
        for key in('selected_capabilities','executed_capabilities','checked_treatment'):
            values=row[key]
            if not isinstance(values,list)or len(values)>3 or any(v not in r.CATALOG for v in values):raise ValueError('BOUNDED_CAPABILITY_IDS_REQUIRED')
            out[key]=list(values)
        if'native_results'in row:
            if type(row['native_results'])is not int or not 0<=row['native_results']<=3:raise ValueError('BOUNDED_NATIVE_COUNT_REQUIRED')
            out['native_results']=row['native_results']
        if'final_delivery_code'in row:
            if row['final_delivery_code']not in DELIVERY:raise ValueError('SAFE_DELIVERY_CODE_REQUIRED')
            out['final_delivery_code']=row['final_delivery_code']
        for key in('arm_seconds','sdk_seconds','non_sdk_seconds'):
            if key in row:out[key]=duration(row[key])
        arms.append(out)
    complete=all('usage_rated_cny'in c for c in calls if c['provider_call'])
    cases,_=r.load_frozen()
    return dict(schema='hcl-two-stage-cny-public-evidence-v1',currency='CNY',stage=r.STAGE,**identity,authorization_ref=r.AUTH,package_sha256=r.digest(package),runtime_sha256=r.RUNTIME,model=r.MODEL,planning_tokens=16384,answer_tokens=8192,production_planning_tokens=4096,cases=cases['cases'],status=receipt['status'],arms=arms,calls=calls,provider_calls=sum(c['provider_call']for c in calls),reserved_cny=str(reserved),usage_complete=complete,usage_rated_cny=str(sum(Decimal(c.get('usage_rated_cny','0'))for c in calls))if complete else None,invoice_cost_cny=None,cost_basis='NATIVE_CNY_PEAK_USAGE_ESTIMATE_NOT_INVOICE_FULL_RESERVATION_RETAINED',elapsed_seconds=duration(receipt['elapsed_seconds']),budget_state='CLOSED_NO_TRANSFER_NO_RETRY',remaining_authorized_calls=0,remaining_authorized_cny='0',stage1_semantic_gate='PENDING_INDEPENDENT_SOURCE_REVIEW'if r.STAGE==1 else'PREVIOUS_FIXED_PASS',efficacy_verified=False,i02_certified=False,limitations='ONE_FUNCTIONAL_CASE_THEN_FOUR_AUTHORED_CASES_NOT_COMPUTE_MATCHED_NO_GENERALIZATION')


def validate_phase1_gate(evidence,review):
    package=json.loads(Path('reports/HCL_TWO_STAGE_CNY_1_PACKAGE.json').read_text())
    case=next(c for c in json.loads((r.ROOT/'cases.json').read_text())if c['id']=='SMOKE1')
    if(evidence.get('schema')!='hcl-two-stage-cny-public-evidence-v1'or evidence.get('currency')!='CNY'or evidence.get('stage')!=1 or evidence.get('authorization_ref')!=r.AUTH or evidence.get('package_sha256')!=r.digest(package)or evidence.get('runtime_sha256')!=r.RUNTIME or evidence.get('model')!=r.MODEL or evidence.get('planning_tokens')!=16384 or evidence.get('answer_tokens')!=8192 or evidence.get('status')!='COMPLETED_ONE_PASS'or evidence.get('provider_calls')!=2 or evidence.get('usage_complete')is not True or evidence.get('budget_state')!='CLOSED_NO_TRANSFER_NO_RETRY'or evidence.get('remaining_authorized_calls')!=0 or evidence.get('remaining_authorized_cny')!='0'):raise ValueError('PHASE1_COMPLETE_KNOWN_CLOSED_REQUIRED')
    if evidence.get('cases')!=[dict(case_id='SMOKE1',question=case['question'],sources=[dict(source_id=case['source_id'],version=1,text=case['source'],recorded_at=r.FIXTURE_RECORDED_AT)])]:raise ValueError('PHASE1_SOURCE_IDENTITY_REQUIRED')
    sha(evidence.get('head_sha'),40)
    if not isinstance(evidence.get('run_id'),str)or not evidence['run_id'].isascii()or not evidence['run_id'].isdecimal()or int(evidence['run_id'])<=0:raise ValueError('PHASE1_RUN_IDENTITY_REQUIRED')
    calls=evidence.get('calls');arms=evidence.get('arms')
    if not isinstance(calls,list)or len(calls)!=2 or [c.get('call_id')for c in calls]!=['SMOKE1:HCL:planning','SMOKE1:HCL:answer']or any(c.get('status')!='RETURNED'or c.get('invocation_status')!='RETURNED'or c.get('provider_call')is not True for c in calls):raise ValueError('PHASE1_TWO_RETURNED_CALLS_REQUIRED')
    if not isinstance(arms,list)or len(arms)!=1:raise ValueError('PHASE1_EXACT_ARM_REQUIRED')
    arm=arms[0]
    if(arm.get('case_id')!='SMOKE1'or arm.get('arm')!='HCL'or arm.get('status')!='ANSWER_ACCEPTED'or arm.get('citations_accepted')is not True or type(arm.get('native_results'))is not int or not 1<=arm['native_results']<=3 or arm.get('final_delivery_code')!='DELIVERED'):raise ValueError('PHASE1_NATIVE_AND_DELIVERY_REQUIRED')
    raw=arm.get('final_text')
    prompt=[dict(role='user',content=json.dumps(dict(sources=evidence['cases'][0]['sources'])))]
    if not r.accepted(prompt,raw)or arm.get('final_fields')!=r.final_fields(raw)or arm.get('final_answer_sha256')!=hashlib.sha256(raw.encode()).hexdigest():raise ValueError('PHASE1_ORIGINAL_SOURCE_AUDIT_REQUIRED')
    reserves=[r.MAX_PLANNING_CNY,r.MAX_ANSWER_CNY];rated=Decimal('0')
    for index,(c,reserve) in enumerate(zip(calls,reserves,strict=True)):
        phase='planning' if index==0 else 'answer'
        if c.get('case_id')!='SMOKE1'or c.get('arm')!='HCL'or c.get('phase')!=phase:raise ValueError('PHASE1_PHASE_IDENTITY_REQUIRED')
        sha(c.get('request_sha256'))
        if phase=='planning':
            expected_request=package['requests']['SMOKE1:HCL:planning']
            if c['request_sha256']!=expected_request['request_sha256']or c['request_bytes']!=expected_request['request_bytes']:raise ValueError('PHASE1_REQUEST_IDENTITY_REQUIRED')
        u=c.get('usage',{})
        if(set(u)!={'prompt_tokens','completion_tokens'}or any(type(v)is not int or v<=0 for v in u.values())or type(c.get('request_bytes'))is not int or not 0<c['request_bytes']<=36000 or u['prompt_tokens']>2*c['request_bytes']+2048 or u['completion_tokens']>(16384 if c['phase']=='planning'else 8192)+32):raise ValueError('PHASE1_VALID_USAGE_REQUIRED')
        quote=((2*c['request_bytes']+2048)*r.CNY_INPUT_RATE+((16384 if phase=='planning'else 8192)+32)*r.CNY_OUTPUT_RATE)/1000000
        if Decimal(money(c['exact_request_reservation_cny']))!=quote or quote>reserve:raise ValueError('PHASE1_QUOTE_REQUIRED')
        cost=(u['prompt_tokens']*r.CNY_INPUT_RATE+u['completion_tokens']*r.CNY_OUTPUT_RATE)/1000000
        if Decimal(money(c['reserved_cny']))!=reserve or Decimal(money(c['usage_rated_cny']))!=cost or cost>reserve:raise ValueError('PHASE1_COST_REQUIRED')
        rated+=cost
    if Decimal(money(evidence['reserved_cny']))!=sum(reserves)or Decimal(money(evidence['usage_rated_cny']))!=rated:raise ValueError('PHASE1_LEDGER_REQUIRED')
    expected_keys={'schema','authorization_ref','evidence_sha256','source_sha256','final_answer_sha256','reviewer_role','criteria','overall_pass'}
    if(set(review)!=expected_keys or review['schema']!='hcl-two-stage-cny-phase1-source-review-v1'or review['authorization_ref']!=r.AUTH or review['evidence_sha256']!=r.digest(evidence)or review['source_sha256']!=case['source_sha256']or review['final_answer_sha256']!=arm['final_answer_sha256']or review['reviewer_role']!='INDEPENDENT_SOURCE_FIRST_AFTER_OUTPUT'or review['overall_pass']is not True):raise ValueError('EXACT_INDEPENDENT_PHASE1_REVIEW_REQUIRED')
    checks=review['criteria']
    if not isinstance(checks,list)or any(not isinstance(c,dict)or type(c.get('id'))is not int for c in checks)or [c.get('id')for c in checks]!=[1,2,3,4]:raise ValueError('ALL_FOUR_PHASE1_CRITERIA_REQUIRED')
    for check in checks:
        if set(check)!={'id','passed','reason'}or check['passed']is not True or not isinstance(check['reason'],str)or not 1<=len(check['reason'])<=1500 or not check['reason'].strip():raise ValueError('ALL_FOUR_PHASE1_CRITERIA_REQUIRED')
    return True

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--stage',type=int,required=True);p.add_argument('--receipt',required=True);p.add_argument('--output',required=True);a=p.parse_args();r.configure(a.stage)
    raw=Path(a.receipt).read_bytes()
    if len(raw)>16*1024*1024:raise ValueError('BOUNDED_RECEIPT_REQUIRED')
    identity=dict(run_id=os.environ['GITHUB_RUN_ID'],head_sha=os.environ['GITHUB_SHA'])
    value=export(json.loads(raw),json.loads(r.PACKAGE.read_text()),json.loads(r.GRANT.read_text()),identity,json.loads(r.SECRET_CHECK.read_text()))
    r.save(a.output,value)
    print('BEGIN_TWO_STAGE_PUBLIC_JSON')
    print(json.dumps(value,ensure_ascii=False,sort_keys=True))
    print('END_TWO_STAGE_PUBLIC_JSON')
