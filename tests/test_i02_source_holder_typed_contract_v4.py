import copy,json
import unittest
from scripts.i02_source_holder_typed_contract_v4 import messages,output_contract,resolve_review_v4
from scripts.i02_source_holder_line_index_v3 import index_source
from scripts.i02_source_holder_v3_calibration_fixture import load_fixture
from tests.test_i02_source_holder_v3_calibration import literal_review

class TypedAuditorContractTests(unittest.TestCase):
    def test_complete_long_input_with_explicit_categorical_contract_and_no_gold(self):
        f=load_fixture();request=messages(f['ordinary_question'],f['source_id'],f['source_text']);p=json.loads(request[-1]['content'])
        self.assertEqual(''.join(x['text'] for x in p['sources'][0]['lines']),f['source_text'])
        enum=p['output_contract']['properties']['obligations']['items']['properties']['expectation']
        self.assertEqual(enum,dict(type='string',enum=['STATE','QUALIFY','AVOID']))
        self.assertNotIn('expected_episode_lines',json.dumps(p));self.assertIn('Never put a sentence',request[0]['content'])
        self.assertEqual(p['question_sha256'],f['question_sha256'])
    def test_positive_resolution_keeps_occurrence_uncertainty_and_no_semantic_promotion(self):
        f=load_fixture();v=literal_review(f);got=resolve_review_v4(v,f['ordinary_question'],f['source_id'],f['source_text'],index_source(f['source_id'],f['source_text']))
        self.assertEqual(got['episodes'][1]['start_line'],402)
        self.assertFalse(got['story_time_verified']);self.assertFalse(got['semantic_truth_verified'])
        self.assertFalse(got['confirmation_qualified']);self.assertEqual(got['provider_calls_authorized'],0)
    def test_observed_freeform_failure_not_normalized_and_revisions_fail_closed(self):
        f=load_fixture();index=index_source(f['source_id'],f['source_text']);v=literal_review(f)
        v['obligations'][0]['expectation']='State the January view solely as reported speech.'
        before=copy.deepcopy(v)
        with self.assertRaises(ValueError):resolve_review_v4(v,f['ordinary_question'],f['source_id'],f['source_text'],index)
        self.assertEqual(v,before)
        with self.assertRaises(ValueError):resolve_review_v4(literal_review(f),'different task',f['source_id'],f['source_text'],index)
        c=output_contract();c['properties']['source_id']['type']='integer'
        self.assertEqual(output_contract()['properties']['source_id']['type'],'string')
if __name__=='__main__':unittest.main()
