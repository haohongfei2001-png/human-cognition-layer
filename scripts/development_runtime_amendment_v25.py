"""Source-bounded ordinary explanation delivery; consumed runtime archives pinned."""
import json
from pathlib import Path

from scripts.development_drc008_replay import validate_archive
from scripts.development_runtime_amendment_v24 import validate_current as validate_v24
from scripts.serious_eval_contract import runtime_digest


def validate_current(*, current_digest=None):
    previous = json.loads(Path('reports/HCL_DEVELOPMENT_RUNTIME_AMENDMENT_V24.json').read_text())
    pin = previous['amended_hcl_runtime_sha256']
    validate_v24(current_digest=pin)
    cert = validate_archive()
    value = json.loads(Path('reports/HCL_DEVELOPMENT_RUNTIME_AMENDMENT_V25.json').read_text())
    batches = ['DRC001', 'DRC002', 'DRE001', 'DRC003', 'DRC004', 'DRC005', 'DRC006', 'DRC007', 'DRC008']
    if (value.get('schema') != 'hcl-development-runtime-amendment-v25'
            or value.get('previous_hcl_runtime_sha256') != pin or cert['runtime_sha256'] != pin
            or value.get('amended_hcl_runtime_sha256') != (current_digest or runtime_digest())
            or value.get('historical_i01_main_sha') != previous['historical_i01_main_sha']
            or value.get('reason') != 'GENERAL_ORDINARY_ANSWER_SOURCE_INFERENCE_BOUNDARY_REPAIR'
            or value.get('development_exposed_batches') != batches
            or value.get('development_only') is not True
            or value.get('new_cognition_module') is not False
            or value.get('answer_gain_claimed') is not False
            or value.get('semantic_certification_claimed') is not False
            or value.get('provider_calls') != 0 or value.get('provider_spend_usd') != 0
            or value.get('confirmation_items_inspected') != 0
            or value.get('longmemeval') != 'SEALED_NOT_ACCESSED'
            or any(value.get('consumed_' + batch.lower() + '_runtime_preserved') is not True for batch in batches)):
        raise ValueError('invalid current development runtime v25')
    return True


if __name__ == '__main__':
    validate_current()
    print('DEVELOPMENT_RUNTIME_V25_VALID_SOURCE_INFERENCE_BOUNDARY')
