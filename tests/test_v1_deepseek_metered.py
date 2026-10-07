import json
import unittest
from types import SimpleNamespace
from hcl.cognition.deepseek_metered import DeepSeekMeteredPort,MeteredPortError,MODEL
from hcl.cognition import UniversalHCL,CallAllowance

class FakeClient:
    max_retries=0;base_url='https://api.deepseek.com';timeout=600
    def __init__(self):self.calls=[];self.chat=SimpleNamespace(completions=SimpleNamespace(create=self.create));self.failure=None
    def create(self,**request):
        self.calls.append(request)
        if self.failure:raise RuntimeError(self.failure)
        content=(dict(task='Conceptual analysis',operations=[],limitations=['No supplied source.'])if request['max_tokens']==16384 else dict(answer='A conceptual analysis.',source_citations=[],uncertainty='Unsourced knowledge.',assumptions='No source facts supplied.'))
        return dict(model=MODEL,choices=[dict(finish_reason='stop',message=dict(content=json.dumps(content),reasoning_content='HIDDEN_REASONING_CANARY'))],usage=dict(prompt_tokens=100,completion_tokens=30,reasoning_content='HIDDEN_USAGE_CANARY'))

class MeteredPortTests(unittest.TestCase):
    def test_real_handler_path_fake_sdk_counts_two_calls_and_hides_reasoning(self):
        class NativePlanClient(FakeClient):
            def create(self,**request):
                value=super().create(**request)
                if request['max_tokens']==16384:
                    value['choices'][0]['message']['content']=json.dumps(dict(task='Prepare caller rule',operations=[dict(capability='G01',question='Prepare caller rule.',source_ids=[],bindings=[])],limitations=[]))
                return value
        client=NativePlanClient();port=DeepSeekMeteredPort(client);journal=[]
        allowance=CallAllowance(2,'1.00','SYNTHETIC_TEST_ONLY',journal=lambda r:journal.append(json.loads(json.dumps(r))))
        result=UniversalHCL().answer('For this analysis, responsibility requires control.',planner_backend=port,answer_backend=port,allowance=allowance)
        self.assertEqual(result['status'],'ANSWERED_WITH_EXPLICIT_LIMITS');self.assertEqual(len(client.calls),2)
        self.assertEqual(result['provider_calls'],2)  # Fake SDK only, zero network.
        self.assertNotIn('HIDDEN_',json.dumps(result));self.assertNotIn('HIDDEN_',json.dumps(journal))
        self.assertEqual([r['max_tokens']for r in client.calls],[16384,8192])
        self.assertTrue(all(r['model']==MODEL and r['extra_body']['thinking']['type']=='enabled'for r in client.calls))

    def test_no_retry_or_unbounded_client_is_admitted(self):
        for changes in [dict(max_retries=1),dict(base_url='https://elsewhere.example'),dict(timeout=None)]:
            client=FakeClient()
            for key,value in changes.items():setattr(client,key,value)
            with self.assertRaises(MeteredPortError):DeepSeekMeteredPort(client)
            self.assertEqual(client.calls,[])

    def test_request_mutation_after_quote_is_rejected_before_call(self):
        client=FakeClient();port=DeepSeekMeteredPort(client);messages=[dict(role='user',content='First question')]
        port.reservation_usd('planning',messages);messages[0]['content']='Different question'
        with self.assertRaises(MeteredPortError):port.complete('planning',messages)
        self.assertEqual(client.calls,[])

    def test_request_overflow_fails_without_truncation(self):
        client=FakeClient();port=DeepSeekMeteredPort(client)
        with self.assertRaises(MeteredPortError):port.reservation_usd('answer',[dict(role='user',content='x'*36000)])
        self.assertEqual(client.calls,[])

    def test_unknown_transport_closes_allowance_and_reserves_spend(self):
        client=FakeClient();client.failure='PRIVATE_PROVIDER_BODY';port=DeepSeekMeteredPort(client)
        allowance=CallAllowance(2,'1.00','TEST',journal=lambda r:None)
        result=UniversalHCL().answer('Discuss cooperation.',planner_backend=port,answer_backend=port,allowance=allowance)
        self.assertEqual(len(client.calls),1);self.assertTrue(allowance.closed)
        self.assertNotIn('PRIVATE_PROVIDER_BODY',json.dumps(result));self.assertGreater(float(result['reserved_usd']),0)
        self.assertEqual(result['provider_attempts'][0]['failure_code'],'PROVIDER_TRANSPORT_FAILURE_NO_RETRY')

    def test_zero_and_inconsistent_usage_are_not_free_success(self):
        for usage in [dict(prompt_tokens=0,completion_tokens=0),dict(prompt_tokens=100,completion_tokens=30,total_tokens=1)]:
            class InvalidUsage(FakeClient):
                def create(self,**request):
                    value=super().create(**request);value['usage']=usage;return value
            client=InvalidUsage();port=DeepSeekMeteredPort(client)
            allowance=CallAllowance(2,'1.00','TEST',journal=lambda r:None)
            result=UniversalHCL().answer('Discuss trust.',planner_backend=port,answer_backend=port,allowance=allowance)
            self.assertEqual(result['status'],'ORCHESTRATION_UNAVAILABLE_OR_FAILED');self.assertTrue(allowance.closed)
            self.assertGreater(float(result['reserved_usd']),0);self.assertNotIn('actual_usd',result['provider_attempts'][0])

    def test_sdk_handoff_has_independent_quoted_snapshot(self):
        messages=[dict(role='user',content='Original task')]
        class Mutator(FakeClient):
            def create(self,**request):
                messages[0]['content']='UNQUOTED_MUTATION';return super().create(**request)
        client=Mutator();port=DeepSeekMeteredPort(client)
        port.reservation_usd('planning',messages);port.complete('planning',messages)
        self.assertEqual(client.calls[0]['messages'][0]['content'],'Original task')

    def test_absolute_wait_timeout_retains_unknown_and_closes_port(self):
        import threading
        release=threading.Event()
        class Hanging(FakeClient):
            def create(self,**request):release.wait(timeout=1);return super().create(**request)
        client=Hanging();port=DeepSeekMeteredPort(client,maximum_wait_seconds=.01)
        allowance=CallAllowance(2,'1.00','TEST',journal=lambda r:None)
        try:
            result=UniversalHCL().answer('Discuss trust.',planner_backend=port,answer_backend=port,allowance=allowance)
            self.assertTrue(allowance.closed);self.assertEqual(result['status'],'ORCHESTRATION_UNAVAILABLE_OR_FAILED')
            self.assertGreater(float(result['reserved_usd']),0)
            with self.assertRaises(MeteredPortError):port.reservation_usd('planning',[dict(role='user',content='Retry')])
        finally:release.set()

    def test_fixed_failure_codes_survive_without_provider_bodies(self):
        from hcl.cognition.deepseek_metered import safe_metered_failure_code
        for code in ('PROVIDER_TRANSPORT_FAILURE_NO_RETRY','NUMERIC_USAGE_REQUIRED','INCOMPLETE_ANSWER_NO_RETRY'):
            class SafeFailure(DeepSeekMeteredPort):
                def complete(self,phase,messages):raise MeteredPortError(code)
            port=SafeFailure(FakeClient());journal=[]
            a=CallAllowance(2,'1','TEST',journal=lambda r:journal.append(json.loads(json.dumps(r))))
            result=UniversalHCL().answer('Discuss cooperation.',planner_backend=port,answer_backend=port,allowance=a)
            self.assertEqual(result['provider_attempts'][0]['failure_code'],code)
            self.assertEqual(journal[-1]['attempts'][0]['failure_code'],code)
            self.assertTrue(a.closed);self.assertGreater(float(result['reserved_usd']),0)
        class Subclass(MeteredPortError):pass
        for error in (MeteredPortError('PRIVATE_CANARY'),RuntimeError('PROVIDER_TRANSPORT_FAILURE_NO_RETRY'),Subclass('NUMERIC_USAGE_REQUIRED'),MeteredPortError('NUMERIC_USAGE_REQUIRED','PRIVATE_CANARY')):
            self.assertEqual(safe_metered_failure_code(error),'METERED_BACKEND_OR_JOURNAL_FAILED')

    def test_rejected_completion_preserves_safe_status_and_validated_cost(self):
        variants=[([],[],0),([dict(finish_reason='length',message={'content':'PRIVATE_OUTPUT','reasoning_content':'PRIVATE_REASONING'})],['length'],1),([dict(finish_reason='stop'),dict(finish_reason='content_filter')],['stop','content_filter'],2),([dict(finish_reason='PRIVATE_ERROR_BODY')],['OTHER_OR_MISSING'],1)]
        for choices,reasons,count in variants:
            class Rejected(FakeClient):
                def create(self,**request):
                    value=super().create(**request);value['choices']=choices;return value
            client=Rejected();port=DeepSeekMeteredPort(client);saved=[]
            a=CallAllowance(2,'1','TEST',journal=lambda r:saved.append(json.loads(json.dumps(r))))
            r=UniversalHCL().answer('Discuss trust.',planner_backend=port,answer_backend=port,allowance=a)
            row=r['provider_attempts'][0]
            self.assertEqual(row['choice_count'],count);self.assertEqual(row['finish_reasons'],reasons)
            self.assertEqual(row['actual_usd'],'0.0002508');self.assertEqual(row['invocation_status'],'RESPONSE_RETURNED_REJECTED')
            self.assertEqual(row['usage'],dict(prompt_tokens=100,completion_tokens=30))
            self.assertTrue(a.closed);self.assertEqual(len(client.calls),1);self.assertNotIn('PRIVATE_',json.dumps(r));self.assertNotIn('PRIVATE_',json.dumps(saved))
    def test_failure_metadata_allowlist_rejects_spoofed_usage_and_text(self):
        from hcl.cognition.deepseek_metered import safe_metered_failure_details
        e=MeteredPortError('INCOMPLETE_ANSWER_NO_RETRY');e.diagnostics=dict(choice_count='PRIVATE_TEXT',finish_reasons=['PRIVATE_BODY'],usage={'prompt_tokens':1,'completion_tokens':1,'reasoning_content':'PRIVATE_REASONING'})
        self.assertEqual(safe_metered_failure_details(e,'1'),{'failure_code':'INCOMPLETE_ANSWER_NO_RETRY'})
        e.diagnostics=dict(usage={'prompt_tokens':100,'completion_tokens':30})
        self.assertNotIn('actual_usd',safe_metered_failure_details(e,'0.000001'))

    def test_journal_exception_cannot_spoof_returned_response_usage(self):
        error=MeteredPortError('INCOMPLETE_ANSWER_NO_RETRY');error.diagnostics=dict(choice_count=1,finish_reasons=['length'],usage=dict(prompt_tokens=100,completion_tokens=30))
        def fail(_):raise error
        client=FakeClient();port=DeepSeekMeteredPort(client);a=CallAllowance(2,'1','TEST',journal=fail)
        r=UniversalHCL().answer('Discuss trust.',planner_backend=port,answer_backend=port,allowance=a)
        row=r['provider_attempts'][0]
        self.assertEqual(client.calls,[]);self.assertFalse(row['provider_call']);self.assertEqual(row['invocation_status'],'NOT_INVOKED')
        self.assertNotIn('actual_usd',row);self.assertNotIn('usage',row);self.assertNotIn('finish_reasons',row)
