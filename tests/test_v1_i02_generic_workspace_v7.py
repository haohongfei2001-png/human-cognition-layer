"""Provider-free exact-source G v7 interface repair and historical boundary."""
import json
import unittest

from scripts.serious_eval_arms_v3 import prepare_primary_arms_v3
from scripts.serious_eval_generic_workspace_v6 import (
    prepare_generic_final_v6, prepare_primary_arms_v6)
from scripts.serious_eval_generic_workspace_v7 import (
    BoundedGenericEvidenceWorkspaceV7, prepare_generic_final_v7,
    prepare_primary_arms_v7)


QUESTION = 'What can the group do after the report deadline changes?'
SOURCE_ID = 'ordinary-source'
LONG_QUOTE = (
    'The instructor said the group could still submit a revised report on '
    'Friday, but the earlier peer feedback did not describe the missing work '
    'and the instructor had not promised any grade adjustment or removal.'
)
SOURCE = (LONG_QUOTE + ' The students agreed to check each citation before '
          'submitting. Another student only guessed that removal was possible.')
MAP = dict(source_index=[dict(id='e1', source_id=SOURCE_ID,
                              quote=LONG_QUOTE)],
           relations=[], answer_plan=[dict(operation='RETRIEVE',
                                          evidence_ids=['e1']),
                                      dict(operation='STATE_UNCERTAINTY',
                                           evidence_ids=['e1'])],
           open_questions=['Whether the instructor will adjust grades is unknown.'])


class BoundedGenericWorkspaceV7Tests(unittest.TestCase):
    def setUp(self):
        self.prepared = prepare_primary_arms_v7(QUESTION, SOURCE_ID, SOURCE)

    def final(self, value):
        return prepare_generic_final_v7(self.prepared,
                                        json.dumps(value, ensure_ascii=False))

    def test_positive_ordinary_input_and_v6_historical_regression(self):
        old = prepare_primary_arms_v3(QUESTION, SOURCE_ID, SOURCE)
        self.assertEqual(self.prepared['C'], old['C'])
        self.assertEqual(self.prepared['P'], old['P'])
        self.assertGreater(len(LONG_QUOTE), 180)
        self.assertLessEqual(len(LONG_QUOTE), 1500)
        self.assertEqual(json.loads(self.prepared['G_map'][-1]['content'])['sources'],
                         old['ordinary_payload']['sources'])
        final = self.final(MAP)
        payload = json.loads(final[-1]['content'])
        self.assertEqual(payload['sources'], old['ordinary_payload']['sources'])
        self.assertEqual(set(payload['answer_fields']),
                         {'answer', 'source_citations', 'uncertainty', 'assumptions'})
        state = payload['generic_evidence_workspace']
        self.assertEqual(state['schema'], 'hcl-i02-generic-source-workspace-v7')
        self.assertEqual(SOURCE[state['source_index'][0]['start']:
                                state['source_index'][0]['end']], LONG_QUOTE)
        self.assertEqual(state['relation_semantics'], 'UNVERIFIED_MODEL_PROPOSAL')
        v6 = prepare_primary_arms_v6(QUESTION, SOURCE_ID, SOURCE)
        with self.assertRaisesRegex(ValueError, 'source row bound'):
            prepare_generic_final_v6(v6, json.dumps(MAP))

    def test_negative_inference_and_extra_fields_fail_closed(self):
        bad = json.loads(json.dumps(MAP))
        bad['source_index'][0]['quote'] = 'The instructor wanted to punish them.'
        with self.assertRaisesRegex(ValueError, 'absent or ambiguous'):
            self.final(bad)
        bad = json.loads(json.dumps(MAP))
        bad['source_index'][0]['motive'] = 'punishment'
        with self.assertRaisesRegex(ValueError, 'source row'):
            self.final(bad)
        bad = json.loads(json.dumps(MAP))
        bad['answer_plan'][0]['operation'] = 'DECLARE_PRIVATE_INTENT'
        with self.assertRaisesRegex(ValueError, 'answer plan'):
            self.final(bad)
        bad = json.loads(json.dumps(MAP))
        bad['source_index'][0]['id'] = 'e9'
        with self.assertRaisesRegex(ValueError, 'source row bound'):
            self.final(bad)
        with self.assertRaisesRegex(ValueError, 'byte bound'):
            prepare_generic_final_v7(self.prepared, 'x' * 3501)

    def test_multisource_composition_revision_and_failed_replacement(self):
        ordinary = dict(self.prepared['ordinary_payload'])
        ordinary['sources'] = ordinary['sources'] + [
            dict(source_id='second-source',
                 text='The secretary said the Friday deadline applied to all groups.')]
        workspace = BoundedGenericEvidenceWorkspaceV7(ordinary)
        value = json.loads(json.dumps(MAP))
        value['source_index'].append(dict(id='e2', source_id='second-source',
            quote='The secretary said the Friday deadline applied to all groups.'))
        value['relations'] = [dict(from_id='e2', to_id='e1', kind='QUALIFIES')]
        checked = workspace.ingest(json.dumps(value))
        self.assertEqual(len(checked['source_index']), 2)
        self.assertEqual(checked['relations'][0]['kind'], 'QUALIFIES')
        workspace.revise_source('second-source',
            'The secretary said the Monday deadline applied to all groups.')
        with self.assertRaisesRegex(ValueError, 'stale'):
            workspace.snapshot()
        value['source_index'][1]['quote'] = (
            'The secretary said the Monday deadline applied to all groups.')
        workspace.ingest(json.dumps(value))
        value['source_index'][1]['quote'] = 'The secretary privately disliked them.'
        with self.assertRaisesRegex(ValueError, 'absent or ambiguous'):
            workspace.ingest(json.dumps(value))
        with self.assertRaisesRegex(ValueError, 'absent or stale'):
            workspace.snapshot()


if __name__ == '__main__':
    unittest.main()
