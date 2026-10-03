"""Bounded quotation/type/admission repair; historical answers remain untouched."""
import ast,hashlib,json
from pathlib import Path
from scripts.serious_eval_contract import runtime_digest
from scripts.development_answer_citation_contract_amendment import HISTORICAL_PINS as PRIOR_PINS
from scripts.development_drc008_replay import validate_archive
from scripts.development_runtime_amendment_v24 import validate_current as validate_v24

REPORT=Path('reports/HCL_CITATION_BOUNDARY_REPAIR_AMENDMENT.json')
HISTORICAL_PINS=dict(PRIOR_PINS,**{'scripts/development_answer_citation_contract_amendment.py': 'd1061f33e7c041b41cc65625a39e47d45d58533110817ff8ba5f82b60df12198', 'reports/HCL_ANSWER_CITATION_CONTRACT_AMENDMENT.json': 'f0e6cdbd13e76d7ef06580aebb634e00dbfa1fc94ec94a9e7529ff0975272ede', 'docs/HCL_ANSWER_CITATION_CONTRACT.md': '690e91ced8a17247ac49a76f5374ab20724fb66db5a8cc18982e1be038b2bfe9'})
PREVIOUS_FILES={'hcl/cognition/retained.py': '86e09696d9aca1ddbb902526fab643c02f98c52cb5cc78e01a97b13f403c5709', 'hcl/cognition/universal_entry.py': '5a41a28604bd7ae0c159882f01877c2ec13f14de5b64fb3d142a6030954e33f8'}
PREVIOUS_RUNTIME='6554c136562a112333071eda9ebb5a18bd1e51686b68a10f96647d4bf0cc331d'
SCOPED_FUNCTIONS={'hcl/cognition/retained.py': {'class_name': None, 'function_name': 'audit_original_citations', 'outside_sha256': '8b5c3bf0f7f45562c140c4c754bd3881046a80f86474ec5e4a7c3686c6b77c83'}, 'hcl/cognition/universal_entry.py': {'class_name': 'UniversalHCL', 'function_name': 'put_source', 'outside_sha256': '10b1ea1013a0d0eb1c801080d89da466144a5ca3678dd5a0057f4b2a7bf808e9'}}


def validate_current(*,current_digest=None):
    for path,expected in HISTORICAL_PINS.items():
        if hashlib.sha256(Path(path).read_bytes()).hexdigest()!=expected:
            raise ValueError('historical amendment or diagnostic evidence changed')
    archive=validate_archive();validate_v24(current_digest=archive['runtime_sha256'])
    # Preserve every byte outside the two reviewed functions, independent of
    # Python AST dump formatting. The whole-runtime restoration also preserves
    # all untouched files and membership, including the prior answer policy.
    for path,scope in SCOPED_FUNCTIONS.items():
        text=Path(path).read_bytes().decode();body=ast.parse(text).body
        if scope['class_name']:
            classes=[n for n in body if isinstance(n,ast.ClassDef)and n.name==scope['class_name']]
            if len(classes)!=1:raise ValueError('expected one scoped class')
            body=classes[0].body
        nodes=[n for n in body if isinstance(n,ast.FunctionDef)and n.name==scope['function_name']]
        if len(nodes)!=1:raise ValueError('expected one scoped function')
        node=nodes[0];lines=text.splitlines(keepends=True)
        outside=''.join(lines[:node.lineno-1]+['<AMENDED_FUNCTION>\n']+lines[node.end_lineno:])
        if hashlib.sha256(outside.encode()).hexdigest()!=scope['outside_sha256']:
            raise ValueError('unrelated code outside reviewed boundary functions changed')
    files={str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in Path('hcl').rglob('*.py')}
    if not set(PREVIOUS_FILES)<=files.keys():raise ValueError('amended runtime file missing')
    files.update(PREVIOUS_FILES)
    if hashlib.sha256(json.dumps(files,sort_keys=True,separators=(',',':')).encode()).hexdigest()!=PREVIOUS_RUNTIME:
        raise ValueError('unrelated runtime or membership changed')
    expected={'schema': 'hcl-citation-boundary-repair-amendment-v1', 'previous_hcl_runtime_sha256': '6554c136562a112333071eda9ebb5a18bd1e51686b68a10f96647d4bf0cc331d', 'amended_hcl_runtime_sha256': 'f65ebbe7d8e0ee0de54c6c81dc838af112558da4c086b24eeaa08718d660e327', 'changed_runtime_files': ['hcl/cognition/retained.py', 'hcl/cognition/universal_entry.py'], 'reason': 'STRICT_ANSWER_TYPE_OVERLAP_AMBIGUITY_AND_SOURCE_ID_ADMISSION_ALIGNMENT', 'citation_field_schema_changed': False, 'unique_quote_relocation_changed': False, 'exact_offset_disambiguation_changed': False, 'whitespace_only_mode_changed': False, 'raw_output_rewriting_added': False, 'model_or_token_settings_changed': False, 'provider_calls': 0, 'provider_spend_usd': 0, 'authorized_additional_calls': 0, 'historical_answers_rescored': False, 'answer_gain_established': False, 'longmemeval': 'SEALED_NOT_ACCESSED'}
    expected['amended_hcl_runtime_sha256']=current_digest or runtime_digest()
    if json.loads(REPORT.read_text())!=expected:raise ValueError('citation boundary repair amendment drift')
    return True


if __name__=='__main__':validate_current();print('CITATION_BOUNDARY_REPAIR_AND_IMMUTABLE_EVIDENCE_PASS')
