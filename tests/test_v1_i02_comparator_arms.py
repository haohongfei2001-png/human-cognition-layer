"""Provider-free ordinary-input, fairness and source boundary for I02 candidates."""
import json
import unittest

from scripts.serious_eval_arms import prepare_generic_final, prepare_primary_arms
from scripts.serious_eval_contract import FIELDS


QUESTION = 'What does the source support about Mira changing her plan?'
SOURCE = ('At noon Mira told Noor, "I plan to check the draft." '
    'At dusk Noor said, "Mira skipped it." Mira later said, "I did check it."')


class ComparatorPreparationTests(unittest.TestCase):
    def test_positive_same_ordinary_input_across_three_arms(self):
        prepared = prepare_primary_arms(QUESTION, 'story-1', SOURCE)
        users = [json.loads(prepared[arm][1]['content']) for arm in ('C', 'P', 'G_map')]
        self.assertEqual(users[0], users[1])
        self.assertEqual(users[1], users[2])
        self.assertEqual(users[0]['answer_fields'], list(FIELDS))
        self.assertEqual(users[2]['sources'][0]['text'], SOURCE)
        self.assertEqual(prepared['accounting']['G_map_calls'] +
            prepared['accounting']['G_final_calls'], 2)
        self.assertEqual(prepared['qualification'], 'C_P_G_CANDIDATES_UNQUALIFIED_NO_PROVIDER_CALL')

    def test_generic_map_composes_without_losing_original_or_opposition(self):
        prepared = prepare_primary_arms(QUESTION, 'story-1', SOURCE)
        mapping = dict(source_index=[
            dict(source_id='story-1', quote='Noor said, "Mira skipped it."', kind='REPORT'),
            dict(source_id='story-1', quote='Mira later said, "I did check it."', kind='REPORT')],
            open_questions=['Which report is accurate?'])
        final = prepare_generic_final(prepared, json.dumps(mapping))
        payload = json.loads(final[1]['content'])
        self.assertEqual(payload['sources'][0]['text'], SOURCE)
        self.assertEqual(len(payload['generic_evidence_workspace']['source_index']), 2)
        self.assertEqual(payload['answer_fields'], list(FIELDS))
        self.assertIn('never independent evidence', final[0]['content'])

    def test_no_foreign_or_paraphrased_quote_in_generic_map(self):
        prepared = prepare_primary_arms(QUESTION, 'story-1', SOURCE)
        for source_id, quote in [('hidden', 'At noon Mira told Noor'),
                ('story-1', 'Mira definitely skipped the draft')]:
            mapping = dict(source_index=[dict(source_id=source_id, quote=quote)],
                open_questions=[])
            with self.assertRaisesRegex(ValueError, 'not grounded'):
                prepare_generic_final(prepared, json.dumps(mapping))

    def test_bad_map_refuses_instead_of_silent_drop(self):
        prepared = prepare_primary_arms(QUESTION, 'story-1', SOURCE)
        for raw in ('garbage', '{}', json.dumps(dict(source_index=[], open_questions='none'))):
            with self.assertRaises(ValueError):
                prepare_generic_final(prepared, raw)

    def test_bounded_source_and_question(self):
        with self.assertRaisesRegex(ValueError, 'bounded authorized'):
            prepare_primary_arms(QUESTION, 'story-1', 'x' * 64001)
        with self.assertRaisesRegex(ValueError, 'bounded ordinary'):
            prepare_primary_arms('', 'story-1', SOURCE)


if __name__ == '__main__':
    unittest.main()
