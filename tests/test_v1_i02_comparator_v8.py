"""Provider-free strong-comparator candidate and citation compatibility."""
import json
import unittest

from scripts.serious_eval_arms_v8 import (
    call_spec_v8, prepare_generic_final_v8, prepare_primary_arms_v8)
from scripts.serious_eval_generic_workspace_v7 import prepare_primary_arms_v7
from scripts.serious_eval_semantic_score import validate_answer


SOURCE_ID = 'ordinary-source'
SOURCE = ('Mira said she wanted the group to check the Friday deadline. '
          'Leo later guessed she intended to blame him, but she did not say that.')
QUESTION = 'What did Mira say she wanted, and is Leo’s claim established?'
MAP = dict(source_index=[dict(id='e1', source_id=SOURCE_ID,
    quote='Mira said she wanted the group to check the Friday deadline.')],
    relations=[], answer_plan=[], open_questions=[])


class ComparatorV8Tests(unittest.TestCase):
    def test_ordinary_input_strong_native_budget_and_citation_shape(self):
        prepared = prepare_primary_arms_v8(QUESTION, SOURCE_ID, SOURCE)
        prior = prepare_primary_arms_v7(QUESTION, SOURCE_ID, SOURCE)
        self.assertEqual(prepared['ordinary_payload'], prior['ordinary_payload'])
        self.assertEqual(prepared['G_map'], prior['G_map'])
        for phase in ('C', 'P'):
            self.assertEqual(prepared[phase][1], prior[phase][1])
            self.assertIn('exactly source_id and quote',
                prepared[phase][0]['content'])
        final = prepare_generic_final_v8(prepared, json.dumps(MAP))
        self.assertIn('exactly source_id and quote', final[0]['content'])
        self.assertEqual(json.loads(final[-1]['content'])['sources'],
                         prepared['ordinary_payload']['sources'])
        good = dict(answer='Mira reported a deadline check; Leo only guessed.',
            source_citations=[dict(source_id=SOURCE_ID,
                quote='Leo later guessed she intended to blame him')],
            uncertainty='Mira’s private motive is unknown.', assumptions='')
        self.assertTrue(validate_answer(good, {SOURCE_ID: SOURCE}))
        bad = dict(good, source_citations=[dict(source_id=SOURCE_ID,
            quotes=['Leo later guessed she intended to blame him'])])
        with self.assertRaisesRegex(ValueError, 'exactly one quote key'):
            validate_answer(bad, {SOURCE_ID: SOURCE})
        specs = prepared['call_specs']
        self.assertEqual(set(specs), {'C', 'P', 'G_map', 'G_final'})
        self.assertTrue(all(spec['thinking'] == {'type': 'enabled'} and
            spec['reasoning_effort'] == 'high' and spec['max_tokens'] == 8192
            for spec in specs.values()))

    def test_negative_inference_and_version_boundary(self):
        prepared = prepare_primary_arms_v8(QUESTION, SOURCE_ID, SOURCE)
        bad = json.loads(json.dumps(MAP))
        bad['source_index'][0]['quote'] = 'Mira wanted Leo punished.'
        with self.assertRaisesRegex(ValueError, 'absent or ambiguous'):
            prepare_generic_final_v8(prepared, json.dumps(bad))
        legacy = prepare_primary_arms_v7(QUESTION, SOURCE_ID, SOURCE)
        with self.assertRaisesRegex(ValueError, 'v8 prepared comparator'):
            prepare_generic_final_v8(legacy, json.dumps(MAP))
        with self.assertRaisesRegex(ValueError, 'unknown comparator phase'):
            call_spec_v8('H')
        spec = call_spec_v8('C')
        spec['thinking']['type'] = 'disabled'
        self.assertEqual(call_spec_v8('C')['thinking']['type'], 'enabled')


if __name__ == '__main__':
    unittest.main()
