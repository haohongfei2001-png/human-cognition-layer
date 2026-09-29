"""I01 provider-free guard for independent evaluation inputs and fair arms.

This does not qualify a source, judge an answer, or make a provider call.
"""
import argparse
import hashlib
import json
from pathlib import Path


FREEZE = Path('reports/HCL_I01_EVALUATION_FREEZE.json')
AMENDMENT = Path('reports/HCL_I02_RUNTIME_AMENDMENT.json')
ARMS = ('C', 'P', 'G', 'H')
FAMILIES = ('LONG_CHARACTER_DEVELOPMENT', 'MULTIPARTY_INFORMATION_STRATEGY',
    'RESPONSIBILITY_VALUE_INTEGRATION', 'ABSTRACT_CONCEPT_PHILOSOPHY')
FIELDS = ('answer', 'source_citations', 'uncertainty', 'assumptions')


def runtime_digest(root=Path('.')):
    """Hash the evaluated Python surface, independent of later docs/tests."""
    files = sorted((root / 'hcl').rglob('*.py'))
    if not files:
        raise ValueError('HCL runtime missing')
    rows = {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in files}
    return hashlib.sha256(json.dumps(rows, sort_keys=True,
        separators=(',', ':')).encode()).hexdigest()


def validate_runtime_amendment(freeze, amendment, *, current_digest=None):
    """Keep I01 immutable while pinning a disclosed repair before confirmation."""
    validate_freeze(freeze)
    if (amendment.get('schema') != 'hcl-i02-runtime-amendment-v1' or
            amendment.get('reason') != 'GENERAL_ORDINARY_INFORMATION_STATE_ENTRY_REPAIR' or
            amendment.get('previous_hcl_runtime_sha256') != freeze['hcl_runtime_sha256'] or
            amendment.get('historical_i01_main_sha') != freeze['architecture_main_sha'] or
            amendment.get('calibration_only') is not True or
            amendment.get('confirmation_items_inspected') != 0 or
            amendment.get('provider_calls') != 0 or
            amendment.get('longmemeval') != 'SEALED_NOT_ACCESSED'):
        raise ValueError('invalid I02 runtime amendment')
    digest = current_digest or runtime_digest()
    if amendment.get('amended_hcl_runtime_sha256') != digest:
        raise ValueError('current runtime differs from disclosed I02 amendment')
    return True


def validate_freeze(freeze):
    if freeze.get('schema') != 'hcl-i01-independent-evaluation-freeze-v1':
        raise ValueError('unrecognized evaluation freeze')
    if freeze.get('stage') != 'I01_QUESTION_AND_ARCHITECTURE_FROZEN_NO_OUTCOMES':
        raise ValueError('outcome or mutable stage in I01 freeze')
    if not all(isinstance(freeze.get(k), str) and len(freeze[k]) == 40
            for k in ('architecture_main_sha', 'architecture_tree_sha')):
        raise ValueError('exact architecture commit and tree required')
    if not isinstance(freeze.get('hcl_runtime_sha256'), str) or len(freeze['hcl_runtime_sha256']) != 64:
        raise ValueError('HCL runtime digest required')
    if tuple(freeze.get('task_families', ())) != FAMILIES:
        raise ValueError('all four prespecified cognition families required')
    if tuple(freeze.get('primary_arms', ())) != ARMS:
        raise ValueError('strong C/P/G/H comparison required')
    if tuple(freeze.get('answer_fields', ())) != FIELDS:
        raise ValueError('shared non-HCL answer contract required')
    if freeze.get('minimum_independent_writing_systems') != 3:
        raise ValueError('three independent writing systems required')
    if freeze.get('minimum_independent_model_families') != 2:
        raise ValueError('two-family transfer target required')
    if freeze.get('confirmation_visibility') != 'SEALED_UNTIL_FREEZE_AND_CALIBRATION':
        raise ValueError('confirmation material must remain unseen')
    if freeze.get('longmemeval') != 'SEALED_NOT_ACCESSED':
        raise ValueError('LongMemEval must remain sealed')
    if freeze.get('scoring_state') != 'OBLIGATIONS_FROZEN_RUBRIC_AND_N_AFTER_I02_BEFORE_CONFIRMATION':
        raise ValueError('rubric and N must be frozen before confirmation')
    if freeze.get('provider_calls') != 0 or freeze.get('provider_spend_usd') != 0:
        raise ValueError('I01 is provider-free')
    if freeze.get('historical_budget_transfer') is not False:
        raise ValueError('historical budget cannot transfer')
    return True


def validate_candidate(freeze, case):
    """Reject invalid I02 candidates before any result or provider call exists.

    One case is one ordinary-input question over licensed and authorized source
    text. This checks provenance and fairness shape; I02 must still inspect it.
    """
    validate_freeze(freeze)
    if not isinstance(case, dict) or case.get('task_family') not in FAMILIES:
        raise ValueError('case outside prespecified families')
    if case.get('split') not in ('CALIBRATION', 'CONFIRMATION'):
        raise ValueError('case split required')
    if case.get('source_origin') != 'INDEPENDENT_NON_HCL_AUTHOR':
        raise ValueError('HCL-authored material is development evidence only')
    if case.get('source_license_status') != 'VERIFIED_FOR_THIS_EVALUATION':
        raise ValueError('source rights unresolved')
    if case.get('source_access_status') != 'AUTHORIZED_FOR_EVERY_ARM':
        raise ValueError('source access must be fair')
    if case.get('longmemeval') != 'NOT_USED':
        raise ValueError('LongMemEval excluded')
    if not all(isinstance(case.get(k), str) and case[k].strip()
            for k in ('case_id', 'writing_system_id', 'author_id', 'template_id',
                'source_group_id', 'question', 'source_text')):
        raise ValueError('ordinary question, source and independence group required')
    if any(k in case for k in ('gold', 'mental_state_labels', 'hcl_state', 'winner')):
        raise ValueError('candidate cannot provide oracle state or visible outcomes')
    inputs = case.get('arm_inputs')
    if not isinstance(inputs, dict) or set(inputs) != set(ARMS):
        raise ValueError('all primary arms must receive ordinary inputs')
    expected = {'question': case['question'], 'source_text': case['source_text']}
    if any(inputs[arm] != expected for arm in ARMS):
        raise ValueError('arms must receive the same question and source text')
    if case.get('answer_fields') != list(FIELDS):
        raise ValueError('identical non-HCL answer contract required')
    return True


def validate_catalog(freeze, cases):
    if not isinstance(cases, list) or not cases:
        raise ValueError('nonempty independent case catalog required')
    for case in cases:
        validate_candidate(freeze, case)
    if len({c['case_id'] for c in cases}) != len(cases):
        raise ValueError('duplicate case identity')
    for key in ('source_group_id', 'author_id', 'template_id', 'writing_system_id'):
        groups = {}
        for case in cases:
            group = case[key]
            prior = groups.setdefault(group, case['split'])
            if prior != case['split']:
                raise ValueError(f'{key} crosses calibration/confirmation')
    if set(c['task_family'] for c in cases) != set(FAMILIES):
        raise ValueError('catalog lacks a prespecified task family')
    if len({c['writing_system_id'] for c in cases}) < freeze['minimum_independent_writing_systems']:
        raise ValueError('insufficient independent writing systems')
    return True


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--check-current-runtime', action='store_true')
    args = parser.parse_args()
    freeze = json.loads(FREEZE.read_text())
    validate_freeze(freeze)
    if args.check_current_runtime:
        if AMENDMENT.exists():
            validate_runtime_amendment(freeze, json.loads(AMENDMENT.read_text()))
        elif runtime_digest() != freeze['hcl_runtime_sha256']:
            raise ValueError('current runtime differs from I01 architecture freeze')
    print('I01_FREEZE_VALID')
