import json,tempfile,unittest
from pathlib import Path
from scripts import development_reader_live_entry as live
from scripts.witness_development_conditional_reader_v15 import SOURCE_LINES,DERIVED_LINES
class ReaderLiveGateTests(unittest.TestCase):
 def raw(self,content,phase=0,tokens=100,finish='stop'):
  return dict(model='deepseek-v4-pro',created=1790802000,usage=dict(prompt_tokens=100,completion_tokens=tokens,prompt_cache_hit_tokens=0),choices=[dict(finish_reason=finish,message=dict(content=json.dumps(content)))])
 def candidates(self):return dict(candidates=[dict(source_id='meeting',quote=q,kind='event',content=dict(canonical_statement=d)) for q,d in zip(SOURCE_LINES,DERIVED_LINES)])
 def test_full_real_pipeline_fake_transport_calls_count_original_source_and_conditional_treatment(self):
  calls=[]
  def provider(req):
   calls.append(req);return self.raw(self.candidates() if len(calls)==1 else dict(answer='Conditional source report.',source_citations=[],uncertainty='Translations unverified.',assumptions='Declared model only.'))
  with tempfile.TemporaryDirectory() as tmp:
   r=live.execute(live.build_package(),provider,Path(tmp)/'r.json')
   self.assertEqual(r['provider_calls'],2);self.assertIn('COMPLETED',r['status']);self.assertTrue(r['preparation']['checked_treatment_present']);self.assertFalse(r['preparation']['semantic_certification'])
   self.assertEqual(calls[0]['thinking'],{'type':'disabled'});self.assertEqual(calls[1]['reasoning_effort'],'high');self.assertEqual(r['authorization_remaining_usd'],0);self.assertLess(r['reserved_usd'],live.CAP)
   with self.assertRaises(ValueError):live.execute(live.build_package(),provider,Path(tmp)/'r.json')
   self.assertEqual(len(calls),2)
 def test_invalid_translation_or_truncation_no_final_call_or_retry(self):
  for raw in (self.raw(dict(candidates=[])),self.raw(self.candidates(),finish='length')):
   calls=[]
   with tempfile.TemporaryDirectory() as tmp:
    p=Path(tmp)/'r.json'
    with self.assertRaises(ValueError):live.execute(live.build_package(),lambda req:calls.append(req) or raw,p)
    r=json.loads(p.read_text());self.assertEqual(r['provider_calls'],1);self.assertEqual(r['authorization_remaining_usd'],0);self.assertEqual(len(calls),1)
 def test_server_one_token_overshoot_explicitly_reserved_and_larger_excess_refused(self):
  req=live.cfg([], 'translation');_,base=live.bound(req);_,margin=live.budget_bound(req)
  self.assertGreater(margin,base)
  for tokens,allowed in ((4097,True),(4129,False)):
   calls=[]
   def provider(req):
    calls.append(req)
    return self.raw(self.candidates(),tokens=tokens) if len(calls)==1 else self.raw(dict(answer='conditional',source_citations=[],uncertainty='unknown',assumptions='hypothesis'))
   with tempfile.TemporaryDirectory() as tmp:
    path=Path(tmp)/'r.json'
    if allowed:self.assertEqual(live.execute(live.build_package(),provider,path)['provider_calls'],2)
    else:
     with self.assertRaises(ValueError):live.execute(live.build_package(),provider,path)
     self.assertEqual(len(calls),1)
 def test_bad_final_format_closes_without_retry_or_efficacy_claim(self):
  calls=[]
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp)/'r.json'
   with self.assertRaises(ValueError):live.execute(live.build_package(),lambda req:calls.append(req) or self.raw(self.candidates() if len(calls)==1 else dict(answer='missing fields')),p)
   r=json.loads(p.read_text());self.assertEqual(len(calls),2);self.assertEqual(r['authorization_remaining_usd'],0);self.assertFalse(r['semantic_quality_claim']);self.assertFalse(r['answer_gain_claim'])
if __name__=='__main__':unittest.main()
