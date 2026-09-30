"""Chain the reader-level argument entry correction without rewriting I01–v4."""
import json
from pathlib import Path

from scripts.i02_runtime_amendment_v4 import validate_runtime_amendment_v4
from scripts.serious_eval_contract import runtime_digest


def validate_runtime_amendment_v5(freeze, v1, v2, v3, v4, v5, *, current_digest=None):
    validate_runtime_amendment_v4(freeze, v1, v2, v3, v4,
        current_digest=v4.get('amended_hcl_runtime_sha256'))
    if (v5.get('schema') != 'hcl-i02-runtime-amendment-v5' or
            v5.get('reason') != 'READER_SOURCE_ARGUMENT_ENTRY' or
            v5.get('historical_i01_main_sha') != freeze['architecture_main_sha'] or
            v5.get('previous_hcl_runtime_sha256') != v4['amended_hcl_runtime_sha256'] or
            v5.get('calibration_only') is not True or
            v5.get('confirmation_items_inspected') != 0 or
            v5.get('provider_calls') != 0 or v5.get('provider_spend_usd') != 0 or
            v5.get('specialized_cognition_treatment_claimed') is not False or
            v5.get('longmemeval') != 'SEALED_NOT_ACCESSED'):
        raise ValueError('invalid I02 v5 runtime amendment')
    if v5.get('amended_hcl_runtime_sha256') != (current_digest or runtime_digest()):
        raise ValueError('current runtime differs from disclosed I02 v5 amendment')
    return True


def validate_current():
    report = Path('reports')
    rows = [json.loads((report / name).read_text()) for name in (
        'HCL_I01_EVALUATION_FREEZE.json', 'HCL_I02_RUNTIME_AMENDMENT.json',
        'HCL_I02_RUNTIME_AMENDMENT_V2.json',
        'HCL_I02_RUNTIME_AMENDMENT_V3.json',
        'HCL_I02_RUNTIME_AMENDMENT_V4.json',
        'HCL_I02_RUNTIME_AMENDMENT_V5.json')]
    return validate_runtime_amendment_v5(*rows)


if __name__ == '__main__':
    validate_current()
    print('I02_RUNTIME_V5_VALID')
