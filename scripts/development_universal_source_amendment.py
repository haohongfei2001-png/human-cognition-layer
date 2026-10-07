"""Exact source-snapshot guard identity; consumed provider authority stays closed."""
import hashlib
import json
from pathlib import Path

from scripts import development_final_context_amendment as previous
from scripts.serious_eval_contract import runtime_digest

BASELINE = 'cd3fa7fffbbfd2caa746812061a0def2edda90fe'
PREVIOUS_RUNTIME = '5e58ad59e7d048098978dbb45a11d714d1e54967286d7a552b765e8c017bb35f'
CURRENT_RUNTIME = '9f3ef69e16d21e5e17ab86725b2fa5696106e944cd646336c7ab6605056e1213'
CONSUMED_CNY_RUNTIME = previous.PREVIOUS_RUNTIME
PREVIOUS_FILES = {'hcl/cognition/universal_entry.py': '64d8b74935182ebee3e1d3430286a1ce4c0914ba6f621f194cb0f9af7adfac3f'}
REVIEWED_FILES = {'hcl/cognition/universal_entry.py': 'b1ddd4db1f5a8ad66d97862aba656bbf7caaeac0a9b207172b3740769cdf1c7b'}
PINS = Path('reports/HCL_UNIVERSAL_SOURCE_SNAPSHOT_HISTORY_PINS.json')
PINS_SHA256 = 'd38803d7b1a07fd67267215a062a1ed3bb3233dbc1c59c470fb4b061b88ea19c'
REPORT = Path('reports/HCL_UNIVERSAL_SOURCE_SNAPSHOT_AMENDMENT.json')


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
    return dict(schema='hcl-universal-source-snapshot-amendment-v1',
        baseline_commit=BASELINE, previous_hcl_runtime_sha256=PREVIOUS_RUNTIME,
        amended_hcl_runtime_sha256=CURRENT_RUNTIME,
        changed_runtime_files=sorted(REVIEWED_FILES),
        reason='RECHECK_SHARED_WORKSPACE_SOURCE_VERSION_AND_EXACT_TEXT',
        entry='UniversalHCL._current', source_text_changed=False,
        source_identity_check_added=True, source_removal_fail_closed=True,
        original_citation_audit_changed=False, native_dispatch_changed=False,
        system_policy_changed=False, native_payload_changed=False,
        valid_same_version_derived_state_preserved=True,
        unrelated_workspace_sources_preserved=True,
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
        raise ValueError('source snapshot amendment drift')
    if json.loads(REPORT.read_text()) != expected_report():
        raise ValueError('source snapshot amendment drift')
    return True


if __name__ == '__main__':
    validate_current()
    print('UNIVERSAL_SOURCE_SNAPSHOT_AND_CLOSED_HISTORY_PASS')
