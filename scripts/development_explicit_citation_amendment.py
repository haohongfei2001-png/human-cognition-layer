"""Explicit final citation shape; no historical experiment or source audit changes."""
import hashlib
import json
from pathlib import Path

from scripts import development_final_delivery_amendment as previous
from scripts.serious_eval_contract import runtime_digest

BASELINE = '2fe35047ffb42327eb72817769300dfaecdeeda3'
PREVIOUS_RUNTIME = '14dbb5805858d41ade7ba1135a22ef6e3b1c4327ae7fad34173274d84b83166c'
REPORT = Path('reports/HCL_EXPLICIT_CITATION_CONTRACT_AMENDMENT.json')
HISTORICAL_PINS = previous.HISTORICAL_PINS
ADDITIONAL_HISTORY_PINS = {'scripts/development_final_delivery_amendment.py': 'db78628bd596f7cabdce211bfb03c3e1352a51d542056954fbaed67cb9d2dbbd', 'reports/HCL_FINAL_DELIVERY_AMENDMENT.json': 'd312bcb3b5c8485a4fa81931a6bb8aa3c32ec3657d638b3ef4d5033fec586069', 'docs/HCL_FINAL_DELIVERY_DIAGNOSTICS.md': 'e78fd00ec286b978e201058404edb74a7c1ea0f705f56bb3af23205ff4d336df'}
PREVIOUS_FILES = {'hcl/cognition/reader_entry.py': '9125524e4843849b41901142e7990ca404a7932f3199e04019b1de7a6dabd84f', 'hcl/cognition/universal_entry.py': '81be72668ff693acd9e1b45f05cf23e0d299da5589bf258bf06f528c7e33cd4a'}
REVIEWED_FILES = {'hcl/cognition/reader_entry.py': '87672344e1988700a9f3fb81f0a62b4c6f216feb1d641604b3d6bff53129d4af', 'hcl/cognition/universal_entry.py': '40307d2b68a0e17601b5012fe7858aa79307a58bc118d1c30bea55dbdbc2f897'}


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def validate_preserved_history():
    for path, expected in {**HISTORICAL_PINS, **ADDITIONAL_HISTORY_PINS}.items():
        if digest(Path(path).read_bytes()) != expected:
            raise ValueError('historical amendment or diagnostic evidence changed')
    previous.validate_preserved_history()
    return True


def expected_report(current_digest=None):
    return dict(schema='hcl-explicit-citation-contract-amendment-v1',
        baseline_commit=BASELINE, previous_hcl_runtime_sha256=PREVIOUS_RUNTIME,
        amended_hcl_runtime_sha256=current_digest or runtime_digest(),
        changed_runtime_files=sorted(PREVIOUS_FILES),
        reason='ALIGN_UNIVERSAL_GENERATION_AND_EXPLICIT_CITATION_OBJECT_CONTRACT',
        entry='UniversalHCL.answer', legacy_reader_policy_value_unchanged=True,
        required_citation_fields=['source_id', 'version', 'quote'],
        optional_citation_fields=['start'], start_null_allowed=False,
        raw_answers_rewritten=False, citation_fields_fabricated=False,
        existing_source_audit_unchanged=True, empty_citations_policy_unchanged=True,
        strict_comparison_acceptance_unchanged=True, historical_executors_unchanged=True,
        model_or_token_defaults_changed=False, provider_phases_changed=False,
        provider_calls=0, provider_spend_usd=0, authorized_additional_calls=0,
        retries_added=0, historical_answers_rescored=False,
        historical_d01_cause_identified=False, model_compliance_verified=False,
        answer_quality_improvement_claimed=False, longmemeval='SEALED_NOT_ACCESSED')


def validate_current(*, current_digest=None):
    validate_preserved_history()
    files = {str(p): digest(p.read_bytes()) for p in Path('hcl').rglob('*.py')}
    for name, expected in REVIEWED_FILES.items():
        if files.get(name) != expected:
            raise ValueError('unrelated runtime outside reviewed scope changed')
    files.update(PREVIOUS_FILES)
    if digest(json.dumps(files, sort_keys=True, separators=(',', ':')).encode()) != PREVIOUS_RUNTIME:
        raise ValueError('unrelated runtime outside reviewed scope changed')
    if json.loads(REPORT.read_text()) != expected_report(current_digest):
        raise ValueError('explicit citation contract amendment drift')
    return True


if __name__ == '__main__':
    validate_current()
    print('EXPLICIT_CITATION_CONTRACT_AND_IMMUTABLE_HISTORY_PASS')
