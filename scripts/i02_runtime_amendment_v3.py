"""Versioned long-source runtime pin without editing consumed I02 runners."""
import json
from pathlib import Path

from scripts.serious_eval_contract import (runtime_digest, validate_runtime_amendment_v2)


def validate_runtime_amendment_v3(freeze, amendment_v1, amendment_v2,
                                  amendment_v3, *, current_digest=None):
    validate_runtime_amendment_v2(freeze, amendment_v1, amendment_v2,
        current_digest=amendment_v2.get('amended_hcl_runtime_sha256'))
    if (amendment_v3.get('schema') != 'hcl-i02-runtime-amendment-v3' or
            amendment_v3.get('reason') != 'GENERAL_COMPLETE_LONG_SOURCE_LOCAL_EVIDENCE_ENTRY' or
            amendment_v3.get('historical_i01_main_sha') != freeze['architecture_main_sha'] or
            amendment_v3.get('previous_hcl_runtime_sha256') !=
                amendment_v2['amended_hcl_runtime_sha256'] or
            amendment_v3.get('calibration_only') is not True or
            amendment_v3.get('confirmation_items_inspected') != 0 or
            amendment_v3.get('provider_calls') != 0 or
            amendment_v3.get('provider_spend_usd') != 0 or
            amendment_v3.get('specialized_cognition_treatment_claimed') is not False or
            amendment_v3.get('longmemeval') != 'SEALED_NOT_ACCESSED'):
        raise ValueError('invalid I02 v3 runtime amendment')
    if amendment_v3.get('amended_hcl_runtime_sha256') != (current_digest or runtime_digest()):
        raise ValueError('current runtime differs from disclosed I02 v3 amendment')
    return True


def validate_current():
    report = Path('reports')
    freeze = json.loads((report / 'HCL_I01_EVALUATION_FREEZE.json').read_text())
    v1 = json.loads((report / 'HCL_I02_RUNTIME_AMENDMENT.json').read_text())
    v2 = json.loads((report / 'HCL_I02_RUNTIME_AMENDMENT_V2.json').read_text())
    v3 = json.loads((report / 'HCL_I02_RUNTIME_AMENDMENT_V3.json').read_text())
    return validate_runtime_amendment_v3(freeze, v1, v2, v3)


if __name__ == '__main__':
    validate_current()
    print('I02_RUNTIME_V3_VALID')
