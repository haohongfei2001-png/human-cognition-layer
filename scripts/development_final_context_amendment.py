"""Current development runtime identity; never a grant to reopen consumed runs."""
import hashlib
import json
from pathlib import Path

from scripts import development_explicit_citation_amendment as previous
from scripts.serious_eval_contract import runtime_digest

BASELINE = 'dbd7ba9fe9b8a2d4aa165f4e39a949b510cd1ee5'
PREVIOUS_RUNTIME = '62bea96c481fcdde3bfb0af8707796d5afaebf1c9d051ace9bd0c82e236f2442'
CURRENT_RUNTIME = '5e58ad59e7d048098978dbb45a11d714d1e54967286d7a552b765e8c017bb35f'
PREVIOUS_FILES = {'hcl/cognition/universal_entry.py': '40307d2b68a0e17601b5012fe7858aa79307a58bc118d1c30bea55dbdbc2f897'}
REVIEWED_FILES = {'hcl/cognition/universal_entry.py': '64d8b74935182ebee3e1d3430286a1ce4c0914ba6f621f194cb0f9af7adfac3f'}
PINS = Path('reports/HCL_FINAL_CONTEXT_HISTORY_PINS.json')
PINS_SHA256 = '7056a60476259b33122580d0ab5b905af723cccc2291ac6a3de85162df3aed54'
REPORT = Path('reports/HCL_FINAL_CONTEXT_TRANSPORT_AMENDMENT.json')


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
            raise ValueError('historical amendment or consumed two-stage evidence changed')
    for stage in (1, 2):
        grant = json.loads(Path(f'.github/HCL_TWO_STAGE_CNY_{stage}_GRANT.json').read_bytes())
        if (grant['status'] != 'CLOSED_NO_TRANSFER_NO_RETRY'
                or grant['remaining_authorized_calls'] != 0
                or grant['remaining_authorized_cny'] != '0'):
            raise ValueError('historical amendment grant must stay closed with zero authority')
    return True


def expected_report():
    return dict(schema='hcl-final-context-transport-amendment-v1',
        baseline_commit=BASELINE, previous_hcl_runtime_sha256=PREVIOUS_RUNTIME,
        amended_hcl_runtime_sha256=CURRENT_RUNTIME,
        changed_runtime_files=sorted(REVIEWED_FILES),
        reason='COMPACT_FINAL_JSON_AND_LOCAL_SIZE_ONLY_DIAGNOSTICS',
        entry='UniversalHCL.answer', source_text_changed=False,
        parsed_payload_values_changed=False, system_policy_changed=False,
        native_dispatch_changed=False, original_citation_audit_changed=False,
        context_limit_changed=False, provider_envelope_changed=False,
        model_or_token_defaults_changed=False, provider_phases_changed=False,
        diagnostics_scope='LOCAL_FINAL_CONTEXT_NOT_PROVIDER_REQUEST',
        diagnostics_persisted_by_historical_executor=False,
        historical_executors_unchanged=True, historical_grants_reopened=False,
        historical_answers_rescored=False, historical_failure_cause_identified=False,
        provider_calls=0, provider_spend_usd=0, authorized_additional_calls=0,
        answer_quality_improvement_claimed=False, longmemeval='SEALED_NOT_ACCESSED')


def validate_current(*, current_digest=None):
    validate_preserved_history()
    files = {str(path): digest(path.read_bytes()) for path in Path('hcl').rglob('*.py')}
    if any(files.get(name) != expected for name, expected in REVIEWED_FILES.items()):
        raise ValueError('unrelated runtime outside reviewed scope changed')
    restored = dict(files, **PREVIOUS_FILES)
    if digest(json.dumps(restored, sort_keys=True, separators=(',', ':')).encode()) != PREVIOUS_RUNTIME:
        raise ValueError('unrelated runtime outside reviewed scope changed')
    # The optional diagnostic input cannot substitute for hashing the real tree.
    if runtime_digest() != CURRENT_RUNTIME or current_digest is not None and current_digest != CURRENT_RUNTIME:
        raise ValueError('final context amendment drift')
    if json.loads(REPORT.read_text()) != expected_report():
        raise ValueError('final context amendment drift')
    return True


if __name__ == '__main__':
    validate_current()
    print('FINAL_CONTEXT_TRANSPORT_AND_CLOSED_HISTORY_PASS')
