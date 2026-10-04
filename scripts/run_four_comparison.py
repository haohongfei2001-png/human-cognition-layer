"""One frozen four-case development comparison. No retries, repairs or budget reuse."""
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
from types import SimpleNamespace

from hcl.cognition import UniversalHCL, CallAllowance
from hcl.cognition.capability_catalog import CATALOG
from hcl.cognition.deepseek_metered import INPUT_RATE, OUTPUT_RATE, OUTPUT_MARGIN, MODEL
from hcl.cognition.reader_entry import _FINAL_ANSWER_POLICY
from hcl.cognition.retained import audit_supplied_source_citations
from hcl.cognition.universal_entry import PLANNER_POLICY
from scripts.output_limit_port import OutputLimitPort
from scripts.serious_eval_contract import runtime_digest
from scripts.universal_launch_guard import verify_run_history

ROOT = Path('.github/frozen/hcl-four-comparison')
PACKAGE = Path('reports/HCL_FOUR_COMPARISON_PACKAGE.json')
GRANT = Path('.github/HCL_FOUR_COMPARISON_GRANT.json')
MARKER = Path('.github/HCL_FOUR_COMPARISON_TRIGGER.json')
TEMPLATE = Path('.github/frozen/hcl-four-comparison-once.yml')
WORKFLOW = Path('.github/workflows/hcl-four-comparison-once.yml')
SECRET_CHECK = Path('/tmp/four-comparison-secret-presence.json')
AUTH = 'OWNER_APPROVED_FOUR_COMPARISON_PUBLIC_SYNTHETIC_20261004_121358'
APPROVED = '2026-10-04T12:13:58Z'
EXPIRES = '2026-10-05T12:13:58Z'
SCOPE = 'FOUR_EXACT_SYNTHETIC_CASES_EIGHT_UNCHANGED_FINAL_OUTPUTS_SAME_HCL_REPOSITORY'
CAP = Decimal('1.28')
MAX_CALLS = 12
WAIT = 180
ELAPSED = 2700
MAX_ANSWER = Decimal('0.13031040')
MAX_SCHEDULE = Decimal('1.27791840')
RUNTIME = '90737b3ed772f65851553d8a673112eae50f2781185d8b5b4ccd127cdfb8663b'
FROZEN_SHA = {
    'inputs.json': '9f8a1a87c1d3e9d8ac96991920871192d3e1c5adab7ee51dfd3cdc90e503d942',
    'rubric.json': '4ec8e11ce3af7603aabcf744e64014145a36ddb760eb9840f9fb4cd82bf91629',
    'proposal.json': '612231909be22435224293525d8fdb8b2160b081618f1f0fd6f2974a25ee1079',
    'README.md': '335b9f1d5285ab1e50324d5454481df80acc2dfdcfb8b1840bc7964e7a05b9cc',
}
ORDER = [('D01', 'Base'), ('D01', 'HCL'), ('D02', 'HCL'), ('D02', 'Base'),
         ('D03', 'Base'), ('D03', 'HCL'), ('D04', 'HCL'), ('D04', 'Base')]
KNOWN_RETURN_FAILURES = {'INCOMPLETE_ANSWER_NO_RETRY', 'CONTENT_BOUND_EXCEEDED'}
KNOWN_HCL_FAILURES = {
    'invalid answer schema', 'NONBLANK_FINAL_ANSWER_REQUIRED', 'invalid bounded task plan',
    'invalid limitations', 'bounded bindings required', 'bounded interpreted question required',
    'unknown capability or operation fields', 'unknown or duplicate source selection',
    'unsupported binding or source', 'invented or stale source anchor', 'operation bound exceeded',
    'NATIVE_HCL_RESULT_REQUIRED_BEFORE_ANSWER', 'planning response exceeds bound',
    'complete context exceeds budget; no truncation', 'answer exceeds bounded contract',
    'duplicate responsibility actor',
}


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def file_sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def utcnow(): return datetime.now(timezone.utc)


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    with tmp.open('w') as stream:
        json.dump(value, stream, ensure_ascii=False, sort_keys=True, indent=2)
        stream.write('\n'); stream.flush(); os.fsync(stream.fileno())
    os.replace(tmp, path)


def load_frozen():
    if any(file_sha(ROOT / name) != sha for name, sha in FROZEN_SHA.items()):
        raise ValueError('FROZEN_PROPOSAL_DRIFT')
    return json.loads((ROOT / 'inputs.json').read_text()), json.loads((ROOT / 'proposal.json').read_text())


def messages(case, arm):
    if arm == 'Base':
        payload = dict(question=case['question'], sources=[{k: s[k] for k in ('source_id', 'version', 'text')} for s in case['sources']],
                       knowledge_basis='SUPPLIED_SOURCES_AND_EXPLICIT_INTERPRETATION')
        policy = _FINAL_ANSWER_POLICY + ' The answer field must contain a nonblank answer; state an evidence limitation explicitly rather than leaving it empty.'
    else:
        payload = dict(question=case['question'], sources=case['sources'], capability_inventory=[asdict(c) for c in CATALOG.values()])
        policy = PLANNER_POLICY
    return [dict(role='system', content=policy), dict(role='user', content=json.dumps(payload, ensure_ascii=False, sort_keys=True))]


def validator():
    return OutputLimitPort(SimpleNamespace(base_url='https://api.deepseek.com', max_retries=0, timeout=WAIT), planning_tokens=16384)


def build_package():
    inputs, proposal = load_frozen()
    if runtime_digest() != RUNTIME: raise ValueError('RUNTIME_DRIFT')
    for name, sha in proposal['freeze']['runtime_and_metering_files_sha256'].items():
        if file_sha(name) != sha: raise ValueError('FROZEN_METERING_DRIFT')
    prior = Path('.github/HCL_CURRENT_FLOW_GRANT.json')
    closed = json.loads(prior.read_text())
    if closed['status'] != 'CLOSED_NO_TRANSFER_NO_RETRY' or closed['remaining_authorized_calls'] != 0 or Decimal(closed['remaining_authorized_usd']) != 0:
        raise ValueError('PREVIOUS_GRANT_MUST_STAY_CLOSED')
    requests = {}
    for case, expected in zip(inputs['cases'], proposal['budget']['requests'], strict=True):
        if case['case_id'] != expected['case_id']: raise ValueError('CASE_ORDER_DRIFT')
        for arm, phase, label in [('Base', 'answer', 'base'), ('HCL', 'planning', 'planning')]:
            port = validator(); prompt = messages(case, arm); request, encoded = port.request(phase, prompt)
            actual = dict(request_sha256=digest(request), messages_sha256=digest(prompt), request_bytes=len(encoded),
                          reservation_usd=port.reservation_usd(phase, prompt), max_tokens=request['max_tokens'], input_token_bound=2*len(encoded)+2048)
            if actual != expected[label]: raise ValueError('FROZEN_REQUEST_DRIFT')
            requests[case['case_id'] + ':' + arm + ':' + phase] = actual
    maximum = sum(Decimal(r['reservation_usd']) for r in requests.values()) + 4 * MAX_ANSWER
    if maximum != MAX_SCHEDULE or maximum > CAP: raise ValueError('SCHEDULE_CAP_DRIFT')
    files = [str(ROOT / n) for n in (*FROZEN_SHA, 'SHA256SUMS')]
    files += ['scripts/run_four_comparison.py', 'scripts/four_comparison_public.py', 'tests/test_four_comparison.py',
              str(TEMPLATE), '.github/workflows/hcl-four-comparison-provider-free.yml',
              'scripts/output_limit_port.py', 'scripts/output_limit_protocol.py', 'scripts/bounded_diagnostic_port.py',
              'scripts/bounded_diagnostic_protocol.py', 'scripts/serious_eval_contract.py', 'scripts/universal_launch_guard.py']
    return dict(schema='hcl-four-comparison-package-v1', authorization_ref=AUTH, public_output_scope=SCOPE,
                runtime_sha256=RUNTIME, baseline_commit=proposal['freeze']['main_commit'], maximum_calls=MAX_CALLS,
                maximum_usd=str(CAP), maximum_schedule_reservation_usd=str(MAX_SCHEDULE), maximum_hcl_answer_reservation_usd=str(MAX_ANSWER),
                maximum_wait_seconds=WAIT, maximum_elapsed_seconds=ELAPSED, maximum_request_bytes=36000,
                model=MODEL, planning_tokens=16384, answer_tokens=8192, production_planning_tokens=4096,
                order=[list(x) for x in ORDER], requests=requests, frozen_files_sha256=FROZEN_SHA,
                prior_closed_grant_sha256=file_sha(prior), retries=0, repairs=0, paid_judges=0, historical_budget_transfer=False,
                execution_files={p: file_sha(p) for p in files})


def expected_grant(package, ready=False):
    return dict(schema='hcl-four-comparison-grant-v1', status='READY' if ready else 'PREPARED_NOT_AUTHORIZED',
                authorization_ref=AUTH if ready else None, approved_at=APPROVED if ready else None,
                expires_at=EXPIRES if ready else None, package_sha256=digest(package),
                authorized_calls=MAX_CALLS if ready else 0, authorized_usd=str(CAP) if ready else '0',
                public_output_scope=SCOPE if ready else None, retries=0, historical_budget_transfer=False)


def require_time(now):
    start = datetime.fromisoformat(APPROVED.replace('Z', '+00:00'))
    end = datetime.fromisoformat(EXPIRES.replace('Z', '+00:00'))
    if not isinstance(now, datetime) or now.tzinfo is None or now < start or now + timedelta(seconds=WAIT) >= end:
        raise ValueError('AUTHORIZATION_TIME_OR_SEND_MARGIN_INVALID')


def require_grant(package, grant, now):
    if package != build_package(): raise ValueError('PACKAGE_DRIFT')
    if grant != expected_grant(package, True): raise ValueError('EXACT_NEW_OWNER_GRANT_REQUIRED')
    require_time(now)


def final_fields(raw):
    if not isinstance(raw, str) or len(raw) > 64000: return None
    try: value = json.loads(raw)
    except (ValueError, TypeError): return None
    if not isinstance(value, dict) or set(value) != {'answer', 'source_citations', 'uncertainty', 'assumptions'}: return None
    if any(not isinstance(value[k], str) for k in ('answer', 'uncertainty', 'assumptions')) or not isinstance(value['source_citations'], list): return None
    for c in value['source_citations']:
        if (not isinstance(c, dict) or not {'source_id', 'version', 'quote'} <= set(c) or not set(c) <= {'source_id', 'version', 'quote', 'start', 'end'}
            or not isinstance(c['source_id'], str) or not isinstance(c['quote'], str) or type(c['version']) is not int
            or any(type(c[k]) is not int for k in ('start', 'end') if k in c)): return None
    return value


def accepted(prompt, raw):
    value = final_fields(raw)
    return bool(value is not None and value['answer'].strip() and value['source_citations']
                and audit_supplied_source_citations(prompt, raw)['deliverable'])


class Ledger:
    def __init__(self, directory, package, grant, clock, monotonic):
        self.directory = Path(directory); self.directory.mkdir(mode=0o700, parents=True, exist_ok=False)
        self.path = self.directory / 'receipt.json'; self.clock = clock; self.monotonic = monotonic
        self.started = monotonic(); self.package = package; self.grant = grant; self.active = None; self.stopped = False
        self.value = dict(schema='hcl-four-comparison-private-receipt-v1', package_sha256=digest(package), authorization_ref=AUTH,
                          status='RUNNING', calls=[], arms=[], reserved_usd='0', started_at=clock().isoformat())
        self.persist()

    def persist(self):
        try: save(self.path, self.value)
        except Exception:
            self.stopped = True
            raise

    def admit(self):
        if self.stopped: raise ValueError('BATCH_STOPPED_NO_RETRY')
        require_time(self.clock())
        if self.monotonic() - self.started + WAIT >= ELAPSED: raise ValueError('BATCH_DEADLINE_SEND_MARGIN')
        if runtime_digest() != RUNTIME: raise ValueError('RUNTIME_DRIFT')
        load_frozen()

    def reserve(self, stage, phase, request, exact_reserve, request_bytes):
        try:
            self.admit()
            if stage != self.active or phase not in ('planning', 'answer'): raise ValueError('ARM_IDENTITY_DRIFT')
            case, arm = stage.split(':'); call_id = stage + ':' + phase
            if any(r['call_id'] == call_id for r in self.value['calls']): raise ValueError('DUPLICATE_CALL_NO_RETRY')
            expected = self.package['requests'].get(call_id)
            if expected:
                if digest(request) != expected['request_sha256'] or str(exact_reserve) != expected['reservation_usd']:
                    raise ValueError('FROZEN_REQUEST_DRIFT')
                reserve = exact_reserve
            elif arm == 'HCL' and phase == 'answer':
                previous = [r for r in self.value['calls'] if r['call_id'] == stage + ':planning']
                if len(previous) != 1 or previous[0]['status'] != 'RETURNED': raise ValueError('PLANNING_MUST_RETURN')
                if exact_reserve > MAX_ANSWER: raise ValueError('PHASE_CAP_EXCEEDED')
                frozen_case = next(c for c in load_frozen()[0]['cases'] if c['case_id'] == case)
                payload = json.loads(request['messages'][-1]['content'])
                expected_sources = [{k: s[k] for k in ('source_id', 'version', 'text')} for s in frozen_case['sources']]
                if payload.get('question') != frozen_case['question'] or payload.get('sources') != expected_sources:
                    raise ValueError('DYNAMIC_ANSWER_SOURCE_IDENTITY_DRIFT')
                reserve = MAX_ANSWER
            else: raise ValueError('UNDECLARED_PHASE')
            held = Decimal(self.value['reserved_usd'])
            expected_case = next(c for c in load_frozen()[1]['budget']['requests'] if c['case_id'] == case)
            held_case = sum(Decimal(c['reserved_usd']) for c in self.value['calls'] if c['case_id'] == case)
            if held_case + reserve > Decimal(expected_case['maximum_case_reservation_usd']):
                raise ValueError('CASE_CAP_EXCEEDED')
            if len(self.value['calls']) >= MAX_CALLS or held + reserve > CAP or held + reserve > MAX_SCHEDULE:
                raise ValueError('AGGREGATE_CAP_EXCEEDED')
            self.value['calls'].append(dict(call_id=call_id, case_id=case, arm=arm, phase=phase,
                request_sha256=digest(request), request_bytes=request_bytes, reserved_usd=str(reserve), exact_request_reservation_usd=str(exact_reserve),
                status='RESERVED_BEFORE_CALL', invocation_status='NOT_INVOKED', provider_call=False))
            self.value['reserved_usd'] = str(held + reserve); self.persist()
            return reserve
        except Exception:
            self.stopped = True
            raise

    def close(self):
        self.value.update(status='STOPPED_NO_RETRY' if self.stopped else 'COMPLETED_ONE_PASS',
                          finished_at=self.clock().isoformat(), elapsed_seconds=self.monotonic()-self.started,
                          budget_state='CLOSED_NO_TRANSFER_NO_RETRY', remaining_authorized_calls=0, remaining_authorized_usd='0')
        self.stopped = True; self.persist()


class Port:
    provider_free = False
    cost_basis = 'USAGE_RATED_PEAK_NOT_INVOICE'
    def __init__(self, client, ledger, stage):
        self.inner = OutputLimitPort(client, planning_tokens=16384); self.ledger = ledger; self.stage = stage
        self.rows = {}; self.prompts = {}; self.responses = {}; self.known_failure = None

    def reservation_usd(self, phase, prompt):
        try:
            exact = Decimal(self.inner.reservation_usd(phase, prompt)); request, encoded = self.inner.request(phase, prompt)
        except Exception as error:
            if str(error) == 'REQUEST_BOUND_EXCEEDED_NO_TRUNCATION' and phase == 'answer' and self.stage.endswith(':HCL'):
                self.known_failure = 'REQUEST_BOUND_EXCEEDED_NO_TRUNCATION'
            else: self.ledger.stopped = True
            raise
        reserve = self.ledger.reserve(self.stage, phase, request, exact, len(encoded))
        self.rows[phase] = self.ledger.value['calls'][-1]; self.prompts[phase] = prompt
        return str(reserve)

    def journal(self, snapshot):
        for attempt in snapshot['attempts']:
            row = self.rows.get(attempt['phase'])
            if row is None or Decimal(row['reserved_usd']) != Decimal(attempt['reserved_usd']):
                self.ledger.stopped = True
                raise ValueError('DURABLE_RESERVATION_IDENTITY_REQUIRED')
        self.ledger.persist()

    def complete(self, phase, prompt):
        row = self.rows[phase]
        try:
            self.ledger.admit()
            request, _ = self.inner.request(phase, prompt)
            if row['invocation_status'] != 'NOT_INVOKED' or digest(request) != row['request_sha256']:
                raise ValueError('RESERVED_REQUEST_DRIFT')
            row.update(provider_call=True, invocation_status='INVOKED_OR_SEND_UNKNOWN'); self.ledger.persist()
        except Exception:
            self.ledger.stopped = True
            raise
        start = self.ledger.monotonic()
        try:
            result = self.inner.complete(phase, prompt)
            self.responses[phase] = result['text']
            row.update(status='RETURNED', invocation_status='RETURNED')
            return result
        except Exception as error:
            code = str(error)
            known = code in KNOWN_RETURN_FAILURES and self.inner.diagnostics.get('usage_valid') is True
            row.update(status='RETURNED_REJECTED' if known else 'FAILED_OR_UNKNOWN',
                       invocation_status='RESPONSE_RETURNED_REJECTED' if known else 'INVOKED_OR_SEND_UNKNOWN',
                       failure_code=code if known else 'UNKNOWN_SEND_USAGE_COST_OR_IDENTITY_STOP')
            self.known_failure = code if known else None
            if not known: self.ledger.stopped = True
            raise
        finally:
            row['sdk_seconds'] = self.ledger.monotonic() - start
            data = self.inner.diagnostics
            if data.get('usage_valid') is True:
                counts = data['usage']; rated = (counts['prompt_tokens']*INPUT_RATE + counts['completion_tokens']*OUTPUT_RATE)/1000000
                if rated > Decimal(row['reserved_usd']): self.ledger.stopped = True
                else: row.update(usage=counts, usage_rated_usd=str(rated))
            self.ledger.persist()


def run(client, package, grant, directory, *, clock=utcnow, monotonic=time.monotonic):
    require_grant(package, grant, clock())
    inputs, _ = load_frozen(); cases = {c['case_id']: c for c in inputs['cases']}
    ledger = Ledger(directory, package, grant, clock, monotonic)
    try:
        for case_id, arm in ORDER:
            case = cases[case_id]; stage = case_id + ':' + arm
            record = dict(case_id=case_id, arm=arm, status='NOT_ATTEMPTED', final_fields=None, final_answer_sha256=None,
                          citations_accepted=False, selected_capabilities=[], executed_capabilities=[], checked_treatment=[])
            ledger.value['arms'].append(record)
            if ledger.stopped: continue
            start = monotonic(); ledger.active = stage; port = None
            try:
                ledger.admit(); port = Port(client, ledger, stage)
                if arm == 'Base':
                    prompt = messages(case, arm); port.reservation_usd('answer', prompt)
                    raw = port.complete('answer', prompt)['text']; good = accepted(prompt, raw)
                    record['status'] = 'ANSWER_ACCEPTED' if good else 'FINAL_SCHEMA_OR_CITATIONS_REJECTED'
                else:
                    session = UniversalHCL()
                    for source in case['sources']:
                        session.put_source(source['source_id'], source['text']); session.sources[source['source_id']] = dict(source)
                    allowance = CallAllowance(2, CAP, AUTH, journal=port.journal)
                    result = session.answer(case['question'], planner_backend=port, answer_backend=port, allowance=allowance)
                    allowance.closed = True
                    record.update(selected_capabilities=[o['capability'] for o in result.get('plan', {}).get('operations', [])],
                                  executed_capabilities=[o['capability'] for o in result['operations'] if o.get('executed')],
                                  checked_treatment=[o['capability'] for o in result['operations'] if o.get('checked_treatment_present')])
                    raw = port.responses.get('answer'); prompt = port.prompts.get('answer'); good = bool(raw is not None and accepted(prompt, raw))
                    failure = result.get('failure_reason')
                    invalid_plan = False
                    invalid_final = False
                    if failure == 'ORCHESTRATION_FAILURE' and raw is not None:
                        try: json.loads(raw)
                        except (ValueError, TypeError): invalid_final = True
                    if failure == 'ORCHESTRATION_FAILURE' and 'planning' in port.responses:
                        try: session._validate_plan(port.responses['planning'])
                        except (ValueError, TypeError, KeyError): invalid_plan = True
                    if (failure and failure not in KNOWN_HCL_FAILURES and not port.known_failure and not invalid_plan and not invalid_final):
                        ledger.stopped = True
                    if ledger.stopped: record['status'] = 'UNKNOWN_FAILURE_STOP'
                    elif result['status'] == 'ANSWERED_WITH_EXPLICIT_LIMITS' and good: record['status'] = 'ANSWER_ACCEPTED'
                    elif result['status'] == 'ANSWER_SOURCE_REVIEW_FAILED' or raw is not None: record['status'] = 'FINAL_SCHEMA_OR_CITATIONS_REJECTED'
                    elif port.known_failure: record['status'] = port.known_failure
                    elif failure in KNOWN_HCL_FAILURES or invalid_plan: record['status'] = 'BOUNDED_HCL_SCHEMA_SELECTION_OR_ADAPTER_FAILURE'
                    else: ledger.stopped = True; record['status'] = 'UNKNOWN_FAILURE_STOP'
                if raw is not None:
                    record.update(final_fields=final_fields(raw), final_answer_sha256=hashlib.sha256(raw.encode()).hexdigest(), citations_accepted=good)
            except Exception:
                if port and port.known_failure and not ledger.stopped: record['status'] = port.known_failure
                else: ledger.stopped = True; record['status'] = 'UNKNOWN_FAILURE_STOP'
            finally:
                record['arm_seconds'] = monotonic() - start
                record['sdk_seconds'] = sum(r.get('sdk_seconds', 0) for r in ledger.value['calls'] if r['call_id'].startswith(stage + ':'))
                record['non_sdk_seconds'] = max(0, record['arm_seconds'] - record['sdk_seconds'])
                ledger.persist()
    finally: ledger.close()
    return ledger.value


def verify_launch(run_id, attempt, runs, event, parent, paths, marker, package, grant, now):
    require_grant(package, grant, now); verify_run_history(run_id, attempt, runs)
    expected = dict(schema='hcl-four-comparison-marker-v1', authorization_ref=AUTH, package_sha256=digest(package), grant_sha256=digest(grant), executor_commit=parent)
    if (event != 'push' or not isinstance(parent, str) or len(parent) != 40 or any(c not in '0123456789abcdef' for c in parent)
        or paths != [str(MARKER)] or marker != expected): raise ValueError('ONE_MARKER_ONLY_LAUNCH_REQUIRED')


def main():
    import argparse
    p = argparse.ArgumentParser(); p.add_argument('--freeze', action='store_true'); p.add_argument('--check-launch'); p.add_argument('--execute', action='store_true')
    args = p.parse_args(); os.umask(0o077)
    if sum((args.freeze, bool(args.check_launch), args.execute)) != 1: raise ValueError('ONE_MODE_REQUIRED')
    if args.freeze:
        package = build_package(); save(PACKAGE, package); save(GRANT, expected_grant(package)); return
    if os.environ.get('GITHUB_REF') != 'refs/heads/main' or os.environ.get('GITHUB_RUN_ATTEMPT') != '1': raise ValueError('MAIN_ATTEMPT_ONE_REQUIRED')
    if WORKFLOW.read_bytes() != TEMPLATE.read_bytes(): raise ValueError('FROZEN_WORKFLOW_REQUIRED')
    package = json.loads(PACKAGE.read_text()); grant = json.loads(GRANT.read_text()); require_grant(package, grant, utcnow())
    identity = dict(run_id=os.environ['GITHUB_RUN_ID'], head_sha=os.environ['GITHUB_SHA'])
    if json.loads(SECRET_CHECK.read_text()) != dict(identity, existing_provider_secret='PRESENT'): raise ValueError('SAME_RUN_SECRET_CHECK_REQUIRED')
    expected = dict(identity, package_sha256=digest(package), grant_sha256=digest(grant)); admission = Path('/tmp/four-comparison-admission.json')
    if args.check_launch:
        history = [r for page in json.loads(Path(args.check_launch).read_text()) for r in page['workflow_runs']]
        ancestry = subprocess.check_output(['git', 'rev-list', '--parents', '-n', '1', 'HEAD'], text=True).split()
        if len(ancestry) != 2: raise ValueError('SINGLE_PARENT_REQUIRED')
        paths = subprocess.check_output(['git', 'diff-tree', '--no-commit-id', '--name-only', '-r', 'HEAD'], text=True).splitlines()
        verify_launch(identity['run_id'], '1', history, os.environ.get('GITHUB_EVENT_NAME'), ancestry[1], paths,
                      json.loads(MARKER.read_text()), package, grant, utcnow())
        save(admission, expected); print('FOUR_COMPARISON_ONE_LAUNCH_ADMITTED')
    else:
        if json.loads(admission.read_text()) != expected: raise ValueError('EXACT_RUN_ADMISSION_REQUIRED')
        import logging
        logging.disable(logging.CRITICAL); os.environ.pop('OPENAI_LOG', None)
        from openai import OpenAI
        key = os.environ.get('DEEPSEEK_API_KEY')
        if not key: raise ValueError('EXISTING_SECRET_UNAVAILABLE')
        run(OpenAI(api_key=key, base_url='https://api.deepseek.com', max_retries=0, timeout=WAIT), package, grant, 'four-comparison-private')
        print('FOUR_COMPARISON_TERMINATED_NO_RETRY')

if __name__ == '__main__': main()
