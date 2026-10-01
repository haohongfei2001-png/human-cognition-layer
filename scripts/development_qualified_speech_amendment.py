"""Qualified-speech successor; preserve the v24 and budget-only evidence pins."""
import hashlib
import json
from pathlib import Path

from scripts.development_drc008_replay import validate_archive
from scripts.development_runtime_amendment_v24 import validate_current as validate_v24
from scripts.serious_eval_contract import runtime_digest


REPORT = Path('reports/HCL_DEVELOPMENT_QUALIFIED_SPEECH_AMENDMENT.json')
BUDGET_REPORT = Path('reports/HCL_DEVELOPMENT_READER_FINAL_BUDGET_AMENDMENT.json')
BUDGET_REPORT_SHA = 'ab1037d2fd4b443f31ca027fe13c1f051bdad8d41a5e7e30ed9338d9ba586d88'
BUDGET_VALIDATOR = Path('scripts/development_reader_final_budget_amendment.py')
BUDGET_VALIDATOR_SHA = '24b8c621aba2f50e5509df44fee0ba8dc106db34f71ede3c1d758cbd72a170fe'
CHANGED_RUNTIME = 'hcl/cognition/semantic.py'


def validate_current(*, current_digest=None):
    cert = validate_archive()
    validate_v24(current_digest=cert['runtime_sha256'])
    if (hashlib.sha256(BUDGET_REPORT.read_bytes()).hexdigest() != BUDGET_REPORT_SHA
            or hashlib.sha256(BUDGET_VALIDATOR.read_bytes()).hexdigest() != BUDGET_VALIDATOR_SHA):
        raise ValueError('historical budget amendment or validator drift')
    budget = json.loads(BUDGET_REPORT.read_text())
    value = json.loads(REPORT.read_text())
    current = {str(p): hashlib.sha256(p.read_bytes()).hexdigest()
               for p in Path('hcl').rglob('*.py')}
    archived = {p: row['sha256'] for p, row in cert['files'].items()
                if p.startswith('hcl/') and p.endswith('.py')}
    if set(current) != set(archived):
        raise ValueError('qualified-speech runtime membership drift')
    # Reconstruct the previous full runtime hash with only semantic.py restored
    # from certified v24. The budget fix did not change that file. Matching the
    # immutable budget digest proves every other current runtime file is intact,
    # including reader_entry.py; no historical size witness is reinterpreted.
    previous = dict(current, **{CHANGED_RUNTIME: archived[CHANGED_RUNTIME]})
    previous_digest = hashlib.sha256(json.dumps(previous, sort_keys=True,
        separators=(',', ':')).encode()).hexdigest()
    if (budget['previous_hcl_runtime_sha256'] != cert['runtime_sha256']
            or previous_digest != budget['amended_hcl_runtime_sha256']):
        raise ValueError('qualified-speech amendment changed unrelated budget runtime')
    if (value.get('schema') != 'hcl-development-qualified-speech-amendment-v1'
            or value.get('previous_hcl_runtime_sha256') != previous_digest
            or value.get('amended_hcl_runtime_sha256') != (current_digest or runtime_digest())
            or value.get('reason') != 'PRESERVE_EXPLICIT_HYPOTHETICAL_SPEECH_SCOPE'
            or value.get('changed_runtime_files') != [CHANGED_RUNTIME]
            or value.get('answer_gain_claimed') is not False
            or value.get('new_prompt_instruction') is not False
            or value.get('provider_calls') != 0 or value.get('provider_spend_usd') != 0
            or value.get('development_only') is not True
            or value.get('longmemeval') != 'SEALED_NOT_ACCESSED'):
        raise ValueError('invalid qualified-speech runtime amendment')
    return True


if __name__ == '__main__':
    validate_current()
    print('QUALIFIED_SPEECH_VALID_HISTORICAL_BUDGET_AND_V24_PRESERVED')
