import copy,json,unittest
from scripts.i02_source_holder_line_index_v3 import index_source,resolve_review,sha
from scripts.i02_source_holder_reference_budget_v5 import messages,resolve_review_v5
SOURCE='Mina reported her position. '+('Additional source context remains source context. '*20)+'\r\nMina reported uncertainty.\r\nMina reported declining the plan.'
QUESTION='What was reported and what remains unproved?'
ID='synthetic-distinct-reference-resource-test'
def review():
    return dict(source_id=ID,source_sha256=sha(SOURCE),question_sha256=sha(QUESTION),family_judgment='PASS',answerability_judgment='PASS',
        episodes=[dict(id='e'+str(i),start_line=i,end_line=i,evidence_kind='REPORTED_SPEECH',time_basis='SOURCE_ORDER_ONLY',analysis='A report, not private state.') for i in range(1,4)],
        obligations=[dict(id='o'+str(i),expectation=e,start_line=i,end_line=i,audit_question='Keep uncertainty.') for i,e in enumerate(('STATE','QUALIFY','AVOID'),1)],
        serious_unsupported_upgrades=['Unproved intention.'],unresolved_limits=['Event time not established.'],judge_limits='Provider-free authored fixture only.')
class ReferenceBudgetTests(unittest.TestCase):
    def resolve(self,r=None,source=SOURCE,question=QUESTION):return resolve_review_v5(review() if r is None else r,question,ID,source,index_source(ID,source))
    def test_positive_longer_focus_with_frozen_receiver_still_refusing(self):
        with self.assertRaises(ValueError):resolve_review(review(),QUESTION,ID,SOURCE,index_source(ID,SOURCE))
        got=self.resolve();self.assertGreater(len(got['episodes'][0]['quote']),500)
        self.assertLessEqual(len(got['episodes'][0]['quote']),1500)
        self.assertFalse(got['semantic_truth_verified']);self.assertFalse(got['story_time_verified']);self.assertFalse(got['confirmation_qualified'])
        self.assertEqual(got['provider_calls_authorized'],0)
    def test_full_ordinary_input_and_unambiguous_new_resource_contract(self):
        request=messages(QUESTION,ID,SOURCE);payload=json.loads(request[-1]['content'])
        self.assertEqual(''.join(x['text'] for x in payload['sources'][0]['lines']),SOURCE)
        self.assertNotIn('totaling at most 500',request[0]['content']);self.assertIn('totaling at most 1500',request[0]['content'])
        self.assertEqual(payload['reference_limits'],dict(max_anchor_characters=1500,max_reconstructed_characters=21000))
        self.assertEqual(payload['output_contract']['properties']['obligations']['items']['properties']['expectation']['enum'],['STATE','QUALIFY','AVOID'])
    def test_hash_range_actor_time_and_enum_boundaries_unchanged(self):
        for mutation in ('question','range','actor','time','enum','order'):
            r=review()
            if mutation=='question':r['question_sha256']=sha('other')
            if mutation=='range':r['episodes'][0]['end_line']=5
            if mutation=='actor':r['episodes'][0]['private_intention']='harm'
            if mutation=='time':r['episodes'][0]['time_basis']='ACTUAL_CAUSE'
            if mutation=='enum':r['obligations'][0]['expectation']='State the report.'
            if mutation=='order':r['episodes'].reverse()
            with self.assertRaises(ValueError):self.resolve(r)
    def test_local_revision_and_whole_source_range_still_refused(self):
        with self.assertRaises(ValueError):self.resolve(source=SOURCE+'\r\nA new report.')
        with self.assertRaises(ValueError):self.resolve(question='new question')
        source='x'*1501+'\r\nMina reported uncertainty.\r\nMina declined.';r=review();r['source_sha256']=sha(source)
        with self.assertRaises(ValueError):self.resolve(r,source=source)
        before=copy.deepcopy(r)
        with self.assertRaises(ValueError):self.resolve(r,source=source)
        self.assertEqual(r,before)
if __name__=='__main__':unittest.main()
