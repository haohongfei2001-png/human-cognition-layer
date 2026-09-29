"""Compact G-map interface after the frozen EPC v5 length failure."""
import json
import unittest

from scripts.serious_eval_arms_v3 import prepare_primary_arms_v3
from scripts.serious_eval_generic_workspace_v6 import (
    CompactGenericEvidenceWorkspace, prepare_generic_final_v6,
    prepare_primary_arms_v6)


QUESTION = 'What did Mira know when she chose the road?'
SOURCE_ID = 'ordinary-source'
SOURCE = ('At noon, Mira said the bridge was open. '
          'At dusk, Mira saw a notice that the bridge was closed. '
          'Mira chose the north road.')
MAP = dict(source_index=[
    dict(id='e1', source_id=SOURCE_ID,
         quote='At noon, Mira said the bridge was open.'),
    dict(id='e2', source_id=SOURCE_ID,
         quote='At dusk, Mira saw a notice that the bridge was closed.')],
    relations=[dict(from_id='e2', to_id='e1', kind='CHALLENGES')],
    answer_plan=[dict(operation='COMPARE', evidence_ids=['e1', 'e2']),
                 dict(operation='STATE_UNCERTAINTY', evidence_ids=['e2'])],
    open_questions=['Whether Mira read the notice is not established.'])


class CompactGenericWorkspaceV6Tests(unittest.TestCase):
    def setUp(self):
        self.prepared = prepare_primary_arms_v6(QUESTION, SOURCE_ID, SOURCE)

    def final(self, data):
        return prepare_generic_final_v6(self.prepared,
            json.dumps(data, ensure_ascii=False))

    def test_positive_ordinary_entry_composition_and_historical_c_p(self):
        previous = prepare_primary_arms_v3(QUESTION, SOURCE_ID, SOURCE)
        self.assertEqual(self.prepared['C'], previous['C'])
        self.assertEqual(self.prepared['P'], previous['P'])
        self.assertEqual(json.loads(self.prepared['G_map'][-1]['content'])['sources'],
                         previous['ordinary_payload']['sources'])
        final = self.final(MAP)
        payload = json.loads(final[-1]['content'])
        self.assertEqual(payload['sources'], previous['ordinary_payload']['sources'])
        self.assertEqual(set(payload['answer_fields']),
                         {'answer', 'source_citations', 'uncertainty', 'assumptions'})
        state = payload['generic_evidence_workspace']
        self.assertEqual(state['schema'], 'hcl-i02-generic-source-workspace-v6')
        self.assertEqual(state['relation_semantics'], 'UNVERIFIED_MODEL_PROPOSAL')
        self.assertEqual(state['relations'], MAP['relations'])
        self.assertEqual(state['answer_plan'], MAP['answer_plan'])
        for row in state['source_index']:
            self.assertEqual(SOURCE[row['start']:row['end']], row['quote'])

    def test_compact_bounds_and_unsupported_inference_fail_closed(self):
        bad = json.loads(json.dumps(MAP))
        bad['source_index'][0]['quote'] = 'Mira privately wanted to deceive.'
        with self.assertRaisesRegex(ValueError, 'absent or ambiguous'):
            self.final(bad)
        bad = json.loads(json.dumps(MAP))
        bad['source_index'][0]['gold'] = 'deception'
        with self.assertRaisesRegex(ValueError, 'source row'):
            self.final(bad)
        bad = json.loads(json.dumps(MAP))
        bad['source_index'][0]['quote'] = 'A' * 181
        with self.assertRaisesRegex(ValueError, 'source row bound'):
            self.final(bad)
        bad = json.loads(json.dumps(MAP))
        bad['source_index'][0]['id'] = 'e9'
        with self.assertRaisesRegex(ValueError, 'source row bound'):
            self.final(bad)
        bad = json.loads(json.dumps(MAP))
        bad['answer_plan'][0]['operation'] = 'DECLARE_INTENTION'
        with self.assertRaisesRegex(ValueError, 'answer plan'):
            self.final(bad)
        bad = json.loads(json.dumps(MAP))
        bad['relations'][0]['to_id'] = 'e8'
        with self.assertRaisesRegex(ValueError, 'relation'):
            self.final(bad)
        with self.assertRaisesRegex(ValueError, 'byte bound'):
            prepare_generic_final_v6(self.prepared, 'x' * 3501)
        with self.assertRaisesRegex(ValueError, 'JSON required'):
            prepare_generic_final_v6(self.prepared, '{"source_index": [')

    def test_local_revision_and_failed_replacement_clear_state(self):
        workspace = CompactGenericEvidenceWorkspace(
            self.prepared['ordinary_payload'])
        workspace.ingest(json.dumps(MAP))
        workspace.revise_source(SOURCE_ID, SOURCE.replace('open', 'blocked'))
        with self.assertRaisesRegex(ValueError, 'stale'):
            workspace.snapshot()
        corrected = json.loads(json.dumps(MAP))
        corrected['source_index'][0]['quote'] = (
            'At noon, Mira said the bridge was blocked.')
        workspace.ingest(json.dumps(corrected))
        with self.assertRaisesRegex(ValueError, 'source row bound'):
            invalid = json.loads(json.dumps(corrected))
            invalid['source_index'][0]['id'] = 'e9'
            workspace.ingest(json.dumps(invalid))
        with self.assertRaisesRegex(ValueError, 'absent or stale'):
            workspace.snapshot()


if __name__ == '__main__':
    unittest.main()
