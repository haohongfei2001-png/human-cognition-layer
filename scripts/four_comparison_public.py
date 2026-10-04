"""Allowlist-only export for the newly approved four-case public synthetic exception."""
import argparse
from decimal import Decimal
import json
import math
import os
from pathlib import Path
from scripts import run_four_comparison as r

STATUSES = {'NOT_ATTEMPTED', 'ANSWER_ACCEPTED', 'FINAL_SCHEMA_OR_CITATIONS_REJECTED',
            'BOUNDED_HCL_SCHEMA_SELECTION_OR_ADAPTER_FAILURE', 'REQUEST_BOUND_EXCEEDED_NO_TRUNCATION',
            'INCOMPLETE_ANSWER_NO_RETRY', 'CONTENT_BOUND_EXCEEDED', 'UNKNOWN_FAILURE_STOP'}
CALL_STATUSES = {'RESERVED_BEFORE_CALL', 'RETURNED', 'RETURNED_REJECTED', 'FAILED_OR_UNKNOWN'}
INVOCATIONS = {'NOT_INVOKED', 'RETURNED', 'RESPONSE_RETURNED_REJECTED', 'INVOKED_OR_SEND_UNKNOWN'}


def sha(value, length=64):
    if not isinstance(value, str) or len(value) != length or any(c not in '0123456789abcdef' for c in value): raise ValueError('EXACT_HASH_REQUIRED')
    return value


def money(value):
    if not isinstance(value, str) or len(value) > 40: raise ValueError('BOUNDED_MONEY_REQUIRED')
    number = Decimal(value)
    if not number.is_finite() or not 0 <= number <= r.CAP: raise ValueError('BOUNDED_MONEY_REQUIRED')
    return str(number)


def duration(value):
    if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 3000: raise ValueError('BOUNDED_DURATION_REQUIRED')
    return value


def export(receipt, package, grant, identity, secret):
    if (set(identity) != {'run_id', 'head_sha'} or not isinstance(identity['run_id'], str)
        or not identity['run_id'].isascii() or not identity['run_id'].isdecimal() or int(identity['run_id']) <= 0): raise ValueError('RUN_ID_REQUIRED')
    sha(identity['head_sha'], 40)
    if (package != r.build_package() or grant != r.expected_grant(package, True)
        or receipt.get('package_sha256') != r.digest(package) or receipt.get('authorization_ref') != r.AUTH
        or secret != dict(identity, existing_provider_secret='PRESENT')): raise ValueError('EXACT_AUTHORITY_AND_IDENTITY_REQUIRED')
    if receipt.get('status') not in {'COMPLETED_ONE_PASS', 'STOPPED_NO_RETRY'} or receipt.get('budget_state') != 'CLOSED_NO_TRANSFER_NO_RETRY': raise ValueError('TERMINAL_RECEIPT_REQUIRED')
    calls = []
    for row in receipt['calls']:
        case, arm, phase = row['call_id'].split(':')
        if (case, arm) not in r.ORDER or phase not in ('planning', 'answer') or (arm == 'Base' and phase != 'answer'): raise ValueError('DECLARED_CALL_REQUIRED')
        if row['status'] not in CALL_STATUSES or row['invocation_status'] not in INVOCATIONS or type(row['provider_call']) is not bool: raise ValueError('KNOWN_CALL_STATE_REQUIRED')
        if type(row['request_bytes']) is not int or not 0 < row['request_bytes'] <= 36000: raise ValueError('BOUNDED_REQUEST_REQUIRED')
        call = dict(call_id=row['call_id'], case_id=case, arm=arm, phase=phase, request_sha256=sha(row['request_sha256']),
                    request_bytes=row['request_bytes'], reserved_usd=money(row['reserved_usd']), exact_request_reservation_usd=money(row['exact_request_reservation_usd']),
                    status=row['status'], invocation_status=row['invocation_status'], provider_call=row['provider_call'])
        if 'sdk_seconds' in row: call['sdk_seconds'] = duration(row['sdk_seconds'])
        if 'failure_code' in row:
            if row['failure_code'] not in r.KNOWN_RETURN_FAILURES | {'UNKNOWN_SEND_USAGE_COST_OR_IDENTITY_STOP'}: raise ValueError('SAFE_FAILURE_REQUIRED')
            call['failure_code'] = row['failure_code']
        if 'usage' in row:
            counts = row['usage']
            if set(counts) != {'prompt_tokens', 'completion_tokens'} or any(type(v) is not int or not 0 < v <= 75000 for v in counts.values()): raise ValueError('BOUNDED_USAGE_REQUIRED')
            rated = (counts['prompt_tokens']*r.INPUT_RATE + counts['completion_tokens']*r.OUTPUT_RATE)/1000000
            if Decimal(money(row['usage_rated_usd'])) != rated or rated > Decimal(call['reserved_usd']): raise ValueError('EXACT_USAGE_COST_REQUIRED')
            call.update(usage=dict(counts), usage_rated_usd=str(rated))
        calls.append(call)
    if len(calls) > r.MAX_CALLS or len({c['call_id'] for c in calls}) != len(calls): raise ValueError('ONE_BOUNDED_CALL_EACH_REQUIRED')
    reserved = sum(Decimal(c['reserved_usd']) for c in calls)
    if Decimal(money(receipt['reserved_usd'])) != reserved or reserved > r.MAX_SCHEDULE: raise ValueError('EXACT_AGGREGATE_LEDGER_REQUIRED')
    arms = []
    if [(a['case_id'], a['arm']) for a in receipt['arms']] != r.ORDER: raise ValueError('ALL_EIGHT_DECLARED_ARMS_REQUIRED')
    for row in receipt['arms']:
        if row['status'] not in STATUSES or type(row['citations_accepted']) is not bool: raise ValueError('KNOWN_ARM_STATUS_REQUIRED')
        fields = row['final_fields']
        if fields is not None and r.final_fields(json.dumps(fields, ensure_ascii=False)) != fields: raise ValueError('CANONICAL_FINAL_FIELDS_REQUIRED')
        arm = dict(case_id=row['case_id'], arm=row['arm'], status=row['status'], final_fields=fields,
                   final_answer_sha256=sha(row['final_answer_sha256']) if row['final_answer_sha256'] is not None else None,
                   citations_accepted=row['citations_accepted'])
        for key in ('selected_capabilities', 'executed_capabilities', 'checked_treatment'):
            values = row[key]
            if not isinstance(values, list) or len(values) > 3 or any(v not in r.CATALOG for v in values): raise ValueError('BOUNDED_CAPABILITY_IDS_REQUIRED')
            arm[key] = list(values); arm[key + '_count'] = len(values)
        for key in ('arm_seconds', 'sdk_seconds', 'non_sdk_seconds'):
            if key in row: arm[key] = duration(row[key])
        arms.append(arm)
    complete = all('usage_rated_usd' in c for c in calls if c['provider_call'])
    inputs, _ = r.load_frozen()
    return dict(schema='hcl-four-comparison-public-evidence-v1', **identity, authorization_ref=r.AUTH,
                public_output_scope=r.SCOPE, package_sha256=r.digest(package), runtime_sha256=r.RUNTIME,
                model=r.MODEL, planning_tokens=16384, answer_tokens=8192, production_planning_tokens=4096,
                frozen_files_sha256=r.FROZEN_SHA, cases=inputs['cases'], rubric=json.loads((r.ROOT/'rubric.json').read_text()),
                status=receipt['status'], arms=arms, calls=calls, provider_calls=sum(c['provider_call'] for c in calls),
                reserved_usd=str(reserved), usage_complete=complete,
                usage_rated_usd=str(sum(Decimal(c.get('usage_rated_usd', '0')) for c in calls)) if complete else None,
                invoice_cost_usd=None, cost_basis='USAGE_RATED_PEAK_NOT_INVOICE_FULL_RESERVATION_RETAINED',
                elapsed_seconds=duration(receipt['elapsed_seconds']), existing_provider_secret='PRESENT',
                budget_state='CLOSED_NO_TRANSFER_NO_RETRY', remaining_authorized_calls=0, remaining_authorized_usd='0',
                source_first_scoring='PENDING_ANONYMIZED_REVIEW_BEFORE_UNMASKING',
                efficacy_verified=False, representative_accuracy=False, i02_certified=False,
                limitations='FOUR_ASSISTANT_AUTHORED_DEVELOPMENT_ITEMS_NO_GENERALIZATION_EXTRA_HCL_COMPUTE_IMPERFECT_BLINDING')


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--receipt', required=True); p.add_argument('--output', required=True); a = p.parse_args()
    raw = Path(a.receipt).read_bytes()
    if len(raw) > 16*1024*1024: raise ValueError('BOUNDED_RECEIPT_REQUIRED')
    value = export(json.loads(raw), json.loads(r.PACKAGE.read_text()), json.loads(r.GRANT.read_text()),
                   dict(run_id=os.environ['GITHUB_RUN_ID'], head_sha=os.environ['GITHUB_SHA']), json.loads(r.SECRET_CHECK.read_text()))
    r.save(a.output, value); print('SCOPED_FOUR_COMPARISON_PUBLIC_EVIDENCE_SAVED')
