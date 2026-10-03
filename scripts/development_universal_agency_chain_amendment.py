"""Bounded existing C05 conditional chain; original-time authority and past evidence stay fixed."""
import ast,hashlib,json
from pathlib import Path
from scripts.serious_eval_contract import runtime_digest
from scripts.development_universal_appraisal_amendment import HISTORICAL_PINS as PRIOR_PINS
from scripts.development_drc008_replay import validate_archive
from scripts.development_runtime_amendment_v24 import validate_current as validate_v24

REPORT=Path('reports/HCL_UNIVERSAL_AGENCY_CHAIN_AMENDMENT.json')
HISTORICAL_PINS=dict(PRIOR_PINS,**{'scripts/development_universal_appraisal_amendment.py': '037677a60c3e6a7c54cf3a171bcfddee5816d23875bf3ac38f2717900e655fca', 'reports/HCL_UNIVERSAL_APPRAISAL_AMENDMENT.json': 'dbf786756495dccd51faa1881da20bcb286af29b4fd506849affb37d32b418d6', 'docs/HCL_UNIVERSAL_APPRAISAL_ENTRY.md': '760c3a1c3a2f22a66fa4178d7424d0cda149e02dad30c89bf6f3f43c25e6b0e2', 'reports/HCL_UNIVERSAL_APPRAISAL_VALIDATION.json': '8c2e27f8d949e21ae636f3a3e9dc789041f5a587a58f6b071c66304c075fe04b'})
PREVIOUS_FILES={'hcl/cognition/capability_catalog.py': 'dce11978833ea54489a5277bb7e96934431b4d84af6a5a7ea770dcba00a2e669', 'hcl/cognition/universal_entry.py': 'b27d243fcfa5e59621b2b5521b4e8df14b13452b418b5d939b94ef6a0c06a656'}
PREVIOUS_RUNTIME='d5d9fc0cdb30eb4e8d828a0e7e04616e0737b2bb4ba2714952c0428c333ac551'


def _without_c05(text,catalog):
    tree=ast.parse(text);nodes=[]
    if catalog:
        for call in ast.walk(tree):
            if (isinstance(call,ast.Call) and isinstance(call.func,ast.Attribute)
                    and isinstance(call.func.value,ast.Name) and call.func.value.id=='_CONTRACTS'
                    and call.func.attr=='update' and len(call.args)==1 and isinstance(call.args[0],ast.Dict)):
                for key,value in zip(call.args[0].keys,call.args[0].values):
                    if isinstance(key,ast.Constant) and key.value=='C05':nodes.append((key.lineno,value.end_lineno))
    else:
        classes=[n for n in tree.body if isinstance(n,ast.ClassDef)and n.name=='UniversalHCL']
        if len(classes)!=1:raise ValueError('one universal entry required')
        methods=[n for n in classes[0].body if isinstance(n,ast.FunctionDef)and n.name=='_execute']
        if len(methods)!=1:raise ValueError('one executor required')
        for node in methods[0].body:
            test=node.test if isinstance(node,ast.If) else None
            if (isinstance(test,ast.Compare) and isinstance(test.left,ast.Name) and test.left.id=='cid'
                    and len(test.ops)==1 and isinstance(test.ops[0],ast.Eq) and len(test.comparators)==1
                    and isinstance(test.comparators[0],ast.Constant) and test.comparators[0].value=='C05'):
                nodes.append((node.lineno,node.end_lineno))
    if len(nodes)!=1:raise ValueError('exactly one added C05 contract or dispatch required')
    first,last=nodes[0];lines=text.splitlines(keepends=True)
    return ''.join(lines[:first-1]+lines[last:])


def validate_current(*,current_digest=None):
    for path,expected in HISTORICAL_PINS.items():
        if hashlib.sha256(Path(path).read_bytes()).hexdigest()!=expected:
            raise ValueError('historical amendment or diagnostic evidence changed')
    archive=validate_archive();validate_v24(current_digest=archive['runtime_sha256'])
    for path,expected in PREVIOUS_FILES.items():
        text=Path(path).read_bytes().decode()
        if hashlib.sha256(_without_c05(text,'capability_catalog' in path).encode()).hexdigest()!=expected:
            raise ValueError('unrelated runtime outside reviewed scope changed')
    files={str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in Path('hcl').rglob('*.py')}
    if not set(PREVIOUS_FILES)<=files.keys():raise ValueError('amended runtime file missing')
    files.update(PREVIOUS_FILES)
    if hashlib.sha256(json.dumps(files,sort_keys=True,separators=(',',':')).encode()).hexdigest()!=PREVIOUS_RUNTIME:
        raise ValueError('unrelated runtime outside reviewed scope changed')
    expected={'schema': 'hcl-universal-agency-chain-amendment-v1', 'previous_hcl_runtime_sha256': 'd5d9fc0cdb30eb4e8d828a0e7e04616e0737b2bb4ba2714952c0428c333ac551', 'amended_hcl_runtime_sha256': '34d16213417405ae402bc938af7f70272fd54b2393bc6a7d9ea04489e74494ad', 'changed_runtime_files': ['hcl/cognition/capability_catalog.py', 'hcl/cognition/universal_entry.py'], 'reason': 'RETAINED_C05_COMPLETE_CONDITIONAL_CHAIN_SINGLE_SOURCE_ENTRY', 'question_origin': 'OPERATION_QUESTION_WITH_ORIGINAL_OUTER_TASK_PRESERVED', 'checked_treatment_basis': 'NATIVE_CHECKED_CONDITIONAL_CHAIN_WITH_NONEMPTY_EXPLANATIONS', 'complete_native_payload_and_policy_preserved': True, 'shared_source_revisions_and_all_support_claim_ids': True, 'action_prefix_original_source_version_preserved': True, 'later_belief_backfills_action': False, 'existing_workspace_full_source_local_preparations': 5, 'existing_workspace_derived_prefix_local_preparations': 2, 'parsing_count_scope': 'CANONICAL_NINE_LINE_ACTION_PRESENT_FIXTURE', 'global_cache_or_workspace_changed': False, 'native_parser_or_grammar_changed': False, 'source_or_transport_budget_changed': False, 'model_or_token_settings_changed': False, 'new_provider_subcalls': False, 'provider_calls': 0, 'provider_spend_usd': 0, 'authorized_additional_calls': 0, 'historical_answers_rescored': False, 'model_selection_efficacy_verified': False, 'b04_entry_adapter': 'DEFERRED_COMPLETE_EVIDENCE_TRANSPORT_GATE', 'longmemeval': 'SEALED_NOT_ACCESSED'}
    expected['amended_hcl_runtime_sha256']=current_digest or runtime_digest()
    if json.loads(REPORT.read_text())!=expected:raise ValueError('universal agency chain amendment drift')
    return True


if __name__=='__main__':validate_current();print('UNIVERSAL_AGENCY_CHAIN_AND_IMMUTABLE_EVIDENCE_PASS')
