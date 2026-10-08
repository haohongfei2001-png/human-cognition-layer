"""NEW offline-only reliability executor candidate. No active/default live entry or credentials.

Adapted from the reviewed 20261006 bounded two-stage logic, without importing its
runner, authority, mutable stage globals, grants, results, or output-limit port.
The offline entry rejects live clients. The reusable run entry requires a NEW exact
reviewed final package/grant/launch; this candidate creates or activates none.
"""
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import hashlib
import json
import math
import os
from pathlib import Path
import queue
import threading
import time

from hcl.cognition import UniversalHCL, CallAllowance
from hcl.cognition.capability_catalog import CATALOG
from hcl.cognition.deepseek_metered import DeepSeekMeteredPort, MeteredPortError, INPUT_RATE, OUTPUT_RATE
from hcl.cognition.reader_entry import _EXPLICIT_CITATION_FINAL_ANSWER_POLICY
from hcl.cognition.retained import audit_supplied_source_citations
from hcl.cognition.universal_entry import PLANNER_POLICY
from hcl.cognition.executable_entry import executable_entry_contract, planner_inventory

AUTH = 'OWNER_APPROVED_HCL_ENTRY_CONTRACT_SMOKE_20261008_2_CALLS_2_30_CNY'
APPROVED = '2026-10-08T00:10:20Z'  # New independent 2.30-CNY/two-call and bounded synthetic-evidence owner approval.
EXPIRES = None  # Owner removed the calendar cutoff; per-stage/send bounds remain.
MODEL = 'deepseek-v4-pro'
FROZEN_SOURCE_TIME_BASIS = 'FROZEN_PACKET_PREPARATION_TIMESTAMP_NOT_ACTUAL_INGESTION_OR_EVENT_TIME'
TOKENS = {'planning': 16384, 'answer': 16384}
EFFORT = {'planning': 'high', 'answer': 'low'}
MAX_REQUEST_BYTES = 36000
WAIT = 180
CNY_INPUT_RATE, CNY_OUTPUT_RATE = Decimal('9'), Decimal('27')
HOLD_CNY = {'planning': Decimal('1.109664'), 'answer': Decimal('1.109664')}
HOLD_USD = {'planning': Decimal('0.16275072'), 'answer': Decimal('0.16275072')}
CAP_CNY = {1: Decimal('2.30')}
SCHEDULE_CNY = {1: Decimal('2.219328')}
MAX_CALLS = {1: 2}
ELAPSED = {1: 600}
TOTAL_CNY = Decimal('2.30')
KNOWN_RETURN_FAILURES = {'INCOMPLETE_ANSWER_NO_RETRY', 'CONTENT_BOUND_EXCEEDED'}
KNOWN_HCL_FAILURES = {'invalid answer schema', 'NONBLANK_FINAL_ANSWER_REQUIRED', 'invalid bounded task plan',
    'invalid limitations', 'bounded bindings required', 'bounded interpreted question required',
    'unknown capability or operation fields', 'unknown or duplicate source selection',
    'unsupported binding or source', 'invented or stale source anchor', 'operation bound exceeded',
    'NATIVE_HCL_RESULT_REQUIRED_BEFORE_ANSWER', 'planning response exceeds bound',
    'complete context exceeds budget; no truncation', 'answer exceeds bounded contract',
    'duplicate responsibility actor', 'EXPLICIT_READER_INPUT_MODE_REQUIRED', 'INVALID_READER_INPUT_MODE', 'REQUIRED_CHECKED_NATIVE_TREATMENT_ABSENT_BEFORE_ANSWER', 'INVALID_CHECKED_NATIVE_REQUIREMENT'}
METRIC_FIELDS = ('question', 'sources', 'capability_inventory', 'hcl_plan', 'hcl_operations', 'hcl_execution', 'knowledge_basis', 'native_reader_contexts')
KNOWN_HCL_FAILURES |= {'UNAVAILABLE_ENTRY_NOT_SELECTABLE', 'SOURCE_ENTRY_NECESSARY_CONDITION_FAILED_BEFORE_NATIVE',
    'LITERAL_ENTRY_NECESSARY_CONDITION_FAILED_BEFORE_NATIVE', 'TRUSTED_ENTRY_SOURCE_BINDING_CHANGED'}


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def file_sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def runtime_digest(root):
    root = Path(root)
    files = sorted((root / 'hcl').rglob('*.py'))
    if not files:
        raise ValueError('HCL_RUNTIME_MISSING')
    return digest({str(p.relative_to(root)): file_sha(p) for p in files})


def exact_sha(value, length=64):
    if not isinstance(value, str) or len(value) != length or any(c not in '0123456789abcdef' for c in value):
        raise ValueError('EXACT_HASH_REQUIRED')
    return value


def timestamp(value):
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if result.tzinfo is None:
        raise ValueError('UTC_TIME_REQUIRED')
    return result


def save(path, value):
    """Write durable bounded evidence; no raw planner/request/envelope is supplied."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    with temporary.open('w', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, sort_keys=True, indent=2)
        stream.write('\n'); stream.flush(); os.fsync(stream.fileno())
    os.replace(temporary, path)
    fd = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def quote(request_bytes, phase, *, currency='CNY'):
    inp, out = (CNY_INPUT_RATE, CNY_OUTPUT_RATE) if currency == 'CNY' else (INPUT_RATE, OUTPUT_RATE)
    if currency not in ('CNY', 'USD'):
        raise ValueError('EXACT_CURRENCY_REQUIRED')
    return ((2 * request_bytes + 2048) * inp + (TOKENS[phase] + 32) * out) / 1000000



SAFE_FINISH_REASONS = frozenset(('stop', 'length', 'content_filter', 'tool_calls',
    'function_call', 'insufficient_system_resource', 'aborted', 'OTHER_OR_MISSING'))


def safe_response_metadata(raw, phase):
    """Bounded scalar observations only, never text, reasoning or envelopes."""
    choices = raw.get('choices') if isinstance(raw, dict) else None
    count = len(choices) if isinstance(choices, list) and len(choices) <= 100 else None
    reasons = []
    if isinstance(choices, list):
        for item in choices[:10]:
            value = item.get('finish_reason') if isinstance(item, dict) else None
            reasons.append(value if type(value) is str and value in SAFE_FINISH_REASONS else 'OTHER_OR_MISSING')
    message = choices[0].get('message') if isinstance(choices, list) and len(choices) == 1 and isinstance(choices[0], dict) else None
    content = message.get('content') if isinstance(message, dict) else None
    content_chars = len(content) if isinstance(content, str) and len(content) <= 2 * 1024 * 1024 else None
    usage = raw.get('usage') if isinstance(raw, dict) else None
    total = usage.get('completion_tokens') if isinstance(usage, dict) else None
    details = usage.get('completion_tokens_details') if isinstance(usage, dict) else None
    reasoning = details.get('reasoning_tokens') if isinstance(details, dict) else None
    if type(total) is not int or not 0 < total <= TOKENS[phase] + 32 or type(reasoning) is not int or not 0 <= reasoning <= total:
        reasoning = None
    return dict(choice_count=count, finish_reasons=reasons,
        visible_content_characters=content_chars, provider_reported_reasoning_tokens=reasoning)


def require_time(now):
    if APPROVED is None: raise ValueError('OWNER_APPROVAL_NOT_FROZEN')
    if not isinstance(now, datetime) or now.tzinfo is None or now < timestamp(APPROVED):
        raise ValueError('AUTHORIZATION_TIME_OR_SEND_MARGIN_INVALID')


def normalized_cases(packet):
    rows = packet.get('cases')
    if not isinstance(rows, list) or len(rows) != 5 or [c.get('role') for c in rows] != ['smoke'] + ['comparison'] * 4:
        raise ValueError('EXACT_FIVE_PREOUTPUT_CASES_REQUIRED')
    recorded = packet['authored_at_utc']; timestamp(recorded)
    cases = []
    ids = set()
    for row in rows:
        cid = row['case_id']; material = row['model_input']; evaluation = row['private_evaluation']
        if not isinstance(cid, str) or not cid or len(cid) > 128 or ':' in cid or cid in ids:
            raise ValueError('UNIQUE_BOUNDED_CASE_ID_REQUIRED')
        ids.add(cid)
        if set(material) != {'question', 'sources'} or not isinstance(material['question'], str) or not 1 <= len(material['question']) <= 8000:
            raise ValueError('ORDINARY_CASE_INPUT_REQUIRED')
        sources = material['sources']
        if not isinstance(sources, list) or not 1 <= len(sources) <= 8 or len({s['source_id'] for s in sources}) != len(sources):
            raise ValueError('COMPLETE_MULTISOURCE_CASE_REQUIRED')
        for source in sources:
            if not isinstance(source.get('source_id'), str) or not 1 <= len(source['source_id']) <= 128 or source.get('complete') is not True or type(source.get('version')) is not int or source['version'] != 1 or not isinstance(source.get('text'), str) or not source['text']:
                raise ValueError('COMPLETE_VERSION_ONE_SOURCE_REQUIRED')
            if source.get('text_sha256') != hashlib.sha256(source['text'].encode()).hexdigest():
                raise ValueError('SOURCE_TEXT_HASH_MISMATCH')
        for key, n in [('key_fact_obligations', 4), ('inference_boundary_obligations', 3), ('citation_source_obligations', 3)]:
            group = evaluation.get(key)
            if not isinstance(group, list) or len(group) != n or len({x['id'] for x in group}) != n:
                raise ValueError('EXACT_FROZEN_RUBRIC_REQUIRED')
        if evaluation.get('scores_and_results') is not None:
            raise ValueError('CASES_MUST_BE_FROZEN_BEFORE_OUTPUT')
        if row['role'] == 'smoke' and ([s['id'] for s in evaluation.get('smoke_semantic_requirements', [])] != ['S1', 'S2', 'S3', 'S4'] or evaluation.get('smoke_semantic_results') is not None):
            raise ValueError('EXACT_FOUR_SMOKE_SEMANTICS_REQUIRED')
        cases.append(dict(case_id=cid, question=material['question'], sources=[dict(source_id=s['source_id'], version=s['version'], text=s['text'], recorded_at=recorded, record_time_basis=FROZEN_SOURCE_TIME_BASIS) for s in sources]))
    return cases


def order(cases, stage):
    if type(stage) is not int or stage != 1:
        raise ValueError('SINGLE_SMOKE_NO_SECOND_STAGE')
    return [(cases[0]['case_id'], 'HCL')]


def messages(case, arm):
    if arm == 'Base':
        payload = dict(question=case['question'], sources=[{k: s[k] for k in ('source_id', 'version', 'text')} for s in case['sources']], knowledge_basis='SUPPLIED_SOURCES_AND_EXPLICIT_INTERPRETATION')
        policy = _EXPLICIT_CITATION_FINAL_ANSWER_POLICY + ' The answer field must contain a nonblank answer; state an evidence limitation explicitly rather than leaving it empty.'
    elif arm == 'HCL':
        payload = dict(question=case['question'], sources=case['sources'], capability_inventory=planner_inventory(),
            executable_entry_contract=executable_entry_contract(case['sources'], require_checked=True))
        policy = PLANNER_POLICY
    else:
        raise ValueError('EXACT_ARM_REQUIRED')
    encoded_payload = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(',', ':')) if arm == 'HCL' else json.dumps(payload, ensure_ascii=False, sort_keys=True)
    result = [dict(role='system', content=policy), dict(role='user', content=encoded_payload)]
    return result


def declared_source_entry_blockers(case):
    """Bind actual current planner conditions back to the unchanged source IDs."""
    payload = json.loads(messages(case, 'HCL')[-1]['content'])
    contract = payload['executable_entry_contract']
    if contract != executable_entry_contract(payload['sources'], require_checked=True):
        raise ValueError('EXACT_CURRENT_EXECUTABLE_ENTRY_CONTRACT_REQUIRED')
    result = []
    for row in contract['sources']:
        source = payload['sources'][row['source_index']]
        if row['version'] != source['version']:
            raise ValueError('EXACT_CURRENT_EXECUTABLE_ENTRY_SOURCE_REQUIRED')
        result.extend(dict(capability=cid, source_id=source['source_id'], version=row['version'], reason=reason)
            for cid, reason in row['source_entry_blockers'].items())
    return result


def request_and_metrics(phase, prompt):
    """Canonical full request metrics are available BEFORE the 36000-byte guard.

    Messages metrics omit the provider envelope and are deliberately named so.
    The field metrics are standalone compact-JSON value sizes, not additive totals.
    """
    if phase not in TOKENS or not isinstance(prompt, list) or not prompt:
        raise MeteredPortError('BOUNDED_PHASE_MESSAGES_REQUIRED')
    if any(not isinstance(m, dict) or set(m) != {'role', 'content'} or m['role'] not in ('system', 'user', 'assistant') or not isinstance(m['content'], str) for m in prompt):
        raise MeteredPortError('PLAIN_MESSAGE_SCHEMA_REQUIRED')
    request = dict(model=MODEL, max_tokens=TOKENS[phase], response_format={'type': 'json_object'}, reasoning_effort=EFFORT[phase], thinking={'type': 'enabled'}, messages=[dict(m) for m in prompt])
    encoded = canonical(request)
    metrics = dict(full_request_utf8_bytes=len(encoded), full_request_sha256=hashlib.sha256(encoded).hexdigest(), serialized_messages_utf8_bytes=len(canonical(prompt)), serialized_messages_sha256=digest(prompt), maximum_request_bytes=MAX_REQUEST_BYTES, within_request_bound=len(encoded) <= MAX_REQUEST_BYTES)
    try:
        payload = json.loads(prompt[-1]['content'])
    except (ValueError, TypeError):
        payload = None
    if isinstance(payload, dict):
        metrics['payload_utf8_bytes'] = len(prompt[-1]['content'].encode())
        metrics['payload_value_utf8_bytes'] = {key: len(canonical(payload[key])) for key in METRIC_FIELDS if key in payload}
    return request, encoded, metrics


@dataclass(frozen=True)
class OfflinePackage:
    """A snapshot for provider-free checks; never a grant or final live freeze."""
    value: dict
    packet: dict
    runtime_root: Path

    @classmethod
    def build(cls, packet, runtime_root):
        # Copy input once; every reservation rechecks these immutable content hashes.
        packet = json.loads(canonical(packet)); cases = normalized_cases(packet)
        runtime_root = Path(runtime_root).resolve()
        requests = {}
        for index in (0,):
            case = cases[index]
            arms = ['HCL']
            for arm in arms:
                phase = 'planning' if arm == 'HCL' else 'answer'
                request, encoded, metrics = request_and_metrics(phase, messages(case, arm))
                if len(encoded) > MAX_REQUEST_BYTES:
                    raise ValueError('STATIC_REQUEST_EXCEEDS_BOUND')
                requests[case['case_id'] + ':' + arm + ':' + phase] = dict(metrics, reservation_cny=str(quote(len(encoded), phase)), reservation_usd=str(quote(len(encoded), phase, currency='USD')), max_tokens=request['max_tokens'])
        root = Path(__file__).parent
        value = dict(schema='hcl-entry-contract-smoke-offline-package-candidate-v1', status='OFFLINE_ONLY_NOT_A_GRANT_OR_FINAL_FREEZE', authorization_ref=AUTH, currency='CNY', packet_sha256=digest(packet), runtime_sha256=runtime_digest(runtime_root), planning_tokens=16384, answer_tokens=16384, maximum_request_bytes=36000, maximum_aggregate_calls=2, maximum_aggregate_cny='2.30', stage_call_caps={str(k): v for k, v in MAX_CALLS.items()}, stage_cny_caps={str(k): str(v) for k, v in CAP_CNY.items()}, stage_reservation_cny={str(k): str(v) for k, v in SCHEDULE_CNY.items()}, phase_holds_cny={k: str(v) for k, v in HOLD_CNY.items()}, rates_cny={'input': str(CNY_INPUT_RATE), 'output': str(CNY_OUTPUT_RATE)}, usd_reference_only=True, reference_rates_usd={'input': str(INPUT_RATE), 'output': str(OUTPUT_RATE)}, source_recorded_at_basis=FROZEN_SOURCE_TIME_BASIS, source_recorded_at=packet['authored_at_utc'], planning_completion_includes_reasoning=True, maximum_wait_seconds=WAIT, stage_windows_seconds={str(k): v for k, v in ELAPSED.items()}, sdk_retries=0, request_retries=0, replanning=False, model_judge=False, fallback=False, case_replacement=False, maximum_final_characters=64000, maximum_final_texts=1, private_native_review_maximum_bytes=1048576, public_native_maximum_case_records=1, public_native_maximum_operations_per_record=3, public_native_maximum_record_bytes=1048576, public_native_requires_new_explicit_grant_permission=True, openai_sdk_version='2.14.0', z3_solver_version='4.15.4.0', approved_at_bound=APPROVED, expires_at=EXPIRES, stage_orders={str(stage): [list(x) for x in order(cases, stage)] for stage in (1,)}, requests=requests, executor_files={name: file_sha(root / name) for name in ('hcl_entry_contract_smoke_candidate.py', 'hcl_entry_contract_smoke_public.py', 'hcl_entry_contract_smoke_native_public.py', 'hcl_entry_contract_smoke_cli.py', 'hcl_entry_contract_smoke_reviews.py', 'tests/test_hcl_entry_contract_smoke_candidate.py', 'tests/test_hcl_entry_contract_smoke_adapter.py', 'tests/test_hcl_entry_contract_smoke_revision3.py', 'tests/test_hcl_entry_contract_smoke_native_regressions.py', 'tests/test_hcl_entry_contract_smoke_time_and_diagnostics.py', 'tests/test_hcl_entry_contract_smoke_routing_gate.py', 'tests/test_hcl_entry_contract_smoke_prefinal_gate.py')}, unresolved_final_freeze_fields=['source_guard_merge_commit', 'trusted_native_policy_merge_commit', 'final_runtime_commit', 'final_runtime_sha256', 'independent_five_case_review_sha256', 'independent_executor_review_sha256', 'final_execution_file_hashes', 'final_workflow_hashes', 'exact_live_launch_binding'])
        value['reasoning_effort'] = dict(EFFORT)
        value['entry_requirements'] = dict(native_source_and_publication_integrity_required_before_final=True, actual_allowed_checked_native_required_before_final=True, known_blocker_selection_rule='NO_SELECTED_OPERATION_MATCHES_DECLARED_SOURCE_VERSION_ENTRY_BLOCKER', necessary_allowed_family_checked_treatment_required=True, absence_of_blocker_is_not_readiness=True, known_native_failure_stops_before_final_reservation=True, no_second_stage=True, independent_source_review_still_required=True)
        value['declared_source_entry_blockers'] = {case['case_id']: declared_source_entry_blockers(case) for case in (cases[0],)}
        return cls(value=value, packet=packet, runtime_root=runtime_root)

    @property
    def cases(self):
        return normalized_cases(self.packet)

    def verify(self):
        if self.value != OfflinePackage.build(self.packet, self.runtime_root).value:
            raise ValueError('OFFLINE_PACKAGE_OR_RUNTIME_DRIFT')


def final_fields(raw):
    if not isinstance(raw, str) or len(raw) > 64000:
        return None
    try:
        obj = json.loads(raw)
    except (ValueError, TypeError):
        return None
    if not isinstance(obj, dict) or set(obj) != {'answer', 'source_citations', 'uncertainty', 'assumptions'} or any(not isinstance(obj[k], str) for k in ('answer', 'uncertainty', 'assumptions')) or not isinstance(obj['source_citations'], list):
        return None
    for citation in obj['source_citations']:
        if not isinstance(citation, dict) or not {'source_id', 'version', 'quote'} <= set(citation) or not set(citation) <= {'source_id', 'version', 'quote', 'start'} or not isinstance(citation['source_id'], str) or type(citation['version']) is not int or not isinstance(citation['quote'], str) or ('start' in citation and (type(citation['start']) is not int or citation['start'] < 0)):
            return None
    return obj


def accepted(prompt, raw):
    obj = final_fields(raw)
    return bool(obj and obj['answer'].strip() and obj['source_citations'] and audit_supplied_source_citations(prompt, raw)['deliverable'])


def validate_pre_final_native(package, case, prompt):
    """Audit actual native final input before any final reservation or dispatch.

    The native operations already ran once. Only code-generated exact shared-pair
    references are expanded for deterministic validation; original arguments,
    source text and results are neither repaired nor replaced. No model call.
    """
    payload = json.loads(prompt[-1]['content'])
    expected_sources = [{key: source[key] for key in ('source_id', 'version', 'text')} for source in case['sources']]
    if payload.get('question') != case['question'] or payload.get('sources') != expected_sources:
        raise ValueError('EXACT_PRE_FINAL_SOURCE_AND_QUESTION_REQUIRED')
    selected = payload['hcl_plan']['operations']; original_outputs = payload['hcl_operations']
    if not isinstance(selected, list) or not isinstance(original_outputs, list) or len(selected) != len(original_outputs) or not 1 <= len(selected) <= 3:
        raise ValueError('COMPLETE_ACTUAL_NATIVE_CAPTURE_REQUIRED_BEFORE_FINAL')
    outputs = json.loads(canonical(original_outputs))
    contexts = payload.get('native_reader_contexts', [])
    if not isinstance(contexts, list) or len(contexts) > 3:
        raise ValueError('EXACT_SHARED_NATIVE_PAIR_REQUIRED')
    for row in outputs:
        if 'native_reader_context_ref' in row:
            ref = row.pop('native_reader_context_ref')
            if type(ref) is not int or not 0 <= ref < len(contexts) or 'result' in row or 'preparation_policy' in row:
                raise ValueError('EXACT_SHARED_NATIVE_PAIR_REQUIRED')
            context = contexts[ref]
            if not isinstance(context, dict) or set(context) != {'result', 'preparation_policy'}:
                raise ValueError('EXACT_SHARED_NATIVE_PAIR_REQUIRED')
            row.update(json.loads(canonical(context)))
    review = private_native_review(case, dict(plan={'operations': selected}, operations=outputs))
    from hcl_entry_contract_smoke_native_public import validate_captured_native_record
    validate_captured_native_record(review, case, package.value['runtime_sha256'])
    required = entry_requirements_from_actual(package, case, review['validated_operation_arguments'], review['native_outputs'])
    if required['known_source_entry_blockers_avoided'] is not True or required['allowed_family_checked_treatment_present'] is not True:
        raise ValueError('NATIVE_ENTRY_REQUIREMENTS_NOT_SATISFIED_BEFORE_FINAL')
    return required


class BoundedPort(DeepSeekMeteredPort):
    """Fixed ordinary 16384-high/16384-low transport with main-thread-only final capture."""
    def __init__(self, client, ledger, arm_id):
        self.ledger, self.arm_id = ledger, arm_id
        self.final_raw = None; self.responses = {}; self.prompts = {}; self.rows = {}
        self.diagnostics = {}; self.known_failure = None
        super().__init__(client, maximum_wait_seconds=WAIT)

    def _validate_client(self):
        super()._validate_client()
        timeout = self.client.timeout
        values = [timeout] if type(timeout) in (int, float) else [getattr(timeout, key, None) for key in ('connect', 'read', 'write', 'pool')]
        if any(v > WAIT for v in values):
            raise MeteredPortError('FINITE_SDK_TIMEOUT_REQUIRED')

    def request(self, phase, prompt):
        self._validate_client()
        request, encoded, metrics = request_and_metrics(phase, prompt)
        self.ledger.observe_request(self.arm_id, phase, metrics)
        if len(encoded) > MAX_REQUEST_BYTES:
            self.known_failure = 'REQUEST_BOUND_EXCEEDED_NO_TRUNCATION'
            raise MeteredPortError(self.known_failure)
        return request, encoded

    def reservation_usd(self, phase, prompt):
        request, encoded = self.request(phase, prompt)
        if phase == 'answer':
            case = next(case for case in self.ledger.package.cases if case['case_id'] == self.arm_id.split(':')[0])
            try:
                validate_pre_final_native(self.ledger.package, case, prompt)
            except Exception:
                self.known_failure = 'PRE_FINAL_NATIVE_REQUIREMENTS_REJECTED_NO_CALL'
                raise MeteredPortError(self.known_failure) from None
        row = self.ledger.reserve(self.arm_id, phase, request, len(encoded))
        self.rows[phase] = row; self.prompts[phase] = prompt
        return row['reserved_usd']

    def journal(self, snapshot):
        for row in snapshot['attempts']:
            if row['phase'] not in self.rows or Decimal(row['reserved_usd']) != Decimal(self.rows[row['phase']]['reserved_usd']):
                self.ledger.stopped = True
                raise ValueError('DURABLE_RESERVATION_IDENTITY_REQUIRED')
        self.ledger.persist()

    def complete(self, phase, prompt):
        row = self.rows[phase]; start = self.ledger.monotonic()
        try:
            self.ledger.admit()
            request, encoded = self.request(phase, prompt)
            if row['invocation_status'] != 'NOT_INVOKED' or digest(request) != row['request_sha256']:
                raise ValueError('RESERVED_REQUEST_DRIFT')
            row.update(provider_call=not self.ledger.offline, offline_transport_call=self.ledger.offline, invocation_status='INVOKED_OR_SEND_UNKNOWN')
            self.ledger.persist()  # The full hold and send intent reach disk first.
            channel = queue.Queue(maxsize=1)
            create = self.client.chat.completions.create
            sdk_request = {k: v for k, v in request.items() if k != 'thinking'}
            sdk_request['extra_body'] = {'thinking': request['thinking']}
            def invoke():
                try:
                    self.ledger.require_final_dispatch_margin()
                except BaseException:
                    channel.put((False, None, 'GUARD_REFUSED_BEFORE_DISPATCH'))
                    return
                # No serialization, disk write or other blocking work is allowed
                # between the final worker margin check and the SDK invocation.
                try:
                    result = create(**sdk_request)
                    channel.put((True, result, 'DISPATCHED'))
                except BaseException:
                    channel.put((False, None, 'DISPATCHED_OR_UNKNOWN'))
            threading.Thread(target=invoke, daemon=True).start()
            try:
                returned, result, dispatch_state = channel.get(timeout=self.maximum_wait_seconds)
            except queue.Empty:
                self._closed = True
                raise MeteredPortError('DEADLINE_SEND_UNKNOWN_NO_RETRY') from None
            if not returned:
                if dispatch_state == 'GUARD_REFUSED_BEFORE_DISPATCH':
                    row.update(provider_call=False, offline_transport_call=False, invocation_status='NOT_INVOKED')
                    raise MeteredPortError('FINAL_DISPATCH_MARGIN_REJECTED_NO_CALL')
                raise MeteredPortError('PROVIDER_TRANSPORT_FAILURE_NO_RETRY')
            raw = result.model_dump(mode='json') if hasattr(result, 'model_dump') else result
            if not isinstance(raw, dict) or raw.get('model') != MODEL:
                raise MeteredPortError('MODEL_ID_OUTSIDE_FREEZE')
            row['response_metadata'] = safe_response_metadata(raw, phase)
            choices = raw.get('choices')
            message = choices[0].get('message') if isinstance(choices, list) and len(choices) == 1 and isinstance(choices[0], dict) else None
            content = message.get('content') if isinstance(message, dict) else None
            # Only the current main thread can capture or persist visible content.
            # Incomplete/bad-JSON final text is retained unchanged within the bound.
            if phase == 'answer' and isinstance(content, str) and len(content) <= 64000:
                self.final_raw = content
            usage = raw.get('usage')
            if not isinstance(usage, dict):
                raise MeteredPortError('NUMERIC_USAGE_REQUIRED')
            counts = {key: usage.get(key) for key in ('prompt_tokens', 'completion_tokens')}
            if any(type(v) is not int or v <= 0 for v in counts.values()) or ('total_tokens' in usage and (type(usage['total_tokens']) is not int or usage['total_tokens'] != sum(counts.values()))):
                raise MeteredPortError('NUMERIC_USAGE_REQUIRED')
            if counts['prompt_tokens'] > 2 * len(encoded) + 2048 or counts['completion_tokens'] > TOKENS[phase] + 32:
                raise MeteredPortError('USAGE_OUTSIDE_FROZEN_BOUND')
            cny = (counts['prompt_tokens'] * CNY_INPUT_RATE + counts['completion_tokens'] * CNY_OUTPUT_RATE) / 1000000
            usd = (counts['prompt_tokens'] * INPUT_RATE + counts['completion_tokens'] * OUTPUT_RATE) / 1000000
            if cny > Decimal(row['reserved_cny']) or usd > Decimal(row['reserved_usd']):
                raise MeteredPortError('USAGE_OUTSIDE_FROZEN_BOUND')
            self.diagnostics.update(usage_valid=True, usage=counts)
            row.update(usage=counts, usage_rated_cny=str(cny), usage_rated_usd=str(usd))
            if not isinstance(choices, list) or len(choices) != 1 or not isinstance(choices[0], dict) or choices[0].get('finish_reason') != 'stop':
                raise MeteredPortError('INCOMPLETE_ANSWER_NO_RETRY')
            if not isinstance(content, str) or len(content) > (32000 if phase == 'planning' else 64000):
                raise MeteredPortError('CONTENT_BOUND_EXCEEDED')
            self.responses[phase] = content
            row.update(status='RETURNED', invocation_status='RETURNED')
            return dict(text=content, actual_usd=str(usd), usage=counts)
        except Exception as error:
            code = error.args[0] if type(error) is MeteredPortError and len(error.args) == 1 else None
            known = code in KNOWN_RETURN_FAILURES and self.diagnostics.get('usage_valid') is True
            row.update(status='RETURNED_REJECTED' if known else 'FAILED_OR_UNKNOWN', invocation_status='RESPONSE_RETURNED_REJECTED' if known else row['invocation_status'], failure_code=code if known or code == 'FINAL_DISPATCH_MARGIN_REJECTED_NO_CALL' else 'UNKNOWN_SEND_USAGE_COST_OR_IDENTITY_STOP')
            self.known_failure = code if known else None
            if not known:
                self.ledger.stopped = True
            raise
        finally:
            row['sdk_seconds'] = self.ledger.monotonic() - start
            if self.final_raw is not None:
                record = self.ledger.arm(self.arm_id)
                record.update(final_text=self.final_raw, final_answer_sha256=hashlib.sha256(self.final_raw.encode()).hexdigest(), final_fields=final_fields(self.final_raw))
            self.ledger.persist()


class Ledger:
    def __init__(self, directory, package, stage, clock, monotonic, *, offline=True, identity=None, admission_hashes=None):
        self.directory = Path(directory); self.directory.mkdir(mode=0o700, parents=True, exist_ok=False)
        self.path = self.directory / 'receipt.json'; self.package = package; self.stage = stage
        self.offline = offline
        self.clock, self.monotonic = clock, monotonic; self.started = monotonic(); self.stopped = False; self.active = None
        arms = [dict(case_id=c, arm=a, status='NOT_ATTEMPTED', final_text=None, final_fields=None, final_answer_sha256=None, citations_accepted=False, selected_capabilities=[], executed_capabilities=[], checked_treatment=[], native_results=0, final_delivery_code='NOT_REACHED', request_diagnostics=[], runtime_final_context_metrics=None, native_review_sha256=None, native_review_available=False, native_projection_sha256=None, native_projection_status='NOT_CAPTURED', native_integrity_status='NOT_CAPTURED', entry_requirements=None, full_request_metrics_unavailable_reason='ANSWER_PHASE_NOT_REACHED') for c, a in order(package.cases, stage)]
        self.value = dict(schema='hcl-entry-contract-smoke-offline-receipt-v1' if offline else 'hcl-entry-contract-smoke-private-receipt-v1', stage=stage, mode='OFFLINE_SYNTHETIC_NO_PROVIDER' if offline else 'LIVE_EXISTING_ACCOUNT', currency='CNY', usd_reference_only=True, authorization_ref=AUTH, package_sha256=digest(package.value), status='RUNNING', calls=[], arms=arms, reserved_cny='0', reserved_usd='0', started_at=clock().isoformat())
        self.value['identity'] = dict(identity) if identity is not None else None
        self.value['admission_hashes'] = dict(admission_hashes) if admission_hashes is not None else None
        self.native_reviews = []
        self.persist()

    def native_review(self, case, result):
        review = private_native_review(case, result)
        self.native_reviews.append(review)
        save(self.directory / 'native-review-private.json', dict(schema='hcl-entry-contract-smoke-private-native-review-bundle-v1', package_sha256=digest(self.package.value), stage=self.stage, reviews=self.native_reviews))
        row = self.arm(case['case_id'] + ':HCL')
        available = review['review_status'] == 'PENDING_INDEPENDENT_SUBSTANTIVE_SOURCE_FIRST_REVIEW'
        projection_hash = None; projection_status = 'NOT_CAPTURED'; integrity_status = 'NOT_CAPTURED'
        if available:
            try:
                from hcl_entry_contract_smoke_native_public import native_projection_from_capture
                projection_hash = digest(native_projection_from_capture(review, self.package.value['runtime_sha256']))
                projection_status = 'CAPTURED'
            except Exception:
                # Capture observability cannot erase an already returned final
                # or valid usage ledger. No proposal/exception text is copied.
                projection_status = 'REJECTED_UNAVAILABLE'
            try:
                from hcl_entry_contract_smoke_native_public import validate_captured_native_record
                validate_captured_native_record(review, case, self.package.value['runtime_sha256'])
                integrity_status = 'VALIDATED'
            except Exception:
                # Never expose rejected proposals or exception text. The original
                # capture is already durable; final/usage recording continues.
                integrity_status = 'REJECTED_UNAVAILABLE'
        row.update(native_review_sha256=digest(review), native_review_available=available, native_projection_sha256=projection_hash, native_projection_status=projection_status, native_integrity_status=integrity_status, entry_requirements=None)
        if available and len(review['validated_operation_arguments']) == len(review['native_outputs']):
            row['entry_requirements'] = entry_requirements_from_actual(self.package, case, review['validated_operation_arguments'], review['native_outputs'])
        self.persist()

    def arm(self, arm_id):
        return next(a for a in self.value['arms'] if a['case_id'] + ':' + a['arm'] == arm_id)

    def persist(self):
        try:
            save(self.path, self.value)
        except Exception:
            self.stopped = True
            raise

    def validate_ledger(self):
        rows = self.value['calls']; total = Decimal('0'); total_usd = Decimal('0')
        if self.value.get('currency') != 'CNY' or self.value.get('usd_reference_only') is not True or len(rows) > MAX_CALLS[self.stage] or len({r['call_id'] for r in rows}) != len(rows):
            raise ValueError('EXACT_NATIVE_CNY_LEDGER_REQUIRED')
        schedule = order(self.package.cases, self.stage)
        for row in rows:
            case, arm, phase = row['call_id'].split(':')
            if (case, arm) not in schedule or phase not in TOKENS or (arm == 'Base' and phase != 'answer'):
                raise ValueError('EXACT_SCHEDULE_REQUIRED')
            if Decimal(row['reserved_cny']) != HOLD_CNY[phase] or Decimal(row['reserved_usd']) != HOLD_USD[phase]:
                raise ValueError('FULL_NONRECYCLABLE_HOLD_REQUIRED')
            total += HOLD_CNY[phase]; total_usd += HOLD_USD[phase]
        previous = Decimal('0') if self.stage == 1 else SCHEDULE_CNY[1]
        if Decimal(self.value['reserved_cny']) != total or Decimal(self.value['reserved_usd']) != total_usd or total > CAP_CNY[self.stage] or total > SCHEDULE_CNY[self.stage] or previous + total > TOTAL_CNY:
            raise ValueError('NATIVE_CNY_CAP_EXCEEDED')

    def require_final_dispatch_margin(self):
        if self.stopped: raise ValueError('BATCH_STOPPED_NO_RETRY')
        if self.monotonic() - self.started + WAIT >= ELAPSED[self.stage]:
            raise ValueError('FINAL_STAGE_SEND_MARGIN_INVALID')
        require_time(self.clock())

    def admit(self):
        self.validate_ledger()
        if self.stopped:
            raise ValueError('BATCH_STOPPED_NO_RETRY')
        require_time(self.clock())
        if self.monotonic() - self.started + WAIT >= ELAPSED[self.stage]:
            raise ValueError('BATCH_DEADLINE_SEND_MARGIN')
        self.package.verify()

    def observe_request(self, arm_id, phase, metrics):
        row = dict(phase=phase, **metrics)
        observed = self.arm(arm_id)['request_diagnostics']
        old = next((x for x in observed if x['phase'] == phase), None)
        if old is not None and old != row:
            self.stopped = True
            raise ValueError('REQUEST_DIAGNOSTIC_IDENTITY_DRIFT')
        if old is None:
            observed.append(row)
            if phase == 'answer': self.arm(arm_id)['full_request_metrics_unavailable_reason'] = None
            self.persist()

    def reserve(self, arm_id, phase, request, request_bytes):
        try:
            self.admit()
            if arm_id != self.active or phase not in TOKENS:
                raise ValueError('ACTIVE_ARM_REQUIRED')
            case_id, arm = arm_id.split(':'); call_id = arm_id + ':' + phase
            if any(r['call_id'] == call_id for r in self.value['calls']):
                raise ValueError('DUPLICATE_CALL_NO_RETRY')
            static = package_configuration(self.package)['requests'].get(call_id)
            if static:
                if digest(request) != static['full_request_sha256'] or request_bytes != static['full_request_utf8_bytes']:
                    raise ValueError('STATIC_REQUEST_DRIFT')
            elif arm == 'HCL' and phase == 'answer':
                prior = [r for r in self.value['calls'] if r['call_id'] == arm_id + ':planning']
                if len(prior) != 1 or prior[0]['status'] != 'RETURNED':
                    raise ValueError('PLANNING_MUST_RETURN')
                case = next(c for c in self.package.cases if c['case_id'] == case_id)
                payload = json.loads(request['messages'][-1]['content'])
                if payload.get('question') != case['question'] or payload.get('sources') != [{k: s[k] for k in ('source_id', 'version', 'text')} for s in case['sources']]:
                    raise ValueError('COMPLETE_DYNAMIC_SOURCE_IDENTITY_REQUIRED')
            else:
                raise ValueError('UNDECLARED_PHASE')
            held = Decimal(self.value['reserved_cny']); held_usd = Decimal(self.value['reserved_usd'])
            case_held = sum(Decimal(r['reserved_cny']) for r in self.value['calls'] if r['case_id'] == case_id)
            case_max = HOLD_CNY['planning'] + HOLD_CNY['answer']
            prior_stage = Decimal('0') if self.stage == 1 else SCHEDULE_CNY[1]
            if not 0 < request_bytes <= MAX_REQUEST_BYTES or quote(request_bytes, phase) > HOLD_CNY[phase] or case_held + HOLD_CNY[phase] > case_max or len(self.value['calls']) >= MAX_CALLS[self.stage] or held + HOLD_CNY[phase] > min(CAP_CNY[self.stage], SCHEDULE_CNY[self.stage]) or prior_stage + held + HOLD_CNY[phase] > TOTAL_CNY:
                raise ValueError('NATIVE_CNY_CAP_EXCEEDED')
            row = dict(call_id=call_id, case_id=case_id, arm=arm, phase=phase, request_sha256=digest(request), request_bytes=request_bytes, reserved_cny=str(HOLD_CNY[phase]), exact_request_reservation_cny=str(quote(request_bytes, phase)), reserved_usd=str(HOLD_USD[phase]), exact_request_reservation_usd=str(quote(request_bytes, phase, currency='USD')), status='RESERVED_BEFORE_CALL', invocation_status='NOT_INVOKED', provider_call=False, offline_transport_call=False)
            self.value['calls'].append(row); self.value.update(reserved_cny=str(held + HOLD_CNY[phase]), reserved_usd=str(held_usd + HOLD_USD[phase])); self.persist()
            return row
        except Exception:
            self.stopped = True
            raise

    def close(self):
        self.value.update(status='STOPPED_NO_RETRY' if self.stopped else 'COMPLETED_ONE_PASS', finished_at=self.clock().isoformat(), elapsed_seconds=self.monotonic() - self.started, budget_state='CLOSED_NO_TRANSFER_NO_RETRY', remaining_authorized_calls=0, remaining_authorized_cny='0')
        self.stopped = True; self.persist()


def run_offline(client, package, stage, directory, *, phase1_evidence=None, phase1_review=None, phase1_review_sha256=None, clock=lambda: datetime.now(timezone.utc), monotonic=time.monotonic):
    """Provider-free test entry; rejects ordinary/live clients without inspecting secrets."""
    if type(package) is not OfflinePackage:
        raise ValueError('EXACT_OFFLINE_PACKAGE_REQUIRED')
    if getattr(client, 'offline_synthetic', None) is not True:
        raise ValueError('LIVE_EXECUTION_UNAVAILABLE_PENDING_FINAL_FREEZE_AND_REVIEW')
    package.verify(); require_time(clock()); order(package.cases, stage)
    if stage == 2:
        from hcl_entry_contract_smoke_public import validate_phase1_gate
        if phase1_review_sha256 != digest(phase1_review):
            raise ValueError('EXACT_PHASE1_REVIEW_HASH_REQUIRED')
        validate_phase1_gate(package, phase1_evidence, phase1_review)
    return _run(client, package, stage, directory, clock=clock, monotonic=monotonic, offline=True)


def _run(client, package, stage, directory, *, clock, monotonic, offline, identity=None, admission_hashes=None):
    ledger = Ledger(directory, package, stage, clock, monotonic, offline=offline, identity=identity, admission_hashes=admission_hashes)
    cases = {c['case_id']: c for c in package.cases}
    try:
        for record in ledger.value['arms']:
            if ledger.stopped:
                continue
            case_id, arm = record['case_id'], record['arm']; case = cases[case_id]; arm_id = case_id + ':' + arm
            ledger.active = arm_id; start = monotonic(); port = None
            try:
                ledger.admit(); port = BoundedPort(client, ledger, arm_id)
                if arm == 'Base':
                    prompt = messages(case, arm); port.reservation_usd('answer', prompt)
                    raw = port.complete('answer', prompt)['text']; good = accepted(prompt, raw)
                    record.update(status='ANSWER_ACCEPTED' if good else 'FINAL_SCHEMA_OR_CITATIONS_REJECTED', final_delivery_code='DELIVERED' if good else 'SCHEMA_INVALID', citations_accepted=good)
                else:
                    session = UniversalHCL()
                    for source in case['sources']:
                        session.put_source(source['source_id'], source['text']); session.sources[source['source_id']] = dict(source)
                    allowance = CallAllowance(2, HOLD_USD['planning'] + HOLD_USD['answer'], AUTH, journal=port.journal)
                    result = session.answer(case['question'], planner_backend=port, answer_backend=port, allowance=allowance, required_checked_capabilities=tuple(x['capability_id'] for x in next(c for c in package.packet['cases'] if c['case_id']==case_id)['private_evaluation']['predeclared_acceptable_relevant_native_operation_families']))
                    allowance.closed = True
                    ledger.native_review(case, result)
                    record.update(native_results=result['hcl_execution']['native_results'], final_delivery_code=result.get('final_delivery_code', 'NOT_REACHED'), selected_capabilities=[o['capability'] for o in result.get('plan', {}).get('operations', [])], executed_capabilities=[o['capability'] for o in result['operations'] if o.get('executed')], checked_treatment=[o['capability'] for o in result['operations'] if o.get('checked_treatment_present')], runtime_final_context_metrics=result.get('final_context_metrics'))
                    # Only metrics from the actual final messages enter the ledger.
                    # A runtime character-guard refusal has no constructed provider
                    # request; retain size-only diagnostics and an explicit reason.
                    if 'actual_final_messages' in result:
                        _, _, metric = request_and_metrics('answer', result['actual_final_messages'])
                        ledger.observe_request(arm_id, 'answer', metric)
                    raw = port.responses.get('answer', port.final_raw)
                    good = bool(raw is not None and accepted(port.prompts.get('answer'), raw))
                    record['citations_accepted'] = good
                    failure = result.get('failure_reason'); invalid_plan = invalid_final = False
                    if failure == 'complete context exceeds budget; no truncation' and 'actual_final_messages' not in result:
                        record['full_request_metrics_unavailable_reason'] = 'RUNTIME_CONTEXT_REFUSED_BEFORE_PROVIDER_REQUEST_CONSTRUCTION'
                    if failure == 'ORCHESTRATION_FAILURE' and raw is not None:
                        try: json.loads(raw)
                        except (ValueError, TypeError): invalid_final = True
                    if failure == 'ORCHESTRATION_FAILURE' and 'planning' in port.responses:
                        try: session._validate_plan(port.responses['planning'])
                        except (ValueError, TypeError, KeyError): invalid_plan = True
                    if failure and failure not in KNOWN_HCL_FAILURES and not port.known_failure and not invalid_plan and not invalid_final:
                        ledger.stopped = True
                    if ledger.stopped: record['status'] = 'UNKNOWN_FAILURE_STOP'
                    elif result['status'] == 'ANSWERED_WITH_EXPLICIT_LIMITS' and good: record['status'] = 'ANSWER_ACCEPTED'
                    elif port.known_failure: record['status'] = port.known_failure
                    elif raw is not None: record['status'] = 'FINAL_SCHEMA_OR_CITATIONS_REJECTED'
                    elif failure in KNOWN_HCL_FAILURES or invalid_plan: record['status'] = 'BOUNDED_HCL_SCHEMA_SELECTION_OR_ADAPTER_FAILURE'
                    else: ledger.stopped = True; record['status'] = 'UNKNOWN_FAILURE_STOP'
                if raw is not None:
                    record.update(final_text=raw, final_fields=final_fields(raw), final_answer_sha256=hashlib.sha256(raw.encode()).hexdigest())
            except Exception:
                if port and port.final_raw is not None:
                    record.update(final_text=port.final_raw, final_fields=final_fields(port.final_raw), final_answer_sha256=hashlib.sha256(port.final_raw.encode()).hexdigest())
                if port and port.known_failure and not ledger.stopped: record['status'] = port.known_failure
                else: ledger.stopped = True; record['status'] = 'UNKNOWN_FAILURE_STOP'
            finally:
                record['arm_seconds'] = monotonic() - start
                record['sdk_seconds'] = sum(r.get('sdk_seconds', 0) for r in ledger.value['calls'] if r['call_id'].startswith(arm_id + ':'))
                record['non_sdk_seconds'] = max(0, record['arm_seconds'] - record['sdk_seconds'])
                required = record.get('entry_requirements')
                if record['status'] != 'ANSWER_ACCEPTED' or not isinstance(required, dict) or required['known_source_entry_blockers_avoided'] is not True or required['allowed_family_checked_treatment_present'] is not True or record['native_review_available'] is not True or record['native_projection_status'] != 'CAPTURED' or record['native_integrity_status'] != 'VALIDATED':
                    ledger.stopped = True
                ledger.persist()
    finally:
        ledger.close()
    return ledger.value


def validate_launch_proposal(*, run_id, attempt, pages, workflow_id, head_sha, parent_sha, event, paths, marker, package_sha256, grant_sha256, stage, executor_commit, grant_commit, executor_ancestor_of_grant, grant_changed_paths):
    """Pure exact-history/one-marker validator; makes no grant, file, or API call.

    Caller must supply every chronological history page for this NEW workflow.
    A malformed, partial, duplicated, retry, dispatch, or previous history fails.
    """
    exact_sha(head_sha, 40); exact_sha(parent_sha, 40); exact_sha(executor_commit, 40); exact_sha(grant_commit, 40); exact_sha(package_sha256); exact_sha(grant_sha256)
    if parent_sha != grant_commit or executor_commit == grant_commit or executor_ancestor_of_grant is not True or grant_changed_paths != [f'.github/HCL_ENTRY_CONTRACT_SMOKE_20261008_{stage}_GRANT.json']:
        raise ValueError('EXACT_EXECUTOR_TO_GRANT_ADOPTION_REQUIRED')
    if type(stage) is not int or stage not in (1,) or type(attempt) is not int or attempt != 1 or event != 'push' or type(run_id) is not int or run_id <= 0 or type(workflow_id) is not int or workflow_id <= 0:
        raise ValueError('EXACT_FIRST_PUSH_REQUIRED')
    if not isinstance(pages, list) or not pages or any(not isinstance(p, dict) or set(p) != {'total_count', 'workflow_runs'} or type(p['total_count']) is not int or not isinstance(p['workflow_runs'], list) for p in pages):
        raise ValueError('COMPLETE_RUN_HISTORY_REQUIRED')
    rows = [r for p in pages for r in p['workflow_runs']]
    if len({r.get('id') for r in rows}) != len(rows) or any(p['total_count'] != len(rows) for p in pages) or not rows:
        raise ValueError('COMPLETE_RUN_HISTORY_REQUIRED')
    for row in rows:
        if type(row.get('id')) is not int or row.get('workflow_id') != workflow_id or row.get('head_branch') != 'main' or row.get('path') != f'.github/workflows/hcl-entry-contract-smoke-20261008-{stage}-once.yml' or type(row.get('run_attempt')) is not int or row['run_attempt'] != 1:
            raise ValueError('EXACT_WORKFLOW_HISTORY_REQUIRED')
        timestamp(row['created_at'])
    if len(rows) != 1 or rows[0]['id'] != run_id or rows[0].get('head_sha') != head_sha or rows[0].get('event') != 'push':
        raise ValueError('ONE_USE_WORKFLOW_ALREADY_CONSUMED_OR_IDENTITY_CHANGED')
    marker_path = f'.github/HCL_ENTRY_CONTRACT_SMOKE_20261008_{stage}_TRIGGER.json'
    expected = dict(schema='hcl-entry-contract-smoke-marker-proposal-v1', authorization_ref=AUTH, stage=stage, package_sha256=package_sha256, grant_sha256=grant_sha256, executor_commit=executor_commit, grant_commit=grant_commit)
    if paths != [marker_path] or marker != expected:
        raise ValueError('EXACT_MARKER_ONLY_LAUNCH_REQUIRED')
    return True


def validate_readonly_prechecks(price, account, identity, now):
    """Pure evidence check; does not read credentials, query balances, or call APIs.

    Future production adapter must obtain these in one run from the same existing
    secret/account. No account balance, account identifier, token, or raw body enters.
    """
    if set(identity) != {'run_id', 'head_sha'} or not isinstance(identity['run_id'], str) or not identity['run_id'].isascii() or not identity['run_id'].isdecimal():
        raise ValueError('EXACT_RUN_IDENTITY_REQUIRED')
    exact_sha(identity['head_sha'], 40)
    if set(price) != {'run_id', 'head_sha', 'url', 'checked_at', 'sha256', 'rates'} or any(price[k] != v for k, v in identity.items()) or price['url'] != 'https://api-docs.deepseek.com/zh-cn/quick_start/pricing/' or price['rates'] != dict(currency='CNY', input='9.0', output='27.0', model=MODEL, version='DeepSeek-V4-Pro-0813'):
        raise ValueError('EXACT_CNY_PRICE_AND_MODEL_REQUIRED')
    exact_sha(price['sha256'])
    if set(account) != {'schema', 'run_id', 'head_sha', 'checked_at', 'currency', 'available', 'model_calls', 'account_read_queries', 'existing_account_only'} or account['schema'] != 'hcl-entry-contract-smoke-account-readiness-v1' or any(account[k] != v for k, v in identity.items()) or account['currency'] != 'CNY' or account['available'] is not True or account['existing_account_only'] is not True or type(account['model_calls']) is not int or account['model_calls'] != 0 or type(account['account_read_queries']) is not int or account['account_read_queries'] != 1:
        raise ValueError('SAME_EXISTING_CNY_ACCOUNT_REQUIRED')
    if any(not timedelta(0) <= now - timestamp(row['checked_at']) <= timedelta(minutes=10) for row in (price, account)):
        raise ValueError('FRESH_SAME_RUN_PRECHECK_REQUIRED')
    return True


@dataclass(frozen=True)
class FrozenPackage:
    """Load-only final package contract. This module never creates/finalizes one.

    A separately reviewed frozen package must be supplied by the parent after both
    source/policy repairs merge. Offline candidate snapshots cannot satisfy it.
    """
    value: dict
    packet: dict
    runtime_root: Path

    @property
    def cases(self):
        return normalized_cases(self.packet)

    def verify(self):
        required = {'schema', 'status', 'authorization_ref', 'currency', 'packet_sha256', 'case_raw_file_sha256', 'runtime_sha256', 'runtime_commit', 'source_guard_merge_commit', 'trusted_native_policy_merge_commit', 'pursuit_uncertainty_merge_commit', 'planner_lifecycle_contracts_merge_commit', 'independent_case_review_sha256', 'independent_executor_review_sha256', 'configuration', 'workflow_files', 'read_only_reader_files'}
        if not isinstance(self.value, dict) or set(self.value) != required or self.value['schema'] != 'hcl-entry-contract-smoke-final-package-v1' or self.value['status'] != 'FROZEN_BEFORE_THIS_ENTRY_CONTRACT_SMOKE_OUTPUT' or self.value['authorization_ref'] != AUTH or self.value['currency'] != 'CNY':
            raise ValueError('EXACT_REVIEWED_FINAL_PACKAGE_REQUIRED')
        for key in ('runtime_commit', 'source_guard_merge_commit', 'trusted_native_policy_merge_commit', 'pursuit_uncertainty_merge_commit', 'planner_lifecycle_contracts_merge_commit'):
            exact_sha(self.value[key], 40)
        for key in ('packet_sha256', 'case_raw_file_sha256', 'runtime_sha256', 'independent_case_review_sha256', 'independent_executor_review_sha256'):
            exact_sha(self.value[key])
        expected = OfflinePackage.build(self.packet, self.runtime_root).value
        configuration = {k: v for k, v in expected.items() if k not in ('schema', 'status', 'unresolved_final_freeze_fields')}
        if self.value['configuration'] != configuration or self.value['packet_sha256'] != digest(self.packet) or self.value['runtime_sha256'] != expected['runtime_sha256']:
            raise ValueError('FINAL_FROZEN_CONFIGURATION_OR_RUNTIME_DRIFT')
        from hcl_entry_contract_smoke_cli import read_only_reader_pins
        if self.value['read_only_reader_files'] != read_only_reader_pins(self.runtime_root):
            raise ValueError('EXACT_FINAL_READ_ONLY_READER_PINS_REQUIRED')
        workflow_files = self.value['workflow_files']
        paths = [f'.github/workflows/hcl-entry-contract-smoke-20261008-{stage}-once.yml' for stage in (1,)]
        if not isinstance(workflow_files, dict) or set(workflow_files) != set(paths) or any(file_sha(Path(self.runtime_root) / path) != exact_sha(sha) for path, sha in workflow_files.items()):
            raise ValueError('EXACT_FINAL_WORKFLOW_FILES_REQUIRED')
        from hcl_entry_contract_smoke_reviews import verify_review_artifacts
        verify_review_artifacts(self)


def package_configuration(package):
    return package.value['configuration'] if isinstance(package, FrozenPackage) else package.value


def require_new_grant(package, grant, stage, now):
    """Validate, never create or activate, the new exact once-only CNY grant."""
    if type(package) is not FrozenPackage:
        raise ValueError('OFFLINE_CANDIDATE_CANNOT_AUTHORIZE_LIVE_EXECUTION')
    package.verify(); require_time(now); order(package.cases, stage)
    expected = dict(schema='hcl-entry-contract-smoke-new-grant-v1', status='READY', authorization_ref=AUTH, currency='CNY', stage=stage, package_sha256=digest(package.value), approved_at_bound=APPROVED, expires_at=EXPIRES, authorized_calls=MAX_CALLS[stage], authorized_cny=str(CAP_CNY[stage]), executor_commit=grant.get('executor_commit'), phase1_source_review_sha256=grant.get('phase1_source_review_sha256') if stage == 2 else None, public_native_evidence_permission=grant.get('public_native_evidence_permission'), retries=0, historical_budget_transfer=False, other_stage_budget_transfer=False)
    if grant != expected:
        raise ValueError('EXACT_NEW_RELIABILITY_GRANT_REQUIRED')
    exact_sha(grant['executor_commit'], 40)
    from hcl_entry_contract_smoke_native_public import validate_permission
    # No verified private review route exists for this study. Permission is an
    # admission prerequisite, before any account/provider action or SDK factory.
    validate_permission(grant['public_native_evidence_permission'], package.value['packet_sha256'])
    if stage == 2:
        exact_sha(grant['phase1_source_review_sha256'])
    return True



def entry_requirements_from_actual(package, case, operations, native_outputs):
    """Pure necessary failure checks after the original complete native/model round.

    No operation is removed, repaired, pre-run or replaced. Passing these cheap
    conditions never certifies relevance, faithful semantics, truth or answer quality.
    """
    config = package_configuration(package)
    declared = config['declared_source_entry_blockers'].get(case['case_id'])
    if not isinstance(declared, list) or not isinstance(operations, list) or len(operations) > 3 or not isinstance(native_outputs, list) or len(native_outputs) > 3:
        raise ValueError('EXACT_CAPTURED_ENTRY_REQUIREMENTS_INPUT_REQUIRED')
    roots = {s['source_id']: s['version'] for s in case['sources']}
    bad = []
    for index, op in enumerate(operations):
        if not isinstance(op, dict) or op.get('capability') not in CATALOG or not isinstance(op.get('source_ids'), list):
            raise ValueError('EXACT_CAPTURED_ENTRY_REQUIREMENTS_INPUT_REQUIRED')
        if any(op['capability'] == item['capability'] and item['source_id'] in op['source_ids'] and roots.get(item['source_id']) == item['version'] for item in declared):
            bad.append(index)
    original = next(row for row in package.packet['cases'] if row['case_id'] == case['case_id'])
    allowed = {x['capability_id'] for x in original['private_evaluation']['predeclared_acceptable_relevant_native_operation_families']}
    present = any(out.get('capability') in allowed and out.get('executed') is True and out.get('checked_treatment_present') is True for out in native_outputs)
    return dict(evaluated_from_actual_capture=True, known_source_entry_blockers_avoided=not bad,
        blocked_operation_indexes=bad, allowed_family_checked_treatment_present=present,
        semantic_relevance_or_quality_certified=False)


def private_native_review(case, result):
    """Bounded local review facts, never a raw planner response or full request.

    Parsed validated operation arguments and actual trusted-native outputs are
    necessary for substantive relevance review. This stays private to the task;
    the public exporter emits only its hash plus capability IDs/counts.
    """
    plan_operations = result.get('plan', {}).get('operations', [])
    rows = result.get('operations', [])
    if not isinstance(plan_operations, list) or len(plan_operations) > 3 or not isinstance(rows, list) or len(rows) > 3:
        raise ValueError('BOUNDED_NATIVE_REVIEW_REQUIRED')
    arguments = [{key: operation[key] for key in ('capability', 'question', 'source_ids', 'bindings', 'input_mode', 'semantic_candidates') if key in operation} for operation in plan_operations]
    allowed = {'capability', 'status', 'executed', 'result', 'preparation_policy', 'checked_treatment_present', 'reader_any_checked_treatment_present', 'support_claim_ids', 'semantic_input_origin', 'semantic_certification', 'additional_provider_calls', 'request_provenance', 'normative_premise_origin'}
    outputs = [{key: value for key, value in row.items() if key in allowed} for row in rows]
    value = dict(schema='hcl-entry-contract-smoke-private-native-review-v1', case_id=case['case_id'], original_question=case['question'], source_roots=[dict(source_id=s['source_id'], version=s['version'], text_sha256=hashlib.sha256(s['text'].encode()).hexdigest()) for s in case['sources']], validated_operation_arguments=arguments, native_outputs=outputs, review_status='PENDING_INDEPENDENT_SUBSTANTIVE_SOURCE_FIRST_REVIEW')
    encoded = canonical(value)
    if len(encoded) > 1048576:
        return dict(schema='hcl-entry-contract-smoke-private-native-review-v1', case_id=case['case_id'], review_status='NATIVE_REVIEW_BOUND_EXCEEDED_NO_SEMANTIC_PASS', native_review_full_sha256=hashlib.sha256(encoded).hexdigest(), native_review_full_utf8_bytes=len(encoded))
    # A trusted native result cannot legitimately contain provider envelopes or
    # credential fields. Reject recursively instead of retaining a surprising shape.
    blocked = {'reasoning_content', 'reasoning', 'api_key', 'authorization', 'access_token', 'password', 'balance_infos', 'choices', 'raw_plan', 'raw_request', 'raw_response'}
    def inspect(item, depth=0):
        if depth > 48: raise ValueError('NATIVE_REVIEW_DEPTH_EXCEEDED')
        if isinstance(item, dict):
            for key, child in item.items():
                if not isinstance(key, str) or key.lower() in blocked: raise ValueError('PRIVATE_NATIVE_REVIEW_FORBIDDEN_FIELD')
                inspect(child, depth + 1)
        elif isinstance(item, list):
            for child in item: inspect(child, depth + 1)
        elif type(item) not in (str, int, float, bool, type(None)) or (type(item) is float and not math.isfinite(item)):
            raise ValueError('NATIVE_REVIEW_JSON_REQUIRED')
    inspect(value)
    return json.loads(encoded)


def run(client, package, grant, directory, *, launch, price, account, identity, phase1_evidence=None, phase1_review=None, clock=lambda: datetime.now(timezone.utc), monotonic=time.monotonic):
    """Reusable future live entry with a caller-owned existing-account client.

    No credential setup, grant activation, trigger writing, API discovery, or
    default CLI occurs here. All admission facts must already be independently
    reviewed and supplied by the final guarded workflow. Unknowns close holds.
    """
    stage = grant.get('stage')
    require_new_grant(package, grant, stage, clock())
    expected_directory = Path(package.runtime_root).resolve() / f'hcl-entry-contract-smoke-20261008-{stage}-private'
    if Path(directory).resolve() != expected_directory:
        raise ValueError('EXACT_ONE_USE_PRIVATE_DIRECTORY_REQUIRED')
    validate_readonly_prechecks(price, account, identity, clock())
    if launch.get('stage') != stage or str(launch.get('run_id')) != identity['run_id'] or launch.get('head_sha') != identity['head_sha'] or launch.get('executor_commit') != grant['executor_commit'] or launch.get('parent_sha') != launch.get('grant_commit') or launch.get('package_sha256') != digest(package.value) or launch.get('grant_sha256') != digest(grant):
        raise ValueError('EXACT_SAME_RUN_LAUNCH_ADMISSION_REQUIRED')
    validate_launch_proposal(**launch)
    if stage == 2:
        from hcl_entry_contract_smoke_public import validate_phase1_gate
        if digest(phase1_review) != grant['phase1_source_review_sha256']:
            raise ValueError('EXACT_PHASE1_SOURCE_REVIEW_LINK_REQUIRED')
        validate_phase1_gate(package, phase1_evidence, phase1_review, native_permission=grant.get('public_native_evidence_permission'))
    return _run(client, package, stage, directory, clock=clock, monotonic=monotonic, offline=False, identity=identity, admission_hashes=dict(grant_sha256=digest(grant), launch_sha256=digest(launch), price_sha256=digest(price), account_sha256=digest(account)))


if __name__ == '__main__':
    raise SystemExit('NO_DEFAULT_LIVE_CLI: final repaired runtime, reviewed package, new grant and guarded workflow admission are required')
