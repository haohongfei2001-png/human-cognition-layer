"""Exact native-reader policy transport; consumed provider authority stays closed."""
import hashlib
import json
from pathlib import Path

from scripts import development_universal_source_amendment as previous
from scripts.serious_eval_contract import runtime_digest

BASELINE = '8f6652c98b4cd0856e3e8d31f67ea73527ebd61d'
PREVIOUS_RUNTIME = '9f3ef69e16d21e5e17ab86725b2fa5696106e944cd646336c7ab6605056e1213'
CURRENT_RUNTIME = 'c345acb8a19cbc906487313a789a2ce108d826a81ec7ee2a2e65e5e968544bae'
CONSUMED_CNY_RUNTIME = previous.CONSUMED_CNY_RUNTIME
PREVIOUS_FILES = {'hcl/cognition/universal_entry.py': 'b1ddd4db1f5a8ad66d97862aba656bbf7caaeac0a9b207172b3740769cdf1c7b'}
REVIEWED_FILES = {'hcl/cognition/universal_entry.py': 'f919a605f3ceb79f296f8a2ac88274cb1de0a63f85552481999cfe068f3425f3'}
PINS = Path('reports/HCL_NATIVE_READER_POLICY_HISTORY_PINS.json')
PINS_SHA256 = '3216cabe2908ff4e30bcea3bf9e45fdf67a73e894d93e5ecaae67320a37d5df2'
REPORT = Path('reports/HCL_NATIVE_READER_POLICY_AMENDMENT.json')


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
    return dict(schema='hcl-native-reader-policy-amendment-v1',
        baseline_commit=BASELINE, previous_hcl_runtime_sha256=PREVIOUS_RUNTIME,
        amended_hcl_runtime_sha256=CURRENT_RUNTIME,
        changed_runtime_files=sorted(REVIEWED_FILES),
        reason='PRESERVE_NATIVE_READER_POLICY_AND_SHARE_EXACT_REPEATED_CONTEXTS',
        entry='UniversalHCL._execute', source_text_changed=False,
        ordinary_families=['B01', 'B02', 'C01', 'C03'],
        native_policy_origin='RETAINED_READER_SYSTEM_MESSAGE_FROM_VERSIONED_CODE',
        native_policy_scope='ASSOCIATED_NATIVE_RESULT_ONLY',
        final_system_policy_changed=True, planner_policy_changed=False,
        final_policy_change_scope='TRUSTED_RESULT_BINDING_AND_EXACT_REFERENCE_INSTRUCTIONS',
        final_citation_contract_unchanged=True,
        exact_duplicate_ordinary_contexts_shared=True,
        full_receipt_operations_preserved=True,
        reference_pool_built_from_source_or_plan=False,
        source_or_planner_text_promoted_to_policy=False,
        native_result_json_changed=False, native_dispatch_changed=False,
        source_snapshot_guard_preserved=True, original_citation_audit_changed=False,
        context_limit_changed=False, provider_envelope_changed=False,
        model_or_token_defaults_changed=False, provider_phases_changed=False,
        historical_executors_unchanged=True, historical_grants_reopened=False,
        historical_answers_rescored=False, historical_failure_cause_identified=False,
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
        raise ValueError('native reader policy amendment drift')
    if json.loads(REPORT.read_text()) != expected_report():
        raise ValueError('native reader policy amendment drift')
    return True


if __name__ == '__main__':
    validate_current()
    print('NATIVE_READER_POLICY_AND_CLOSED_HISTORY_PASS')
