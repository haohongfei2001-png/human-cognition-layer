"""Pin the prior runtime, preserve its historical receipt, amend final answer policy only."""
import hashlib
import json
from pathlib import Path
from scripts.serious_eval_contract import runtime_digest
REPORT=Path('reports/HCL_DEVELOPMENT_ANSWER_BOUNDARY_AMENDMENT.json')
PREVIOUS_REPORT=Path('reports/HCL_DEVELOPMENT_EMBEDDED_SCENE_AMENDMENT.json')
PREVIOUS_VALIDATOR=Path('scripts/development_embedded_scene_amendment.py')
PREVIOUS_REPORT_SHA='6ae2202f34ed105b821e84d1e942cbba9642864c183b9fdb9bac20208e5b128e'
PREVIOUS_VALIDATOR_SHA='550393384c24cfd408830accb113870366cbc247e3b2c208e17305c97165c6b2'
CHANGED='hcl/cognition/reader_entry.py'
PREVIOUS_FILE_SHA='9bb6cc1d52f19104f5b07bbf8baa7d1e54fb1adef317c2952eb87591a463e30c'

def validate_current(*, current_digest=None):
    for path, expected in ((PREVIOUS_REPORT,PREVIOUS_REPORT_SHA),(PREVIOUS_VALIDATOR,PREVIOUS_VALIDATOR_SHA)):
        if hashlib.sha256(path.read_bytes()).hexdigest()!=expected:raise ValueError('historical amendment drift')
    prior=json.loads(PREVIOUS_REPORT.read_text())
    files={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in Path('hcl').rglob('*.py')}
    files[CHANGED]=PREVIOUS_FILE_SHA
    files.pop('hcl/cognition/orchestration.py',None)
    restored=hashlib.sha256(json.dumps(files,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    if restored!=prior['amended_hcl_runtime_sha256']:raise ValueError('unrelated runtime changed')
    value=json.loads(REPORT.read_text())
    expected=dict(schema='hcl-development-answer-boundary-amendment-v1',previous_hcl_runtime_sha256=restored,
        amended_hcl_runtime_sha256=current_digest or runtime_digest(),changed_runtime_files=[CHANGED,'hcl/cognition/orchestration.py'],
        reason='UNIVERSAL_ENTRY_FIRST_SLICE_AND_ANSWER_BOUNDARY',
        new_prompt_instruction=True,answer_gain_claimed=False,semantic_checker_added=False,
        provider_calls=0,provider_spend_usd=0,development_only=True,longmemeval='SEALED_NOT_ACCESSED')
    if value!=expected:raise ValueError('answer boundary amendment drift')
    return True

if __name__=='__main__':validate_current();print('ANSWER_BOUNDARY_CURRENT_RUNTIME_PIN_PASS')
