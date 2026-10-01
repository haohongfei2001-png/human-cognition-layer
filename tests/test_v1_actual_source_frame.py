"""Actual source IDs versus benchmark assumptions; raw preservation, no rescoring."""
import copy,json,unittest
from hcl.cognition import CognitionWorkspace, audit_supplied_source_citations, original_sources_from_messages
from tests.test_v1_conditional_reader_entry import SOURCE,QUERY,Backend

def messages(source_id='ordinary-source',text=SOURCE,version=1):return [dict(role='user',content=json.dumps(dict(sources=[dict(source_id=source_id,version=version,text=text)])))]
def raw(source_id='ordinary-source',quote='Dana expressed a desire to protect the gate.'):
 return json.dumps(dict(answer='The source reports a desire.',source_citations=[dict(source_id=source_id,quote=quote,version=1)],uncertainty='Meaning is unverified.',assumptions='No private truth.'))
class ActualSourceFrameTests(unittest.TestCase):
 def test_actual_base_and_h_ids_are_used_without_source_alias_rewriting(self):
  for identity in ('development-source','ordinary-source','caller-authorized'):
   output=raw(identity);a=audit_supplied_source_citations(messages(identity),output)
   self.assertTrue(a['deliverable']);self.assertEqual(a['actual_primary_source_ids'],[identity]);self.assertFalse(a['source_identity_substituted']);self.assertFalse(a['raw_output_rewritten']);self.assertFalse(a['semantic_certification'])
 def test_guessed_expected_alias_wrong_version_or_changed_quote_stays_invalid(self):
  self.assertFalse(audit_supplied_source_citations(messages(),raw('development-source'))['deliverable'])
  self.assertFalse(audit_supplied_source_citations(messages(version=2),raw())['deliverable'])
  self.assertFalse(audit_supplied_source_citations(messages(),raw(quote='Dana wants to protect the gate.'))['deliverable'])
 def test_derived_primary_and_conflicting_duplicate_frames_fail(self):
  m=messages();p=json.loads(m[0]['content']);p['shared_semantic_binding']=dict(original_sources=[dict(source_id='meeting',text=SOURCE)]);m[0]['content']=json.dumps(p)
  self.assertFalse(audit_supplied_source_citations(m,raw())['deliverable'])
  self.assertFalse(audit_supplied_source_citations(messages()+messages(text=SOURCE+' revision'),raw())['deliverable'])
  self.assertTrue(audit_supplied_source_citations(messages()+messages(),raw())['deliverable'])
 def test_conditional_compact_original_ids_even_hash_ids_remain_primary(self):
  identity='a'*64;w=CognitionWorkspace();w.put_source(identity,SOURCE)
  rows=Backend().rows if hasattr(Backend(),'rows') else None
  from tests.test_v1_conditional_reader_entry import proposals
  rows=proposals()
  for r in rows:r['source_id']=identity
  p=w.prepare_reader_semantic(QUERY,source_ids=(identity,),backend=Backend(rows),compact_context=True)
  m=p.messages;a=audit_supplied_source_citations(m,raw(identity))
  self.assertTrue(a['deliverable']);self.assertEqual(a['actual_primary_source_ids'],[identity])
  self.assertFalse(audit_supplied_source_citations(m,raw('@HCL_ID_0'))['deliverable'])
 def test_ordinary_input_one_final_zero_extraction_valid_quote_raw_intact(self):
  w=CognitionWorkspace();w.put_source('meeting',SOURCE);calls=[];output=raw()
  r=w.answer_source_guarded(QUERY,lambda m:calls.append(m) or output,source_ids=('meeting',))
  self.assertEqual(r['answer'],output);self.assertEqual(r['answer_raw'],output);self.assertEqual(r['preparation_provider_calls'],0);self.assertEqual(len(calls),1);self.assertEqual(calls,[r['actual_final_messages']])
 def test_invalid_quote_or_revision_during_final_blocks_delivery_without_retry(self):
  for revision in (False,True):
   w=CognitionWorkspace();w.put_source('meeting',SOURCE);calls=[];output=raw() if revision else raw('invented-source')
   def callback(m):
    calls.append(m)
    if revision:w.put_source('meeting','Dana withdrew the report.')
    return output
   r=w.answer_source_guarded(QUERY,callback,source_ids=('meeting',));self.assertEqual(r['answer_raw'],output);self.assertFalse(r['source_citation_audit']['deliverable']);self.assertEqual(len(calls),1);self.assertEqual(json.loads(r['answer'])['source_citations'],[])
 def test_missing_frame_fails_before_transport_and_negative_inference_stays_unknown(self):
  for m in ([],[dict(role='system',content='source text')],messages(version=True)):
   with self.assertRaises(ValueError):original_sources_from_messages(m)
  a=audit_supplied_source_citations(messages(),raw());self.assertEqual(a['semantic_adequacy'],'UNASSESSED')
 def test_source_bearing_ordinary_dialogue_actual_composition_zero_extraction(self):
  text='Eva said, “I want to protect the garden.”\nEva added, “I plan to call Noor in order to protect the garden if the gate is clear.”\nEva said, “I have an opportunity to call Noor.”\nEva said, “I believe the gate is clear.”'
  w=CognitionWorkspace();w.put_source('garden',text)
  output=raw(quote='I plan to call Noor in order to protect the garden if the gate is clear.')
  a=w.answer_source_guarded(QUERY,lambda _:output,source_ids=('garden',))
  self.assertEqual(a['answer'],output);self.assertEqual(a['preparation_provider_calls'],0)
  p=json.loads(a['actual_final_messages'][-2]['content']);plan=p['checked_plan_feasibility'][0]['plans'][0]
  self.assertEqual(plan['subjective_feasibility'],'SUPPORTED_UNDER_REPORTED_BELIEFS');self.assertEqual(plan['world_feasibility'],'NOT_ESTABLISHED');self.assertEqual(plan['deliberate_impossibility'],'NOT_INFERRED')
  self.assertFalse(a['source_citation_audit']['semantic_certification'])
 def test_duplicate_source_ids_and_actor_name_as_unlisted_source_fail(self):
  m=messages();p=json.loads(m[0]['content']);p['sources']*=2;m[0]['content']=json.dumps(p)
  with self.assertRaises(ValueError):original_sources_from_messages(m)
  self.assertFalse(audit_supplied_source_citations(messages(),raw('Dana'))['deliverable'])
if __name__=='__main__':unittest.main()
