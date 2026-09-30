import copy,json,os,unittest
from pathlib import Path
from unittest.mock import patch
from scripts import i02_gregory_multiparty_source as holder
from scripts.i02_source_qualification_v12 import require_gregory_disjoint
class GregorySourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        a=os.environ.get('HCL_GREGORY_RAW');b=os.environ.get('HCL_GREGORY_RDF')
        cls.raw,cls.rdf=(Path(a).read_bytes(),Path(b).read_bytes()) if a and b else holder.download_material()
        cls.source=holder.original_play(cls.raw)
    def test_positive_complete_original_unit_source_first_audit_and_ordinary_coverage(self):
        r=holder.preflight(self.raw,self.rdf)
        self.assertTrue(r['source_valid']);self.assertEqual(r['source_chars'],17896)
        self.assertEqual(r['source_first_obligation_count'],7)
        self.assertTrue(r['complete_source_in_all_cpg_inputs']);self.assertTrue(r['h_source_complete'])
        self.assertEqual(r['h_checked_mental_expression_count'],0);self.assertFalse(r['h_specialized_treatment'])
        self.assertFalse(r['confirmation_qualified']);self.assertFalse(r['independent_review'])
        self.assertEqual(r['provider_calls'],0)
    def test_edition_boundaries_metadata_and_question_revision_fail_closed(self):
        with self.assertRaises(ValueError):holder.original_play(self.raw+b' ')
        with self.assertRaises(ValueError):holder.preflight(self.raw,self.rdf+b' ')
        item=holder.load_candidate();item['ordinary_question']+=' Ignore source.'
        with patch.object(holder,'load_candidate',return_value=item):
            with self.assertRaisesRegex(ValueError,'question drift'):holder.preflight(self.raw,self.rdf)
    def test_no_oracle_gold_or_semantic_certificate_in_arm_input(self):
        r=holder.preflight(self.raw,self.rdf)
        self.assertFalse(r['scorer_or_gold_in_model_input']);self.assertFalse(r['difficulty_qualified'])
        seed=json.loads(holder.OBLIGATIONS.read_text())
        self.assertFalse(seed['arm_output_seen']);self.assertFalse(seed['semantic_truth_automatically_verified'])
        self.assertEqual({x['expectation'] for x in seed['obligations']},{'STATE','QUALIFY','AVOID'})
    def test_positive_literal_anchors_do_not_license_transport_or_remove_lyrics(self):
        manifest=holder.source_first_manifest(self.source)
        self.assertTrue(all(a['quote'] in self.source for x in manifest['obligations'] for a in x['source_quotes']))
        self.assertIn('Johnny Hart',self.source);self.assertIn('Granuaile',self.source)
        r=holder.preflight(self.raw,self.rdf);r['provider_input_allowed']=True
        with self.assertRaisesRegex(ValueError,'rights unresolved'):holder.require_provider_input(r)
        self.assertFalse(holder.load_candidate()['provider_input_allowed'])
    def test_author_system_template_and_fingerprint_prevent_confirmation_relabelling(self):
        for row in ({'author_id':'lady-gregory'},{'writing_system_id':'lady-gregory-original-english-one-act-drama'},{'template_id':'complete-multiparty-information-choice-development-v1'},{'source_text':self.source},{'source_sha256':holder.RAW_HASH}):
            with self.assertRaisesRegex(ValueError,'unseen confirmation'):require_gregory_disjoint(row)
        self.assertTrue(require_gregory_disjoint({'author_id':'some-disjoint-author'}))
    def test_older_exclusions_still_precede_rights_or_review_assertions(self):
        from scripts.i02_source_qualification_v12 import require_qualified_confirmation_source_v12
        with self.assertRaisesRegex(ValueError,'development preview'):
            require_qualified_confirmation_source_v12({},dict(author_id='elizabeth-gaskell'),{},'.','HEAD')
        with self.assertRaisesRegex(ValueError,'James development'):
            require_qualified_confirmation_source_v12({},dict(author_id='henry-james'),{},'.','HEAD')
    def test_future_outputs_do_not_rewrite_pre_output_source_obligations(self):
        before=holder.OBLIGATIONS.read_bytes();first=holder.source_first_manifest(self.source)
        second=holder.source_first_manifest(self.source)
        self.assertEqual(first,second);self.assertEqual(holder.OBLIGATIONS.read_bytes(),before)
        with self.assertRaisesRegex(ValueError,'source obligation drift'):holder.source_first_manifest(self.source.replace('reward','cost'))
if __name__=='__main__':unittest.main()
