"""Lossless identity-reference reader transport; historical raw source boundary preserved."""
import json
from pathlib import Path
from scripts.development_runtime_amendment_v16 import validate_current as validate_v16
from scripts.development_dre001_replay import validate_archive
from scripts.serious_eval_contract import runtime_digest

def validate_current(*, current_digest=None):
    previous = json.loads(Path('reports/HCL_DEVELOPMENT_RUNTIME_AMENDMENT_V16.json').read_text())
    pin = previous['amended_hcl_runtime_sha256']
    validate_v16(current_digest=pin)
    cert = validate_archive()
    v = json.loads(Path('reports/HCL_DEVELOPMENT_RUNTIME_AMENDMENT_V17.json').read_text())
    if (v.get('schema') != 'hcl-development-runtime-amendment-v17'
            or v.get('reason') != 'GENERAL_CONDITIONAL_READER_CONTEXT_COST_REDUCTION'
            or v.get('previous_hcl_runtime_sha256') != pin or cert['runtime_sha256'] != previous['previous_hcl_runtime_sha256']
            or v.get('amended_hcl_runtime_sha256') != (current_digest or runtime_digest())
            or v.get('historical_i01_main_sha') != previous['historical_i01_main_sha']
            or v.get('consumed_v16_source_boundary_preserved') is not True
            or v.get('development_only') is not True
            or v.get('new_cognition_module') is not False
            or v.get('answer_gain_claimed') is not False
            or v.get('semantic_certification_claimed') is not False
            or v.get('provider_calls') != 0 or v.get('provider_spend_usd') != 0
            or v.get('confirmation_items_inspected') != 0
            or any(v.get(k) is not True for k in ('consumed_drc001_runtime_preserved',
                'consumed_drc002_runtime_preserved','consumed_dre001_runtime_preserved'))
            or v.get('longmemeval') != 'SEALED_NOT_ACCESSED'):
        raise ValueError('invalid current development runtime v17')
    return True

if __name__ == '__main__':
    validate_current(); print('DEVELOPMENT_RUNTIME_V17_VALID_LOSSLESS_READER_COST')
