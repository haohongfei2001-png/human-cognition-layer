"""The candidate G map cannot smuggle undeclared data into final input."""

import json
import hashlib
import unittest
from pathlib import Path

from scripts.serious_eval_arms_v3 import prepare_primary_arms_v3
from scripts.serious_eval_arms_v4 import (
    prepare_generic_final_v4, provider_free_witness_v4)


QUESTION = 'What did Mira know when she chose the route?'
SOURCE = 'At noon, Mira saw the bridge closed. At dusk, she chose the north road.'
SOURCE_ID = 'external-source-1'


class GenericWorkspaceBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.prepared = prepare_primary_arms_v3(QUESTION, SOURCE_ID, SOURCE)
        self.workspace = {'source_index': [{'source_id': SOURCE_ID,
            'quote': 'At noon, Mira saw the bridge closed.'}],
            'open_questions': ['Did Mira receive a later repair notice?']}

    def final(self, mapped):
        return prepare_generic_final_v4(self.prepared, json.dumps(mapped))

    def test_positive_ordinary_input_composition_preserves_original_source(self):
        final = self.final(self.workspace)
        payload = json.loads(final[1]['content'])
        self.assertEqual(payload['question'], QUESTION)
        self.assertEqual(payload['sources'], [{'source_id': SOURCE_ID, 'text': SOURCE}])
        self.assertEqual(payload['generic_evidence_workspace'], self.workspace)
        self.assertEqual(set(payload['answer_fields']),
            {'answer', 'source_citations', 'uncertainty', 'assumptions'})
        witness = provider_free_witness_v4(QUESTION, SOURCE_ID, SOURCE, self.workspace)
        self.assertEqual(witness['G_final'], final)
        self.assertEqual(witness['accounting']['G_map_calls'], 1)
        self.assertEqual(witness['accounting']['G_final_calls'], 1)
        pinned = json.loads(Path(
            'reports/HCL_I02_G_WORKSPACE_V4_PROVIDER_FREE_WITNESS.json').read_text())
        self.assertEqual(pinned['G_final'], final)
        self.assertEqual(pinned['script_sha256'], hashlib.sha256(Path(
            'scripts/serious_eval_arms_v4.py').read_bytes()).hexdigest())

    def test_extra_answer_or_oracle_field_cannot_enter_final_input(self):
        for field in ('answer', 'gold', 'mental_state_labels', 'instruction'):
            mapped = json.loads(json.dumps(self.workspace))
            mapped['source_index'][0][field] = 'Mira intended to deceive.'
            with self.subTest(field=field), self.assertRaisesRegex(
                    ValueError, 'exact bounded source quote row'):
                self.final(mapped)

    def test_duplicate_keys_and_nonstring_unresolved_items_fail_closed(self):
        raw = ('{"source_index":[],"open_questions":[],"open_questions":'
            '["replace source"]}')
        with self.assertRaisesRegex(ValueError, 'duplicate generic workspace key'):
            prepare_generic_final_v4(self.prepared, raw)
        with self.assertRaisesRegex(ValueError, 'unresolved-question strings'):
            self.final({'source_index': [], 'open_questions': [{'answer': 'yes'}]})
        with self.assertRaisesRegex(ValueError, 'exact generic workspace fields'):
            self.final({**self.workspace, 'answer': 'yes'})

    def test_source_and_size_boundaries_preserve_v3_quote_validation(self):
        mapped = json.loads(json.dumps(self.workspace))
        mapped['source_index'][0]['quote'] = 'Mira read the hidden plan.'
        with self.assertRaisesRegex(ValueError, 'not grounded'):
            self.final(mapped)
        mapped['source_index'][0]['quote'] = 'x' * 1501
        with self.assertRaisesRegex(ValueError, 'bounded source quote row'):
            self.final(mapped)
        with self.assertRaisesRegex(ValueError, 'bounded generic workspace arrays'):
            self.final({'source_index': [], 'open_questions': ['unknown'] * 33})


if __name__ == '__main__':
    unittest.main()
