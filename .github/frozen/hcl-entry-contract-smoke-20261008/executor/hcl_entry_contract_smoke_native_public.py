"""Permission-gated bounded native evidence; never publish a private bundle wholesale.

No transport, SDK, credential, account query, grant creation or permission inference.
Local deterministic native re-execution validates source-rooted captured outputs;
it is not a model call, a retry, a semantic judge, or replacement study evidence.
"""
import json
import math
import re

import hcl_entry_contract_smoke_candidate as r

DESTINATION = 'https://github.com/haohongfei2001-png/human-cognition-layer'
MAX_RECORDS = 1
MAX_OPERATIONS = 3
MAX_RECORD_BYTES = 1048576
PERMISSION_SCOPE = 'ONE_FROZEN_REGRESSION_SMOKE_BOUNDED_SOURCE_VALIDATED_NATIVE_EVIDENCE'
ARGUMENT_ORIGIN = 'PLANNER_PROPOSAL_ANCHORS_VALIDATED_NOT_SEMANTIC_CERTIFICATION'
FORBIDDEN_KEYS = frozenset(('task', 'limitations', 'raw_plan', 'raw_planning', 'planner_response', 'raw_request', 'raw_response', 'messages', 'choices', 'reasoning', 'reasoning_content', 'analysis', 'api_key', 'access_token', 'authorization', 'password', 'balance_infos', 'balance', 'provider_envelope', 'exception', 'traceback', 'error', 'errors', 'private_history', 'conversation_history'))


def validate_permission(permission, packet_sha256):
    """Only an explicit bounded field of the NEW exact grant can authorize output.

    The parent must fill approval_message_ref from verified owner approval. A
    fixture string used in offline tests does not create or activate a grant.
    """
    expected = {'schema', 'authorization_ref', 'approval_message_ref', 'destination', 'packet_sha256', 'scope', 'maximum_case_records', 'maximum_operations_per_record', 'maximum_record_utf8_bytes'}
    if not isinstance(permission, dict) or set(permission) != expected or permission['schema'] != 'hcl-entry-contract-smoke-native-public-permission-v1' or permission['authorization_ref'] != r.AUTH or permission['destination'] != DESTINATION or permission['packet_sha256'] != packet_sha256 or permission['scope'] != PERMISSION_SCOPE:
        raise ValueError('EXPLICIT_NATIVE_PUBLICATION_PERMISSION_REQUIRED')
    if not isinstance(permission['approval_message_ref'], str) or not 1 <= len(permission['approval_message_ref']) <= 256 or any(c.isspace() for c in permission['approval_message_ref']):
        raise ValueError('EXACT_OWNER_APPROVAL_MESSAGE_REFERENCE_REQUIRED')
    for key, value in [('maximum_case_records', MAX_RECORDS), ('maximum_operations_per_record', MAX_OPERATIONS), ('maximum_record_utf8_bytes', MAX_RECORD_BYTES)]:
        if type(permission[key]) is not int or permission[key] != value:
            raise ValueError('EXACT_NATIVE_PUBLICATION_BOUNDS_REQUIRED')
    r.exact_sha(permission['packet_sha256'])
    return True


def _json_safety(value, depth=0):
    if depth > 48:
        raise ValueError('NATIVE_PUBLIC_DEPTH_EXCEEDED')
    if isinstance(value, dict):
        for key, child in value.items():
            if not isinstance(key, str) or key.lower() in FORBIDDEN_KEYS:
                raise ValueError('NATIVE_PUBLIC_FORBIDDEN_FIELD')
            _json_safety(child, depth + 1)
    elif isinstance(value, list):
        for child in value:
            _json_safety(child, depth + 1)
    elif type(value) not in (str, int, float, bool, type(None)) or (type(value) is float and not math.isfinite(value)):
        raise ValueError('NATIVE_PUBLIC_JSON_REQUIRED')


def _session(case):
    session = r.UniversalHCL()
    for source in case['sources']:
        session.put_source(source['source_id'], source['text'])
        session.sources[source['source_id']] = dict(source)
    return session


def _validate_source_anchors(session, argument):
    """Independently verify every anchor, including adapter-rejected proposals.

    The pinned planner validator checks semantic-candidate shape only. Its
    acceptance or a matching rejected native result is not anchor validation.
    Roots have already been matched to the frozen case, and the workspace must
    still hold those exact versions and complete texts. Translation content is
    a planner proposal, never a semantic certification of its source quote.
    """
    session._current(session._versions())
    ids = argument['source_ids']
    for field in ('bindings', 'semantic_candidates'):
        for anchor in argument.get(field, []):
            if not isinstance(anchor, dict):
                raise ValueError('EXACT_FROZEN_SOURCE_ANCHOR_REQUIRED')
            sid = anchor.get('source_id')
            if not isinstance(sid, str) or sid not in ids or sid not in session.sources:
                raise ValueError('EXACT_FROZEN_SOURCE_ANCHOR_REQUIRED')
            if field == 'semantic_candidates' and (len(ids) != 1 or sid != ids[0]):
                raise ValueError('EXACT_FROZEN_SOURCE_ANCHOR_REQUIRED')
            source = session.sources[sid]['text']; quote = anchor.get('quote')
            if not isinstance(quote, str) or not quote:
                raise ValueError('EXACT_FROZEN_SOURCE_ANCHOR_REQUIRED')
            if 'start' in anchor:
                offset = anchor['start']
                if type(offset) is not int or offset < 0 or source[offset:offset + len(quote)] != quote:
                    raise ValueError('EXACT_FROZEN_SOURCE_ANCHOR_REQUIRED')
            elif field == 'bindings' or quote not in source:
                raise ValueError('EXACT_FROZEN_SOURCE_ANCHOR_REQUIRED')


def _validated_arguments(session, arguments):
    if not isinstance(arguments, list) or len(arguments) > MAX_OPERATIONS:
        raise ValueError('BOUNDED_ACTUAL_NATIVE_OPERATIONS_REQUIRED')
    plan = dict(task='Bounded native evidence verification', operations=arguments, limitations=[])
    session._validate_plan(json.dumps(plan, ensure_ascii=False, sort_keys=True),require_input_modes=True)
    for argument in arguments:
        if not isinstance(argument, dict) or not {'capability', 'question', 'source_ids', 'bindings'} <= set(argument) or set(argument) - {'capability', 'question', 'source_ids', 'bindings', 'input_mode', 'semantic_candidates'}:
            raise ValueError('EXACT_SOURCE_VALIDATED_ARGUMENTS_REQUIRED')
        _json_safety(argument)
        _validate_source_anchors(session, argument)
    return arguments


def native_projection_from_capture(review, runtime_sha256):
    """Exact permitted byte projection, computed at capture time without disclosure.

    This is a commitment, not approval or anchor/semantic validation. Only actual
    dispatched operations enter it; undispatched proposal text remains private.
    The complete private capture hash binds those undisclosed original bytes.
    """
    arguments = review['validated_operation_arguments']; outputs = review['native_outputs']
    if not isinstance(arguments, list) or not isinstance(outputs, list) or len(outputs) > len(arguments) or len(arguments) > MAX_OPERATIONS:
        raise ValueError('BOUNDED_CAPTURE_PROJECTION_REQUIRED')
    operations = []
    for index, captured in enumerate(outputs):
        argument = arguments[index]
        if not isinstance(argument, dict) or not isinstance(captured, dict) or captured.get('capability') != argument.get('capability') or type(captured.get('executed')) is not bool:
            raise ValueError('EXACT_CAPTURE_PROJECTION_OPERATION_REQUIRED')
        operations.append(dict(operation_index=index, capability_id=argument['capability'], arguments_origin=ARGUMENT_ORIGIN, source_validated_arguments=json.loads(r.canonical(argument)), native_result_and_policy=json.loads(r.canonical(captured)), arguments_sha256=r.digest(argument), native_output_sha256=r.digest(captured)))
    projection = dict(schema='hcl-entry-contract-smoke-approved-native-record-v1', case_id=review['case_id'], arm='HCL', source_roots=json.loads(r.canonical(review['source_roots'])), original_question_sha256=r.hashlib.sha256(review['original_question'].encode()).hexdigest(), private_native_review_sha256=r.digest(review), operations=operations, actual_operation_count=len(operations), actual_executed_count=sum(row['executed'] for row in outputs), runtime_sha256=runtime_sha256)
    if len(r.canonical(projection)) > MAX_RECORD_BYTES:
        raise ValueError('NATIVE_CAPTURE_PROJECTION_BOUND_EXCEEDED')
    return projection


def published_projection_sha256(record):
    return r.digest({key: value for key, value in record.items() if key != 'native_projection_sha256'})


def _bind_bundle_to_receipt(bundle, receipt, package):
    """Bind original proposals and captured results, not merely case membership."""
    if not isinstance(receipt, dict) or receipt.get('package_sha256') != r.digest(package.value) or type(receipt.get('stage')) is not int or bundle['stage'] != receipt['stage']:
        raise ValueError('EXACT_NATIVE_RECEIPT_PACKAGE_AND_STAGE_REQUIRED')
    arms = receipt.get('arms')
    if not isinstance(arms, list) or any(not isinstance(arm, dict) for arm in arms) or [(arm.get('case_id'), arm.get('arm')) for arm in arms] != r.order(package.cases, receipt['stage']):
        raise ValueError('EXACT_NATIVE_RECEIPT_ARMS_REQUIRED')
    expected = []
    for arm in arms:
        if arm.get('arm') != 'HCL':
            if arm.get('native_review_available') or arm.get('native_review_sha256') is not None or any(arm.get(key) for key in ('selected_capabilities', 'executed_capabilities', 'checked_treatment', 'native_results')):
                raise ValueError('NATIVE_RECEIPT_HCL_ARM_REQUIRED')
        elif arm.get('native_review_available') is True:
            expected.append(arm)
    if [row['case_id'] for row in bundle['reviews']] != [arm['case_id'] for arm in expected]:
        raise ValueError('EXACT_ATTEMPTED_HCL_RECORDS_REQUIRED')
    for row, arm in zip(bundle['reviews'], expected, strict=True):
        # This binds every original argument and native output, including their
        # order and undispatched selections, to the actual durable capture.
        if r.digest(row) != arm.get('native_review_sha256'):
            raise ValueError('EXACT_RECEIPT_NATIVE_CAPTURE_HASH_REQUIRED')
        if arm.get('native_projection_status') != 'CAPTURED' or r.digest(native_projection_from_capture(row, package.value['runtime_sha256'])) != arm.get('native_projection_sha256'):
            raise ValueError('EXACT_RECEIPT_NATIVE_PROJECTION_REQUIRED')
        arguments = row.get('validated_operation_arguments'); outputs = row.get('native_outputs')
        if not isinstance(arguments, list) or not isinstance(outputs, list) or any(not isinstance(value, dict) for value in arguments + outputs) or len(outputs) > len(arguments):
            raise ValueError('EXACT_RECEIPT_NATIVE_SEQUENCE_REQUIRED')
        if any(type(value.get('executed')) is not bool for value in outputs):
            raise ValueError('EXACT_RECEIPT_NATIVE_SEQUENCE_REQUIRED')
        selected = [value.get('capability') for value in arguments]
        dispatched = [value.get('capability') for value in outputs]
        executed = [value.get('capability') for value in outputs if value['executed']]
        checked = [value.get('capability') for value in outputs if value.get('checked_treatment_present')]
        results = sum(value['executed'] and isinstance(value.get('result'), dict) for value in outputs)
        if selected != arm.get('selected_capabilities') or dispatched != selected[:len(outputs)] or executed != arm.get('executed_capabilities') or checked != arm.get('checked_treatment') or type(arm.get('native_results')) is not int or results != arm['native_results']:
            raise ValueError('EXACT_RECEIPT_NATIVE_SEQUENCE_AND_COUNTS_REQUIRED')


def _bind_published_to_receipt(value, receipt, package):
    """Check disclosed actual evidence against optional exact receipt context.

    No undispatched planner proposals are published or reconstructed. Export
    itself already binds the complete private capture before selecting fields.
    """
    if not isinstance(receipt, dict) or receipt.get('package_sha256') != r.digest(package.value) or type(receipt.get('stage')) is not int or receipt['stage'] != value['stage']:
        raise ValueError('EXACT_NATIVE_RECEIPT_PACKAGE_AND_STAGE_REQUIRED')
    arms = receipt.get('arms')
    if not isinstance(arms, list) or any(not isinstance(arm, dict) for arm in arms) or [(arm.get('case_id'), arm.get('arm')) for arm in arms] != r.order(package.cases, receipt['stage']):
        raise ValueError('EXACT_NATIVE_RECEIPT_ARMS_REQUIRED')
    expected = [arm for arm in arms if arm['arm'] == 'HCL' and arm.get('native_review_available') is True]
    if [row['case_id'] for row in value['records']] != [arm['case_id'] for arm in expected]:
        raise ValueError('EXACT_ATTEMPTED_HCL_RECORDS_REQUIRED')
    cases = {case['case_id']: case for case in package.cases}
    for row, arm in zip(value['records'], expected, strict=True):
        if row['private_native_review_sha256'] != arm.get('native_review_sha256'):
            raise ValueError('EXACT_RECEIPT_NATIVE_CAPTURE_HASH_REQUIRED')
        if arm.get('native_projection_status') != 'CAPTURED' or row['native_projection_sha256'] != arm.get('native_projection_sha256') or published_projection_sha256(row) != arm['native_projection_sha256']:
            raise ValueError('EXACT_PUBLISHED_NATIVE_PROJECTION_REQUIRED')
        operations = row['operations']; outputs = [op['native_result_and_policy'] for op in operations]
        selected = arm.get('selected_capabilities')
        if not isinstance(selected, list) or [op['capability_id'] for op in operations] != selected[:len(operations)] or len(operations) > len(selected) or [op['capability'] for op in outputs if op['executed']] != arm.get('executed_capabilities') or [op['capability'] for op in outputs if op.get('checked_treatment_present')] != arm.get('checked_treatment') or type(arm.get('native_results')) is not int or sum(op['executed'] and isinstance(op.get('result'), dict) for op in outputs) != arm['native_results']:
            raise ValueError('EXACT_RECEIPT_NATIVE_SEQUENCE_AND_COUNTS_REQUIRED')
        # Only when every selected operation has a captured dispatch are all
        # bytes needed to reconstitute the capture present in disclosed fields.
        if len(selected) == len(operations):
            reconstructed = r.private_native_review(cases[row['case_id']], dict(plan={'operations': [op['source_validated_arguments'] for op in operations]}, operations=outputs))
            if r.digest(reconstructed) != arm['native_review_sha256']:
                raise ValueError('EXACT_PUBLISHED_NATIVE_CAPTURE_HASH_REQUIRED')


def validate_captured_native_record(row, case, runtime_sha256):
    """Same complete local integrity checks used by disclosure, without publishing.

    Called only after the original round returns. The private capture and original
    final/usage remain unchanged; this replay is neither a model retry nor semantic
    relevance certification. A byte projection alone never passes this check.
    """
    if set(row) != {'schema', 'case_id', 'original_question', 'source_roots', 'validated_operation_arguments', 'native_outputs', 'review_status'} or row['schema'] != 'hcl-entry-contract-smoke-private-native-review-v1' or row['review_status'] != 'PENDING_INDEPENDENT_SUBSTANTIVE_SOURCE_FIRST_REVIEW' or row['case_id'] != case['case_id'] or row['original_question'] != case['question']:
        raise ValueError('COMPLETE_ORIGINAL_NATIVE_REVIEW_REQUIRED')
    roots = [dict(source_id=s['source_id'], version=s['version'], text_sha256=r.hashlib.sha256(s['text'].encode()).hexdigest()) for s in case['sources']]
    if r.canonical(row['source_roots']) != r.canonical(roots):
        raise ValueError('EXACT_SYNTHETIC_SOURCE_ROOTS_REQUIRED')
    if len(r.canonical(row)) > MAX_RECORD_BYTES:
        raise ValueError('NATIVE_PUBLIC_RECORD_BOUND_EXCEEDED_NO_TRUNCATION')
    session = _session(case)
    arguments = _validated_arguments(session, row['validated_operation_arguments'])
    native = row['native_outputs']
    if not isinstance(native, list) or len(native) > len(arguments) or len(native) > MAX_OPERATIONS:
        raise ValueError('BOUNDED_ACTUAL_NATIVE_OPERATIONS_REQUIRED')
    operations = []
    for index, captured in enumerate(native):
        argument = arguments[index]
        if not isinstance(captured, dict) or captured.get('capability') != argument['capability'] or type(captured.get('executed')) is not bool:
            raise ValueError('ACTUAL_NATIVE_OPERATION_IDENTITY_REQUIRED')
        # Re-execute only captured dispatched operations in their original
        # order against complete frozen sources. No hidden planner text or
        # model backend enters this replay. Capture remains original evidence.
        try:
            replay = session._execute(argument, case['question'])
        except ValueError:
            replay = dict(capability=argument['capability'], status='ADAPTER_REJECTED_NOT_COMPLETED', executed=False)
        selected = r.private_native_review(case, dict(plan={'operations': [argument]}, operations=[replay]))['native_outputs'][0]
        if r.canonical(captured) != r.canonical(selected):
            raise ValueError('CAPTURED_NATIVE_RESULT_POLICY_OR_SUPPORT_BINDING_DRIFT')
        _json_safety(captured)
        record = dict(operation_index=index, capability_id=argument['capability'], arguments_origin=ARGUMENT_ORIGIN, source_validated_arguments=json.loads(r.canonical(argument)), native_result_and_policy=json.loads(r.canonical(captured)), arguments_sha256=r.digest(argument), native_output_sha256=r.digest(captured))
        operations.append(record)
    exported = native_projection_from_capture(row, runtime_sha256)
    if exported['operations'] != operations:
        raise ValueError('EXACT_VALIDATED_CAPTURE_PROJECTION_REQUIRED')
    exported['native_projection_sha256'] = r.digest(exported)
    if len(r.canonical(exported)) > MAX_RECORD_BYTES:
        raise ValueError('NATIVE_PUBLIC_RECORD_BOUND_EXCEEDED_NO_TRUNCATION')
    return exported


def export_native_records(bundle, package, permission, *, expected_case_ids=None, receipt=None):
    """Explicitly selected original structured facts, bounded to one case record.

    This function rejects missing approval, unknown cases, extra records, changed
    sources, invented anchors, forbidden content, result/policy/claim-ID changes,
    oversized records, and non-current runtime code. It never truncates content.
    """
    validate_permission(permission, package.value['packet_sha256'])
    package.verify()
    if not isinstance(bundle, dict) or set(bundle) != {'schema', 'package_sha256', 'stage', 'reviews'} or bundle['schema'] != 'hcl-entry-contract-smoke-private-native-review-bundle-v1' or bundle['package_sha256'] != r.digest(package.value) or type(bundle['stage']) is not int or bundle['stage'] not in (1,):
        raise ValueError('EXACT_PRIVATE_NATIVE_BUNDLE_REQUIRED')
    rows = bundle['reviews']
    if not isinstance(rows, list) or not 0 <= len(rows) <= MAX_RECORDS or any(not isinstance(row, dict) for row in rows) or len({row.get('case_id') for row in rows}) != len(rows):
        raise ValueError('ONE_BOUNDED_NATIVE_RECORD_PER_HCL_CASE_REQUIRED')
    cases = {case['case_id']: case for case in package.cases}
    scheduled = [cid for cid, arm in r.order(package.cases, bundle['stage']) if arm == 'HCL']
    if any(row.get('case_id') not in scheduled for row in rows) or [row['case_id'] for row in rows] != [cid for cid in scheduled if any(x.get('case_id') == cid for x in rows)]:
        raise ValueError('EXACT_SCHEDULED_NATIVE_CASE_ORDER_REQUIRED')
    if expected_case_ids is not None and [row['case_id'] for row in rows] != expected_case_ids:
        raise ValueError('EXACT_ATTEMPTED_HCL_RECORDS_REQUIRED')
    if receipt is not None:
        _bind_bundle_to_receipt(bundle, receipt, package)
    output = []
    for row in rows:
        cid = row['case_id']; case = cases[cid]
        exported = validate_captured_native_record(row, case, package.value['runtime_sha256'])
        output.append(exported)
    return dict(schema='hcl-entry-contract-smoke-approved-native-evidence-v1', destination=DESTINATION, permission_sha256=r.digest(permission), packet_sha256=package.value['packet_sha256'], package_sha256=r.digest(package.value), stage=bundle['stage'], receipt_sha256=r.digest(receipt) if receipt is not None else None, records=output, record_count=len(output), semantic_certification=False, reviewed_native_relevance=False)


def validate_published_native_evidence(value, package, permission, *, receipt=None, public_capture=None):
    """Revalidate already-published structured evidence for the stage-two gate."""
    validate_permission(permission, package.value['packet_sha256']); package.verify()
    keys = {'schema', 'destination', 'permission_sha256', 'packet_sha256', 'package_sha256', 'stage', 'receipt_sha256', 'records', 'record_count', 'semantic_certification', 'reviewed_native_relevance'}
    if not isinstance(value, dict) or set(value) != keys or value['schema'] != 'hcl-entry-contract-smoke-approved-native-evidence-v1' or value['destination'] != DESTINATION or value['permission_sha256'] != r.digest(permission) or value['packet_sha256'] != package.value['packet_sha256'] or value['package_sha256'] != r.digest(package.value) or type(value['stage']) is not int or value['stage'] not in (1,) or value['semantic_certification'] is not False or value['reviewed_native_relevance'] is not False:
        raise ValueError('EXACT_APPROVED_NATIVE_EVIDENCE_REQUIRED')
    if value['receipt_sha256'] is not None:
        r.exact_sha(value['receipt_sha256'])
    if receipt is not None and value['receipt_sha256'] != r.digest(receipt):
        raise ValueError('EXACT_NATIVE_RECEIPT_HASH_REQUIRED')
    if value['receipt_sha256'] is not None and receipt is None and public_capture is None:
        raise ValueError('ACTUAL_NATIVE_CAPTURE_CONTEXT_REQUIRED')
    if public_capture is not None and (not isinstance(public_capture, dict) or public_capture.get('receipt_sha256') != value['receipt_sha256'] or value['receipt_sha256'] is None):
        raise ValueError('EXACT_PUBLIC_CAPTURE_RECEIPT_HASH_REQUIRED')
    records = value['records']; cases = {case['case_id']: case for case in package.cases}
    scheduled = [cid for cid, arm in r.order(package.cases, value['stage']) if arm == 'HCL']
    if not isinstance(records, list) or len(records) > MAX_RECORDS or any(not isinstance(row, dict) for row in records) or type(value['record_count']) is not int or value['record_count'] != len(records) or len({row.get('case_id') for row in records}) != len(records) or any(row.get('case_id') not in scheduled for row in records) or [row['case_id'] for row in records] != [cid for cid in scheduled if any(row['case_id'] == cid for row in records)]:
        raise ValueError('EXACT_BOUNDED_NATIVE_RECORD_ORDER_REQUIRED')
    for row in records:
        expected = {'schema', 'case_id', 'arm', 'source_roots', 'original_question_sha256', 'private_native_review_sha256', 'operations', 'actual_operation_count', 'actual_executed_count', 'runtime_sha256', 'native_projection_sha256'}
        if set(row) != expected or row['schema'] != 'hcl-entry-contract-smoke-approved-native-record-v1' or row['arm'] != 'HCL' or row['runtime_sha256'] != package.value['runtime_sha256'] or len(r.canonical(row)) > MAX_RECORD_BYTES:
            raise ValueError('EXACT_BOUNDED_NATIVE_RECORD_REQUIRED')
        r.exact_sha(row['native_projection_sha256'])
        if published_projection_sha256(row) != row['native_projection_sha256']:
            raise ValueError('EXACT_PUBLISHED_NATIVE_PROJECTION_REQUIRED')
        case = cases[row['case_id']]; session = _session(case)
        roots = [dict(source_id=s['source_id'], version=s['version'], text_sha256=r.hashlib.sha256(s['text'].encode()).hexdigest()) for s in case['sources']]
        if r.canonical(row['source_roots']) != r.canonical(roots) or row['original_question_sha256'] != r.hashlib.sha256(case['question'].encode()).hexdigest():
            raise ValueError('EXACT_NATIVE_SOURCE_AND_QUESTION_REQUIRED')
        r.exact_sha(row['private_native_review_sha256'])
        operations = row['operations']
        if not isinstance(operations, list) or len(operations) > MAX_OPERATIONS or type(row['actual_operation_count']) is not int or row['actual_operation_count'] != len(operations):
            raise ValueError('EXACT_ACTUAL_NATIVE_OPERATION_COUNT_REQUIRED')
        if any(not isinstance(operation, dict) or 'source_validated_arguments' not in operation for operation in operations):
            raise ValueError('EXACT_SELECTED_AND_CAPTURED_ARGUMENTS_REQUIRED')
        arguments = _validated_arguments(session, [operation['source_validated_arguments'] for operation in operations])
        for index, (operation, argument) in enumerate(zip(operations, arguments, strict=True)):
            if set(operation) != {'operation_index', 'capability_id', 'arguments_origin', 'source_validated_arguments', 'native_result_and_policy', 'arguments_sha256', 'native_output_sha256'} or operation['arguments_origin'] != ARGUMENT_ORIGIN or type(operation['operation_index']) is not int or operation['operation_index'] != index or operation['capability_id'] != argument['capability'] or operation['arguments_sha256'] != r.digest(argument) or operation['native_output_sha256'] != r.digest(operation['native_result_and_policy']):
                raise ValueError('EXACT_NATIVE_OPERATION_HASH_AND_IDENTITY_REQUIRED')
            try: replay = session._execute(argument, case['question'])
            except ValueError: replay = dict(capability=argument['capability'], status='ADAPTER_REJECTED_NOT_COMPLETED', executed=False)
            selected = r.private_native_review(case, dict(plan={'operations': [argument]}, operations=[replay]))['native_outputs'][0]
            if r.canonical(selected) != r.canonical(operation['native_result_and_policy']):
                raise ValueError('NATIVE_PUBLIC_RESULT_REPLAY_MISMATCH')
            _json_safety(operation)
        if type(row['actual_executed_count']) is not int or row['actual_executed_count'] != sum(operation['native_result_and_policy']['executed'] for operation in operations):
            raise ValueError('EXACT_EXECUTED_NATIVE_COUNT_REQUIRED')
    if receipt is not None:
        _bind_published_to_receipt(value, receipt, package)
    if public_capture is not None:
        _bind_published_to_receipt(value, public_capture, package)
    return True
