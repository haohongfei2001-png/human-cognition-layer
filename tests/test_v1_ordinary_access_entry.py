import json, unittest
from hcl.cognition import CognitionWorkspace
from hcl.cognition.ordinary_access import prepare_ordinary_access
SOURCE='Leah said, “I believe the gate is clear.”\nAri Stone heard Leah\'s last statement.\nTess did not hear Leah\'s last statement.\nLeah\'s last statement was publicly available.'
QUERY='Who has a reported route to the statement, and what remains unknown?'
class NoCall:
 def complete_json(self,*a,**k):raise AssertionError('unexpected extraction')

class OrdinaryAccessTests(unittest.TestCase):
 def workspace(self,text=SOURCE):
  w=CognitionWorkspace();w.put_source('meeting',text);return w
 def test_ordinary_actor_access_reuses_B02_exact_source_anchors(self):
  w=self.workspace();p=w.prepare_reader_entry(QUERY,source_ids=('meeting',),backend=NoCall());payload=json.loads(p.messages[-1]['content']);state=payload['checked_reported_communication'];views={r['source_named_actor']:r for r in state['views']}
  self.assertEqual(state['mechanism'],'EXISTING_B02_COMMUNICATION_SCENE');self.assertEqual(views['Ari Stone']['access_audit'][0]['status'],'REPORTED_EXPOSURE');self.assertEqual(views['Tess']['access_audit'][0]['status'],'REPORTED_NON_EXPOSURE');self.assertEqual(views['Tess']['visible_derived_statements'],[]);self.assertEqual(len(views['Ari Stone']['visible_derived_statements']),1)
  for b in state['original_quote_bindings']:self.assertEqual(SOURCE[b['start']:b['start']+len(b['quote'])],b['quote'])
  self.assertEqual(payload['sources'][0]['text'],SOURCE);self.assertEqual(p.receipt['extraction_calls'],0);self.assertTrue(payload['checked_epistemic'])
 def test_reported_hearing_never_promoted_to_belief_knowledge_comprehension(self):
  p=self.workspace().prepare_reader_entry(QUERY,source_ids=('meeting',));state=json.loads(p.messages[-1]['content'])['checked_reported_communication']
  for view in state['views']:
   self.assertEqual(view['comprehension'],'NOT_ESTABLISHED');self.assertEqual(view['acceptance'],'NOT_ESTABLISHED');self.assertEqual(view['knowledge'],'NOT_ESTABLISHED');self.assertEqual(view['ignorance_from_missing_route'],'NOT_INFERRED')
  self.assertFalse(state['private_state_established']);self.assertFalse(state['world_receipt_verified']);self.assertFalse(state['semantic_certification']);self.assertFalse(state['shared_exposure_establishes_shared_belief'])
 def test_availability_addressing_do_not_become_receipt(self):
  for suffix,expected in [("Leah's last statement was publicly available.",'PUBLIC_AVAILABILITY_EXPOSURE_UNKNOWN'),("Leah sent their last statement privately to Ari.",'ADDRESSED_RECEIPT_UNKNOWN')]:
   text='Leah said, “I believe the gate is clear.”\n'+('Ari said, “Hello.”\n' if expected=='PUBLIC_AVAILABILITY_EXPOSURE_UNKNOWN' else '')+suffix
   state=prepare_ordinary_access(text,source_id='meeting',version=1)['state'];views={v['source_named_actor']:v for v in state['views']}
   if 'Ari' in views:self.assertEqual(views['Ari']['access_audit'][0]['status'],expected);self.assertEqual(views['Ari']['visible_derived_statements'],['Person2: Hello.'] if expected=='PUBLIC_AVAILABILITY_EXPOSURE_UNKNOWN' else [])
   else:self.assertEqual(state['original_quote_bindings'][-1]['derived_line'],"Narrator: Person1's last statement was publicly available.")
 def test_later_receipt_preserves_earlier_nonreceipt_and_source_order_only(self):
  text=SOURCE+'\nTess later heard Leah\'s last statement.'
  state=prepare_ordinary_access(text,source_id='meeting',version=1)['state'];view=next(v for v in state['views'] if v['source_named_actor']=='Tess');self.assertEqual(view['access_audit'][0]['status'],'REPORTED_LATER_EXPOSURE');proofs=view['access_audit'][0]['relevant_access_proofs'];self.assertEqual([r['kind'] for r in proofs],['NON_RECEIPT','LATER_RECEIPT']);self.assertLess(proofs[0]['source_line'],proofs[1]['source_line']);self.assertIn('NOT_CALENDAR',state['temporal_semantics'])
 def test_conflicting_reports_do_not_transmit_content(self):
  text='Leah said, “I believe the gate is clear.”\nTess heard Leah\'s last statement.\nTess did not hear Leah\'s last statement.'
  state=prepare_ordinary_access(text,source_id='meeting',version=1)['state'];view=next(v for v in state['views'] if v['source_named_actor']=='Tess');self.assertEqual(view['access_audit'][0]['status'],'CONFLICTING_EXPOSURE_REPORTS');self.assertEqual(view['visible_derived_statements'],[])
 def test_unknown_reference_qualifier_or_co_presence_not_inferred(self):
  for text in ["Ari heard Leah's last statement.", 'Leah said, “I believe the gate is clear.”\nThey heard Leah\'s last statement.', 'Leah said, “I believe the gate is clear.”\nAri watched Leah.', 'If Leah said, “I believe the gate is clear.”\nAri heard Leah\'s last statement.',SOURCE+'\nThe episode was hypothetical.']:
   p=prepare_ordinary_access(text,source_id='meeting',version=1);self.assertIsNone(p['state']);self.assertEqual(p['checked_operations'],0)
 def test_revision_and_bad_derived_quote_never_raw_rewrite(self):
  w=self.workspace();p=w.prepare_reader_entry(QUERY,source_ids=('meeting',));raw=json.dumps(dict(answer='The source reports Ari hearing.',source_citations=[dict(source_id='meeting',quote='Person1: I believe the gate is clear.')],uncertainty='No private truth.',assumptions='Source report only.'))
  result=w.answer_reader_entry(QUERY,lambda _:raw,source_ids=('meeting',));self.assertEqual(result['answer_raw'],raw);self.assertFalse(result['source_citation_audit']['deliverable'])
  w.put_source('meeting',SOURCE.replace('Ari Stone heard','Ari Stone did not hear'))
  with self.assertRaises(ValueError):p.current_messages(w)
  q=w.prepare_reader_entry(QUERY,source_ids=('meeting',));state=json.loads(q.messages[-1]['content'])['checked_reported_communication'];self.assertEqual(state['source_version'],2);self.assertEqual(next(v for v in state['views'] if v['source_named_actor']=='Ari Stone')['visible_derived_statements'],[])
 def test_default_backend_is_not_automatic_paid_generic_extraction(self):
  w=self.workspace('Kai entered the hall. Ren left.')
  p=w.prepare_reader_entry(QUERY,source_ids=('meeting',),backend=NoCall());self.assertEqual(p.receipt['extraction_calls'],0);self.assertFalse(p.receipt['allow_translation']);self.assertFalse(p.receipt['checked_treatment_present']);self.assertEqual(json.loads(p.messages[-1]['content'])['sources'][0]['text'],'Kai entered the hall. Ren left.')
 def test_complete_access_state_budget_overflow_fails_without_truncation(self):
  w=self.workspace()
  with self.assertRaises(ValueError):w.prepare_reader_entry(QUERY,source_ids=('meeting',),backend=NoCall(),max_chars=2500)
if __name__=='__main__':unittest.main()
