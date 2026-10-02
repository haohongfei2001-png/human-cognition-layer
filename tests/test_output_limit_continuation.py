"""Offline continuation checks inside the unchanged aggregate owner ceiling."""
from datetime import datetime,timedelta,timezone
from decimal import Decimal
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tests.test_bounded_diagnostics import Client
from scripts import run_output_limit_continuation as runner
from scripts.output_limit_port import OutputLimitPort

NOW=datetime(2026,10,2,23,30,tzinfo=timezone.utc)


def execute(client,clock=lambda:NOW):
    package=runner.build_package()
    with tempfile.TemporaryDirectory()as root:
        path=Path(root)/'run';r=runner.run(client,package,runner.expected_grant(package),path,clock=clock)
        assert json.loads((path/'receipt.json').read_text())==json.loads(json.dumps(r))
        return r


class OutputLimitTests(unittest.TestCase):
    def test_four_call_success_imports_previous_full_holds_without_recycling(self):
        client=Client();r=execute(client)
        self.assertEqual(r['status'],'COMPLETED_OUTPUT_LIMIT_FUNCTIONAL_DIAGNOSTIC');self.assertEqual(len(client.calls),4)
        self.assertEqual(r['aggregate_calls'],8);self.assertEqual(r['aggregate_remaining_calls'],4)
        self.assertEqual(Decimal(r['aggregate_reserved_usd']),runner.PRIOR_HELD+sum(Decimal(c['reserved_usd'])for c in r['calls']))
        self.assertEqual(Decimal(r['aggregate_remaining_usd']),Decimal('1')-Decimal(r['aggregate_reserved_usd']))
        self.assertEqual(r['prior_charges']['receipt_sha256'],runner.PRIOR_RECEIPT_SHA)
        self.assertEqual(r['remaining_authorized_calls'],0)
        self.assertNotIn('HIDDEN_',json.dumps(r))
        sent=copy.deepcopy(client.calls[0]);sent['thinking']=sent.pop('extra_body')['thinking'];sent['max_tokens']=4096
        self.assertEqual(sent,runner.frozen_request())

    def test_validated_8192_length_allows_only_one_16384_source_differential(self):
        def mutate(r,i,q):
            if i==1:
                r['choices'][0]['finish_reason']='length';r['choices'][0]['message']['content']=''
                r['usage']=dict(prompt_tokens=2400,completion_tokens=8192,total_tokens=10592,
                    completion_tokens_details={'reasoning_tokens':8192})
        client=Client(mutate);r=execute(client)
        self.assertEqual(len(client.calls),5);self.assertEqual(r['aggregate_calls'],9)
        self.assertEqual(r['selected_planning_tokens'],16384)
        a,b=copy.deepcopy(client.calls[:2]);self.assertEqual(a.pop('max_tokens'),8192)
        self.assertEqual(b.pop('max_tokens'),16384);self.assertEqual(a,b)
        self.assertEqual([q['max_tokens']for q in client.calls],[8192,16384,8192,16384,8192])
        self.assertTrue(r['results'][0]['conditional_output_limit_differential_admitted'])

    def test_16384_length_stops_and_validated_usage_is_not_lost_or_double_counted(self):
        def mutate(r,i,q):
            tokens=q['max_tokens'];r['choices'][0]['finish_reason']='length';r['choices'][0]['message']['content']=''
            r['usage']=dict(prompt_tokens=2400,completion_tokens=tokens,total_tokens=2400+tokens,
                completion_tokens_details={'reasoning_tokens':tokens})
        client=Client(mutate);r=execute(client)
        self.assertEqual(len(client.calls),2);self.assertEqual(r['status'],'SOURCE_FLOW_FAILED_NO_FURTHER_CALL')
        row=r['calls'][-1];self.assertEqual(row['usage']['completion_tokens'],16384)
        self.assertEqual(row['response_diagnostics']['reasoning_tokens'],16384)
        self.assertEqual(row['invocation_status'],'RESPONSE_RETURNED_REJECTED')
        self.assertEqual(Decimal(row['actual_usd']),(Decimal(2400)*Decimal('1.32')+Decimal(16384)*Decimal('3.96'))/1000000)
        self.assertGreater(Decimal(row['reserved_usd']),Decimal(row['actual_usd']))

    def test_full_answer_or_g05_failure_cannot_admit_differential(self):
        for call in (2,3):
            def mutate(r,i,q):
                if i==call:r['choices'][0]['finish_reason']='length'
            client=Client(mutate);r=execute(client)
            self.assertEqual(len(client.calls),call)
            self.assertNotIn('source_flow_16384',[x['stage']for x in r['results']])

    def test_transport_invalid_usage_and_schema_failures_have_no_retry(self):
        changes=[lambda r:r.update(model='different'),lambda r:r['usage'].update(total_tokens=999),
            lambda r:r['choices'][0]['message'].update(content='{}'),lambda r:r['choices'][0].update(finish_reason='content_filter')]
        for change in changes:
            client=Client(lambda r,i,q:change(r));out=execute(client);self.assertEqual(len(client.calls),1)
            self.assertEqual(out['status'],'SOURCE_FLOW_FAILED_NO_FURTHER_CALL')
        client=Client();client.failure='PRIVATE_ERROR_CANARY';out=execute(client)
        self.assertEqual(len(client.calls),1);self.assertNotIn('PRIVATE_ERROR_CANARY',json.dumps(out))

    def test_past_charges_closed_grant_and_original_request_are_immutable(self):
        original=Path.read_text
        for path,modify in [(runner.PRIOR_CLOSURE,lambda r:r.update(calls=0)),
                (runner.PRIOR_CLOSURE,lambda r:r.update(reserved_usd='0.05790444')),
                (runner.PRIOR_GRANT,lambda r:r.update(status='READY')),
                (runner.FROZEN_REQUEST,lambda r:r.update(max_tokens=8192))]:
            def read(p,*args,**kwargs):
                data=original(p,*args,**kwargs)
                if p==path:
                    value=json.loads(data);modify(value);return json.dumps(value)
                return data
            with patch.object(Path,'read_text',read),self.assertRaises(ValueError):runner.build_package()

    def test_aggregate_and_subrun_caps_block_before_transport(self):
        package=runner.build_package()
        for edge in ('dollars','subrun_calls','aggregate_calls'):
            with self.subTest(edge=edge),tempfile.TemporaryDirectory()as root:
                ledger=runner.Ledger(Path(root)/'run',package,runner.expected_grant(package),lambda:NOW)
                if edge=='dollars':ledger.value['reserved_usd']='0.82452712'
                else:ledger.value['calls']=[dict(call_id=str(i))for i in range(5 if edge=='subrun_calls'else 8)]
                client=Client();port=runner.RecordedPort(client,ledger,'new',8192)
                reserve=port.reservation_usd('planning',runner.frozen_request()['messages'])
                with self.assertRaises(ValueError):port.journal(dict(attempts=[dict(phase='planning',reserved_usd=reserve,invocation_status='NOT_INVOKED')]))
                self.assertEqual(client.calls,[])

    def test_prior_import_cannot_be_removed_from_new_grant(self):
        p=runner.build_package();client=Client()
        for change in (dict(prior_calls=0),dict(prior_reserved_usd='0'),dict(aggregate_maximum_usd='2'),
                       dict(aggregate_maximum_calls=16),dict(subrun_maximum_calls=8),dict(status='PREPARED_REVIEW_REQUIRED')):
            with tempfile.TemporaryDirectory()as root,self.assertRaises(ValueError):
                runner.run(client,p,dict(runner.expected_grant(p),**change),Path(root)/'run',clock=lambda:NOW)
        self.assertEqual(client.calls,[])

    def test_output_request_and_response_use_same_declared_16384_bound(self):
        client=Client(lambda r,i,q:r['usage'].update(prompt_tokens=100,completion_tokens=16000,total_tokens=16100))
        port=OutputLimitPort(client,planning_tokens=16384);messages=runner.frozen_request()['messages']
        reserve=Decimal(port.reservation_usd('planning',messages));result=port.complete('planning',messages)
        self.assertEqual(result['usage']['completion_tokens'],16000);self.assertLessEqual(Decimal(result['actual_usd']),reserve)
        port=OutputLimitPort(Client(),planning_tokens=16384)
        with self.assertRaisesRegex(Exception,'REQUEST_BOUND_EXCEEDED'):port.reservation_usd('planning',[dict(role='user',content='界'*12000)])
        with self.assertRaises(ValueError):OutputLimitPort(Client(),planning_tokens=32768)

    def test_real_g05_stage_keeps_source_and_caller_condition(self):
        def mutate(r,i,q):
            if q['messages'][0]['content']==runner.previous.PLANNER_POLICY:
                data=json.loads(q['messages'][-1]['content'])
                if data['question'].startswith('If Tavi'):
                    r['choices'][0]['message']['content']=json.dumps(dict(task='Conditional source analysis',operations=[dict(
                        capability='G05',question=data['question'],source_ids=['choice'],bindings=[])],limitations=[]))
        r=execute(Client(mutate));op=r['results'][-1]['orchestration']['operations'][0]
        self.assertEqual(op['status'],'G05_SENSITIVITY_PREPARED');self.assertEqual(op['variant_count'],1)
        self.assertEqual(op['request_provenance']['authority'],'ANALYSIS_CONDITION_NOT_WORLD_EVIDENCE')

    def test_complete_c01_payload_fits_new_bound_without_truncation(self):
        def mutate(r,i,q):
            if q['messages'][0]['content']==runner.previous.PLANNER_POLICY:
                data=json.loads(q['messages'][-1]['content'])
                if data['question']==runner.CASES[1]['question']:
                    r['choices'][0]['message']['content']=json.dumps(dict(task='Source-local goals',operations=[dict(
                        capability='C01',question="What are Rina's goals and plans?",source_ids=['meeting'],bindings=[])],limitations=[]))
        client=Client(mutate);r=execute(client)
        self.assertEqual(r['status'],'COMPLETED_OUTPUT_LIMIT_FUNCTIONAL_DIAGNOSTIC')
        row=[c for c in r['calls']if c['call_id']=='source_flow_8192:answer'][0]
        size=len(json.dumps(row['request'],ensure_ascii=False,sort_keys=True,separators=(',',':')).encode())
        self.assertGreater(size,18000);self.assertLessEqual(size,36000)
        final=json.loads(row['request']['messages'][-1]['content'])
        self.assertEqual(final['sources'][0]['text'],runner.CASES[1]['sources']['meeting'])
        self.assertTrue(final['hcl_operations'][0]['checked_treatment_present'])

    def test_combined_payload_over_36k_stops_without_truncation_or_answer_call(self):
        def mutate(r,i,q):
            if i==1:
                op=dict(capability='C01',question="What are Rina's goals and plans?",source_ids=['meeting'],bindings=[])
                r['choices'][0]['message']['content']=json.dumps(dict(task='Repeated operations',operations=[op,op,op],limitations=[]))
        client=Client(mutate);r=execute(client)
        self.assertEqual(len(client.calls),1);self.assertEqual(r['status'],'SOURCE_FLOW_FAILED_NO_FURTHER_CALL')
        result=r['results'][0]['orchestration'];self.assertEqual(len(result['operations']),3)
        self.assertEqual(json.loads(result['actual_final_messages'][-1]['content'])['sources'][0]['text'],runner.CASES[1]['sources']['meeting'])

    def test_disk_failure_expiry_and_repeated_output_directory_stop(self):
        expiry=datetime.fromisoformat(runner.EXPIRES_AT.replace('Z','+00:00'))
        with self.assertRaises(ValueError):execute(Client(),clock=lambda:expiry-timedelta(seconds=180))
        original=runner.previous.save;count=0;client=Client()
        def fail(path,value):
            nonlocal count
            count+=1
            if count==3:raise OSError('PRIVATE_DISK_CANARY')
            original(path,value)
        with patch.object(runner.previous,'save',fail):
            out=execute(client)
        self.assertEqual(client.calls,[]);self.assertNotIn('PRIVATE_DISK_CANARY',json.dumps(out))
        p=runner.build_package();client=Client()
        with tempfile.TemporaryDirectory()as root:
            d=Path(root)/'run';runner.run(client,p,runner.expected_grant(p),d,clock=lambda:NOW)
            with self.assertRaises(FileExistsError):runner.run(client,p,runner.expected_grant(p),d,clock=lambda:NOW)
            self.assertEqual(len(client.calls),4)

    def test_invoked_same_identity_cannot_be_rearmed_or_undercharged(self):
        p=runner.build_package()
        with tempfile.TemporaryDirectory()as root:
            ledger=runner.Ledger(Path(root)/'run',p,runner.expected_grant(p),lambda:NOW)
            client=Client();port=runner.RecordedPort(client,ledger,'same_stage',8192)
            reserve=port.reservation_usd('planning',runner.frozen_request()['messages'])
            attempt=dict(phase='planning',reserved_usd=reserve,status='RESERVED_BEFORE_CALL',invocation_status='NOT_INVOKED')
            port.journal(dict(attempts=[attempt]));port.complete('planning',runner.frozen_request()['messages'])
            self.assertEqual(len(client.calls),1);held=ledger.value['aggregate_reserved_usd']
            with self.assertRaisesRegex(ValueError,'CANNOT_BE_REARMED'):port.journal(dict(attempts=[attempt]))
            self.assertEqual(len(client.calls),1);self.assertEqual(ledger.value['aggregate_reserved_usd'],held)
            self.assertEqual(ledger.value['aggregate_calls'],5)

    def test_single_marker_launch_and_caps_math(self):
        p=runner.build_package();g=runner.expected_grant(p);parent='a'*40
        marker=dict(schema='hcl-output-limit-single-launch-marker-v1',authorization_ref=runner.AUTH,
            package_sha256=runner.digest(p),grant_sha256=runner.digest(g),executor_commit=parent)
        history=[dict(id=1,event='push',created_at='2026-10-02T23:30:00Z')]
        self.assertTrue(runner.verify_launch(1,1,history,'push',parent,[str(runner.MARKER)],marker,p,g,NOW))
        for rid,attempt in ((2,1),(1,2)):
            with self.assertRaises(ValueError):runner.verify_launch(rid,attempt,history,'push',parent,[str(runner.MARKER)],marker,p,g,NOW)
        self.assertEqual(p['remaining_campaign_calls'],8);self.assertEqual(p['remaining_campaign_usd'],'0.82452712')
        self.assertEqual(p['subrun_worst_reservation_usd'],'0.71643264')
        self.assertEqual(p['aggregate_worst_reservation_usd'],'0.89190552')
        self.assertLess(Decimal(p['aggregate_worst_reservation_usd']),Decimal('1'))
        if runner.GRANT.exists()and json.loads(runner.GRANT.read_text())['status']=='PREPARED_REVIEW_REQUIRED':
            self.assertFalse(runner.WORKFLOW.exists());self.assertFalse(runner.MARKER.exists())


if __name__=='__main__':unittest.main()
