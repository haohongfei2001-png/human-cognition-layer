"""Existing C01 checks share grounded complete ordinary-source preparation."""
import json
from pathlib import Path
from scripts.i02_runtime_amendment_v9 import validate_runtime_amendment_v9
from scripts.serious_eval_contract import runtime_digest

def validate_runtime_amendment_v10(freeze,*versions,current_digest=None):
    if len(versions)!=10:raise ValueError('complete runtime amendment chain required')
    v9,v10=versions[-2:]
    validate_runtime_amendment_v9(freeze,*versions[:-1],current_digest=v9['amended_hcl_runtime_sha256'])
    if (v10.get('schema')!='hcl-i02-runtime-amendment-v10' or v10.get('reason')!='EXISTING_C01_LONG_READER_INTEGRATION' or
        v10.get('previous_hcl_runtime_sha256')!=v9['amended_hcl_runtime_sha256'] or v10.get('historical_i01_main_sha')!=freeze['architecture_main_sha'] or
        v10.get('development_only') is not True or v10.get('confirmation_items_inspected')!=0 or v10.get('provider_calls')!=0 or v10.get('provider_spend_usd')!=0 or
        v10.get('answer_gain_claimed') is not False or v10.get('new_cognition_module') is not False or
        v10.get('amended_hcl_runtime_sha256')!=(current_digest or runtime_digest()) or v10.get('longmemeval')!='SEALED_NOT_ACCESSED'):
        raise ValueError('invalid current I02 v10 runtime amendment')
    return True

def validate_current():
    names=['HCL_I01_EVALUATION_FREEZE.json','HCL_I02_RUNTIME_AMENDMENT.json']+[f'HCL_I02_RUNTIME_AMENDMENT_V{i}.json' for i in range(2,11)]
    return validate_runtime_amendment_v10(*[json.loads(Path('reports',n).read_text()) for n in names])
if __name__=='__main__':validate_current();print('I02_RUNTIME_V10_VALID')
