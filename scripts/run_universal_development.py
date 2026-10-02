"""Exactly one fresh approved six-task development comparison; no automatic retry."""
import hashlib,json,os,threading,time
from decimal import Decimal
from pathlib import Path
from hcl.cognition import UniversalHCL,CallAllowance
from hcl.cognition.deepseek_metered import DeepSeekMeteredPort,safe_metered_failure_details
from hcl.cognition.reader_entry import _FINAL_ANSWER_POLICY
from scripts.universal_development_protocol import CASES,ordinary,protocol,digest

CAP=Decimal('2.50');MAX_CALLS=18;MAX_SECONDS=1800
PACKAGE=Path('reports/HCL_UNIVERSAL_DEVELOPMENT_PACKAGE.json')
GRANT=Path('.github/HCL_UNIVERSAL_DEVELOPMENT_GRANT.json')
TEMPLATE=Path('.github/frozen/hcl-universal-development-once.yml')
WORKFLOW=Path('.github/workflows/hcl-universal-development-once.yml')


def save(path,value):
    path=Path(path);temporary=path.with_suffix(path.suffix+'.tmp')
    with temporary.open('w')as stream:
        json.dump(value,stream,ensure_ascii=False,sort_keys=True,indent=2);stream.write('\n');stream.flush();os.fsync(stream.fileno())
    os.replace(temporary,path)
    descriptor=os.open(str(path.parent),os.O_RDONLY)
    try:os.fsync(descriptor)
    finally:os.close(descriptor)


def base_messages(case):
    return [dict(role='system',content=_FINAL_ANSWER_POLICY),dict(role='user',content=json.dumps(dict(
        question=case['question'],sources=[dict(source_id=k,version=1,text=v)for k,v in case['sources'].items()],
        knowledge_basis='SUPPLIED_SOURCES_AND_EXPLICIT_INTERPRETATION' if case['sources'] else 'UNSOURCED_MODEL_KNOWLEDGE'),ensure_ascii=False,sort_keys=True))]


def score(case,raw):
    result=dict(format_valid=False,exact_option_correct=None if case['expected_label']is None else False,
        explanation_semantics='SOURCE_FIRST_REVIEW_REQUIRED',open_ended=case['expected_label']is None)
    try:
        value=json.loads(raw)
        valid=isinstance(value,dict)and set(value)=={'answer','source_citations','uncertainty','assumptions'}and all(isinstance(value[k],str)for k in ('answer','uncertainty','assumptions'))and isinstance(value['source_citations'],list)
        result['format_valid']=valid
        if case['expected_label']is not None:result['exact_option_correct']=valid and value['answer'].strip()==case['expected_label']
    except (TypeError,ValueError):pass
    return result


def build_package():
    files=['scripts/universal_development_protocol.py','scripts/run_universal_development.py',str(TEMPLATE),
           'tests/test_universal_development_execution.py','tests/test_v1_deepseek_metered.py',
           'scripts/universal_encrypted_result.py','tests/test_universal_encrypted_result.py',
           '.github/HCL_UNIVERSAL_DEVELOPMENT_RECIPIENT.pem',
           'reports/HCL_DEVELOPMENT_BENCHMARK_EXPOSURE_REGISTER.json',
           'scripts/universal_launch_guard.py','tests/test_universal_launch_guard.py']
    proposed=protocol()
    for field in ('authorized_calls','authorized_spend_usd','live_execution_enabled'):proposed.pop(field)
    return dict(proposed,schema='hcl-universal-development-package-v1',
        execution_authority='SEPARATE_MATCHING_READY_GRANT_REQUIRED',
        approved_maximum_calls=18,approved_maximum_usd='2.50',
        execution_files={p:hashlib.sha256(Path(p).read_bytes()).hexdigest()for p in files},
        common_answer_contract_sha256=hashlib.sha256(_FINAL_ANSWER_POLICY.encode()).hexdigest(),
        base_request_messages_sha256={c['case_id']:digest(base_messages(c))for c in CASES},
        maximum_elapsed_seconds=MAX_SECONDS,actual_requests_recorded_before_each_transport=True,
        output_policy='CONTENT_ONLY_NO_PROVIDER_REASONING_OR_RAW_EXCEPTIONS',
        scorer='FIVE_EXACT_OPTIONS_AND_ONE_UNSCORED_OPEN_ENDED_CASE; EXPLANATION_REVIEW_SEPARATE')


class Ledger:
    def __init__(self,directory,package,grant):
        self.directory=Path(directory);self.directory.mkdir(parents=True,exist_ok=False,mode=0o700)
        self.path=self.directory/'receipt.json';self.lock=threading.Lock();self.deadline=time.monotonic()+MAX_SECONDS
        self.value=dict(schema='hcl-universal-development-receipt-v1',package_sha256=digest(package),
            status='RUNNING',grant_authorization_ref=grant['authorization_ref'],maximum_calls=MAX_CALLS,
            maximum_usd=str(CAP),reserved_usd='0',calls=[],results=[],
            cost_basis='USAGE_RATED_PEAK_NOT_INVOICE',actual_invoice_cost_usd=None,
            historical_budget_transfer=False,longmemeval='SEALED_NOT_ACCESSED')
        save(self.path,self.value)

    def record(self,case_id,arm,snapshot,requests,responses):
        with self.lock:
            for attempt in snapshot['attempts']:
                phase=attempt['phase'];key=(case_id,arm,phase)
                rows=[r for r in self.value['calls']if (r['case_id'],r['arm'],r['phase'])==key]
                if not rows:
                    if time.monotonic()>=self.deadline:raise ValueError('BATCH_DEADLINE_EXPIRED')
                    if len(self.value['calls'])>=MAX_CALLS:raise ValueError('CALL_CAP_EXHAUSTED')
                    reserve=Decimal(attempt['reserved_usd'])
                    if Decimal(self.value['reserved_usd'])+reserve>CAP:raise ValueError('USD_CAP_EXHAUSTED')
                    request=requests[phase]
                    row=dict(case_id=case_id,arm=arm,phase=phase,request=request,request_sha256=digest(request))
                    self.value['calls'].append(row);self.value['reserved_usd']=str(Decimal(self.value['reserved_usd'])+reserve)
                else:row=rows[0]
                row.update(attempt)
                if phase in responses:row['response_content']=responses[phase]
            save(self.path,self.value)

    def close(self,status):
        with self.lock:
            self.value.update(status=status,budget_state='CLOSED_NO_TRANSFER_NO_RETRY',remaining_authorized_usd='0',remaining_authorized_calls=0)
            save(self.path,self.value)


class RecordedPort:
    def __init__(self,client,ledger,case_id,arm):
        self.inner=DeepSeekMeteredPort(client);self.ledger=ledger;self.case_id=case_id;self.arm=arm
        self.requests={};self.responses={};self.provider_free=False;self.cost_basis=self.inner.cost_basis
    def reservation_usd(self,phase,messages):
        reserve=self.inner.reservation_usd(phase,messages);request,_=self.inner.request(phase,messages)
        self.requests[phase]=request;return reserve
    def complete(self,phase,messages):
        result=self.inner.complete(phase,messages);self.responses[phase]=result['text'];return result
    def journal(self,snapshot):self.ledger.record(self.case_id,self.arm,snapshot,self.requests,self.responses)


def require_grant(package,grant):
    expected=dict(schema='hcl-universal-development-grant-v1',status='READY',package_sha256=digest(package),
        authorization_ref='OWNER_APPROVED_2026_10_02_NEW_2_50_18_CALLS',maximum_usd='2.50',maximum_calls=18,
        historical_budget_transfer=False,retries=0)
    if grant!=expected:raise ValueError('EXACT_NEW_BOUNDED_GRANT_REQUIRED')
    if package!=build_package():raise ValueError('FROZEN_PACKAGE_DRIFT')


def run(client,package,grant,directory):
    require_grant(package,grant);ledger=Ledger(directory,package,grant)
    try:
        for index,case in enumerate(CASES):
            for arm in (['Base','HCL']if index%2==0 else ['HCL','Base']):
                port=RecordedPort(client,ledger,case['case_id'],arm)
                if arm=='Base':
                    messages=base_messages(case);reserve=port.reservation_usd('answer',messages)
                    attempt=dict(phase='answer',reserved_usd=reserve,status='RESERVED_BEFORE_CALL',provider_call=False,invocation_status='NOT_INVOKED')
                    port.journal(dict(attempts=[attempt]))
                    inside_backend=False
                    try:
                        attempt.update(provider_call=True,invocation_status='INVOKED_OR_SEND_UNKNOWN')
                        inside_backend=True
                        result=port.complete('answer',messages)
                        inside_backend=False
                        attempt.update(status='RETURNED',actual_usd=result['actual_usd'],usage=result['usage'],invocation_status='RETURNED')
                        port.journal(dict(attempts=[attempt]));raw=result['text'];details=None
                    except Exception as error:
                        attempt.update(safe_metered_failure_details(error,reserve)if inside_backend else {'failure_code':'METERED_BACKEND_OR_JOURNAL_FAILED'})
                        attempt['status']='FAILED_OR_UNKNOWN_NO_RETRY';port.journal(dict(attempts=[attempt]));raise
                else:
                    session=UniversalHCL()
                    for source_id,text in case['sources'].items():session.put_source(source_id,text)
                    allowance=CallAllowance(2,CAP,grant['authorization_ref'],journal=port.journal)
                    details=session.answer(case['question'],planner_backend=port,answer_backend=port,allowance=allowance)
                    if details['status'] not in ('ANSWERED_WITH_EXPLICIT_LIMITS','ANSWER_SOURCE_REVIEW_FAILED'):
                        ledger.value['results'].append(dict(case_id=case['case_id'],arm=arm,orchestration=details))
                        raise ValueError('HCL_ORCHESTRATION_FAILED_NO_RETRY')
                    raw=details['answer_raw']
                ledger.value['results'].append(dict(case_id=case['case_id'],arm=arm,score=score(case,raw),orchestration=details))
                save(ledger.path,ledger.value)
        ledger.close('COMPLETED_CONSTRUCTED_DEVELOPMENT_ONLY')
    except Exception:
        ledger.close('FAILED_OR_INCOMPLETE_NO_RETRY')
        raise
    return ledger.value


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--freeze',action='store_true');parser.add_argument('--execute',action='store_true');parser.add_argument('--output',default='universal-development-private')
    args=parser.parse_args()
    os.umask(0o077)
    if args.freeze:
        if args.execute:raise ValueError('choose one mode')
        save(PACKAGE,build_package())
    elif args.execute:
        if os.environ.get('GITHUB_REF')!='refs/heads/main' or os.environ.get('GITHUB_RUN_ATTEMPT')!='1' or os.environ.get('HCL_UNIVERSAL_DEVELOPMENT_AUTHORIZED')!='ONE_NEW_2_50_18_CALL_BATCH':raise ValueError('UNIQUE_APPROVED_MAIN_EXECUTION_REQUIRED')
        if WORKFLOW.read_bytes()!=TEMPLATE.read_bytes():raise ValueError('FROZEN_WORKFLOW_REQUIRED')
        package=json.loads(PACKAGE.read_text());grant=json.loads(GRANT.read_text());require_grant(package,grant)
        from scripts.universal_launch_guard import verify_execution_event
        verify_execution_event(digest(package),digest(grant))
        # Public workflow logs must never contain request/response bodies.
        import logging
        logging.disable(logging.CRITICAL)
        os.environ.pop('OPENAI_LOG',None)
        from openai import OpenAI
        key=os.environ.get('DEEPSEEK_API_KEY')
        if not key:raise ValueError('EXISTING_SERVER_SECRET_UNAVAILABLE')
        client=OpenAI(api_key=key,base_url='https://api.deepseek.com',max_retries=0,timeout=180)
        run(client,package,grant,args.output)
    else:raise ValueError('explicit freeze or execute mode required')
