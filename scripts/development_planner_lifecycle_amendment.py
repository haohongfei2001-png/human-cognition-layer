"""Exact planner-visible lifecycle forms; consumed authority stays closed."""
import hashlib
import json
from pathlib import Path

from scripts import development_plan_pursuit_amendment as previous
from scripts.serious_eval_contract import runtime_digest

BASELINE = '92c8990e0c13983ada4b8b88a1480875019fd00e'
PREVIOUS_RUNTIME = 'c13a04ce24d0e830dc903614595124c63d80565226e3d8151c9e88bc3f8746ec'
CURRENT_RUNTIME = 'da8349d12f8d13001e565ccdc8dbd6933cdbff5d8ec3b6369823c01925a379e9'
CONSUMED_CNY_RUNTIME = previous.CONSUMED_CNY_RUNTIME
PREVIOUS_FILES = {'hcl/cognition/universal_entry.py': 'f919a605f3ceb79f296f8a2ac88274cb1de0a63f85552481999cfe068f3425f3'}
REVIEWED_FILES = {'hcl/cognition/universal_entry.py': '4f545536e31d37d3966a172271f4883a417bbca1a808fd8c6db7193eb62eff19'}
PINS = Path('reports/HCL_PLANNER_LIFECYCLE_CONTRACT_HISTORY_PINS.json')
PINS_SHA256 = 'a2fcaade4938aaded54d92d940c04ac03e59d292dd75ea3778f17b655a037263'
REPORT = Path('reports/HCL_PLANNER_LIFECYCLE_CONTRACT_AMENDMENT.json')


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
    return dict(schema='hcl-planner-lifecycle-contract-amendment-v1',
        baseline_commit=BASELINE, previous_hcl_runtime_sha256=PREVIOUS_RUNTIME,
        amended_hcl_runtime_sha256=CURRENT_RUNTIME,
        changed_runtime_files=sorted(REVIEWED_FILES),
        reason='EXPOSE_EXISTING_LIFECYCLE_FORMS_WITH_LOSSLESS_PLANNING_JSON',
        entry='PLANNER_POLICY_AND_PLANNING_JSON', source_text_changed=False,
        planning_json_structural_spaces_removed=True, planning_payload_values_unchanged=True,
        embedded_string_bytes_and_unicode_unchanged=True,
        native_parser_or_results_changed=False, final_policy_changed=False,
        planner_policy_addition='SIX_EXISTING_FORMS_AND_QUALIFICATIONS_ONLY',
        consideration_not_selection=True, goal_and_plan_lifecycle_distinct=True,
        completion_not_inferred_from_outcome=True,
        model_selected_routing_preserved=True, mandatory_native_result_preserved=True,
        translation_semantic_certification=False,
        original_citation_audit_changed=False, context_limit_changed=False,
        source_snapshot_guard_preserved=True, native_policy_sharing_preserved=True,
        unknown_pursuit_classification_preserved=True,
        provider_envelope_changed=False, model_or_token_defaults_changed=False,
        provider_phases_changed=False, historical_executors_unchanged=True,
        historical_grants_reopened=False, historical_answers_rescored=False,
        provider_calls=0, provider_spend_cny=0, authorized_additional_calls=0,
        model_planning_improvement_demonstrated=False,
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
        raise ValueError('planner lifecycle contract amendment drift')
    if json.loads(REPORT.read_text()) != expected_report():
        raise ValueError('planner lifecycle contract amendment drift')
    return True


if __name__ == '__main__':
    validate_current()
    print('PLANNER_LIFECYCLE_CONTRACT_AND_CLOSED_HISTORY_PASS')
