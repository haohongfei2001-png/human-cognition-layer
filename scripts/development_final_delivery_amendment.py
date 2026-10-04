"""Next ordinary runtime; historical executions and their validators stay frozen."""
import hashlib
import json
from pathlib import Path

from scripts.development_nonblank_answer_amendment import HISTORICAL_PINS
from scripts.development_drc008_replay import validate_archive
from scripts.development_runtime_amendment_v24 import validate_current as validate_v24
from scripts.serious_eval_contract import runtime_digest

BASELINE = '9c0fb6164860150a2d03c39f0804c51f9ba0c47f'
PREVIOUS_RUNTIME = '90737b3ed772f65851553d8a673112eae50f2781185d8b5b4ccd127cdfb8663b'
CHANGED = 'hcl/cognition/universal_entry.py'
PREVIOUS_FILE_SHA = 'ae854eb6630474bdbf673239679652f477d8d4a9c6513ecffd2740d1b5ca67f3'
REPORT = Path('reports/HCL_FINAL_DELIVERY_AMENDMENT.json')
PINS = Path('reports/HCL_FINAL_DELIVERY_HISTORY_PINS.json')
PINS_SHA = 'eba80f08f328578b229e03c0c11f9b89fd998e911344b8aa9e134f98653f0be0'
REVIEWED_FILE_SHA = '81be72668ff693acd9e1b45f05cf23e0d299da5589bf258bf06f528c7e33cd4a'


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def validate_preserved_history():
    # Keep the predecessor's public pin mapping unchanged for existing tests.
    for name, expected in HISTORICAL_PINS.items():
        if digest(Path(name).read_bytes()) != expected:
            raise ValueError('historical amendment or diagnostic evidence changed')
    raw = PINS.read_bytes()
    if digest(raw) != PINS_SHA:
        raise ValueError('historical amendment pin manifest drift')
    manifest = json.loads(raw)
    if set(manifest) != {'schema', 'baseline_commit', 'files_sha256'} or manifest['schema'] != 'hcl-final-delivery-history-pins-v1' or manifest['baseline_commit'] != BASELINE:
        raise ValueError('historical amendment pin manifest invalid')
    for name, expected in manifest['files_sha256'].items():
        if digest(Path(name).read_bytes()) != expected:
            raise ValueError('historical amendment or consumed execution changed')
    for name in ('.github/HCL_CURRENT_FLOW_GRANT.json', '.github/HCL_FOUR_COMPARISON_GRANT.json'):
        grant = json.loads(Path(name).read_text())
        if (grant['status'] != 'CLOSED_NO_TRANSFER_NO_RETRY' or
                grant['remaining_authorized_calls'] != 0 or grant['remaining_authorized_usd'] != '0'):
            raise ValueError('consumed grants must remain closed at zero')
    archive = validate_archive()
    validate_v24(current_digest=archive['runtime_sha256'])
    return True


def validate_current(*, current_digest=None):
    validate_preserved_history()
    files = {str(p): digest(p.read_bytes()) for p in Path('hcl').rglob('*.py')}
    if files.get(CHANGED) != REVIEWED_FILE_SHA:
        raise ValueError('unrelated runtime outside reviewed scope changed')
    files[CHANGED] = PREVIOUS_FILE_SHA
    restored = digest(json.dumps(files, sort_keys=True, separators=(',', ':')).encode())
    if restored != PREVIOUS_RUNTIME:
        raise ValueError('unrelated runtime outside reviewed scope changed')
    expected = dict(
        schema='hcl-final-delivery-amendment-v1', baseline_commit=BASELINE,
        previous_hcl_runtime_sha256=PREVIOUS_RUNTIME,
        amended_hcl_runtime_sha256=current_digest or runtime_digest(),
        changed_runtime_files=[CHANGED],
        reason='ADDITIVE_CONTENT_FREE_FINAL_DELIVERY_DIAGNOSTICS',
        entry='UniversalHCL.answer', receipt_field='final_delivery_code',
        codes=['NOT_REACHED', 'RETURNED_UNVALIDATED', 'JSON_INVALID', 'SCHEMA_INVALID',
               'ANSWER_BLANK', 'SOURCE_REVIEW_REJECTED', 'DELIVERED'],
        existing_receipt_fields_unchanged=True, acceptance_rules_changed=False,
        prompts_changed=False, raw_answers_rewritten=False,
        source_citation_audit_changed=False, model_or_token_defaults_changed=False,
        provider_phases_changed=False, retries_added=0, provider_calls=0,
        provider_spend_usd=0, authorized_additional_calls=0,
        historical_answers_rescored=False, answer_quality_improvement_claimed=False,
        historical_checks='EXACT_BASELINE_ISOLATED_PROVIDER_FREE_ONLY',
        longmemeval='SEALED_NOT_ACCESSED')
    if json.loads(REPORT.read_text()) != expected:
        raise ValueError('final delivery amendment drift')
    return True


if __name__ == '__main__':
    validate_current()
    print('FINAL_DELIVERY_CURRENT_RUNTIME_AND_PRESERVED_HISTORY_PASS')
