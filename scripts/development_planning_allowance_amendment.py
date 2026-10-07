"""Fixed ordinary planning allowance; all consumed experiments remain immutable."""
import hashlib
import json
from pathlib import Path

from scripts import development_planner_lifecycle_amendment as previous
from scripts.serious_eval_contract import runtime_digest

BASELINE = '3c997084f2c5d49b6cc48637f653e60f5f550299'
PREVIOUS_RUNTIME = 'da8349d12f8d13001e565ccdc8dbd6933cdbff5d8ec3b6369823c01925a379e9'
CURRENT_RUNTIME = 'e621355a10ad6d2da716ed64d244f6c3f69bdc0dcd59cf91673d7ba4b2b05cac'
CONSUMED_CNY_RUNTIME = previous.CONSUMED_CNY_RUNTIME
PREVIOUS_FILES = {'hcl/cognition/deepseek_metered.py': 'cc44617848918615b7fad9fb29a1006968f29454babd8fa08de377bccc727c7a'}
REVIEWED_FILES = {'hcl/cognition/deepseek_metered.py': 'd2d60d5c2456f91857deae88a361d9468d3acae429f53428b6f35c1f8b919fec'}
PINS = Path('reports/HCL_ORDINARY_PLANNING_ALLOWANCE_HISTORY_PINS.json')
PINS_SHA256 = '2d0a531e318c4881794168c9a2c550b9a85d2056aa94b641eb8c95d60af43f02'
REPORT = Path('reports/HCL_ORDINARY_PLANNING_ALLOWANCE_AMENDMENT.json')


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
    return dict(schema='hcl-ordinary-planning-allowance-amendment-v1',
        baseline_commit=BASELINE, previous_hcl_runtime_sha256=PREVIOUS_RUNTIME,
        amended_hcl_runtime_sha256=CURRENT_RUNTIME,
        changed_runtime_files=sorted(REVIEWED_FILES),
        reason='FIXED_16K_COMPLETION_ALLOWANCE_FOR_ORDINARY_HIGH_THINKING_PLANNING',
        previous_planning_tokens=4096, planning_tokens=16384, answer_tokens=8192,
        reasoning_effort='high', thinking='enabled', model='deepseek-v4-pro',
        maximum_request_bytes=36000, maximum_planning_text_characters=32000,
        exact_request_reservation_and_usage_validation_preserved=True,
        safe_rejected_usage_bound_tracks_new_completion_allowance=True,
        old_budget_cannot_admit_larger_request=True, automatic_upgrade=False,
        automatic_retry=False, provider_phases=['planning', 'answer'],
        source_text_changed=False, planning_prompt_changed=False,
        native_parser_or_results_changed=False, mandatory_native_result_preserved=True,
        source_snapshot_guard_preserved=True, native_policy_sharing_preserved=True,
        original_citation_audit_changed=False, final_policy_changed=False,
        historical_executors_unchanged=True, historical_grants_reopened=False,
        historical_answers_rescored=False, provider_calls=0, provider_spend_cny=0,
        authorized_additional_calls=0, current_model_planning_success_verified=False,
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
        raise ValueError('ordinary planning allowance amendment drift')
    if json.loads(REPORT.read_text()) != expected_report():
        raise ValueError('ordinary planning allowance amendment drift')
    return True


if __name__ == '__main__':
    validate_current()
    print('ORDINARY_PLANNING_ALLOWANCE_AND_CLOSED_HISTORY_PASS')
