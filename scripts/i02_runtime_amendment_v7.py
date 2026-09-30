"""Versioned bounded complete long-source entry; no specialized cognition gain claim."""
import json
from pathlib import Path
from scripts.i02_runtime_amendment_v6 import validate_runtime_amendment_v6
from scripts.serious_eval_contract import runtime_digest

def validate_runtime_amendment_v7(freeze,v1,v2,v3,v4,v5,v6,v7,*,current_digest=None):
    validate_runtime_amendment_v6(freeze,v1,v2,v3,v4,v5,v6,current_digest=v6['amended_hcl_runtime_sha256'])
    if (v7.get('schema')!='hcl-i02-runtime-amendment-v7' or v7.get('reason')!='BOUNDED_COMPLETE_ORDINARY_LONG_SOURCE_ENTRY' or
        v7.get('previous_hcl_runtime_sha256')!=v6['amended_hcl_runtime_sha256'] or v7.get('historical_i01_main_sha')!=freeze['architecture_main_sha'] or
        v7.get('development_only') is not True or v7.get('confirmation_items_inspected')!=0 or v7.get('provider_calls')!=0 or v7.get('provider_spend_usd')!=0 or
        v7.get('answer_gain_claimed') is not False or v7.get('specialized_cognition_treatment_claimed') is not False or
        v7.get('amended_hcl_runtime_sha256')!=(current_digest or runtime_digest()) or v7.get('longmemeval')!='SEALED_NOT_ACCESSED'):
        raise ValueError('invalid current I02 v7 runtime amendment')
    return True

def validate_current():
    names=['HCL_I01_EVALUATION_FREEZE.json','HCL_I02_RUNTIME_AMENDMENT.json']+[f'HCL_I02_RUNTIME_AMENDMENT_V{i}.json' for i in range(2,8)]
    return validate_runtime_amendment_v7(*[json.loads(Path('reports',n).read_text()) for n in names])
if __name__=='__main__':validate_current();print('I02_RUNTIME_V7_VALID')
