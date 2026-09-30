"""Opt-in ordinary typographic dialogue joins the existing B01 modal checker."""
import json
from pathlib import Path
from scripts.i02_runtime_amendment_v8 import validate_runtime_amendment_v8
from scripts.serious_eval_contract import runtime_digest

def validate_runtime_amendment_v9(freeze,*versions,current_digest=None):
    if len(versions)!=9:raise ValueError('complete runtime amendment chain required')
    v8,v9=versions[-2:]
    validate_runtime_amendment_v8(freeze,*versions[:-1],current_digest=v8['amended_hcl_runtime_sha256'])
    if (v9.get('schema')!='hcl-i02-runtime-amendment-v9' or v9.get('reason')!='EXISTING_B01_TYPOGRAPHIC_DIALOGUE_ENTRY' or
        v9.get('previous_hcl_runtime_sha256')!=v8['amended_hcl_runtime_sha256'] or v9.get('historical_i01_main_sha')!=freeze['architecture_main_sha'] or
        v9.get('development_only') is not True or v9.get('confirmation_items_inspected')!=0 or v9.get('provider_calls')!=0 or v9.get('provider_spend_usd')!=0 or
        v9.get('answer_gain_claimed') is not False or v9.get('new_cognition_module') is not False or
        v9.get('amended_hcl_runtime_sha256')!=(current_digest or runtime_digest()) or v9.get('longmemeval')!='SEALED_NOT_ACCESSED'):
        raise ValueError('invalid current I02 v9 runtime amendment')
    return True

def validate_current():
    names=['HCL_I01_EVALUATION_FREEZE.json','HCL_I02_RUNTIME_AMENDMENT.json']+[f'HCL_I02_RUNTIME_AMENDMENT_V{i}.json' for i in range(2,10)]
    return validate_runtime_amendment_v9(*[json.loads(Path('reports',n).read_text()) for n in names])
if __name__=='__main__':validate_current();print('I02_RUNTIME_V9_VALID')
