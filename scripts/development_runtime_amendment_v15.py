"""Conditional nonliteral reader entry; no historical or semantic-efficacy drift."""
import json
from pathlib import Path
from scripts.development_runtime_amendment_v14 import validate_current as validate_v14
from scripts.serious_eval_contract import runtime_digest

def validate_current(*, current_digest=None):
    previous = json.loads(Path('reports/HCL_DEVELOPMENT_RUNTIME_AMENDMENT_V14.json').read_text())
    pin = previous['amended_hcl_runtime_sha256']
    validate_v14(current_digest=pin)
    v = json.loads(Path('reports/HCL_DEVELOPMENT_RUNTIME_AMENDMENT_V15.json').read_text())
    if (v.get('schema') != 'hcl-development-runtime-amendment-v15'
            or v.get('reason') != 'GENERAL_NONLITERAL_CONDITIONAL_READER_ENTRY'
            or v.get('previous_hcl_runtime_sha256') != pin
            or v.get('amended_hcl_runtime_sha256') != (runtime_digest() if current_digest is None else current_digest)
            or v.get('historical_i01_main_sha') != previous['historical_i01_main_sha']
            or v.get('development_only') is not True
            or v.get('new_cognition_module') is not False
            or v.get('answer_gain_claimed') is not False
            or v.get('semantic_certification_claimed') is not False
            or v.get('provider_calls') != 0 or v.get('provider_spend_usd') != 0
            or v.get('confirmation_items_inspected') != 0
            or v.get('consumed_drc001_runtime_preserved') is not True
            or v.get('consumed_drc002_runtime_preserved') is not True
            or v.get('longmemeval') != 'SEALED_NOT_ACCESSED'):
        raise ValueError('invalid current development runtime v15')
    return True

if __name__ == '__main__':
    validate_current(); print('DEVELOPMENT_RUNTIME_V15_VALID_CONDITIONAL_NOT_CERTIFIED')
