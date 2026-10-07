"""Exact pursuit uncertainty classification; consumed authority stays closed."""
import hashlib
import json
from pathlib import Path

from scripts import development_native_reader_policy_amendment as previous
from scripts.serious_eval_contract import runtime_digest

BASELINE = '61da904bd5de34a974316c0d8188f582d21b9646'
PREVIOUS_RUNTIME = 'c345acb8a19cbc906487313a789a2ce108d826a81ec7ee2a2e65e5e968544bae'
CURRENT_RUNTIME = 'c13a04ce24d0e830dc903614595124c63d80565226e3d8151c9e88bc3f8746ec'
CONSUMED_CNY_RUNTIME = previous.CONSUMED_CNY_RUNTIME
PREVIOUS_FILES = {'hcl/cognition/plan_feasibility.py': '8ac5106fdcdb1dec9426a1d0514a80c23edb3bd5000eadecd98a8205b97d8eb4'}
REVIEWED_FILES = {'hcl/cognition/plan_feasibility.py': '0d1b39c166c9b2392838bc0078b6fed7c136abf9c6b78fb2bce2d84a0905d1e7'}
PINS = Path('reports/HCL_PLAN_PURSUIT_UNCERTAINTY_HISTORY_PINS.json')
PINS_SHA256 = '2fd2cea396f94c17bd5febb7303a81e53c87529901fe583d84bb0701a7447a2b'
REPORT = Path('reports/HCL_PLAN_PURSUIT_UNCERTAINTY_AMENDMENT.json')


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
    return dict(schema='hcl-plan-pursuit-uncertainty-amendment-v1',
        baseline_commit=BASELINE, previous_hcl_runtime_sha256=PREVIOUS_RUNTIME,
        amended_hcl_runtime_sha256=CURRENT_RUNTIME,
        changed_runtime_files=sorted(REVIEWED_FILES),
        reason='KEEP_MISSING_UNCERTAIN_AND_CONFLICTED_PURSUIT_UNRESOLVED',
        entry='check_plan_candidates', source_text_changed=False,
        extraction_or_native_grammar_changed=False, positive_eligibility_changed=False,
        explicit_nonselection_abandonment_completion_preserved=True,
        belief_opportunity_and_declared_model_checks_preserved=True,
        unknown_pursuit_not_counterevidence=True,
        native_policy_addition='FIXED_CODE_TEXT_ONLY_WHEN_PURSUIT_IS_UNRESOLVED',
        payload_policy_text_promoted_to_system=False,
        downstream_consumer_code_changed=False,
        downstream_wrong_motive_answer_demonstrated=False,
        source_snapshot_guard_preserved=True, native_policy_sharing_preserved=True,
        original_citation_audit_changed=False, context_limit_changed=False,
        provider_envelope_changed=False, model_or_token_defaults_changed=False,
        provider_phases_changed=False, historical_executors_unchanged=True,
        historical_grants_reopened=False, historical_answers_rescored=False,
        provider_calls=0, provider_spend_cny=0, authorized_additional_calls=0,
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
        raise ValueError('plan pursuit uncertainty amendment drift')
    if json.loads(REPORT.read_text()) != expected_report():
        raise ValueError('plan pursuit uncertainty amendment drift')
    return True


if __name__ == '__main__':
    validate_current()
    print('PLAN_PURSUIT_UNCERTAINTY_AND_CLOSED_HISTORY_PASS')
