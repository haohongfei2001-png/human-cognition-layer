import json,unittest
from hcl.cognition import CognitionWorkspace
SOURCE='The wind moved a curtain beside the doorway. A cabinet remained shut.'
QUERY='Describe the supplied scene with uncertainty rather than inventing a private mental state.'
class NoCall:
 def complete_json(self,*a,**kw):raise AssertionError('no automatic extraction')
class EmptyStateTests(unittest.TestCase):
 def prepare(self,source=SOURCE):
  w=CognitionWorkspace();w.put_source('scene',source);return w,w.prepare_reader_entry(QUERY,source_ids=('scene',),backend=NoCall())
 def test_absence_is_explicit_not_false_anchored_candidates_assurance(self):
  w,p=self.prepare();self.assertFalse(p.receipt['checked_treatment_present']);self.assertIn('No checked cognition state was derived',p.messages[0]['content']);self.assertNotIn('locally anchored candidates',p.messages[0]['content']);self.assertEqual(p.receipt['local_preparation']['system_contract'],'EXPLICIT_NO_CHECKED_STATE_MINIMAL_ORIGINAL_SOURCE_GUARD')
 def test_complete_source_query_quote_and_world_private_boundary(self):
  w,p=self.prepare();d=json.loads(p.messages[-1]['content']);self.assertEqual(d,dict(query=QUERY,sources=[dict(source_id='scene',version=1,text=SOURCE)]));self.assertIn('private states or world truth',p.messages[0]['content']);self.assertIn('Quote only original text',p.messages[0]['content']);self.assertEqual(p.receipt['extraction_calls'],0)
 def test_actual_checked_b01_c01_c03_contract_is_retained(self):
  source='Adele believes the path is open. Adele said, "I do not believe the path is open." Adele said, "I plan to walk the path in order to inspect the hall if the path is open."';w,p=self.prepare(source);d=json.loads(p.messages[-1]['content']);self.assertTrue(p.receipt['checked_treatment_present']);self.assertNotIn('No checked cognition state was derived',p.messages[0]['content']);self.assertTrue(d['checked_epistemic']['comparisons']);self.assertTrue(d['checked_agency']);self.assertTrue(d['checked_plan_feasibility'])
 def test_no_partial_checker_promise_for_ambiguous_or_hypothetical_narration(self):
  for source in ['Perhaps Adele believes the path is open.','They believe the path is open.', 'Adele opened a window if the path was safe. Adele believes the path is open.']:
   w,p=self.prepare(source);self.assertFalse(p.receipt['checked_treatment_present']);self.assertIn('No checked cognition state was derived',p.messages[0]['content']);self.assertEqual(json.loads(p.messages[-1]['content'])['sources'][0]['text'],source)
 def test_revision_invalidates_input_and_rebuilds_exact_new_source(self):
  w,p=self.prepare();updated=SOURCE+' The doorway remained empty.';w.put_source('scene',updated)
  with self.assertRaises(ValueError):p.current_messages(w)
  q=w.prepare_reader_entry(QUERY,source_ids=('scene',),backend=NoCall());d=json.loads(q.messages[-1]['content']);self.assertEqual(d['sources'][0]['version'],2);self.assertEqual(d['sources'][0]['text'],updated)
 def test_other_source_identity_never_substitutes_or_shares_private_state(self):
  w,p=self.prepare();w.put_source('other','Adele believes the path is open.');q=w.prepare_reader_entry(QUERY,source_ids=('scene',),backend=NoCall());self.assertEqual(q.messages,p.messages);self.assertEqual(json.loads(q.messages[-1]['content'])['sources'][0]['source_id'],'scene')
 def test_ordinary_source_cited_smoke_without_output_rewrite_or_token_claim(self):
  w,p=self.prepare();raw=json.dumps(dict(answer='The source describes a curtain and cabinet; no private state is established.',source_citations=[dict(source_id='scene',quote=SOURCE,version=1)],uncertainty='No mental or world-truth certification.',assumptions='Original source reports only.'));r=w.answer_reader_entry(QUERY,lambda _:raw,source_ids=('scene',),backend=NoCall());self.assertEqual(r['answer_raw'],raw);self.assertTrue(r['source_citation_audit']['deliverable']);self.assertFalse(r['source_citation_audit']['semantic_certification']);self.assertEqual(r['preparation_provider_calls'],0)
if __name__=='__main__':unittest.main()
