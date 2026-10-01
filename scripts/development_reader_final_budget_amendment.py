"""Budget-only successor to certified v24; historical runtime pins stay immutable."""
import hashlib
import json
from pathlib import Path
from scripts.development_drc008_replay import validate_archive
from scripts.development_runtime_amendment_v24 import validate_current as validate_v24
from scripts.serious_eval_contract import runtime_digest

REPORT = Path('reports/HCL_DEVELOPMENT_READER_FINAL_BUDGET_AMENDMENT.json')
CHANGED_RUNTIME = 'hcl/cognition/reader_entry.py'


def validate_current(*, current_digest=None):
    previous = json.loads(Path('reports/HCL_DEVELOPMENT_RUNTIME_AMENDMENT_V24.json').read_text())
    baseline = previous['amended_hcl_runtime_sha256']
    validate_v24(current_digest=baseline)
    cert = validate_archive()
    value = json.loads(REPORT.read_text())
    if (value.get('schema') != 'hcl-development-reader-final-budget-amendment-v1'
            or cert['runtime_sha256'] != baseline
            or value.get('previous_hcl_runtime_sha256') != baseline
            or value.get('amended_hcl_runtime_sha256') != (current_digest or runtime_digest())
            or value.get('reason') != 'ENFORCE_FINAL_CONTEXT_LIMIT_WITH_UNCHANGED_V24_MESSAGE_CONTENT'
            or value.get('changed_runtime_files') != [CHANGED_RUNTIME]
            or value.get('answer_gain_claimed') is not False
            or value.get('new_prompt_instruction') is not False
            or value.get('provider_calls') != 0 or value.get('provider_spend_usd') != 0
            or value.get('development_only') is not True
            or value.get('longmemeval') != 'SEALED_NOT_ACCESSED'):
        raise ValueError('invalid reader final-budget runtime amendment')
    archived = {p: row['sha256'] for p, row in cert['files'].items()
                if p.startswith('hcl/') and p.endswith('.py')}
    current = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in Path('hcl').rglob('*.py')}
    if set(current) != set(archived) or any(current[p] != archived[p] for p in current if p != CHANGED_RUNTIME):
        raise ValueError('budget amendment changed unrelated certified runtime')
    return True


if __name__ == '__main__':
    validate_current()
    print('READER_FINAL_BUDGET_VALID_UNCHANGED_V24_MESSAGE_POLICY')
