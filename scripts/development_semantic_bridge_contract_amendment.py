"""Explicit first-plan semantic-input responsibility; consumed runs remain immutable."""
import hashlib
import json
from pathlib import Path

from scripts import development_planning_allowance_amendment as previous
from scripts.serious_eval_contract import runtime_digest

BASELINE = 'a231195dd3e85b580466e7bcd462fdd269e6b19f'
PREVIOUS_RUNTIME = 'e621355a10ad6d2da716ed64d244f6c3f69bdc0dcd59cf91673d7ba4b2b05cac'
CURRENT_RUNTIME = 'a3ace7e929e46a1aebd6cc5706c549abf930189fd032c54ab31298e3742b3672'
CONSUMED_CNY_RUNTIME = previous.CONSUMED_CNY_RUNTIME
PREVIOUS_FILES = {'hcl/cognition/universal_entry.py': '4f545536e31d37d3966a172271f4883a417bbca1a808fd8c6db7193eb62eff19'}
REVIEWED_FILES = {'hcl/cognition/universal_entry.py': 'bde140aefa5d97798d95cb99ff3f84c5d1ef56c504cd08457dac510000310d0e'}
PINS = Path('reports/HCL_SEMANTIC_BRIDGE_CONTRACT_HISTORY_PINS.json')
PINS_SHA256 = '3fd3bc6d6524107f45e7e6300ed1b93ee9872dd933d93d4cc721d581d218f676'
REPORT = Path('reports/HCL_SEMANTIC_BRIDGE_CONTRACT_AMENDMENT.json')

PLANNER_POLICY_REPLACEMENTS = (('For at most ONE selected B01, C01, C02 or C03 operation with one complete source, you may also supply semantic_candidates to translate ordinary source wording into existing structured tool inputs in this same planning response. ', 'For ordinary prose outside native literal forms, construct faithful semantic_candidates for at most ONE relevant B01/C01/C02/C03 operation with one complete source in this first planning response. Source IDs alone do not create typed premises. '), ('Omit semantic_candidates when unnecessary; no automatic extraction call or retry will occur. ', 'Omit semantic_candidates for already supported literal input or when no faithful supported translation is possible. B02 and D02 do not accept semantic_candidates. Native readers are literal checkers, not another LLM. No automatic extraction call or retry will occur. '))


def apply_reviewed_planner_contract(policy):
    for before, after in PLANNER_POLICY_REPLACEMENTS:
        if policy.count(before) != 1:
            raise ValueError('exact prior planner contract required')
        policy = policy.replace(before, after)
    return policy


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def validate_preserved_history():
    previous.validate_preserved_history()
    raw = PINS.read_bytes()
    if digest(raw) != PINS_SHA256:
        raise ValueError('historical pin manifest drift')
    manifest = json.loads(raw)
    if manifest['baseline_commit'] != BASELINE:
        raise ValueError('historical amendment baseline drift')
    for name, expected in manifest['files_sha256'].items():
        if digest(Path(name).read_bytes()) != expected:
            raise ValueError('historical amendment or consumed evidence changed')
    return True


def expected_report():
    return dict(schema='hcl-semantic-bridge-contract-amendment-v1',
        baseline_commit=BASELINE, previous_hcl_runtime_sha256=PREVIOUS_RUNTIME,
        amended_hcl_runtime_sha256=CURRENT_RUNTIME,
        changed_runtime_files=sorted(REVIEWED_FILES),
        reason='CLARIFY_EXISTING_FIRST_PLAN_TYPED_INPUT_RESPONSIBILITY',
        planner_policy_utf8_delta=190, existing_bridge_families=['B01', 'C01', 'C02', 'C03'],
        maximum_translated_operations=1, maximum_candidates=24,
        maximum_operations=3, source_ids_are_not_typed_premises=True,
        literal_input_may_omit_translation=True, unfaithful_translation_must_not_be_forced=True,
        b02_d02_bridge_unavailable=True, original_failed_arguments_replayed_unchanged=True,
        d02_empty_bindings_valid=True, native_parser_or_results_changed=False,
        source_text_changed=False, catalog_changed=False, local_readiness_probe_added=False,
        automatic_translation_added=False, provider_phases_changed=False,
        planning_tokens=16384, answer_tokens=8192, maximum_request_bytes=36000,
        source_snapshot_guard_preserved=True, native_policy_sharing_preserved=True,
        original_citation_audit_changed=False, mandatory_native_result_preserved=True,
        semantic_certification=False, execution_is_treatment_proof=False,
        historical_executors_unchanged=True, historical_grants_reopened=False,
        historical_answers_rescored=False, provider_calls=0, provider_spend_cny=0,
        authorized_additional_calls=0, model_argument_compliance_verified=False,
        answer_quality_improvement_claimed=False, longmemeval='SEALED_NOT_ACCESSED')


def validate_current(*, current_digest=None):
    validate_preserved_history()
    files = {str(path): digest(path.read_bytes()) for path in Path('hcl').rglob('*.py')}
    if any(files.get(name) != expected for name, expected in REVIEWED_FILES.items()):
        raise ValueError('unrelated runtime outside reviewed scope changed')
    restored = dict(files, **PREVIOUS_FILES)
    if digest(json.dumps(restored, sort_keys=True, separators=(',', ':')).encode()) != PREVIOUS_RUNTIME:
        raise ValueError('unrelated runtime outside reviewed scope changed')
    if runtime_digest() != CURRENT_RUNTIME or current_digest is not None and current_digest != CURRENT_RUNTIME:
        raise ValueError('semantic bridge contract amendment drift')
    if json.loads(REPORT.read_text()) != expected_report():
        raise ValueError('semantic bridge contract amendment drift')
    return True


if __name__ == '__main__':
    validate_current()
    print('SEMANTIC_BRIDGE_CONTRACT_AND_CLOSED_HISTORY_PASS')
