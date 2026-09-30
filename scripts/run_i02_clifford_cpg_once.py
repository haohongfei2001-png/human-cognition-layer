"""One complete-essay strong C/P/G semantic development calibration; no H efficacy."""
import argparse,hashlib,json,os
from pathlib import Path
from scripts.i02_clifford_source import audit,SOURCE,OBLIGATIONS
from scripts.run_i02_acl_ethics_cpg_v8_once import LedgerV8,_request,_input_bound,_reservation
from scripts.run_i02_comparator_calibration_once import Ledger,PEAK,PHASES,digest,transport,write_json
from scripts.serious_eval_full_source_arms_v9 import prepare_primary_arms_v9,prepare_generic_final_v9,MAX_MAP_BYTES
from scripts.serious_eval_arms_v8 import call_spec_v8
from scripts.serious_eval_semantic_score import validate_answer
from scripts.serious_eval_contract import runtime_digest
PACKAGE=Path('reports/HCL_I02_CLIFFORD_CPG_PACKAGE.json')
TEMPLATE=Path('.github/frozen/hcl-i02-clifford-cpg-once.yml')
WORKFLOW=Path('.github/workflows/hcl-i02-clifford-cpg-once.yml')
GRANT=Path('.github/HCL_I02_CLIFFORD_CPG_GRANT.json')
CAP_USD=1.40
OUTPUT_TOKENS=32768

def build_package():
    from scripts.i02_runtime_amendment_v11 import validate_current
    validate_current()
    gate=audit()
    legacy=json.loads(Path('reports/HCL_I02_OBP_METAETHICS_CPG_PACKAGE.json').read_text())
    # Certified existing ledger/scorers/strong native prompts, plus v9 full-source G.
    files=set(legacy['execution_files']) | {str(SOURCE),str(OBLIGATIONS),str(TEMPLATE),
        'reports/HCL_I02_CLIFFORD_QUESTION_PRESELECTION.json',
        'scripts/i02_clifford_source.py','scripts/i02_source_qualification_v13.py',
        'scripts/i02_source_qualification_v12.py','scripts/i02_source_qualification_v11.py',
        'scripts/serious_eval_full_source_arms_v9.py','scripts/run_i02_clifford_cpg_once.py',
        'tests/test_i02_clifford_cpg.py','.github/workflows/hcl-i02-clifford-provider-free.yml'}
    files.update(str(p) for pattern in ('scripts/i02_runtime_amendment*.py','reports/HCL_I02_RUNTIME_AMENDMENT*.json') for p in Path('.').glob(pattern))
    hashes={p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in sorted(files)}
    return dict(schema='hcl-i02-clifford-cpg-package-v1',
        purpose='ONE_COMPLETE_ESSAY_STRONG_CPG_SEMANTIC_DEVELOPMENT_CALIBRATION_NOT_INTERFACE_RETEST',
        authorization='OWNER_DEFAULT_EXISTING_PROVIDER_NORMAL_BOUNDED_COST',historical_budget_transfer=False,
        provider='deepseek',provider_endpoint='https://api.deepseek.com',model='deepseek-v4-pro',
        model_family='DeepSeek-V4-Pro-0813',service_tier='provider_default_no_tier_parameter',
        call_specs={p:dict(call_spec_v8(p),max_tokens=OUTPUT_TOKENS) for p in PHASES},phases=list(PHASES),
        retries=0,maximum_provider_calls=4,maximum_map_bytes=MAX_MAP_BYTES,budget_cap_usd=CAP_USD,
        peak_rates_usd_per_million=PEAK,price_source='https://api-docs.deepseek.com/quick_start/pricing/',price_verified_date='2026-09-30',
        source_file_sha256=gate['source_file_sha256'],obligations_file_sha256=gate['obligations_file_sha256'],
        source_sha256=gate['source_sha256'],question_sha256=gate['question_sha256'],
        source_distribution='COMPLETE_CLIFFORD_ORIGINAL_ESSAY_DEVELOPMENT_EXPOSED',
        question_origin='IMPLEMENTER_AUTHORED_BEFORE_COMPLETE_TARGET_READ_DEVELOPMENT_ONLY',
        comparison_rule='SOURCE_FIRST_ACCEPTABLE_REASONING_MULTIPLE_CRITIQUES_NO_NORMATIVE_AGREEMENT_REQUIRED',
        semantic_review='IMPLEMENTER_DEVELOPMENT_ONLY_INDEPENDENT_REVIEW_UNQUALIFIED',
        confirmation_items_inspected=0,h_arm_calls=0,hnew_arm_calls=0,
        hcl_runtime_sha256=runtime_digest(),execution_files=hashes,execution_sha256=digest(hashes),longmemeval='SEALED_NOT_ACCESSED')

def load_package():
    p=json.loads(PACKAGE.read_text())
    if p!=build_package():raise ValueError('frozen package/runtime/execution drift')
    return p

def preflight(p,raw=None,rdf=None):
    if p!=build_package():raise ValueError('exact frozen comparison required')
    gate=audit(raw,rdf);item=json.loads(SOURCE.read_text())
    arms=prepare_primary_arms_v9(item['ordinary_question'],item['source_id'],item['source_text'])
    quote=json.loads(OBLIGATIONS.read_text())['obligations'][0]['source_quotes'][0]['quote']
    mock=json.dumps(dict(source_index=[dict(id='e1',source_id=item['source_id'],quote=quote)],relations=[],answer_plan=[],open_questions=[]))
    messages={phase:arms[phase] for phase in ('C','P','G_map')};messages['G_final']=prepare_generic_final_v9(arms,mock)
    bounds={}
    for phase in PHASES:
        req=_request(p['call_specs'][phase],messages[phase]);bounds[phase]=dict(input_token_bound=_input_bound(req),reserved_usd=_reservation(req))
    # Reserve full map after nested request JSON escaping, plus derived metadata;
    # raw-map bytes alone undercount escaped quotes/newlines in final transport.
    bounds['G_final']['input_token_bound']+=4*MAX_MAP_BYTES+4096
    bounds['G_final']['reserved_usd']+=(4*MAX_MAP_BYTES+4096)*PEAK['input']/1000000
    worst=sum(x['reserved_usd'] for x in bounds.values())
    if worst>p['budget_cap_usd']:raise ValueError('whole-run peak reservation exceeds hard cap')
    return dict(schema='hcl-i02-clifford-cpg-preflight-v1',status='PASS_SOURCE_FIRST_COMPLETE_CPG_ONLY',package_sha256=digest(p),source_gate=gate,phase_bounds=bounds,all_phase_peak_reservation_usd=worst,provider_calls=0,provider_spend_usd=0,longmemeval='SEALED_NOT_ACCESSED'),arms

class CliffordLedger(LedgerV8):
    def __init__(self,p,output):
        Ledger.__init__(self,p,output);self.receipt['schema']='hcl-i02-clifford-cpg-run-v1'
        self.receipt['source_attribution']='William Kingdon Clifford, The Ethics of Belief, complete essay in Gutenberg50189; public-domain original text, metadata/boundary/hash in frozen source'
        self.save()

def execute(p,provider,output):
    gate,arms=preflight(p);ledger=CliffordLedger(p,output);ledger.receipt['preflight']=gate;ledger.save()
    item=json.loads(SOURCE.read_text());results={}
    try:
        for phase in PHASES:
            messages=arms[phase] if phase!='G_final' else prepare_generic_final_v9(arms,results['G_map'])
            content=ledger.call(phase,messages,provider);results[phase]=content
            try:
                parsed=json.loads(content)
                if phase=='G_map':prepare_generic_final_v9(arms,content)
                else:validate_answer(parsed,{item['source_id']:item['source_text']})
                disposition='SHAPE_AND_SOURCE_CITATIONS_VALID'
            except (ValueError,TypeError,KeyError) as exc:
                disposition='INVALID_'+type(exc).__name__.upper()
                ledger.receipt.setdefault('shape_results',{})[phase]=disposition;ledger.save()
                if phase=='G_map':ledger.receipt['status']='G_MAP_INVALID_G_FINAL_NOT_CALLED';break
            ledger.receipt.setdefault('shape_results',{})[phase]=disposition;ledger.save()
        if ledger.receipt['status']=='STARTED':ledger.receipt['status']='COMPLETED_REQUIRES_SOURCE_FIRST_SEMANTIC_AUDIT'
    except Exception as exc:
        ledger.receipt['status']='FAILED_NO_RETRY';ledger.receipt['failure_type']=type(exc).__name__;raise
    finally:
        ledger.receipt['authorization_remaining_usd']=0;ledger.receipt['budget_state']='CLOSED_NO_TRANSFER_NO_RERUN';ledger.save()
    return ledger.receipt

def require_execution_grant(p):
    grant=json.loads(GRANT.read_text())
    if (grant!=dict(schema='hcl-i02-clifford-once-grant-v1',status='READY',package_sha256=digest(p),remaining_usd=CAP_USD,maximum_calls=4,retries=0,historical_budget_transfer=False) or
        not WORKFLOW.exists() or WORKFLOW.read_bytes()!=TEMPLATE.read_bytes() or
        os.environ.get('GITHUB_RUN_ATTEMPT')!='1' or os.environ.get('HCL_I02_CLIFFORD_AUTHORIZED')!='ONE_DEVELOPMENT_CALIBRATION_ONLY'):
        raise ValueError('unique main first-run grant required; no retry/transfer')

def main():
    parser=argparse.ArgumentParser();m=parser.add_mutually_exclusive_group(required=True)
    for name in ('freeze','preflight','execute'):m.add_argument('--'+name,action='store_true')
    parser.add_argument('--output',default='i02-clifford-cpg-receipt.json');parser.add_argument('--raw');parser.add_argument('--rdf');a=parser.parse_args()
    if a.freeze:write_json(PACKAGE,build_package());return
    p=load_package();raw=Path(a.raw).read_bytes() if a.raw else None;rdf=Path(a.rdf).read_bytes() if a.rdf else None
    gate,_=preflight(p,raw,rdf)
    if a.preflight:write_json(a.output,gate);return
    if not gate['source_gate']['publisher_reconstruction_verified']:raise ValueError('paid transport requires exact publisher reconstruction')
    require_execution_grant(p)
    from openai import OpenAI
    key=os.environ.get('DEEPSEEK_API_KEY')
    if not key:raise ValueError('existing DeepSeek secret required')
    client=OpenAI(api_key=key,base_url=p['provider_endpoint'],max_retries=0,timeout=600)
    execute(p,lambda request:transport(request,client),a.output)
if __name__=='__main__':main()
