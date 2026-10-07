"""An empty final answer is a failed delivery, even after a real native HCL result."""
import json,unittest
from hcl.cognition import UniversalHCL,CallAllowance
from hcl.cognition.deepseek_metered import DeepSeekMeteredPort
from tests.test_v1_c02_planned_input import SOURCE,ORIGINAL,QUOTES,selected
from tests.test_v1_universal_question import Stub,operation,plan,run
from tests.test_v1_deepseek_metered import FakeClient


def body(answer,*,sourced=True):
    return dict(answer=answer,source_citations=[dict(source_id='maintenance',version=1,quote=QUOTES[0])]if sourced else[],
        uncertainty='Source and interpretation limits remain.',assumptions='No actual motive established.')


class AnswerPort(Stub):
    def __init__(self,answer,*,sourced=True):
        super().__init__(plan(selected())if sourced else plan(operation('G01','Prepare the original condition.',[])))
        self.raw=json.dumps(body(answer,sourced=sourced),ensure_ascii=False)
    def complete(self,phase,messages):
        result=super().complete(phase,messages)
        if phase=='answer':result['text']=self.raw
        return result


class NonblankAnswerTests(unittest.TestCase):
    def session(self):
        session=UniversalHCL();session.put_source('maintenance',SOURCE);return session

    def test_empty_ascii_and_unicode_whitespace_fail_with_raw_output_and_execution_preserved(self):
        cases={'empty':'','ascii':' \t\r\n','nbsp':'\u00a0','unicode':'\u2003\u2028\u2029\u3000',
               'controls':'\v\f\x85','bounded_large':' '*60000}
        for label,answer in cases.items():
            with self.subTest(case=label):
                port=AnswerPort(answer);result=run(self.session(),ORIGINAL,port)
                self.assertEqual(result['status'],'ORCHESTRATION_UNAVAILABLE_OR_FAILED')
                self.assertEqual(result['failure_reason'],'NONBLANK_FINAL_ANSWER_REQUIRED')
                self.assertNotIn('answer',result);self.assertEqual(result['answer_raw'],port.raw)
                self.assertEqual(result['hcl_execution']['native_results'],1)
                self.assertEqual([phase for phase,_ in port.calls],['planning','answer'])
                self.assertEqual([a['status']for a in result['provider_attempts']],['RETURNED','RETURNED'])
                self.assertEqual(result['provider_calls'],0)

    def test_source_free_native_result_also_cannot_deliver_a_blank_answer(self):
        port=AnswerPort('\u3000',sourced=False)
        result=run(UniversalHCL(),'For this analysis, responsibility requires control.',port)
        self.assertEqual(result.get('failure_reason'),'NONBLANK_FINAL_ANSWER_REQUIRED')
        self.assertEqual(result['hcl_execution']['native_results'],1)
        self.assertEqual(result['answer_raw'],port.raw);self.assertNotIn('answer',result)

    def test_nonblank_unicode_and_surrounding_whitespace_are_not_rewritten(self):
        for answer in ('A conditional report.','不确定。','🙂','e\u0301','\u2003 可能。 \n'):
            with self.subTest(answer=answer):
                port=AnswerPort(answer);result=run(self.session(),ORIGINAL,port)
                self.assertEqual(result['status'],'ANSWERED_WITH_EXPLICIT_LIMITS')
                self.assertEqual(result['answer'],port.raw);self.assertEqual(result['answer_raw'],port.raw)
                self.assertEqual(json.loads(result['answer'])['answer'],answer)
                self.assertFalse(result['source_review']['semantic_certification'])

    def test_nonblank_text_does_not_override_existing_citation_rejection(self):
        port=AnswerPort('A nonblank report.');value=json.loads(port.raw)
        value['source_citations'][0]['end']=1;port.raw=json.dumps(value)
        result=run(self.session(),ORIGINAL,port)
        self.assertEqual(result['status'],'ANSWER_SOURCE_REVIEW_FAILED')
        self.assertEqual(result['answer_raw'],port.raw);self.assertNotIn('answer',result)

    def test_real_meter_interface_keeps_two_reservations_and_does_not_retry_blank_output(self):
        class EmptySDK(FakeClient):
            def create(self,**request):
                result=super().create(**request)
                content=plan(operation('G01','Prepare the caller condition.',[]))if request['reasoning_effort']=='high' else body(' ',sourced=False)
                result['choices'][0]['message']['content']=json.dumps(content)
                return result
        client=EmptySDK();port=DeepSeekMeteredPort(client);journal=[]
        allowance=CallAllowance(2,'1','SYNTHETIC_NO_NETWORK_ONLY',journal=lambda row:journal.append(json.loads(json.dumps(row))))
        session=UniversalHCL();question='For this analysis, responsibility requires control.'
        result=session.answer(question,planner_backend=port,answer_backend=port,allowance=allowance)
        self.assertEqual(result.get('failure_reason'),'NONBLANK_FINAL_ANSWER_REQUIRED')
        self.assertEqual(len(client.calls),2);self.assertTrue(allowance.closed)
        self.assertEqual(len(allowance.attempts),2);self.assertGreater(allowance.reserved_usd,0)
        self.assertEqual([r['status']for r in journal[-1]['attempts']],['RETURNED','RETURNED'])
        self.assertEqual(json.loads(result['answer_raw'])['answer'],' ')
        self.assertNotIn('HIDDEN_',json.dumps(result))
        held=allowance.reserved_usd
        session.answer(question,planner_backend=port,answer_backend=port,allowance=allowance)
        self.assertEqual(len(client.calls),2);self.assertEqual(allowance.reserved_usd,held)


if __name__=='__main__':unittest.main()
