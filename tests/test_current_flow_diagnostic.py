"""Offline consumed G05 flow/authority/privacy checks; no provider network calls."""
from datetime import datetime,timedelta,timezone
from decimal import Decimal
import copy,json,tempfile,time,unittest
from pathlib import Path
from unittest.mock import patch
from tests.test_bounded_diagnostics import Client
from scripts import run_current_flow_diagnostic as runner

NOW=datetime(2026,10,4,12,tzinfo=timezone.utc)
VERIFIED=dict(existing_secret_presence_verified=True,existing_recipient_decryption_verified=True,durable_key_custody_verified=True,
    public_recipient_sha256=runner.recipient_fingerprint(runner.RECIPIENT.read_bytes()),test_fixture_only=True)

def grant(package):return runner.expected_grant(package,authorization_ref=runner.AUTHORIZATION,
    approved_at=runner.APPROVED_AT,expires_at=runner.EXPIRES_AT)

def response(raw,index,request):
    payload=json.loads(request['messages'][-1]['content'])
    if index==1:
        raw['choices'][0]['message']['content']=json.dumps(dict(task='Inspect the original caller condition',operations=[
            dict(capability='G05',question='Compare the requested conditional change.',source_ids=['choice'],bindings=[])],limitations=[]))
    else:
        source=payload['sources'][0];quote=source['text'].splitlines()[0]
        raw['choices'][0]['message']['content']=json.dumps(dict(answer='The stated argument loses this support under the assumption; the conclusion is not proven false.',
            source_citations=[dict(source_id='choice',version=1,quote=quote,start=0)],uncertainty='Source claims and the hypothetical are not verified world facts.',assumptions='Source reports only.'))

def execute(client,*,clock=lambda:NOW):
    with patch.object(runner,'readiness',return_value=VERIFIED):
        package=runner.build_package()
        with tempfile.TemporaryDirectory()as root:
            path=Path(root)/'run';result=runner.run(client,package,grant(package),path,clock=clock)
            assert json.loads((path/'receipt.json').read_text())==json.loads(json.dumps(result))
            return result

class CurrentFlowTests(unittest.TestCase):
    def test_default_closed_and_public_exception_does_not_require_private_custody(self):
        client=Client(response)
        package=runner.build_package()
        with tempfile.TemporaryDirectory()as root:
            with self.assertRaisesRegex(ValueError,'NEW_EXPLICIT_OWNER_AUTHORIZATION_REQUIRED'):
                runner.run(client,package,runner.expected_grant(package),Path(root)/'run',clock=lambda:NOW)
        runner.require_grant(package,grant(package),NOW)
        self.assertEqual(client.calls,[])

    def test_offline_grant_checks_allow_workflow_and_marker_presence(self):
        client=Client(response)
        with tempfile.TemporaryDirectory()as root:
            workflow=Path(root)/'workflow.yml';marker=Path(root)/'marker.json'
            for present in (False,True):
                if present:
                    workflow.write_bytes(runner.TEMPLATE.read_bytes());marker.write_text('{}')
                with patch.object(runner,'WORKFLOW',workflow),patch.object(runner,'MARKER',marker),patch.object(runner,'readiness',return_value=VERIFIED):
                    self.assertEqual(runner.WORKFLOW.exists(),present);self.assertEqual(runner.MARKER.exists(),present)
                    package=runner.build_package();runner.require_grant(package,grant(package),NOW)
                    with self.assertRaisesRegex(ValueError,'NEW_EXPLICIT_OWNER_AUTHORIZATION_REQUIRED'):
                        runner.run(client,package,runner.expected_grant(package),Path(root)/'run',clock=lambda:NOW)
        self.assertEqual(client.calls,[])

    def test_full_request_freeze_and_budget_are_exact(self):
        p=runner.build_package()
        self.assertLess(p['requests']['planning']['bytes'],36000)
        self.assertEqual(p['maximum_calls'],2);self.assertEqual(p['maximum_usd'],'0.30')
        self.assertLess(Decimal(p['maximum_schedule_reservation_usd']),runner.CAP)
        self.assertEqual(len(p['historical_grants_sha256']),15)
        self.assertEqual(p['production_default_planning_tokens'],4096)
        original=json.loads(json.loads(runner.ORIGINAL_REQUEST.read_text())['messages'][-1]['content'])
        self.assertEqual(runner.frozen_input()['question'],original['question'])
        self.assertEqual(runner.frozen_input()['sources'],original['sources'])
        self.assertEqual(p['requests']['planning']['bytes'],29225)
        self.assertEqual(p['maximum_schedule_reservation_usd'],'0.27517512')

    def test_g05_source_request_support_and_answer_without_semantic_certification(self):
        client=Client(response);r=execute(client)
        self.assertEqual(len(client.calls),2);self.assertEqual([q['max_tokens']for q in client.calls],[16384,8192])
        self.assertEqual(r['status'],'G05_ANSWER_ACCEPTED_READBACK_PENDING')
        self.assertEqual(r['executed_capabilities'],['G05'])
        operation=r['hcl']['operations'][0]
        self.assertEqual(operation['result']['variants'][0]['kind'],'FACT_COUNTERFACTUAL')
        self.assertEqual(operation['result']['variants'][0]['comparisons'][0]['sensitivity'],'SUPPORT_REMOVED_UNDER_ASSUMPTION')
        self.assertEqual(r['g05_treatment_gate'],'SOURCE_AND_ORIGINAL_REQUEST_SUPPORTED')
        plan,hcl=[json.loads(q['messages'][-1]['content'])for q in client.calls]
        self.assertEqual(plan['question'],hcl['question']);self.assertEqual(hcl['question'],runner.frozen_input()['question'])
        self.assertEqual(hcl['sources'][0]['text'],plan['sources'][0]['text'])
        self.assertFalse(r['efficacy_verified']);self.assertFalse(r['hcl_source_review']['semantic_certification'])
        self.assertEqual(r['remaining_authorized_calls'],0)
        self.assertEqual(Decimal(r['reserved_usd']),sum(Decimal(c['reserved_usd'])for c in r['calls']))
        self.assertNotIn('HIDDEN_',json.dumps(r))

    def test_empty_or_unavailable_selection_is_recorded_and_not_replaced(self):
        for operations in ([],[dict(capability='E05',question='Describe limitations.',source_ids=['choice'],bindings=[])]):
            def mutate(raw,i,q):
                response(raw,i,q)
                if i==1:raw['choices'][0]['message']['content']=json.dumps(dict(task='Record limitations',operations=operations,limitations=[]))
            client=Client(mutate);r=execute(client)
            self.assertEqual(len(client.calls),1);self.assertEqual(r['executed_capabilities'],[])
            self.assertNotIn('g05_treatment_gate',r)
            self.assertEqual(r['status'],'HCL_FAILED_NO_RETRY')
            self.assertEqual(r['selected_capabilities'],[o['capability']for o in operations])

    def test_bad_plan_length_transport_or_model_stops_once_without_expansion(self):
        for edge in ('schema','length','model','transport'):
            def mutate(raw,i,q):
                response(raw,i,q)
                if edge=='schema':raw['choices'][0]['message']['content']='{}'
                elif edge=='length':raw['choices'][0].update(finish_reason='length')
                elif edge=='model':raw['model']='unapproved'
            client=Client(mutate)
            if edge=='transport':client.failure='PRIVATE_ERROR_CANARY'
            r=execute(client);self.assertEqual(len(client.calls),1);self.assertEqual(r['status'],'HCL_FAILED_NO_RETRY')
            self.assertNotIn('PRIVATE_ERROR_CANARY',json.dumps(r))

    def test_citation_rejection_is_terminal_and_never_repaired(self):
        for phase in (2,):
            def mutate(raw,i,q):
                response(raw,i,q)
                if i==phase:
                    value=json.loads(raw['choices'][0]['message']['content']);value['source_citations'][0]['end']=5
                    raw['choices'][0]['message']['content']=json.dumps(value)
            client=Client(mutate);r=execute(client)
            self.assertEqual(len(client.calls),phase);self.assertNotEqual(r['status'],'G05_ANSWER_ACCEPTED_READBACK_PENDING')
            self.assertIn('"end": 5',r['calls'][-1]['response_content'])

    def test_empty_citations_do_not_count_as_full_flow(self):
        def mutate(raw,i,q):
            response(raw,i,q)
            if i==2:
                value=json.loads(raw['choices'][0]['message']['content']);value['source_citations']=[]
                raw['choices'][0]['message']['content']=json.dumps(value)
        client=Client(mutate);r=execute(client)
        self.assertEqual(len(client.calls),2);self.assertFalse(r['hcl_citations_accepted'])

    def test_complete_output_usage_keeps_full_failed_reservation(self):
        def mutate(raw,i,q):
            raw['choices'][0].update(finish_reason='length');raw['choices'][0]['message']['content']=''
            raw['usage']=dict(prompt_tokens=5000,completion_tokens=16384,total_tokens=21384,completion_tokens_details=dict(reasoning_tokens=16384))
        client=Client(mutate);r=execute(client);row=r['calls'][0]
        self.assertEqual(row['usage']['completion_tokens'],16384)
        self.assertEqual(row['response_diagnostics']['reasoning_tokens'],16384)
        self.assertEqual(r['reserved_usd'],row['reserved_usd']);self.assertGreater(Decimal(row['reserved_usd']),Decimal(row['actual_usd']))

    def test_changed_request_cap_and_rearm_are_refused(self):
        with patch.object(runner,'readiness',return_value=VERIFIED):
            p=runner.build_package()
            for edge in ('request','usd','rearm','call_count','underreserve'):
                with tempfile.TemporaryDirectory()as root:
                    l=runner.Ledger(Path(root)/'run',p,grant(p),lambda:NOW);client=Client(response)
                    port=runner.RecordedPort(client,l,'hcl',16384);messages=runner.planning_messages();reserve=port.reservation_usd('planning',messages)
                    attempt=dict(phase='planning',reserved_usd=reserve,status='RESERVED_BEFORE_CALL',invocation_status='NOT_INVOKED')
                    if edge=='request':port.requests['planning']['messages'][0]['content']+=' drift'
                    elif edge=='usd':l.value['reserved_usd']='0.30'
                    elif edge=='call_count':l.value['calls']=[dict(call_id='x')]*2
                    elif edge=='underreserve':attempt['reserved_usd']='0'
                    else:port.journal(dict(attempts=[attempt]));port.complete('planning',messages)
                    with self.assertRaises(ValueError):port.journal(dict(attempts=[attempt]))
                    self.assertEqual(len(client.calls),1 if edge=='rearm'else 0)

    def test_expiry_directory_reuse_and_durable_failure_prevent_send(self):
        with patch.object(runner,'readiness',return_value=VERIFIED):
            p=runner.build_package();g=grant(p);client=Client(response)
            with tempfile.TemporaryDirectory()as root:
                with self.assertRaises(ValueError):runner.run(client,p,g,Path(root)/'run',clock=lambda:datetime.fromisoformat(runner.EXPIRES_AT.replace('Z','+00:00')))
                d=Path(root)/'run';d.mkdir()
                with self.assertRaises(FileExistsError):runner.run(client,p,g,d,clock=lambda:NOW)
            self.assertEqual(client.calls,[])
        original=runner.common.save;count=0
        def fail(path,value):
            nonlocal count
            count+=1
            if count==2:raise OSError('PRIVATE_DISK_CANARY')
            original(path,value)
        with patch.object(runner.common,'save',fail):r=execute(client)
        self.assertEqual(client.calls,[]);self.assertNotIn('PRIVATE_DISK_CANARY',json.dumps(r))

    def test_exact_marker_and_first_attempt_only(self):
        with patch.object(runner,'readiness',return_value=VERIFIED):
            p=runner.build_package();g=grant(p);parent='a'*40
            marker=dict(schema='hcl-current-flow-marker-v1',authorization_ref=g['authorization_ref'],package_sha256=runner.digest(p),grant_sha256=runner.digest(g),executor_commit=parent)
            history=[dict(id=1,event='push',created_at=NOW.isoformat())]
            runner.verify_launch(1,1,history,'push',parent,[str(runner.MARKER)],marker,p,g,NOW)
            for attempt,event,paths in ((2,'push',[str(runner.MARKER)]),(1,'workflow_dispatch',[]),(1,'push',[str(runner.MARKER),'extra'])):
                with self.assertRaises(ValueError):runner.verify_launch(1,attempt,history,event,parent,paths,marker,p,g,NOW)
            with self.assertRaises(ValueError):runner.verify_launch(2,1,history,'push',parent,[str(runner.MARKER)],marker,p,g,NOW)

    def test_complete_oversize_plan_is_preserved_and_stops_before_answer(self):
        def mutate(raw,i,q):
            response(raw,i,q)
            raw['choices'][0]['message']['content']=json.dumps(dict(task='Oversized interpretations',operations=[
                dict(capability='G05',question='界'*8000,source_ids=['choice'],bindings=[])for _ in range(3)],limitations=[]),ensure_ascii=False)
        client=Client(mutate);r=execute(client)
        self.assertEqual(len(client.calls),1)
        self.assertEqual(len(r['hcl']['plan']['operations']),3)
        self.assertTrue(all(len(o['question'])==8000 for o in r['hcl']['plan']['operations']))
        self.assertEqual(r['status'],'HCL_FAILED_NO_RETRY')

    def test_missing_usage_and_timeout_hold_once_without_followup(self):
        client=Client(lambda raw,i,q:raw.update(usage={}))
        r=execute(client);self.assertEqual(len(client.calls),1);self.assertNotIn('actual_usd',r['calls'][0])
        self.assertEqual(r['reserved_usd'],r['calls'][0]['reserved_usd'])
        class Slow(Client):
            def create(self,**request):
                value=super().create(**request);time.sleep(0.04);return value
        original=runner.OutputLimitPort.__init__
        def short(port,*a,**kw):original(port,*a,**kw);port.maximum_wait_seconds=0.001
        client=Slow(response)
        with patch.object(runner.OutputLimitPort,'__init__',short):r=execute(client)
        self.assertEqual(len(client.calls),1);self.assertEqual(r['calls'][0]['failure_code'],'DEADLINE_SEND_UNKNOWN_NO_RETRY')
        self.assertEqual(r['reserved_usd'],r['calls'][0]['reserved_usd'])

    def test_grant_cannot_expand_reset_or_extend_authority(self):
        with patch.object(runner,'readiness',return_value=VERIFIED):
            p=runner.build_package();g=grant(p);client=Client(response)
            changes=[dict(authorized_calls=4),dict(authorized_usd='1'),dict(status='PREPARED_NOT_AUTHORIZED'),
                     dict(authorization_ref='OLD_CLOSED_GRANT'),dict(historical_budget_transfer=True),
                     dict(expires_at=(NOW+timedelta(days=2)).isoformat())]
            for delta in changes:
                with tempfile.TemporaryDirectory()as root,self.assertRaises(ValueError):runner.run(client,p,dict(g,**delta),Path(root)/'run',clock=lambda:NOW)
            self.assertEqual(client.calls,[])

    def test_either_provenance_root_withdrawal_prevents_answer(self):
        original=runner.G05RecordedPort.reservation_usd
        for kind in ('source','request'):
            def withdraw(port,phase,messages):
                if phase=='answer':
                    payload=json.loads(messages[-1]['content']);operation=payload['hcl_operations'][0]
                    root=port.session.workspace._spans['choice']if kind=='source'else operation['request_provenance']['span_id']
                    port.session.workspace.core.withdraw(root)
                return original(port,phase,messages)
            client=Client(response)
            with patch.object(runner.G05RecordedPort,'reservation_usd',withdraw):r=execute(client)
            self.assertEqual(len(client.calls),1)
            self.assertEqual(r['g05_treatment_gate'],'MISSING_OR_UNSUPPORTED_G05_NO_ANSWER')

    def test_empty_answer_is_not_delivery_success(self):
        def mutate(raw,i,q):
            response(raw,i,q)
            if i==2:
                value=json.loads(raw['choices'][0]['message']['content']);value['answer']=' '
                raw['choices'][0]['message']['content']=json.dumps(value)
        client=Client(mutate);r=execute(client)
        self.assertEqual(len(client.calls),2);self.assertNotIn('hcl_citations_accepted',r)
        self.assertEqual(r['status'],'HCL_FAILED_NO_RETRY')

    def test_public_readback_hash_is_bound_and_plaintext_silent(self):
        package=json.loads(runner.PACKAGE.read_text())
        with tempfile.TemporaryDirectory()as root:
            path=Path(root)/'receipt.json'
            raw=json.dumps(dict(package_sha256=runner.digest(package),answer='PRIVATE_CANARY'))
            path.write_text(raw)
            result=runner.public_readback_identity(path,'123','b'*40)
            self.assertEqual(result['receipt_sha256'],runner.hashlib.sha256(raw.encode()).hexdigest())
            self.assertNotIn('PRIVATE_CANARY',json.dumps(result));self.assertEqual(result['head_sha'],'b'*40)
            for run,head in [('0','b'*40),('１２３','b'*40),('123','main')]:
                with self.assertRaises(ValueError):runner.public_readback_identity(path,run,head)
            path.write_text('{"package_sha256":"wrong"}')
            with self.assertRaises(ValueError):runner.public_readback_identity(path,'123','b'*40)

if __name__=='__main__':unittest.main()
