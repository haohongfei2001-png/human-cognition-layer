"""Current universal-question slice, with immutable previous runtime linkage."""
import hashlib
import json
from pathlib import Path
from scripts.serious_eval_contract import runtime_digest

REPORT=Path('reports/HCL_DEVELOPMENT_UNIVERSAL_QUESTION_AMENDMENT.json')
PREVIOUS_REPORT=Path('reports/HCL_DEVELOPMENT_ANSWER_BOUNDARY_AMENDMENT.json')
PREVIOUS_VALIDATOR=Path('scripts/development_answer_boundary_amendment.py')
PREVIOUS_REPORT_SHA='ed044f76c7d2b296edbbd68bbff12f924883858a6708bd550490540f4f7dbfdf'
PREVIOUS_VALIDATOR_SHA='405981b6ed8a64064bf4534942e088119da8d1b16cb798097de8a94bcf5b50da'
CHANGED='hcl/cognition/__init__.py'
PREVIOUS_INIT_SHA='bb03bb73012b237b6753a823a54cc041317f79977395c2b802d008c1532bdbb8'
ADDED=['hcl/cognition/capability_catalog.py','hcl/cognition/universal_entry.py']


def validate_current(*, current_digest=None):
    for path,expected in ((PREVIOUS_REPORT,PREVIOUS_REPORT_SHA),(PREVIOUS_VALIDATOR,PREVIOUS_VALIDATOR_SHA)):
        if hashlib.sha256(path.read_bytes()).hexdigest()!=expected:raise ValueError('prior runtime receipt or validator changed')
    prior=json.loads(PREVIOUS_REPORT.read_text())
    files={str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in Path('hcl').rglob('*.py')}
    files[CHANGED]=PREVIOUS_INIT_SHA
    for path in ADDED:files.pop(path,None)
    restored=hashlib.sha256(json.dumps(files,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    if restored!=prior['amended_hcl_runtime_sha256']:raise ValueError('unrelated prior runtime changed')
    expected=dict(schema='hcl-development-universal-question-amendment-v1',
        previous_hcl_runtime_sha256=restored,amended_hcl_runtime_sha256=current_digest or runtime_digest(),
        changed_runtime_files=[CHANGED,*ADDED],reason='ORDINARY_QUESTION_PLANNING_AND_CURRENT_C02_G02_ADAPTERS',
        model_planner_efficacy_verified=False,complete_capability_integration=False,
        provider_transport_installed=False,provider_calls=0,provider_spend_usd=0,
        historical_budget_transfer=False,longmemeval='SEALED_NOT_ACCESSED')
    if json.loads(REPORT.read_text())!=expected:raise ValueError('current universal-question amendment drift')
    return True

if __name__=='__main__':validate_current();print('UNIVERSAL_QUESTION_CURRENT_RUNTIME_PIN_PASS')
