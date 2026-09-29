"""Generic G memory/relations/plan stay source-bound and versioned."""
import hashlib
import json
import unittest
from pathlib import Path

from scripts.serious_eval_arms_v3 import prepare_primary_arms_v3
from scripts.serious_eval_generic_workspace_v5 import (
    GenericEvidenceWorkspace, prepare_generic_final_v5, prepare_primary_arms_v5)


QUESTION = 'What did Mira know when she chose the road?'
SOURCE = ('At noon, Mira said the bridge was open. '
          'At dusk, Mira saw a notice that the bridge was closed. '
          'Mira chose the north road.')
SOURCE_ID = 'synthetic-source'
MAP = dict(source_index=[
    dict(id='e1', source_id=SOURCE_ID,
         quote='At noon, Mira said the bridge was open.'),
    dict(id='e2', source_id=SOURCE_ID,
         quote='At dusk, Mira saw a notice that the bridge was closed.')],
    relations=[dict(from_id='e2', to_id='e1', kind='CHALLENGES')],
    answer_plan=[dict(operation='RETRIEVE', evidence_ids=['e1', 'e2']),
                 dict(operation='CHECK_COUNTEREVIDENCE', evidence_ids=['e2']),
                 dict(operation='STATE_UNCERTAINTY', evidence_ids=[])],
    open_questions=['Whether Mira read the notice is source-reported only.'])


class GenericWorkspaceV5Tests(unittest.TestCase):
    def setUp(self):
        self.prepared = prepare_primary_arms_v5(QUESTION, SOURCE_ID, SOURCE)

    def final(self, mapped):
        return prepare_generic_final_v5(self.prepared,
            json.dumps(mapped, ensure_ascii=False))

    def test_positive_exact_final_composition_and_historical_c_p(self):
        older = prepare_primary_arms_v3(QUESTION, SOURCE_ID, SOURCE)
        self.assertEqual(self.prepared['C'], older['C'])
        self.assertEqual(self.prepared['P'], older['P'])
        map_input = json.loads(self.prepared['G_map'][-1]['content'])
        self.assertEqual(map_input['question'], QUESTION)
        self.assertEqual(map_input['sources'], older['ordinary_payload']['sources'])
        final = self.final(MAP)
        payload = json.loads(final[-1]['content'])
        self.assertEqual(payload['sources'], older['ordinary_payload']['sources'])
        self.assertEqual(set(payload['answer_fields']),
                         {'answer', 'source_citations', 'uncertainty', 'assumptions'})
        state = payload['generic_evidence_workspace']
        self.assertEqual(state['relation_semantics'], 'UNVERIFIED_MODEL_PROPOSAL')
        self.assertEqual(state['relations'], MAP['relations'])
        self.assertEqual(state['answer_plan'], MAP['answer_plan'])
        for row in state['source_index']:
            self.assertEqual(SOURCE[row['start']:row['end']], row['quote'])
            self.assertEqual(row['source_version'], 1)
        self.assertEqual(self.prepared['accounting']['G_map_calls'], 1)
        self.assertEqual(self.prepared['accounting']['G_final_calls'], 1)
        witness = json.loads(Path(
            'reports/HCL_I02_G_WORKSPACE_V5_PROVIDER_FREE_WITNESS.json').read_text())
        self.assertEqual(witness['G_final'], final)
        self.assertEqual(witness['G_map'], self.prepared['G_map'])
        self.assertEqual(witness['script_sha256'], hashlib.sha256(Path(
            'scripts/serious_eval_generic_workspace_v5.py').read_bytes()).hexdigest())

    def test_oracle_fields_duplicate_keys_and_unanchored_quote_fail(self):
        bad = json.loads(json.dumps(MAP))
        bad['source_index'][0]['gold'] = 'Mira intended to deceive.'
        with self.assertRaisesRegex(ValueError, 'source row'):
            self.final(bad)
        raw = '{"source_index":[],"relations":[],"answer_plan":[],"open_questions":[],"open_questions":[]}'
        with self.assertRaisesRegex(ValueError, 'duplicate generic workspace key'):
            prepare_generic_final_v5(self.prepared, raw)
        bad = json.loads(json.dumps(MAP))
        bad['source_index'][0]['quote'] = 'Mira privately wanted to deceive.'
        with self.assertRaisesRegex(ValueError, 'absent or ambiguous'):
            self.final(bad)
        with self.assertRaisesRegex(ValueError, 'absent or ambiguous'):
            self.final(dict(MAP, source_index=[
                dict(id='e1', source_id=SOURCE_ID, quote='Mira')],
                relations=[], answer_plan=[]))

    def test_relations_and_plan_only_reference_checked_quotes(self):
        bad = json.loads(json.dumps(MAP))
        bad['relations'][0]['to_id'] = 'e9'
        with self.assertRaisesRegex(ValueError, 'relation'):
            self.final(bad)
        bad = json.loads(json.dumps(MAP))
        bad['answer_plan'][0]['evidence_ids'] = ['e9']
        with self.assertRaisesRegex(ValueError, 'answer plan'):
            self.final(bad)
        bad = json.loads(json.dumps(MAP))
        bad['answer_plan'][0]['operation'] = 'DECLARE_PRIVATE_MOTIVE'
        with self.assertRaisesRegex(ValueError, 'answer plan'):
            self.final(bad)
        bad = json.loads(json.dumps(MAP))
        bad['relations'][0]['from_id'] = []
        with self.assertRaisesRegex(ValueError, 'relation'):
            self.final(bad)

    def test_source_revision_invalidates_memory_and_all_dependent_edges(self):
        workspace = GenericEvidenceWorkspace(self.prepared['ordinary_payload'])
        state = workspace.ingest(json.dumps(MAP))
        self.assertEqual(len(state['relations']), 1)
        workspace.revise_source(SOURCE_ID, SOURCE.replace('open', 'blocked'))
        with self.assertRaisesRegex(ValueError, 'stale'):
            workspace.snapshot()
        with self.assertRaisesRegex(ValueError, 'absent or ambiguous'):
            workspace.ingest(json.dumps(MAP))
        corrected = json.loads(json.dumps(MAP))
        corrected['source_index'][0]['quote'] = (
            'At noon, Mira said the bridge was blocked.')
        state = workspace.ingest(json.dumps(corrected))
        self.assertTrue(all(row['source_version'] == 2
                            for row in state['source_index']))


if __name__ == '__main__':
    unittest.main()
