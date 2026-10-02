"""Pin the bounded existing G01 adapter; historical paid evidence stays immutable."""
import hashlib,json
from pathlib import Path
from scripts.serious_eval_contract import runtime_digest
REPORT=Path('reports/HCL_DEVELOPMENT_UNIVERSAL_NORMATIVE_AMENDMENT.json')
def validate_current(*,current_digest=None):
    # Restore the two changed file hashes and verify the entire prior runtime.
    # Older validators are immutable; their historical evidence pins are retained
    # here because their live-tree restoration predates catalog evolution.
    for path,expected in [('reports/HCL_DEVELOPMENT_COMPLETION_METADATA_AMENDMENT.json', 'd3ede4a8d3efe3bdf0b9a62f7fdb507448574a708ff722afdfa0e5c81cea02cc'), ('reports/HCL_DEVELOPMENT_SAFE_FAILURE_AMENDMENT.json', '937147296c6f54caee65dd4b23d677112a300d98413ec4357394cdcfe55968c3'), ('reports/HCL_DEVELOPMENT_METERED_UNIVERSAL_AMENDMENT.json', 'dfbe6dec18199a437a87c69e03e9562ebc39acda3a6252a27d1999497c263792'), ('reports/HCL_DEVELOPMENT_UNIVERSAL_QUESTION_AMENDMENT.json', '08bd9a87e5672fbb41f5120aa3846cc792ab6e59ce78287b1f763cb5da9ba152'), ('scripts/development_completion_metadata_amendment.py', '9d789c1c620cb1e371664f4c76fced6066b8204c4ff530bdf0aaa243422aabf0'), ('scripts/development_safe_failure_amendment.py', 'f1c5382051616f3def2a70389a8f6f64a3551cf47978fb15e1b0164ea2bf8454'), ('scripts/development_metered_universal_amendment.py', '889cdd717ef9bdf041728d4993387e48ac32bd7c4f0c097081889d78c517ba32'), ('scripts/development_universal_question_amendment.py', '971df7bbb78ded8c216da48fc04ecb105b6b8c292f6fcbdaf3f0bfadc92f0111')]:
        if hashlib.sha256(Path(path).read_bytes()).hexdigest()!=expected:raise ValueError('historical evidence changed')
    files={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in Path('hcl').rglob('*.py')}
    files.update({'hcl/cognition/capability_catalog.py': '0ececc3aa3a4f531f8d7c437b3998f5380540104951824a68ece7ffa50079dd2', 'hcl/cognition/universal_entry.py': '78ca00253978d96afad0ab8c5bf1086515f403513d43f88a01d7cb090e37a036'})
    restored=hashlib.sha256(json.dumps(files,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    if restored!='e90e6348eabd6d478bc30c1cb5762685191ad8335aefdfb1993ad23417523f7e':raise ValueError('unrelated runtime changed')
    expected={'schema': 'hcl-development-universal-normative-amendment-v1', 'previous_hcl_runtime_sha256': 'e90e6348eabd6d478bc30c1cb5762685191ad8335aefdfb1993ad23417523f7e', 'amended_hcl_runtime_sha256': '86dadf5bbcdbbb59dce68de453ac443575c0e7772edd412d5d16f3a63599a348', 'changed_runtime_files': ['hcl/cognition/capability_catalog.py', 'hcl/cognition/universal_entry.py'], 'reason': 'EXISTING_G01_ORIGINAL_USER_CONDITION_ADAPTER', 'provider_calls_in_preparation': 0, 'provider_spend_usd': 0, 'complete_capability_integration': False, 'model_planner_efficacy_verified': False, 'responsibility_verdict_added': False, 'longmemeval': 'SEALED_NOT_ACCESSED'}
    expected['amended_hcl_runtime_sha256']=current_digest or runtime_digest()
    if json.loads(REPORT.read_text())!=expected:raise ValueError('universal normative amendment drift')
    return True
if __name__=='__main__':validate_current();print('UNIVERSAL_NORMATIVE_CURRENT_RUNTIME_PIN_PASS')
