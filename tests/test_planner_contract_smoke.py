"""Offline two-call smoke admission and observation tests; no model invocations."""
from datetime import datetime,timedelta,timezone
from decimal import Decimal
import copy,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from tests.test_bounded_diagnostics import Client
from scripts import run_planner_contract_smoke as runner

NOW=datetime(2026,10,3,1,tzinfo=timezone.utc)


def execute(client):
    p=runner.build_package()
    with tempfile.TemporaryDirectory()as root:
        d=Path(root)/'run';r=runner.run(client,p,runner.expected_grant(p),d,clock=lambda:NOW)
        assert json.loads((d/'receipt.json').read_text())==json.loads(json.dumps(r))
        return r


class ContractSmokeTests(unittest.TestCase):
    def test_new_complete_request_and_reservation_are_fixed(self):
        p=runner.build_package()
        self.assertEqual(p['complete_planning_request_utf8_bytes'],19599)
        self.assertEqual(p['planning_reservation_usd'],'0.11945208')
        self.assertEqual(Decimal(p['maximum_answer_reservation_usd']),Decimal('0.13031040'))
        self.assertEqual(p['maximum_new_reservation_usd'],'0.24976248')
        self.assertEqual(p['maximum_aggregate_reservation_usd'],'0.76504824')
        self.assertEqual(p['request_sha256'],runner.REQUEST_SHA)
        self.assertEqual(p['prior_charges']['calls'],9)
        self.assertEqual(p['prior_charges']['reserved_usd'],'0.51528576')

    def test_negative_selection_is_recorded_without_forcing_g05_or_retrying(self):
        client=Client();r=execute(client)
        self.assertEqual(len(client.calls),2);self.assertEqual(r['aggregate_calls'],11)
        self.assertEqual(r['selected_capabilities'],[]);self.assertFalse(r['g05_preparation_executed'])
        self.assertEqual(r['status'],'COMPLETED_SELECTION_RECORDED_NO_RETRY')
        self.assertEqual(r['aggregate_remaining_calls'],1);self.assertEqual(r['remaining_authorized_calls'],0)
        self.assertEqual(Decimal(r['aggregate_reserved_usd']),runner.PRIOR_HELD+sum(Decimal(c['reserved_usd'])for c in r['calls']))
        self.assertFalse(r['efficacy_verified']);self.assertNotIn('HIDDEN_',json.dumps(r))
        first=copy.deepcopy(client.calls[0]);first['thinking']=first.pop('extra_body')['thinking']
        self.assertEqual(first,runner.frozen_request());self.assertEqual([c['max_tokens']for c in client.calls],[16384,8192])

    def test_actual_selected_g05_preparation_and_original_authority_reach_answer(self):
        def mutate(r,i,q):
            if i==1:
                payload=json.loads(q['messages'][-1]['content'])
                r['choices'][0]['message']['content']=json.dumps(dict(task='Source-local conditional',operations=[dict(
                    capability='G05',question='An operation interpretation cannot adopt a premise.',source_ids=['choice'],bindings=[])],limitations=[]))
        client=Client(mutate);r=execute(client)
        self.assertTrue(r['g05_preparation_executed']);self.assertEqual(r['executed_capabilities'],['G05'])
        op=r['orchestration']['operations'][0];self.assertEqual(op['variant_count'],1)
        self.assertFalse(op['result']['source_modified']);self.assertEqual(op['request_provenance']['authority'],'ANALYSIS_CONDITION_NOT_WORLD_EVIDENCE')
        final=json.loads(client.calls[1]['messages'][-1]['content']);original=json.loads(runner.frozen_request()['messages'][-1]['content'])
        self.assertEqual(final['question'],original['question'])
        self.assertEqual(final['sources'][0]['text'],original['sources'][0]['text'])

    def test_malformed_plan_length_or_transport_stops_without_differential(self):
        changes=[lambda r:r['choices'][0]['message'].update(content='{}'),lambda r:r['choices'][0].update(finish_reason='length'),
                 lambda r:r.update(model='unapproved-model')]
        for change in changes:
            client=Client(lambda r,i,q:change(r));out=execute(client)
            self.assertEqual(len(client.calls),1);self.assertEqual(out['status'],'FAILED_OR_UNSUPPORTED_NO_RETRY')
        client=Client();client.failure='PRIVATE_ERROR_CANARY';out=execute(client)
        self.assertEqual(len(client.calls),1);self.assertNotIn('PRIVATE_ERROR_CANARY',json.dumps(out))

    def test_incomplete_16384_usage_is_preserved_once_without_refund(self):
        def mutate(r,i,q):
            r['choices'][0]['finish_reason']='length';r['choices'][0]['message']['content']=''
            r['usage']=dict(prompt_tokens=5000,completion_tokens=16384,total_tokens=21384,
                completion_tokens_details={'reasoning_tokens':16384})
        client=Client(mutate);r=execute(client);row=r['calls'][0]
        self.assertEqual(len(client.calls),1);self.assertEqual(row['usage']['completion_tokens'],16384)
        self.assertEqual(Decimal(row['actual_usd']),(Decimal(5000)*Decimal('1.32')+Decimal(16384)*Decimal('3.96'))/1000000)
        self.assertEqual(Decimal(r['aggregate_reserved_usd']),runner.PRIOR_HELD+Decimal(row['reserved_usd']))
        self.assertGreater(Decimal(row['reserved_usd']),Decimal(row['actual_usd']))

    def test_valid_unavailable_selection_remains_explicit_without_another_plan(self):
        def mutate(r,i,q):
            if i==1:r['choices'][0]['message']['content']=json.dumps(dict(task='Explicit limitation',operations=[dict(capability='E05',question='Describe limits.',source_ids=['choice'],bindings=[])],limitations=[]))
        client=Client(mutate);r=execute(client)
        self.assertEqual(len(client.calls),2);self.assertEqual(r['selected_capabilities'],['E05'])
        self.assertEqual(r['executed_capabilities'],[]);self.assertFalse(r['g05_preparation_executed'])
        self.assertEqual(r['orchestration']['operations'][0]['status'],'RETAINED_IMPLEMENTATION_REQUIRES_ENTRY_ADAPTER')

    def test_complete_oversized_answer_input_stops_before_transport_without_truncation(self):
        def mutate(r,i,q):
            if i==1:r['choices'][0]['message']['content']=json.dumps(dict(task='Over-budget typed plan',operations=[dict(capability='G04',question='界'*8000,source_ids=['choice'],bindings=[])for _ in range(3)],limitations=[]),ensure_ascii=False)
        client=Client(mutate);r=execute(client)
        self.assertEqual(len(client.calls),1);self.assertEqual(r['status'],'FAILED_OR_UNSUPPORTED_NO_RETRY')
        final=json.loads(r['orchestration']['actual_final_messages'][-1]['content'])
        self.assertEqual(len(final['hcl_plan']['operations']),3)
        self.assertTrue(all(o['question']=='界'*8000 for o in final['hcl_plan']['operations']))

    def test_prior_receipt_accounting_and_current_request_tampering_reject(self):
        original=Path.read_text
        for target,change in ((runner.PRIOR,lambda r:r.update(aggregate_calls=5)),(runner.PRIOR,lambda r:r.update(aggregate_reserved_usd='0.17653680')),
                              (runner.PRIOR_GRANT,lambda r:r.update(status='READY')),(runner.REQUEST,lambda r:r.update(max_tokens=8192))):
            def read(p,*a,**kw):
                value=original(p,*a,**kw)
                if p==target:
                    r=json.loads(value);change(r);return json.dumps(r)
                return value
            with patch.object(Path,'read_text',read),self.assertRaises(ValueError):runner.build_package()

    def test_grant_cannot_reset_aggregate_or_expand_calls(self):
        p=runner.build_package();client=Client()
        for change in (dict(prior_calls=0),dict(prior_reserved_usd='0'),dict(aggregate_maximum_calls=14),
                       dict(aggregate_maximum_usd='2.00'),dict(subrun_maximum_calls=3),dict(status='PREPARED_REVIEW_REQUIRED')):
            with tempfile.TemporaryDirectory()as root,self.assertRaises(ValueError):
                runner.run(client,p,dict(runner.expected_grant(p),**change),Path(root)/'run',clock=lambda:NOW)
        self.assertEqual(client.calls,[])

    def test_duplicate_rearming_caps_and_changed_request_prevent_transport(self):
        p=runner.build_package()
        for edge in ('rearm','new_cap','aggregate_cap','request','calls'):
            with self.subTest(edge=edge),tempfile.TemporaryDirectory()as root:
                ledger=runner.Ledger(Path(root)/'run',p,runner.expected_grant(p),lambda:NOW);client=Client()
                port=runner.RecordedPort(client,ledger,'contract_smoke',16384);messages=runner.frozen_request()['messages']
                reserve=port.reservation_usd('planning',messages)
                attempt=dict(phase='planning',reserved_usd=reserve,status='RESERVED_BEFORE_CALL',invocation_status='NOT_INVOKED')
                if edge=='rearm':port.journal(dict(attempts=[attempt]));port.complete('planning',messages)
                elif edge=='new_cap':ledger.value['reserved_usd']=p['maximum_new_reservation_usd']
                elif edge=='aggregate_cap':ledger.value['reserved_usd']='0.48471424'
                elif edge=='request':port.requests['planning']['messages'][0]['content']+=' changed'
                else:ledger.value['calls']=[dict(phase='x'),dict(phase='y')]
                with self.assertRaises(ValueError):port.journal(dict(attempts=[attempt]))
                self.assertEqual(len(client.calls),1 if edge=='rearm'else 0)

    def test_expiry_persistence_and_directory_reuse_stop(self):
        p=runner.build_package();expiry=datetime.fromisoformat(runner.EXPIRES_AT.replace('Z','+00:00'));client=Client()
        with tempfile.TemporaryDirectory()as root,self.assertRaises(ValueError):
            runner.run(client,p,runner.expected_grant(p),Path(root)/'run',clock=lambda:expiry-timedelta(seconds=180))
        original=runner.common.save;count=0
        def fail(path,value):
            nonlocal count
            count+=1
            if count==3:raise OSError('PRIVATE_DISK_CANARY')
            original(path,value)
        with patch.object(runner.common,'save',fail):r=execute(client)
        self.assertEqual(client.calls,[]);self.assertNotIn('PRIVATE_DISK_CANARY',json.dumps(r))
        with tempfile.TemporaryDirectory()as root:
            d=Path(root)/'run';runner.run(client,p,runner.expected_grant(p),d,clock=lambda:NOW)
            with self.assertRaises(FileExistsError):runner.run(client,p,runner.expected_grant(p),d,clock=lambda:NOW)
            self.assertEqual(len(client.calls),2)

    def test_single_marker_and_dormant_encrypted_workflow(self):
        p=runner.build_package();g=runner.expected_grant(p);parent='a'*40
        marker=dict(schema='hcl-planner-contract-smoke-marker-v1',authorization_ref=runner.AUTH,package_sha256=runner.digest(p),grant_sha256=runner.digest(g),executor_commit=parent)
        history=[dict(id=1,event='push',created_at='2026-10-03T01:00:00Z')]
        self.assertTrue(runner.verify_launch(1,1,history,'push',parent,[str(runner.MARKER)],marker,p,g,NOW))
        for rid,attempt,event in ((2,1,'push'),(1,2,'push'),(1,1,'workflow_dispatch')):
            with self.assertRaises(ValueError):runner.verify_launch(rid,attempt,history,event,parent,[str(runner.MARKER)],marker,p,g,NOW)
        s=runner.TEMPLATE.read_text();self.assertIn('path: planner-contract-smoke.enc.json',s);self.assertNotIn('path: planner-contract-smoke-private',s)
        if runner.GRANT.exists()and json.loads(runner.GRANT.read_text())['status']=='PREPARED_REVIEW_REQUIRED':
            self.assertFalse(runner.WORKFLOW.exists());self.assertFalse(runner.MARKER.exists())


if __name__=='__main__':unittest.main()
