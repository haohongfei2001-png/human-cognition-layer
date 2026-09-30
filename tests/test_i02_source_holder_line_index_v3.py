import json
import unittest
from scripts.i02_source_holder_line_index_v3 import index_source,reviewer_payload,resolve_review,sha,MAX_SOURCE_BYTES,messages
from scripts import run_i02_james_holder_once as james
from scripts import run_i02_gilman_holder_once as gilman

Q='How does Mina revise the plan?'
S='Earlier Mina trusted a plan.\r\nOther actor intention unknown.\r\nLater Mina declined the plan.\r\n'
def review():
    return dict(source_id='fixture',source_sha256=sha(S),question_sha256=sha(Q),family_judgment='PASS',answerability_judgment='PASS',episodes=[dict(id='e'+str(i),start_line=i,end_line=i,evidence_kind='NARRATOR_REPORT',time_basis='SOURCE_ORDER_ONLY',analysis='Reported view only; not a private motive.') for i in range(1,4)],obligations=[dict(id='o'+str(i),start_line=i,end_line=i,expectation=e,audit_question='Keep supported report separate from motive and uncertainty.') for i,e in enumerate(['STATE','QUALIFY','AVOID'],1)],serious_unsupported_upgrades=['Unsupported intention or moral truth.'],unresolved_limits=['Story time needs semantic review.'],judge_limits='No independent human review or semantic truth certificate.')
class SourceReferenceTests(unittest.TestCase):
    def setUp(self):self.index=index_source('fixture',S)
    def test_complete_ordinary_source_and_positive_grounded_reference_witness(self):
        payload=reviewer_payload('How does Mina revise the plan?',self.index)
        self.assertEqual(''.join(x['text'] for x in payload['sources'][0]['lines']),S)
        self.assertEqual(payload['sources'][0]['source_sha256'],sha(S))
        self.assertEqual(json.loads(messages('How does Mina revise the plan?','fixture',S)[-1]['content']),payload)
        got=resolve_review(review(),Q,'fixture',S,self.index)
        self.assertEqual(got['episodes'][0]['quote'],'Earlier Mina trusted a plan.')
        self.assertTrue(all(x['quote'] in S for x in got['obligations']))
        for key in ['story_time_verified','semantic_truth_verified','actor_or_motive_semantics_verified','confirmation_qualified','live_capacity_verified']:
            self.assertFalse(got[key])
        self.assertEqual(got['provider_calls_authorized'],0)
    def test_source_and_actor_boundaries_reject_stale_or_wrong_identity(self):
        for text in [S+'New reported view.\r\n',S.replace('Mina','Ravi')]:
            with self.assertRaises(ValueError):resolve_review(review(),Q,'fixture',text,self.index)
        with self.assertRaises(ValueError):resolve_review(review(),Q,'other',S,self.index)
        with self.assertRaises(ValueError):resolve_review(review(),'Which actor intended harm?','fixture',S,self.index)
        r=review();r['episodes'][0]['actor']='owner'
        with self.assertRaises(ValueError):resolve_review(r,Q,'fixture',S,self.index)
    def test_negative_inference_unknown_ranges_time_upgrade_and_missing_uncertainty(self):
        for field,value in [('start_line',99),('end_line',False),('time_basis','SOURCE_ORDER_PROVES_STORY_TIME')]:
            r=review();r['episodes'][0][field]=value
            with self.assertRaises(ValueError):resolve_review(r,Q,'fixture',S,self.index)
        r=review();r['obligations'][2]['expectation']='STATE'
        with self.assertRaises(ValueError):resolve_review(r,Q,'fixture',S,self.index)
        r=review();r['moral_truth']=True
        with self.assertRaises(ValueError):resolve_review(r,Q,'fixture',S,self.index)
    def test_local_revision_and_repeated_words_keep_occurrence_not_unique_quote_heuristic(self):
        repeated=S+S;index=index_source('fixture',repeated);r=review();r['source_sha256']=sha(repeated)
        got=resolve_review(r,Q,'fixture',repeated,index)
        self.assertEqual(got['episodes'][0]['source_start'],0)
        self.assertEqual(repeated.count(got['episodes'][0]['quote']),2)
        self.assertNotEqual(index['source_sha256'],self.index['source_sha256'])
    def test_whole_source_overflow_refusal_and_frozen_consumed_budgets(self):
        with self.assertRaises(ValueError):index_source('fixture','x'*(MAX_SOURCE_BYTES+1))
        self.assertEqual(gilman.load_package()['max_tokens'],8192)
        self.assertEqual(james.load_package()['max_tokens'],16384)
        self.assertEqual(james.load_package()['maximum_provider_calls'],1)
        self.assertFalse(james.load_package()['historical_budget_transfer'])
if __name__=='__main__':unittest.main()
