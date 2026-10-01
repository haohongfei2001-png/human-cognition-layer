import copy,json,tempfile,unittest
from pathlib import Path
from scripts import development_reality_batch007 as m

class Batch007Tests(unittest.TestCase):
 def test_frozen_template_invokes_correct_batch_and_unique_certified_activation(self):
  template=m.TEMPLATE.read_text();self.assertIn('python -m scripts.development_reality_batch007 --execute --history --publisher',template);self.assertNotIn('scripts.development_reality_batch004',template);self.assertIn('hcl-drc007-once.yml/runs',template);self.assertEqual(m.WORKFLOW.name,'hcl-drc007-once.yml')
 def test_package_all_possible_costs_call_limit_freeze_without_provider(self):
  p=m.build_package();self.assertLessEqual(p['maximum_provider_calls'],12);self.assertLessEqual(p['all_call_worst_peak_reservation_usd'],m.CAP);self.assertEqual(p['arms'],['Base','HCL']);self.assertEqual(p['retries'],0);self.assertFalse(p['historical_budget_transfer'])
 def test_whole_inputs_and_native_vocabulary_both_arms_no_gold_keys(self):
  p=m.build_package()
  for row in m.cases()['cases']:
   f=p['inputs'][row['case_id']]
   for arm in ['Base','HCL_local_or_fallback']:
    messages=f[arm];strings=[s for item in messages if item['role']=='user' for s in m._strings(json.loads(item['content']))];self.assertIn(row['source'],strings);self.assertIn(row['question'],strings);self.assertIn(row['task'],[json.loads(item['content']).get('task') for item in messages if item['role']=='user']);self.assertNotIn('"gold"',json.dumps(messages))
 def test_original_freeform_not_invented_options_gold_or_rubric_to_arms(self):
  for row in m.cases()['cases']:
   self.assertEqual(row['source'],row['native']['scenario']);self.assertEqual(row['question'],row['native']['question']);self.assertIn(row['native']['tier'],['hard','expert']);self.assertNotIn('labels',row['task']);self.assertNotIn('options',row['task'])
   for arm in ['Base','HCL_local_or_fallback']:
    wire=json.dumps(m.build_package()['inputs'][row['case_id']][arm]);self.assertNotIn('expected_answer',wire);self.assertNotIn('answer_aliases',wire);self.assertNotIn('rubric',wire)
 def response(self,content):return dict(model='deepseek-v4-pro',choices=[dict(finish_reason='stop',message=dict(content=content))],usage=dict(prompt_tokens=10,completion_tokens=10,prompt_cache_hit_tokens=0,prompt_cache_miss_tokens=10))
 def output(self,row,id='development-source'):return json.dumps(dict(answer=row['gold'],source_citations=[dict(source_id=id,quote=row['source'],version=1)],uncertainty='Source conventions only.',assumptions='Not private or moral truth.'))
 def test_actual_source_audit_not_guessed_namespace_and_raw_label_independent(self):
  row=m.cases()['cases'][0];messages=m.base_messages(row);self.assertTrue(m.score(row,self.response(self.output(row)),messages)['native_correct'])
  bad=m.score(row,self.response(self.output(row,'invented')),messages);self.assertTrue(bad['native_correct']);self.assertFalse(bad['source_delivery_valid'])
 def test_length_unfinished_invalid_and_native_ambiguity_not_forced_wrong(self):
  row=m.cases()['cases'][0];r=self.response(self.output(row));r['choices'][0]['finish_reason']='length';self.assertFalse(m.score(row,r,m.base_messages(row))['native_correct'])
  r=self.response(json.dumps(dict(answer=' '.join(['unresolved']*30),source_citations=[],uncertainty='',assumptions='')));s=m.score(row,r,m.base_messages(row));self.assertEqual(s['native_verdict'],'AMBIGUOUS_UNSCORED');self.assertIsNone(s['native_score_outcome']['correct'])
 def test_unmodified_author_scorer_negation_word_boundary_and_ambiguity(self):
  from scripts.vendor.drc007_tom_benchmark.models import Scenario
  from scripts.vendor.drc007_tom_benchmark.scorer import score_response
  synthetic=Scenario(id='authored-scorer',category='false_belief',name='Scorer boundary',tier='easy',complexity=dict(belief_depth=1,num_agents=1),scenario='A synthetic token-scoring fixture.',question='Where?',expected_answer='basket',answer_aliases=[],rubric='Token matching only.',explanation='No native gold or case modified.')
  self.assertTrue(score_response(synthetic,'will look in basket').correct);self.assertFalse(score_response(synthetic,'not basket').correct);self.assertFalse(score_response(synthetic,'basketball').correct);self.assertIsNone(score_response(synthetic,' '.join(['unresolved']*30)).correct)
 def test_stub_bounded_run_raw_requests_all_preparation_attempts_once(self):
  p=m.build_package();calls=[]
  def provider(req):
   calls.append(req)
   return self.response('{"candidates":[]}' if req['thinking']['type']=='disabled' else json.dumps(dict(answer='Unresolved',source_citations=[],uncertainty='unknown',assumptions='source convention')))
  with tempfile.TemporaryDirectory() as d:
   output=Path(d)/'receipt.json';r=m.execute(p,provider,output,{'provider_calls':0});self.assertEqual(r['status'],'COMPLETED_DEVELOPMENT_ONLY');self.assertEqual(len(calls),p['maximum_provider_calls']);self.assertEqual(r['provider_calls'],len(calls));self.assertEqual(len(r['results']),12);self.assertEqual(r['authorization_remaining_usd'],0)
   for x in r['results']:
    if x['arm']=='HCL':self.assertFalse(x['actual_treatment_present']);self.assertEqual(x['preparation']['extraction_calls'],0);self.assertEqual(len(x['preparation']['extraction_responses']),0)
   with self.assertRaises(ValueError):m.execute(p,provider,output,{})
 def test_failed_http_unknown_cost_and_body_saved_no_retry(self):
  p=m.build_package();calls=[]
  class Failure(Exception):status_code=400;request_id='id';body={'error':{'message':'bad JSON contract'}}
  def provider(req):calls.append(req);raise Failure()
  with tempfile.TemporaryDirectory() as d:
   f=Path(d)/'r.json'
   with self.assertRaises(m.TransportGateError):m.execute(p,provider,f,{})
   r=json.loads(f.read_text());self.assertEqual(len(calls),1);self.assertIsNone(r['estimated_actual_cost_usd']);self.assertIsNone(r['rated_peak_cost_usd']);self.assertEqual(r['attempts'][0]['error_receipt']['http_status'],400);self.assertEqual(r['authorization_remaining_usd'],0)
 def test_hard_cap_precedes_provider(self):
  p=m.build_package();p['maximum_provider_calls']=0
  with tempfile.TemporaryDirectory() as d:
   f=Path(d)/'r.json'
   with self.assertRaises(m.TransportGateError):m.execute(p,lambda _:self.fail('call forbidden'),f,{})
   self.assertEqual(json.loads(f.read_text())['provider_calls'],0)
if __name__=='__main__':unittest.main()
