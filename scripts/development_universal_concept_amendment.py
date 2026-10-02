"""Pin the existing G03 adapter while preserving all prior runtime/evidence guards."""
import hashlib,json
from pathlib import Path
from scripts.serious_eval_contract import runtime_digest
from scripts.development_universal_normative_amendment import validate_current as validate_previous
REPORT=Path('reports/HCL_DEVELOPMENT_UNIVERSAL_CONCEPT_AMENDMENT.json')
def validate_current(*,current_digest=None):
    for path,expected in {'scripts/development_universal_normative_amendment.py': '8130b19d3726a391fcb1851e755064d2e2cd31893116749ca5b3536bf44f9bdd', 'reports/HCL_DEVELOPMENT_UNIVERSAL_NORMATIVE_AMENDMENT.json': '4de6782122d2b35f55fa0411c5d873583e352445e2f1c7e0807715261076545e'}.items():
        if hashlib.sha256(Path(path).read_bytes()).hexdigest()!=expected:raise ValueError('historical normative evidence changed')
    validate_previous(current_digest='86dadf5bbcdbbb59dce68de453ac443575c0e7772edd412d5d16f3a63599a348')
    files={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in Path('hcl').rglob('*.py')}
    files.update({'hcl/cognition/capability_catalog.py': '068431f3c1e264ba672bb189e4e006d413236ac9bfcd3a5039ed21ef26618941', 'hcl/cognition/universal_entry.py': 'f9230ba62a8dd0125147770e899eb8a232a4674ad8b6bd0ba8c484f565d81f9d'})
    restored=hashlib.sha256(json.dumps(files,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    if restored!='86dadf5bbcdbbb59dce68de453ac443575c0e7772edd412d5d16f3a63599a348':raise ValueError('unrelated runtime changed')
    expected={'schema': 'hcl-development-universal-concept-amendment-v1', 'previous_hcl_runtime_sha256': '86dadf5bbcdbbb59dce68de453ac443575c0e7772edd412d5d16f3a63599a348', 'amended_hcl_runtime_sha256': '026c918ef8937b1a6ea287b49a9b566c0f2df5cf5905d035cf729a6a365aac52', 'changed_runtime_files': ['hcl/cognition/capability_catalog.py', 'hcl/cognition/universal_entry.py'], 'reason': 'EXISTING_G03_SINGLE_SOURCE_CONDITIONAL_CONCEPT_ADAPTER', 'provider_calls_in_preparation': 0, 'provider_spend_usd': 0, 'complete_capability_integration': False, 'model_planner_efficacy_verified': False, 'concept_grammar_changed': False, 'longmemeval': 'SEALED_NOT_ACCESSED'}
    expected['amended_hcl_runtime_sha256']=current_digest or runtime_digest()
    if json.loads(REPORT.read_text())!=expected:raise ValueError('universal concept amendment drift')
    return True
if __name__=='__main__':validate_current();print('UNIVERSAL_CONCEPT_CURRENT_RUNTIME_PIN_PASS')
