"""Explicit-allowlist public candidate; no raw request/plan/envelope copying."""
from decimal import Decimal
import hashlib
import math

import hcl_recovery_candidate as r

ARM_STATUSES = {'NOT_ATTEMPTED', 'ANSWER_ACCEPTED', 'FINAL_SCHEMA_OR_CITATIONS_REJECTED', 'BOUNDED_HCL_SCHEMA_SELECTION_OR_ADAPTER_FAILURE', 'REQUEST_BOUND_EXCEEDED_NO_TRUNCATION', 'INCOMPLETE_ANSWER_NO_RETRY', 'CONTENT_BOUND_EXCEEDED', 'UNKNOWN_FAILURE_STOP'}
CALL_STATUSES = {'RESERVED_BEFORE_CALL', 'RETURNED', 'RETURNED_REJECTED', 'FAILED_OR_UNKNOWN'}
INVOCATIONS = {'NOT_INVOKED', 'RETURNED', 'RESPONSE_RETURNED_REJECTED', 'INVOKED_OR_SEND_UNKNOWN'}
DELIVERY = {'NOT_REACHED', 'RETURNED_UNVALIDATED', 'JSON_INVALID', 'SCHEMA_INVALID', 'ANSWER_BLANK', 'SOURCE_REVIEW_REJECTED', 'DELIVERED'}
FAILURES = r.KNOWN_RETURN_FAILURES | {'UNKNOWN_SEND_USAGE_COST_OR_IDENTITY_STOP', 'FINAL_DISPATCH_MARGIN_REJECTED_NO_CALL'}
GATES = ('complete_source_delivery_passed', 'trusted_native_policy_passed', 'relevant_native_execution_passed', 'all_key_facts_preserved', 'inference_boundaries_preserved', 'citations_and_complete_final_delivery_passed')


def money(value):
    if not isinstance(value, str) or len(value) > 40:
        raise ValueError('BOUNDED_MONEY_REQUIRED')
    number = Decimal(value)
    if not number.is_finite() or not 0 <= number <= 6:
        raise ValueError('BOUNDED_MONEY_REQUIRED')
    return str(number)


def duration(value):
    if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 3000:
        raise ValueError('BOUNDED_DURATION_REQUIRED')
    return value


def metric_size(value):
    if type(value) is not int or not 0 <= value <= 4 * 1024 * 1024:
        raise ValueError('BOUNDED_SIZE_METRIC_REQUIRED')
    return value


def clean_metrics(row):
    required = {'phase', 'full_request_utf8_bytes', 'full_request_sha256', 'serialized_messages_utf8_bytes', 'serialized_messages_sha256', 'maximum_request_bytes', 'within_request_bound'}
    if not isinstance(row, dict) or not required <= set(row) or set(row) - required - {'payload_utf8_bytes', 'payload_value_utf8_bytes'} or row['phase'] not in r.TOKENS:
        raise ValueError('EXACT_SIZE_METRIC_SCHEMA_REQUIRED')
    out = dict(phase=row['phase'], full_request_utf8_bytes=metric_size(row['full_request_utf8_bytes']), full_request_sha256=r.exact_sha(row['full_request_sha256']), serialized_messages_utf8_bytes=metric_size(row['serialized_messages_utf8_bytes']), serialized_messages_sha256=r.exact_sha(row['serialized_messages_sha256']), maximum_request_bytes=r.MAX_REQUEST_BYTES, within_request_bound=row['within_request_bound'])
    if row['maximum_request_bytes'] != r.MAX_REQUEST_BYTES or type(row['within_request_bound']) is not bool or row['within_request_bound'] != (0 < row['full_request_utf8_bytes'] <= r.MAX_REQUEST_BYTES) or row['full_request_utf8_bytes'] <= row['serialized_messages_utf8_bytes']:
        raise ValueError('FULL_REQUEST_NOT_MESSAGES_METRIC_REQUIRED')
    if 'payload_utf8_bytes' in row:
        out['payload_utf8_bytes'] = metric_size(row['payload_utf8_bytes'])
    if 'payload_value_utf8_bytes' in row:
        fields = row['payload_value_utf8_bytes']
        if not isinstance(fields, dict) or set(fields) - set(r.METRIC_FIELDS):
            raise ValueError('ALLOWLISTED_FIELD_METRICS_REQUIRED')
        out['payload_value_utf8_bytes'] = {key: metric_size(value) for key, value in fields.items()}
    return out


def clean_runtime_metrics(row):
    if row is None:
        return None
    if row == {'utf8_encoding_available': False}:
        return dict(row)
    keys = {'payload_utf8_bytes', 'serialized_messages_utf8_bytes', 'payload_value_utf8_bytes'}
    if not isinstance(row, dict) or set(row) != keys or not isinstance(row['payload_value_utf8_bytes'], dict) or not (set(r.METRIC_FIELDS) - {'capability_inventory', 'native_reader_contexts'}) <= set(row['payload_value_utf8_bytes']) or set(row['payload_value_utf8_bytes']) - (set(r.METRIC_FIELDS) - {'capability_inventory'}):
        raise ValueError('EXACT_RUNTIME_SIZE_METRICS_REQUIRED')
    return dict(payload_utf8_bytes=metric_size(row['payload_utf8_bytes']), serialized_messages_utf8_bytes=metric_size(row['serialized_messages_utf8_bytes']), payload_value_utf8_bytes={k: metric_size(v) for k, v in row['payload_value_utf8_bytes'].items()})



def clean_response_metadata(value, phase):
    keys = {'choice_count', 'finish_reasons', 'visible_content_characters', 'provider_reported_reasoning_tokens'}
    if not isinstance(value, dict) or set(value) != keys:
        raise ValueError('EXACT_SAFE_RESPONSE_METADATA_REQUIRED')
    for key, maximum in [('choice_count', 100), ('visible_content_characters', 2 * 1024 * 1024),
                         ('provider_reported_reasoning_tokens', r.TOKENS[phase] + 32)]:
        item = value[key]
        if item is not None and (type(item) is not int or not 0 <= item <= maximum):
            raise ValueError('BOUNDED_SAFE_RESPONSE_COUNT_REQUIRED')
    reasons = value['finish_reasons']
    if not isinstance(reasons, list) or len(reasons) > 10 or any(type(reason) is not str or reason not in r.SAFE_FINISH_REASONS for reason in reasons):
        raise ValueError('ALLOWLISTED_FINISH_REASON_REQUIRED')
    return dict(value, finish_reasons=list(reasons))


def export(receipt, package, grant=None, identity=None, native_bundle=None):
    package.verify(); stage = receipt['stage']
    offline = type(package) is r.OfflinePackage
    expected_mode = 'OFFLINE_SYNTHETIC_NO_PROVIDER' if offline else 'LIVE_EXISTING_ACCOUNT'
    expected_schema = 'hcl-planning-recovery-offline-receipt-v1' if offline else 'hcl-planning-recovery-private-receipt-v1'
    if not offline:
        if not isinstance(grant, dict): raise ValueError('EXACT_NEW_GRANT_REQUIRED_FOR_PUBLIC_EXPORT')
        r.require_new_grant(package, grant, stage, r.timestamp(receipt['started_at']))
        if identity != receipt.get('identity') or not isinstance(identity, dict) or set(identity) != {'run_id', 'head_sha'} or not isinstance(identity['run_id'], str) or not identity['run_id'].isascii() or not identity['run_id'].isdecimal() or int(identity['run_id']) <= 0:
            raise ValueError('EXACT_LIVE_RUN_IDENTITY_REQUIRED')
        r.exact_sha(identity['head_sha'], 40)
        admission = receipt.get('admission_hashes')
        if not isinstance(admission, dict) or set(admission) != {'grant_sha256', 'launch_sha256', 'price_sha256', 'account_sha256'} or admission['grant_sha256'] != r.digest(grant):
            raise ValueError('EXACT_LIVE_ADMISSION_HASHES_REQUIRED')
        for value in admission.values(): r.exact_sha(value)
    if type(stage) is not int or stage not in (1, 2) or receipt.get('schema') != expected_schema or receipt.get('mode') != expected_mode or receipt.get('currency') != 'CNY' or receipt.get('usd_reference_only') is not True or receipt.get('authorization_ref') != r.AUTH or receipt.get('package_sha256') != r.digest(package.value):
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
        out = dict(case_id=row['case_id'], arm=row['arm'], status=row['status'], final_text=final, final_fields=r.final_fields(final), final_answer_sha256=sha, citations_accepted=row['citations_accepted'], native_results=row['native_results'], final_delivery_code=row['final_delivery_code'])
        if type(row.get('native_review_available')) is not bool:
            raise ValueError('EXACT_NATIVE_REVIEW_AVAILABILITY_REQUIRED')
        out['native_review_available'] = row['native_review_available']
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
    output = dict(schema='hcl-planning-recovery-offline-public-evidence-v1' if offline else 'hcl-planning-recovery-public-evidence-v1', mode=expected_mode, currency='CNY', authorization_ref=r.AUTH, package_sha256=r.digest(package.value), packet_sha256=package.value['packet_sha256'], runtime_sha256=package.value['runtime_sha256'], stage=stage, model=r.MODEL, authorization_expiry_utc=r.EXPIRES, send_margin_seconds=r.WAIT, stage_window_seconds=r.ELAPSED[stage], planning_tokens=16384, answer_tokens=8192, cases=package.cases, status=receipt['status'], arms=arms, calls=calls, provider_calls=sum(x['provider_call'] for x in calls), offline_transport_calls=sum(x['offline_transport_call'] for x in calls), reserved_cny=str(reserved), usage_complete=complete, invoice_cost_cny=None, elapsed_seconds=(None if receipt.get('process_interrupted') is True and receipt['status'] == 'STOPPED_NO_RETRY' and receipt.get('elapsed_seconds') is None else duration(receipt['elapsed_seconds'])), budget_state='CLOSED_NO_TRANSFER_NO_RETRY', remaining_authorized_calls=0, remaining_authorized_cny='0', independent_semantic_gate='PENDING_INDEPENDENT_SOURCE_FIRST_REVIEW', efficacy_verified=False, i02_certified=False)
    if receipt.get('process_interrupted') is True:
        output['timing_availability'] = 'PROCESS_INTERRUPTED_ELAPSED_UNKNOWN'
    output['receipt_sha256'] = r.digest(receipt)
    cost = str(sum(Decimal(x.get('usage_rated_cny', '0')) for x in calls)) if complete else None
    if offline:
        output.update(simulated_usage_rated_cny=cost, actual_spend_cny='0')
    else:
        output.update(usage_rated_cny=cost, cost_basis='CNY_PEAK_USAGE_ESTIMATE_NOT_INVOICE_FULL_HOLDS_RETAINED', **identity)
    output.update(native_publication_status='NOT_AUTHORIZED_GATE_CLOSED', approved_native_evidence=None)
    if isinstance(grant, dict) and grant.get('public_native_evidence_permission') is not None:
        if native_bundle is None:
            output.update(native_publication_status='AUTHORIZED_BUT_NATIVE_UNAVAILABLE_GATE_CLOSED')
        else:
            from hcl_recovery_native_public import export_native_records
            expected_ids = [a['case_id'] for a in arms if a['arm'] == 'HCL' and a['native_review_available']]
            approved = export_native_records(native_bundle, package, grant['public_native_evidence_permission'], expected_case_ids=expected_ids, receipt=receipt)
            output.update(native_publication_status='AUTHORIZED_BOUNDED_NATIVE_EVIDENCE', approved_native_evidence=approved)
    return output


def obligation_ids(case):
    evaluation = case['private_evaluation']
    return [row['id'] for key in ('key_fact_obligations', 'inference_boundary_obligations', 'citation_source_obligations') for row in evaluation[key]]


def validate_phase1_gate(package, evidence, review, *, native_permission=None):
    """Gate simulation only; requires linked independent source-first review.

    No automatic/model judge. Passing a synthetic fixture proves gate control flow,
    never establishes independent semantic quality or permission for a live run.
    """
    package.verify()
    offline = type(package) is r.OfflinePackage
    expected_schema = 'hcl-planning-recovery-offline-public-evidence-v1' if offline else 'hcl-planning-recovery-public-evidence-v1'
    expected_mode = 'OFFLINE_SYNTHETIC_NO_PROVIDER' if offline else 'LIVE_EXISTING_ACCOUNT'
    smoke = package.packet['cases'][0]; cid = smoke['case_id']
    if not isinstance(evidence, dict) or evidence.get('schema') != expected_schema or evidence.get('mode') != expected_mode or evidence.get('authorization_ref') != r.AUTH or evidence.get('currency') != 'CNY' or evidence.get('stage') != 1 or evidence.get('package_sha256') != r.digest(package.value) or evidence.get('packet_sha256') != r.digest(package.packet) or evidence.get('runtime_sha256') != package.value['runtime_sha256'] or evidence.get('model') != r.MODEL or evidence.get('planning_tokens') != 16384 or evidence.get('answer_tokens') != 8192 or evidence.get('cases') != package.cases or evidence.get('status') != 'COMPLETED_ONE_PASS' or evidence.get('usage_complete') is not True or evidence.get('offline_transport_calls') != (2 if offline else 0) or evidence.get('provider_calls') != (0 if offline else 2) or evidence.get('budget_state') != 'CLOSED_NO_TRANSFER_NO_RETRY' or evidence.get('remaining_authorized_calls') != 0 or evidence.get('remaining_authorized_cny') != '0':
        raise ValueError('PHASE1_EXACT_COMPLETE_KNOWN_CLOSED_REQUIRED')
    if not offline:
        native = evidence.get('approved_native_evidence')
        if evidence.get('native_publication_status') != 'AUTHORIZED_BOUNDED_NATIVE_EVIDENCE' or not isinstance(native, dict) or native.get('record_count') != 1 or len(native.get('records', [])) != 1 or native['records'][0].get('case_id') != cid:
            raise ValueError('APPROVED_PUBLIC_NATIVE_EVIDENCE_REQUIRED_FOR_REVIEW_GATE')
        from hcl_recovery_native_public import validate_published_native_evidence
        validate_published_native_evidence(native, package, native_permission, public_capture=evidence)
        r.exact_sha(evidence.get('head_sha'), 40)
        if not isinstance(evidence.get('run_id'), str) or not evidence['run_id'].isascii() or not evidence['run_id'].isdecimal() or int(evidence['run_id']) <= 0: raise ValueError('PHASE1_LIVE_RUN_IDENTITY_REQUIRED')
    calls = evidence.get('calls'); arms = evidence.get('arms')
    if not isinstance(calls, list) or [c.get('call_id') for c in calls] != [cid + ':HCL:planning', cid + ':HCL:answer'] or any(c.get('status') != 'RETURNED' or c.get('invocation_status') != 'RETURNED' or c.get('offline_transport_call' if offline else 'provider_call') is not True for c in calls) or not isinstance(arms, list) or len(arms) != 1:
        raise ValueError('PHASE1_TWO_RETURNED_CALLS_REQUIRED')
    arm = arms[0]; raw = arm.get('final_text')
    if not offline:
        record = evidence['approved_native_evidence']['records'][0]
        ids = [op['capability_id'] for op in record['operations'] if op['native_result_and_policy']['executed']]
        if record['private_native_review_sha256'] != arm.get('native_review_sha256') or ids != arm.get('executed_capabilities') or record['actual_executed_count'] != arm.get('native_results'):
            raise ValueError('PUBLIC_NATIVE_RECORD_MUST_MATCH_ACTUAL_ARM')
    prompt = r.messages(package.cases[0], 'Base')
    if arm.get('case_id') != cid or arm.get('arm') != 'HCL' or arm.get('status') != 'ANSWER_ACCEPTED' or arm.get('final_delivery_code') != 'DELIVERED' or arm.get('citations_accepted') is not True or type(arm.get('native_results')) is not int or not 1 <= arm['native_results'] <= 3 or not r.accepted(prompt, raw) or arm.get('final_fields') != r.final_fields(raw) or arm.get('final_answer_sha256') != hashlib.sha256(raw.encode()).hexdigest():
        raise ValueError('PHASE1_NATIVE_COMPLETE_DELIVERY_AND_SOURCE_AUDIT_REQUIRED')
    expected_keys = {'schema', 'authorization_ref', 'package_sha256', 'packet_sha256', 'evidence_sha256', 'final_answer_sha256', 'request_diagnostics_sha256', 'native_review_sha256', 'reviewer_role', 'all_selected_cases_and_rubrics_fixed_before_recovery_output', 'gates', 'obligations', 'smoke_semantics', 'relevant_native_capability_ids', 'critical_failure_tags', 'overall_pass'}
    if not offline: expected_keys.add('approved_native_evidence_sha256')
    if not offline and review.get('approved_native_evidence_sha256') != r.digest(evidence['approved_native_evidence']):
        raise ValueError('EXACT_APPROVED_NATIVE_EVIDENCE_REVIEW_LINK_REQUIRED')
    if not isinstance(review, dict) or set(review) != expected_keys or review['schema'] != 'hcl-planning-recovery-source-review-candidate-v1' or review['authorization_ref'] != r.AUTH or review['package_sha256'] != r.digest(package.value) or review['packet_sha256'] != r.digest(package.packet) or review['evidence_sha256'] != r.digest(evidence) or review['final_answer_sha256'] != arm['final_answer_sha256'] or review['request_diagnostics_sha256'] != r.digest(arm['request_diagnostics']) or arm.get('native_review_available') is not True or review['native_review_sha256'] != arm.get('native_review_sha256') or review['reviewer_role'] != 'INDEPENDENT_SOURCE_FIRST_AFTER_OUTPUT' or review['all_selected_cases_and_rubrics_fixed_before_recovery_output'] is not True or review['overall_pass'] is not True or review['critical_failure_tags'] != []:
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


def fixed_denominator_positions(evidence):
    """No missing-slot deletion, no synthetic scores for unreviewed successes.

    All failed/not-attempted scheduled positions score zero. Accepted but not yet
    independently reviewed positions remain NA. HCL stress-case denominator is always two; there is no Base comparison.
    """
    if evidence.get('stage') != 2 or len(evidence.get('arms', [])) != 2:
        raise ValueError('EXACT_TWO_HCL_STRESS_POSITIONS_REQUIRED')
    return dict(fixed_case_denominator=2, fixed_arm_denominator=2, positions=[dict(case_id=a['case_id'], arm=a['arm'], status=a['status'], semantic_score=None if a['status'] == 'ANSWER_ACCEPTED' else 0, score_state='NA_PENDING_INDEPENDENT_REVIEW' if a['status'] == 'ANSWER_ACCEPTED' else 'FAILED_POSITION_RETAINED_ZERO', cost_known=all('usage_rated_cny' in c for c in evidence['calls'] if c['case_id'] == a['case_id'] and c['arm'] == a['arm'] and (c['offline_transport_call'] or c['provider_call']))) for a in evidence['arms']], population_efficacy_claim=False)
