"""Generic goal/intent boundary without changing C or consumed v2 bytes."""

import json
import unittest

from scripts.serious_eval_arms_v2 import prepare_primary_arms_v2
from scripts.serious_eval_arms_v3 import (
    prepare_generic_final_v3, prepare_primary_arms_v3, provider_free_witness,
)


SOURCE = ('Mira said she wanted to keep the path safe. Under one proposed '
          'plan she installed lamps, and visitors felt safer. Under another '
          'proposed plan she installed a fence, and a visitor was hurt. '
          'No source says Mira intended the injury.')
QUESTION = 'What does the source establish about Mira’s goal and the injury?'


class ComparatorV3Tests(unittest.TestCase):
    def test_ordinary_input_fairness_and_direct_c_historical_stability(self):
        v2 = prepare_primary_arms_v2(QUESTION, 'story', SOURCE)
        v3 = prepare_primary_arms_v3(QUESTION, 'story', SOURCE)
        self.assertEqual(v3['C'], v2['C'])
        self.assertEqual(v3['ordinary_payload'], v2['ordinary_payload'])
        for arm in ('C', 'P', 'G_map'):
            payload = json.loads(v3[arm][1]['content'])
            self.assertEqual(payload['question'], QUESTION)
            self.assertEqual(payload['sources'][0], {'source_id': 'story', 'text': SOURCE})
        self.assertEqual(v3['accounting'], v2['accounting'])
        self.assertIn('UNQUALIFIED', v3['qualification'])
        self.assertEqual(v2['qualification'], 'C_P_G_V2_PROVIDER_FREE_CANDIDATE_UNQUALIFIED')

    def test_goal_and_harmful_intent_are_distinct_in_process_and_map(self):
        arms = prepare_primary_arms_v3(QUESTION, 'story', SOURCE)
        self.assertIn('explicit reported aim', arms['P'][0]['content'])
        self.assertIn('not proof of a separate harmful intention', arms['P'][0]['content'])
        self.assertIn('explicit goals, plans, norms', arms['G_map'][0]['content'])
        self.assertIn('unknown specific harmful intention', arms['G_map'][0]['content'])
        self.assertNotIn('Mira', arms['P'][0]['content'])
        self.assertNotIn('Mira', arms['G_map'][0]['content'])

    def test_grounded_generic_map_reaches_full_final_input(self):
        map_response = {'source_index': [{'source_id': 'story',
            'quote': 'Mira said she wanted to keep the path safe.'}],
            'open_questions': ['Did Mira foresee a visitor getting hurt?']}
        witness = provider_free_witness(QUESTION, 'story', SOURCE, map_response)
        payload = json.loads(witness['G_final'][1]['content'])
        self.assertEqual(payload['sources'][0]['text'], SOURCE)
        self.assertEqual(payload['answer_fields'],
                         ['answer', 'source_citations', 'uncertainty', 'assumptions'])
        self.assertEqual(payload['generic_evidence_workspace'], map_response)
        self.assertIn('narrower uncertainty', witness['G_final'][0]['content'])

    def test_unsupported_map_and_wrong_runtime_are_rejected(self):
        arms = prepare_primary_arms_v3(QUESTION, 'story', SOURCE)
        with self.assertRaisesRegex(ValueError, 'grounded'):
            prepare_generic_final_v3(arms, json.dumps({'source_index': [
                {'source_id': 'story', 'quote': 'Mira intended injury.'}],
                'open_questions': []}))
        with self.assertRaisesRegex(ValueError, 'v3 prepared'):
            prepare_generic_final_v3(prepare_primary_arms_v2(QUESTION, 'story', SOURCE),
                json.dumps({'source_index': [], 'open_questions': []}))


if __name__ == '__main__':
    unittest.main()
