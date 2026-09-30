"""Existing B01 separates source-narrator attribution in complete ordinary H input."""
import json
from pathlib import Path
from scripts.i02_runtime_amendment_v11 import validate_runtime_amendment_v11
from scripts.serious_eval_contract import runtime_digest

def validate_runtime_amendment_v12(freeze,*versions,current_digest=None):
    if len(versions)!=12:raise ValueError('complete runtime amendment chain required')
    v11,v12=versions[-2:]
    validate_runtime_amendment_v11(freeze,*versions[:-1],current_digest=v11['amended_hcl_runtime_sha256'])
    if (v12.get('schema')!='hcl-i02-runtime-amendment-v12' or v12.get('reason')!='EXISTING_B01_SOURCE_NARRATOR_ATTRIBUTION_ENTRY' or
        v12.get('previous_hcl_runtime_sha256')!=v11['amended_hcl_runtime_sha256'] or v12.get('historical_i01_main_sha')!=freeze['architecture_main_sha'] or
        v12.get('development_only') is not True or v12.get('confirmation_items_inspected')!=0 or v12.get('provider_calls')!=0 or v12.get('provider_spend_usd')!=0 or
        v12.get('answer_gain_claimed') is not False or v12.get('new_cognition_module') is not False or
        v12.get('amended_hcl_runtime_sha256')!=(current_digest or runtime_digest()) or v12.get('longmemeval')!='SEALED_NOT_ACCESSED'):
        raise ValueError('invalid current I02 v12 runtime amendment')
    return True

def validate_current():
    names=['HCL_I01_EVALUATION_FREEZE.json','HCL_I02_RUNTIME_AMENDMENT.json']+[f'HCL_I02_RUNTIME_AMENDMENT_V{i}.json' for i in range(2,13)]
    return validate_runtime_amendment_v12(*[json.loads(Path('reports',n).read_text()) for n in names])
if __name__=='__main__':validate_current();print('I02_RUNTIME_V12_VALID')
