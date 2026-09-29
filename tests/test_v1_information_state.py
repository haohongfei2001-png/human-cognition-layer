"""Provider-free ordinary information-state entry and inference boundaries."""
import json
import unittest

from hcl.v1 import CognitionRequest, HCLCognitionLayer
from hcl.v1.information_state import check_information_state, information_query
from hcl.v1.router import CognitionRouter, PerspectiveMode
from scripts.i02_native_treatment_preflight import require_treatment


SOURCE = ('Bea put the key in the drawer. '
          'Alice saw Bea put the key in the drawer. '
          'Bea moved the key to the shelf.')
QUESTION = 'Where would Alice look for the key?'


class InformationStateTests(unittest.TestCase):
    def setUp(self):
        self.layer = HCLCognitionLayer(lambda messages: 'source-bounded answer')

    def _prepared(self, source=SOURCE, question=QUESTION):
        return self.layer.prepare(CognitionRequest(question, narrative=source))

    def test_positive_checked_treatment_in_actual_final_input(self):
        prepared = self._prepared()
        self.assertFalse(prepared.plan.direct)
        self.assertIn('information_state', prepared.plan.capabilities)
        payload = json.loads(prepared.messages[-1]['content'])
        self.assertEqual(payload['query'], QUESTION)
        self.assertEqual(payload['narrative'], SOURCE)
        state = payload['cognition_context']['information_state']
        self.assertEqual(state['checked_observation_count'], 1)
        self.assertEqual(state['last_reported_observation']['location'], 'drawer')
        self.assertTrue(state['later_source_movement_without_observation_evidence'])
        for row in state['observations'] + state['source_movements']:
            self.assertEqual(SOURCE[row['source_start']:row['source_end']], row['source_quote'])
        self.assertEqual(prepared.preparation_receipt['extraction_provider_calls'], 0)
        self.assertIn('private belief', prepared.messages[0]['content'])
        self.assertEqual(self.layer.answer(CognitionRequest(QUESTION, narrative=SOURCE)),
                         'source-bounded answer')

    def test_actor_boundary_and_no_access_promotion(self):
        state = self._prepared(question='Where would Cara look for the key?').context.information_state
        self.assertEqual(state['checked_observation_count'], 0)
        self.assertIsNone(state['last_reported_observation'])
        self.assertEqual(state['status'], 'UNRESOLVED_NO_EXPLICIT_NAMED_OBSERVATION')
        self.assertEqual(self._prepared(question='Where would Cara look for the key?').preparation_receipt['failure'],
                         'no_explicit_named_observation')
        with self.assertRaisesRegex(ValueError, 'actor conflicts'):
            self.layer.prepare(CognitionRequest(QUESTION, narrative=SOURCE, target_actor='Cara'))

    def test_pronoun_negation_and_unclear_time_fail_closed(self):
        source = ('Bea put the key in the drawer. She saw the key in the drawer. '
                  'Alice did not see Bea move the key to the shelf. '
                  'Later, Alice saw the key on the piano.')
        state = self._prepared(source).context.information_state
        self.assertEqual(state['checked_observation_count'], 0)
        self.assertEqual(state['time_basis'], 'NARRATIVE_ORDER_ONLY')
        self.assertFalse(state['later_source_movement_without_observation_evidence'])

    def test_local_revision_recomputes_only_named_observation(self):
        old = self._prepared().context.information_state
        revised_source = SOURCE.replace('Alice saw Bea put the key in the drawer.',
            'Alice saw Bea put the key on the table.')
        revised = self._prepared(revised_source).context.information_state
        self.assertEqual(old['last_reported_observation']['location'], 'drawer')
        self.assertEqual(revised['last_reported_observation']['location'], 'table')
        self.assertEqual(old['source_movements'][0]['location'], revised['source_movements'][0]['location'])
        self.assertEqual(check_information_state(SOURCE, 'Cara', 'key')['observations'],
                         check_information_state(revised_source, 'Cara', 'key')['observations'])

    def test_composition_with_existing_actor_scope_and_ablation(self):
        request = CognitionRequest(QUESTION, narrative=SOURCE, target_actor='Alice')
        prepared = self.layer.prepare(request)
        self.assertIn('source_visibility', prepared.plan.capabilities)
        self.assertEqual(prepared.context.actors, ['Alice'])
        ablated = HCLCognitionLayer(lambda _: '',
            router=CognitionRouter(information_state_enabled=False)).prepare(request)
        self.assertTrue(ablated.plan.direct is False)  # explicit actor scope remains
        self.assertNotIn('information_state', ablated.plan.capabilities)
        self.assertEqual(set(prepared.plan.capabilities) - set(ablated.plan.capabilities),
                         {'information_state'})
        self.assertNotIn('information_state', json.loads(ablated.messages[-1]['content'])['cognition_context'])
        self.assertEqual(prepared.preparation_receipt['answer_provider_calls'], 1)

    def test_character_view_does_not_receive_reader_only_later_move(self):
        request = CognitionRequest(QUESTION, narrative=SOURCE, target_actor='Alice',
            perspective_mode=PerspectiveMode.CHARACTER_PERSPECTIVE)
        prepared = self.layer.prepare(request)
        payload = json.loads(prepared.messages[-1]['content'])
        self.assertNotIn('narrative', payload)
        self.assertNotIn('shelf', prepared.messages[-1]['content'])
        state = payload['cognition_context']['information_state']
        self.assertEqual(state['last_reported_observation']['location'], 'drawer')
        self.assertEqual(state['source_movements'], [])
        self.assertIsNone(state['later_source_movement_without_observation_evidence'])

    def test_adjacent_unique_subject_glimpse_enters_actual_input_and_ablation(self):
        source = ("Carefully lifting Bea's box, Kai sets it on the table. "
                  'At the table, he glimpses a key among the papers. '
                  'Bea moved the key to the drawer.')
        question = 'Where would Kai look for the key?'
        request = CognitionRequest(question, narrative=source)
        h = self.layer.prepare(request)
        h_new = HCLCognitionLayer(lambda _: '',
            router=CognitionRouter(information_state_enabled=False)).prepare(request)
        a = json.loads(h.messages[-1]['content'])
        b = json.loads(h_new.messages[-1]['content'])
        state = a['cognition_context']['information_state']
        self.assertEqual(state['checked_observation_count'], 1)
        self.assertEqual(state['last_reported_observation']['location'], 'table')
        self.assertEqual(state['last_reported_observation']['actor_binding'],
                         'SOURCE_LOCAL_PRONOUN_INFERENCE_NOT_IDENTITY_FACT')
        self.assertEqual(state['last_reported_observation']['observer'], 'Kai')
        self.assertEqual(set(h.plan.capabilities) - set(h_new.plan.capabilities),
                         {'information_state'})
        self.assertEqual(a['query'], b['query'])
        self.assertEqual(a['narrative'], b['narrative'])
        self.assertEqual({k: v for k, v in a['cognition_context'].items()
                          if k != 'information_state'}, b['cognition_context'])
        self.assertEqual(state['source_movements'][0]['location'], 'drawer')
        for row in state['observations'] + state['source_movements']:
            self.assertEqual(source[row['source_start']:row['source_end']], row['source_quote'])
        self.assertEqual(h.preparation_receipt['extraction_provider_calls'], 0)

    def test_direct_named_sight_and_local_revision(self):
        original = 'At the table, Kai glimpses a key. Bea moved the key to the drawer.'
        revised = original.replace('Kai glimpses', 'Kai mentions')
        self.assertEqual(check_information_state(original, 'Kai', 'key')
                         ['checked_observation_count'], 1)
        self.assertEqual(check_information_state(revised, 'Kai', 'key')
                         ['checked_observation_count'], 0)
        self.assertEqual(check_information_state(original, 'Bea', 'key')
                         ['checked_observation_count'], 0)
        self.assertEqual(check_information_state(revised, 'Bea', 'key')
                         ['source_movements'],
                         check_information_state(original, 'Bea', 'key')['source_movements'])

    def test_pronoun_binding_refuses_ambiguous_or_unobserved_access(self):
        refused = (
            'Kai greeted Bea. At the table, he saw a key.',
            'Kai moved a box.\n\nAt the table, he saw a key.',
            'Kai moved a box. At the table, he did not see a key.',
            'Kai moved a box. At the table, he dreamed of a key.',
            'Kai moved a box. At the table, he glimpses a key in a dream.',
            'Bea moved a box. At the table, he glimpses a key.',
            'Kai moved a box. Bea claimed he glimpsed a key at the table.',
            'Kai moved a box. He glimpses a key.',
        )
        for source in refused:
            with self.subTest(source=source):
                self.assertEqual(check_information_state(source, 'Kai', 'key')
                                 ['checked_observation_count'], 0)

    def test_paid_gate_requires_checked_state_not_just_router_activation(self):
        receipt = dict(provider_calls=0, native_gold_used=False,
            longmemeval='SEALED_NOT_ACCESSED', specialized_treatment_present=True,
            cognition_context_present=True, checked_observation_count=0)
        with self.assertRaisesRegex(ValueError, 'treatment-presence'):
            require_treatment(receipt)
        receipt['checked_observation_count'] = 1
        self.assertTrue(require_treatment(receipt))

    def test_unrelated_task_preserves_direct_route(self):
        self.assertEqual(information_query('Summarize the story.'), None)
        self.assertIsNone(information_query('Where would She look for the key?'))
        prepared = self._prepared(question='Summarize the story.')
        self.assertTrue(prepared.plan.direct)
        self.assertIsNone(prepared.context)


if __name__ == '__main__':
    unittest.main()
