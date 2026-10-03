"""Exact A02 copy-cue admission and occurrence-bound provenance dependencies."""
import ast,hashlib,json
from pathlib import Path
from scripts.serious_eval_contract import runtime_digest
from scripts.development_a02_structural_scope_amendment import HISTORICAL_PINS as PRIOR_PINS
from scripts.development_drc008_replay import validate_archive
from scripts.development_runtime_amendment_v24 import validate_current as validate_v24

REPORT=Path('reports/HCL_B04_SCOPE_CONSUMER_AMENDMENT.json')
HISTORICAL_PINS=dict(PRIOR_PINS,**{'scripts/development_a02_structural_scope_amendment.py': '1d7730f19f5b4e1b94f97e829e8bbbc4b61720976ed7d50b2d275ee8da0317de', 'reports/HCL_A02_STRUCTURAL_SCOPE_AMENDMENT.json': '88ac452b14255b051eda6abae0272437036f68066da156f6341c9ea41073ec25', 'docs/HCL_A02_STRUCTURAL_SCOPE.md': '99014b97aff856edf7086425e3530562fc5b6a92c9acefa54ec7794f9fe615ca', 'reports/HCL_A02_RETAINED_SCOPE_RECHECK.json': '7f51056624de994f9ac356178ca2a4b560625359e15aee0a888266e6d78d097e', 'reports/HCL_RETAINED_ENTRY_SCOPE_BLOCKERS.json': 'd261173c5ca32363010e0d8571682f18d3660236ba1a80e0b1da710f9d0be06b', 'reports/HCL_A02_STRUCTURAL_SCOPE_CANDIDATE.json': 'c5c907e1201acf9667d50d592eee582a8bdb4d00ee2f4066fb06968d0bca3931', 'reports/HCL_A02_STRUCTURAL_SCOPE_VALIDATION.json': '276d0e4f1dd0fc824a74ec3bb356e2ab573a5a46100d9fef0984f85fbd1c5817', 'docs/HCL_A02_STRUCTURAL_SCOPE_CANDIDATE.md': '50494f2d8ec68e0005324a2bb49659e0a7e16703b3bc21ee756726b2a590e6b6'})
PREVIOUS_FILE_SHA='d2ad5d1119a75a8809027bbefa0489bccfd5beaca2b5d6d7f9673033300dd9b2'
PREVIOUS_RUNTIME='f02e86a390ff4935851e9da28fad127d93379f2631a768072e2f7d4103c81c57'
OUTSIDE_FUNCTION_SHA='2cd12abb2e705d69c886d7dfffe29d16446337e0d7c81fce684a147318ea46ad'


def validate_current(*,current_digest=None):
    for path,expected in HISTORICAL_PINS.items():
        if hashlib.sha256(Path(path).read_bytes()).hexdigest()!=expected:
            raise ValueError('historical amendment or diagnostic evidence changed')
    archive=validate_archive();validate_v24(current_digest=archive['runtime_sha256'])
    path=Path('hcl/cognition/report_provenance.py');text=path.read_bytes().decode()
    nodes=[n for n in ast.parse(text).body if isinstance(n,ast.FunctionDef)and n.name=='prepare_reports']
    if len(nodes)!=1:raise ValueError('one report preparer required')
    node=nodes[0];lines=text.splitlines(keepends=True)
    outside=''.join(lines[:node.lineno-1])+'<PREPARE_REPORTS>'+''.join(lines[node.end_lineno:])
    if hashlib.sha256(outside.encode()).hexdigest()!=OUTSIDE_FUNCTION_SHA:
        raise ValueError('unrelated runtime outside reviewed scope changed')
    files={str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in Path('hcl').rglob('*.py')}
    if str(path)not in files:raise ValueError('report module missing')
    files[str(path)]=PREVIOUS_FILE_SHA
    if hashlib.sha256(json.dumps(files,sort_keys=True,separators=(',',':')).encode()).hexdigest()!=PREVIOUS_RUNTIME:
        raise ValueError('unrelated runtime outside reviewed scope changed')
    expected={'schema': 'hcl-b04-scope-consumer-amendment-v1', 'previous_hcl_runtime_sha256': 'f02e86a390ff4935851e9da28fad127d93379f2631a768072e2f7d4103c81c57', 'amended_hcl_runtime_sha256': '430d756b75eb808ba926275a1e93f08f8ffaab899053d6ad684d677ce4e18a71', 'changed_runtime_files': ['hcl/cognition/report_provenance.py'], 'reason': 'EXACT_ELIGIBLE_A02_COPY_CUE_OCCURRENCE_AND_CONJUNCTIVE_DEPENDENCIES', 'semantic_preparations_per_operation': 1, 'source_revision_and_full_line_span_required': True, 'bounded_literal_narrator_source_report_required': True, 'cue_and_both_antecedents_required': True, 'repeated_cue_occurrences_have_distinct_relation_ids': True, 'unsupported_cue_raw_fallback': False, 'latest_utterance_behavior_changed': False, 'candidate_or_copy_grammar_changed': False, 'source_or_transport_budget_changed': False, 'adapter_added': False, 'provider_calls': 0, 'provider_spend_usd': 0, 'authorized_additional_calls': 0, 'historical_answers_rescored': False, 'model_selection_efficacy_verified': False, 'longmemeval': 'SEALED_NOT_ACCESSED'}
    expected['amended_hcl_runtime_sha256']=current_digest or runtime_digest()
    if json.loads(REPORT.read_text())!=expected:raise ValueError('B04 scope consumer amendment drift')
    return True


if __name__=='__main__':validate_current();print('B04_SCOPE_CONSUMER_AND_IMMUTABLE_EVIDENCE_PASS')
