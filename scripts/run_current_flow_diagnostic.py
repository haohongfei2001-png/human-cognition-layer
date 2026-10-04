"""One consumed-source G05 delivery regression; prepared closed, no automatic retries."""
from dataclasses import asdict
from datetime import datetime,timedelta,timezone
from decimal import Decimal
import hashlib,json,os,subprocess,threading,time
from pathlib import Path
from types import SimpleNamespace

from hcl.cognition import UniversalHCL,CallAllowance
from hcl.cognition.capability_catalog import CATALOG
from hcl.cognition.deepseek_metered import MODEL,INPUT_RATE,OUTPUT_RATE,OUTPUT_MARGIN
from hcl.cognition.retained import audit_supplied_source_citations
from hcl.cognition.universal_entry import PLANNER_POLICY
from scripts import run_bounded_diagnostics as common
from scripts.output_limit_port import OutputLimitPort
from scripts.run_output_limit_continuation import RecordedPort
from scripts.run_universal_development import save
from scripts.universal_development_protocol import digest
from scripts.universal_launch_guard import verify_run_history
from scripts.universal_encrypted_result import recipient_fingerprint
from scripts.development_nonblank_answer_amendment import validate_current
from scripts.serious_eval_contract import runtime_digest

RUNTIME_COMMIT='93e85b78ce26a91bf28e975420e4a93febc7cc52'
RUNTIME_SHA='90737b3ed772f65851553d8a673112eae50f2781185d8b5b4ccd127cdfb8663b'
CAP=Decimal('0.30');MAX_CALLS=2;WAIT=180;ELAPSED=900
AUTHORIZATION='OWNER_APPROVED_CURRENT_FLOW_PUBLIC_SYNTHETIC_20261004_113427'
APPROVED_AT='2026-10-04T11:34:27Z'
EXPIRES_AT='2026-10-05T11:34:27Z'
PUBLIC_SCOPE='ONE_CONSUMED_G05_FINAL_FIELDS_CITATIONS_IDENTITY_USAGE_ONLY_SAME_HCL_REPOSITORY'
SECRET_CHECK=Path('/tmp/current-flow-secret-presence.json')
INPUT=Path('.github/frozen/hcl-current-flow-input.json')
INPUT_SHA='561f54c04c71e0a61a0edfec1b36578b62f460a602025e73745703fdce068328'
ORIGINAL_REQUEST=Path('.github/frozen/hcl-planner-contract-smoke-request.json')
ORIGINAL_REQUEST_SHA='b8d2e0f68e9ceabb8a92d47a9bbebba182e3769fb61c561ae341bb69e6f32ab6'
PACKAGE=Path('reports/HCL_CURRENT_FLOW_PACKAGE.json')
GRANT=Path('.github/HCL_CURRENT_FLOW_GRANT.json')
READINESS=Path('reports/HCL_CURRENT_FLOW_READINESS.json')
TEMPLATE=Path('.github/frozen/hcl-current-flow-once.yml')
WORKFLOW=Path('.github/workflows/hcl-current-flow-once.yml')
MARKER=Path('.github/HCL_CURRENT_FLOW_TRIGGER.json')
RECIPIENT=Path('.github/HCL_UNIVERSAL_DEVELOPMENT_RECIPIENT.pem')
HISTORICAL_GRANTS=tuple(Path('.github')/('HCL_'+name+'_GRANT.json')for name in (
    'BOUNDED_DIAGNOSTIC','OUTPUT_LIMIT_CONTINUATION','PLANNER_CONTRACT_SMOKE','PLANNING_DIAGNOSTIC',
    'UNIVERSAL_DEVELOPMENT','I02_CLIFFORD_CPG','DRE001',*[f'DRC00{i}'for i in range(1,9)]))

def utcnow():return datetime.now(timezone.utc)
def file_sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def readiness():return json.loads(READINESS.read_text())

def frozen_input():
    if file_sha(INPUT)!=INPUT_SHA:raise ValueError('FROZEN_CONSUMED_INPUT_REQUIRED')
    value=json.loads(INPUT.read_text());original=json.loads(ORIGINAL_REQUEST.read_text())
    if digest(original)!=ORIGINAL_REQUEST_SHA:raise ValueError('HISTORICAL_FAILED_REQUEST_DRIFT')
    payload=json.loads(original['messages'][-1]['content'])
    if value['question']!=payload['question']or value['sources']!=payload['sources']:
        raise ValueError('UNCHANGED_FAILED_G05_INPUT_REQUIRED')
    return value

def planning_messages():
    source=frozen_input()
    return [dict(role='system',content=PLANNER_POLICY),dict(role='user',content=json.dumps(dict(
        question=source['question'],sources=source['sources'],capability_inventory=[asdict(c)for c in CATALOG.values()]),ensure_ascii=False,sort_keys=True))]

def build_package():
    validate_current()
    if runtime_digest()!=RUNTIME_SHA:raise ValueError('CERTIFIED_CURRENT_RUNTIME_REQUIRED')
    historical={}
    for path in HISTORICAL_GRANTS:
        value=json.loads(path.read_text())
        if 'CLOSED'not in value['status']or Decimal(str(value.get('remaining_authorized_usd',value.get('remaining_usd',-1))))!=0:
            raise ValueError('HISTORICAL_GRANT_MUST_STAY_CLOSED')
        historical[str(path)]=file_sha(path)
    port=OutputLimitPort(SimpleNamespace(base_url='https://api.deepseek.com',max_retries=0,timeout=WAIT),planning_tokens=16384)
    requests={}
    for name,phase,messages in [('planning','planning',planning_messages())]:
        request,encoded=port.request(phase,messages)
        requests[name]=dict(sha256=digest(request),bytes=len(encoded),reservation_usd=port.reservation_usd(phase,messages))
    maximum_answer=((2*36000+2048)*INPUT_RATE+(8192+OUTPUT_MARGIN)*OUTPUT_RATE)/1000000
    maximum=Decimal(requests['planning']['reservation_usd'])+maximum_answer
    if maximum>CAP:raise ValueError('COMPLETE_SCHEDULE_EXCEEDS_CAP')
    files=[__file__,str(INPUT),str(ORIGINAL_REQUEST),'reports/HCL_PLANNER_CONTRACT_SMOKE_CLOSURE.json',
        str(TEMPLATE),str(READINESS),str(RECIPIENT),'tests/test_current_flow_diagnostic.py',
        'scripts/output_limit_port.py','scripts/output_limit_protocol.py','scripts/bounded_diagnostic_port.py',
        'scripts/bounded_diagnostic_protocol.py','scripts/run_bounded_diagnostics.py','scripts/run_output_limit_continuation.py',
        'scripts/run_universal_development.py','scripts/universal_development_protocol.py',
        'scripts/universal_launch_guard.py','scripts/universal_encrypted_result.py',
        'scripts/development_nonblank_answer_amendment.py','scripts/serious_eval_contract.py',
        'scripts/current_flow_public_evidence.py','tests/test_current_flow_public_evidence.py']
    files=[str(Path(p).relative_to(Path.cwd()))if Path(p).is_absolute()else p for p in files]
    return dict(schema='hcl-current-flow-package-v1',purpose='CONSUMED_G05_FAILED_CITATION_REGRESSION_NOT_I02_COMPLETION_OR_EFFICACY',
        runtime_commit=RUNTIME_COMMIT,runtime_sha256=RUNTIME_SHA,input_sha256=INPUT_SHA,model=MODEL,
        thinking='enabled',reasoning_effort='high',planning_tokens=16384,answer_tokens=8192,
        production_default_planning_tokens=4096,maximum_request_bytes=36000,maximum_calls=MAX_CALLS,maximum_usd=str(CAP),
        maximum_schedule_reservation_usd=str(maximum),maximum_answer_reservation_usd=str(maximum_answer),requests=requests,
        historical_failed_request_sha256=ORIGINAL_REQUEST_SHA,
        historical_failed_receipt_sha256='88bb45c146ebe0f5f6f1bf745d8a0c786fb250c901558ceddf8c225f931f3de9',
        rates_usd_per_million=dict(input=str(INPUT_RATE),output=str(OUTPUT_RATE)),output_margin=OUTPUT_MARGIN,
        maximum_wait_seconds=WAIT,maximum_elapsed_seconds=ELAPSED,maximum_authorization_seconds=86400,
        sequence=['HCL_PLANNING','HCL_ANSWER_ONLY_IF_SOURCE_REQUEST_SUPPORTED_G05'],retries=0,
        base_calls=0,grader_calls=0,differential_calls=0,forced_selection=False,historical_budget_transfer=False,hcla_budget_transfer=False,
        recipient_sha256=recipient_fingerprint(RECIPIENT.read_bytes()),historical_private_readback=readiness(),
        public_output_scope=PUBLIC_SCOPE,public_output_authorization=AUTHORIZATION,
        historical_grants_sha256=historical,execution_files={p:file_sha(p)for p in files})

def expected_grant(package,*,authorization_ref=None,approved_at=None,expires_at=None):
    return dict(schema='hcl-current-flow-grant-v1',status='PREPARED_NOT_AUTHORIZED'if authorization_ref is None else 'READY',
        authorization_ref=authorization_ref,approved_at=approved_at,expires_at=expires_at,package_sha256=digest(package),
        authorized_calls=0 if authorization_ref is None else MAX_CALLS,authorized_usd='0'if authorization_ref is None else str(CAP),
        historical_budget_transfer=False,hcla_budget_transfer=False,retries=0,
        public_output_scope=PUBLIC_SCOPE if authorization_ref is not None else None)

def require_time(grant,now):
    approved=datetime.fromisoformat(grant['approved_at'].replace('Z','+00:00'))
    expires=datetime.fromisoformat(grant['expires_at'].replace('Z','+00:00'))
    if (not isinstance(now,datetime)or now.tzinfo is None or approved.tzinfo is None or expires.tzinfo is None or
        not timedelta(seconds=WAIT)<expires-approved<=timedelta(days=1)or now<approved or now+timedelta(seconds=WAIT)>=expires):
        raise ValueError('AUTHORIZATION_TIME_OR_SEND_MARGIN_INVALID')

def require_grant(package,grant,now):
    if package!=build_package():raise ValueError('CURRENT_FLOW_PACKAGE_DRIFT')
    ref=grant.get('authorization_ref')
    if ref!=AUTHORIZATION:raise ValueError('NEW_EXPLICIT_OWNER_AUTHORIZATION_REQUIRED')
    if grant!=expected_grant(package,authorization_ref=AUTHORIZATION,approved_at=APPROVED_AT,expires_at=EXPIRES_AT):
        raise ValueError('EXACT_BOUNDED_GRANT_REQUIRED')
    # This exact owner exception applies only to this public synthetic input. Old
    # private-readback flags remain historical facts, not a prerequisite for it.
    if package.get('public_output_scope')!=PUBLIC_SCOPE or package.get('input_sha256')!=INPUT_SHA:
        raise ValueError('EXACT_PUBLIC_SYNTHETIC_SCOPE_REQUIRED')
    require_time(grant,now)

class Ledger(common.Ledger):
    def __init__(self,directory,package,grant,clock):
        self.clock=clock;self.started=time.monotonic();self.lock=threading.Lock();self.closed=False
        self.package=package;self.grant=grant
        self.directory=Path(directory);self.directory.mkdir(parents=True,exist_ok=False,mode=0o700)
        self.path=self.directory/'receipt.json'
        self.value=dict(schema='hcl-current-flow-receipt-v1',package_sha256=digest(package),authorization_ref=grant['authorization_ref'],
            status='RUNNING',calls=[],reserved_usd='0',maximum_calls=MAX_CALLS,maximum_usd=str(CAP),invoice_cost_usd=None,
            source_status='CONSUMED_SYNTHETIC_REGRESSION',efficacy_verified=False,historical_budget_transfer=False,hcla_budget_transfer=False)
        self.persist()
    def admit(self):
        if self.closed:raise ValueError('CLOSED_NO_RETRY')
        require_time(self.grant,self.clock())
        if time.monotonic()-self.started+WAIT>=ELAPSED:raise ValueError('RUN_SEND_MARGIN_EXPIRED')
    def record(self,stage,snapshot,requests,responses,diagnostics):
        with self.lock:
            for attempt in snapshot['attempts']:
                phase=attempt['phase'];identity=stage+':'+phase;request=requests[phase];request_hash=digest(request)
                if identity not in ('hcl:planning','hcl:answer'):raise ValueError('FIXED_TWO_PHASES_ONLY')
                expected=self.package['requests'].get('planning'if identity=='hcl:planning'else '')
                if expected and request_hash!=expected['sha256']:raise ValueError('FROZEN_REQUEST_DRIFT')
                rows=[r for r in self.value['calls']if r['call_id']==identity]
                if not rows:
                    self.admit();reserve=Decimal(attempt['reserved_usd']);held=Decimal(self.value['reserved_usd'])
                    validator=OutputLimitPort(SimpleNamespace(base_url='https://api.deepseek.com',max_retries=0,timeout=WAIT),planning_tokens=16384)
                    exact,_=validator.request(phase,request['messages'])
                    if exact!=request or reserve!=Decimal(validator.reservation_usd(phase,request['messages'])):
                        raise ValueError('EXACT_REQUEST_RESERVATION_REQUIRED')
                    if len(self.value['calls'])>=MAX_CALLS:raise ValueError('CALL_CAP_EXHAUSTED')
                    if not reserve.is_finite()or reserve<0 or held+reserve>CAP or held+reserve>Decimal(self.package['maximum_schedule_reservation_usd']):
                        raise ValueError('USD_CAP_EXHAUSTED')
                    expected_order=['hcl:planning','hcl:answer']
                    if identity!=expected_order[len(self.value['calls'])]:raise ValueError('FIXED_CALL_ORDER_REQUIRED')
                    if phase=='answer'and stage=='hcl'and self.value['calls'][-1]['status']!='RETURNED':raise ValueError('PLANNING_MUST_RETURN')
                    row=dict(call_id=identity,ordinal=len(self.value['calls'])+1,stage=stage,phase=phase,request=request,request_sha256=request_hash)
                    self.value['calls'].append(row);self.value['reserved_usd']=str(held+reserve)
                else:
                    row=rows[0]
                    if row['request_sha256']!=request_hash or row['reserved_usd']!=attempt['reserved_usd']:raise ValueError('RESERVED_REQUEST_CHANGED')
                    if attempt.get('invocation_status')=='NOT_INVOKED'and row.get('invocation_status')!='NOT_INVOKED':raise ValueError('INVOKED_CALL_CANNOT_REARM')
                row.update(attempt)
                if phase in responses:row['response_content']=responses[phase]
                if phase in diagnostics:
                    data=diagnostics[phase];row['response_diagnostics']=data
                    if data.get('usage_valid')is True:
                        counts=data['usage'];rated=(counts['prompt_tokens']*INPUT_RATE+counts['completion_tokens']*OUTPUT_RATE)/1000000
                        if rated>Decimal(row['reserved_usd']):raise ValueError('USAGE_EXCEEDS_RESERVATION')
                        row.update(usage=counts,actual_usd=str(rated),validated_returned_model=MODEL)
                        if row.get('status')!='RETURNED':row['invocation_status']='RESPONSE_RETURNED_REJECTED'
            self.persist()

class G05RecordedPort(RecordedPort):
    """Observe real selection; refuse answer admission if the requested treatment is absent."""
    def __init__(self,client,ledger,session):
        super().__init__(client,ledger,'hcl',16384);self.session=session
    def reservation_usd(self,phase,messages):
        if phase=='answer':
            original=frozen_input();payload=json.loads(messages[-1]['content'])
            sources=[{k:r[k]for k in ('source_id','version','text')}for r in original['sources']]
            valid=False;core=self.session.workspace.core;statuses=core.support_statuses()
            if payload['question']==original['question']and payload['sources']==sources:
                for operation in payload['hcl_operations']:
                    if operation.get('capability')!='G05'or not operation.get('executed'):continue
                    result=operation.get('result',{});provenance=operation.get('request_provenance',{})
                    sid=result.get('source_id');request_root=provenance.get('span_id');source_root=self.session.workspace._spans.get(sid)
                    variants=result.get('variants',[]);claims=operation.get('support_claim_ids',[])
                    valid=(sid==sources[0]['source_id']and result.get('source_version')==sources[0]['version']and
                        result.get('question')==original['question']and result.get('source_modified')is False and
                        provenance.get('authority')=='ANALYSIS_CONDITION_NOT_WORLD_EVIDENCE'and
                        request_root in core.spans and source_root in core.spans and core.spans[request_root].quote==original['question']and
                        bool(variants)and all(v.get('question')==original['question']and v.get('only_one_factor_changed')is True
                            and v.get('source_modified')is False and bool(v.get('comparisons'))for v in variants)and
                        bool(claims)and all(statuses.get(c)=='SUPPORT_AVAILABLE'and core.dependencies.get(c)==
                            {tuple(sorted((request_root,source_root)))}for c in claims))
                    if valid:break
            self.ledger.value['g05_treatment_gate']='SOURCE_AND_ORIGINAL_REQUEST_SUPPORTED'if valid else 'MISSING_OR_UNSUPPORTED_G05_NO_ANSWER'
            self.ledger.persist()
            if not valid:raise ValueError('MISSING_OR_UNSUPPORTED_G05_NO_ANSWER')
        return super().reservation_usd(phase,messages)

def source_review(messages,raw):
    value=json.loads(raw)
    if (not isinstance(value,dict)or set(value)!={'answer','source_citations','uncertainty','assumptions'}or
        any(not isinstance(value[k],str)for k in ('answer','uncertainty','assumptions'))or
        not value['answer'].strip()or not isinstance(value['source_citations'],list)or not value['source_citations']):
        return dict(deliverable=False,status='NONEMPTY_CANONICAL_ANSWER_REQUIRED',semantic_certification=False)
    return audit_supplied_source_citations(messages,raw)

def run(client,package,grant,directory,*,clock=utcnow):
    require_grant(package,grant,clock());ledger=Ledger(directory,package,grant,clock)
    try:
        source=frozen_input();session=UniversalHCL()
        for row in source['sources']:
            session.put_source(row['source_id'],row['text']);session.sources[row['source_id']]=dict(row)
        port=G05RecordedPort(client,ledger,session);allowance=CallAllowance(2,CAP,grant['authorization_ref'],journal=port.journal)
        result=session.answer(source['question'],planner_backend=port,answer_backend=port,allowance=allowance);allowance.closed=True
        ledger.value.update(hcl=result,selected_capabilities=[o['capability']for o in result.get('plan',{}).get('operations',[])],
            executed_capabilities=[o['capability']for o in result['operations']if o['executed']],
            checked_treatment=[o['capability']for o in result['operations']if o.get('checked_treatment_present')])
        if result['status']!='ANSWERED_WITH_EXPLICIT_LIMITS':ledger.close('HCL_FAILED_NO_RETRY');return ledger.value
        review=source_review(result['actual_final_messages'],result['answer_raw']);ledger.value['hcl_source_review']=review
        ledger.value['hcl_citations_accepted']=review['deliverable'];ledger.persist()
        ledger.value['semantic_review']='PENDING_SOURCE_FIRST_REVIEW_NOT_MODEL_GRADED'
        ledger.close('G05_ANSWER_ACCEPTED_READBACK_PENDING'if review['deliverable']else 'HCL_CITATIONS_REJECTED_NO_RETRY')
    except Exception:ledger.close('FAILED_OR_UNKNOWN_NO_RETRY')
    return ledger.value

def verify_launch(run_id,attempt,runs,event,parent,paths,marker,package,grant,now):
    require_grant(package,grant,now);verify_run_history(run_id,attempt,runs)
    expected=dict(schema='hcl-current-flow-marker-v1',authorization_ref=grant['authorization_ref'],package_sha256=digest(package),grant_sha256=digest(grant),executor_commit=parent)
    if (event!='push'or not isinstance(parent,str)or len(parent)!=40 or any(c not in '0123456789abcdef'for c in parent)
        or paths!=[str(MARKER)]or marker!=expected):raise ValueError('ONE_EXACT_MARKER_ONLY_LAUNCH_REQUIRED')

def public_readback_identity(receipt_path,run_id,head_sha):
    if (not isinstance(run_id,str)or not run_id.isascii()or not run_id.isdecimal()or int(run_id)<=0 or
        not isinstance(head_sha,str)or len(head_sha)!=40 or any(c not in '0123456789abcdef'for c in head_sha)):
        raise ValueError('EXACT_PUBLIC_RUN_HEAD_REQUIRED')
    with Path(receipt_path).open('rb')as stream:raw=stream.read(16*1024*1024+1)
    if len(raw)>16*1024*1024:raise ValueError('BOUNDED_PRIVATE_RECEIPT_REQUIRED')
    receipt=json.loads(raw)
    package=json.loads(PACKAGE.read_text())
    if receipt.get('package_sha256')!=digest(package):raise ValueError('RECEIPT_PACKAGE_IDENTITY_REQUIRED')
    return dict(schema='hcl-current-flow-public-readback-identity-v1',run_id=int(run_id),head_sha=head_sha,
        package_sha256=digest(package),receipt_sha256=hashlib.sha256(raw).hexdigest(),runtime_sha256=RUNTIME_SHA,recipient_sha256=package['recipient_sha256'])

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--freeze',action='store_true');parser.add_argument('--check-launch');parser.add_argument('--execute',action='store_true');parser.add_argument('--output',default='current-flow-private');args=parser.parse_args();os.umask(0o077)
    if sum((args.freeze,bool(args.check_launch),args.execute))!=1:raise ValueError('ONE_MODE_REQUIRED')
    if args.freeze:
        package=build_package();save(PACKAGE,package);save(GRANT,expected_grant(package))
    else:
        if os.environ.get('GITHUB_REF')!='refs/heads/main'or os.environ.get('GITHUB_RUN_ATTEMPT')!='1':raise ValueError('MAIN_ATTEMPT_ONE_REQUIRED')
        if WORKFLOW.read_bytes()!=TEMPLATE.read_bytes():raise ValueError('FROZEN_WORKFLOW_REQUIRED')
        package=json.loads(PACKAGE.read_text());grant=json.loads(GRANT.read_text());require_grant(package,grant,utcnow())
        identity=dict(run_id=os.environ['GITHUB_RUN_ID'],head_sha=os.environ['GITHUB_SHA'])
        if json.loads(SECRET_CHECK.read_text())!=dict(identity,existing_provider_secret='PRESENT'):
            raise ValueError('SAME_RUN_EXISTING_SECRET_PRESENCE_REQUIRED')
        expected=dict(identity,package_sha256=digest(package),grant_sha256=digest(grant))
        admission=Path('/tmp/current-flow-admission.json')
        if args.check_launch:
            history=[r for page in json.loads(Path(args.check_launch).read_text())for r in page['workflow_runs']]
            ancestry=subprocess.check_output(['git','rev-list','--parents','-n','1','HEAD'],text=True).split()
            if len(ancestry)!=2:raise ValueError('SINGLE_PARENT_REQUIRED')
            paths=subprocess.check_output(['git','diff-tree','--no-commit-id','--name-only','-r','HEAD'],text=True).splitlines()
            verify_launch(os.environ['GITHUB_RUN_ID'],os.environ['GITHUB_RUN_ATTEMPT'],history,os.environ.get('GITHUB_EVENT_NAME'),ancestry[1],paths,json.loads(MARKER.read_text()),package,grant,utcnow())
            save(admission,expected);print('CURRENT_FLOW_SINGLE_LAUNCH_ADMITTED')
        else:
            if json.loads(admission.read_text())!=expected:raise ValueError('EXACT_RUN_ADMISSION_REQUIRED')
            import logging
            logging.disable(logging.CRITICAL);os.environ.pop('OPENAI_LOG',None)
            from openai import OpenAI
            key=os.environ.get('DEEPSEEK_API_KEY')
            if not key:raise ValueError('EXISTING_SECRET_UNAVAILABLE')
            run(OpenAI(api_key=key,base_url='https://api.deepseek.com',max_retries=0,timeout=WAIT),package,grant,args.output)
            print('CURRENT_FLOW_TERMINATED_NO_RETRY')
