"""Shared structural scope isolation; immutable past evidence and exact source anchors."""
import ast,hashlib,json
from pathlib import Path
from scripts.serious_eval_contract import runtime_digest
from scripts.development_b04_copy_reference_amendment import HISTORICAL_PINS as PRIOR_PINS
from scripts.development_drc008_replay import validate_archive
from scripts.development_runtime_amendment_v24 import validate_current as validate_v24

REPORT=Path('reports/HCL_A02_STRUCTURAL_SCOPE_AMENDMENT.json')
HISTORICAL_PINS=dict(PRIOR_PINS,**{'scripts/development_b04_copy_reference_amendment.py': '0bbd46429a7c45c4d0e9f8349fd96849fa2e223df1b49c2da1c6a3bb54555b2a', 'reports/HCL_B04_COPY_REFERENCE_AMENDMENT.json': 'c36e6f2ad6ee31021dbe9e81278c9797231c70bce1a0f252d9c7815b288eed04', 'docs/HCL_B04_COPY_REFERENCE_REPAIR.md': '34881ac5cc79a1834b60806610a942fc06bf920304948a97c13787fc8fcc23b8', 'eval/a02_scope_proposal_v1.json': 'd17355a0da81507560660ab24e01c072c1758ff30c5b5920ff762876c627e16a', 'eval/a02_scope_boundary_review_v1.json': '7dd1904a7c832b02fc7f4f1fc807e0c96054f23ad99496cef256af7908461290'})
PREVIOUS_FILE_SHA='6232c46532cf7943d2dc30fcbd3587c8e28f7091c54a9fb9b8f35ba4a5bd97c3'
PREVIOUS_RUNTIME='e7154168e3765fbdd248845bce9dc08fcd2c4960950e369100a05f73ed8a7174'
OUTSIDE_SCOPE_SHA='8367179084c73b4d8494c2d72df0801f2ff8b43d0d1ef3b745c0c780371ef9d2'
SCOPED_FUNCTIONS=('_narration_context','_narrator_scene_cues','_narrator_report_candidates','_local_candidates')


def validate_current(*,current_digest=None):
    for path,expected in HISTORICAL_PINS.items():
        if hashlib.sha256(Path(path).read_bytes()).hexdigest()!=expected:
            raise ValueError('historical amendment or diagnostic evidence changed')
    archive=validate_archive();validate_v24(current_digest=archive['runtime_sha256'])
    path=Path('hcl/cognition/semantic.py');text=path.read_bytes().decode()
    body=ast.parse(text).body
    nodes=[n for n in body if isinstance(n,ast.FunctionDef)and n.name in SCOPED_FUNCTIONS]
    if tuple(n.name for n in nodes)!=SCOPED_FUNCTIONS:
        raise ValueError('reviewed A02 scope functions required once in order')
    between=[n for n in body if nodes[0].lineno<=n.lineno<=nodes[-1].end_lineno]
    if between!=nodes:raise ValueError('unexpected declaration within A02 scope boundary')
    lines=text.splitlines(keepends=True)
    outside=''.join(lines[:nodes[0].lineno-1])+ '<REVIEWED_A02_SCOPE_FUNCTIONS>'+''.join(lines[nodes[-1].end_lineno:])
    if hashlib.sha256(outside.encode()).hexdigest()!=OUTSIDE_SCOPE_SHA:
        raise ValueError('unrelated semantic code outside reviewed scope changed')
    files={str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in Path('hcl').rglob('*.py')}
    if str(path)not in files:raise ValueError('semantic module missing')
    files[str(path)]=PREVIOUS_FILE_SHA
    if hashlib.sha256(json.dumps(files,sort_keys=True,separators=(',',':')).encode()).hexdigest()!=PREVIOUS_RUNTIME:
        raise ValueError('unrelated runtime or membership changed')
    expected={'schema': 'hcl-a02-structural-scope-amendment-v1', 'previous_hcl_runtime_sha256': 'e7154168e3765fbdd248845bce9dc08fcd2c4960950e369100a05f73ed8a7174', 'amended_hcl_runtime_sha256': 'd1964a8f2e47472a24dbcf55b67c89ae9a781122c4f5a95013d65f07669d16ab', 'changed_runtime_files': ['hcl/cognition/semantic.py'], 'reason': 'SHARED_OFFSET_PRESERVING_STRUCTURAL_CONTAINMENT_AND_NARRATION_SCOPE', 'source_text_or_candidate_schema_changed': False, 'formatting_establishes_hypothetical_world': False, 'explicit_actual_transcript_admission_added': False, 'candidate_matcher_grammar_changed': False, 'structural_container_grammar': 'DOUBLE_QUOTES_NESTED_SQUARE_BRACKETS_LINE_BOUNDED_BACKTICK_FENCES', 'b04_consumer_changed': False, 'adapter_added': False, 'source_candidate_or_transport_budget_changed': False, 'provider_calls': 0, 'provider_spend_usd': 0, 'authorized_additional_calls': 0, 'historical_answers_rescored': False, 'model_selection_efficacy_verified': False, 'longmemeval': 'SEALED_NOT_ACCESSED'}
    expected['amended_hcl_runtime_sha256']=current_digest or runtime_digest()
    if json.loads(REPORT.read_text())!=expected:raise ValueError('A02 structural scope amendment drift')
    return True


if __name__=='__main__':validate_current();print('A02_STRUCTURAL_SCOPE_AND_IMMUTABLE_EVIDENCE_PASS')
