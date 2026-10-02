"""Pin the existing-client adapter without rewriting prior runtime evidence."""
import hashlib,json
from pathlib import Path
from scripts.serious_eval_contract import runtime_digest
REPORT=Path('reports/HCL_DEVELOPMENT_METERED_UNIVERSAL_AMENDMENT.json')
PREVIOUS_REPORT=Path('reports/HCL_DEVELOPMENT_UNIVERSAL_QUESTION_AMENDMENT.json')
PREVIOUS_VALIDATOR=Path('scripts/development_universal_question_amendment.py')
PREVIOUS_REPORT_SHA='08bd9a87e5672fbb41f5120aa3846cc792ab6e59ce78287b1f763cb5da9ba152'
PREVIOUS_VALIDATOR_SHA='971df7bbb78ded8c216da48fc04ecb105b6b8c292f6fcbdaf3f0bfadc92f0111'
CHANGED='hcl/cognition/universal_entry.py'
PREVIOUS_FILE_SHA='d9dddfbb92074fe9392cd4147d0b61f360890e55723b568c0d123161a66ec850'
ADDED='hcl/cognition/deepseek_metered.py'

def validate_current(*,current_digest=None):
    for path,expected in ((PREVIOUS_REPORT,PREVIOUS_REPORT_SHA),(PREVIOUS_VALIDATOR,PREVIOUS_VALIDATOR_SHA)):
        if hashlib.sha256(path.read_bytes()).hexdigest()!=expected:raise ValueError('historical universal-question evidence changed')
    files={str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in Path('hcl').rglob('*.py')}
    files[CHANGED]=PREVIOUS_FILE_SHA;files.pop(ADDED,None)
    restored=hashlib.sha256(json.dumps(files,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    if restored!=json.loads(PREVIOUS_REPORT.read_text())['amended_hcl_runtime_sha256']:raise ValueError('unrelated runtime changed')
    expected=dict(schema='hcl-development-metered-universal-amendment-v1',previous_hcl_runtime_sha256=restored,
        amended_hcl_runtime_sha256=current_digest or runtime_digest(),changed_runtime_files=[CHANGED,ADDED],
        reason='BOUNDED_EXISTING_CLIENT_PORT_WITH_CONTENT_ONLY_OUTPUT',provider_calls_in_preparation=0,
        provider_spend_in_preparation_usd=0,model_planner_efficacy_verified=False,
        complete_capability_integration=False,longmemeval='SEALED_NOT_ACCESSED')
    if json.loads(REPORT.read_text())!=expected:raise ValueError('metered runtime amendment drift')
    return True
if __name__=='__main__':validate_current();print('METERED_UNIVERSAL_CURRENT_RUNTIME_PIN_PASS')
