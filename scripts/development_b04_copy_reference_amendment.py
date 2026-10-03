"""Literal last-speech repair; no adapter, scope-parser rewrite or historical rescore."""
import ast,hashlib,json
from pathlib import Path
from scripts.serious_eval_contract import runtime_digest
from scripts.development_citation_boundary_amendment import HISTORICAL_PINS as PRIOR_PINS
from scripts.development_drc008_replay import validate_archive
from scripts.development_runtime_amendment_v24 import validate_current as validate_v24

REPORT=Path('reports/HCL_B04_COPY_REFERENCE_AMENDMENT.json')
HISTORICAL_PINS=dict(PRIOR_PINS,**{'scripts/development_citation_boundary_amendment.py': '932b1175b2346819c853f15383cf79cb0aaa8e5a287480af8e050349816c31ff', 'reports/HCL_CITATION_BOUNDARY_REPAIR_AMENDMENT.json': '6b3d2d033bd72778027e06370d6d1294193f4b3827bf2feb3da19702ea13911c', 'docs/HCL_CITATION_BOUNDARY_REPAIR.md': '335089ec2416725ac0c082a75694286c7f21c73e31afd07a421256b5c6f2f87d', 'eval/b04_copy_reference_counterexamples_v1.json': '60167873ae475a197058b470a35ee813fc882db1475d7e8d58ed3d6189b3b021'})
PREVIOUS_FILE_SHA='bc0f66634caadc9303293164d8b36e431fea2f8466c4d34ea6f03f5c008e16ba'
OUTSIDE_FUNCTION_SHA='e27bc39f365349f8f427b550b246bb0a7b42a60909a0b0c017ea3d7604e04e4c'
PREVIOUS_RUNTIME='f65ebbe7d8e0ee0de54c6c81dc838af112558da4c086b24eeaa08718d660e327'


def validate_current(*,current_digest=None):
    for path,expected in HISTORICAL_PINS.items():
        if hashlib.sha256(Path(path).read_bytes()).hexdigest()!=expected:raise ValueError('historical amendment or diagnostic evidence changed')
    archive=validate_archive();validate_v24(current_digest=archive['runtime_sha256'])
    path=Path('hcl/cognition/report_provenance.py');text=path.read_bytes().decode()
    text=text.replace('from .epistemic import Attitude, MentalProposition, _query_path, check_epistemic_candidates','from .epistemic import Attitude, MentalProposition, _query_path, prepare_epistemic')
    nodes=[n for n in ast.parse(text).body if isinstance(n,ast.FunctionDef)and n.name=='prepare_reports']
    if len(nodes)!=1:raise ValueError('one report preparer required')
    node=nodes[0];lines=text.splitlines(keepends=True)
    outside=''.join(lines[:node.lineno-1]+['<PREPARE_REPORTS>\n']+lines[node.end_lineno:])
    if hashlib.sha256(outside.encode()).hexdigest()!=OUTSIDE_FUNCTION_SHA:raise ValueError('unrelated report code changed')
    files={str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in Path('hcl').rglob('*.py')}
    if str(path)not in files:raise ValueError('report module missing')
    files[str(path)]=PREVIOUS_FILE_SHA
    if hashlib.sha256(json.dumps(files,sort_keys=True,separators=(',',':')).encode()).hexdigest()!=PREVIOUS_RUNTIME:raise ValueError('unrelated runtime changed')
    expected={'schema': 'hcl-b04-copy-reference-amendment-v1', 'previous_hcl_runtime_sha256': 'f65ebbe7d8e0ee0de54c6c81dc838af112558da4c086b24eeaa08718d660e327', 'amended_hcl_runtime_sha256': 'e7154168e3765fbdd248845bce9dc08fcd2c4960950e369100a05f73ed8a7174', 'changed_runtime_files': ['hcl/cognition/report_provenance.py'], 'reason': 'RESOLVE_LITERAL_LAST_NAMED_SPEECH_BEFORE_MENTAL_FILTERING', 'semantic_preparations_per_operation': 1, 'provider_calls': 0, 'provider_spend_usd': 0, 'authorized_additional_calls': 0, 'adapter_added': False, 'grammar_expanded': False, 'source_or_report_budget_changed': False, 'scope_cue_classification_changed': False, 'known_copy_cue_scope_gap': 'FENCED_AND_NARRATOR_HYPOTHETICAL_A02_CLASSIFICATION_DEFERRED', 'historical_answers_rescored': False, 'model_selection_efficacy_verified': False, 'longmemeval': 'SEALED_NOT_ACCESSED'}
    expected['amended_hcl_runtime_sha256']=current_digest or runtime_digest()
    if json.loads(REPORT.read_text())!=expected:raise ValueError('B04 copy reference amendment drift')
    return True


if __name__=='__main__':validate_current();print('B04_COPY_REFERENCE_AND_IMMUTABLE_EVIDENCE_PASS')
