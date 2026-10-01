"""Embedded scene-cue successor; preserve prior narrator and speech evidence."""
import hashlib
import json
from pathlib import Path

from scripts.development_narrator_actual_amendment import validate_current as validate_previous
from scripts.serious_eval_contract import runtime_digest

REPORT = Path('reports/HCL_DEVELOPMENT_EMBEDDED_SCENE_AMENDMENT.json')
PREVIOUS_REPORT = Path('reports/HCL_DEVELOPMENT_NARRATOR_ACTUAL_AMENDMENT.json')
PREVIOUS_REPORT_SHA = '3cba3300953341a71fe23b518ac169f481386837a9b5b0c7ce65af9bc455a06f'
PREVIOUS_VALIDATOR = Path('scripts/development_narrator_actual_amendment.py')
PREVIOUS_VALIDATOR_SHA = '772646429475b7f4eab0b3e47e7e454346e95d3f615ad97913d0d36119da033d'
CHANGED_RUNTIME = 'hcl/cognition/semantic.py'
PREVIOUS_SEMANTIC_SHA = '8bc114807af5b4e0d5a53085602df451fced1512d638cb3e04338e58fa6f95a3'


def validate_current(*, current_digest=None):
    if (hashlib.sha256(PREVIOUS_REPORT.read_bytes()).hexdigest() != PREVIOUS_REPORT_SHA
            or hashlib.sha256(PREVIOUS_VALIDATOR.read_bytes()).hexdigest() != PREVIOUS_VALIDATOR_SHA):
        raise ValueError('historical narrator-actual amendment or validator drift')
    previous = json.loads(PREVIOUS_REPORT.read_text())
    validate_previous(current_digest=previous['amended_hcl_runtime_sha256'])
    current = {str(p): hashlib.sha256(p.read_bytes()).hexdigest()
               for p in Path('hcl').rglob('*.py')}
    restored = dict(current, **{CHANGED_RUNTIME: PREVIOUS_SEMANTIC_SHA})
    restored_digest = hashlib.sha256(json.dumps(restored, sort_keys=True,
        separators=(',', ':')).encode()).hexdigest()
    if restored_digest != previous['amended_hcl_runtime_sha256']:
        raise ValueError('embedded-scene repair changed unrelated runtime')
    value = json.loads(REPORT.read_text())
    if (value.get('schema') != 'hcl-development-embedded-scene-amendment-v1'
            or value.get('previous_hcl_runtime_sha256') != restored_digest
            or value.get('amended_hcl_runtime_sha256') != (current_digest or runtime_digest())
            or value.get('reason') != 'KEEP_EMBEDDED_SCENE_CUES_OUT_OF_NARRATION'
            or value.get('changed_runtime_files') != [CHANGED_RUNTIME]
            or value.get('answer_gain_claimed') is not False
            or value.get('new_prompt_instruction') is not False
            or value.get('provider_calls') != 0 or value.get('provider_spend_usd') != 0
            or value.get('development_only') is not True
            or value.get('longmemeval') != 'SEALED_NOT_ACCESSED'):
        raise ValueError('invalid embedded-scene runtime amendment')
    return True


if __name__ == '__main__':
    validate_current()
    print('EMBEDDED_SCENE_VALID_HISTORICAL_NARRATOR_SPEECH_BUDGET_AND_V24_PRESERVED')
