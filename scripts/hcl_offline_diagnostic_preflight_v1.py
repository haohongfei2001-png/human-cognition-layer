"""Pin the current original-flute request; reuse the PR415 offline chain only.

Controls are fixed injected replies, never the historical reply, independent
semantic review, or evidence of efficacy. No transport/client can be supplied.
A future integration must preserve these complete inputs, durable diagnostics,
original receipt/capture trust anchors and the separate independent success gate.
This module creates no live route, grant, paid package or historical rewrite.
"""
import hashlib
import json
from pathlib import Path

from scripts import hcl_offline_diagnostic_export_v1 as r
from scripts import hcl_offline_diagnostic_public_v1 as p
from scripts.hcl_offline_diagnostic_reference import DIRECTORY

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = Path(__file__).with_suffix('.json')
MANIFEST_SHA256 = '42d1005dbc03a1cea093ac777b23b73af4326b0add0e57db2aa83d591a06aa2a'
CONTROLS = {
    'malformed_json': ('INVALID_PLANNING_JSON', 'PLANNING_RESPONSE_VALIDATION'),
    'invalid_typed_plan': ('operation bound exceeded', 'PLANNING_RESPONSE_VALIDATION'),
    'invalid_typed_entry': ('INVALID_READER_INPUT_MODE', 'PLANNING_RESPONSE_VALIDATION'),
    'blocked_source_entry': ('SOURCE_ENTRY_NECESSARY_CONDITION_FAILED_BEFORE_NATIVE', 'ENTRY_ADMISSION'),
    'valid_empty_plan': ('NATIVE_HCL_RESULT_REQUIRED_BEFORE_ANSWER', 'NATIVE_RESULT_ADMISSION'),
}


def _read_json(path, *, file_sha256=None):
    """Never silently repair ambiguous or non-JSON durable originals."""
    def unique(pairs):
        value = {}
        for key, child in pairs:
            if key in value:
                raise ValueError('DUPLICATE_JSON_KEY')
            value[key] = child
        return value
    data = Path(path).read_bytes()
    if file_sha256 is not None and hashlib.sha256(data).hexdigest() != file_sha256:
        raise ValueError('VERIFIED_FILE_CHANGED_DURING_READ')
    if len(data) > 1048576:
        raise ValueError('BOUNDED_JSON_FILE_REQUIRED')
    value = json.loads(data, object_pairs_hook=unique)
    r.require_plain_json(value)
    return value


def preflight():
    """Fail before FakeClient construction/output on input/config/runtime drift."""
    if r.file_sha(MANIFEST) != MANIFEST_SHA256:
        raise ValueError('PREFLIGHT_MANIFEST_DRIFT')
    manifest = _read_json(MANIFEST, file_sha256=MANIFEST_SHA256)
    path = ROOT / manifest['cases_file']
    if r.file_sha(path) != manifest['cases_file_sha256']:
        raise ValueError('ORIGINAL_CASES_FILE_DRIFT')
    expected = manifest['expected_package']
    if r.runtime_digest(ROOT) != expected['runtime_sha256']:
        raise ValueError('CURRENT_RUNTIME_DRIFT')
    for name, pin in expected['reference_helper_files'].items():
        if r.file_sha(DIRECTORY / name) != pin:
            raise ValueError('ARCHIVED_HELPER_HASH_CHANGED')
    package = r.OfflinePackage.build(_read_json(path, file_sha256=manifest['cases_file_sha256']), ROOT)
    if r.canonical(package.value) != r.canonical(expected):
        raise ValueError('CURRENT_REQUEST_OR_CONFIGURATION_DRIFT')
    return package


def _response(control, package):
    if control == 'malformed_json':
        return '{OFFLINE_INJECTED_MALFORMED_PLANNER_CANARY'
    proposal = dict(task='OFFLINE_INJECTED_PLANNER_CANARY', operations=[], limitations=[])
    if control == 'invalid_typed_plan':
        proposal['operations'] = {}
    elif control in ('invalid_typed_entry', 'blocked_source_entry'):
        case = package.cases[0]
        operation = dict(capability='B02', question=case['question'],
                         source_ids=[case['sources'][0]['source_id']], bindings=[])
        if control == 'invalid_typed_entry':
            operation.update(capability='B01', input_mode=False)
        proposal['operations'] = [operation]
    return json.dumps(proposal)


def _unreviewed_binding(package, evidence):
    """An explicitly non-passing identity fixture; no semantic judgment is made."""
    arm = evidence['arms'][0]
    def checks(ids):
        return [dict(id=item, passed=False, source_evidence='NOT_ASSESSED_OFFLINE_CONTROL',
                     answer_evidence='NO_FINAL_ANSWER') for item in ids]
    return dict(schema=p.REVIEW_SCHEMA, authorization_ref=r.AUTH,
        package_sha256=r.digest(package.value), packet_sha256=r.digest(package.packet),
        evidence_sha256=r.digest(evidence), final_answer_sha256=arm['final_answer_sha256'],
        request_diagnostics_sha256=r.digest(arm['request_diagnostics']),
        native_review_sha256=arm['native_review_sha256'],
        reviewer_role='OFFLINE_INJECTED_CONTROL_IDENTITY_ONLY',
        same_smoke_and_rules_fixed_before_entry_contract_smoke_output=False,
        gates={key: False for key in p.GATES},
        obligations=checks(p.obligation_ids(package.packet['cases'][0])),
        smoke_semantics=checks(['S1', 'S2', 'S3', 'S4']),
        relevant_native_capability_ids=[], critical_failure_tags=[], overall_pass=False)


def _original_native(receipt, path):
    if Path(path).exists():
        native = _read_json(path)
        if type(native) is not dict:
            raise ValueError('EXACT_ORIGINAL_NATIVE_BUNDLE_REQUIRED')
        return native
    arms = receipt.get('arms') if type(receipt) is dict else None
    if type(arms) is not list or len(arms) != 1 or type(arms[0]) is not dict:
        raise ValueError('EXACT_ORIGINAL_RECEIPT_ARM_REQUIRED')
    arm = arms[0]
    expected = dict(capture_failure='POST_RUNTIME_CAPTURE_FAILED', native_review_available=False,
                    native_review_sha256=None, native_projection_status='NOT_CAPTURED',
                    native_projection_sha256=None, native_integrity_status='NOT_CAPTURED')
    if any(key not in arm or type(arm[key]) is not type(value) or arm[key] != value
           for key, value in expected.items()):
        raise ValueError('RECEIPT_DECLARED_CAPTURE_MISSING')
    return None


def validate_saved_binding(package, evidence, review, *, original_receipt_path,
                           original_native_bundle_path, original_receipt_sha256,
                           original_native_bundle_sha256):
    """Reload trusted originals independently of public/review projections.

    Expected hashes must be retained by the caller from its trusted capture,
    never derived from mutable public evidence. Replacing both originals and
    the caller's trust anchors is outside hash integrity's authentication scope.
    Even a valid stopped binding does not pass the independent success gate.
    """
    r.require_package(package)
    if r.canonical(package.value) != r.canonical(preflight().value):
        raise ValueError('CURRENT_PREFLIGHT_PACKAGE_REQUIRED')
    receipt = _read_json(original_receipt_path)
    if r.digest(receipt) != r.exact_sha(original_receipt_sha256):
        raise ValueError('TRUSTED_ORIGINAL_HASH_CHANGED')
    native_bundle = _original_native(receipt, original_native_bundle_path)
    if native_bundle is not None or original_native_bundle_sha256 is not None:
        if native_bundle is None or original_native_bundle_sha256 is None or r.digest(native_bundle) != r.exact_sha(original_native_bundle_sha256):
            raise ValueError('TRUSTED_ORIGINAL_HASH_CHANGED')
    fresh = p.export(receipt, package, native_bundle=native_bundle)
    if r.canonical(evidence) != r.canonical(fresh):
        raise ValueError('EXACT_ORIGINAL_DURABLE_EXPORT_REQUIRED')
    return p.validate_review_binding(package, evidence, review)


def run_control(control, directory):
    """One fixed fake planning reply on the unchanged original smoke, then stop."""
    if type(control) is not str or control not in CONTROLS:
        raise ValueError('FIXED_INJECTED_OFFLINE_CONTROL_REQUIRED')
    package = preflight()
    directory = Path(directory)
    client = r.FakeClient([_response(control, package)])
    r.run_offline(client, package, 1, directory)
    receipt_path = directory / 'receipt.json'
    native_path = directory / 'native-review-private.json'
    # Export the durable diagnosis even when capture cannot be loaded or validated.
    # Subsequent original binding may fail; it cannot erase that public diagnosis.
    evidence = p.export_terminal(directory, package)
    receipt = _read_json(receipt_path)
    native = _original_native(receipt, native_path)
    arm = evidence['arms'][0]
    code, stage = CONTROLS[control]
    if (arm['orchestration_failure'] != dict(code=code, stage=stage)
            or len(client.calls) != 1 or [c['phase'] for c in evidence['calls']] != ['planning']
            or evidence['status'] != 'STOPPED_NO_RETRY'
            or evidence['reserved_cny'] != str(r.HOLD_CNY['planning'])
            or arm['final_text'] is not None or arm['native_results'] != 0):
        raise ValueError('INJECTED_CONTROL_DID_NOT_STOP_AS_EXPECTED')
    review = _unreviewed_binding(package, evidence)
    anchors = dict(original_receipt_sha256=r.digest(receipt),
                   original_native_bundle_sha256=r.digest(native) if native is not None else None)
    validate_saved_binding(package, evidence, review, original_receipt_path=receipt_path,
                           original_native_bundle_path=native_path, **anchors)
    r.save(directory / 'source-review-binding.json', review)
    summary = dict(schema='hcl-offline-current-smoke-control-v1', control=control,
        claim='FIXED_INJECTED_OFFLINE_CONTROL_NOT_HISTORICAL_DIAGNOSIS_OR_SEMANTIC_REVIEW',
        manifest_sha256=MANIFEST_SHA256, package_sha256=r.digest(package.value),
        request_sha256=evidence['calls'][0]['request_sha256'],
        public_sha256=r.digest(evidence), source_review_sha256=r.digest(review), **anchors,
        orchestration_failure=arm['orchestration_failure'], capture_failure=arm['capture_failure'],
        native_publication_status=evidence['native_publication_status'],
        native_integrity_status=arm['native_integrity_status'],
        simulated_reserved_cny=evidence['reserved_cny'], actual_spend_cny=evidence['actual_spend_cny'],
        provider_calls=evidence['provider_calls'], live_execution_authorized=False, efficacy_verified=False)
    r.save(directory / 'preflight-control.json', summary)
    return summary
