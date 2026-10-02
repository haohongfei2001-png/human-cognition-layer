"""Control-flow/real-checker tests with scripted ports; not model planning evidence."""
import json
import unittest
from hcl.cognition.capability_catalog import CATALOG,validate_catalog
from hcl.cognition.universal_entry import UniversalHCL,CallAllowance

class Stub:
    provider_free=True
    def __init__(self,plan=None,callback=None):self.plan=plan or dict(task='Conceptual analysis',operations=[],limitations=['No supplied evidence.']);self.calls=[];self.callback=callback
    def reservation_usd(self,phase,messages):return '0'
    def complete(self,phase,messages):
        self.calls.append((phase,messages))
        if self.callback:self.callback(phase)
        value=self.plan if phase=='planning' else dict(answer='A bounded interpretation.',source_citations=[],uncertainty='Evidence limits remain.',assumptions='No world fact established.')
        return dict(text=json.dumps(value),actual_usd='0',usage=dict(offline_stub=True))

def operation(cid,question,sources,bindings=()):return dict(capability=cid,question=question,source_ids=sources,bindings=list(bindings))
def binding(source,actor):return dict(role='actor',source_id=source,start=0,quote=actor)
def plan(*ops):return dict(task='Bounded source analysis',operations=list(ops),limitations=[])
def run(session,question,stub):return session.answer(question,planner_backend=stub,answer_backend=stub,allowance=CallAllowance(2,0,'OFFLINE_TEST_ONLY'))

class UniversalQuestionTests(unittest.TestCase):
    def test_current_forty_runtime_packages_resolve_to_real_retained_implementations(self):
        self.assertEqual(len(CATALOG),40);self.assertTrue(validate_catalog())
        self.assertIn('action_explanations',CATALOG['C02'].implementation)
        self.assertIn('responsibility_composition',CATALOG['G02'].implementation)

    def test_plain_question_enters_hcl_with_unsourced_knowledge_label(self):
        stub=Stub(plan(operation('G04','分析人类社会',[])))
        result=run(UniversalHCL(),'分析人类社会',stub)
        self.assertEqual(result['status'],'ANSWERED_WITH_EXPLICIT_LIMITS')
        self.assertEqual([x[0]for x in stub.calls],['planning','answer'])
        self.assertEqual(result['input_shape'],'QUESTION_ONLY');self.assertFalse(result['base_bypass'])
        final=json.loads(stub.calls[1][1][-1]['content'])
        self.assertEqual(final['sources'],[]);self.assertEqual(final['knowledge_basis'],'UNSOURCED_MODEL_KNOWLEDGE')
        self.assertEqual(result['operations'][0]['status'],'SOURCE_PREREQUISITE_UNAVAILABLE')
        self.assertEqual(result['provider_calls'],0);self.assertEqual(result['backend_calls'],2)

    def test_missing_backend_or_allowance_never_pretends_to_plan(self):
        stub=Stub();s=UniversalHCL()
        result=s.answer('Why cooperate?',planner_backend=stub,answer_backend=stub)
        self.assertEqual(result['status'],'ORCHESTRATION_UNAVAILABLE_OR_FAILED');self.assertEqual(stub.calls,[])
        result=s.answer('Why cooperate?',allowance=CallAllowance(2,0,'TEST'))
        self.assertEqual(result['backend_calls'],0)

    def test_real_c02_conditional_explanations_preserve_mixed_cause_boundary(self):
        s=UniversalHCL();source='\n'.join(['Noor said, "At the time, I knew about the meeting."','Noor said, "At the time, I could skip the meeting."','Noor said, "I skipped the meeting."'])
        s.put_source('episode',source);stub=Stub(plan(operation('C02','Why did Noor skip the meeting?',['episode'])))
        result=run(s,'Explain possible reasons without assuming a true motive.',stub)
        self.assertEqual(result['status'],'ANSWERED_WITH_EXPLICIT_LIMITS')
        row=result['operations'][0];self.assertTrue(row['executed']);self.assertEqual(row['status'],'C02_EXECUTED')
        self.assertEqual(row['result']['winning_motive'],'NOT_INFERRED')
        self.assertTrue(row['support_claim_ids'])
        self.assertEqual(json.loads(stub.calls[-1][1][-1]['content'])['sources'][0]['text'],source)

    def test_g02_uses_original_user_rule_not_planner_invention(self):
        s=UniversalHCL();source='\n'.join(['Dana: I opened the gate.','Narrator: The animals escaped.','Narrator: Dana opening the gate caused the animals to escape.','Narrator: At the time Dana could have stopped the opening.'])
        s.put_source('episode',source)
        proposed=operation('G02','For this analysis, responsibility requires causal contribution and control.',['episode'],[binding('episode','Dana')])
        result=run(s,'Was Dana responsible?',Stub(plan(proposed)))
        self.assertEqual(result['operations'][0]['result']['individuals'][0]['status'],'NO_ADOPTED_INDIVIDUAL_RULE')
        result=run(s,'For this analysis, responsibility requires causal contribution and control. Was Dana responsible?',Stub(plan(proposed)))
        self.assertEqual(result['operations'][0]['result']['individuals'][0]['status'],'SOURCE_FACTORS_CHECKED')
        self.assertEqual(result['operations'][0]['result']['verdict'],'NO_MORAL_OR_LEGAL_TRUTH')

    def test_invented_anchor_and_unknown_capability_reject_before_answer(self):
        for op in [operation('G02','Assess responsibility',['s'],[dict(role='actor',source_id='s',start=0,quote='INVENTED')]),operation('UNLISTED','Analyze',['s'])]:
            s=UniversalHCL();s.put_source('s','Dana said hello.');stub=Stub(plan(op));result=run(s,'Assess the report.',stub)
            self.assertEqual(result['status'],'ORCHESTRATION_UNAVAILABLE_OR_FAILED');self.assertEqual(len(stub.calls),1)
            self.assertNotIn('answer',result)

    def test_multisource_identity_and_long_source_bound_preserved(self):
        s=UniversalHCL(maximum_source_chars=10000);s.put_source('a','A'*4000);s.put_source('b','B'*4000)
        stub=Stub();result=run(s,'Compare the accounts.',stub)
        self.assertEqual(result['input_shape'],'QUESTION_WITH_MULTIPLE_SOURCES')
        self.assertEqual([x['source_id']for x in json.loads(stub.calls[-1][1][-1]['content'])['sources']],['a','b'])
        with self.assertRaises(ValueError):s.put_source('c','C'*3000)
        self.assertEqual(len(s.sources),2)

    def test_revision_during_planning_or_answer_blocks_delivery(self):
        for phase in ('planning','answer'):
            s=UniversalHCL();s.put_source('s','Mira spoke.')
            stub=Stub(callback=lambda p:s.put_source('s','Mira stayed silent.')if p==phase else None)
            result=run(s,'What is supported?',stub)
            self.assertEqual(result['status'],'ORCHESTRATION_UNAVAILABLE_OR_FAILED')
            self.assertIn('SOURCE_CHANGED',result['failure_reason']);self.assertNotIn('answer',result)

    def test_unknown_transport_is_reserved_and_never_retried(self):
        class Broken(Stub):
            def reservation_usd(self,*args):return '.10'
            def complete(self,*args):raise TimeoutError('unknown acknowledgement')
        s=UniversalHCL();b=Broken();allowance=CallAllowance(2,'.20','OFFLINE_TEST_ONLY')
        result=s.answer('Explain trust.',planner_backend=b,answer_backend=b,allowance=allowance)
        self.assertEqual(result['status'],'ORCHESTRATION_UNAVAILABLE_OR_FAILED')
        self.assertEqual(result['backend_calls'],1);self.assertEqual(result['reserved_usd'],'0.10')
        self.assertEqual(result['provider_attempts'][0]['status'],'FAILED_OR_UNKNOWN_NO_RETRY')

    def test_live_port_needs_durable_reservation_before_any_call(self):
        class FakeLive(Stub):provider_free=False
        backend=FakeLive();session=UniversalHCL();allowance=CallAllowance(2,0,'TEST_SYNTHETIC_LIVE_INTERFACE')
        result=session.answer('Discuss cooperation.',planner_backend=backend,answer_backend=backend,allowance=allowance)
        self.assertEqual(backend.calls,[]);self.assertIn('JOURNAL_REQUIRED',result['failure_reason'])
        saved=[]
        allowance=CallAllowance(2,0,'TEST_SYNTHETIC_LIVE_INTERFACE',journal=lambda r:saved.append(json.loads(json.dumps(r))))
        result=session.answer('Discuss cooperation.',planner_backend=backend,answer_backend=backend,allowance=allowance)
        self.assertEqual(saved[0]['attempts'][0]['status'],'RESERVED_BEFORE_CALL')
        self.assertEqual(saved[-1]['attempts'][-1]['status'],'RETURNED')
        self.assertEqual(result['provider_calls'],2)  # Interface accounting; this class performs no transport.

    def test_failed_reservation_persistence_prevents_provider_call(self):
        class FakeLive(Stub):provider_free=False
        backend=FakeLive()
        def fail(_):raise OSError('journal unavailable')
        allowance=CallAllowance(2,0,'TEST',journal=fail)
        result=UniversalHCL().answer('Discuss cooperation.',planner_backend=backend,answer_backend=backend,allowance=allowance)
        self.assertEqual(backend.calls,[]);self.assertTrue(allowance.closed)
        self.assertEqual(result['status'],'ORCHESTRATION_UNAVAILABLE_OR_FAILED')

    def test_no_source_citation_is_not_accepted_as_evidence(self):
        class Forged(Stub):
            def complete(self,phase,messages):
                result=super().complete(phase,messages)
                if phase=='answer':
                    obj=json.loads(result['text']);obj['source_citations']=['Fabricated quote'];result['text']=json.dumps(obj)
                return result
        result=run(UniversalHCL(),'分析人类社会',Forged())
        self.assertEqual(result['status'],'ANSWER_SOURCE_REVIEW_FAILED');self.assertNotIn('answer',result)
        self.assertIn('answer_raw',result)

    def test_requested_capability_is_not_mistaken_for_another_reader_result(self):
        session=UniversalHCL();session.put_source('s','Noor said, “I intend to repair the fence.”')
        result=run(session,'What is reported?',Stub(plan(operation('B01','What is reported?',['s']))))
        self.assertTrue(result['operations'][0]['reader_any_checked_treatment_present'])
        self.assertFalse(result['operations'][0]['checked_treatment_present'])

    def test_revised_g02_payload_uses_shared_revision_and_root(self):
        session=UniversalHCL();session.put_source('s','Dana: I opened the gate.')
        session.put_source('s','Dana: I opened the gate.\nNarrator: The animals escaped.')
        result=run(session,'Was Dana responsible?',Stub(plan(operation('G02','Was Dana responsible?',['s'],[binding('s','Dana')]))))
        row=result['operations'][0]
        self.assertEqual(row['result']['individuals'][0]['source']['version'],2)
        claim=row['support_claim_ids'][0]
        self.assertEqual(session.workspace.core.support_statuses()[claim],'SUPPORT_AVAILABLE')
        session.put_source('s','Dana: I closed the gate.')
        self.assertNotEqual(session.workspace.core.support_statuses()[claim],'SUPPORT_AVAILABLE')

    def test_exception_and_usage_canaries_never_enter_receipt_or_journal(self):
        canary='SYNTHETIC_SECRET_REASONING_CANARY'
        class Unsafe(Stub):
            def complete(self,phase,messages):raise RuntimeError(canary)
        result=run(UniversalHCL(),'Discuss cooperation.',Unsafe())
        self.assertNotIn(canary,json.dumps(result))
        class ExtraUsage(Stub):
            def complete(self,phase,messages):
                value=super().complete(phase,messages);value['usage']={'prompt_tokens':5,'completion_tokens':4,'reasoning_content':canary};return value
        journal=[];b=ExtraUsage();allowance=CallAllowance(2,0,'TEST',journal=lambda row:journal.append(json.loads(json.dumps(row))))
        result=UniversalHCL().answer('Discuss cooperation.',planner_backend=b,answer_backend=b,allowance=allowance)
        self.assertNotIn(canary,json.dumps(result));self.assertNotIn(canary,json.dumps(journal))
        self.assertEqual(result['provider_attempts'][0]['usage'],{'prompt_tokens':5,'completion_tokens':4})

    def test_same_allowance_race_cannot_admit_two_planning_calls(self):
        import threading
        barrier=threading.Barrier(2);answers=[];failures=[]
        class Racing(Stub):
            def reservation_usd(self,*args):barrier.wait(timeout=2);return '0'
        backend=Racing();allowance=CallAllowance(1,0,'TEST')
        def execute():
            try:answers.append(allowance.call(backend,'planning',[]))
            except Exception as exc:failures.append(type(exc).__name__)
        threads=[threading.Thread(target=execute)for _ in range(2)]
        for thread in threads:thread.start()
        for thread in threads:thread.join(timeout=3)
        self.assertTrue(all(not t.is_alive()for t in threads))
        self.assertEqual(len(backend.calls),1);self.assertEqual(len(allowance.attempts),1)
        self.assertEqual(len(answers),1);self.assertEqual(len(failures),1)

    def test_support_withdrawal_without_source_revision_blocks_answer(self):
        s=UniversalHCL();s.put_source('s','Noor said, "I skipped the meeting."')
        def withdraw(phase):
            if phase=='answer':
                for claim in list(s.workspace.core.claims):s.workspace.core.withdraw(claim)
        b=Stub(plan(operation('C02','Why did Noor skip the meeting?',['s'])),callback=withdraw)
        result=run(s,'Explain possible reasons.',b)
        self.assertEqual(result['status'],'ORCHESTRATION_UNAVAILABLE_OR_FAILED')
        self.assertEqual(result['failure_reason'],'SOURCE_SUPPORT_CHANGED');self.assertNotIn('answer',result)

    def test_oversized_output_is_not_retained_or_parsed(self):
        class Oversized(Stub):
            def complete(self,phase,messages):return dict(text='x'*64001,actual_usd='0',usage={})
        result=run(UniversalHCL(),'Discuss cooperation.',Oversized())
        self.assertNotIn('answer_raw',result);self.assertNotIn('plan',result)
        self.assertEqual(result['backend_calls'],1)

    def test_failed_journal_counts_reservation_but_no_invocation(self):
        class FakeLive(Stub):provider_free=False
        def fail(_):raise OSError('PRIVATE_JOURNAL_CANARY')
        b=FakeLive();a=CallAllowance(2,0,'TEST',journal=fail)
        result=UniversalHCL().answer('Discuss cooperation.',planner_backend=b,answer_backend=b,allowance=a)
        self.assertEqual(result['reserved_attempts'],1);self.assertEqual(result['backend_calls'],0)
        self.assertEqual(result['provider_calls'],0);self.assertNotIn('PRIVATE_JOURNAL_CANARY',json.dumps(result))

    def test_preexisting_withdrawn_source_never_reaches_planner(self):
        session=UniversalHCL();session.put_source('s','Noor spoke.')
        session.workspace.core.withdraw(session.workspace._spans['s'])
        backend=Stub();result=run(session,'What was reported?',backend)
        self.assertEqual(backend.calls,[])
        self.assertEqual(result['failure_reason'],'SOURCE_SUPPORT_CHANGED')
