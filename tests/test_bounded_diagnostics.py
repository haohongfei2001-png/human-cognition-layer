"""Offline authorization, metering, diagnosis and privacy tests; no provider calls."""
from datetime import datetime,timedelta,timezone
from decimal import Decimal
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tests.test_v1_deepseek_metered import FakeClient
from scripts.bounded_diagnostic_port import DiagnosticPort
from scripts import run_bounded_diagnostics as runner
from scripts.bounded_diagnostic_protocol import CAP,MAX_CALLS,CASES,EXPIRES_AT

NOW=datetime(2026,10,2,23,tzinfo=timezone.utc)


class Client(FakeClient):
    timeout=180
    def __init__(self,mutate=None):super().__init__();self.mutate=mutate
    def create(self,**request):
        result=super().create(**request)
        if request['messages'][0]['content']==runner.PLANNER_POLICY:
            result['choices'][0]['message']['content']=json.dumps(dict(task='Bounded synthetic plan',operations=[],limitations=[]))
        if self.mutate:self.mutate(result,len(self.calls),request)
        return result


def execute(client,clock=lambda:NOW):
    package=runner.build_package()
    with tempfile.TemporaryDirectory()as root:
        path=Path(root)/'run'
        value=runner.run(client,package,runner.expected_grant(package),path,clock=clock)
        assert json.loads((path/'receipt.json').read_text())==json.loads(json.dumps(value))
        return value


class BoundedDiagnosticTests(unittest.TestCase):
    def test_baseline_success_selects_4096_and_all_three_full_flows(self):
        client=Client();value=execute(client)
        self.assertEqual(value['status'],'COMPLETED_SYNTHETIC_FUNCTIONAL_DIAGNOSTIC')
        self.assertEqual(value['selected_planning_tokens'],4096)
        self.assertEqual(len(client.calls),7);self.assertEqual(len(value['calls']),7)
        self.assertEqual([r['stage']for r in value['results']][1:],[c['case_id']for c in CASES])
        self.assertEqual(len({r['call_id']for r in value['calls']}),7)
        self.assertEqual(value['budget_state'],'CLOSED_NO_TRANSFER_NO_RETRY')
        self.assertEqual(value['remaining_authorized_calls'],0)
        self.assertLess(Decimal(value['reserved_usd']),CAP)
        for row in value['calls']:
            self.assertEqual(row['request_sha256'],runner.digest(row['request']))
            self.assertEqual(row['request']['model'],'deepseek-v4-pro')
            self.assertEqual(row['request']['thinking'],{'type':'enabled'})
            self.assertEqual(row['request']['reasoning_effort'],'high')
            self.assertEqual(row['response_diagnostics']['finish_reasons'],['stop'])
        self.assertNotIn('HIDDEN_',json.dumps(value))

    def test_only_validated_length_admits_single_one_factor_differential(self):
        def mutate(r,i,q):
            if i==1:
                r['choices'][0]['finish_reason']='length';r['choices'][0]['message']['content']=''
                r['usage'].update(prompt_tokens=100,completion_tokens=4096,total_tokens=4196)
        client=Client(mutate);value=execute(client)
        self.assertEqual(len(client.calls),8);self.assertEqual(value['selected_planning_tokens'],8192)
        first,second=copy.deepcopy(client.calls[:2]);self.assertEqual(first.pop('max_tokens'),4096)
        self.assertEqual(second.pop('max_tokens'),8192);self.assertEqual(first,second)
        self.assertTrue(value['results'][0]['conditional_output_limit_differential_admitted'])
        self.assertEqual(value['calls'][0]['response_diagnostics']['content_kind'],'EMPTY')
        self.assertEqual(value['calls'][0]['reserved_usd'],runner.build_package()['probe_requests']['4096']['reservation_usd'])
        self.assertEqual(sum(Decimal(r['reserved_usd'])for r in value['calls']),Decimal(value['reserved_usd']))
        self.assertNotIn('response_content',value['calls'][0])

    def test_second_length_never_escalates_again(self):
        def mutate(r,i,q):r['choices'][0]['finish_reason']='length'
        client=Client(mutate);value=execute(client)
        self.assertEqual(len(client.calls),2);self.assertEqual(value['status'],'PLANNING_FAILED_NO_FULL_FLOW')

    def test_other_probe_failures_never_retry(self):
        mutations=[lambda r:r.update(model='other-model'),
            lambda r:r['usage'].update(completion_tokens=True),
            lambda r:r['choices'][0].update(finish_reason='content_filter'),
            lambda r:r['choices'][0].update(finish_reason='private-reason-canary'),
            lambda r:r.update(choices=[]),
            lambda r:r['choices'].append(copy.deepcopy(r['choices'][0])),
            lambda r:r['choices'][0]['message'].update(content=''),
            lambda r:r['choices'][0]['message'].update(content='{}'),
            lambda r:r['choices'][0]['message'].update(content=123)]
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                client=Client(lambda r,i,q:mutation(r));value=execute(client)
                self.assertEqual(len(client.calls),1);self.assertEqual(value['remaining_authorized_calls'],0)
                self.assertNotIn('private-reason-canary',json.dumps(value))
        client=Client();client.failure='RAW_EXCEPTION_CANARY';value=execute(client)
        self.assertEqual(len(client.calls),1);self.assertNotIn('RAW_EXCEPTION_CANARY',json.dumps(value))
        self.assertEqual(value['calls'][0]['failure_code'],'PROVIDER_TRANSPORT_FAILURE_NO_RETRY')

    def test_length_with_invalid_usage_does_not_admit_differential(self):
        for counts in (dict(prompt_tokens=1,completion_tokens=-1),dict(prompt_tokens=1,completion_tokens=100000),
                       dict(prompt_tokens=1,completion_tokens=1,total_tokens=3)):
            def mutate(r,i,q):r['choices'][0]['finish_reason']='length';r['usage']=counts
            client=Client(mutate);value=execute(client)
            self.assertEqual(len(client.calls),1);self.assertFalse(value['results'][0]['conditional_output_limit_differential_admitted'])

    def test_plan_schema_rejection_stops_without_prompt_repair(self):
        client=Client(lambda r,i,q:r['choices'][0]['message'].update(content='{}'))
        value=execute(client)
        self.assertEqual(len(client.calls),1);self.assertEqual(value['status'],'PLANNING_SCHEMA_REJECTED_NO_FULL_FLOW')

    def test_full_flow_failure_closes_batch_and_no_replacement_case(self):
        def mutate(r,i,q):
            if i==2:r['choices'][0]['finish_reason']='length'
        client=Client(mutate);value=execute(client)
        self.assertEqual(len(client.calls),2);self.assertEqual(value['status'],'FULL_FLOW_FAILED_NO_RETRY')
        self.assertEqual(len(value['results']),2)

    def test_request_limits_count_utf8_and_never_truncate(self):
        client=Client();port=DiagnosticPort(client,planning_tokens=4096)
        messages=[dict(role='user',content='界'*6000)]
        with self.assertRaisesRegex(Exception,'REQUEST_BOUND_EXCEEDED_NO_TRUNCATION'):port.reservation_usd('planning',messages)
        self.assertEqual(client.calls,[])

    def test_per_call_output_limit_binds_request_reservation_and_response_validation(self):
        for tokens in (4096,8192):
            client=Client(lambda r,i,q:r['usage'].update(prompt_tokens=100,completion_tokens=6000,total_tokens=6100))
            port=DiagnosticPort(client,planning_tokens=tokens);messages=[dict(role='user',content='Return JSON.')]
            reserve=Decimal(port.reservation_usd('planning',messages));request,encoded=port.request('planning',messages)
            self.assertEqual(request['max_tokens'],tokens)
            expected=((2*len(encoded)+2048)*runner.INPUT_RATE+(tokens+32)*runner.OUTPUT_RATE)/1000000
            self.assertEqual(reserve,expected)
            if tokens==4096:
                with self.assertRaisesRegex(Exception,'USAGE_OUTSIDE_FROZEN_BOUND'):port.complete('planning',messages)
            else:self.assertLessEqual(Decimal(port.complete('planning',messages)['actual_usd']),reserve)

    def test_request_mutation_after_reservation_prevents_transport(self):
        client=Client();port=DiagnosticPort(client,planning_tokens=4096);messages=[dict(role='user',content='Return JSON.')]
        port.reservation_usd('planning',messages);port.planning_tokens=8192
        with self.assertRaisesRegex(Exception,'EXACT_REQUEST_MUST_BE_RESERVED_FIRST'):port.complete('planning',messages)
        self.assertEqual(client.calls,[])

    def test_optional_reasoning_counts_are_bounded_and_never_counted_twice(self):
        for count in (5,True,-1,999999,'private-canary'):
            def mutate(r,i,q):
                r['usage']['completion_tokens_details']={'reasoning_tokens':count,'other':'PRIVATE_USAGE_CANARY'}
                r['choices'][0]['message']['reasoning_content']='PRIVATE_REASONING_CANARY'
                r['choices'][0]['message']['refusal']='PRIVATE_REFUSAL_CANARY'
            value=execute(Client(mutate));data=value['calls'][0]['response_diagnostics']
            self.assertEqual('reasoning_tokens'in data,type(count)is int and count==5)
            self.assertNotIn('PRIVATE_',json.dumps(value));self.assertNotIn('private-canary',json.dumps(value))
            actual=(data['usage']['prompt_tokens']*runner.INPUT_RATE+data['usage']['completion_tokens']*runner.OUTPUT_RATE)/1000000
            self.assertEqual(Decimal(value['calls'][0]['actual_usd']),actual)

    def test_prepared_closed_old_enlarged_and_drifted_grants_prevent_calls(self):
        package=runner.build_package();client=Client()
        for mutation in [dict(status='PREPARED_REVIEW_REQUIRED'),dict(status='CLOSED_NO_TRANSFER_NO_RETRY'),
                         dict(authorization_ref='OWNER_APPROVED_2026_10_02_NEW_2_50_18_CALLS'),dict(maximum_calls=13),
                         dict(maximum_usd='1.01'),dict(expires_at='2026-10-04T08:00:00Z'),dict(hcla_budget_transfer=True)]:
            with tempfile.TemporaryDirectory()as root,self.assertRaises(ValueError):
                runner.run(client,package,dict(runner.expected_grant(package),**mutation),Path(root)/'run',clock=lambda:NOW)
        with tempfile.TemporaryDirectory()as root,self.assertRaises(ValueError):
            runner.run(client,dict(package,scheduled_maximum_calls=12),runner.expected_grant(package),Path(root)/'run',clock=lambda:NOW)
        self.assertEqual(client.calls,[])

    def test_expiry_before_launch_and_between_calls_stops(self):
        expiry=datetime.fromisoformat(EXPIRES_AT.replace('Z','+00:00'))
        for now in (expiry,expiry-timedelta(seconds=180),datetime(2026,10,2,23)):
            with self.assertRaises(ValueError):execute(Client(),clock=lambda:now)
        times=iter([NOW,NOW,NOW,expiry])
        client=Client();value=execute(client,clock=lambda:next(times,expiry))
        self.assertEqual(len(client.calls),1);self.assertNotEqual(value['status'],'COMPLETED_SYNTHETIC_FUNCTIONAL_DIAGNOSTIC')

    def test_persistence_failures_prevent_transport_or_further_calls(self):
        original=runner.save
        for failure_at,expected_calls in ((1,0),(2,0),(3,0),(4,1)):
            with self.subTest(failure_at=failure_at):
                count=0;client=Client()
                def fail(path,value):
                    nonlocal count
                    count+=1
                    if count==failure_at:raise OSError('PRIVATE_DISK_CANARY')
                    original(path,value)
                with patch.object(runner,'save',fail):
                    try:value=execute(client)
                    except OSError:pass
                self.assertEqual(len(client.calls),expected_calls)

    def test_ledger_cap_duplicate_request_and_closed_gate(self):
        package=runner.build_package()
        for edge in ('usd','calls','duplicate','closed','deadline'):
            with self.subTest(edge=edge),tempfile.TemporaryDirectory()as root:
                ledger=runner.Ledger(Path(root)/'run',package,runner.expected_grant(package),lambda:NOW)
                client=Client();port=runner.RecordedPort(client,ledger,'test',4096)
                reserve=port.reservation_usd('planning',runner.probe_messages())
                attempt=dict(phase='planning',reserved_usd=reserve,status='RESERVED_BEFORE_CALL',provider_call=False,invocation_status='NOT_INVOKED')
                if edge=='usd':ledger.value['reserved_usd']='1.00'
                elif edge=='calls':ledger.value['calls']=[dict(call_id=str(i))for i in range(MAX_CALLS)]
                elif edge=='closed':ledger.closed=True
                elif edge=='deadline':ledger.started-=1800
                elif edge=='duplicate':
                    port.journal(dict(attempts=[attempt]));port.requests['planning']['messages'][0]['content']+=' changed'
                with self.assertRaises(ValueError):port.journal(dict(attempts=[attempt]))
                self.assertEqual(client.calls,[])

    def test_no_directory_reuse_or_second_send(self):
        package=runner.build_package();client=Client()
        with tempfile.TemporaryDirectory()as root:
            path=Path(root)/'run';runner.run(client,package,runner.expected_grant(package),path,clock=lambda:NOW)
            with self.assertRaises(FileExistsError):runner.run(client,package,runner.expected_grant(package),path,clock=lambda:NOW)
            self.assertEqual(len(client.calls),7)
        with tempfile.TemporaryDirectory()as root:
            ledger=runner.Ledger(Path(root)/'run',package,runner.expected_grant(package),lambda:NOW)
            port=runner.RecordedPort(Client(),ledger,'once',4096);reserve=port.reservation_usd('planning',runner.probe_messages())
            port.journal(dict(attempts=[dict(phase='planning',reserved_usd=reserve,invocation_status='NOT_INVOKED')]))
            ledger.before_send('once','planning')
            with self.assertRaises(ValueError):ledger.before_send('once','planning')

    def test_frozen_one_shot_marker_and_history_precede_execution(self):
        package=runner.build_package();grant=runner.expected_grant(package);parent='a'*40
        marker=dict(schema='hcl-bounded-diagnostic-single-launch-marker-v1',authorization_ref=runner.AUTH,
            package_sha256=runner.digest(package),grant_sha256=runner.digest(grant),executor_commit=parent)
        history=[dict(id=1,event='push',created_at='2026-10-02T23:00:00Z')]
        self.assertTrue(runner.verify_launch(1,1,history,'push',parent,[str(runner.MARKER)],marker,package,grant,NOW))
        for run_id,attempt,event,paths,change in [(2,1,'push',[str(runner.MARKER)],{}),(1,2,'push',[str(runner.MARKER)],{}),
                (1,1,'workflow_dispatch',[str(runner.MARKER)],{}),(1,1,'push',['unrelated'],{}),
                (1,1,'push',[str(runner.MARKER)],dict(executor_commit='b'*40))]:
            with self.assertRaises(ValueError):runner.verify_launch(run_id,attempt,history,event,parent,paths,dict(marker,**change),package,grant,NOW)

    def test_scalar_response_observation_does_not_assert_valid_cost(self):
        client=Client(lambda r,i,q:r['usage'].update(total_tokens=999))
        value=execute(client);row=value['calls'][0]
        self.assertTrue(row['response_diagnostics']['response_returned'])
        self.assertFalse(row['response_diagnostics']['usage_valid'])
        self.assertNotIn('actual_usd',row)

    def test_stage_retains_real_selected_operations_and_complete_sources(self):
        def mutate(r,i,q):
            if q['messages'][0]['content']==runner.PLANNER_POLICY:
                source=json.loads(q['messages'][-1]['content'])
                if source['question'].startswith('If Tavi'):
                    r['choices'][0]['message']['content']=json.dumps(dict(task='One caller conditional',
                        operations=[dict(capability='G05',question=source['question'],source_ids=['choice'],bindings=[])],limitations=[]))
        client=Client(mutate);value=execute(client)
        result=value['results'][-1]['orchestration'];row=result['operations'][0]
        self.assertEqual(row['status'],'G05_SENSITIVITY_PREPARED');self.assertEqual(row['variant_count'],1)
        final=json.loads(client.calls[-1]['messages'][-1]['content'])
        self.assertEqual(final['sources'][0]['text'],CASES[-1]['sources']['choice'])
        self.assertEqual(final['hcl_operations'],result['operations'])
        self.assertFalse(row['source_modified'])

    def test_new_port_rejects_oversized_sdk_timeout_and_late_send(self):
        client=Client();client.timeout=600
        with self.assertRaisesRegex(Exception,'FINITE_SDK_TIMEOUT_REQUIRED'):DiagnosticPort(client,planning_tokens=4096)
        package=runner.build_package();expiry=datetime.fromisoformat(EXPIRES_AT.replace('Z','+00:00'))
        clock=iter([NOW,expiry])
        with tempfile.TemporaryDirectory()as root:
            ledger=runner.Ledger(Path(root)/'run',package,runner.expected_grant(package),lambda:next(clock,expiry))
            client=Client();port=runner.RecordedPort(client,ledger,'late',4096)
            reserve=port.reservation_usd('planning',runner.probe_messages())
            port.journal(dict(attempts=[dict(phase='planning',reserved_usd=reserve,invocation_status='NOT_INVOKED')]))
            with self.assertRaises(ValueError):port.complete('planning',runner.probe_messages())
            self.assertEqual(client.calls,[])

    def test_budget_arithmetic_and_dormant_ciphertext_only_template(self):
        package=runner.build_package()
        self.assertEqual(package['maximum_schedule_reservation_usd'],'0.64610304')
        self.assertEqual(package['maximum_authorized_reservation_usd'],'0.97726464')
        self.assertLessEqual(Decimal(package['maximum_authorized_reservation_usd']),CAP)
        self.assertEqual(package['scheduled_maximum_calls'],8)
        source=runner.TEMPLATE.read_text();self.assertIn('path: bounded-diagnostic.enc.json',source)
        self.assertNotIn('path: bounded-diagnostic-private',source);self.assertNotIn('workflow_dispatch',source)
        self.assertIn('--paginate --slurp',source)
        if runner.WORKFLOW.exists():self.assertEqual(runner.WORKFLOW.read_bytes(),runner.TEMPLATE.read_bytes())
        if runner.GRANT.exists()and json.loads(runner.GRANT.read_text())['status']=='PREPARED_REVIEW_REQUIRED':
            self.assertFalse(runner.WORKFLOW.exists());self.assertFalse(runner.MARKER.exists())


if __name__=='__main__':unittest.main()
