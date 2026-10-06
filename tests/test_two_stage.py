"""Synthetic transport only; no provider client or credential is constructed."""
from contextlib import ExitStack
from datetime import datetime,timezone,timedelta
from decimal import Decimal
import copy,hashlib,json,tempfile,time,unittest
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace
from scripts import run_two_stage_once as r
from scripts import two_stage_public as public
from tests.test_v1_deepseek_metered import FakeClient

NOW=datetime(2026,10,6,19,tzinfo=timezone.utc)
class Client(FakeClient):
    timeout=180
    def __init__(self,mutate=None,empty=False):super().__init__();self.mutate=mutate;self.empty=empty
    def create(self,**request):
        value=super().create(**request);payload=json.loads(request['messages'][-1]['content']);source=payload['sources'][0]
        if request['max_tokens']==16384:
            answer=dict(task='Synthetic native operation',operations=[]if self.empty else[dict(capability='B01',question='What is directly reported?',source_ids=[source['source_id']],bindings=[])],limitations=[])
        else:
            answer=dict(answer='Rowan reports Wednesday; Mara reports Thursday. No authoritative actual date is established.',source_citations=[dict(source_id=source['source_id'],version=source['version'],quote=source['text'],start=0)],uncertainty='Reports do not establish the true date.',assumptions='No additional schedule.')
        value['choices'][0]['message']['content']=json.dumps(answer)
        value['choices'][0]['message']['reasoning_content']='PRIVATE_REASONING_CANARY'
        if self.mutate:self.mutate(value,len(self.calls),request)
        return value

def exported(result,package):
    identity=dict(run_id='42',head_sha='a'*40)
    return public.export(result,package,r.expected_grant(package,True,'b'*64 if r.STAGE==2 else None),identity,dict(identity,existing_provider_secret='PRESENT'))

def stage1_review(evidence):
    case=next(c for c in json.loads((r.ROOT/'cases.json').read_text())if c['id']=='SMOKE1')
    return dict(schema='hcl-two-stage-cny-phase1-source-review-v1',authorization_ref=r.AUTH,evidence_sha256=r.digest(evidence),source_sha256=case['source_sha256'],final_answer_sha256=evidence['arms'][0]['final_answer_sha256'],reviewer_role='INDEPENDENT_SOURCE_FIRST_AFTER_OUTPUT',criteria=[dict(id=i,passed=True,reason='Synthetic independent-check fixture, not an actual review.')for i in range(1,5)],overall_pass=True)

def execute(client,stage=1,**kwargs):
    with ExitStack()as stack,tempfile.TemporaryDirectory()as directory:
        if stage==2:
            first,pkg1=execute(Client(),stage=1);r.configure(1);evidence=exported(first,pkg1);review=stage1_review(evidence)
            ep=Path(directory)/'phase1.json';rp=Path(directory)/'review.json';r.save(ep,evidence);r.save(rp,review)
            stack.enter_context(patch.object(r,'PHASE1_EVIDENCE',ep));stack.enter_context(patch.object(r,'PHASE1_REVIEW',rp));review_sha=r.file_sha(rp)
        else:review_sha=None
        r.configure(stage);package=r.build_package();grant=r.expected_grant(package,True,review_sha)
        result=r.run(client,package,grant,Path(directory)/'run',clock=lambda:NOW,**kwargs)
        assert json.loads((Path(directory)/'run/receipt.json').read_text())==result
    return result,package

class TwoStageTests(unittest.TestCase):
    def tearDown(self):r.configure(1)
    def test_public_receipt_currency_schema_and_reference_role_are_explicit(self):
        result,package=execute(Client())
        for field,value in [('schema','hcl-two-stage-private-receipt-v1'),('currency','USD'),('usd_reference_only',False)]:
            with self.subTest(field=field):
                changed=copy.deepcopy(result);changed[field]=value
                with self.assertRaises(ValueError):exported(changed,package)
                changed.pop(field)
                with self.assertRaises(ValueError):exported(changed,package)
    def test_exact_static_requests_and_new_zero_grants(self):
        for stage,count in((1,1),(2,8)):
            r.configure(stage);package=r.build_package()
            self.assertEqual(len(package['requests']),count)
            self.assertLessEqual(Decimal(package['maximum_schedule_reservation_cny']),r.CAP_CNY)
            self.assertEqual(json.loads(r.PACKAGE.read_text()),package)
            self.assertEqual(r.expected_grant(package)['authorized_calls'],0)
            with self.assertRaises(ValueError):r.require_grant(package,r.expected_grant(package),NOW)
            for row in package['requests'].values():self.assertLessEqual(row['request_bytes'],36000)
    def test_one_smoke_then_fixed_comparison_with_unchanged_source_and_policy(self):
        for stage,total in((1,2),(2,12)):
            client=Client();result,package=execute(client,stage)
            self.assertEqual(result['status'],'COMPLETED_ONE_PASS');self.assertEqual(len(client.calls),total)
            self.assertEqual(Decimal(result['reserved_usd']),r.MAX_SCHEDULE)
            self.assertEqual(Decimal(result['reserved_cny']),r.MAX_SCHEDULE_CNY)
            self.assertEqual(result['currency'],'CNY')
            self.assertTrue(all(a['status']=='ANSWER_ACCEPTED'for a in result['arms']))
            data=exported(result,package)
            self.assertEqual(data['provider_calls'],total);self.assertTrue(data['usage_complete'])
            self.assertNotIn('PRIVATE_REASONING_CANARY',json.dumps(data));self.assertNotIn('hcl_plan',json.dumps(data))
            self.assertEqual(result['remaining_authorized_calls'],0)
            for request in client.calls:
                payload=json.loads(request['messages'][-1]['content'])
                self.assertNotIn('criteria',payload);self.assertNotIn('rubric',payload)
                if request['max_tokens']==8192:self.assertTrue(request['messages'][0]['content'].startswith(r._EXPLICIT_CITATION_FINAL_ANSWER_POLICY))
                self.assertEqual(request['model'],'deepseek-v4-pro');self.assertEqual(request['reasoning_effort'],'high')
    def test_phase1_review_must_reference_full_known_success(self):
        result,package=execute(Client());evidence=exported(result,package)
        self.assertTrue(public.validate_phase1_gate(evidence,stage1_review(evidence)))
        for field,value in(('overall_pass',False),('reviewer_role','IMPLEMENTER'),('final_answer_sha256','f'*64)):
            review=stage1_review(evidence);review[field]=value
            with self.assertRaises(ValueError):public.validate_phase1_gate(evidence,review)
    def test_schema_failures_preserve_exact_final_text_and_do_not_retry(self):
        for stage in(1,2):
            def mutate(value,index,request):
                if request['max_tokens']==8192:value['choices'][0]['message']['content']='{broken final JSON'
            client=Client(mutate);result,package=execute(client,stage);out=exported(result,package)
            self.assertEqual(len(client.calls),2 if stage==1 else 12)
            self.assertEqual(result['status'],'STOPPED_NO_RETRY'if stage==1 else'COMPLETED_ONE_PASS')
            self.assertTrue(all(a['final_text']=='{broken final JSON'for a in out['arms']))
            self.assertTrue(all(a['final_fields']is None for a in out['arms']))
            self.assertNotIn('PRIVATE_REASONING_CANARY',json.dumps(out))
    def test_empty_native_selection_is_retained_not_replaced(self):
        for stage,total in((1,1),(2,8)):
            client=Client(empty=True);result,package=execute(client,stage);out=exported(result,package)
            self.assertEqual(len(client.calls),total)
            self.assertEqual(len(out['arms']),1 if stage==1 else 8)
            self.assertEqual(sum(a['status']=='ANSWER_ACCEPTED'for a in out['arms']),0 if stage==1 else 4)
    def test_unknown_usage_and_transport_stop_and_hold(self):
        for stage in(1,2):
            for unknown in('usage','model','transport'):
                def mutate(value,index,request):
                    if unknown=='usage':value['usage']={}
                    if unknown=='model':value['model']='unknown-model'
                client=Client(mutate)
                if unknown=='transport':client.failure='PRIVATE_ERROR_CANARY'
                result,package=execute(client,stage);out=exported(result,package)
                self.assertEqual(len(client.calls),1);self.assertEqual(result['status'],'STOPPED_NO_RETRY')
                self.assertFalse(out['usage_complete']);self.assertIsNone(out['usage_rated_cny'])
                self.assertNotIn('PRIVATE_ERROR_CANARY',json.dumps(out));self.assertGreater(Decimal(out['reserved_cny']),0)
    def test_finish_length_content_is_preserved_before_transport_validation(self):
        def mutate(value,index,request):
            if request['max_tokens']==8192:
                value['choices'][0]['finish_reason']='length';value['choices'][0]['message']['content']='{"answer":"partial'
        result,package=execute(Client(mutate));out=exported(result,package)
        self.assertEqual(out['arms'][0]['status'],'INCOMPLETE_ANSWER_NO_RETRY')
        self.assertEqual(out['arms'][0]['final_text'],'{"answer":"partial')
        self.assertTrue(out['usage_complete'])
    def test_dynamic_overflow_never_truncates_or_calls_answer(self):
        def large(session,operation,question):return dict(capability=operation['capability'],executed=True,result={'large':'x'*40000},support_claim_ids=[])
        with patch.object(r.UniversalHCL,'_execute',large):
            client=Client();result,package=execute(client)
        self.assertEqual(len(client.calls),1);self.assertEqual(result['arms'][0]['status'],'REQUEST_BOUND_EXCEEDED_NO_TRUNCATION')
    def test_late_timeout_thread_cannot_rewrite_terminal_receipt(self):
        client=Client();original=client.chat.completions.create
        def slow(**kwargs):
            if kwargs['max_tokens']==8192:time.sleep(.06)
            return original(**kwargs)
        client.chat.completions.create=slow
        init=r.OutputLimitPort.__init__
        def fast(self,*args,**kwargs):init(self,*args,**kwargs);self.maximum_wait_seconds=.01
        with patch.object(r.OutputLimitPort,'__init__',fast):result,package=execute(client)
        frozen=copy.deepcopy(result);time.sleep(.08)
        self.assertEqual(result,frozen);self.assertEqual(result['status'],'STOPPED_NO_RETRY')

if __name__=='__main__':unittest.main()
