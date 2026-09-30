"""Existing B01 checked modal objects enter whole ordinary long-source H input."""
import json
from pathlib import Path
from scripts.i02_runtime_amendment_v7 import validate_runtime_amendment_v7
from scripts.serious_eval_contract import runtime_digest

def validate_runtime_amendment_v8(freeze,v1,v2,v3,v4,v5,v6,v7,v8,*,current_digest=None):
    validate_runtime_amendment_v7(freeze,v1,v2,v3,v4,v5,v6,v7,current_digest=v7['amended_hcl_runtime_sha256'])
    if (v8.get('schema')!='hcl-i02-runtime-amendment-v8' or v8.get('reason')!='EXISTING_B01_LONG_READER_INTEGRATION' or
        v8.get('previous_hcl_runtime_sha256')!=v7['amended_hcl_runtime_sha256'] or v8.get('historical_i01_main_sha')!=freeze['architecture_main_sha'] or
        v8.get('development_only') is not True or v8.get('confirmation_items_inspected')!=0 or v8.get('provider_calls')!=0 or v8.get('provider_spend_usd')!=0 or
        v8.get('answer_gain_claimed') is not False or v8.get('new_cognition_module') is not False or
        v8.get('amended_hcl_runtime_sha256')!=(current_digest or runtime_digest()) or v8.get('longmemeval')!='SEALED_NOT_ACCESSED'):
        raise ValueError('invalid current I02 v8 runtime amendment')
    return True

def validate_current():
    names=['HCL_I01_EVALUATION_FREEZE.json','HCL_I02_RUNTIME_AMENDMENT.json']+[f'HCL_I02_RUNTIME_AMENDMENT_V{i}.json' for i in range(2,9)]
    return validate_runtime_amendment_v8(*[json.loads(Path('reports',n).read_text()) for n in names])
if __name__=='__main__':validate_current();print('I02_RUNTIME_V8_VALID')
