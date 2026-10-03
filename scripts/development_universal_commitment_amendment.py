"""Bounded existing D01 lifecycle; source authority and past evidence stay fixed."""
import ast,hashlib,json
from pathlib import Path
from scripts.serious_eval_contract import runtime_digest
from scripts.development_b02_access_authority_amendment import HISTORICAL_PINS as PRIOR_PINS
from scripts.development_drc008_replay import validate_archive
from scripts.development_runtime_amendment_v24 import validate_current as validate_v24

REPORT=Path('reports/HCL_UNIVERSAL_COMMITMENT_AMENDMENT.json')
HISTORICAL_PINS=dict(PRIOR_PINS,**{'scripts/development_b02_access_authority_amendment.py': '3659edad4bcc8401968d3d877aa7f057a80a7574bf39ad6ed0238e0a791ac35f', 'reports/HCL_B02_ACCESS_AUTHORITY_AMENDMENT.json': '2b5ce20c056fa524dc776e788bb1ec90d98be017faba7efe1ab43e68266bfae4', 'docs/HCL_B02_ACCESS_AUTHORITY.md': '7672ea1d0c0033785b319c2e61cf652bcdcf87c6447ea1b581acea421d162459', 'reports/HCL_B02_ACCESS_AUTHORITY_VALIDATION.json': '8200934d203da4ca03bdf2617a245592c5f15208ecfc2f8489764097c8466429'})
PREVIOUS_FILES={'hcl/cognition/capability_catalog.py': 'c5a5532997017ca63eb0b83ba107fc63f985ffac84438c2f0a147893a79cd84b', 'hcl/cognition/universal_entry.py': 'faf90e9b4b9194e9954ae506dda1d8298797a6bf855fdfee8c607e8ad93660f5'}
PREVIOUS_RUNTIME='f07df5b3402596459df4ca05b714d1d0209e8d3dd15d29a868cfca7377085e91'


def _without_d01(text,catalog):
    tree=ast.parse(text);nodes=[]
    if catalog:
        for call in ast.walk(tree):
            if (isinstance(call,ast.Call) and isinstance(call.func,ast.Attribute)
                    and isinstance(call.func.value,ast.Name) and call.func.value.id=='_CONTRACTS'
                    and call.func.attr=='update' and len(call.args)==1 and isinstance(call.args[0],ast.Dict)):
                for key,value in zip(call.args[0].keys,call.args[0].values):
                    if isinstance(key,ast.Constant) and key.value=='D01':nodes.append((key.lineno,value.end_lineno))
    else:
        classes=[n for n in tree.body if isinstance(n,ast.ClassDef)and n.name=='UniversalHCL']
        if len(classes)!=1:raise ValueError('one universal entry required')
        methods=[n for n in classes[0].body if isinstance(n,ast.FunctionDef)and n.name=='_execute']
        if len(methods)!=1:raise ValueError('one executor required')
        for node in methods[0].body:
            test=node.test if isinstance(node,ast.If) else None
            if (isinstance(test,ast.Compare) and isinstance(test.left,ast.Name) and test.left.id=='cid'
                    and len(test.ops)==1 and isinstance(test.ops[0],ast.Eq) and len(test.comparators)==1
                    and isinstance(test.comparators[0],ast.Constant) and test.comparators[0].value=='D01'):
                nodes.append((node.lineno,node.end_lineno))
    if len(nodes)!=1:raise ValueError('exactly one added D01 contract or dispatch required')
    first,last=nodes[0];lines=text.splitlines(keepends=True)
    return ''.join(lines[:first-1]+lines[last:])


def validate_current(*,current_digest=None):
    for path,expected in HISTORICAL_PINS.items():
        if hashlib.sha256(Path(path).read_bytes()).hexdigest()!=expected:
            raise ValueError('historical amendment or diagnostic evidence changed')
    archive=validate_archive();validate_v24(current_digest=archive['runtime_sha256'])
    for path,expected in PREVIOUS_FILES.items():
        text=Path(path).read_bytes().decode()
        if hashlib.sha256(_without_d01(text,'capability_catalog' in path).encode()).hexdigest()!=expected:
            raise ValueError('unrelated runtime outside reviewed scope changed')
    files={str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in Path('hcl').rglob('*.py')}
    if not set(PREVIOUS_FILES)<=files.keys():raise ValueError('amended runtime file missing')
    files.update(PREVIOUS_FILES)
    if hashlib.sha256(json.dumps(files,sort_keys=True,separators=(',',':')).encode()).hexdigest()!=PREVIOUS_RUNTIME:
        raise ValueError('unrelated runtime outside reviewed scope changed')
    expected={'schema': 'hcl-universal-commitment-amendment-v1', 'previous_hcl_runtime_sha256': 'f07df5b3402596459df4ca05b714d1d0209e8d3dd15d29a868cfca7377085e91', 'amended_hcl_runtime_sha256': 'a202c903dd5f96262362a7f14700e6524a8a5d80230095c63d4cd973a9a51b25', 'changed_runtime_files': ['hcl/cognition/capability_catalog.py', 'hcl/cognition/universal_entry.py'], 'reason': 'RETAINED_D01_COMPLETE_CONDITIONAL_COMMITMENT_SINGLE_SOURCE_ENTRY', 'question_origin': 'OPERATION_QUESTION_WITH_ORIGINAL_OUTER_TASK_PRESERVED', 'checked_treatment_basis': 'NATIVE_CHECKED_CONDITIONAL_LIFECYCLE', 'complete_native_payload_and_policy_preserved': True, 'shared_source_revisions_and_all_support_claim_ids': True, 'receipt_acceptance_expectation_withdrawal_and_fulfillment_separate': True, 'later_receipt_backfills_earlier_expectation': False, 'source_order_verified_chronology': False, 'obligation_or_private_understanding_established': False, 'native_parser_or_grammar_changed': False, 'communication_authority_or_cache_changed': False, 'source_or_transport_budget_changed': False, 'model_or_token_settings_changed': False, 'new_provider_subcalls': False, 'provider_calls': 0, 'provider_spend_usd': 0, 'authorized_additional_calls': 0, 'historical_answers_rescored': False, 'model_selection_efficacy_verified': False, 'b04_entry_adapter': 'DEFERRED_COMPLETE_EVIDENCE_TRANSPORT_GATE', 'longmemeval': 'SEALED_NOT_ACCESSED'}
    expected['amended_hcl_runtime_sha256']=current_digest or runtime_digest()
    if json.loads(REPORT.read_text())!=expected:raise ValueError('universal commitment amendment drift')
    return True


if __name__=='__main__':validate_current();print('UNIVERSAL_COMMITMENT_AND_IMMUTABLE_EVIDENCE_PASS')
