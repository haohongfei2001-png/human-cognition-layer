import json,tempfile,unittest
from pathlib import Path
from scripts import development_reality_batch008 as m
class Batch008Tests(unittest.TestCase):
 def response(self,text):return dict(model='deepseek-v4-pro',usage=dict(prompt_tokens=1,completion_tokens=1,prompt_cache_hit_tokens=0,prompt_cache_miss_tokens=1),choices=[dict(finish_reason='stop',message=dict(content=text))])
 def output(self,answer='A development fixture interpretation.',source_id='development-source'):
  row=m.cases()['cases'][0];return json.dumps(dict(answer=answer,source_citations=[dict(source_id=source_id,quote=row['source'],version=1)],uncertainty='Narrative interpretation only.',assumptions='Not universal moral truth.'))
 def test_subset_exact_native_and_no_output_or_treatment_selection(self):
  import hashlib
  rows=m.cases()['cases'];self.assertEqual(len(rows),6)
  for row in rows:self.assertEqual(row['source'],row['native']['story']);self.assertEqual(row['title'],row['native']['title']);self.assertEqual(row['gold'],row['native']['moral']);self.assertEqual(row['native_row_sha256'],m.digest(row['native']))
  self.assertIn('no native moral/length/H-treatment/output filter',m.cases()['selection'])
 def test_both_arms_full_original_title_question_and_no_gold_key(self):
  p=m.build_package()
  for row in m.cases()['cases']:
   for arm in ('Base','HCL_local_or_fallback'):
    wire=p['inputs'][row['case_id']][arm];strings=[s for item in wire if item['role']=='user' for s in m._strings(json.loads(item['content']))]
    for s in (row['source'],row['title'],row['question']):self.assertIn(s,strings)
    self.assertNotIn('"gold"',json.dumps(wire));self.assertNotIn('"author_reference"',json.dumps(wire))
 def test_call_budget_includes_all_six_graders_and_worst_serialized_answer_ceiling(self):
  p=m.build_package();self.assertEqual(p['maximum_provider_calls'],18);self.assertLessEqual(p['all_call_worst_peak_reservation_usd'],m.CAP);self.assertEqual(p['retries'],0);self.assertFalse(p['historical_budget_transfer'])
  for row in m.cases()['cases']:
   req=m.grading_request(row,dict(Base='😀'*2000,HCL='😀'*2000));m.validate_json_mode_request(req);self.assertEqual(req['thinking']['type'],'disabled');self.assertNotIn('Base',req['messages'][-1]['content']);self.assertNotIn('HCL',req['messages'][-1]['content'])
 def test_no_private_universal_truth_or_final_certification(self):
  self.assertIn('not universal moral truth',m.GRADING_CONTRACT);self.assertIn('not verified real private',m.POLICY);self.assertIn('same-family judge not independent',m.build_package()['scoring'])
 def test_grader_uncertainty_partial_and_shape_are_distinct(self):
  g={'x':{'verdict':'UNCERTAIN','rationale':'ambiguous annotation'},'y':{'verdict':'PARTIAL','rationale':'secondary lesson'}};self.assertEqual(m.grade_result(self.response(json.dumps(g))),g)
  g['x']['verdict']='true';self.assertIsNone(m.grade_result(self.response(json.dumps(g))));self.assertIsNone(m.grade_result(self.response('not JSON')))
 def test_format_quote_audit_and_score_are_separate(self):
  row=m.cases()['cases'][0];s=m.score(row,self.response(self.output()),m.base_messages(row));self.assertTrue(s['format_valid']);self.assertTrue(s['source_delivery_valid']);self.assertNotIn('native_correct',s)
  s=m.score(row,self.response(self.output(source_id='invented')),m.base_messages(row));self.assertTrue(s['format_valid']);self.assertFalse(s['source_delivery_valid'])
  self.assertFalse(m.score(row,self.response(self.output(answer='x'*2001)),m.base_messages(row))['format_valid'])
 def test_stub_entire_run_grades_pairs_once_and_all_raw_costs_saved(self):
  calls=[]
  def provider(req):
   calls.append(req)
   if req['thinking']['type']=='disabled':text=json.dumps({k:dict(verdict='UNCERTAIN',rationale='Fixture, no semantic judgment.') for k in ('x','y')})
   else:text=json.dumps(dict(answer='Fixture interpretation.',source_citations=[],uncertainty='Not a real judgment.',assumptions='Authored fake backend.'))
   return self.response(text)
  with tempfile.TemporaryDirectory() as d:
   f=Path(d)/'r.json';r=m.execute(m.build_package(),provider,f,{});self.assertEqual(r['provider_calls'],18);self.assertEqual(len(r['results']),12);self.assertEqual(sum(x['phase']=='grading' for x in r['attempts']),6);self.assertEqual(r['authorization_remaining_usd'],0)
   for a in r['attempts']:self.assertIn('request_raw',a);self.assertIn('response_raw',a);self.assertIn('rated_peak_cost_usd',a)
   for i in r['results']:self.assertEqual(i['score']['native_verdict'],'UNCERTAIN');self.assertFalse(i['score']['native_correct']);self.assertFalse(i['score']['independent_semantic_certification'])
   with self.assertRaises(ValueError):m.execute(m.build_package(),provider,f,{})
 def test_invalid_grader_stops_without_regrade_or_next_pair(self):
  calls=[]
  def provider(req):
   calls.append(req);return self.response('broken' if req['thinking']['type']=='disabled' else json.dumps(dict(answer='Fixture.',source_citations=[],uncertainty='',assumptions='')))
  with tempfile.TemporaryDirectory() as d:
   f=Path(d)/'r.json'
   with self.assertRaises(m.TransportGateError):m.execute(m.build_package(),provider,f,{})
   r=json.loads(f.read_text());self.assertEqual(len(calls),3);self.assertEqual(r['authorization_remaining_usd'],0);self.assertEqual(r['status'],'FAILED_NO_RETRY');self.assertIn('response_raw',r['attempts'][-1])
 def test_failed_http_cost_unknown_and_no_retry(self):
  calls=[]
  class Failure(Exception):status_code=400;body={'error':{'message':'bad JSON contract'}}
  def provider(req):calls.append(req);raise Failure()
  with tempfile.TemporaryDirectory() as d:
   f=Path(d)/'r.json'
   with self.assertRaises(m.TransportGateError):m.execute(m.build_package(),provider,f,{})
   r=json.loads(f.read_text());self.assertEqual(len(calls),1);self.assertIsNone(r['rated_peak_cost_usd']);self.assertIsNone(r['estimated_actual_cost_usd']);self.assertEqual(r['attempts'][0]['error_receipt']['http_status'],400)
 def test_hard_cap_before_call_and_exact_activation(self):
  p=m.build_package();p['maximum_provider_calls']=0
  with tempfile.TemporaryDirectory() as d:
   with self.assertRaises(m.TransportGateError):m.execute(p,lambda _:self.fail('forbidden call'),Path(d)/'r.json',{})
  template=m.TEMPLATE.read_text();self.assertIn('python -m scripts.development_reality_batch008 --execute --history --publisher',template);self.assertIn('hcl-drc008-once.yml/runs',template);self.assertNotIn('scripts.development_reality_batch007',template)
if __name__=='__main__':unittest.main()
