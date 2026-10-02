"""Pin bounded G05 integration without changing retained logic or historical evidence."""
import hashlib
import json
from pathlib import Path
from scripts.serious_eval_contract import runtime_digest
from scripts.development_universal_argument_amendment import validate_current as validate_previous
from scripts.development_universal_argument_amendment import HISTORICAL_PINS as PRIOR_PINS

REPORT=Path('reports/HCL_DEVELOPMENT_UNIVERSAL_SENSITIVITY_AMENDMENT.json')
HISTORICAL_PINS = dict(PRIOR_PINS, **{'scripts/development_universal_argument_amendment.py': '2519c6dc94af285c999bf7c47c493500cb6a06e766a93398433c6d0000542067', 'reports/HCL_DEVELOPMENT_UNIVERSAL_ARGUMENT_AMENDMENT.json': '03cd3631279947a6a50712b4915e4db92477cbfc197ce13b1ffbf0ea817941d0'})
PREVIOUS_FILES = {'hcl/cognition/capability_catalog.py': '06f7743b44989547f21c3980e49e46606fef99e6b75067401426925e31c9050d', 'hcl/cognition/universal_entry.py': '30602af01a2ab784078e02cafe3e0d4f7f40902f9d70c8368405e3f9e8866ede'}
PREVIOUS_RUNTIME = 'eb1d5fad80254bf7e546e41595509713dc4167bf4c7004556d076bf0bbaf7e09'


def validate_current(*,current_digest=None):
    for path,expected in HISTORICAL_PINS.items():
        if hashlib.sha256(Path(path).read_bytes()).hexdigest()!=expected:
            raise ValueError('historical amendment script or report changed')
    # The preceding validator masks these same dispatch/catalog paths, checks
    # its earlier argument repair, and verifies the entire consumed archive chain.
    validate_previous(current_digest=PREVIOUS_RUNTIME)
    files={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in Path('hcl').rglob('*.py')}
    if not set(PREVIOUS_FILES)<=files.keys():raise ValueError('amended runtime file missing')
    files.update(PREVIOUS_FILES)
    restored=hashlib.sha256(json.dumps(files,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    if restored!=PREVIOUS_RUNTIME:raise ValueError('unrelated runtime or membership changed')
    expected={'schema': 'hcl-development-universal-sensitivity-amendment-v1', 'previous_hcl_runtime_sha256': 'eb1d5fad80254bf7e546e41595509713dc4167bf4c7004556d076bf0bbaf7e09', 'amended_hcl_runtime_sha256': 'ad67e85c9bd00cb23dd61825bf7c35790f72282754574da19612435e96839cfe', 'changed_runtime_files': ['hcl/cognition/capability_catalog.py', 'hcl/cognition/universal_entry.py'], 'reason': 'EXISTING_G05_SINGLE_SOURCE_ORIGINAL_REQUEST_CONDITIONAL_ADAPTER', 'provider_calls_in_preparation': 0, 'provider_spend_usd': 0, 'complete_capability_integration': False, 'model_planner_efficacy_verified': False, 'sensitivity_grammar_changed': False, 'source_mutation_added': False, 'verdict_added': False, 'longmemeval': 'SEALED_NOT_ACCESSED'}
    expected['amended_hcl_runtime_sha256']=current_digest or runtime_digest()
    if json.loads(REPORT.read_text())!=expected:raise ValueError('universal sensitivity amendment drift')
    return True


if __name__=='__main__':validate_current();print('UNIVERSAL_SENSITIVITY_CURRENT_RUNTIME_AND_HISTORICAL_CHAIN_PASS')
