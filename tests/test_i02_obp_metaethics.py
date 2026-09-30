import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from scripts.i02_obp_metaethics_preflight import audit, SOURCE, OBLIGATIONS
from scripts.i02_source_qualification_v9 import require_obp_disjoint, require_qualified_confirmation_source_v9
from scripts.i02_obp_metaethics_source import reconstruct, audit_pdf
from scripts.serious_eval_semantic_score import validate_manifest, load_rubric
from scripts.i02_runtime_amendment_v6 import validate_current


class OBPSourceTests(unittest.TestCase):
    def test_complete_native_ordinary_input_and_no_treatment_claim(self):
        item = json.loads(SOURCE.read_text()); gate = audit()
        self.assertEqual(json.loads(gate['h_final_messages'][-1]['content'])['narrative'], item['source_text'])
        self.assertTrue(gate['full_ordinary_input_equal_for_cpg'])
        self.assertTrue(gate['g_final_original_source_present'])
        self.assertTrue(gate['h_direct'])
        self.assertFalse(gate['h_specialized_treatment_present'])
        self.assertFalse(gate['h_hnew_calls_allowed'])
        self.assertFalse(gate['difficulty_qualified'])
        self.assertFalse(gate['independent_confirmation_qualified'])
        self.assertEqual(gate['provider_calls'], 0)

    def test_rights_question_source_and_obligation_mutations_fail_closed(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'mutant.json'
            for field, value in [('license', 'unspecified'), ('source_unit', 'WHOLE_CHAPTER'),
                                  ('source_text', 'The theorist intends harm.'),
                                  ('ordinary_question', 'Do all theorists approve theft?'),
                                  ('independent_confirmation_qualified', True)]:
                item = json.loads(SOURCE.read_text()); item[field] = value
                p.write_text(json.dumps(item))
                with patch('scripts.i02_obp_metaethics_preflight.SOURCE', p):
                    with self.assertRaises(ValueError): audit()
            manifest = json.loads(OBLIGATIONS.read_text())
            manifest['obligations'][0]['audit_question'] = 'Demand automatic moral truth.'
            p.write_text(json.dumps(manifest))
            with patch('scripts.i02_obp_metaethics_preflight.OBLIGATIONS', p):
                with self.assertRaises(ValueError): audit()

    def test_development_author_system_and_literal_mirror_never_confirmation(self):
        item = json.loads(SOURCE.read_text())
        for candidate in ({'author_id': a} for a in ('mark-dimmock', 'andrew-fisher', 'dimmock-fisher')):
            with self.assertRaises(ValueError): require_obp_disjoint(candidate)
        for candidate in ({'writing_system_id': item['writing_system_id']},
                          {'template_id': item['template_id']},
                          {'author_id': 'renamed', 'source_text': item['source_text']}):
            with patch('scripts.i02_source_qualification_v9.require_qualified_confirmation_source_v8') as old:
                with self.assertRaises(ValueError):
                    require_qualified_confirmation_source_v9({}, candidate, {}, '.', 'HEAD')
                old.assert_not_called()
        with patch('scripts.i02_source_qualification_v9.require_qualified_confirmation_source_v8', return_value=True) as old:
            self.assertTrue(require_qualified_confirmation_source_v9({}, {'author_id': 'other'}, {}, '.', 'HEAD'))
            old.assert_called_once()

    def test_source_first_negative_inference_and_local_revision_not_silently_accepted(self):
        manifest = json.loads(OBLIGATIONS.read_text())
        validate_manifest(manifest, load_rubric())
        self.assertEqual([o['expectation'] for o in manifest['obligations']], ['STATE', 'QUALIFY', 'AVOID'])
        revised = json.loads(json.dumps(manifest))
        revised['sources'][0]['text'] = revised['sources'][0]['text'].replace(
            'this does not entail a love of stealing on their part.', 'this entails a love of stealing on their part.')
        with self.assertRaises(ValueError): validate_manifest(revised, load_rubric())
        self.assertEqual(manifest, json.loads(OBLIGATIONS.read_text()))

    def test_fixed_source_reconstruction_no_arbitrary_extraction_or_pdf(self):
        item = json.loads(SOURCE.read_text())
        pages = {205: '7. Metaethics and Stealing\n' + item['source_text'], 206: '',
                 208: '10. ' + item['ordinary_question'] + ' KEY TERMINOLOGY'}
        self.assertEqual(reconstruct(pages)['source_text'], item['source_text'])
        pages[206] = 'Unsupported extra premise.'
        with self.assertRaises(ValueError): reconstruct(pages)
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'wrong.pdf'; p.write_bytes(b'%PDF wrong edition')
            with self.assertRaises(ValueError): audit_pdf(p)

    def test_historical_runtime_and_reconstruction_receipts_not_upgraded(self):
        self.assertTrue(validate_current())
        r = json.loads(Path('reports/HCL_I02_OBP_METAETHICS_RECONSTRUCTION.json').read_text())
        self.assertEqual(r['author_unit_reconstruction'], 'EXACT_NORMALIZED_MATCH')
        self.assertFalse(r['confirmation_qualified'])
        self.assertEqual(r['provider_calls'], 0)
        self.assertNotIn('Russell', json.loads(SOURCE.read_text())['source_text'])


if __name__ == '__main__': unittest.main()
