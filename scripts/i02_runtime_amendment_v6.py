"""Disclose complete ordinary reader-source carry; preserve historical freezes."""
import json
from pathlib import Path
from scripts.i02_runtime_amendment_v5 import validate_runtime_amendment_v5
from scripts.serious_eval_contract import runtime_digest

def validate_runtime_amendment_v6(freeze,v1,v2,v3,v4,v5,v6,*,current_digest=None):
    validate_runtime_amendment_v5(freeze,v1,v2,v3,v4,v5,
        current_digest=v5['amended_hcl_runtime_sha256'])
    if (v6.get('schema')!='hcl-i02-runtime-amendment-v6' or
            v6.get('reason')!='COMPLETE_UNRESTRICTED_READER_SOURCE_CARRY' or
            v6.get('historical_i01_main_sha')!=freeze['architecture_main_sha'] or
            v6.get('previous_hcl_runtime_sha256')!=v5['amended_hcl_runtime_sha256'] or
            v6.get('development_only') is not True or
            v6.get('confirmation_items_inspected')!=0 or v6.get('provider_calls')!=0 or
            v6.get('provider_spend_usd')!=0 or v6.get('answer_gain_claimed') is not False or
            v6.get('longmemeval')!='SEALED_NOT_ACCESSED' or
            v6.get('amended_hcl_runtime_sha256')!=(current_digest or runtime_digest())):
        raise ValueError('invalid current I02 v6 runtime amendment')
    return True

def validate_current():
    paths=['HCL_I01_EVALUATION_FREEZE.json','HCL_I02_RUNTIME_AMENDMENT.json']+[
        f'HCL_I02_RUNTIME_AMENDMENT_V{i}.json' for i in range(2,7)]
    return validate_runtime_amendment_v6(*[json.loads(Path('reports',p).read_text()) for p in paths])

if __name__=='__main__':
    validate_current();print('I02_RUNTIME_V6_VALID')
