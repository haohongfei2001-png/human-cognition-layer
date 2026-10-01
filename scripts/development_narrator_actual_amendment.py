"""Narrator resumption successor; preserve prior speech and budget evidence."""
import hashlib
import json
from pathlib import Path

from scripts.development_qualified_speech_amendment import validate_current as validate_previous
from scripts.serious_eval_contract import runtime_digest

REPORT = Path('reports/HCL_DEVELOPMENT_NARRATOR_ACTUAL_AMENDMENT.json')
PREVIOUS_REPORT = Path('reports/HCL_DEVELOPMENT_QUALIFIED_SPEECH_AMENDMENT.json')
PREVIOUS_REPORT_SHA = '56ee187b743c3d8a8b2b7ad632457e5a711d6c380c2c70bc9e2ebdc663308aac'
PREVIOUS_VALIDATOR = Path('scripts/development_qualified_speech_amendment.py')
PREVIOUS_VALIDATOR_SHA = 'd6352e090250bfd55db4415c3636c649a41526008eb0c0393bd520830ed02eeb'
CHANGED_RUNTIME = 'hcl/cognition/semantic.py'
PREVIOUS_SEMANTIC_SHA = 'c581e81228526574c979a7c465d86bf73e3ec8f29a6eb207a21514180b0cc688'


def validate_current(*, current_digest=None):
    if (hashlib.sha256(PREVIOUS_REPORT.read_bytes()).hexdigest() != PREVIOUS_REPORT_SHA
            or hashlib.sha256(PREVIOUS_VALIDATOR.read_bytes()).hexdigest() != PREVIOUS_VALIDATOR_SHA):
        raise ValueError('historical qualified-speech amendment or validator drift')
    previous = json.loads(PREVIOUS_REPORT.read_text())
    validate_previous(current_digest=previous['amended_hcl_runtime_sha256'])
    current = {str(p): hashlib.sha256(p.read_bytes()).hexdigest()
               for p in Path('hcl').rglob('*.py')}
    restored = dict(current, **{CHANGED_RUNTIME: PREVIOUS_SEMANTIC_SHA})
    restored_digest = hashlib.sha256(json.dumps(restored, sort_keys=True,
        separators=(',', ':')).encode()).hexdigest()
    if restored_digest != previous['amended_hcl_runtime_sha256']:
        raise ValueError('narrator resumption changed unrelated runtime')
    value = json.loads(REPORT.read_text())
    if (value.get('schema') != 'hcl-development-narrator-actual-amendment-v1'
            or value.get('previous_hcl_runtime_sha256') != restored_digest
            or value.get('amended_hcl_runtime_sha256') != (current_digest or runtime_digest())
            or value.get('reason') != 'RESTORE_EXPLICIT_ACTUAL_NARRATOR_REPORT_SCOPE'
            or value.get('changed_runtime_files') != [CHANGED_RUNTIME]
            or value.get('answer_gain_claimed') is not False
            or value.get('new_prompt_instruction') is not False
            or value.get('provider_calls') != 0 or value.get('provider_spend_usd') != 0
            or value.get('development_only') is not True
            or value.get('longmemeval') != 'SEALED_NOT_ACCESSED'):
        raise ValueError('invalid narrator-actual runtime amendment')
    return True


if __name__ == '__main__':
    validate_current()
    print('NARRATOR_ACTUAL_VALID_HISTORICAL_SPEECH_BUDGET_AND_V24_PRESERVED')
