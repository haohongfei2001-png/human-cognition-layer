"""Bounded existing D02 finite acknowledgment; target authority and past evidence stay fixed."""
import ast,hashlib,json
from pathlib import Path
from scripts.serious_eval_contract import runtime_digest
from scripts.development_d01_source_line_amendment import HISTORICAL_PINS as PRIOR_PINS
from scripts.development_drc008_replay import validate_archive
from scripts.development_runtime_amendment_v24 import validate_current as validate_v24

REPORT=Path('reports/HCL_UNIVERSAL_UNDERSTANDING_AMENDMENT.json')
HISTORICAL_PINS=dict(PRIOR_PINS,**{'scripts/development_d01_source_line_amendment.py': '3ca92ddb111a9c8b984ca8d89f04051d8003c0a86fb8773ea533061ad499f314', 'reports/HCL_D01_SOURCE_LINE_BOUNDARY_AMENDMENT.json': 'ddd5662bffceeb4fa8b33926d6aab31d76629079ef999a2720d0c5c297bb92b2', 'docs/HCL_D01_SOURCE_LINE_BOUNDARY.md': '2007ac887736fc6445721b6137993948d500b6cc13afb5b98feb1dd73b349682', 'reports/HCL_D01_SOURCE_LINE_BOUNDARY_VALIDATION.json': '2110c6302f3d5a7696a1c3c1eed2aefd280675e1da1f8953412bcaffcee1b436', 'reports/HCL_D01_SOURCE_LINE_BOUNDARY_RECHECK.json': 'a684570886e57e79cdebb142005dd8cdf53d879902ea7205611dea6b82027903'})
PREVIOUS_FILES={'hcl/cognition/capability_catalog.py': 'a36afdb69c467fa26cfc7c0de8eb30b3d4de1fa010ccb6b582378b72169e46f4', 'hcl/cognition/universal_entry.py': 'e02ef0b0b3d4a557e0b00c455e4a1f028c6f4447bcd5f88a6fffa39f1acec23f'}
PREVIOUS_RUNTIME='e1ce80691173efd9e76b5f3466d9d573fc9da7e5c7c125ce8003a8383118ca2d'


def _without_d02(text,catalog):
    tree=ast.parse(text);nodes=[]
    if catalog:
        for call in ast.walk(tree):
            if (isinstance(call,ast.Call) and isinstance(call.func,ast.Attribute)
                    and isinstance(call.func.value,ast.Name) and call.func.value.id=='_CONTRACTS'
                    and call.func.attr=='update' and len(call.args)==1 and isinstance(call.args[0],ast.Dict)):
                for key,value in zip(call.args[0].keys,call.args[0].values):
                    if isinstance(key,ast.Constant) and key.value=='D02':nodes.append((key.lineno,value.end_lineno))
    else:
        classes=[n for n in tree.body if isinstance(n,ast.ClassDef)and n.name=='UniversalHCL']
        if len(classes)!=1:raise ValueError('one universal entry required')
        methods=[n for n in classes[0].body if isinstance(n,ast.FunctionDef)and n.name=='_execute']
        if len(methods)!=1:raise ValueError('one executor required')
        for node in methods[0].body:
            test=node.test if isinstance(node,ast.If) else None
            if (isinstance(test,ast.Compare) and isinstance(test.left,ast.Name) and test.left.id=='cid'
                    and len(test.ops)==1 and isinstance(test.ops[0],ast.Eq) and len(test.comparators)==1
                    and isinstance(test.comparators[0],ast.Constant) and test.comparators[0].value=='D02'):
                nodes.append((node.lineno,node.end_lineno))
    if len(nodes)!=1:raise ValueError('exactly one added D02 contract or dispatch required')
    first,last=nodes[0];lines=text.splitlines(keepends=True)
    return ''.join(lines[:first-1]+lines[last:])


def validate_current(*,current_digest=None):
    for path,expected in HISTORICAL_PINS.items():
        if hashlib.sha256(Path(path).read_bytes()).hexdigest()!=expected:
            raise ValueError('historical amendment or diagnostic evidence changed')
    archive=validate_archive();validate_v24(current_digest=archive['runtime_sha256'])
    for path,expected in PREVIOUS_FILES.items():
        text=Path(path).read_bytes().decode()
        if hashlib.sha256(_without_d02(text,'capability_catalog' in path).encode()).hexdigest()!=expected:
            raise ValueError('unrelated runtime outside reviewed scope changed')
    files={str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in Path('hcl').rglob('*.py')}
    if not set(PREVIOUS_FILES)<=files.keys():raise ValueError('amended runtime file missing')
    files.update(PREVIOUS_FILES)
    if hashlib.sha256(json.dumps(files,sort_keys=True,separators=(',',':')).encode()).hexdigest()!=PREVIOUS_RUNTIME:
        raise ValueError('unrelated runtime outside reviewed scope changed')
    expected={'schema': 'hcl-universal-understanding-amendment-v1', 'previous_hcl_runtime_sha256': 'e1ce80691173efd9e76b5f3466d9d573fc9da7e5c7c125ce8003a8383118ca2d', 'amended_hcl_runtime_sha256': '071d5327b32903c96b6e397103b8715acd82a4974af4195e32f49f35ddd3b53d', 'changed_runtime_files': ['hcl/cognition/capability_catalog.py', 'hcl/cognition/universal_entry.py'], 'reason': 'RETAINED_D02_TARGET_BOUND_FINITE_ACKNOWLEDGMENT_SINGLE_SOURCE_ENTRY', 'question_origin': 'OPERATION_QUESTION_WITH_ORIGINAL_OUTER_TASK_PRESERVED', 'checked_treatment_basis': 'EXACT_CHAIN_OR_EXPLICIT_DOUBT_CONTENT_MATCHES_THIS_SUPPORTED_NATIVE_SUMMARY_TARGET', 'summary_alone_is_treatment': False, 'complete_native_payload_and_policy_preserved': True, 'shared_source_revisions_and_all_support_claim_ids': True, 'receipt_link_times_and_historical_meanings_preserved': True, 'later_receipt_backfills_earlier_links': False, 'private_comprehension_or_common_knowledge_established': False, 'supported_source_separators': ['LF', 'CRLF'], 'other_splitlines_separators': 'REFUSE_BEFORE_NATIVE_WITH_ORIGINAL_SOURCE_UNCHANGED', 'retained_native_format_gap': 'UNREPAIRED_OUTSIDE_BOUNDED_ADAPTER', 'native_branch_specific_receipt_validation_preserved': True, 'native_parser_or_grammar_changed': False, 'source_or_transport_budget_changed': False, 'model_or_token_settings_changed': False, 'new_provider_subcalls': False, 'provider_calls': 0, 'provider_spend_usd': 0, 'authorized_additional_calls': 0, 'historical_answers_rescored': False, 'model_selection_efficacy_verified': False, 'b04_entry_adapter': 'DEFERRED_COMPLETE_EVIDENCE_TRANSPORT_GATE', 'longmemeval': 'SEALED_NOT_ACCESSED'}
    expected['amended_hcl_runtime_sha256']=current_digest or runtime_digest()
    if json.loads(REPORT.read_text())!=expected:raise ValueError('universal understanding amendment drift')
    return True


if __name__=='__main__':validate_current();print('UNIVERSAL_UNDERSTANDING_AND_IMMUTABLE_EVIDENCE_PASS')
