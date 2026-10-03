"""Bounded existing C04 ordinary adapter; native semantics and past evidence stay fixed."""
import ast,hashlib,json
from pathlib import Path
from scripts.serious_eval_contract import runtime_digest
from scripts.development_b04_scope_consumer_amendment import HISTORICAL_PINS as PRIOR_PINS
from scripts.development_drc008_replay import validate_archive
from scripts.development_runtime_amendment_v24 import validate_current as validate_v24

REPORT=Path('reports/HCL_UNIVERSAL_APPRAISAL_AMENDMENT.json')
HISTORICAL_PINS=dict(PRIOR_PINS,**{'scripts/development_b04_scope_consumer_amendment.py': '2311e5078d10928f8ab6737c11c8982d38c3ea2867ed95a336f0e8efdd88aaf7', 'reports/HCL_B04_SCOPE_CONSUMER_AMENDMENT.json': 'd24008cf903f25cbd7472671ad1dda5e52adfa40b70ea99b5dc77a23cff44921', 'docs/HCL_B04_SCOPE_CONSUMER.md': '11bf1fcd2aa8c841aa62dd5769acbc718a2d0d211bc47c21307fc750b8ccec80', 'reports/HCL_B04_SCOPE_CONSUMER_RECHECK.json': 'c895b649e0522fc92ddf94325516bd527b89145322f66c069e192e15de761190', 'reports/HCL_B04_SCOPE_CONSUMER_VALIDATION.json': 'c63dc9a011c05426f2dbd156cf8a8e44b26f0d2422ad207e4fd5b2b393d0a4ba'})
PREVIOUS_FILES={'hcl/cognition/capability_catalog.py': 'c73b50036e58daed7633bee79d42290e3f7641d58799e7cc4bee93af49435586', 'hcl/cognition/universal_entry.py': 'ab407e84fce796ddf29c1ed9cda972a47b37b3cd2f70350670a9e311bee465b8'}
PREVIOUS_RUNTIME='430d756b75eb808ba926275a1e93f08f8ffaab899053d6ad684d677ce4e18a71'


def _without_c04(text,catalog):
    tree=ast.parse(text);nodes=[]
    if catalog:
        for call in ast.walk(tree):
            if (isinstance(call,ast.Call) and isinstance(call.func,ast.Attribute)
                    and isinstance(call.func.value,ast.Name) and call.func.value.id=='_CONTRACTS'
                    and call.func.attr=='update' and len(call.args)==1 and isinstance(call.args[0],ast.Dict)):
                for key,value in zip(call.args[0].keys,call.args[0].values):
                    if isinstance(key,ast.Constant) and key.value=='C04':nodes.append((key.lineno,value.end_lineno))
    else:
        classes=[n for n in tree.body if isinstance(n,ast.ClassDef)and n.name=='UniversalHCL']
        if len(classes)!=1:raise ValueError('one universal entry required')
        methods=[n for n in classes[0].body if isinstance(n,ast.FunctionDef)and n.name=='_execute']
        if len(methods)!=1:raise ValueError('one executor required')
        for node in methods[0].body:
            test=node.test if isinstance(node,ast.If) else None
            if (isinstance(test,ast.Compare) and isinstance(test.left,ast.Name) and test.left.id=='cid'
                    and len(test.ops)==1 and isinstance(test.ops[0],ast.Eq) and len(test.comparators)==1
                    and isinstance(test.comparators[0],ast.Constant) and test.comparators[0].value=='C04'):
                nodes.append((node.lineno,node.end_lineno))
    if len(nodes)!=1:raise ValueError('exactly one added C04 contract or dispatch required')
    first,last=nodes[0];lines=text.splitlines(keepends=True)
    return ''.join(lines[:first-1]+lines[last:])


def validate_current(*,current_digest=None):
    for path,expected in HISTORICAL_PINS.items():
        if hashlib.sha256(Path(path).read_bytes()).hexdigest()!=expected:
            raise ValueError('historical amendment or diagnostic evidence changed')
    archive=validate_archive();validate_v24(current_digest=archive['runtime_sha256'])
    for path,expected in PREVIOUS_FILES.items():
        text=Path(path).read_bytes().decode()
        if hashlib.sha256(_without_c04(text,'capability_catalog' in path).encode()).hexdigest()!=expected:
            raise ValueError('unrelated runtime outside reviewed scope changed')
    files={str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in Path('hcl').rglob('*.py')}
    if not set(PREVIOUS_FILES)<=files.keys():raise ValueError('amended runtime file missing')
    files.update(PREVIOUS_FILES)
    if hashlib.sha256(json.dumps(files,sort_keys=True,separators=(',',':')).encode()).hexdigest()!=PREVIOUS_RUNTIME:
        raise ValueError('unrelated runtime outside reviewed scope changed')
    expected={'schema': 'hcl-universal-appraisal-amendment-v1', 'previous_hcl_runtime_sha256': '430d756b75eb808ba926275a1e93f08f8ffaab899053d6ad684d677ce4e18a71', 'amended_hcl_runtime_sha256': 'd5d9fc0cdb30eb4e8d828a0e7e04616e0737b2bb4ba2714952c0428c333ac551', 'changed_runtime_files': ['hcl/cognition/capability_catalog.py', 'hcl/cognition/universal_entry.py'], 'reason': 'RETAINED_C04_COMPLETE_PAYLOAD_SINGLE_SOURCE_ORDINARY_ENTRY', 'question_origin': 'OPERATION_QUESTION_WITH_ORIGINAL_OUTER_TASK_PRESERVED', 'checked_treatment_basis': 'NONEMPTY_NATIVE_CURRENT_C04_EVIDENCE_NOT_AGENCY_CLAIMS', 'complete_native_payload_and_policy_preserved': True, 'shared_source_revisions_and_support_claim_ids': True, 'native_parser_or_grammar_changed': False, 'source_or_transport_budget_changed': False, 'model_or_token_settings_changed': False, 'new_provider_subcalls': False, 'provider_calls': 0, 'provider_spend_usd': 0, 'authorized_additional_calls': 0, 'historical_answers_rescored': False, 'model_selection_efficacy_verified': False, 'b04_entry_adapter': 'DEFERRED_COMPLETE_EVIDENCE_TRANSPORT_GATE', 'longmemeval': 'SEALED_NOT_ACCESSED'}
    expected['amended_hcl_runtime_sha256']=current_digest or runtime_digest()
    if json.loads(REPORT.read_text())!=expected:raise ValueError('universal appraisal amendment drift')
    return True


if __name__=='__main__':validate_current();print('UNIVERSAL_APPRAISAL_AND_IMMUTABLE_EVIDENCE_PASS')
