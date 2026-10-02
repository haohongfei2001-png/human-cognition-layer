import json
import unittest
from hcl.cognition import CognitionWorkspace
from hcl.v1.capabilities import CAPABILITIES

class UniversalOrchestrationTests(unittest.TestCase):
    def prepare(self, source, question='Explain the people and what can be concluded.'):
        w=CognitionWorkspace();w.put_source('story',source)
        return w,w.prepare_reader_entry(question,source_ids=('story',),allow_translation=False)

    def test_every_question_enumerates_registry_and_records_real_insufficiency(self):
        for question in ('Why did Mira shut the door?', 'Compare their values.', 'Could this reflect mixed motives?'):
            _,entry=self.prepare('Mira shut the door. Theo waited outside.',question)
            plan=entry.receipt['local_preparation']['orchestration']
            self.assertEqual([x['capability_id'] for x in plan['inventory']],list(CAPABILITIES))
            self.assertEqual(plan['task']['question'],question)
            self.assertFalse(plan['base_bypass'])
            self.assertFalse(plan['complete_capability_integration'])
            self.assertFalse(plan['checked_treatment_present'])
            self.assertGreater(len(plan['integration_gaps']),0)
            payload=json.loads(entry.messages[-1]['content'])
            self.assertEqual(payload['hcl_orchestration']['composition_status'],'HCL_EXPLICIT_CAPABILITY_INSUFFICIENCY')
            self.assertIn('Mira shut the door.',payload['sources'][0]['text'])
            self.assertEqual(plan['provider_calls'],0)

    def test_supported_operations_are_real_and_not_all_modules_claimed(self):
        cases=[('Nia said, “I believe the gate is clear.”','belief'),
               ('Nia said, “I intend to repair the fence.”','intention'),
               ('Nia said, “The gate is clear.” Tom heard Nia\'s last statement.','perspective')]
        for source, expected in cases:
            _,entry=self.prepare(source)
            plan=entry.receipt['local_preparation']['orchestration']
            op=next(o for o in plan['operations'] if o['capability_id']==expected)
            self.assertGreater(op['checked_operations'],0)
            self.assertTrue(plan['checked_treatment_present'])
            self.assertEqual(plan['checked_treatment_present'],entry.receipt['checked_treatment_present'])
            self.assertFalse(plan['complete_capability_integration'])

    def test_named_observation_path_executes_and_has_live_source_support(self):
        source='Mira saw the key in the drawer. Theo moved the key to the shelf.'
        w,entry=self.prepare(source,'Where would Mira look for the key?')
        payload=json.loads(entry.messages[-1]['content'])
        state=payload['checked_information_state']
        self.assertEqual(state['last_reported_observation']['location'],'drawer')
        self.assertTrue(state['later_source_movement_without_observation_evidence'])
        self.assertIn('does not prove',state['inference_boundary'])
        self.assertEqual(w.core.support_statuses()[state['claim_id']],'SUPPORT_AVAILABLE')
        operation=next(o for o in payload['hcl_orchestration']['operations'] if o['capability_id']=='information_state')
        self.assertEqual(operation['checked_operations'],1)
        self.assertTrue(entry.receipt['checked_treatment_present'])
        w.put_source('story','Mira saw the key in the cupboard.')
        with self.assertRaises(ValueError):entry.current_messages(w)
        self.assertNotEqual(w.core.support_statuses()[state['claim_id']],'SUPPORT_AVAILABLE')

    def test_source_change_and_final_review_are_not_fake_trace(self):
        w,entry=self.prepare('Nia said, “I believe the gate is clear.”')
        w.put_source('story','Nia said, “I believe the gate is blocked.”')
        with self.assertRaises(ValueError):entry.current_messages(w)
        result=w.answer_reader_entry('What is reported?',lambda messages:json.dumps(dict(
            answer='A source report.',source_citations=['NOT IN THE SOURCE'],uncertainty='',assumptions='')),
            source_ids=('story',),allow_translation=False)
        self.assertFalse(result['source_citation_audit']['deliverable'])
        self.assertEqual(result['orchestration_review']['source_audit_status'],result['source_citation_audit']['status'])
        self.assertNotEqual(result['answer'],result['answer_raw'])
        self.assertFalse(result['orchestration_review']['base_bypass'])
