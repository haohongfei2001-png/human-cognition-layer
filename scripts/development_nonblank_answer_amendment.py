"""Minimal ordinary-answer presence guard; native tools and historical results stay frozen."""
import hashlib,json
from pathlib import Path
from scripts.serious_eval_contract import runtime_digest
from scripts.development_c02_planned_input_amendment import HISTORICAL_PINS as PRIOR_PINS
from scripts.development_drc008_replay import validate_archive
from scripts.development_runtime_amendment_v24 import validate_current as validate_v24

REPORT=Path('reports/HCL_NONBLANK_ANSWER_AMENDMENT.json')
HISTORICAL_PINS=dict(PRIOR_PINS,**{'scripts/development_c02_planned_input_amendment.py': '189014a3e6393db3ef01698f960ecd2e3ce83ce42059523b3e31fdedc896663f', 'reports/HCL_C02_PLANNED_INPUT_AMENDMENT.json': '41d0add2b43bdb33602d98d28ee658293974aa6a500c5a39a0adaaca94e52bda', 'docs/HCL_C02_PLANNED_INPUT.md': '75163b5fb3cdab3956b7a95c193a1f55887c897e8abece0114f50bc2a80cba01', 'reports/HCL_C02_PLANNED_INPUT_VALIDATION.json': 'a5ef82e0aac426ff4dd34eb492e25036c424c22b4f6793c6c5874fd93bebc622', 'reports/HCL_C02_PLANNED_INPUT_WITNESS.json': '913d8e4bc04b34bececaaee2e33866efbbb607a1ba5ab2e27782690863842ee3'})
PREVIOUS_FILES={'hcl/cognition/universal_entry.py': '86220045affc5dcd961fb20f8c2f09fdee42f9d9af872e1ed561f0db40c29ca2'}
REVIEWED_FILES={'hcl/cognition/universal_entry.py': 'ae854eb6630474bdbf673239679652f477d8d4a9c6513ecffd2740d1b5ca67f3'}
PREVIOUS_RUNTIME='38ee8c979847ccf68f32747d5485d0494274fdb65165d1bde7fe7a08fc4dc9a4'


def validate_current(*,current_digest=None):
    for path,expected in HISTORICAL_PINS.items():
        if hashlib.sha256(Path(path).read_bytes()).hexdigest()!=expected:
            raise ValueError('historical amendment or diagnostic evidence changed')
    archive=validate_archive();validate_v24(current_digest=archive['runtime_sha256'])
    for path,expected in REVIEWED_FILES.items():
        if hashlib.sha256(Path(path).read_bytes()).hexdigest()!=expected:
            raise ValueError('unrelated runtime outside reviewed scope changed')
    files={str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in Path('hcl').rglob('*.py')}
    if not set(PREVIOUS_FILES)<=files.keys():raise ValueError('amended runtime file missing')
    files.update(PREVIOUS_FILES)
    if hashlib.sha256(json.dumps(files,sort_keys=True,separators=(',',':')).encode()).hexdigest()!=PREVIOUS_RUNTIME:
        raise ValueError('unrelated runtime outside reviewed scope changed')
    expected={'schema': 'hcl-nonblank-answer-amendment-v1', 'previous_hcl_runtime_sha256': '38ee8c979847ccf68f32747d5485d0494274fdb65165d1bde7fe7a08fc4dc9a4', 'amended_hcl_runtime_sha256': '90737b3ed772f65851553d8a673112eae50f2781185d8b5b4ccd127cdfb8663b', 'changed_runtime_files': ['hcl/cognition/universal_entry.py'], 'reason': 'REJECT_EMPTY_OR_UNICODE_WHITESPACE_ONLY_ORDINARY_FINAL_ANSWERS', 'entry': 'UniversalHCL.answer', 'whitespace_definition': 'PYTHON_STR_STRIP_UNICODE_WHITESPACE', 'failure_code': 'NONBLANK_FINAL_ANSWER_REQUIRED', 'validation_after_existing_schema_check': True, 'raw_bounded_answer_preserved': True, 'returned_native_results_preserved': True, 'successful_reservations_and_usage_preserved': True, 'valid_nonblank_text_rewritten': False, 'source_citation_audit_changed': False, 'legacy_quote_location_audit_changed': False, 'provider_phases_changed': False, 'additional_provider_calls': 0, 'retries_added': 0, 'native_parsers_changed': False, 'model_or_token_defaults_changed': False, 'output_size_bounds_changed': False, 'provider_calls': 0, 'provider_spend_usd': 0, 'authorized_additional_calls': 0, 'historical_answers_rescored': False, 'semantic_answer_quality_certified': False, 'longmemeval': 'SEALED_NOT_ACCESSED'}
    expected['amended_hcl_runtime_sha256']=current_digest or runtime_digest()
    if json.loads(REPORT.read_text())!=expected:raise ValueError('nonblank answer amendment drift')
    return True


if __name__=='__main__':validate_current();print('NONBLANK_ANSWER_AND_IMMUTABLE_EVIDENCE_PASS')
