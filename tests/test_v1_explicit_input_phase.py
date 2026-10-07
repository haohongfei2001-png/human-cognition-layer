"""Bounded current planning modes and pre-final treatment admission; no model calls."""
import copy
from decimal import Decimal
import json
from pathlib import Path
from types import SimpleNamespace
import unittest

from hcl.cognition import UniversalHCL, CallAllowance
from hcl.cognition.deepseek_metered import DeepSeekMeteredPort, INPUT_RATE, OUTPUT_RATE


class Scripted:
    provider_free = True
    def __init__(self, operations):
        self.operations = operations; self.calls = []
    def reservation_usd(self, phase, messages):
        return '0'
    def complete(self, phase, messages):
        self.calls.append((phase, copy.deepcopy(messages)))
        if phase == 'planning':
            return dict(text=json.dumps(dict(task='Preserve the source-scoped question.', operations=self.operations, limitations=[])),actual_usd='0',usage={})
        payload = json.loads(messages[-1]['content']); sources = payload['sources']
        return dict(text=json.dumps(dict(answer='The source reports a limited expression, not established private knowledge.',
            source_citations=[dict(source_id=s['source_id'],version=s['version'],quote=s['text']) for s in sources],
            uncertainty='No private state is certified.',assumptions='No additional evidence.')),actual_usd='0',usage={})


def operation(mode='literal', capability='B01', **fields):
    value=dict(capability=capability,question='What does Nora believe Ivo knows?',source_ids=['control'],bindings=[],input_mode=mode)
    value.update(fields);return value


def run(operations, text='Nora: I believe Ivo knows the lamp is blue.', **options):
    session=UniversalHCL();session.put_source('control',text);port=Scripted(operations)
    result=session.answer('What does Nora report about Ivo, and what remains uncertain?',planner_backend=port,answer_backend=port,
        allowance=CallAllowance(2,0,'OFFLINE_CONTROL_ONLY'),**options)
    return session,port,result


class ExplicitInputModeTests(unittest.TestCase):
    def test_omission_is_rejected_before_any_native_or_final_call(self):
        op=operation();del op['input_mode']
        _,port,result=run([op])
        self.assertEqual([p for p,_ in port.calls],['planning'])
        self.assertEqual(result['failure_reason'],'EXPLICIT_READER_INPUT_MODE_REQUIRED')
        self.assertEqual(result['operations'],[])

    def test_valid_literal_still_executes_real_native_and_delivers(self):
        _,port,result=run([operation()])
        self.assertEqual([p for p,_ in port.calls],['planning','answer'])
        self.assertEqual(result['status'],'ANSWERED_WITH_EXPLICIT_LIMITS')
        self.assertTrue(result['operations'][0]['checked_treatment_present'])
        self.assertEqual(result['operations'][0]['status'],'EXISTING_READER_EXECUTED')

    def test_semantic_requires_nonempty_candidates_and_literal_forbids_them(self):
        for op in (operation('semantic'),operation('semantic',semantic_candidates=[]),operation('literal',semantic_candidates=[])):
            with self.subTest(op=op):
                _,port,result=run([op]);self.assertEqual([p for p,_ in port.calls],['planning'])
                self.assertEqual(result['operations'],[])

    def test_source_validated_semantic_negation_is_not_upgraded_to_private_truth(self):
        text='At noon, Nora said, "I do not believe Ivo knows the lamp is blue."'
        candidate=dict(source_id='control',quote=text,kind='event',content={'canonical_statement':'Nora: I do not believe Ivo knows the lamp is blue.'})
        session,port,result=run([operation('semantic',semantic_candidates=[candidate])],text)
        self.assertEqual(result['status'],'ANSWERED_WITH_EXPLICIT_LIMITS')
        self.assertEqual(len(port.calls),2);native=result['operations'][0]
        self.assertTrue(native['checked_treatment_present']);self.assertFalse(native['semantic_certification'])
        self.assertIn('DENY',json.dumps(native['result']))
        self.assertEqual(session.sources['control']['text'],text)
        final=json.loads(port.calls[-1][1][-1]['content']);self.assertEqual(final['sources'][0]['text'],text)

    def test_false_semantic_anchor_never_executes_even_an_earlier_valid_operation(self):
        candidate=dict(source_id='control',quote='ABSENT_ANCHOR_CANARY',kind='event',content={'canonical_statement':'Nora: I believe the lamp is blue.'})
        _,port,result=run([operation(),operation('semantic',semantic_candidates=[candidate])])
        self.assertEqual([p for p,_ in port.calls],['planning'])
        self.assertEqual(result['operations'],[])
        self.assertEqual(result['failure_reason'],'invented or stale source anchor')

    def test_insufficient_is_explicit_and_never_a_fake_native_receipt(self):
        _,port,result=run([operation('insufficient')])
        self.assertEqual([p for p,_ in port.calls],['planning'])
        self.assertEqual(result['hcl_execution']['native_results'],0)
        self.assertFalse(result['operations'][0]['executed'])
        self.assertEqual(result['operations'][0]['status'],'EXPLICIT_READER_INPUT_INSUFFICIENT')

    def test_input_mode_cannot_authorize_an_unsupported_family_bridge(self):
        for op in (operation('anything'),operation(True),operation('semantic',capability='B02')):
            _,port,result=run([op]);self.assertEqual(len(port.calls),1);self.assertEqual(result['operations'],[])

    def test_normal_evidence_limited_answer_remains_available(self):
        text='The observer records an ordinary scene without admitted typed mental premises.'
        _,port,result=run([operation('literal')],text)
        self.assertEqual([p for p,_ in port.calls],['planning','answer'])
        self.assertEqual(result['status'],'ANSWERED_WITH_EXPLICIT_LIMITS')
        self.assertFalse(result['operations'][0]['checked_treatment_present'])

    def test_strict_caller_requirement_stops_zero_treatment_before_final_reservation(self):
        text='The observer records an ordinary scene without admitted typed mental premises.'
        _,port,result=run([operation('literal')],text,required_checked_capabilities=('B01',))
        self.assertEqual([p for p,_ in port.calls],['planning'])
        self.assertEqual(result['reserved_attempts'],1)
        self.assertTrue(result['operations'][0]['executed'])
        self.assertFalse(result['operations'][0]['checked_treatment_present'])
        self.assertNotIn('actual_final_messages',result)
        self.assertEqual(result['failure_reason'],'REQUIRED_CHECKED_NATIVE_TREATMENT_ABSENT_BEFORE_ANSWER')

    def test_strict_gate_accepts_actual_allowed_family_only_not_other_checked_results(self):
        for allowed, expected in [(('B01',),2),(('C01',),1)]:
            _,port,result=run([operation()],required_checked_capabilities=allowed)
            self.assertEqual(len(port.calls),expected)
            self.assertTrue(result['operations'][0]['checked_treatment_present'])

    def test_supported_literal_c02_is_admitted_by_its_actual_native_treatment(self):
        text='Noor: At the time, I knew about the meeting.\nNoor: At the time, I could skip the meeting.\nNoor: I skipped the meeting.'
        op=operation('literal','C02',question='Why did Noor skip the meeting?')
        _,port,result=run([op],text,required_checked_capabilities=('C02',))
        self.assertEqual([phase for phase,_ in port.calls],['planning','answer'])
        row=result['operations'][0];self.assertTrue(row['checked_treatment_present'])
        self.assertEqual(row['status'],'C02_EXECUTED')
        self.assertTrue(row['support_claim_ids'])
        self.assertTrue(any(x['disposition']=='CONDITIONALLY_SUPPORTED' and
            x['retained_checker_status']=='CONSISTENT_CONDITIONAL' for x in row['result']['explanations']))
        self.assertEqual(row['result']['winning_motive'],'NOT_INFERRED')

    def test_literal_c02_without_recorded_action_remains_unchecked_and_stops_final(self):
        text='Noor: At the time, I knew about the meeting.\nNoor: At the time, I could skip the meeting.'
        op=operation('literal','C02',question='Why did Noor skip the meeting?')
        _,port,result=run([op],text,required_checked_capabilities=('C02',))
        self.assertEqual([phase for phase,_ in port.calls],['planning'])
        row=result['operations'][0];self.assertTrue(row['executed'])
        self.assertEqual(row['result']['explanations'],[])
        self.assertFalse(row['checked_treatment_present'])
        self.assertEqual(result['failure_reason'],'REQUIRED_CHECKED_NATIVE_TREATMENT_ABSENT_BEFORE_ANSWER')

    def test_required_capabilities_are_caller_configuration_not_planner_authority(self):
        for configured in (['B01'],('B01','B01'),('MISSING',),True):
            with self.subTest(configured=configured),self.assertRaises(ValueError):
                run([operation()],required_checked_capabilities=configured)

    def test_same_real_failed_args_require_explicit_mode_then_strictly_stop_before_final(self):
        evidence=json.loads(Path('reports/HCL_ENTRY_VALIDATION_20261007_1_PUBLIC_EVIDENCE.json').read_text())
        args=copy.deepcopy(evidence['approved_native_evidence']['records'][0]['operations'][0]['source_validated_arguments'])
        source=evidence['cases'][0]['sources'][0]
        session=UniversalHCL();session.put_source(source['source_id'],source['text'])
        port=Scripted([args]);result=session.answer(evidence['cases'][0]['question'],planner_backend=port,answer_backend=port,
            allowance=CallAllowance(2,0,'OFFLINE_REPLAY_ONLY'),required_checked_capabilities=('B01',))
        self.assertEqual(result['failure_reason'],'EXPLICIT_READER_INPUT_MODE_REQUIRED');self.assertEqual(len(port.calls),1)
        args['input_mode']='literal' # A disclosed diagnostic variant, never a repaired live plan.
        port=Scripted([args]);result=session.answer(evidence['cases'][0]['question'],planner_backend=port,answer_backend=port,
            allowance=CallAllowance(2,0,'OFFLINE_REPLAY_ONLY'),required_checked_capabilities=('B01',))
        self.assertEqual(result['failure_reason'],'REQUIRED_CHECKED_NATIVE_TREATMENT_ABSENT_BEFORE_ANSWER')
        self.assertEqual(len(port.calls),1);self.assertTrue(result['operations'][0]['executed'])


    def test_previous_real_semantic_args_keep_identical_native_output_with_explicit_mode(self):
        evidence=json.loads(Path('reports/HCL_SEMANTIC_SMOKE_20261007_1_PUBLIC_EVIDENCE.json').read_text())
        operation_record=next(op for op in evidence['approved_native_evidence']['records'][0]['operations'] if op['capability_id']=='B01')
        args=copy.deepcopy(operation_record['source_validated_arguments']);args['input_mode']='semantic'
        case=evidence['cases'][0];session=UniversalHCL()
        for source in case['sources']:
            session.put_source(source['source_id'],source['text']);session.sources[source['source_id']]=copy.deepcopy(source)
        port=Scripted([args]);result=session.answer(case['question'],planner_backend=port,answer_backend=port,
            allowance=CallAllowance(2,0,'OFFLINE_DISCLOSED_MODE_VARIANT'),required_checked_capabilities=('B01',))
        self.assertEqual(result['status'],'ANSWERED_WITH_EXPLICIT_LIMITS')
        expected=operation_record['native_result_and_policy'];actual=result['operations'][0]
        self.assertEqual({key:actual[key] for key in expected},expected)
        self.assertTrue(actual['checked_treatment_present']);self.assertEqual(len(port.calls),2)
        self.assertEqual(json.loads(port.calls[-1][1][-1]['content'])['sources'],
            [{key:source[key] for key in ('source_id','version','text')} for source in case['sources']])

    def test_planner_cannot_supply_caller_checked_requirement(self):
        class Forged(Scripted):
            def complete(self,phase,messages):
                value=super().complete(phase,messages)
                if phase=='planning':
                    body=json.loads(value['text']);body['required_checked_capabilities']=[];value['text']=json.dumps(body)
                return value
        session=UniversalHCL();session.put_source('control','Nora: I believe Ivo knows the lamp is blue.')
        port=Forged([operation()]);result=session.answer('What is reported?',planner_backend=port,answer_backend=port,
            allowance=CallAllowance(2,0,'OFFLINE_CONTROL_ONLY'),required_checked_capabilities=('B01',))
        self.assertEqual(len(port.calls),1);self.assertEqual(result['operations'],[])


class FixedPhaseConfigurationTests(unittest.TestCase):
    def client(self):
        calls=[]
        def create(**kwargs):calls.append(kwargs);raise AssertionError('NO_SDK_DISPATCH_EXPECTED')
        return SimpleNamespace(max_retries=0,base_url='https://api.deepseek.com',timeout=180,
            chat=SimpleNamespace(completions=SimpleNamespace(create=create)),calls=calls)

    def test_phases_have_explicit_separate_effort_and_full_completion_allowance(self):
        client=self.client();port=DeepSeekMeteredPort(client);messages=[dict(role='user',content='原文 stays intact.')]
        for phase,effort in [('planning','high'),('answer','low')]:
            request,wire=port.request(phase,messages)
            self.assertEqual(request['max_tokens'],16384);self.assertEqual(request['reasoning_effort'],effort)
            self.assertEqual(request['thinking'],{'type':'enabled'});self.assertEqual(request['messages'],messages)
            expected=((2*len(wire)+2048)*INPUT_RATE+(16384+32)*OUTPUT_RATE)/1000000
            self.assertEqual(Decimal(port.reservation_usd(phase,messages)),expected)
        self.assertEqual(client.calls,[])

    def test_old_final_hold_cannot_silently_pay_for_new_completion_allowance(self):
        client=self.client();port=DeepSeekMeteredPort(client);messages=[dict(role='user',content='Source remains complete.')]
        _,wire=port.request('answer',messages)
        old=((2*len(wire)+2048)*INPUT_RATE+(8192+32)*OUTPUT_RATE)/1000000
        allowance=CallAllowance(2,str(old),'OFFLINE_OLD_HOLD_ONLY',journal=lambda _:None)
        allowance.call(Scripted([]),'planning',messages)
        with self.assertRaisesRegex(ValueError,'COST_ALLOWANCE_EXHAUSTED'):allowance.call(port,'answer',messages)
        self.assertEqual(client.calls,[]);self.assertEqual([x['phase'] for x in allowance.attempts],['planning'])

if __name__=='__main__':unittest.main()
