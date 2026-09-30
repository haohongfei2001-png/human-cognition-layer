"""One new long authored v3-interface calibration; no consumed source or H comparison."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
from scripts.i02_source_holder_v3_calibration_fixture import load_fixture,PATH as FIXTURE,fixture_anchor_witness
from scripts.i02_source_holder_line_index_v3 import messages,index_source,resolve_review

PACKAGE=Path('reports/HCL_I02_SOURCE_HOLDER_V3_CALIBRATION_PACKAGE.json')
WORKFLOW='.github/workflows/hcl-i02-source-holder-v3-calibration-once.yml'
CLOSED=Path('.github/HCL_I02_SOURCE_HOLDER_V3_CALIBRATION_CLOSED')
CAP=0.38
RATES=dict(input=1.32,cache_hit=.044,output=3.96)

def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
def write(path,value):
    p=Path(path);tmp=p.with_suffix(p.suffix+'.tmp');tmp.write_text(json.dumps(value,sort_keys=True,indent=2,ensure_ascii=False)+'\n');tmp.replace(p)

def build_package():
    f=load_fixture()
    files=['scripts/i02_source_holder_line_index_v3.py','scripts/i02_source_holder_v3_calibration_fixture.py',
        'scripts/run_i02_source_holder_v3_calibration_once.py',str(FIXTURE),'tests/test_i02_source_holder_v3_calibration.py',WORKFLOW]
    return dict(schema='hcl-i02-v3-long-authored-interface-package-v1',
        purpose='ONE_NATIVE_LONG_INPUT_LINE_REFERENCE_INTEROPERABILITY_CALIBRATION_NOT_INDEPENDENT_SOURCE',
        authorization='OWNER_DEFAULT_EXISTING_PROVIDER_NORMAL_BOUNDED_COST',
        source_origin=f['source_origin'],source_sha256=f['source_sha256'],question_sha256=f['question_sha256'],
        fixture_file_sha256=hashlib.sha256(FIXTURE.read_bytes()).hexdigest(),
        provider='deepseek',endpoint='https://api.deepseek.com',model='deepseek-v4-pro',
        publisher_model_version='DeepSeek-V4-Pro-0813',service_tier='provider_default_no_tier_parameter',
        thinking=dict(type='enabled'),reasoning_effort='high',max_tokens=16384,timeout_seconds=300,
        maximum_provider_calls=1,retries=0,budget_cap_usd=CAP,rates_peak_usd_per_million=RATES,
        price_source='https://api-docs.deepseek.com/quick_start/pricing/',price_verified_date='2026-09-30',
        historical_budget_transfer=False,consumed_case_reopened=False,h_calls=0,cpg_calls=0,
        fixture_gold_in_provider_input=False,confirmation_qualified=False,semantic_truth_verified=False,
        execution_files={p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in files},longmemeval='SEALED_NOT_ACCESSED')

def load_package():
    p=json.loads(PACKAGE.read_text())
    if p!=build_package():raise ValueError('frozen interface/fixture/request/budget drift')
    return p

def preflight(package):
    if package!=build_package():raise ValueError('exact new freeze required')
    f=load_fixture();source=f['source_text'];prepared=messages(f['ordinary_question'],f['source_id'],source)
    payload=json.loads(prepared[-1]['content']);lines=payload['sources'][0]['lines']
    if ''.join(x['text'] for x in lines)!=source or set(payload)!={'question','question_sha256','sources'}:
        raise ValueError('complete ordinary source/question preservation required')
    if len(source)<80958:raise ValueError('do not substitute a small-source capacity witness')
    request=dict(model=package['model'],messages=prepared,thinking=package['thinking'],
        reasoning_effort=package['reasoning_effort'],max_tokens=package['max_tokens'],response_format=dict(type='json_object'))
    bound=2*len(json.dumps(request,ensure_ascii=False).encode())+2048
    reserve=(bound*RATES['input']+package['max_tokens']*RATES['output'])/1_000_000
    if reserve>package['budget_cap_usd']:raise ValueError('whole-request peak reservation exceeds new cap')
    return request,dict(schema='hcl-i02-v3-long-interface-preflight-v1',package_sha256=digest(package),
        source_sha256=f['source_sha256'],question_sha256=f['question_sha256'],source_characters=len(source),
        source_lines=len(lines),complete_source_reconstruction_exact=True,request_sha256=digest(request),
        input_token_bound=bound,peak_reservation_usd=reserve,fixture_gold_in_provider_input=False,
        source_origin=f['source_origin'],independent_source=False,confirmation_qualified=False,
        story_time_actor_semantics_qualified=False,provider_calls=0,provider_spend_usd=0,longmemeval='SEALED_NOT_ACCESSED')

def execute(package,provider,output):
    if Path(output).exists():raise ValueError('existing receipt refuses rerun')
    request,gate=preflight(package)
    receipt=dict(schema='hcl-i02-v3-long-interface-run-v1',status='STARTED',run_id=os.environ.get('GITHUB_RUN_ID'),
        run_attempt=os.environ.get('GITHUB_RUN_ATTEMPT'),sha=os.environ.get('GITHUB_SHA'),preflight=gate,
        request_raw=request,provider_calls=1,retries=0,phase='SOURCE_HOLDER_V3_INTERFACE',h_calls=0,cpg_calls=0,
        conservative_reserved_usd=gate['peak_reservation_usd'],hard_cap_usd=package['budget_cap_usd'],
        actual_invoice_cost_usd=None,rated_peak_cost_usd=None,estimated_actual_cost_usd=None,
        authorization_remaining_usd=0,budget_state='CLOSED_NO_TRANSFER_NO_RERUN',
        confirmation_qualified=False,source_origin=package['source_origin'],longmemeval='SEALED_NOT_ACCESSED')
    write(output,receipt)
    try:
        raw=provider(request);receipt['response_raw']=raw;write(output,receipt)
        choice=(raw.get('choices') or [{}])[0];usage=raw.get('usage') or {};inp=usage.get('prompt_tokens');out=usage.get('completion_tokens')
        receipt.update(actual_model_id=raw.get('model'),usage=usage,finish_reason=choice.get('finish_reason'))
        if (raw.get('model')!=package['model'] or type(inp) is not int or type(out) is not int or
                not 0<=inp<=gate['input_token_bound'] or not 0<=out<=package['max_tokens']):
            raise ValueError('actual model/usage contract failed')
        receipt['rated_peak_cost_usd']=(inp*RATES['input']+out*RATES['output'])/1_000_000
        hit,miss,created=usage.get('prompt_cache_hit_tokens'),usage.get('prompt_cache_miss_tokens'),raw.get('created')
        if type(hit) is int and type(miss) is int and min(hit,miss)>=0 and hit+miss==inp and type(created) is int:
            t=datetime.fromtimestamp(created,timezone.utc);peak=t.weekday()<5 and (1<=t.hour<4 or 6<=t.hour<10)
            receipt['estimated_actual_cost_usd']=(hit*RATES['cache_hit']+miss*RATES['input']+out*RATES['output'])/1_000_000*(1 if peak else .5)
            receipt['estimate_limit']='USAGE_CLOCK_ESTIMATE_HOLIDAY_AND_INVOICE_UNVERIFIED'
        if choice.get('finish_reason')!='stop':raise ValueError('incomplete native output; no retry')
        f=load_fixture();parsed=json.loads(choice['message']['content'])
        resolved=resolve_review(parsed,f['ordinary_question'],f['source_id'],f['source_text'],index_source(f['source_id'],f['source_text']))
        receipt['resolved_review']=resolved;receipt['literal_fixture_witness']=fixture_anchor_witness(resolved,f)
        receipt['status']='COMPLETED_LONG_INTERFACE_ONLY' if receipt['literal_fixture_witness']['all_declared_literal_episode_anchors_present'] else 'COMPLETED_INTERFACE_WITHOUT_DECLARED_EPISODES'
    except Exception as exc:
        receipt.update(status='FAILED_NO_RETRY',failure_type=type(exc).__name__)
        if getattr(exc,'body',None) is not None:receipt['provider_error_response_raw']=exc.body
    finally:write(output,receipt)
    return receipt

def main():
    p=argparse.ArgumentParser();m=p.add_mutually_exclusive_group(required=True)
    for mode in ('freeze','preflight','execute'):m.add_argument('--'+mode,action='store_true')
    p.add_argument('--output',default='i02-v3-interface-calibration-receipt.json');args=p.parse_args()
    if args.freeze:write(PACKAGE,build_package());return
    package=load_package()
    if args.preflight:write(args.output,preflight(package)[1]);return
    if CLOSED.exists() or os.environ.get('GITHUB_RUN_ATTEMPT')!='1' or os.environ.get('HCL_I02_V3_INTERFACE_AUTHORIZED')!='ONE_NEW_INTERFACE_CALIBRATION_ONLY':
        raise ValueError('unique first authorized dispatch required; closed grants never reopen')
    from openai import OpenAI
    key=os.environ.get('DEEPSEEK_API_KEY')
    if not key:raise ValueError('existing DeepSeek secret required')
    client=OpenAI(api_key=key,base_url=package['endpoint'],max_retries=0,timeout=package['timeout_seconds'])
    def transport(request):
        return client.chat.completions.create(**{k:v for k,v in request.items() if k!='thinking'},extra_body={'thinking':request['thinking']}).model_dump(mode='json')
    result=execute(package,transport,args.output)
    print(result['status'])
    if result['status']=='FAILED_NO_RETRY':raise SystemExit(1)
if __name__=='__main__':main()
