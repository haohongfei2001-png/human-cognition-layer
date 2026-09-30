"""Existing C03 composition reaches bounded complete ordinary-source H input."""
import json
from pathlib import Path
from scripts.i02_runtime_amendment_v10 import validate_runtime_amendment_v10
from scripts.serious_eval_contract import runtime_digest

def validate_runtime_amendment_v11(freeze,*versions,current_digest=None):
    if len(versions)!=11:raise ValueError('complete runtime amendment chain required')
    v10,v11=versions[-2:]
    validate_runtime_amendment_v10(freeze,*versions[:-1],current_digest=v10['amended_hcl_runtime_sha256'])
    if (v11.get('schema')!='hcl-i02-runtime-amendment-v11' or v11.get('reason')!='EXISTING_C03_LONG_READER_COMPOSITION' or
        v11.get('previous_hcl_runtime_sha256')!=v10['amended_hcl_runtime_sha256'] or v11.get('historical_i01_main_sha')!=freeze['architecture_main_sha'] or
        v11.get('development_only') is not True or v11.get('confirmation_items_inspected')!=0 or v11.get('provider_calls')!=0 or v11.get('provider_spend_usd')!=0 or
        v11.get('answer_gain_claimed') is not False or v11.get('new_cognition_module') is not False or
        v11.get('amended_hcl_runtime_sha256')!=(current_digest or runtime_digest()) or v11.get('longmemeval')!='SEALED_NOT_ACCESSED'):
        raise ValueError('invalid current I02 v11 runtime amendment')
    return True

def validate_current():
    names=['HCL_I01_EVALUATION_FREEZE.json','HCL_I02_RUNTIME_AMENDMENT.json']+[f'HCL_I02_RUNTIME_AMENDMENT_V{i}.json' for i in range(2,12)]
    return validate_runtime_amendment_v11(*[json.loads(Path('reports',n).read_text()) for n in names])
if __name__=='__main__':validate_current();print('I02_RUNTIME_V11_VALID')
