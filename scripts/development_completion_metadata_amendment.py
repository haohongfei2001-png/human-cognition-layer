"""Pin safe completion metadata without upgrading previous run evidence."""
import hashlib,json
from pathlib import Path
from scripts.serious_eval_contract import runtime_digest
from scripts.development_safe_failure_amendment import validate_current as validate_previous
REPORT=Path('reports/HCL_DEVELOPMENT_COMPLETION_METADATA_AMENDMENT.json')
def validate_current(*,current_digest=None):
    for path,expected in [('reports/HCL_DEVELOPMENT_SAFE_FAILURE_AMENDMENT.json', '937147296c6f54caee65dd4b23d677112a300d98413ec4357394cdcfe55968c3'), ('scripts/development_safe_failure_amendment.py', 'f1c5382051616f3def2a70389a8f6f64a3551cf47978fb15e1b0164ea2bf8454')]:
        if hashlib.sha256(Path(path).read_bytes()).hexdigest()!=expected:raise ValueError('historical safe failure evidence changed')
    validate_previous(current_digest='5056a61bc1baa2c81a4c913c66c7e4cf1c9964df9c2cd41d9bea807a2afe5cb7')
    expected=dict(schema='hcl-development-completion-metadata-amendment-v1',previous_hcl_runtime_sha256='5056a61bc1baa2c81a4c913c66c7e4cf1c9964df9c2cd41d9bea807a2afe5cb7',
        amended_hcl_runtime_sha256=current_digest or runtime_digest(),
        changed_runtime_files=['hcl/cognition/deepseek_metered.py','hcl/cognition/universal_entry.py'],
        reason='BOUNDED_FINISH_ENUM_AND_VALIDATED_USAGE_ON_REJECTED_COMPLETION',provider_calls_in_preparation=0,
        historical_finish_reason='NOT_RETAINED_CANNOT_RECOVER',complete_capability_integration=False,
        model_planner_efficacy_verified=False,longmemeval='SEALED_NOT_ACCESSED')
    if json.loads(REPORT.read_text())!=expected:raise ValueError('completion metadata amendment drift')
    return True
if __name__=='__main__':validate_current();print('COMPLETION_METADATA_CURRENT_RUNTIME_PIN_PASS')
