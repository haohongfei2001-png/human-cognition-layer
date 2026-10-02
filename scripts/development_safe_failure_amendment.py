"""Current safe failure diagnostics; prior experiment runtime evidence is immutable."""
import hashlib,json
from pathlib import Path
from scripts.serious_eval_contract import runtime_digest
from scripts.development_metered_universal_amendment import validate_current as validate_previous
REPORT=Path('reports/HCL_DEVELOPMENT_SAFE_FAILURE_AMENDMENT.json')
def validate_current(*,current_digest=None):
    for path,expected in [('reports/HCL_DEVELOPMENT_METERED_UNIVERSAL_AMENDMENT.json', 'dfbe6dec18199a437a87c69e03e9562ebc39acda3a6252a27d1999497c263792'), ('scripts/development_metered_universal_amendment.py', '889cdd717ef9bdf041728d4993387e48ac32bd7c4f0c097081889d78c517ba32')]:
        if hashlib.sha256(Path(path).read_bytes()).hexdigest()!=expected:raise ValueError('historical metered evidence changed')
    validate_previous(current_digest='f8e0c2c15cba4c75f314046a822aa367c450f1c480e121acad1b2ba47df08253')
    expected=dict(schema='hcl-development-safe-failure-amendment-v1',previous_hcl_runtime_sha256='f8e0c2c15cba4c75f314046a822aa367c450f1c480e121acad1b2ba47df08253',
        amended_hcl_runtime_sha256=current_digest or runtime_digest(),
        changed_runtime_files=['hcl/cognition/deepseek_metered.py','hcl/cognition/universal_entry.py'],
        reason='FIXED_ALLOWLIST_FAILURE_CODES_ONLY_NO_RAW_EXCEPTION',provider_calls_in_preparation=0,
        historical_failure_cause='UNRESOLVED_CANNOT_RETROACTIVELY_RECOVER',complete_capability_integration=False,
        model_planner_efficacy_verified=False,longmemeval='SEALED_NOT_ACCESSED')
    if json.loads(REPORT.read_text())!=expected:raise ValueError('safe failure amendment drift')
    return True
if __name__=='__main__':validate_current();print('SAFE_FAILURE_CURRENT_RUNTIME_PIN_PASS')
