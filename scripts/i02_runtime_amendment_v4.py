"""Chain the ordinary long-source default-budget fix from consumed v3."""
import json
from pathlib import Path

from scripts.i02_runtime_amendment_v3 import validate_runtime_amendment_v3
from scripts.serious_eval_contract import runtime_digest


def validate_runtime_amendment_v4(freeze, v1, v2, v3, v4, *, current_digest=None):
    validate_runtime_amendment_v3(freeze, v1, v2, v3,
        current_digest=v3.get('amended_hcl_runtime_sha256'))
    if (v4.get('schema') != 'hcl-i02-runtime-amendment-v4' or
            v4.get('reason') != 'DEFAULT_COMPLETE_LONG_SOURCE_CONTEXT_BUDGET' or
            v4.get('historical_i01_main_sha') != freeze['architecture_main_sha'] or
            v4.get('previous_hcl_runtime_sha256') != v3['amended_hcl_runtime_sha256'] or
            v4.get('calibration_only') is not True or
            v4.get('confirmation_items_inspected') != 0 or
            v4.get('provider_calls') != 0 or v4.get('provider_spend_usd') != 0 or
            v4.get('specialized_cognition_treatment_claimed') is not False or
            v4.get('longmemeval') != 'SEALED_NOT_ACCESSED'):
        raise ValueError('invalid I02 v4 runtime amendment')
    if v4.get('amended_hcl_runtime_sha256') != (current_digest or runtime_digest()):
        raise ValueError('current runtime differs from disclosed I02 v4 amendment')
    return True


def validate_current():
    report = Path('reports')
    rows = [json.loads((report / name).read_text()) for name in (
        'HCL_I01_EVALUATION_FREEZE.json', 'HCL_I02_RUNTIME_AMENDMENT.json',
        'HCL_I02_RUNTIME_AMENDMENT_V2.json',
        'HCL_I02_RUNTIME_AMENDMENT_V3.json',
        'HCL_I02_RUNTIME_AMENDMENT_V4.json')]
    return validate_runtime_amendment_v4(*rows)


if __name__ == '__main__':
    validate_current()
    print('I02_RUNTIME_V4_VALID')
