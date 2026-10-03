"""Source-prefix authority for B02 access, targets and visible expressions."""
import ast,hashlib,json
from pathlib import Path
from scripts.serious_eval_contract import runtime_digest
from scripts.development_universal_agency_chain_amendment import HISTORICAL_PINS as PRIOR_PINS
from scripts.development_drc008_replay import validate_archive
from scripts.development_runtime_amendment_v24 import validate_current as validate_v24

REPORT=Path('reports/HCL_B02_ACCESS_AUTHORITY_AMENDMENT.json')
HISTORICAL_PINS=dict(PRIOR_PINS,**{'scripts/development_universal_agency_chain_amendment.py': 'bd8d54753e0f3ccdc1852ccfe9c2fc32d18484b76f6a74fe997fd9f279fac24a', 'reports/HCL_UNIVERSAL_AGENCY_CHAIN_AMENDMENT.json': '96f5b37496cf6ded56e139054a0e5a962604c94cbaa50a48da35cbdc8c262e8f', 'docs/HCL_UNIVERSAL_AGENCY_CHAIN_ENTRY.md': 'a7193694d3362d01251548de84b8f3750f0641fcf09cd0a2ec0aede97c6f6bb9', 'reports/HCL_UNIVERSAL_AGENCY_CHAIN_VALIDATION.json': 'bcb6b08ac6bcb7e3c2bbe80fe133178578a8d1068c66e95b333809f26e46577e'})
PREVIOUS_FILE_SHA='3c76779c5c0b9911e359b19ac2911ddbcbb6d0532d4f54cda4642ece4df703ad'
PREVIOUS_RUNTIME='487eb33bf9adf6312f89c7f13957a1df55ab62c7d529432bf307ecd6effc64a1'
OUTSIDE_CLASS_SHA='5f2f53e3e035d11bbefd5d072c49cd03d3de56f63eb0b05e0c9327db9cf6a2ff'


def validate_current(*,current_digest=None):
    for path,expected in HISTORICAL_PINS.items():
        if hashlib.sha256(Path(path).read_bytes()).hexdigest()!=expected:
            raise ValueError('historical amendment or diagnostic evidence changed')
    archive=validate_archive();validate_v24(current_digest=archive['runtime_sha256'])
    path=Path('hcl/cognition/communication.py');text=path.read_bytes().decode()
    nodes=[n for n in ast.parse(text).body if isinstance(n,ast.ClassDef)and n.name=='CommunicationScene']
    if len(nodes)!=1:raise ValueError('one communication scene required')
    node=nodes[0];lines=text.splitlines(keepends=True)
    outside=''.join(lines[:node.lineno-1])+'<COMMUNICATION_SCENE>'+''.join(lines[node.end_lineno:])
    if hashlib.sha256(outside.encode()).hexdigest()!=OUTSIDE_CLASS_SHA:
        raise ValueError('unrelated runtime outside reviewed scope changed')
    files={str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in Path('hcl').rglob('*.py')}
    if str(path)not in files:raise ValueError('communication module missing')
    files[str(path)]=PREVIOUS_FILE_SHA
    if hashlib.sha256(json.dumps(files,sort_keys=True,separators=(',',':')).encode()).hexdigest()!=PREVIOUS_RUNTIME:
        raise ValueError('unrelated runtime outside reviewed scope changed')
    expected={'schema': 'hcl-b02-access-authority-amendment-v1', 'previous_hcl_runtime_sha256': '487eb33bf9adf6312f89c7f13957a1df55ab62c7d529432bf307ecd6effc64a1', 'amended_hcl_runtime_sha256': 'f07df5b3402596459df4ca05b714d1d0209e8d3dd15d29a868cfca7377085e91', 'changed_runtime_files': ['hcl/cognition/communication.py'], 'reason': 'SHARED_PREFIX_A02_SCOPE_FOR_ACCESS_CUE_TARGET_AND_VISIBLE_EXPRESSION', 'selected_prefix_only': True, 'source_representation': 'EXISTING_PER_LINE_STRIP_WITH_EXACT_ORIGINAL_OCCURRENCE_MAPPING', 'shared_local_candidate_calls_per_nonempty_view': 1, 'raw_access_cue_fallback': False, 'ineligible_statements': 'ORDERED_UNTRANSMITTED_SENTINELS_NO_OLDER_FALLBACK', 'actual_resumption_preserved': True, 'original_proof_quotes_and_visible_event_identity_preserved': True, 'audit_shape_changed': False, 'native_d01_changed': False, 'semantic_parser_or_grammar_changed': False, 'source_actor_line_or_transport_budget_changed': False, 'adapter_added': False, 'provider_calls': 0, 'provider_spend_usd': 0, 'authorized_additional_calls': 0, 'historical_answers_rescored': False, 'model_selection_efficacy_verified': False, 'longmemeval': 'SEALED_NOT_ACCESSED'}
    expected['amended_hcl_runtime_sha256']=current_digest or runtime_digest()
    if json.loads(REPORT.read_text())!=expected:raise ValueError('B02 access authority amendment drift')
    return True


if __name__=='__main__':validate_current();print('B02_ACCESS_AUTHORITY_AND_IMMUTABLE_EVIDENCE_PASS')
