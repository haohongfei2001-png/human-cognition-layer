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
        content=(dict(task='Conceptual analysis',operations=[],limitations=['No supplied source.'])if request['max_tokens']==4096 else dict(answer='A conceptual analysis.',source_citations=[],uncertainty='Unsourced knowledge.',assumptions='No source facts supplied.'))
        return dict(model=MODEL,choices=[dict(finish_reason='stop',message=dict(content=json.dumps(content),reasoning_content='HIDDEN_REASONING_CANARY'))],usage=dict(prompt_tokens=100,completion_tokens=30,reasoning_content='HIDDEN_USAGE_CANARY'))

class MeteredPortTests(unittest.TestCase):
    def test_real_handler_path_fake_sdk_counts_two_calls_and_hides_reasoning(self):
        client=FakeClient();port=DeepSeekMeteredPort(client);journal=[]
        allowance=CallAllowance(2,'1.00','SYNTHETIC_TEST_ONLY',journal=lambda r:journal.append(json.loads(json.dumps(r))))
        result=UniversalHCL().answer('分析人类社会',planner_backend=port,answer_backend=port,allowance=allowance)
        self.assertEqual(result['status'],'ANSWERED_WITH_EXPLICIT_LIMITS');self.assertEqual(len(client.calls),2)
        self.assertEqual(result['provider_calls'],2)  # Fake SDK only, zero network.
        self.assertNotIn('HIDDEN_',json.dumps(result));self.assertNotIn('HIDDEN_',json.dumps(journal))
        self.assertEqual([r['max_tokens']for r in client.calls],[4096,8192])
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
