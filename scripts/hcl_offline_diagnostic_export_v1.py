"""Provider-free complete-chain diagnostic harness; no live executor or grant.

Only the exact deterministic FakeClient is admitted. The archived modules are
read-only implementation references, never authority. Whole runtime/request/native
identities, full non-recyclable simulated holds and the one-pass stop gate remain.
Nothing here recovers the cause of a historical receipt missing a diagnosis.
"""
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from decimal import Decimal
import hashlib
import json
import math
import time
from types import SimpleNamespace

from hcl.cognition import UniversalHCL, CallAllowance
from hcl.cognition.universal_entry import safe_orchestration_failure_details
from scripts.hcl_offline_diagnostic_reference import _reference, PINS

__all__ = ('OfflinePackage', 'FakeClient', 'run_offline', 'clean_diagnostic')

AUTH = 'OFFLINE_DIAGNOSTIC_TEST_ONLY_NO_LIVE_AUTHORITY'
MODE = 'OFFLINE_SYNTHETIC_NO_PROVIDER'
RECEIPT_SCHEMA = 'hcl-offline-diagnostic-receipt-v1'
MODEL = _reference.MODEL
TOKENS, EFFORT = dict(_reference.TOKENS), dict(_reference.EFFORT)
HOLD_CNY, HOLD_USD = dict(_reference.HOLD_CNY), dict(_reference.HOLD_USD)
MAX_REQUEST_BYTES, WAIT = _reference.MAX_REQUEST_BYTES, _reference.WAIT
CAP_CNY, SCHEDULE_CNY = dict(_reference.CAP_CNY), dict(_reference.SCHEDULE_CNY)
MAX_CALLS, ELAPSED = dict(_reference.MAX_CALLS), dict(_reference.ELAPSED)
TOTAL_CNY = _reference.TOTAL_CNY
CNY_INPUT_RATE, CNY_OUTPUT_RATE = _reference.CNY_INPUT_RATE, _reference.CNY_OUTPUT_RATE
CATALOG = _reference.CATALOG
KNOWN_HCL_FAILURES = frozenset(_reference.KNOWN_HCL_FAILURES) | {'INVALID_PLANNING_JSON'}
canonical, digest, save = _reference.canonical, _reference.digest, _reference.save
file_sha, runtime_digest, exact_sha = _reference.file_sha, _reference.runtime_digest, _reference.exact_sha
quote, messages, order = _reference.quote, _reference.messages, _reference.order
accepted, final_fields = _reference.accepted, _reference.final_fields
request_and_metrics = _reference.request_and_metrics
package_configuration = _reference.package_configuration


def require_plain_json(value, depth=0):
    """Reject enum/object spoofing before membership tests or JSON serialization."""
    if depth > 64:
        raise ValueError('PLAIN_BOUNDED_JSON_REQUIRED')
    if type(value) is dict:
        for key, child in value.items():
            if type(key) is not str:
                raise ValueError('PLAIN_BOUNDED_JSON_REQUIRED')
            require_plain_json(child, depth + 1)
    elif type(value) is list:
        for child in value:
            require_plain_json(child, depth + 1)
    elif type(value) not in (str, int, float, bool, type(None)) or (type(value) is float and not math.isfinite(value)):
        raise ValueError('PLAIN_BOUNDED_JSON_REQUIRED')


def clean_diagnostic(value):
    """Validate by round-tripping the current runtime helper, not a copied enum list."""
    if value is None:
        return None
    if type(value) is not dict or set(value) != {'code', 'stage'} or any(type(key) is not str for key in value) or any(type(value[key]) is not str for key in ('code', 'stage')):
        raise ValueError('EXACT_SAFE_ORCHESTRATION_DIAGNOSTIC_REQUIRED')
    safe = safe_orchestration_failure_details(dict(status='ORCHESTRATION_UNAVAILABLE_OR_FAILED',
        failure_reason=value['code'], failure_stage=value['stage']))
    if safe != value:
        raise ValueError('EXACT_SAFE_ORCHESTRATION_DIAGNOSTIC_REQUIRED')
    return dict(safe)


@dataclass(frozen=True)
class OfflinePackage:
    """New offline snapshot; cannot be passed as a frozen live package."""
    value: dict
    packet: dict
    runtime_root: Path

    @classmethod
    def build(cls, packet, runtime_root):
        require_plain_json(packet)
        loaded_runtime_root = Path(__import__('hcl').__file__).resolve().parent.parent
        if Path(runtime_root).resolve() != loaded_runtime_root:
            raise ValueError('EXACT_LOADED_RUNTIME_ROOT_REQUIRED')
        base = _reference.OfflinePackage.build(packet, runtime_root)
        # Reuse only request/control data. No archived approval, grant, cutoff,
        # workflow, owner authority, account or future-live fields are imported.
        keys = ('packet_sha256', 'runtime_sha256', 'planning_tokens', 'answer_tokens',
            'maximum_request_bytes', 'maximum_aggregate_calls', 'maximum_aggregate_cny',
            'stage_call_caps', 'stage_cny_caps', 'stage_reservation_cny', 'phase_holds_cny',
            'rates_cny', 'reference_rates_usd', 'source_recorded_at_basis', 'source_recorded_at',
            'maximum_wait_seconds', 'stage_windows_seconds', 'sdk_retries', 'request_retries',
            'replanning', 'model_judge', 'fallback', 'case_replacement', 'maximum_final_characters',
            'maximum_final_texts', 'requests', 'reasoning_effort', 'entry_requirements',
            'declared_source_entry_blockers', 'stage_orders')
        value = {key: base.value[key] for key in keys}
        value.update(schema='hcl-offline-diagnostic-package-v1', mode=MODE,
            authorization_ref=AUTH, live_execution_authorized=False, actual_spend_cny='0',
            reference_helper_files=dict(PINS), implementation_files={name: file_sha(Path(__file__).parent / name)
            for name in ('hcl_offline_diagnostic_export_v1.py', 'hcl_offline_diagnostic_public_v1.py', 'hcl_offline_diagnostic_reference.py')})
        return cls(value, base.packet, base.runtime_root)

    @property
    def cases(self):
        return _reference.normalized_cases(self.packet)

    def verify(self):
        require_plain_json(self.value)
        if self.value != type(self).build(self.packet, self.runtime_root).value:
            raise ValueError('OFFLINE_PACKAGE_OR_RUNTIME_DRIFT')


def require_package(package):
    if type(package) is not OfflinePackage:
        raise ValueError('EXACT_OFFLINE_DIAGNOSTIC_PACKAGE_REQUIRED')


class FakeClient:
    """Bounded deterministic responses only. No injected transport or callbacks.

    Raw JSON strings permit malformed-plan/final tests; absent responses use the
    unrelated B01 control. SDK-shaped access exists only for the reused meter.
    All captured requests and envelopes remain in memory, never in receipts.
    """
    __slots__ = ('_responses', '_calls')
    offline_synthetic = True
    max_retries = 0
    timeout = WAIT

    def __init__(self, responses=()):
        if type(responses) not in (tuple, list) or len(responses) > 2 or any(type(text) is not str or len(text) > 64000 for text in responses):
            raise ValueError('BOUNDED_DETERMINISTIC_FAKE_RESPONSES_REQUIRED')
        self._responses = tuple(responses)
        self._calls = []

    @property
    def calls(self):
        return json.loads(canonical(self._calls))

    @property
    def chat(self):
        return SimpleNamespace(completions=SimpleNamespace(create=self.create))

    def create(self, **request):
        if len(self._calls) >= 2:
            raise ValueError('FAKE_CLIENT_NO_RETRY')
        expected_effort = EFFORT['planning' if not self._calls else 'answer']
        if request.get('reasoning_effort') != expected_effort:
            raise ValueError('FAKE_PHASE_ORDER_REQUIRED')
        self._calls.append(json.loads(canonical(request)))
        payload = json.loads(request['messages'][-1]['content'])
        if len(self._calls) <= len(self._responses):
            text = self._responses[len(self._calls) - 1]
        elif len(self._calls) == 1:
            text = json.dumps(dict(task='Interpret the offline control question.', operations=[dict(
                capability='B01', question='What does Mira explicitly report?',
                source_ids=[payload['sources'][0]['source_id']], bindings=[], input_mode='literal')], limitations=[]))
        else:
            text = json.dumps(dict(answer='Mira reports that the box is blue. This stated belief is not an independent inspection.',
                source_citations=[dict(source_id=s['source_id'], version=s['version'], quote=s['text'], start=0) for s in payload['sources']],
                uncertainty='The actual color is not independently established.', assumptions='No extra evidence.'))
        return dict(model=MODEL, usage=dict(prompt_tokens=100, completion_tokens=100, total_tokens=200),
            choices=[dict(finish_reason='stop', message=dict(content=text,
                reasoning_content='OFFLINE_PRIVATE_REASONING_CANARY'))], envelope_private='OFFLINE_PRIVATE_ENVELOPE_CANARY')


class BoundedPort(_reference.BoundedPort):
    provider_free = True

    def _validate_client(self):
        # Refuse before touching any client attributes, account, credential or SDK.
        if type(self.client) is not FakeClient:
            raise ValueError('EXACT_DETERMINISTIC_FAKE_CLIENT_REQUIRED')
        if self._closed:
            raise ValueError('OFFLINE_PORT_CLOSED_NO_RETRY')


class Ledger(_reference.Ledger):
    authorization_ref = AUTH

    def make_port(self, client, arm_id):
        return BoundedPort(client, self, arm_id)

    def __init__(self, directory, package, stage, clock, monotonic, *, offline=True):
        require_package(package)
        if offline is not True:
            raise ValueError('OFFLINE_ONLY_NO_LIVE_AUTHORITY')
        super().__init__(directory, package, stage, clock, monotonic, offline=True)

    def persist(self):
        self.value.update(schema=RECEIPT_SCHEMA, authorization_ref=AUTH,
                          live_execution_authorized=False, actual_spend_cny='0')
        for arm in self.value['arms']:
            arm.setdefault('orchestration_failure', None)
            arm.setdefault('capture_failure', None)
        super().persist()

    def require_final_dispatch_margin(self):
        if self.stopped:
            raise ValueError('BATCH_STOPPED_NO_RETRY')
        if self.monotonic() - self.started + WAIT >= ELAPSED[self.stage]:
            raise ValueError('FINAL_STAGE_SEND_MARGIN_INVALID')
        now = self.clock()
        if not isinstance(now, datetime) or now.tzinfo is None:
            raise ValueError('UTC_TIME_REQUIRED')

    def admit(self):
        self.validate_ledger()
        self.require_final_dispatch_margin()
        self.package.verify()


def run_offline(client, package, stage, directory, *, clock=lambda: datetime.now(timezone.utc), monotonic=time.monotonic):
    """Only fake transport; type checks occur before verification or output creation."""
    if type(client) is not FakeClient:
        raise ValueError('EXACT_DETERMINISTIC_FAKE_CLIENT_REQUIRED')
    require_package(package)
    package.verify(); order(package.cases, stage)
    return _run(client, package, stage, directory, clock=clock, monotonic=monotonic)


def _run(client, package, stage, directory, *, clock, monotonic):
    ledger = Ledger(directory, package, stage, clock, monotonic, offline=True)
    return _run_with_ledger(ledger, client)


def _run_with_ledger(ledger, client):
    """Shared one-pass mechanics, reached only through a fixed admitting wrapper.

    The wrapper owns package/client admission and constructs its trusted ledger;
    this helper creates no authority, configuration, client or transport policy.
    """
    package = ledger.package
    monotonic = ledger.monotonic
    cases = {c['case_id']: c for c in package.cases}
    try:
        for record in ledger.value['arms']:
            if ledger.stopped:
                continue
            case_id, arm = record['case_id'], record['arm']; case = cases[case_id]; arm_id = case_id + ':' + arm
            ledger.active = arm_id; start = monotonic(); port = None; runtime_returned = False
            try:
                ledger.admit(); port = ledger.make_port(client, arm_id)
                if arm == 'Base':
                    prompt = messages(case, arm); port.reservation_usd('answer', prompt)
                    raw = port.complete('answer', prompt)['text']; good = accepted(prompt, raw)
                    record.update(status='ANSWER_ACCEPTED' if good else 'FINAL_SCHEMA_OR_CITATIONS_REJECTED', final_delivery_code='DELIVERED' if good else 'SCHEMA_INVALID', citations_accepted=good)
                else:
                    session = UniversalHCL()
                    for source in case['sources']:
                        session.put_source(source['source_id'], source['text']); session.sources[source['source_id']] = dict(source)
                    allowance = CallAllowance(2, HOLD_USD['planning'] + HOLD_USD['answer'], ledger.authorization_ref, journal=port.journal)
                    result = session.answer(case['question'], planner_backend=port, answer_backend=port, allowance=allowance, required_checked_capabilities=tuple(x['capability_id'] for x in next(c for c in package.packet['cases'] if c['case_id']==case_id)['private_evaluation']['predeclared_acceptable_relevant_native_operation_families']))
                    # Persist the helper's exact bounded result before capture/replay can fail.
                    # Null means no failed runtime receipt, never proof of treatment.
                    record['orchestration_failure'] = clean_diagnostic(safe_orchestration_failure_details(result))
                    ledger.persist()
                    runtime_returned = True
                    allowance.closed = True
                    record.update(native_results=result['hcl_execution']['native_results'], final_delivery_code=result.get('final_delivery_code', 'NOT_REACHED'), selected_capabilities=[o['capability'] for o in result.get('plan', {}).get('operations', [])], executed_capabilities=[o['capability'] for o in result['operations'] if o.get('executed')], checked_treatment=[o['capability'] for o in result['operations'] if o.get('checked_treatment_present')], runtime_final_context_metrics=result.get('final_context_metrics'))
                    ledger.persist()
                    ledger.native_review(case, result)
                    # Only metrics from the actual final messages enter the ledger.
                    # A runtime character-guard refusal has no constructed provider
                    # request; retain size-only diagnostics and an explicit reason.
                    if 'actual_final_messages' in result:
                        _, _, metric = request_and_metrics('answer', result['actual_final_messages'])
                        ledger.observe_request(arm_id, 'answer', metric)
                    raw = port.responses.get('answer', port.final_raw)
                    good = bool(raw is not None and accepted(port.prompts.get('answer'), raw))
                    record['citations_accepted'] = good
                    failure = (record['orchestration_failure'] or {}).get('code'); invalid_plan = invalid_final = False
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
                if runtime_returned: record['capture_failure'] = 'POST_RUNTIME_CAPTURE_FAILED'
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
