"""Audit immutable one-run receipt/strict quotation closure; no transport or rescoring."""
import hashlib,json,zipfile
from pathlib import Path
from scripts.run_i02_clifford_cpg_once import load_package,digest,GRANT,WORKFLOW,TEMPLATE
from scripts.i02_clifford_source import SOURCE,OBLIGATIONS
from scripts.serious_eval_semantic_score import validate_answer
from scripts.serious_eval_full_source_arms_v9 import prepare_primary_arms_v9,prepare_generic_final_v9
BASE=Path('reports/HCL_I02_CLIFFORD_CPG')
def audit():
    p=load_package();r=json.loads(Path(str(BASE)+'_RAW_RECEIPT.json').read_text());c=json.loads(Path(str(BASE)+'_CLOSURE.json').read_text())
    raw=Path(str(BASE)+'_RAW_ARTIFACT.zip').read_bytes()
    if hashlib.sha256(raw).hexdigest()!=c['artifact_sha256'] or len(raw)!=185931:raise ValueError('raw ZIP digest/size drift')
    with zipfile.ZipFile(Path(str(BASE)+'_RAW_ARTIFACT.zip')) as z:
        for src,dst in [('i02-clifford-cpg-receipt.json',str(BASE)+'_RAW_RECEIPT.json'),('i02-clifford-cpg-preflight.json',str(BASE)+'_RUN_PREFLIGHT.json'),('reports/HCL_I02_CLIFFORD_CPG_PACKAGE.json','reports/HCL_I02_CLIFFORD_CPG_PACKAGE.json'),('reports/HCL_I02_CLIFFORD_SOURCE_FIRST_OBLIGATIONS.json',str(OBLIGATIONS))]:
            if z.read(src)!=Path(dst).read_bytes():raise ValueError('canonical artifact extraction not exact')
    if (r['run_id']!='36741974004' or r['sha']!='a8c2c3d08e0addbcf24dcfd247805c025c8cacab' or r['run_attempt']!='1' or r['package_sha256']!=digest(p) or r['provider_calls']!=3 or r['retries']!=0 or r['authorization_remaining_usd']!=0 or r['h_arm_calls']!=0 or r['status']!='G_MAP_INVALID_G_FINAL_NOT_CALLED'):raise ValueError('run/consumed grant boundary drift')
    g=json.loads(GRANT.read_text())
    if g['status']!='CLOSED' or g['remaining_usd']!=0 or g['maximum_calls']!=0 or WORKFLOW.exists() or not TEMPLATE.exists():raise ValueError('budget or live trigger reopened')
    if (c['disposition']!='INCONCLUSIVE' or c['formal_semantic_scores'] is not None or c['source_semantics_qualified'] or c['outputs_rescored'] or c['old_source_rerun_allowed'] or not c['historical_dispositions_unchanged'] or c['longmemeval']!='SEALED_NOT_ACCESSED'):raise ValueError('unsupported evidence upgrade')
    item=json.loads(SOURCE.read_text());s=item['source_text'];arms=prepare_primary_arms_v9(item['ordinary_question'],item['source_id'],s);badcounts={};usage=[]
    for a in r['attempts']:
        request=a['request_raw'];phase=a['phase'];v=json.loads(a['response_raw']['choices'][0]['message']['content'])
        if request['messages']!=arms[phase] or request['thinking']!={'type':'enabled'} or request['max_tokens']!=32768 or a['actual_model_id']!=p['model']:raise ValueError('frozen request or actual model drift')
        rows=v['source_index'] if phase=='G_map' else v['source_citations'];badcounts[phase]=sum(row['quote'] not in s for row in rows)
        try:
            if phase=='G_map':prepare_generic_final_v9(arms,a['response_raw']['choices'][0]['message']['content'])
            else:validate_answer(v,{item['source_id']:s})
        except ValueError:pass
        else:raise ValueError('old output was newly accepted')
        usage.append(dict(phase=phase,model=a['actual_model_id'],usage=a['usage']))
    if badcounts!={'C':2,'P':2,'G_map':31}:raise ValueError('strict quotation failure drift')
    if (r['estimated_actual_cost_usd']!=c['estimated_actual_cost_usd'] or r['rated_peak_cost_usd']!=c['rated_peak_cost_usd'] or r['actual_invoice_cost_usd'] is not None or r['conservative_reserved_usd']>r['hard_cap_usd']):raise ValueError('cost/accounting drift')
    return dict(status='PASS_IMMUTABLE_SOURCE_FIRST_INCONCLUSIVE_CLOSURE',run_id=c['run_id'],main_sha=c['run_sha'],provider_calls=3,new_audit_provider_calls=0,strict_invalid_quotation_counts=badcounts,formal_semantic_scores=None,grant_remaining_usd=0,trigger_removed=True,artifact_sha256=c['artifact_sha256'],actual_usage=usage,longmemeval='SEALED_NOT_ACCESSED')
if __name__=='__main__':print(json.dumps(audit(),indent=2))
