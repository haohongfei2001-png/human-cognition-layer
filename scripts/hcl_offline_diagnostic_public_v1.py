"""Offline-only v1 diagnostic projection. No grants, publication or live authority.

The ordinary receipt and semantic checks below retain the reviewed Oct 8 logic;
only offline identity, required diagnostic fields and failure hash binding differ.
Native operation/argument schemas are reused unchanged, without repair.
"""
from decimal import Decimal
import hashlib
import json

from scripts import hcl_offline_diagnostic_export_v1 as r
from scripts.hcl_offline_diagnostic_reference import _public, _native, _reference

PUBLIC_SCHEMA = 'hcl-offline-diagnostic-public-evidence-v1'
REVIEW_SCHEMA = 'hcl-offline-diagnostic-source-review-v1'
ARM_STATUSES = _public.ARM_STATUSES
CALL_STATUSES = _public.CALL_STATUSES
INVOCATIONS = _public.INVOCATIONS
DELIVERY = _public.DELIVERY
FAILURES = _public.FAILURES
GATES = _public.GATES
money = _public.money
duration = _public.duration
clean_metrics = _public.clean_metrics
clean_runtime_metrics = _public.clean_runtime_metrics
clean_response_metadata = _public.clean_response_metadata
clean_entry_requirements = _public.clean_entry_requirements
validate_actual_entry_requirements = _public.validate_actual_entry_requirements
obligation_ids = _public.obligation_ids
fixed_denominator_positions = _public.fixed_denominator_positions


def validate_offline_flags(value, scope):
    """Exact offline claims at their declared wrapper scope, never inferred."""
    fields = {'live_execution_authorized', 'actual_spend_cny', 'efficacy_verified',
              'i02_certified', 'semantic_certification', 'reviewed_native_relevance'}
    expected = {
        'receipt': dict(live_execution_authorized=False, actual_spend_cny='0'),
        'public': dict(live_execution_authorized=False, actual_spend_cny='0',
                       efficacy_verified=False, i02_certified=False),
        'native': dict(live_execution_authorized=False, semantic_certification=False),
    }[scope]
    if type(value) is not dict or (set(value) & fields) != set(expected) or any(
            type(value[key]) is not type(fixed) or value[key] != fixed
            for key, fixed in expected.items()):
        raise ValueError('EXACT_OFFLINE_FLAGS_AND_SCOPE_REQUIRED')


def clean_diagnostic_field(arm):
    if type(arm) is not dict or 'orchestration_failure' not in arm:
        raise ValueError('REQUIRED_NULLABLE_ORCHESTRATION_FAILURE')
    return r.clean_diagnostic(arm['orchestration_failure'])


def clean_capture_field(arm):
    if 'capture_failure' not in arm or (arm['capture_failure'] is not None and
            (type(arm['capture_failure']) is not str or arm['capture_failure'] != 'POST_RUNTIME_CAPTURE_FAILED')):
        raise ValueError('EXACT_CAPTURE_FAILURE_REQUIRED')
    return arm['capture_failure']


def export_native_bundle(bundle, receipt, package):
    """Local fixture projection, never permission to publish source/native data."""
    if type(bundle) is not dict or set(bundle) != {'schema', 'package_sha256', 'stage', 'reviews'} or bundle['schema'] != 'hcl-entry-contract-smoke-private-native-review-bundle-v1' or bundle['package_sha256'] != r.digest(package.value) or type(bundle['stage']) is not int or bundle['stage'] != 1 or type(bundle['reviews']) is not list or len(bundle['reviews']) > 1:
        raise ValueError('EXACT_OFFLINE_NATIVE_BUNDLE_REQUIRED')
    _native._bind_bundle_to_receipt(bundle, receipt, package)
    cases = {case['case_id']: case for case in package.cases}
    records = [_native.validate_captured_native_record(row, cases[row['case_id']], package.value['runtime_sha256']) for row in bundle['reviews']]
    return dict(schema='hcl-offline-diagnostic-native-evidence-v1',
                package_sha256=r.digest(package.value), packet_sha256=package.value['packet_sha256'],
                receipt_sha256=r.digest(receipt), stage=1, records=records,
                record_count=len(records), semantic_certification=False, live_execution_authorized=False)


def validate_success_native_evidence(evidence, package):
    """Check disclosed native integrity after the original-export comparison.

    Reconstruct only a complete disclosed capture and pass it to the unchanged
    native validator. Replay checks arguments/results against current sources;
    by itself this does not prove which valid operation was originally executed.
    """
    value = evidence.get('approved_native_evidence')
    if value is not None: validate_offline_flags(value, 'native')
    keys = {'schema', 'package_sha256', 'packet_sha256', 'receipt_sha256', 'stage',
            'records', 'record_count', 'semantic_certification', 'live_execution_authorized'}
    if evidence.get('native_publication_status') != 'OFFLINE_LOCAL_NATIVE_EVIDENCE' or type(value) is not dict or set(value) != keys or value['schema'] != 'hcl-offline-diagnostic-native-evidence-v1' or value['package_sha256'] != r.digest(package.value) or value['packet_sha256'] != package.value['packet_sha256'] or value['receipt_sha256'] != evidence.get('receipt_sha256') or type(value['stage']) is not int or value['stage'] != 1 or value['semantic_certification'] is not False or value['live_execution_authorized'] is not False:
        raise ValueError('ACTUAL_OFFLINE_NATIVE_EVIDENCE_REQUIRED_FOR_SUCCESS')
    records = value['records']
    case = package.cases[0]
    if type(records) is not list or len(records) != 1 or type(value['record_count']) is not int or value['record_count'] != 1 or type(records[0]) is not dict or records[0].get('case_id') != case['case_id']:
        raise ValueError('EXACT_COMPLETE_NATIVE_RECORD_REQUIRED_FOR_SUCCESS')
    record = records[0]; operations = record.get('operations')
    arm = evidence['arms'][0]
    if type(operations) is not list or not 1 <= len(operations) <= 3 or len(operations) != len(arm['selected_capabilities']) or any(type(operation) is not dict or not {'source_validated_arguments', 'native_result_and_policy'} <= set(operation) for operation in operations):
        raise ValueError('COMPLETE_NATIVE_OPERATIONS_REQUIRED_FOR_SUCCESS')
    _native._bind_published_to_receipt(value, evidence, package)
    captured = _reference.private_native_review(case, dict(
        plan={'operations': [operation['source_validated_arguments'] for operation in operations]},
        operations=[operation['native_result_and_policy'] for operation in operations]))
    validated = _native.validate_captured_native_record(captured, case, package.value['runtime_sha256'])
    if r.canonical(validated) != r.canonical(record):
        raise ValueError('EXACT_SOURCE_VALIDATED_NATIVE_RECORD_REQUIRED_FOR_SUCCESS')
    validate_actual_entry_requirements(evidence, package)
    return True


REVIEW_KEYS = {'schema', 'authorization_ref', 'package_sha256', 'packet_sha256',
    'evidence_sha256', 'final_answer_sha256', 'request_diagnostics_sha256',
    'native_review_sha256', 'reviewer_role',
    'same_smoke_and_rules_fixed_before_entry_contract_smoke_output', 'gates',
    'obligations', 'smoke_semantics', 'relevant_native_capability_ids',
    'critical_failure_tags', 'overall_pass'}


def validate_review_binding(package, evidence, review):
    """Identity/hash check independent of success, judgment or live permission.

    A stopped receipt can be correctly reviewed and hash-bound. That never makes
    it successful. The whole evidence hash binds diagnostics and native records.
    This checks supplied artifact/review consistency, not original execution
    provenance; only the success gate compares against separately supplied originals.
    """
    r.require_package(package); package.verify()
    r.require_plain_json(evidence); r.require_plain_json(review)
    validate_offline_flags(evidence, 'public')
    if type(evidence) is not dict or evidence.get('schema') != PUBLIC_SCHEMA or evidence.get('mode') != r.MODE or evidence.get('authorization_ref') != r.AUTH or evidence.get('package_sha256') != r.digest(package.value) or evidence.get('packet_sha256') != r.digest(package.packet) or evidence.get('runtime_sha256') != package.value['runtime_sha256'] or type(evidence.get('stage')) is not int or evidence['stage'] != 1:
        raise ValueError('EXACT_REVIEW_EVIDENCE_IDENTITY_REQUIRED')
    r.exact_sha(evidence.get('receipt_sha256'))
    arms = evidence.get('arms')
    if type(arms) is not list or len(arms) != 1 or (arms[0].get('case_id'), arms[0].get('arm')) != r.order(package.cases, 1)[0]:
        raise ValueError('EXACT_REVIEW_ARM_IDENTITY_REQUIRED')
    arm = arms[0]; clean_diagnostic_field(arm); clean_capture_field(arm)
    captured = evidence.get('approved_native_evidence')
    if captured is not None:
        validate_offline_flags(captured, 'native')
        if type(captured) is not dict or captured.get('schema') != 'hcl-offline-diagnostic-native-evidence-v1' or captured.get('package_sha256') != evidence['package_sha256'] or captured.get('packet_sha256') != evidence['packet_sha256'] or captured.get('receipt_sha256') != evidence.get('receipt_sha256'):
            raise ValueError('EXACT_NATIVE_EVIDENCE_RECEIPT_LINK_REQUIRED')
        _native._bind_published_to_receipt(captured, evidence, package)
    if type(review) is not dict or set(review) != REVIEW_KEYS or review.get('schema') != REVIEW_SCHEMA or review.get('authorization_ref') != r.AUTH or review.get('package_sha256') != r.digest(package.value) or review.get('packet_sha256') != r.digest(package.packet) or review.get('evidence_sha256') != r.digest(evidence) or review.get('final_answer_sha256') != arm['final_answer_sha256'] or review.get('request_diagnostics_sha256') != r.digest(arm['request_diagnostics']) or review.get('native_review_sha256') != arm.get('native_review_sha256'):
        raise ValueError('EXACT_REVIEW_HASH_BINDING_REQUIRED')
    return True


def export(receipt, package, *, native_bundle=None):
    r.require_package(package)
    r.require_plain_json(receipt)
    validate_offline_flags(receipt, 'receipt')
    package.verify(); stage = receipt['stage']
    offline = True
    expected_mode = r.MODE
    expected_schema = r.RECEIPT_SCHEMA
    if type(stage) is not int or stage not in (1,) or receipt.get('schema') != expected_schema or receipt.get('mode') != expected_mode or receipt.get('currency') != 'CNY' or receipt.get('usd_reference_only') is not True or receipt.get('authorization_ref') != r.AUTH or receipt.get('package_sha256') != r.digest(package.value):
        raise ValueError('EXACT_OFFLINE_AUTHORITY_IDENTITY_REQUIRED')
    if receipt.get('status') not in {'COMPLETED_ONE_PASS', 'STOPPED_NO_RETRY'} or receipt.get('budget_state') != 'CLOSED_NO_TRANSFER_NO_RETRY' or type(receipt.get('remaining_authorized_calls')) is not int or receipt['remaining_authorized_calls'] != 0 or receipt.get('remaining_authorized_cny') != '0':
        raise ValueError('EXACT_TERMINAL_CLOSED_RECEIPT_REQUIRED')
    schedule = r.order(package.cases, stage)
    if [(a.get('case_id'), a.get('arm')) for a in receipt['arms']] != schedule:
        raise ValueError('ALL_SCHEDULED_POSITIONS_REQUIRED')
    arms = []
    for row in receipt['arms']:
        if row.get('status') not in ARM_STATUSES or type(row.get('citations_accepted')) is not bool:
            raise ValueError('EXACT_ARM_STATUS_REQUIRED')
        final = row.get('final_text')
        if final is not None and (not isinstance(final, str) or len(final) > 64000):
            raise ValueError('BOUNDED_UNCHANGED_FINAL_REQUIRED')
        sha = hashlib.sha256(final.encode()).hexdigest() if final is not None else None
        if row.get('final_answer_sha256') != sha or row.get('final_fields') != r.final_fields(final):
            raise ValueError('UNCHANGED_FINAL_HASH_AND_FIELDS_REQUIRED')
        if row.get('final_delivery_code') not in DELIVERY or type(row.get('native_results')) is not int or not 0 <= row['native_results'] <= 3:
            raise ValueError('KNOWN_NATIVE_AND_DELIVERY_STATE_REQUIRED')
        diagnostic = clean_diagnostic_field(row)
        out = dict(orchestration_failure=diagnostic, capture_failure=clean_capture_field(row), case_id=row['case_id'], arm=row['arm'], status=row['status'], final_text=final, final_fields=r.final_fields(final), final_answer_sha256=sha, citations_accepted=row['citations_accepted'], native_results=row['native_results'], final_delivery_code=row['final_delivery_code'])
        if type(row.get('native_review_available')) is not bool:
            raise ValueError('EXACT_NATIVE_REVIEW_AVAILABILITY_REQUIRED')
        out['native_review_available'] = row['native_review_available']
        out['entry_requirements'] = clean_entry_requirements(row.get('entry_requirements'))
        out['native_review_sha256'] = r.exact_sha(row['native_review_sha256']) if row.get('native_review_sha256') is not None else None
        if row['native_review_available'] and out['native_review_sha256'] is None:
            raise ValueError('EXACT_PRIVATE_NATIVE_REVIEW_HASH_REQUIRED')
        projection_status = row.get('native_projection_status')
        if projection_status not in ('NOT_CAPTURED', 'CAPTURED', 'REJECTED_UNAVAILABLE'):
            raise ValueError('EXACT_NATIVE_PROJECTION_CAPTURE_STATE_REQUIRED')
        projection_hash = row.get('native_projection_sha256')
        if projection_status == 'CAPTURED':
            r.exact_sha(projection_hash)
            if not row['native_review_available']: raise ValueError('CAPTURE_PROJECTION_REQUIRES_NATIVE_REVIEW')
        elif projection_hash is not None:
            raise ValueError('NO_UNCAPTURED_NATIVE_PROJECTION_HASH')
        out.update(native_projection_status=projection_status, native_projection_sha256=projection_hash)
        integrity_status = row.get('native_integrity_status')
        if integrity_status not in ('NOT_CAPTURED', 'VALIDATED', 'REJECTED_UNAVAILABLE') or (integrity_status == 'VALIDATED' and (not row['native_review_available'] or projection_status != 'CAPTURED')):
            raise ValueError('EXACT_NATIVE_INTEGRITY_STATE_REQUIRED')
        out['native_integrity_status'] = integrity_status
        for key in ('selected_capabilities', 'executed_capabilities', 'checked_treatment'):
            values = row.get(key)
            if not isinstance(values, list) or len(values) > 3 or any(v not in r.CATALOG for v in values):
                raise ValueError('ALLOWLISTED_NATIVE_IDS_REQUIRED')
            out[key] = list(values)
        if any(v not in out['selected_capabilities'] for v in out['executed_capabilities']) or any(v not in out['executed_capabilities'] for v in out['checked_treatment']):
            raise ValueError('NATIVE_ID_LINEAGE_REQUIRED')
        observed = row.get('request_diagnostics')
        if not isinstance(observed, list) or len(observed) > (2 if row['arm'] == 'HCL' else 1) or len({x.get('phase') for x in observed}) != len(observed):
            raise ValueError('BOUNDED_PHASE_DIAGNOSTICS_REQUIRED')
        out['request_diagnostics'] = [clean_metrics(x) for x in observed]
        if row['arm'] == 'Base' and any(x['phase'] != 'answer' for x in out['request_diagnostics']):
            raise ValueError('DECLARED_PHASE_DIAGNOSTICS_REQUIRED')
        out['runtime_final_context_metrics'] = clean_runtime_metrics(row.get('runtime_final_context_metrics'))
        actual = next((x for x in out['request_diagnostics'] if x['phase'] == 'answer'), None)
        runtime = out['runtime_final_context_metrics']
        reason = row.get('full_request_metrics_unavailable_reason')
        if reason not in (None, 'ANSWER_PHASE_NOT_REACHED', 'RUNTIME_CONTEXT_REFUSED_BEFORE_PROVIDER_REQUEST_CONSTRUCTION') or (actual is not None and reason is not None) or (actual is None and reason is None):
            raise ValueError('EXACT_REQUEST_METRIC_AVAILABILITY_REQUIRED')
        if reason == 'RUNTIME_CONTEXT_REFUSED_BEFORE_PROVIDER_REQUEST_CONSTRUCTION' and runtime is None:
            raise ValueError('RUNTIME_CONTEXT_SIZE_ONLY_METRICS_REQUIRED')
        out.update(final_request_full_utf8_bytes=actual['full_request_utf8_bytes'] if actual else None, final_request_full_sha256=actual['full_request_sha256'] if actual else None, full_request_metrics_unavailable_reason=reason)
        if runtime and actual and runtime != {key: actual[key] for key in ('payload_utf8_bytes', 'serialized_messages_utf8_bytes', 'payload_value_utf8_bytes')}:
            raise ValueError('CURRENT_RUNTIME_AND_REQUEST_METRICS_DIVERGED')
        oversized = [metric for metric in out['request_diagnostics'] if metric['within_request_bound'] is False]
        if row['status'] == 'REQUEST_BOUND_EXCEEDED_NO_TRUNCATION':
            if len(oversized) != 1: raise ValueError('OVERSIZED_REFUSAL_NEEDS_PHASE_SPECIFIC_FULL_REQUEST_METRICS')
            out['request_bound_failure_phase'] = oversized[0]['phase']
        for key in ('arm_seconds', 'sdk_seconds', 'non_sdk_seconds'):
            if key in row:
                out[key] = duration(row[key])
        if row['status'] == 'NOT_ATTEMPTED' and (final is not None or observed or row['native_results'] or row['citations_accepted']):
            raise ValueError('NOT_ATTEMPTED_CANNOT_CONTAIN_OUTPUT')
        arms.append(out)
    calls = []
    for row in receipt['calls']:
        case, arm, phase = row['call_id'].split(':')
        if (case, arm) not in schedule or phase not in r.TOKENS or (arm == 'Base' and phase != 'answer') or row['case_id'] != case or row['arm'] != arm or row['phase'] != phase:
            raise ValueError('DECLARED_CALL_IDENTITY_REQUIRED')
        if row.get('status') not in CALL_STATUSES or row.get('invocation_status') not in INVOCATIONS or type(row.get('provider_call')) is not bool or type(row.get('offline_transport_call')) is not bool or (offline and row['provider_call']) or (not offline and row['offline_transport_call']):
            raise ValueError('EXACT_OFFLINE_CALL_STATE_REQUIRED')
        if type(row['request_bytes']) is not int or not 0 < row['request_bytes'] <= r.MAX_REQUEST_BYTES:
            raise ValueError('ADMITTED_FULL_REQUEST_BOUND_REQUIRED')
        call = dict(call_id=row['call_id'], case_id=case, arm=arm, phase=phase, request_sha256=r.exact_sha(row['request_sha256']), request_bytes=row['request_bytes'], reserved_cny=money(row['reserved_cny']), exact_request_reservation_cny=money(row['exact_request_reservation_cny']), status=row['status'], invocation_status=row['invocation_status'], provider_call=row['provider_call'], offline_transport_call=row['offline_transport_call'])
        if Decimal(call['reserved_cny']) != r.HOLD_CNY[phase] or Decimal(call['exact_request_reservation_cny']) != r.quote(row['request_bytes'], phase):
            raise ValueError('EXACT_NATIVE_CNY_RESERVATION_REQUIRED')
        diag = next((x for a in arms if a['case_id'] == case and a['arm'] == arm for x in a['request_diagnostics'] if x['phase'] == phase), None)
        if diag is None or diag['full_request_utf8_bytes'] != row['request_bytes'] or diag['full_request_sha256'] != row['request_sha256']:
            raise ValueError('REQUEST_DIAGNOSTIC_MATCH_REQUIRED')
        static = r.package_configuration(package)['requests'].get(row['call_id'])
        if static and (static['full_request_utf8_bytes'] != row['request_bytes'] or static['full_request_sha256'] != row['request_sha256']):
            raise ValueError('STATIC_REQUEST_IDENTITY_REQUIRED')
        if 'response_metadata' in row:
            call['response_metadata'] = clean_response_metadata(row['response_metadata'], phase)
        if 'sdk_seconds' in row:
            call['sdk_seconds'] = duration(row['sdk_seconds'])
        if 'failure_code' in row:
            if row['failure_code'] not in FAILURES:
                raise ValueError('SAFE_FAILURE_ENUM_REQUIRED')
            call['failure_code'] = row['failure_code']
        if 'usage' in row:
            counts = row['usage']
            if not isinstance(counts, dict) or set(counts) != {'prompt_tokens', 'completion_tokens'} or any(type(v) is not int or v <= 0 for v in counts.values()) or counts['prompt_tokens'] > 2 * row['request_bytes'] + 2048 or counts['completion_tokens'] > r.TOKENS[phase] + 32:
                raise ValueError('BOUNDED_USAGE_REQUIRED')
            rated = (counts['prompt_tokens'] * r.CNY_INPUT_RATE + counts['completion_tokens'] * r.CNY_OUTPUT_RATE) / 1000000
            if Decimal(money(row['usage_rated_cny'])) != rated or rated > r.HOLD_CNY[phase]:
                raise ValueError('EXACT_USAGE_COST_REQUIRED')
            call.update(usage=dict(counts), usage_rated_cny=str(rated))
        if call['status'] in ('RETURNED', 'RETURNED_REJECTED') and ('usage' not in call or not (call['offline_transport_call'] or call['provider_call'])):
            raise ValueError('RETURNED_REQUIRES_KNOWN_USAGE')
        calls.append(call)
    if len(calls) > r.MAX_CALLS[stage] or len({x['call_id'] for x in calls}) != len(calls):
        raise ValueError('ONE_CALL_PER_PHASE_REQUIRED')
    reserved = sum(Decimal(x['reserved_cny']) for x in calls)
    prior = Decimal('0') if stage == 1 else r.SCHEDULE_CNY[1]
    if Decimal(money(receipt['reserved_cny'])) != reserved or reserved > min(r.CAP_CNY[stage], r.SCHEDULE_CNY[stage]) or prior + reserved > r.TOTAL_CNY:
        raise ValueError('EXACT_CLOSED_CNY_LEDGER_REQUIRED')
    for case, arm in schedule:
        rows = [x for x in calls if x['case_id'] == case and x['arm'] == arm]
        record = next(x for x in arms if x['case_id'] == case and x['arm'] == arm)
        if record['status'] == 'NOT_ATTEMPTED' and rows:
            raise ValueError('NOT_ATTEMPTED_MUST_HAVE_NO_CALLS')
        if arm == 'HCL' and any(x['phase'] == 'answer' for x in rows) and (not rows or rows[0]['phase'] != 'planning' or rows[0]['status'] != 'RETURNED'):
            raise ValueError('HCL_ANSWER_REQUIRES_PRIOR_RETURNED_PLAN')
    complete = all('usage_rated_cny' in x for x in calls if x['offline_transport_call'] or x['provider_call'])
    output = dict(schema=PUBLIC_SCHEMA, mode=expected_mode, currency='CNY', authorization_ref=r.AUTH, package_sha256=r.digest(package.value), packet_sha256=package.value['packet_sha256'], runtime_sha256=package.value['runtime_sha256'], stage=stage, model=r.MODEL, send_margin_seconds=r.WAIT, stage_window_seconds=r.ELAPSED[stage], planning_tokens=16384, answer_tokens=16384, cases=[next(case for case in package.cases if case['case_id'] == cid) for cid, _ in r.order(package.cases, stage)], status=receipt['status'], arms=arms, calls=calls, provider_calls=sum(x['provider_call'] for x in calls), offline_transport_calls=sum(x['offline_transport_call'] for x in calls), reserved_cny=str(reserved), usage_complete=complete, invoice_cost_cny=None, elapsed_seconds=(None if receipt.get('process_interrupted') is True and receipt['status'] == 'STOPPED_NO_RETRY' and receipt.get('elapsed_seconds') is None else duration(receipt['elapsed_seconds'])), budget_state='CLOSED_NO_TRANSFER_NO_RETRY', remaining_authorized_calls=0, remaining_authorized_cny='0', independent_semantic_gate='PENDING_INDEPENDENT_SOURCE_FIRST_REVIEW', efficacy_verified=False, i02_certified=False)
    if receipt.get('process_interrupted') is True:
        output['timing_availability'] = 'PROCESS_INTERRUPTED_ELAPSED_UNKNOWN'
    output['reasoning_effort'] = dict(r.EFFORT)
    output['receipt_sha256'] = r.digest(receipt)
    cost = str(sum(Decimal(x.get('usage_rated_cny', '0')) for x in calls)) if complete else None
    output.update(simulated_usage_rated_cny=cost, actual_spend_cny='0', live_execution_authorized=False)
    output.update(native_publication_status='OFFLINE_NATIVE_UNAVAILABLE_GATE_CLOSED', approved_native_evidence=None)
    if native_bundle is not None:
        output.update(native_publication_status='OFFLINE_LOCAL_NATIVE_EVIDENCE',
                      approved_native_evidence=export_native_bundle(native_bundle, receipt, package))
        validate_actual_entry_requirements(output, package)
    return output

def validate_phase1_gate(package, evidence, review, *, original_receipt, original_native_bundle):
    """Success gate bound to separately loaded original durable evidence.

    The caller must supply its trusted original receipt and private native capture;
    neither is reconstructed from the mutable public evidence. Their exact fresh
    export must equal the reviewed public artifact, including the original request
    identities and capture commitments. This cannot authenticate a caller that
    forges or replaces the originals too; hashes/replay only establish integrity.
    No automatic/model judge. Passing a synthetic fixture proves gate control flow,
    never establishes independent semantic quality or permission for a live run.
    """
    r.require_package(package)
    package.verify()
    r.require_plain_json(evidence); r.require_plain_json(review)
    validate_offline_flags(evidence, 'public')
    offline = True
    expected_schema = PUBLIC_SCHEMA
    expected_mode = r.MODE
    smoke = package.packet['cases'][0]; cid = smoke['case_id']
    if not isinstance(evidence, dict) or evidence.get('schema') != expected_schema or evidence.get('mode') != expected_mode or evidence.get('authorization_ref') != r.AUTH or evidence.get('currency') != 'CNY' or evidence.get('stage') != 1 or evidence.get('package_sha256') != r.digest(package.value) or evidence.get('packet_sha256') != r.digest(package.packet) or evidence.get('runtime_sha256') != package.value['runtime_sha256'] or evidence.get('model') != r.MODEL or evidence.get('planning_tokens') != 16384 or evidence.get('answer_tokens') != 16384 or evidence.get('cases') != package.cases[:1] or evidence.get('status') != 'COMPLETED_ONE_PASS' or evidence.get('usage_complete') is not True or evidence.get('offline_transport_calls') != (2 if offline else 0) or evidence.get('provider_calls') != (0 if offline else 2) or evidence.get('budget_state') != 'CLOSED_NO_TRANSFER_NO_RETRY' or evidence.get('remaining_authorized_calls') != 0 or evidence.get('remaining_authorized_cny') != '0':
        raise ValueError('PHASE1_EXACT_COMPLETE_KNOWN_CLOSED_REQUIRED')
    if type(original_receipt) is not dict or type(original_native_bundle) is not dict:
        raise ValueError('ORIGINAL_DURABLE_RECEIPT_AND_CAPTURE_REQUIRED')
    r.require_plain_json(original_receipt); r.require_plain_json(original_native_bundle)
    if r.digest(original_receipt) != evidence.get('receipt_sha256'):
        raise ValueError('EXACT_ORIGINAL_DURABLE_RECEIPT_HASH_REQUIRED')
    original_export = export(original_receipt, package, native_bundle=original_native_bundle)
    if r.canonical(evidence) != r.canonical(original_export):
        raise ValueError('EXACT_ORIGINAL_DURABLE_EXPORT_REQUIRED')
    if evidence.get('reasoning_effort') != r.EFFORT:raise ValueError('EXACT_PHASE_REASONING_CONFIGURATION_REQUIRED')
    calls = evidence.get('calls'); arms = evidence.get('arms')
    if not isinstance(calls, list) or [c.get('call_id') for c in calls] != [cid + ':HCL:planning', cid + ':HCL:answer'] or any(c.get('status') != 'RETURNED' or c.get('invocation_status') != 'RETURNED' or c.get('offline_transport_call' if offline else 'provider_call') is not True for c in calls) or not isinstance(arms, list) or len(arms) != 1:
        raise ValueError('PHASE1_TWO_RETURNED_CALLS_REQUIRED')
    validate_success_native_evidence(evidence, package)
    arm = arms[0]; raw = arm.get('final_text')
    if arm.get('native_integrity_status') != 'VALIDATED':
        raise ValueError('VALIDATED_NATIVE_INTEGRITY_REQUIRED')
    entry = clean_entry_requirements(arm.get('entry_requirements'))
    if entry is None or entry['known_source_entry_blockers_avoided'] is not True or entry['allowed_family_checked_treatment_present'] is not True:
        raise ValueError('NECESSARY_ENTRY_REQUIREMENTS_NOT_SATISFIED')
    prompt = r.messages(package.cases[0], 'Base')
    if arm.get('case_id') != cid or arm.get('arm') != 'HCL' or arm.get('status') != 'ANSWER_ACCEPTED' or arm.get('final_delivery_code') != 'DELIVERED' or arm.get('citations_accepted') is not True or type(arm.get('native_results')) is not int or not 1 <= arm['native_results'] <= 3 or not r.accepted(prompt, raw) or arm.get('final_fields') != r.final_fields(raw) or arm.get('final_answer_sha256') != hashlib.sha256(raw.encode()).hexdigest():
        raise ValueError('PHASE1_NATIVE_COMPLETE_DELIVERY_AND_SOURCE_AUDIT_REQUIRED')
    validate_review_binding(package, evidence, review)
    if arm['orchestration_failure'] is not None or arm['capture_failure'] is not None:
        raise ValueError('SUCCESS_CANNOT_CONTAIN_FAILURE_DIAGNOSTIC')
    if set(review) != REVIEW_KEYS or review['reviewer_role'] != 'INDEPENDENT_SOURCE_FIRST_AFTER_OUTPUT' or review['same_smoke_and_rules_fixed_before_entry_contract_smoke_output'] is not True or review['overall_pass'] is not True or review['critical_failure_tags'] != [] or arm.get('native_review_available') is not True:
        raise ValueError('EXACT_INDEPENDENT_SOURCE_REVIEW_REQUIRED')
    if not isinstance(review['gates'], dict) or set(review['gates']) != set(GATES) or any(value is not True for value in review['gates'].values()):
        raise ValueError('ALL_STRICT_SEMANTIC_AND_DELIVERY_GATES_REQUIRED')
    for checks, ids in ((review['obligations'], obligation_ids(smoke)), (review['smoke_semantics'], ['S1', 'S2', 'S3', 'S4'])):
        if not isinstance(checks, list) or [x.get('id') for x in checks] != ids:
            raise ValueError('ALL_FROZEN_OBLIGATIONS_REQUIRED')
        for check in checks:
            if set(check) != {'id', 'passed', 'source_evidence', 'answer_evidence'} or check['passed'] is not True or any(not isinstance(check[key], str) or not check[key].strip() or len(check[key]) > 1500 for key in ('source_evidence', 'answer_evidence')):
                raise ValueError('EACH_OBLIGATION_SOURCE_AND_ANSWER_EVIDENCE_REQUIRED')
    relevant = review['relevant_native_capability_ids']
    allowed = {x['capability_id'] for x in smoke['private_evaluation']['predeclared_acceptable_relevant_native_operation_families']}
    if not isinstance(relevant, list) or not 1 <= len(relevant) <= 3 or len(set(relevant)) != len(relevant) or any(x not in allowed or x not in arm['executed_capabilities'] for x in relevant):
        raise ValueError('RELEVANT_ACTUAL_NATIVE_EXECUTION_REQUIRED')
    # Check phase identity, usage, quote and immutable full holds independently.
    rated = Decimal('0')
    for index, call in enumerate(calls):
        phase = 'planning' if index == 0 else 'answer'; counts = call.get('usage')
        if call.get('case_id') != cid or call.get('arm') != 'HCL' or call.get('phase') != phase or type(call.get('request_bytes')) is not int or not 0 < call['request_bytes'] <= r.MAX_REQUEST_BYTES or not isinstance(counts, dict) or set(counts) != {'prompt_tokens', 'completion_tokens'} or any(type(v) is not int or v <= 0 for v in counts.values()) or counts['prompt_tokens'] > 2 * call['request_bytes'] + 2048 or counts['completion_tokens'] > r.TOKENS[phase] + 32:
            raise ValueError('PHASE1_VALID_BOUNDED_USAGE_REQUIRED')
        r.exact_sha(call['request_sha256'])
        metric = next((x for x in arm['request_diagnostics'] if x.get('phase') == phase), None)
        if metric is None or clean_metrics(metric)['full_request_sha256'] != call['request_sha256'] or metric['full_request_utf8_bytes'] != call['request_bytes']:
            raise ValueError('PHASE1_ACTUAL_REQUEST_METRICS_REQUIRED')
        static = r.package_configuration(package)['requests'].get(call['call_id'])
        if static and (static['full_request_sha256'] != call['request_sha256'] or static['full_request_utf8_bytes'] != call['request_bytes']):
            raise ValueError('PHASE1_STATIC_REQUEST_IDENTITY_REQUIRED')
        cost = (counts['prompt_tokens'] * r.CNY_INPUT_RATE + counts['completion_tokens'] * r.CNY_OUTPUT_RATE) / 1000000
        if Decimal(money(call['reserved_cny'])) != r.HOLD_CNY[phase] or Decimal(money(call['exact_request_reservation_cny'])) != r.quote(call['request_bytes'], phase) or Decimal(money(call['usage_rated_cny'])) != cost:
            raise ValueError('PHASE1_EXACT_CNY_LEDGER_REQUIRED')
        rated += cost
    if Decimal(money(evidence['reserved_cny'])) != r.SCHEDULE_CNY[1] or Decimal(money(evidence['simulated_usage_rated_cny' if offline else 'usage_rated_cny'])) != rated:
        raise ValueError('PHASE1_FULL_HOLD_AND_COST_REQUIRED')
    return True



def close_interrupted_receipt(receipt, package):
    """Close existing holds; never infer a diagnosis or resume a transport."""
    r.require_package(package); package.verify()
    r.require_plain_json(receipt)
    validate_offline_flags(receipt, 'receipt')
    if receipt.get('schema') != r.RECEIPT_SCHEMA or receipt.get('mode') != r.MODE or receipt.get('authorization_ref') != r.AUTH or receipt.get('package_sha256') != r.digest(package.value):
        raise ValueError('EXACT_INTERRUPTED_RECEIPT_REQUIRED')
    for arm in receipt['arms']:
        clean_diagnostic_field(arm); clean_capture_field(arm)
    if receipt.get('status') in ('COMPLETED_ONE_PASS', 'STOPPED_NO_RETRY'):
        return receipt
    if receipt.get('status') != 'RUNNING' or receipt.get('currency') != 'CNY' or type(receipt.get('stage')) is not int or receipt['stage'] != 1:
        raise ValueError('EXACT_INTERRUPTED_RECEIPT_REQUIRED')
    value = json.loads(r.canonical(receipt))
    for arm in value['arms']:
        calls = [c for c in value['calls'] if c['case_id'] == arm['case_id'] and c['arm'] == arm['arm']]
        if calls and arm['status'] == 'NOT_ATTEMPTED': arm['status'] = 'UNKNOWN_FAILURE_STOP'
        for call in calls:
            if call['invocation_status'] == 'INVOKED_OR_SEND_UNKNOWN':
                call.update(status='FAILED_OR_UNKNOWN', failure_code='UNKNOWN_SEND_USAGE_COST_OR_IDENTITY_STOP')
                arm['status'] = 'UNKNOWN_FAILURE_STOP'
    value.update(status='STOPPED_NO_RETRY', process_interrupted=True, elapsed_seconds=None,
                 budget_state='CLOSED_NO_TRANSFER_NO_RETRY', remaining_authorized_calls=0, remaining_authorized_cny='0')
    return value


def export_terminal(directory, package):
    """Local recovery only. Malformed ordinary evidence fails without replacement."""
    directory = r.Path(directory)
    original = json.loads((directory / 'receipt.json').read_text())
    receipt = close_interrupted_receipt(original, package)
    output = export(receipt, package)
    if receipt != original: r.save(directory / 'receipt.json', receipt)
    path = directory / 'native-review-private.json'
    if path.exists():
        try:
            output = export(receipt, package, native_bundle=json.loads(path.read_text()))
        except Exception:
            output.update(native_publication_status='OFFLINE_NATIVE_EXPORT_REJECTED_GATE_CLOSED', approved_native_evidence=None)
    r.save(directory / 'public.json', output)
    return output
