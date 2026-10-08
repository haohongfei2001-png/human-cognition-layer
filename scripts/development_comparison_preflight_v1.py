"""Small synthetic-only fairness preflight for ordinary Base versus HCL.

There is no SDK, live transport, grant, launch marker, public exporter or semantic
success gate here. Complete injected responses and requests are local test data.
The archived readers are reused for input/citation/native integrity, not their
single-smoke treatment requirement, budget authority or stage-two gate.
"""
import copy
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import time

from hcl.cognition import UniversalHCL, CallAllowance
from hcl.cognition import deepseek_metered as meter
from hcl.cognition.universal_entry import safe_orchestration_failure_details
from scripts.hcl_offline_diagnostic_export_v1 import require_plain_json
from scripts.hcl_offline_diagnostic_reference import _reference as ref, _native as native

MODE = 'SYNTHETIC_FAIRNESS_PREFLIGHT_NO_LIVE_AUTHORITY'
MAX_BYTES = 36000
TOKENS = 16384


def canonical(value):
    require_plain_json(value)
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def cases_snapshot(cases):
    """Only model input fields; no gold, selection rubric or evaluator metadata."""
    require_plain_json(cases)
    if type(cases) is not list or not 1 <= len(cases) <= 2:
        raise ValueError('ONE_OR_TWO_COMPLETE_CASES_REQUIRED')
    ids = set()
    for case in cases:
        if type(case) is not dict or set(case) != {'case_id', 'question', 'sources'}:
            raise ValueError('MODEL_INPUT_ONLY_CASE_REQUIRED')
        if type(case['case_id']) is not str or not 1 <= len(case['case_id']) <= 128 or case['case_id'] in ids:
            raise ValueError('UNIQUE_CASE_ID_REQUIRED')
        ids.add(case['case_id'])
        if type(case['question']) is not str or not 1 <= len(case['question']) <= 8000:
            raise ValueError('BOUNDED_ORIGINAL_QUESTION_REQUIRED')
        sources = case['sources']
        if type(sources) is not list or not 1 <= len(sources) <= 8:
            raise ValueError('COMPLETE_SOURCES_REQUIRED')
        source_ids = set()
        for source in sources:
            if type(source) is not dict or set(source) != {'source_id', 'version', 'text', 'recorded_at', 'record_time_basis'}:
                raise ValueError('EXACT_SOURCE_SNAPSHOT_REQUIRED')
            if (type(source['source_id']) is not str or not 1 <= len(source['source_id']) <= 128
                    or source['source_id'] in source_ids or type(source['version']) is not int or source['version'] != 1
                    or type(source['text']) is not str or not source['text']
                    or any(type(source[k]) is not str or not source[k] for k in ('recorded_at', 'record_time_basis'))):
                raise ValueError('INITIAL_VERSION_SOURCE_SNAPSHOT_REQUIRED')
            source_ids.add(source['source_id'])
        if sum(len(s['text']) for s in sources) > 64000:
            raise ValueError('COMPLETE_SOURCE_BOUND_NO_TRUNCATION')
    return json.loads(canonical(cases))


def request(arm, phase, messages):
    """Base keeps high reasoning; HCL uses its unchanged ordinary phase settings."""
    require_plain_json(messages)
    if (meter.MODEL != 'deepseek-v4-pro' or meter.OUTPUT_TOKENS != {'planning': TOKENS, 'answer': TOKENS}
            or meter.REASONING_EFFORT != {'planning': 'high', 'answer': 'low'} or meter.MAX_REQUEST_BYTES != MAX_BYTES):
        raise ValueError('REVIEWED_PHASE_CONFIGURATION_CHANGED')
    if (arm, phase) not in (('Base', 'answer'), ('HCL', 'planning'), ('HCL', 'answer')):
        raise ValueError('EXACT_ARM_PHASE_REQUIRED')
    value, _ = meter.bounded_request(phase, messages)
    if arm == 'Base':
        value['reasoning_effort'] = 'high'
    encoded = canonical(value)
    if len(encoded) > MAX_BYTES:
        raise ValueError('REQUEST_BOUND_EXCEEDED_NO_TRUNCATION')
    return value


def illustrative_quote(request_bytes):
    """Historical peak 9/27 CNY rates, not a current-price check or spending grant."""
    if type(request_bytes) is not int or not 1 <= request_bytes <= MAX_BYTES:
        raise ValueError('BOUNDED_WIRE_SIZE_REQUIRED')
    return str((Decimal(2 * request_bytes + 2048) * 9 + Decimal(TOKENS + 32) * 27) / 1000000)


def schedule(cases):
    return [(case['case_id'], arm) for i, case in enumerate(cases)
            for arm in (('Base', 'HCL') if i % 2 == 0 else ('HCL', 'Base'))]


def _source_projection(case):
    return [{k: source[k] for k in ('source_id', 'version', 'text')} for source in case['sources']]


def _validate_payload(case, phase, messages, runtime_sha256):
    payload = json.loads(messages[-1]['content'])
    expected = case['sources'] if phase == 'planning' else _source_projection(case)
    if payload['question'] != case['question'] or payload['sources'] != expected:
        raise ValueError('FULL_ORIGINAL_INPUT_BINDING_REQUIRED')
    if phase == 'planning':
        if payload['executable_entry_contract']['caller_requirement'] != 'ORDINARY_EVIDENCE_LIMITS_ALLOWED':
            raise ValueError('ORDINARY_HCL_WITHOUT_STRICT_FAMILY_GATE_REQUIRED')
        return
    planned = payload['hcl_plan']['operations']
    actual = payload['hcl_operations']
    if (type(planned) is not list or type(actual) is not list
            or not 1 <= len(planned) <= 3 or len(actual) != len(planned)
            or any(type(row) is not dict for row in actual)):
        raise ValueError('COMPLETE_PREFINAL_NATIVE_OPERATIONS_REQUIRED')
    # Expand only the runtime's exact shared-pair representation for the existing
    # native integrity replay. This does not assert treatment or relevance.
    outputs = copy.deepcopy(payload['hcl_operations'])
    for row in outputs:
        if 'native_reader_context_ref' in row:
            index = row.pop('native_reader_context_ref')
            if type(index) is not int or not 0 <= index < len(payload.get('native_reader_contexts', [])):
                raise ValueError('EXACT_NATIVE_CONTEXT_REFERENCE_REQUIRED')
            if 'result' in row or 'preparation_policy' in row:
                raise ValueError('EXACT_NATIVE_CONTEXT_REFERENCE_REQUIRED')
            shared = payload['native_reader_contexts'][index]
            if set(shared) != {'result', 'preparation_policy'}:
                raise ValueError('EXACT_NATIVE_CONTEXT_REFERENCE_REQUIRED')
            row.update(copy.deepcopy(shared))
    capture = ref.private_native_review(case, {'plan': payload['hcl_plan'], 'operations': outputs})
    native.validate_captured_native_record(capture, case, runtime_sha256)
    native_count = sum(row.get('executed') is True and type(row.get('result')) is dict for row in outputs)
    summary = dict(status='NATIVE_RESULTS_RETURNED', selected_operations=len(planned),
                   dispatched_operations=len(outputs), native_results=native_count,
                   selection_basis='LLM_BEST_EFFORT_NOT_SEMANTIC_CERTIFICATION', execution_is_treatment_proof=False)
    if not native_count or canonical(payload.get('hcl_execution')) != canonical(summary):
        raise ValueError('EXACT_PREFINAL_NATIVE_EXECUTION_SUMMARY_REQUIRED')


class _SyntheticPort:
    """Closed deterministic transport; no callbacks, clients or SDK-shaped objects."""
    provider_free = True

    def __init__(self, case, arm, responses, runtime_sha256):
        self.case, self.arm = case, arm
        self.responses = dict(responses)
        self.runtime_sha256 = runtime_sha256
        self.events, self._reserved = [], {}
        self.integrity_failure = False

    def reservation_usd(self, phase, messages):
        if phase in self._reserved or any(e['phase'] == phase for e in self.events):
            raise ValueError('NO_DUPLICATE_PHASE_OR_RETRY')
        try:
            value = request(self.arm, phase, messages)
            if self.arm == 'HCL':
                if phase == 'answer':
                    if (len(self.events) != 1 or self.events[0]['phase'] != 'planning'
                            or self.events[0]['status'] != 'INJECTED_RETURNED'):
                        raise ValueError('EXACT_RETURNED_PLANNING_EVENT_REQUIRED')
                    original_plan = native._session(self.case)._validate_plan(
                        self.events[0]['response_text'], require_input_modes=True)
                    if canonical(json.loads(messages[-1]['content']).get('hcl_plan')) != canonical(original_plan):
                        raise ValueError('ORIGINAL_RETURNED_PLAN_BINDING_REQUIRED')
                _validate_payload(self.case, phase, messages, self.runtime_sha256)
            else:
                payload = json.loads(messages[-1]['content'])
                if payload['question'] != self.case['question'] or payload['sources'] != _source_projection(self.case):
                    raise ValueError('FULL_ORIGINAL_INPUT_BINDING_REQUIRED')
        except Exception:
            self.integrity_failure = True
            raise
        self._reserved[phase] = value
        return '0'  # Exact synthetic transport only; illustrative CNY quote is separate.

    def complete(self, phase, messages):
        value = request(self.arm, phase, messages)
        if self._reserved.pop(phase, None) != value:
            self.integrity_failure = True
            raise ValueError('EXACT_RESERVED_REQUEST_REQUIRED')
        raw = self.responses[phase]
        encoded = canonical(value)
        event = dict(phase=phase, request=value, request_sha256=hashlib.sha256(encoded).hexdigest(),
                     request_bytes=len(encoded), illustrative_peak_quote_cny=illustrative_quote(len(encoded)),
                     response_text=raw, status='INJECTED_UNKNOWN' if raw is None else 'INJECTED_RETURNED')
        self.events.append(event)
        if raw is None:
            raise RuntimeError('SYNTHETIC_TRANSPORT_UNKNOWN')
        return dict(text=raw, actual_usd='0', usage={'prompt_tokens': 1, 'completion_tokens': 1})


def run_synthetic(cases, responses):
    """Run every fixed arm unless integrity/unknown-send stops the remaining arms.

    Known output/native failures stay in the denominator. This is an offline
    design control, not permission for a future paid run to continue after failure.
    Responses use keys case_id:arm:phase and strings, or None for an unknown return.
    """
    cases = cases_snapshot(cases)
    require_plain_json(responses)
    expected = {f'{case["case_id"]}:{arm}:{phase}' for case in cases
                for arm, phase in (('Base', 'answer'), ('HCL', 'planning'), ('HCL', 'answer'))}
    if (type(responses) is not dict or set(responses) != expected
            or any(value is not None and (type(value) is not str or len(value) > 64000) for value in responses.values())):
        raise ValueError('EXACT_BOUNDED_SYNTHETIC_RESPONSES_REQUIRED')
    runtime = ref.runtime_digest(Path(__file__).resolve().parents[1])
    frozen_input = digest(cases)
    rows = [dict(case_id=cid, arm=arm, status='NOT_ATTEMPTED', events=[], semantic_review='NOT_EVALUATED_SYNTHETIC_ONLY')
            for cid, arm in schedule(cases)]
    for row in rows:
        case = next(c for c in cases if c['case_id'] == row['case_id'])
        arm = row['arm']
        port = _SyntheticPort(case, arm, {phase: responses[f'{case["case_id"]}:{arm}:{phase}']
            for phase in (('answer',) if arm == 'Base' else ('planning', 'answer'))}, runtime)
        started = time.monotonic()
        if arm == 'Base':
            prompt = ref.messages(case, 'Base')
            try:
                port.reservation_usd('answer', prompt)
                raw = port.complete('answer', prompt)['text']
                accepted = ref.accepted(prompt, raw)
                row.update(status='ANSWER_ACCEPTED' if accepted else 'ANSWER_REJECTED', delivery_accepted=accepted, final_text=raw)
            except Exception:
                row.update(status='BASE_UNAVAILABLE', delivery_accepted=False, final_text=None)
            row.update(native_capture=None, native_integrity='NOT_APPLICABLE', native_results=0, checked_results=0)
        else:
            session = UniversalHCL()
            for source in case['sources']:
                session.put_source(source['source_id'], source['text'])
                session.sources[source['source_id']] = dict(source)
            result = session.answer(case['question'], planner_backend=port, answer_backend=port,
                                    allowance=CallAllowance(2, Decimal('0'), MODE), required_checked_capabilities=())
            # Runtime tuples (source_versions) have their ordinary JSON array
            # representation; native values and all returned text stay exact.
            row.update(runtime_receipt=json.loads(ref.canonical(result)), status=result['status'],
                       final_text=result.get('answer_raw'), safe_failure=safe_orchestration_failure_details(result),
                       delivery_accepted=result['status'] == 'ANSWERED_WITH_EXPLICIT_LIMITS' and ref.accepted(
                           result.get('actual_final_messages', []), result.get('answer_raw')),
                       native_results=result['hcl_execution']['native_results'],
                       checked_results=sum(r.get('executed') is True and r.get('checked_treatment_present') is True for r in result['operations']))
            capture = None
            try:
                capture = ref.private_native_review(case, result)
                native.validate_captured_native_record(capture, case, runtime)
                row.update(native_capture=capture, native_integrity='VALIDATED_NOT_SEMANTIC_CERTIFICATION')
            except Exception:
                row.update(native_capture=capture, native_integrity='REJECTED')
                port.integrity_failure = True
        row.update(events=port.events, offline_elapsed_seconds=time.monotonic() - started,
                   input_sha256=digest(case))
        if (port.integrity_failure or any(e['status'] == 'INJECTED_UNKNOWN' for e in port.events)
                or digest(cases) != frozen_input or ref.runtime_digest(Path(__file__).resolve().parents[1]) != runtime):
            row['comparison_stop'] = 'INTEGRITY_OR_UNKNOWN_STOP_NO_RETRY'
            break
    return dict(schema='hcl-development-comparison-preflight-v1', mode=MODE,
                live_execution_authorized=False, provider_calls=0, actual_spend_cny='0',
                efficacy_verified=False, i02_certified=False, runtime_sha256=runtime,
                original_cases=cases, input_sha256=frozen_input, arms=rows,
                offline_transport_calls=sum(len(r['events']) for r in rows),
                maximum_potential_calls=3 * len(cases),
                illustrative_full_schedule_peak_cny=str(Decimal(illustrative_quote(MAX_BYTES)) * 3 * len(cases)),
                cost_basis='HISTORICAL_RATE_CAPACITY_ARITHMETIC_NOT_CURRENT_PRICE_OR_AUTHORITY',
                comparison_basis='STRONG_BASE_HIGH_VS_ORDINARY_HCL_HIGH_LOW_NOT_COMPUTE_MATCHED')


def save_original(result, path):
    """Local synthetic original only, exclusive create; return an external byte anchor."""
    if result.get('mode') != MODE or result.get('live_execution_authorized') is not False or result.get('provider_calls') != 0:
        raise ValueError('SYNTHETIC_ORIGINAL_REQUIRED')
    raw = canonical(result) + b'\n'
    with Path(path).open('xb') as stream:
        stream.write(raw)
    return hashlib.sha256(raw).hexdigest()


def load_original(path, trusted_sha256):
    """A caller-retained anchor is required; recomputing a changed file is not trust."""
    raw = Path(path).read_bytes()
    if hashlib.sha256(raw).hexdigest() != trusted_sha256:
        raise ValueError('ORIGINAL_SYNTHETIC_BYTES_CHANGED')
    value = json.loads(raw)
    if canonical(value) + b'\n' != raw:
        raise ValueError('EXACT_CANONICAL_SYNTHETIC_ORIGINAL_REQUIRED')
    return value
