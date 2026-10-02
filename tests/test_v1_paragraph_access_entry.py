import json,unittest
from hcl.cognition import CognitionWorkspace
from hcl.cognition.ordinary_access import prepare_ordinary_access
SOURCE='Mara said, “I believe the road is clear.” Niko Reed heard Mara\'s last statement. Tess did not hear Mara\'s last statement. Tess later read Mara\'s last statement.'
QUERY='Compare the source-reported information routes and unknown mental states.'
class NoCall:
 def complete_json(self,*a,**k):raise AssertionError('no extraction')
class ParagraphAccessTests(unittest.TestCase):
 def entry(self,source=SOURCE):
  w=CognitionWorkspace();w.put_source('report',source);return w,w.prepare_reader_entry(QUERY,source_ids=('report',),backend=NoCall())
 def test_same_paragraph_real_B02_B01_exact_source_and_coordinates(self):
  w,p=self.entry();d=json.loads(p.messages[-1]['content']);state=d['checked_reported_communication'];self.assertTrue(d['checked_epistemic']);self.assertEqual(d['sources'][0]['text'],SOURCE);self.assertEqual(p.receipt['extraction_calls'],0)
  views={v['source_named_actor']:v for v in state['views']};self.assertEqual(views['Niko Reed']['access_audit'][0]['status'],'REPORTED_EXPOSURE');self.assertEqual(views['Tess']['access_audit'][0]['status'],'REPORTED_LATER_EXPOSURE');self.assertIn('derived statement ordinal',state['audit_coordinates'])
  bindings=state['original_quote_bindings'];self.assertEqual(len(bindings),4);self.assertEqual([b['original_source_line'] for b in bindings],[1]*4)
  for b in bindings:self.assertEqual(SOURCE[b['start']:b['start']+len(b['quote'])],b['quote'])
  self.assertFalse(state['private_state_established']);self.assertTrue(all(v['knowledge']=='NOT_ESTABLISHED' for v in views.values()))
 def test_period_in_speech_never_becomes_new_narrator_receipt(self):
  text='Mara said, "I believe the road is clear. Niko heard Tess\'s last statement." Tess did not hear Mara\'s last statement.'
  state=prepare_ordinary_access(text,source_id='s',version=1)['state'];self.assertNotIn('Niko',state['source_local_actor_aliases']);self.assertEqual(len(state['original_quote_bindings']),2);self.assertEqual(next(v for v in state['views'] if v['source_named_actor']=='Tess')['visible_derived_statements'],[])
 def test_unmatched_quote_or_remainder_conditional_prevents_partial_access(self):
  for text in [SOURCE+' It was hypothetical.', 'If '+SOURCE, SOURCE+' Unless Niko misunderstood.',SOURCE.replace('clear.”','clear."'), SOURCE+' Mara said, "Unknown.', SOURCE.replace('Niko Reed heard','Perhaps Niko Reed heard'),SOURCE.replace('Tess later read','Tess later did not read')]:
   d=prepare_ordinary_access(text,source_id='s',version=1);self.assertIsNone(d['state']);self.assertEqual(d['checked_operations'],0)
 def test_public_availability_addressing_and_conflict_remain_unknown(self):
  text='Mara said, "Hello." Niko Reed said, "Hi." Mara\'s last statement was publicly available. Mara sent their last statement privately to Niko Reed.'
  state=prepare_ordinary_access(text,source_id='s',version=1)['state'];view=next(v for v in state['views'] if v['source_named_actor']=='Niko Reed');self.assertNotIn('Person1: Hello.',view['visible_derived_statements']);self.assertEqual(view['knowledge'],'NOT_ESTABLISHED')
  conflict=prepare_ordinary_access(SOURCE+" Niko Reed did not hear Mara's last statement.",source_id='s',version=1)['state'];self.assertEqual(next(v for v in conflict['views'] if v['source_named_actor']=='Niko Reed')['access_audit'][0]['status'],'CONFLICTING_EXPOSURE_REPORTS')
 def test_revision_invalidates_and_source_identity_does_not_join(self):
  w,p=self.entry();w.put_source('other',SOURCE);q=w.prepare_reader_entry(QUERY,source_ids=('other',));self.assertEqual(json.loads(q.messages[-1]['content'])['checked_reported_communication']['source_id'],'other')
  w.put_source('report',SOURCE.replace('Niko Reed heard','Niko Reed did not hear'))
  with self.assertRaises(ValueError):p.current_messages(w)
  q=w.prepare_reader_entry(QUERY,source_ids=('report',));self.assertEqual(json.loads(q.messages[-1]['content'])['checked_reported_communication']['source_version'],2)
 def test_absent_checked_state_minimal_full_source_not_model_inference(self):
  source='Mara said, "Hello." Niko entered the yard.';w,p=self.entry(source);d=json.loads(p.messages[-1]['content']);self.assertEqual(set(d),{'query','sources','hcl_orchestration'});self.assertEqual(d['sources'][0]['text'],source);self.assertFalse(p.receipt['checked_treatment_present']);self.assertEqual(p.receipt['local_preparation']['context_selection'],'HCL_EXPLICIT_CAPABILITY_INSUFFICIENCY');self.assertIn('private belief',p.messages[0]['content']);self.assertEqual(p.receipt['extraction_calls'],0)
 def test_ordinary_smoke_raw_citation_guard_preserved(self):
  w,_=self.entry();raw=json.dumps(dict(answer='The source reports later receipt, not knowledge.',source_citations=[dict(source_id='report',quote="Tess later read Mara's last statement.",version=1)],uncertainty='No calendar/private truth.',assumptions='Reported source order only.'));r=w.answer_reader_entry(QUERY,lambda _:raw,source_ids=('report',),backend=NoCall());self.assertEqual(r['answer_raw'],raw);self.assertTrue(r['source_citation_audit']['deliverable']);self.assertEqual(r['preparation_provider_calls'],0)
if __name__=='__main__':unittest.main()
