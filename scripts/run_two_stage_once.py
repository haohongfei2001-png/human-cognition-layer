"""Owner-approved bounded two-stage study; no credentials or live defaults in imports."""
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
from hcl.cognition.deepseek_metered import INPUT_RATE, OUTPUT_RATE, MODEL
from hcl.cognition.reader_entry import _EXPLICIT_CITATION_FINAL_ANSWER_POLICY
from hcl.cognition.retained import audit_supplied_source_citations
from hcl.cognition.universal_entry import PLANNER_POLICY
from scripts.output_limit_port import OutputLimitPort
from scripts.serious_eval_contract import runtime_digest
from scripts.universal_launch_guard import verify_run_history

ROOT = Path('.github/frozen/hcl-two-stage-20261006')
AUTH = 'OWNER_APPROVED_TWO_STAGE_CNY_REPLACEMENT_20261006_14_CALLS_14_CNY'
APPROVED = '2026-10-06T18:21:19Z'  # Conservative received-at bound for the CNY replacement.
FIXTURE_RECORDED_AT = '2026-10-06T17:32:48Z'
EXPIRES = '2026-10-07T17:32:48Z'
RUNTIME = '62bea96c481fcdde3bfb0af8707796d5afaebf1c9d051ace9bd0c82e236f2442'
MAX_PLANNING = Decimal('0.16275072')
MAX_ANSWER = Decimal('0.13031040')
# The unchanged runtime adapter uses correctly denominated USD estimates only
# as interface bookkeeping. The independent CNY ledger below is the authority.
CNY_INPUT_RATE = Decimal('9.0')
CNY_OUTPUT_RATE = Decimal('27.0')
MAX_PLANNING_CNY = Decimal('1.109664')
MAX_ANSWER_CNY = Decimal('0.888480')
TOTAL_CAP_CNY = Decimal('14')
WAIT = 180
FROZEN_SHA = {'cases.json': '3c794a715d4fa2d5ec97bba58f441feeef1d446dbb67a826d485f0dc031eb48b', 'proposal.json': 'c64d7d372b686829584d0051add1a9d303a013e68aacccc73bdf9954b8c5713e', 'cny-amendment.json': 'e965bf7b22b25673d37a75a437c4abe47ff955ff1eb7b152e02c667f346e4d5c'}
PHASE1_EVIDENCE = Path('reports/HCL_TWO_STAGE_CNY_1_PUBLIC_EVIDENCE.json')
PHASE1_REVIEW = Path('reports/HCL_TWO_STAGE_CNY_1_SOURCE_REVIEW.json')
KNOWN_RETURN_FAILURES = {'INCOMPLETE_ANSWER_NO_RETRY', 'CONTENT_BOUND_EXCEEDED'}
KNOWN_HCL_FAILURES = {'invalid answer schema', 'NONBLANK_FINAL_ANSWER_REQUIRED', 'invalid bounded task plan',
 'invalid limitations','bounded bindings required','bounded interpreted question required','unknown capability or operation fields',
 'unknown or duplicate source selection','unsupported binding or source','invented or stale source anchor','operation bound exceeded',
 'NATIVE_HCL_RESULT_REQUIRED_BEFORE_ANSWER','planning response exceeds bound','complete context exceeds budget; no truncation',
 'answer exceeds bounded contract','duplicate responsibility actor'}
STAGE = None


def configure(stage):
    global STAGE, ORDER, CAP, CAP_CNY, MAX_CALLS, MAX_SCHEDULE, MAX_SCHEDULE_CNY, ELAPSED, PACKAGE, GRANT, MARKER, TEMPLATE, WORKFLOW, SECRET_CHECK
    if type(stage) is not int or stage not in (1, 2): raise ValueError('EXACT_STAGE_REQUIRED')
    STAGE = stage
    ORDER = [('SMOKE1','HCL')] if stage == 1 else [('PAIR1','Base'),('PAIR1','HCL'),('PAIR2','HCL'),('PAIR2','Base'),('PAIR3','Base'),('PAIR3','HCL'),('PAIR4','HCL'),('PAIR4','Base')]
    # Correct USD reference ceilings retained only for the unchanged runtime interface.
    CAP = Decimal('0.30' if stage == 1 else '1.70'); MAX_CALLS = 2 if stage == 1 else 12
    MAX_SCHEDULE = MAX_PLANNING + MAX_ANSWER if stage == 1 else 4*MAX_PLANNING + 8*MAX_ANSWER
    CAP_CNY = Decimal('2' if stage == 1 else '12')
    MAX_SCHEDULE_CNY = MAX_PLANNING_CNY + MAX_ANSWER_CNY if stage == 1 else 4*MAX_PLANNING_CNY + 8*MAX_ANSWER_CNY
    ELAPSED = 600 if stage == 1 else 2700
    PACKAGE = Path(f'reports/HCL_TWO_STAGE_CNY_{stage}_PACKAGE.json')
    GRANT = Path(f'.github/HCL_TWO_STAGE_CNY_{stage}_GRANT.json')
    MARKER = Path(f'.github/HCL_TWO_STAGE_CNY_{stage}_TRIGGER.json')
    TEMPLATE = ROOT / f'stage{stage}-cny-once.yml'
    WORKFLOW = Path(f'.github/workflows/hcl-two-stage-cny-{stage}-once.yml')
    SECRET_CHECK = Path(f'/tmp/hcl-two-stage-cny-{stage}-secret-presence.json')


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()

def cny_quote(request_bytes,max_tokens):
    return ((2*request_bytes+2048)*CNY_INPUT_RATE+(max_tokens+32)*CNY_OUTPUT_RATE)/1000000

def file_sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def utcnow(): return datetime.now(timezone.utc)

def save(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    with tmp.open('w') as stream:
        json.dump(value, stream, ensure_ascii=False, sort_keys=True, indent=2)
        stream.write('\n'); stream.flush(); os.fsync(stream.fileno())
    os.replace(tmp, path)


def load_frozen():
    if STAGE not in (1,2): raise ValueError('EXACT_STAGE_REQUIRED')
    if any(file_sha(ROOT/name) != sha for name, sha in FROZEN_SHA.items()): raise ValueError('FROZEN_PROPOSAL_DRIFT')
    rows = json.loads((ROOT/'cases.json').read_text())
    cases = [dict(case_id=c['id'], question=c['question'], sources=[dict(source_id=c['source_id'], version=c['version'], text=c['source'], recorded_at=FIXTURE_RECORDED_AT)]) for c in rows if c['stage']==STAGE]
    return dict(cases=cases), json.loads((ROOT/'proposal.json').read_text())


def messages(case, arm):
    if arm == 'Base':
        payload = dict(question=case['question'], sources=[{k:s[k] for k in ('source_id','version','text')} for s in case['sources']], knowledge_basis='SUPPLIED_SOURCES_AND_EXPLICIT_INTERPRETATION')
        policy = _EXPLICIT_CITATION_FINAL_ANSWER_POLICY + ' The answer field must contain a nonblank answer; state an evidence limitation explicitly rather than leaving it empty.'
    else:
        payload = dict(question=case['question'], sources=case['sources'], capability_inventory=[asdict(c) for c in CATALOG.values()])
        policy = PLANNER_POLICY
    return [dict(role='system',content=policy), dict(role='user',content=json.dumps(payload,ensure_ascii=False,sort_keys=True))]


def validator(): return OutputLimitPort(SimpleNamespace(base_url='https://api.deepseek.com',max_retries=0,timeout=WAIT),planning_tokens=16384)


def build_package():
    inputs, _ = load_frozen()
    if runtime_digest() != RUNTIME: raise ValueError('RUNTIME_DRIFT')
    requests = {}
    for case in inputs['cases']:
        phases = [('HCL','planning')] if STAGE==1 else [('Base','answer'),('HCL','planning')]
        for arm, phase in phases:
            port=validator(); prompt=messages(case,arm); request,encoded=port.request(phase,prompt)
            requests[case['case_id']+':'+arm+':'+phase] = dict(request_sha256=digest(request),messages_sha256=digest(prompt),request_bytes=len(encoded),reservation_usd=port.reservation_usd(phase,prompt),reservation_cny=str(cny_quote(len(encoded),request['max_tokens'])),max_tokens=request['max_tokens'],input_token_bound=2*len(encoded)+2048)
    files = ['scripts/run_two_stage_once.py','scripts/two_stage_public.py','scripts/two_stage_price.py','scripts/two_stage_account.py','tests/test_two_stage.py','tests/test_two_stage_review.py','tests/test_two_stage_account.py','scripts/output_limit_port.py','scripts/bounded_diagnostic_port.py','scripts/bounded_diagnostic_protocol.py','scripts/output_limit_protocol.py','scripts/universal_launch_guard.py','scripts/serious_eval_contract.py',str(TEMPLATE),str(WORKFLOW)] + [str(ROOT/n)for n in FROZEN_SHA]
    if STAGE==2:files.append('reports/HCL_TWO_STAGE_CNY_1_PACKAGE.json')
    return dict(schema='hcl-two-stage-cny-package-v1',currency='CNY',stage=STAGE,authorization_ref=AUTH,runtime_sha256=RUNTIME,
       frozen_files_sha256=FROZEN_SHA,requests=requests,order=[list(x)for x in ORDER],maximum_calls=MAX_CALLS,maximum_cny=str(CAP_CNY),maximum_schedule_reservation_cny=str(MAX_SCHEDULE_CNY),usd_reference_only=True,maximum_reference_usd=str(CAP),maximum_schedule_reference_usd=str(MAX_SCHEDULE),maximum_request_bytes=36000,maximum_wait_seconds=WAIT,maximum_elapsed_seconds=ELAPSED,
       model=MODEL,planning_tokens=16384,answer_tokens=8192,maximum_each_planning_cny=str(MAX_PLANNING_CNY),maximum_each_answer_cny=str(MAX_ANSWER_CNY),rates_cny=dict(input=str(CNY_INPUT_RATE),output=str(CNY_OUTPUT_RATE)),reference_rates_usd=dict(input=str(INPUT_RATE),output=str(OUTPUT_RATE)),execution_files={name:file_sha(name)for name in files},retries=0,case_substitution=False,maximum_aggregate_calls=14,maximum_aggregate_cny='14')


def expected_grant(package,ready=False,review_sha=None):
    return dict(schema='hcl-two-stage-cny-grant-v1',currency='CNY',stage=STAGE,status='READY'if ready else'PREPARED_NOT_AUTHORIZED',authorization_ref=AUTH if ready else None,approved_at=APPROVED if ready else None,expires_at=EXPIRES if ready else None,package_sha256=digest(package),authorized_calls=MAX_CALLS if ready else 0,authorized_cny=str(CAP_CNY)if ready else'0',phase1_source_review_sha256=review_sha if STAGE==2 and ready else None,retries=0,historical_budget_transfer=False,other_stage_budget_transfer=False)


def require_time(now):
    start=datetime.fromisoformat(APPROVED.replace('Z','+00:00'));end=datetime.fromisoformat(EXPIRES.replace('Z','+00:00'))
    if not isinstance(now,datetime)or now.tzinfo is None or now<start or now+timedelta(seconds=WAIT)>=end: raise ValueError('AUTHORIZATION_TIME_OR_SEND_MARGIN_INVALID')


def validate_phase1_review(expected_sha):
    from scripts.two_stage_public import validate_phase1_gate
    if not isinstance(expected_sha,str)or file_sha(PHASE1_REVIEW)!=expected_sha: raise ValueError('EXACT_PHASE1_REVIEW_REQUIRED')
    return validate_phase1_gate(json.loads(PHASE1_EVIDENCE.read_text()),json.loads(PHASE1_REVIEW.read_text()))


def require_grant(package,grant,now):
    if package!=build_package():raise ValueError('PACKAGE_DRIFT')
    expected=expected_grant(package,True,grant.get('phase1_source_review_sha256'))
    if grant!=expected:raise ValueError('EXACT_NEW_OWNER_GRANT_REQUIRED')
    require_time(now)
    if STAGE==2:validate_phase1_review(grant['phase1_source_review_sha256'])


def final_fields(raw):
    if not isinstance(raw,str)or len(raw)>64000:return None
    try:value=json.loads(raw)
    except(ValueError,TypeError):return None
    if not isinstance(value,dict)or set(value)!={'answer','source_citations','uncertainty','assumptions'}:return None
    if any(not isinstance(value[k],str)for k in ('answer','uncertainty','assumptions'))or not isinstance(value['source_citations'],list):return None
    for c in value['source_citations']:
        if(not isinstance(c,dict)or not {'source_id','version','quote'}<=set(c)or not set(c)<={'source_id','version','quote','start'}or not isinstance(c['source_id'],str)or not isinstance(c['quote'],str)or type(c['version'])is not int or ('start'in c and(type(c['start'])is not int or c['start']<0))):return None
    return value


def accepted(prompt,raw):
    value=final_fields(raw)
    return bool(value is not None and value['answer'].strip() and value['source_citations'] and audit_supplied_source_citations(prompt,raw)['deliverable'])


class CaptureClient:
    """Intercept only bounded final visible text, never the full envelope or reasoning."""
    def __init__(self,client,port):
        self.client=client;self.port=port
        self.base_url=client.base_url;self.max_retries=client.max_retries;self.timeout=client.timeout
        self.chat=SimpleNamespace(completions=SimpleNamespace(create=self.create))
    def create(self,**request):
        result=self.client.chat.completions.create(**request)
        if request.get('max_tokens')==8192:
            raw=result.model_dump(mode='json')if hasattr(result,'model_dump')else result
            choices=raw.get('choices')if isinstance(raw,dict)and raw.get('model')==MODEL else None
            message=choices[0].get('message')if isinstance(choices,list)and len(choices)==1 and isinstance(choices[0],dict)else None
            text=message.get('content')if isinstance(message,dict)else None
            if isinstance(text,str)and len(text)<=64000:
                self.port.final_raw=text
                # Main thread persists this bounded text in Port.finally before
                # runtime schema validation. A late timed-out thread never writes files.
        return result


class Ledger:
    def __init__(self, directory, package, grant, clock, monotonic):
        self.directory = Path(directory); self.directory.mkdir(mode=0o700, parents=True, exist_ok=False)
        self.path = self.directory / 'receipt.json'; self.clock = clock; self.monotonic = monotonic
        self.started = monotonic(); self.package = package; self.grant = grant; self.active = None; self.stopped = False
        self.value = dict(schema='hcl-two-stage-cny-private-receipt-v1', currency='CNY', usd_reference_only=True, stage=STAGE, package_sha256=digest(package), authorization_ref=AUTH,
                          status='RUNNING', calls=[], arms=[], reserved_usd='0', reserved_cny='0', started_at=clock().isoformat())
        self.persist()

    def persist(self):
        try: save(self.path, self.value)
        except Exception:
            self.stopped = True
            raise

    def admit(self):
        self.validate_native_ledger()
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
                reserve = MAX_PLANNING if phase == 'planning' else MAX_ANSWER
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
            expected_case = dict(maximum_case_reservation_usd=str(MAX_PLANNING + MAX_ANSWER if STAGE == 1 else MAX_PLANNING + 2*MAX_ANSWER))
            held_case = sum(Decimal(c['reserved_usd']) for c in self.value['calls'] if c['case_id'] == case)
            if held_case + reserve > Decimal(expected_case['maximum_case_reservation_usd']):
                raise ValueError('CASE_CAP_EXCEEDED')
            if len(self.value['calls']) >= MAX_CALLS or held + reserve > CAP or held + reserve > MAX_SCHEDULE:
                raise ValueError('AGGREGATE_CAP_EXCEEDED')
            reserve_cny=MAX_PLANNING_CNY if phase=='planning'else MAX_ANSWER_CNY
            exact_cny=cny_quote(request_bytes,request['max_tokens'])
            held_cny=Decimal(self.value['reserved_cny'])
            held_case_cny=sum(Decimal(c['reserved_cny'])for c in self.value['calls']if c['case_id']==case)
            case_cap_cny=MAX_PLANNING_CNY+MAX_ANSWER_CNY if STAGE==1 else MAX_PLANNING_CNY+2*MAX_ANSWER_CNY
            if exact_cny>reserve_cny or held_case_cny+reserve_cny>case_cap_cny or held_cny+reserve_cny>CAP_CNY or held_cny+reserve_cny>MAX_SCHEDULE_CNY:raise ValueError('NATIVE_CNY_CAP_EXCEEDED')
            prior_cny=Decimal('0')if STAGE==1 else MAX_PLANNING_CNY+MAX_ANSWER_CNY
            if prior_cny+held_cny+reserve_cny>TOTAL_CAP_CNY:raise ValueError('AGGREGATE_CNY_CAP_EXCEEDED')
            self.value['calls'].append(dict(call_id=call_id, case_id=case, arm=arm, phase=phase,
                request_sha256=digest(request), request_bytes=request_bytes, reserved_usd=str(reserve), exact_request_reservation_usd=str(exact_reserve), reserved_cny=str(reserve_cny),exact_request_reservation_cny=str(exact_cny),
                status='RESERVED_BEFORE_CALL', invocation_status='NOT_INVOKED', provider_call=False))
            self.value['reserved_usd'] = str(held + reserve);self.value['reserved_cny']=str(held_cny+reserve_cny); self.persist()
            return reserve
        except Exception:
            self.stopped = True
            raise

    def validate_native_ledger(self):
        if self.value.get('currency')!='CNY'or self.value.get('usd_reference_only')is not True:raise ValueError('NATIVE_CNY_LEDGER_REQUIRED')
        rows=self.value['calls'];total=Decimal('0')
        if len(rows)>MAX_CALLS or len({row['call_id']for row in rows})!=len(rows):raise ValueError('NATIVE_CNY_CALL_LIMIT')
        for row in rows:
            case,arm,phase=row['call_id'].split(':')
            if(case,arm)not in ORDER or phase not in('planning','answer')or(arm=='Base'and phase!='answer'):raise ValueError('NATIVE_CNY_DECLARED_PHASE_REQUIRED')
            expected=MAX_PLANNING_CNY if phase=='planning'else MAX_ANSWER_CNY
            held=Decimal(row['reserved_cny'])
            if not held.is_finite()or held!=expected:raise ValueError('NATIVE_CNY_RESERVATION_REQUIRED')
            total+=held
        recorded=Decimal(self.value['reserved_cny'])
        prior=Decimal('0')if STAGE==1 else MAX_PLANNING_CNY+MAX_ANSWER_CNY
        if not recorded.is_finite()or recorded!=total or total>CAP_CNY or total>MAX_SCHEDULE_CNY or prior+total>TOTAL_CAP_CNY:raise ValueError('NATIVE_CNY_LEDGER_CAP_EXCEEDED')
        return True

    def close(self):
        self.value.update(status='STOPPED_NO_RETRY' if self.stopped else 'COMPLETED_ONE_PASS',
                          finished_at=self.clock().isoformat(), elapsed_seconds=self.monotonic()-self.started,
                          budget_state='CLOSED_NO_TRANSFER_NO_RETRY', remaining_authorized_calls=0, remaining_authorized_usd='0',remaining_authorized_cny='0')
        self.stopped = True; self.persist()


class Port:
    provider_free = False
    cost_basis = 'USAGE_RATED_PEAK_NOT_INVOICE'
    def __init__(self, client, ledger, stage):
        self.ledger = ledger; self.stage = stage; self.final_raw = None
        self.inner = OutputLimitPort(CaptureClient(client, self), planning_tokens=16384)
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
            if self.final_raw is not None:
                record=next(a for a in self.ledger.value['arms']if a['case_id']+':'+a['arm']==self.stage)
                record.update(final_text=self.final_raw,final_answer_sha256=hashlib.sha256(self.final_raw.encode()).hexdigest())
            row['sdk_seconds'] = self.ledger.monotonic() - start
            data = self.inner.diagnostics
            if data.get('usage_valid') is True:
                counts = data['usage']; rated = (counts['prompt_tokens']*INPUT_RATE + counts['completion_tokens']*OUTPUT_RATE)/1000000
                rated_cny=(counts['prompt_tokens']*CNY_INPUT_RATE+counts['completion_tokens']*CNY_OUTPUT_RATE)/1000000
                if rated > Decimal(row['reserved_usd']) or rated_cny>Decimal(row['reserved_cny']): self.ledger.stopped = True
                else: row.update(usage=counts, usage_rated_usd=str(rated),usage_rated_cny=str(rated_cny))
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
                    record.update(native_results=result['hcl_execution']['native_results'], final_delivery_code=result.get('final_delivery_code', 'NOT_REACHED'), selected_capabilities=[o['capability'] for o in result.get('plan', {}).get('operations', [])],
                                  executed_capabilities=[o['capability'] for o in result['operations'] if o.get('executed')],
                                  checked_treatment=[o['capability'] for o in result['operations'] if o.get('checked_treatment_present')])
                    raw = port.responses.get('answer', port.final_raw); prompt = port.prompts.get('answer'); good = bool(raw is not None and accepted(prompt, raw))
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
                    elif port.known_failure: record['status'] = port.known_failure
                    elif result['status'] == 'ANSWER_SOURCE_REVIEW_FAILED' or raw is not None: record['status'] = 'FINAL_SCHEMA_OR_CITATIONS_REJECTED'
                    elif failure in KNOWN_HCL_FAILURES or invalid_plan: record['status'] = 'BOUNDED_HCL_SCHEMA_SELECTION_OR_ADAPTER_FAILURE'
                    else: ledger.stopped = True; record['status'] = 'UNKNOWN_FAILURE_STOP'
                if raw is not None:
                    record['final_text'] = raw
                    record.update(final_fields=final_fields(raw), final_answer_sha256=hashlib.sha256(raw.encode()).hexdigest(), citations_accepted=good)
            except Exception:
                if port and port.final_raw is not None:
                    record.update(final_text=port.final_raw, final_fields=final_fields(port.final_raw), final_answer_sha256=hashlib.sha256(port.final_raw.encode()).hexdigest())
                if port and port.known_failure and not ledger.stopped: record['status'] = port.known_failure
                else: ledger.stopped = True; record['status'] = 'UNKNOWN_FAILURE_STOP'
            finally:
                record['arm_seconds'] = monotonic() - start
                record['sdk_seconds'] = sum(r.get('sdk_seconds', 0) for r in ledger.value['calls'] if r['call_id'].startswith(stage + ':'))
                record['non_sdk_seconds'] = max(0, record['arm_seconds'] - record['sdk_seconds'])
                if STAGE == 1 and record['status'] != 'ANSWER_ACCEPTED': ledger.stopped = True
                ledger.persist()
    finally: ledger.close()
    return ledger.value


def verify_launch(run_id,attempt,runs,event,parent,paths,marker,package,grant,now):
    require_grant(package,grant,now);verify_run_history(run_id,attempt,runs)
    expected=dict(schema='hcl-two-stage-cny-marker-v1',stage=STAGE,authorization_ref=AUTH,package_sha256=digest(package),grant_sha256=digest(grant),executor_commit=parent)
    if(event!='push'or not isinstance(parent,str)or len(parent)!=40 or any(c not in '0123456789abcdef'for c in parent)or paths!=[str(MARKER)]or marker!=expected):raise ValueError('ONE_MARKER_ONLY_LAUNCH_REQUIRED')


def main():
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--stage',type=int,required=True);parser.add_argument('--freeze',action='store_true');parser.add_argument('--check-launch');parser.add_argument('--execute',action='store_true')
    args=parser.parse_args();configure(args.stage);os.umask(0o077)
    if sum((args.freeze,bool(args.check_launch),args.execute))!=1:raise ValueError('ONE_MODE_REQUIRED')
    if args.freeze:
        package=build_package();save(PACKAGE,package);save(GRANT,expected_grant(package));return
    if os.environ.get('GITHUB_REF')!='refs/heads/main'or os.environ.get('GITHUB_RUN_ATTEMPT')!='1':raise ValueError('MAIN_ATTEMPT_ONE_REQUIRED')
    if WORKFLOW.read_bytes()!=TEMPLATE.read_bytes():raise ValueError('FROZEN_WORKFLOW_REQUIRED')
    package=json.loads(PACKAGE.read_text());grant=json.loads(GRANT.read_text());require_grant(package,grant,utcnow())
    identity=dict(run_id=os.environ['GITHUB_RUN_ID'],head_sha=os.environ['GITHUB_SHA'])
    if json.loads(SECRET_CHECK.read_text())!=dict(identity,existing_provider_secret='PRESENT'):raise ValueError('SAME_RUN_SECRET_CHECK_REQUIRED')
    from scripts.two_stage_price import validate_price_evidence
    price_path=Path(f'/tmp/hcl-two-stage-cny-{STAGE}-prices.json')
    price=json.loads(price_path.read_text());validate_price_evidence(price,identity,utcnow())
    from scripts.two_stage_account import validate as validate_account
    account=json.loads(Path(f'/tmp/hcl-two-stage-cny-{STAGE}-account.json').read_text());validate_account(account,identity,utcnow())
    expected=dict(identity,package_sha256=digest(package),grant_sha256=digest(grant),price_sha256=digest(price),account_sha256=digest(account));admission=Path(f'/tmp/hcl-two-stage-cny-{STAGE}-admission.json')
    if args.check_launch:
        pages=json.loads(Path(args.check_launch).read_text());history=[run for page in pages for run in page['workflow_runs']]
        ancestry=subprocess.check_output(['git','rev-list','--parents','-n','1','HEAD'],text=True).split()
        if len(ancestry)!=2:raise ValueError('SINGLE_PARENT_REQUIRED')
        paths=subprocess.check_output(['git','diff-tree','--no-commit-id','--name-only','-r','HEAD'],text=True).splitlines()
        verify_launch(identity['run_id'],'1',history,os.environ.get('GITHUB_EVENT_NAME'),ancestry[1],paths,json.loads(MARKER.read_text()),package,grant,utcnow())
        save(admission,expected);print('TWO_STAGE_ONE_LAUNCH_ADMITTED')
    else:
        if json.loads(admission.read_text())!=expected:raise ValueError('EXACT_RUN_ADMISSION_REQUIRED')
        import logging
        logging.disable(logging.CRITICAL);os.environ.pop('OPENAI_LOG',None)
        from openai import OpenAI
        key=os.environ.get('DEEPSEEK_API_KEY')
        if not key:raise ValueError('EXISTING_SECRET_UNAVAILABLE')
        run(OpenAI(api_key=key,base_url='https://api.deepseek.com',max_retries=0,timeout=WAIT),package,grant,f'two-stage-cny-{STAGE}-private')
        print('TWO_STAGE_TERMINATED_NO_RETRY')

if __name__=='__main__':main()
