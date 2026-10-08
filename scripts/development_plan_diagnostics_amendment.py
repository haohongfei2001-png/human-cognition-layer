"""Current safe failure stages and exact-quote binding normalization; paid history is immutable."""
import hashlib
import json
from pathlib import Path
from scripts import development_executable_entry_amendment as previous
from scripts.serious_eval_contract import runtime_digest

BASELINE = '6c7c4cd0f736fb942558f4710f26329273af81b0'
PREVIOUS_RUNTIME = '50e62d02790f165d1d73fc3275fc6f795da7582b9f81143eaa7aa69806660d16'
CONSUMED_CNY_RUNTIME = previous.CONSUMED_CNY_RUNTIME
CURRENT_RUNTIME = 'f5d155b9a8f8efd8e94143ff622d955028f5b83f43a6f1e76c7e2fa033d06940'
PREVIOUS_FILES = {'hcl/cognition/universal_entry.py': '014641df1dd290261dcf2ec77d92b86532cf6a17801a214b6e6a9e858ace1661', 'hcl/cognition/capability_catalog.py': '535f99af4c9d385dae34c1053a7e6b4a1372f85d28f12929ff1e60e8adbca0bf'}
REVIEWED_FILES = {'hcl/cognition/universal_entry.py': 'f71c0c71d5f6dbd3cf8ff716e3dce47c346176c1387ca42c7081ab0e73e52e6c', 'hcl/cognition/capability_catalog.py': '68b7099936e92b19edd05c398943ae343386791f171ddba19da05309ad86e180'}
PINS_SHA256 = '287a9d2f55742d55435f86c597ecfe04278e054439890a9c0ebfa136b2fb405a'
BINDING_POLICY_BEFORE = 'Each binding has exactly role, source_id, start, quote. Quote exact supplied text at its character offset. Only role actor is accepted in this slice. Never invent sources, facts, normative rules, dates or authority. '
BINDING_POLICY_AFTER = 'Bindings: role, source_id, quote, optional start. Missing start needs a unique exact quote; supplied Unicode offsets must match. Only role actor; never invent sources, facts, normative rules, dates or authority. '
G02_INPUT_LIMITS_BEFORE = 'One to four bound actor episodes using existing literal action/outcome forms; unsupported episodes remain SOURCE_EPISODE_UNRESOLVED. Each episode at most 16000 characters; original question at most 8000 characters. Source/actor bindings must use exact supplied quotes and offsets.'
G02_INPUT_LIMITS_AFTER = 'One to four bound actor episodes using existing literal action/outcome forms; unsupported episodes remain SOURCE_EPISODE_UNRESOLVED. Each episode at most 16000 characters; original question at most 8000 characters. Bindings use exact quotes; omit offsets only for unique matches.'
PINS = Path('reports/HCL_PLAN_DIAGNOSTICS_HISTORY_PINS.json')
REPORT = Path('reports/HCL_PLAN_DIAGNOSTICS_AMENDMENT.json')
CURRENT_PLANNER_POLICY = previous.CURRENT_PLANNER_POLICY.replace(BINDING_POLICY_BEFORE, BINDING_POLICY_AFTER)


def digest(raw): return hashlib.sha256(raw).hexdigest()


def apply_reviewed_planner_contract(policy):
    policy = previous.apply_reviewed_planner_contract(policy)
    if policy != previous.CURRENT_PLANNER_POLICY or policy.count(BINDING_POLICY_BEFORE) != 1:
        raise ValueError('exact previous planner contract required')
    return policy.replace(BINDING_POLICY_BEFORE, BINDING_POLICY_AFTER)


def validate_preserved_history():
    previous.validate_preserved_history()
    raw = PINS.read_bytes()
    if digest(raw) != PINS_SHA256: raise ValueError('historical pin manifest drift')
    manifest = json.loads(raw)
    if manifest['baseline_commit'] != BASELINE: raise ValueError('historical amendment baseline drift')
    for name, expected in manifest['files_sha256'].items():
        if digest(Path(name).read_bytes()) != expected:
            raise ValueError('historical amendment or consumed evidence changed')
    return True


def expected_report():
    return dict(schema='hcl-plan-diagnostics-amendment-v1', baseline_commit=BASELINE,
        previous_hcl_runtime_sha256=PREVIOUS_RUNTIME, amended_hcl_runtime_sha256=CURRENT_RUNTIME,
        changed_runtime_files=sorted(REVIEWED_FILES),
        reason='SAFE_FAILURE_STAGE_CODES_AND_UNIQUE_EXACT_ACTOR_QUOTE_BINDINGS',
        failure_details_are_code_owned_bounded_enums=True,
        provider_source_exception_or_reasoning_text_in_diagnostics=False,
        malformed_planning_json_has_specific_safe_code=True,
        missing_binding_offset_requires_unique_exact_named_source_match=True,
        overlapping_matches_count=True, supplied_wrong_offsets_are_never_repaired=True,
        unicode_character_offsets_not_bytes_or_normalized_text=True,
        existing_explicit_binding_semantics_unchanged=True,
        source_version_and_native_treatment_gates_preserved=True,
        native_adapter_or_semantic_candidate_parser_changed=False,
        planning_request_fixed_overhead_delta_bytes=-5,
        phase_configuration=dict(planning=dict(max_tokens=16384,reasoning_effort='high'),
                                 answer=dict(max_tokens=16384,reasoning_effort='low')),
        maximum_request_bytes=36000, additional_provider_phases=0, automatic_retry=False,
        historical_executors_unchanged=True, historical_grants_reopened=False,
        historical_outputs_rescored=False, previous_failure_cause_reconstructed=False,
        provider_calls=0, provider_spend_cny=0, authorized_additional_calls=0,
        model_compliance_or_quality_verified=False, longmemeval='SEALED_NOT_ACCESSED')


def validate_current(*, current_digest=None):
    validate_preserved_history()
    files = {str(path):digest(path.read_bytes()) for path in Path('hcl').rglob('*.py')}
    if any(files.get(name) != expected for name, expected in REVIEWED_FILES.items()):
        raise ValueError('plan diagnostics amendment drift: runtime outside reviewed scope changed')
    restored = dict(files, **PREVIOUS_FILES)
    if digest(json.dumps(restored,sort_keys=True,separators=(',',':')).encode()) != PREVIOUS_RUNTIME:
        raise ValueError('unrelated runtime outside reviewed scope changed')
    if runtime_digest() != CURRENT_RUNTIME or current_digest is not None and current_digest != CURRENT_RUNTIME:
        raise ValueError('plan diagnostics amendment drift')
    if json.loads(REPORT.read_text()) != expected_report(): raise ValueError('plan diagnostics amendment drift')
    return True


if __name__ == '__main__':
    validate_current()
    print('SAFE_PLAN_DIAGNOSTICS_AND_CLOSED_HISTORY_PASS')
