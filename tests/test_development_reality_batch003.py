"""Development only: fair complete inputs, bounds/no retry, annotation limits."""
import copy,json,tempfile,time,unittest
from pathlib import Path
from unittest.mock import patch
import scripts.development_reality_batch003 as m

def raw(content,finish='stop',model='deepseek-v4-pro',tokens=20):
 return dict(model=model,created=int(time.time()),usage=dict(prompt_tokens=100,completion_tokens=tokens,prompt_cache_hit_tokens=0,prompt_cache_miss_tokens=100),choices=[dict(finish_reason=finish,message=dict(content=json.dumps(content)))])

def answer(row,citations=[]):return dict(answer=row['gold'] if row['kind']=='label' else 'A scholarly explanation.',source_citations=citations,uncertainty='Annotation and interpretation uncertainty.',assumptions='No moral truth.')

class DevelopmentBatch003Tests(unittest.TestCase):
 def test_frozen_build_complete_sources_queries_vocabulary_no_gold_checklist_hints(self):
  p=m.build_package();self.assertLessEqual(p['all_call_worst_peak_reservation_usd'],p['budget_cap_usd']);self.assertEqual(p['maximum_provider_calls'],22);self.assertEqual(p['retries'],0)
  for row in m.cases()['cases']:
   inputs=p['inputs'][row['case_id']]
   for arm in ('Base','HCL_fallback'):
    text='\n'.join(x['content'] for x in inputs[arm]);leaves=[s for x in inputs[arm] if x['role']=='user' for s in m._strings(json.loads(x['content']))]
    self.assertIn(row['source'],leaves);self.assertIn(row['question'],leaves)
    if row['kind']=='philosophy':self.assertNotIn(row['gold'],text);self.assertTrue(all(c not in text for c in row['checklist']))
    else:self.assertIn('agency',text);self.assertIn('experience',text)
   self.assertNotIn('golden_answer',json.dumps(inputs['translation_request']))
 def test_valid_label_invalid_unfinished_and_common_quote_audit(self):
  row=m.cases()['cases'][0];a=m.format_score(row,raw(answer(row)));self.assertTrue(a['native_correct']);self.assertTrue(a['source_delivery_valid'])
  self.assertFalse(m.format_score(row,raw(answer(row),finish='length'))['native_correct'])
  a=m.format_score(row,raw(answer(row,['fabricated quote'])));self.assertTrue(a['native_correct']);self.assertFalse(a['source_delivery_valid'])
 def test_native_checklist_grade_requires_five_booleans_and_reasoning(self):
  row=m.cases()['cases'][-1];g=m.grade_score(row,raw(dict(passes=[True]*5,reasons=['substance supplied']*5)));self.assertEqual(g['units_correct'],5);self.assertIn('NOT_EXPERT_TRUTH',g['interpretation'])
  for obj in (dict(passes=[1]*5,reasons=['x']*5),dict(passes=[True]*4,reasons=['x']*4),dict(passes=[True]*5,reasons=['x']*5,extra=True)):
   self.assertFalse(m.grade_score(row,raw(obj))['valid'])
 def test_all_phases_bounded_fallback_no_hidden_second_extraction_or_promotion(self):
  p=m.build_package();rows=m.cases()['cases'];sent=[];counter={'answer':0}
  def provider(request):
   sent.append(request)
   if request['thinking']['type']=='disabled':return raw(dict(candidates=[]))
   if request['messages'][0]['content']==m.JUDGE_POLICY:return raw(dict(passes=[True]*5,reasons=['stub only']*5))
   question=json.loads(request['messages'][-1]['content'])['question'];row=next(x for x in rows if x['question']==question);counter['answer']+=1;return raw(answer(row))
  with tempfile.TemporaryDirectory() as t:
   r=m.execute(p,provider,str(Path(t)/'receipt.json'),{})
   self.assertEqual(r['provider_calls'],22);self.assertEqual(counter['answer'],12);self.assertEqual(len(sent),22)
   self.assertEqual(len(r['results']),12);self.assertTrue(all(x.get('actual_treatment_present') is False for x in r['results'] if x['arm']=='HCL'))
   self.assertEqual(r['authorization_remaining_usd'],0);self.assertTrue(r['results_are_development_only']);self.assertEqual(r['longmemeval'],'SEALED_NOT_ACCESSED')
   self.assertEqual(sum(x['phase']=='translation' for x in r['attempts']),6)
   with self.assertRaises(ValueError):m.execute(p,provider,str(Path(t)/'receipt.json'),{})
 def test_transport_failure_or_model_drift_never_falls_back_or_retries(self):
  for failure in ('provider','model','usage'):
   p=m.build_package();calls=[]
   def provider(request):
    calls.append(request)
    if failure=='provider':raise RuntimeError('failure')
    return raw(answer(m.cases()['cases'][0]),model='wrong' if failure=='model' else p['model'],tokens=request['max_tokens']+33 if failure=='usage' else 20)
   with tempfile.TemporaryDirectory() as t:
    path=Path(t)/'r.json'
    with self.assertRaises(m.TransportGateError):m.execute(p,provider,str(path),{})
    self.assertEqual(len(calls),1);self.assertEqual(json.loads(path.read_text())['status'],'FAILED_NO_RETRY')
 def test_hard_cap_blocks_first_call_with_complete_zero_call_receipt(self):
  p=m.build_package();p['budget_cap_usd']=0;calls=[]
  with tempfile.TemporaryDirectory() as t:
   path=Path(t)/'r.json'
   with self.assertRaises(m.TransportGateError):m.execute(p,lambda request:calls.append(request),str(path),{})
   self.assertFalse(calls);self.assertEqual(json.loads(path.read_text())['provider_calls'],0)
 def test_declared_usage_margin_reserved_without_silent_clamping(self):
  row=m.cases()['cases'][0];r=m.req(m.base_messages(row),'answer',row);tokens,res=m.budget(r)
  self.assertAlmostEqual(res,m.bound(r)[1]+32*m.RATES['output']/1e6)
  self.assertEqual(r['max_tokens'],8192);self.assertNotIn('service_tier',r)
 def test_corrupted_frozen_inputs_source_config_and_runtime_detected(self):
  p=m.build_package()
  with patch.object(Path,'read_text',return_value=json.dumps(dict(p,maximum_provider_calls=23))):
   with self.assertRaises(ValueError):m.load_package()

if __name__=='__main__':unittest.main()
