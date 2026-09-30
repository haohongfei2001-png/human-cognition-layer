"""One protected automated task audit, no arm comparison and no retry."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
import subprocess
from pathlib import Path
from scripts import i02_gilman_protected_candidate as holder
from scripts.i02_source_holder_review import messages, validate_review

PACKAGE = Path('reports/HCL_I02_GILMAN_HOLDER_PACKAGE.json')
WORKFLOW = '.github/workflows/hcl-i02-gilman-holder-once.yml'
RATES = dict(input=1.32, cache_hit=0.044, output=3.96)
CAP = 0.18


def sha(raw): return hashlib.sha256(raw).hexdigest()
def digest(value): return sha(json.dumps(value, sort_keys=True, ensure_ascii=False).encode())
def write(path, value):
    p = Path(path); tmp = p.with_suffix(p.suffix + '.tmp')
    tmp.write_text(json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False) + '\n'); tmp.replace(p)


def build_package():
    files = ['scripts/i02_gilman_protected_candidate.py', 'scripts/i02_exposure_history.py',
             'scripts/i02_exposure_snapshot.py', 'scripts/i02_source_holder_review.py',
             'scripts/run_i02_gilman_holder_once.py', 'reports/HCL_I02_GILMAN_PROTECTED_CANDIDATE.json',
             'tests/test_i02_gilman_holder_once.py', WORKFLOW]
    return dict(schema='hcl-i02-gilman-protected-holder-package-v1',
        purpose='ONE_AUTOMATED_SOURCE_FIRST_TASK_FIT_AUDIT_NO_H_OR_ARM_OUTPUTS',
        authorization='OWNER_DEFAULT_EXISTING_PROVIDER_NORMAL_BOUNDED_COST',
        historical_budget_transfer=False, maximum_provider_calls=1, retries=0, budget_cap_usd=CAP,
        model='deepseek-v4-pro', model_version_publisher='DeepSeek-V4-Pro-0813',
        endpoint='https://api.deepseek.com', service_tier='provider_default_no_tier_parameter',
        thinking=dict(type='enabled'), reasoning_effort='high', max_tokens=8192,
        rates_peak_usd_per_million=RATES, price_verified_date='2026-09-30',
        price_source='https://api-docs.deepseek.com/quick_start/pricing/',
        source_sha256=holder.BODY_SHA256, question_sha256=holder.QUESTION_SHA256,
        permission_scope='SOURCE_HOLDER_AUDIT_ONLY_NOT_ARM_EXECUTION_OR_CONFIRMATION',
        raw_visibility='HELD_AWAY_FROM_IMPLEMENTER_BY_ROLE_NOT_CRYPTOGRAPHIC_SEAL',
        independent_human_review=False, independent_model_family_judge=False,
        confirmation_qualified=False, h_calls=0, cpg_calls=0,
        execution_files={p: sha(Path(p).read_bytes()) for p in files}, longmemeval='SEALED_NOT_ACCESSED')


def load_package():
    p = json.loads(PACKAGE.read_text())
    if p != build_package(): raise ValueError('protected audit freeze drift')
    return p


def current_head():
    return subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()


def prepare(package, source, source_gate):
    if package != build_package() or sha(source.encode()) != package['source_sha256']:
        raise ValueError('frozen audit or complete source mismatch')
    if (source_gate.get('status') != 'READY_FOR_SOURCE_FIRST_HOLDER_REVIEW' or
            source_gate.get('source_sha256') != package['source_sha256'] or
            source_gate.get('history',{}).get('checkout_head') != current_head() or
            source_gate.get('snapshot',{}).get('repository_commit') != current_head() or
            source_gate.get('history',{}).get('status') != 'REACHABLE_HISTORY_NO_TEXT_MATCH' or
            source_gate.get('snapshot',{}).get('status') != 'TEXT_SNAPSHOT_NO_MATCH'):
        raise ValueError('current source history gate not clear')
    request = dict(model=package['model'], messages=messages(holder.load_package()['source_id'], source),
                   thinking=package['thinking'], reasoning_effort=package['reasoning_effort'],
                   max_tokens=package['max_tokens'], response_format=dict(type='json_object'))
    bound = 2 * len(json.dumps(request, ensure_ascii=False).encode()) + 2048
    reserve = (bound * RATES['input'] + package['max_tokens'] * RATES['output']) / 1_000_000
    if reserve > package['budget_cap_usd']: raise ValueError('hard cap refuses transport')
    gate = dict(schema='hcl-i02-protected-holder-preflight-v1', package_sha256=digest(package),
        source_gate=source_gate, request_sha256=digest(request), input_token_bound=bound,
        peak_reservation_usd=reserve, provider_calls=0, provider_spend_usd=0,
        source_or_quote_text_displayed=False, longmemeval='SEALED_NOT_ACCESSED')
    return request, gate


def execute(package, source, source_gate, provider, raw_path, metadata_path):
    if Path(raw_path).exists() or Path(metadata_path).exists(): raise ValueError('existing receipt refuses rerun')
    request, gate = prepare(package, source, source_gate)
    raw = dict(schema='hcl-i02-protected-source-holder-raw-v1', status='STARTED',
        run_id=os.environ.get('GITHUB_RUN_ID'), sha=os.environ.get('GITHUB_SHA'),
        preflight=gate, request_raw=request, provider_calls=1, retries=0,
        conservative_reserved_usd=gate['peak_reservation_usd'], hard_cap_usd=CAP,
        authorization_remaining_usd=0, budget_state='CLOSED_NO_TRANSFER_NO_RERUN',
        h_calls=0, cpg_calls=0, actual_invoice_cost_usd=None,
        estimated_actual_cost_usd=None, rated_peak_cost_usd=None, longmemeval='SEALED_NOT_ACCESSED')
    write(raw_path, raw)
    result = None
    try:
        response = provider(request); raw['response_raw'] = response; write(raw_path, raw)
        choice = (response.get('choices') or [{}])[0]; usage = response.get('usage') or {}
        inp, out = usage.get('prompt_tokens'), usage.get('completion_tokens')
        raw.update(actual_model_id=response.get('model'), usage=usage)
        if (type(inp) is not int or type(out) is not int or not 0 <= inp <= gate['input_token_bound'] or
                not 0 <= out <= package['max_tokens'] or response.get('model') != package['model']):
            raise ValueError('model/usage contract failed')
        raw['rated_peak_cost_usd'] = (inp*RATES['input']+out*RATES['output'])/1_000_000
        hit, miss, created = usage.get('prompt_cache_hit_tokens'), usage.get('prompt_cache_miss_tokens'), response.get('created')
        if type(hit) is int and type(miss) is int and min(hit,miss)>=0 and hit+miss==inp and type(created) is int:
            t=datetime.fromtimestamp(created,timezone.utc)
            peak=t.weekday()<5 and (1<=t.hour<4 or 6<=t.hour<10)
            raw['estimated_actual_cost_usd']=(hit*RATES['cache_hit']+miss*RATES['input']+out*RATES['output'])/1_000_000*(1 if peak else .5)
            raw['estimate_limit']='PUBLISHED_CLOCK_RATES; HOLIDAY_ADJUSTMENT_AND_INVOICE_NOT_VERIFIED'
        if choice.get('finish_reason') != 'stop': raise ValueError('incomplete source audit; no retry')
        result = validate_review(json.loads(choice['message']['content']), source)
        raw['status']='COMPLETED_PRELIMINARY_ONLY'
    except Exception as exc:
        raw.update(status='FAILED_NO_RETRY', failure_type=type(exc).__name__)
        if getattr(exc,'body',None) is not None:
            raw['provider_error_response_raw']=getattr(exc,'body')
            raw['provider_error_status_code']=getattr(exc,'status_code',None)
    finally:
        write(raw_path,raw)
        # Only an explicit whitelist crosses the implementer boundary.
        meta={k:raw.get(k) for k in ('schema','status','run_id','sha','provider_calls','retries',
            'conservative_reserved_usd','hard_cap_usd','authorization_remaining_usd','budget_state',
            'h_calls','cpg_calls','actual_invoice_cost_usd','actual_model_id','usage',
            'estimated_actual_cost_usd','rated_peak_cost_usd','estimate_limit','failure_type','longmemeval')}
        meta['usage']={k:v for k,v in (raw.get('usage') or {}).items() if
            k in {'prompt_tokens','completion_tokens','total_tokens','prompt_cache_hit_tokens','prompt_cache_miss_tokens'} and type(v) is int}
        if meta.get('actual_model_id') != package['model']:
            meta['actual_model_id']='UNVERIFIED_RESPONSE_MODEL_FIELD'
        meta.update(schema='hcl-i02-source-holder-metadata-v1', preflight=gate,
            raw_receipt_sha256=sha(Path(raw_path).read_bytes()), preliminary_review=result,
            raw_source_or_quote_text_displayed=False, confirmation_qualified=False,
            independent_human_review=False, independent_model_family_judge=False)
        write(metadata_path,meta)
    return meta


def main():
    parser=argparse.ArgumentParser();m=parser.add_mutually_exclusive_group(required=True)
    for mode in ('freeze','preflight','execute'):m.add_argument('--'+mode,action='store_true')
    parser.add_argument('--raw',default='gilman-holder-protected-raw.json')
    parser.add_argument('--metadata',default='gilman-holder-metadata.json');args=parser.parse_args()
    if args.freeze:write(PACKAGE,build_package());return
    if args.execute and Path('.github/HCL_I02_GILMAN_HOLDER_CLOSED').exists():
        raise ValueError('closed source-audit authorization refuses execution')
    package=load_package();raw=holder.download(holder.RAW_URL);rdf=holder.download(holder.RDF_URL)
    source=holder.original_body(raw);source_gate=holder.screen('.',raw,rdf)
    _,gate=prepare(package,source,source_gate)
    if args.preflight:write(args.metadata,gate);print('PROTECTED_PREFLIGHT_NO_TEXT_DISPLAY');return
    if os.environ.get('GITHUB_RUN_ATTEMPT')!='1' or os.environ.get('HCL_I02_GILMAN_HOLDER_AUTHORIZED')!='ONE_SOURCE_AUDIT_ONLY':
        raise ValueError('unique first-attempt source-audit workflow required')
    from openai import OpenAI
    key=os.environ.get('DEEPSEEK_API_KEY')
    if not key:raise ValueError('existing DeepSeek secret required')
    client=OpenAI(api_key=key,base_url=package['endpoint'],max_retries=0,timeout=120)
    def transport(request):
        return client.chat.completions.create(**{k:v for k,v in request.items() if k!='thinking'},
            extra_body={'thinking':request['thinking']}).model_dump(mode='json')
    meta=execute(package,source,source_gate,transport,args.raw,args.metadata)
    print('PROTECTED_SOURCE_AUDIT_FINISHED_METADATA_ONLY')
    if meta['status']=='FAILED_NO_RETRY':raise SystemExit(1)

if __name__=='__main__':main()
