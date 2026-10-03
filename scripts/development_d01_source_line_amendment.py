"""Bounded D01 line admission without rewriting native parsers or old evidence."""
import hashlib,json
from pathlib import Path
from scripts.serious_eval_contract import runtime_digest
from scripts.development_universal_commitment_amendment import HISTORICAL_PINS as PRIOR_PINS
from scripts.development_drc008_replay import validate_archive
from scripts.development_runtime_amendment_v24 import validate_current as validate_v24

REPORT=Path('reports/HCL_D01_SOURCE_LINE_BOUNDARY_AMENDMENT.json')
HISTORICAL_PINS=dict(PRIOR_PINS,**{'scripts/development_universal_commitment_amendment.py': '8d9d29f689e2039c3ddbf4f4dd42738080721108744471f0e0d6c5d7a31a6604', 'reports/HCL_UNIVERSAL_COMMITMENT_AMENDMENT.json': '19120e391d6e8d9539fbc7fe76c174c33623b02d922378d076e78981a827a0d7', 'docs/HCL_UNIVERSAL_COMMITMENT_ENTRY.md': '1894ec6182669aa083e5814133f0c6e8c8d85a90444ed19758b111b0c4186af0', 'reports/HCL_UNIVERSAL_COMMITMENT_VALIDATION.json': 'd15672ed32d19f544d7ce4a74dc626e058a8daa1ecdc42af7201435bd4851717'})
PREVIOUS_FILES={'hcl/cognition/capability_catalog.py': '4e32b113204e44e85baa294c86742a6d13fb84cf806e2057128f6e248279460c', 'hcl/cognition/universal_entry.py': '1ce2fc49f0023e2d2133d758703728b56bcc9dbf68746f16a05841ea0ed9c7e8'}
ADDITIONS={'hcl/cognition/capability_catalog.py': 'LF or CRLF source separators only; other line separators are explicitly unsupported. ', 'hcl/cognition/universal_entry.py': "            source=self.sources[ids[0]]['text']\n            if '\\r' in source.replace('\\r\\n','') or any(c in source for c in '\\v\\f\\x1c\\x1d\\x1e\\x85\\u2028\\u2029'):\n                return dict(capability=cid,status='D01_REQUIRES_LF_OR_CRLF_SOURCE',executed=False)\n"}
PREVIOUS_RUNTIME='0638c2a372b95eb3befd3609455d019c497050a9293ac61a0d7e9d3d8a204c05'


def validate_current(*,current_digest=None):
    for path,expected in HISTORICAL_PINS.items():
        if hashlib.sha256(Path(path).read_bytes()).hexdigest()!=expected:
            raise ValueError('historical amendment or diagnostic evidence changed')
    archive=validate_archive();validate_v24(current_digest=archive['runtime_sha256'])
    for path,expected in PREVIOUS_FILES.items():
        text=Path(path).read_bytes().decode();addition=ADDITIONS[path]
        if text.count(addition)!=1 or hashlib.sha256(text.replace(addition,'',1).encode()).hexdigest()!=expected:
            raise ValueError('unrelated runtime outside reviewed scope changed')
    files={str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in Path('hcl').rglob('*.py')}
    if not set(PREVIOUS_FILES)<=files.keys():raise ValueError('amended runtime file missing')
    files.update(PREVIOUS_FILES)
    if hashlib.sha256(json.dumps(files,sort_keys=True,separators=(',',':')).encode()).hexdigest()!=PREVIOUS_RUNTIME:
        raise ValueError('unrelated runtime outside reviewed scope changed')
    expected={'schema': 'hcl-d01-source-line-boundary-amendment-v1', 'previous_hcl_runtime_sha256': '0638c2a372b95eb3befd3609455d019c497050a9293ac61a0d7e9d3d8a204c05', 'amended_hcl_runtime_sha256': 'e1ce80691173efd9e76b5f3466d9d573fc9da7e5c7c125ce8003a8383118ca2d', 'changed_runtime_files': ['hcl/cognition/capability_catalog.py', 'hcl/cognition/universal_entry.py'], 'reason': 'FAIL_CLOSED_D01_ADMISSION_BEFORE_INCONSISTENT_NATIVE_LINE_INDEX', 'supported_source_separators': ['LF', 'CRLF'], 'rejected_source_separators': ['CR', 'VT', 'FF', 'U+001C', 'U+001D', 'U+001E', 'U+0085', 'U+2028', 'U+2029'], 'native_invoked_on_refusal': False, 'original_source_bytes_preserved': True, 'selected_source_only': True, 'native_d01_or_b02_changed': False, 'retained_native_format_gap': 'UNREPAIRED_OUTSIDE_BOUNDED_ORDINARY_ADAPTER', 'line_separator_conversion': False, 'source_or_transport_budget_changed': False, 'adapter_added': False, 'provider_calls': 0, 'provider_spend_usd': 0, 'authorized_additional_calls': 0, 'historical_answers_rescored': False, 'model_selection_efficacy_verified': False, 'longmemeval': 'SEALED_NOT_ACCESSED'}
    expected['amended_hcl_runtime_sha256']=current_digest or runtime_digest()
    if json.loads(REPORT.read_text())!=expected:raise ValueError('D01 source line boundary amendment drift')
    return True


if __name__=='__main__':validate_current();print('D01_SOURCE_LINE_BOUNDARY_AND_IMMUTABLE_EVIDENCE_PASS')
