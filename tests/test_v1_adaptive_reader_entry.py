import json, unittest
from hcl.cognition import CognitionWorkspace
from tests.test_v1_conditional_reader_entry import SOURCE, QUERY, Backend

DIALOGUE='Eva said, “I want to protect the garden.”\nEva added, “I plan to call Noor in order to protect the garden if the gate is clear.”\nEva said, “I have an opportunity to call Noor.”\nEva said, “I believe the gate is clear.”'

def raw(source_id,quote,version=1):
 return json.dumps(dict(answer='The source reports a conditional plan.', source_citations=[dict(source_id=source_id, quote=quote, version=version)], uncertainty='Private sincerity and world feasibility unknown.', assumptions='Source order is not receipt time.'))

class AdaptiveReaderTests(unittest.TestCase):
 def workspace(self,source=DIALOGUE):
  w=CognitionWorkspace();w.put_source('garden',source);return w
 def test_literal_ordinary_composition_skips_available_provider(self):
  w=self.workspace()
  class NoCall:
   def complete_json(self,*a,**k):raise AssertionError('unnecessary extraction')
  p=w.prepare_reader_entry(QUERY,source_ids=('garden',),backend=NoCall())
  self.assertEqual(p.receipt['selection'],'LOCAL_COMPLETE_SOURCE');self.assertEqual(p.receipt['extraction_calls'],0);self.assertTrue(p.receipt['checked_treatment_present'])
  payload=json.loads(p.messages[-1]['content']);self.assertEqual(payload['sources'][0]['source_id'],'garden');self.assertEqual(payload['sources'][0]['text'],DIALOGUE)
  self.assertTrue(payload['checked_epistemic']);self.assertTrue(payload['checked_agency']);plan=payload['checked_plan_feasibility'][0]['plans'][0]
  self.assertEqual(plan['world_feasibility'],'NOT_ESTABLISHED');self.assertEqual(plan['deliberate_impossibility'],'NOT_INFERRED')
 def test_narrator_ordinary_prose_no_forced_mechanism_without_backend(self):
  w=self.workspace('Eva entered the garden. Noor left by the north path.')
  p=w.prepare_reader_entry(QUERY,source_ids=('garden',));self.assertFalse(p.receipt['checked_treatment_present']);self.assertEqual(p.receipt['extraction_calls'],0);self.assertFalse(p.receipt['private_state_established']);self.assertFalse(p.receipt['semantic_certification'])
 def test_optional_conditional_coverage_one_extraction_real_state(self):
  w=self.workspace(SOURCE);backend=Backend()
  from tests.test_v1_conditional_reader_entry import proposals
  rows=proposals()
  for r in rows:r['source_id']='garden'
  backend=Backend(rows)
  p=w.prepare_reader_entry(QUERY,source_ids=('garden',),backend=backend,allow_translation=True)
  self.assertEqual(p.receipt['selection'],'CONDITIONAL_TRANSLATION');self.assertEqual(p.receipt['extraction_calls'],1);self.assertEqual(len(p.receipt['extraction_requests']),1);self.assertTrue(p.receipt['checked_treatment_present'])
  payload=json.loads(p.messages[-1]['content']);self.assertEqual(payload['sources'][0]['text'],SOURCE);self.assertTrue(payload['shared_semantic_binding']['assumptions']);self.assertFalse(p.receipt['semantic_certification'])
 def test_empty_candidate_fallback_full_source_with_attempt_receipt(self):
  w=self.workspace(SOURCE);p=w.prepare_reader_entry(QUERY,source_ids=('garden',),backend=Backend([]),allow_translation=True)
  self.assertEqual(p.receipt['selection'],'COMPLETE_SOURCE_AFTER_UNUSABLE_TRANSLATION');self.assertFalse(p.receipt['checked_treatment_present']);self.assertEqual(p.receipt['extraction_calls'],1);self.assertEqual(len(p.receipt['extraction_responses']),1);self.assertEqual(json.loads(p.messages[-1]['content'])['sources'][0]['text'],SOURCE)
 def test_one_final_raw_delivery_actual_source_namespace(self):
  w=self.workspace();calls=[];output=raw('garden','I believe the gate is clear.')
  r=w.answer_reader_entry(QUERY,lambda m:calls.append(m) or output,source_ids=('garden',))
  self.assertEqual(r['answer'],output);self.assertEqual(r['answer_raw'],output);self.assertEqual(len(calls),1);self.assertEqual(r['preparation_provider_calls'],0);self.assertTrue(r['source_citation_audit']['deliverable'])
 def test_revision_caching_and_unrelated_source_dependency(self):
  w=self.workspace();p=w.prepare_reader_entry(QUERY,source_ids=('garden',));count=w.executions
  w.put_source('unrelated','Noor went home.')
  self.assertEqual(w.prepare_reader_entry(QUERY,source_ids=('garden',)).prepared.id,p.prepared.id);self.assertEqual(w.executions,count)
  w.put_source('garden',DIALOGUE+'\nEva said, “I now believe the gate is blocked instead of the gate is clear.”')
  with self.assertRaises(ValueError):p.current_messages(w)
  q=w.prepare_reader_entry(QUERY,source_ids=('garden',));self.assertEqual(json.loads(q.messages[-1]['content'])['sources'][0]['version'],2)
  a=raw('garden','I believe the gate is clear.',version=2);r=w.answer_reader_entry(QUERY,lambda _:a,source_ids=('garden',));self.assertTrue(r['source_citation_audit']['deliverable'])
 def test_revision_during_extraction_never_fallback_or_relabel(self):
  w=self.workspace(SOURCE)
  class Changed:
   def complete_json(self,*a,**k):w.put_source('garden','Eva retracted the earlier report.');return {'candidates':[]}
  with self.assertRaises(ValueError):w.prepare_reader_entry(QUERY,source_ids=('garden',),backend=Changed(),allow_translation=True)
 def test_transport_failure_propagates_no_retry(self):
  w=self.workspace(SOURCE);calls=[]
  class Failed:
   def complete_json(self,*a,**k):calls.append(1);raise RuntimeError('provider transport unavailable')
  with self.assertRaises(RuntimeError):w.prepare_reader_entry(QUERY,source_ids=('garden',),backend=Failed(),allow_translation=True)
  self.assertEqual(len(calls),1)
 def test_bad_ids_and_revision_during_final_block_raw_not_rewrite(self):
  for revision in (False,True):
   w=self.workspace();output=raw('garden' if revision else 'ordinary-source','I believe the gate is clear.');calls=[]
   def final(m):
    calls.append(m)
    if revision:w.put_source('garden','Eva withdrew the report.')
    return output
   r=w.answer_reader_entry(QUERY,final,source_ids=('garden',));self.assertEqual(r['answer_raw'],output);self.assertFalse(r['source_citation_audit']['deliverable']);self.assertEqual(len(calls),1)
 def test_statement_snapshot_not_silently_replaced_by_full_later_source(self):
  w=self.workspace()
  for query in ('At statement 2, what does Eva believe?', 'Before statement 3 what is possible?'):
   with self.assertRaises(ValueError):w.prepare_reader_entry(query,source_ids=('garden',))
 def test_actor_separation_other_person_opportunity_does_not_complete_plan(self):
  text='Eva said, “I want to protect the garden.”\nEva said, “I plan to call Noor in order to protect the garden if the gate is clear.”\nNoor said, “I have an opportunity to call Noor.”\nEva said, “I believe the gate is clear.”'
  w=self.workspace(text);p=w.prepare_reader_entry(QUERY,source_ids=('garden',));payload=json.loads(p.messages[-1]['content'])
  row=next(r for r in payload['checked_plan_feasibility'] if r['actor']=='Eva');self.assertEqual(row['plans'][0]['opportunity'],'UNKNOWN');self.assertEqual(row['plans'][0]['subjective_feasibility'],'OPPORTUNITY_UNRESOLVED');self.assertEqual(row['plans'][0]['world_feasibility'],'NOT_ESTABLISHED')
 def test_budget_or_cross_source_fail_before_optional_call(self):
  w=self.workspace(SOURCE);w.put_source('other',DIALOGUE)
  class NoCall:
   def complete_json(self,*a,**k):raise AssertionError('must reject before transport')
  for args in (dict(source_ids=('garden','other')),dict(source_ids=('garden',),max_chars=512)):
   with self.assertRaises(ValueError):w.prepare_reader_entry(QUERY,backend=NoCall(),**args)

if __name__=='__main__':unittest.main()
