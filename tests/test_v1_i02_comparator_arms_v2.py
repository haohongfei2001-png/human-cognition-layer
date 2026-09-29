"""Post-calibration map interface avoids an answer-shaped intermediate call."""
import json
import unittest

from scripts.serious_eval_arms_v2 import (
    prepare_generic_final, prepare_primary_arms_v2)


class ComparatorMapV2Tests(unittest.TestCase):
    def test_same_complete_source_and_question_distinct_intermediate_contract(self):
        source = 'Kai saw the key on the table. Bea said it was moved to the desk.'
        arms = prepare_primary_arms_v2('Where would Kai look for the key?', 's1', source)
        c = json.loads(arms['C'][1]['content'])
        p = json.loads(arms['P'][1]['content'])
        g = json.loads(arms['G_map'][1]['content'])
        self.assertEqual(c, p)
        for row in (c, p, g):
            self.assertEqual(row['question'], c['question'])
            self.assertEqual(row['sources'], c['sources'])
        self.assertEqual(c['answer_fields'],
                         ['answer', 'source_citations', 'uncertainty', 'assumptions'])
        self.assertNotIn('answer_fields', g)
        self.assertEqual(g['workspace_fields'], ['source_index', 'open_questions'])
        self.assertIn('do not answer', arms['G_map'][0]['content'])
        self.assertEqual(arms['accounting']['G_map_calls'] +
                         arms['accounting']['G_final_calls'], 2)
        self.assertIn('UNQUALIFIED', arms['qualification'])

    def test_source_anchored_map_feeds_original_final_contract(self):
        source = 'Kai saw the key on the table. Bea said it was moved to the desk.'
        arms = prepare_primary_arms_v2('Where would Kai look for the key?', 's1', source)
        raw = json.dumps(dict(source_index=[dict(source_id='s1',
            quote='Kai saw the key on the table.')],
            open_questions=['Did Kai receive Bea\'s report?']))
        final = prepare_generic_final(arms, raw)
        payload = json.loads(final[1]['content'])
        self.assertEqual(payload['sources'][0]['text'], source)
        self.assertEqual(payload['answer_fields'],
                         ['answer', 'source_citations', 'uncertainty', 'assumptions'])
        self.assertEqual(payload['generic_evidence_workspace']['open_questions'],
                         ["Did Kai receive Bea's report?"])
        with self.assertRaisesRegex(ValueError, 'generic map shape'):
            prepare_generic_final(arms, json.dumps(dict(answer='desk')))


if __name__ == '__main__':
    unittest.main()
