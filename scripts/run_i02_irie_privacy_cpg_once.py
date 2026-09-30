"""One native privacy-concept C/P/G development calibration; no H efficacy."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.i02_irie_privacy_preflight import audit, SOURCE, OBLIGATIONS
from scripts.run_i02_acl_ethics_cpg_v8_once import LedgerV8, _request, _input_bound, _reservation
from scripts.run_i02_comparator_calibration_once import Ledger, PEAK, PHASES, digest, transport, write_json
from scripts.serious_eval_arms_v8 import call_spec_v8, prepare_primary_arms_v8, prepare_generic_final_v8
from scripts.serious_eval_generic_workspace_v6 import MAX_MAP_BYTES
from scripts.serious_eval_semantic_score import validate_answer
from scripts.serious_eval_contract import runtime_digest

PACKAGE=Path('reports/HCL_I02_IRIE_PRIVACY_CPG_PACKAGE.json')
WORKFLOW=Path('.github/workflows/hcl-i02-irie-privacy-cpg-once.yml')
CAP_USD=0.24

def build_package():
    gate=audit()
    # Reuse the unchanged certified strong comparator and its transitive files.
    legacy=json.loads(Path('reports/HCL_I02_ACL_ETHICS_CPG_V8_PACKAGE.json').read_text())
    files=set(legacy['execution_files']) | {str(SOURCE),str(OBLIGATIONS),str(WORKFLOW),
        'scripts/i02_irie_privacy_preflight.py','scripts/i02_source_qualification_v7.py',
        'scripts/run_i02_irie_privacy_cpg_once.py'}
    hashes={p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in sorted(files)}
    return dict(schema='hcl-i02-irie-privacy-cpg-package-v1',
        purpose='ONE_NATIVE_PRIVACY_CONCEPT_DEVELOPMENT_CALIBRATION_NO_H_EFFICACY',
        authorization='OWNER_DEFAULT_EXISTING_PROVIDER_NORMAL_BOUNDED_COST',
        historical_budget_transfer=False,provider='deepseek',
        provider_endpoint='https://api.deepseek.com',model='deepseek-v4-pro',
        model_family='DeepSeek-V4-Pro-0813',service_tier='provider_default_no_tier_parameter',
        call_specs={phase:call_spec_v8(phase) for phase in PHASES},phases=list(PHASES),
        retries=0,maximum_provider_calls=4,maximum_map_bytes=MAX_MAP_BYTES,
        budget_cap_usd=CAP_USD,peak_rates_usd_per_million=PEAK,
        price_source='https://api-docs.deepseek.com/quick_start/pricing/',
        price_verified_date='2026-09-30',source_file_sha256=gate['source_file_sha256'],
        obligations_file_sha256=gate['obligations_file_sha256'],
        source_sha256=gate['source_sha256'],question_sha256=gate['question_sha256'],
        question_origin='NATIVE_PUBLISHER_QUESTION_WHITESPACE_ONLY',
        source_distribution='IRIE_34_2024_AUTHOR_FICTIONAL_CASE_DEVELOPMENT_EXPOSED',
        confirmation_items_inspected=0,h_arm_calls=0,hnew_arm_calls=0,
        hcl_runtime_sha256=runtime_digest(),execution_files=hashes,execution_sha256=digest(hashes),
        longmemeval='SEALED_NOT_ACCESSED')

def load_package():
    package=json.loads(PACKAGE.read_text())
    if package!=build_package():
        raise ValueError('frozen package or execution surface drift')
    return package

def preflight(package):
    if package!=build_package():
        raise ValueError('preflight requires exact frozen package')
    gate=audit()
    item=json.loads(SOURCE.read_text())
    arms=prepare_primary_arms_v8(item['ordinary_question'],item['source_id'],item['source_text'])
    quote=json.loads(OBLIGATIONS.read_text())['obligations'][0]['source_quotes'][0]['quote']
    mock=json.dumps(dict(source_index=[dict(id='e1',source_id=item['source_id'],quote=quote)],
        relations=[],answer_plan=[],open_questions=[]))
    messages={phase:arms[phase] for phase in ('C','P','G_map')}
    messages['G_final']=prepare_generic_final_v8(arms,mock)
    bounds={}
    for phase in PHASES:
        request=_request(package['call_specs'][phase],messages[phase])
        bounds[phase]=dict(input_token_bound=_input_bound(request),reserved_usd=_reservation(request))
    bounds['G_final']['input_token_bound']+=2*MAX_MAP_BYTES
    bounds['G_final']['reserved_usd']+=2*MAX_MAP_BYTES*PEAK['input']/1_000_000
    worst=sum(row['reserved_usd'] for row in bounds.values())
    if worst>package['budget_cap_usd']:
        raise ValueError('all-phase peak reservation exceeds hard cap')
    return dict(schema='hcl-i02-irie-privacy-cpg-preflight-v1',status='PASS_SOURCE_FIRST_CPG_ONLY',
        package_sha256=digest(package),source_gate=gate,phase_bounds=bounds,
        all_phase_peak_reservation_usd=worst,provider_calls=0,provider_spend_usd=0,
        longmemeval='SEALED_NOT_ACCESSED'),arms

class PrivacyLedger(LedgerV8):
    def __init__(self,package,output):
        Ledger.__init__(self,package,output)
        self.receipt['schema']='hcl-i02-irie-privacy-cpg-run-v1'
        self.receipt['source_attribution']='Norman Mooradian; IRIE 34 (2024), doi:10.29173/irie536, CC BY 4.0'
        self.save()

def execute(package,provider,output):
    gate,arms=preflight(package)
    ledger=PrivacyLedger(package,output)
    ledger.receipt['preflight']=gate
    ledger.save()
    item=json.loads(SOURCE.read_text())
    results={}
    try:
        for phase in PHASES:
            messages=arms[phase] if phase!='G_final' else prepare_generic_final_v8(arms,results['G_map'])
            content=ledger.call(phase,messages,provider)
            results[phase]=content
            try:
                parsed=json.loads(content)
                if phase=='G_map':
                    if len(content.encode())>MAX_MAP_BYTES:
                        raise ValueError('map byte bound')
                    prepare_generic_final_v8(arms,content)
                else:
                    validate_answer(parsed,{item['source_id']:item['source_text']})
                disposition='SHAPE_AND_SOURCE_CITATIONS_VALID'
            except (ValueError,TypeError,KeyError) as exc:
                disposition='INVALID_'+type(exc).__name__.upper()
                ledger.receipt.setdefault('shape_results',{})[phase]=disposition
                ledger.save()
                if phase=='G_map':
                    ledger.receipt['status']='G_MAP_INVALID_G_FINAL_NOT_CALLED'
                    break
            ledger.receipt.setdefault('shape_results',{})[phase]=disposition
            ledger.save()
        if ledger.receipt['status']=='STARTED':
            ledger.receipt['status']='COMPLETED_REQUIRES_SOURCE_FIRST_SEMANTIC_AUDIT'
    except Exception as exc:
        ledger.receipt['status']='FAILED_NO_RETRY'
        ledger.receipt['failure_type']=type(exc).__name__
        raise
    finally:
        ledger.receipt['authorization_remaining_usd']=0
        ledger.receipt['budget_state']='CLOSED_NO_TRANSFER_NO_RERUN'
        ledger.save()
    return ledger.receipt

def main():
    parser=argparse.ArgumentParser()
    modes=parser.add_mutually_exclusive_group(required=True)
    for name in ('freeze','preflight','execute'):
        modes.add_argument('--'+name,action='store_true')
    parser.add_argument('--output',default='i02-irie-privacy-cpg-receipt.json')
    args=parser.parse_args()
    if args.freeze:
        write_json(PACKAGE,build_package());return
    package=load_package()
    gate,_=preflight(package)
    if args.preflight:
        write_json(args.output,gate);return
    if (os.environ.get('GITHUB_RUN_ATTEMPT')!='1' or
            os.environ.get('HCL_I02_IRIE_PRIVACY_CPG_AUTHORIZED')!='ONE_CALIBRATION_ONLY'):
        raise ValueError('first unique one-shot workflow required')
    from openai import OpenAI
    key=os.environ.get('DEEPSEEK_API_KEY')
    if not key:
        raise ValueError('existing DeepSeek secret required')
    client=OpenAI(api_key=key,base_url=package['provider_endpoint'],max_retries=0,timeout=120)
    execute(package,lambda request:transport(request,client),args.output)

if __name__=='__main__':
    main()
