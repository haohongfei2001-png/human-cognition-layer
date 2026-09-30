import copy,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from scripts import development_reality_batch as drc
from scripts.development_confirmation_firewall import require_final_development_disjoint

def raw(answer,finish='stop'):return {'choices':[{'finish_reason':finish,'message':{'content':json.dumps(dict(answer=answer,source_citations=[],uncertainty='',assumptions='development interpretation'))}}]}
class DevelopmentRealityBatch(unittest.TestCase):
 def test_all_native_tasks_full_equal_source_no_gold_or_route_hints(self):
  for row in drc.load_cases()['cases']:
   arms,rec=drc.prepare_case(row)
   self.assertEqual(json.loads(arms['Base'][-1]['content'])['source'],row['source'])
   self.assertNotIn('"gold"',json.dumps(arms));self.assertNotIn('cot_content',json.dumps(arms))
   if rec['available']:
    self.assertEqual(json.loads(arms['HCL'][-1]['content']),dict(question=row['question'],task=row['task']))
    self.assertEqual(rec['actual_final_messages'],arms['HCL'])
   else:self.assertIsNone(arms['HCL']);self.assertEqual(rec['answer_provider_calls'],0)
 def test_philosophy_native_options_gold_never_in_fields(self):
  rows=[r for r in drc.load_cases()['cases'] if r['kind']=='mc']
  self.assertEqual(len(rows),6)
  for r in rows:self.assertEqual(r['source'],r['question']);self.assertIn(r['gold'],r['task']['choices']);self.assertFalse(r['cot_content_enters_model'])
 def test_guardian_positive_negative_and_duplicate_invalid(self):
  row=dict(kind='guardian',task=dict(chapter_vocabulary=['c'],detector_vocabulary=['l2.pov-leak']),gold=[dict(chapter_id='c',detector_id='l2.pov-leak')])
  self.assertTrue(drc.score(row,raw(row['gold']))['correct'])
  self.assertFalse(drc.score(row,raw([]))['correct'])
  self.assertFalse(drc.score(row,raw(row['gold']*2))['format_valid'])
  empty=dict(row,gold=[]);self.assertTrue(drc.score(empty,raw([]))['correct']);self.assertFalse(drc.score(empty,raw(row['gold']))['correct'])
 def test_arc_types_partial_wrong_and_truncated_not_success(self):
  row=dict(kind='arc',task=dict(entities=['A','B'],arc_type_vocabulary=['rise','fall']),gold={'A':'rise','B':'fall'})
  self.assertTrue(drc.score(row,raw(row['gold']))['correct'])
  changed=drc.score(row,raw({'A':'fall','B':'fall'}));self.assertFalse(changed['correct']);self.assertEqual(changed['units_correct'],1)
  for response in (raw({'A':'rise'}),raw(row['gold'],'length'),{},raw({'A':'rise','B':'maybe'})):self.assertFalse(drc.score(row,response)['correct'])
 def test_actual_preparation_failure_not_silent_base_substitution(self):
  row=copy.deepcopy(drc.load_cases()['cases'][0])
  with patch.object(drc,'prepare_person_context',side_effect=ValueError('bounded actual failure')):
   arms,rec=drc.prepare_case(row)
  self.assertIsNone(arms['HCL']);self.assertFalse(rec['available']);self.assertIn('bounded actual failure',rec['failure']);self.assertIsNone(rec['actual_final_messages'])
 def test_source_local_revision_changes_actual_input(self):
  row=copy.deepcopy(drc.load_cases()['cases'][0]);before,_=drc.prepare_case(row);row['source']+=' A later correction is explicitly recorded.'
  after,_=drc.prepare_case(row);self.assertNotEqual(before,after);self.assertEqual(json.loads(after['Base'][-1]['content'])['source'],row['source'])
 def test_final_isolation_new_development_systems_and_raw_hash(self):
  for candidate in ({'dataset_id':'TIGER-Lab/MMLU-Pro'},{'writing_system_id':'creader-narrative-bench'},{'source_sha256':drc.load_cases()['cases'][0]['source_sha256']}):
   with self.assertRaises(ValueError):require_final_development_disjoint(candidate)
 def test_failure_and_no_retry_budget_closed(self):
  package=dict(arms=['Base','HCL'],inputs={'x':{'Base':[dict(role='user',content='source')],'HCL':None}},preparations={'x':{'available':False}},runtime_sha256='stub',model='deepseek-v4-pro',maximum_output_tokens=8192,maximum_provider_calls=2,budget_cap_usd=1,evidence_level='DEVELOPMENT_ONLY')
  calls=[]
  def fail(req):calls.append(req);raise RuntimeError('transport failed')
  with tempfile.TemporaryDirectory() as tmp,patch.object(drc,'load_cases',return_value={'cases':[dict(case_id='x',kind='mc',gold='A')]}):
   p=Path(tmp)/'receipt.json'
   with self.assertRaises(RuntimeError):drc.execute(package,fail,p,{})
   r=json.loads(p.read_text());self.assertEqual(len(calls),1);self.assertEqual(r['authorization_remaining_usd'],0)
   with self.assertRaises(ValueError):drc.execute(package,fail,p,{})
 def test_no_call_for_frozen_h_preparation_failure(self):
  package=dict(arms=['HCL'],inputs={'x':{'HCL':None}},preparations={'x':{'available':False}},runtime_sha256='stub',maximum_provider_calls=0,budget_cap_usd=0,evidence_level='DEVELOPMENT_ONLY')
  with tempfile.TemporaryDirectory() as tmp,patch.object(drc,'load_cases',return_value={'cases':[dict(case_id='x',kind='mc',gold='A')]}):
   r=drc.execute(package,lambda _:self.fail('no invented H transport'),Path(tmp)/'r.json',{})
   self.assertEqual(r['provider_calls'],0);self.assertTrue(r['system_failures'][0]['score']['system_error']);self.assertEqual(r['status'],'COMPLETED_DEVELOPMENT_ONLY')
 def test_hard_cap_denies_transport(self):
  package=dict(arms=['Base'],inputs={'x':{'Base':[dict(role='user',content='source')]}},preparations={},runtime_sha256='stub',maximum_provider_calls=1,budget_cap_usd=0,evidence_level='DEVELOPMENT_ONLY')
  with tempfile.TemporaryDirectory() as tmp,patch.object(drc,'load_cases',return_value={'cases':[dict(case_id='x',kind='mc',gold='A')]}):
   with self.assertRaises(ValueError):drc.execute(package,lambda _:self.fail('hard cap'),Path(tmp)/'r.json',{})
if __name__=='__main__':unittest.main()
