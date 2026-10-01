import json,unittest
from hcl.cognition import CognitionWorkspace
from hcl.cognition.core import ClaimKind
SOURCE='Mara believes the gate is safe. Mara said, "I do not believe the gate is safe."'
QUERY='Compare source narrator attribution with the subject own expression.'
class NoCall:
 def complete_json(self,*a,**k):raise AssertionError('no model state input')
class ParagraphNarratorTests(unittest.TestCase):
 def entry(self,source=SOURCE,id='report'):
  w=CognitionWorkspace();w.put_source(id,source);return w,w.prepare_reader_entry(QUERY,source_ids=(id,),backend=NoCall())
 def test_actual_source_report_subject_comparison_not_private_truth(self):
  w,p=self.entry();d=json.loads(p.messages[-1]['content']);c=d['checked_epistemic'];self.assertEqual(len(c['comparisons']),1);row=c['comparisons'][0];self.assertEqual(row['relation'],'DIFFERS_FROM_SUBJECT_REPORT');self.assertTrue(row['reporter'].startswith('SourceNarrator@'));self.assertNotEqual(row['reporter'],row['subject']);self.assertEqual(row['private_belief_truth'],'NOT_ESTABLISHED')
  records=c['epistemic_objects'];narrator=next(r for r in records if r['public_expression']['channel']=='SOURCE_NARRATOR_ATTRIBUTION');self.assertIsNone(narrator['private_interpretation']);self.assertEqual(narrator['public_expression']['expressed_content']['attitude'],'REPORTED_ATTRIBUTION');self.assertEqual(d['sources'][0]['text'],SOURCE);self.assertEqual(p.receipt['extraction_calls'],0)
  for r in d['cognitive_candidates']:
   span=w.core.spans[r['source_span_id']];self.assertEqual(SOURCE[span.start:span.end],span.quote)
 def test_uncertainty_and_outer_denial_no_inner_belief_laundering(self):
  w,p=self.entry('Mara is unsure whether the gate is safe. Mara said, "I believe the gate is safe."');self.assertEqual(json.loads(p.messages[-1]['content'])['checked_epistemic']['comparisons'][0]['relation'],'UNRESOLVED_EXPLICIT_UNCERTAINTY')
  w,p=self.entry('Mara does not believe Niko believes the gate is safe. Niko said, "I believe the gate is safe."');self.assertEqual(json.loads(p.messages[-1]['content'])['checked_epistemic']['comparisons'],[])
 def test_complete_paragraph_qualifications_and_quote_context_refuse_new_report(self):
  for source in ['If '+SOURCE,SOURCE+' The statements were hypothetical.',SOURCE+' Niko later doubted the account.',SOURCE.replace('Mara believes','They believe'),SOURCE.replace('Mara believes the gate is safe.','Mara believes the gate is safe if Niko approves.'), 'Niko said, "Mara believes the gate is safe." Mara said, "I do not believe the gate is safe."']:
   w,p=self.entry(source);d=json.loads(p.messages[-1]['content']);c=d.get('checked_epistemic',{});self.assertFalse(any(r['public_expression']['channel']=='SOURCE_NARRATOR_ATTRIBUTION' for r in c.get('epistemic_objects',[])));self.assertEqual(c.get('comparisons',[]),[])
 def test_source_revision_all_nested_original_anchors_use_current_version(self):
  w,p=self.entry();w.put_source('report',SOURCE.replace('Mara believes','Mara does not believe'));q=w.prepare_reader_entry(QUERY,source_ids=('report',));d=json.loads(q.messages[-1]['content']);self.assertEqual(d['sources'][0]['version'],2);self.assertEqual(d['checked_epistemic']['comparisons'][0]['relation'],'CONSISTENT_WITH_SUBJECT_REPORT')
  ids=q.receipt['local_preparation']['shared_support_claim_ids'];self.assertTrue(ids);self.assertTrue(all(w.core.support_statuses()[i]=='SUPPORT_AVAILABLE' for i in ids))
  for r in d['cognitive_candidates']:self.assertEqual(w.core.spans[r['source_span_id']].version,2)
  with self.assertRaises(ValueError):p.current_messages(w)
 def test_shared_checked_claim_challenge_invalidates_actual_final_input(self):
  w,p=self.entry();d=json.loads(p.messages[-1]['content']);claim=d['checked_epistemic']['comparisons'][0]['claim_id'];self.assertIn(claim,w.core.claims);scope=w.core.claims[claim].scope;counter=w.core.claim(scope,ClaimKind.SOURCE_REPORT,dict(challenge='Evidence does not resolve the interpretation.'));w.core.support(counter,w._spans['report']);w.core.challenge(claim,counter)
  with self.assertRaises(ValueError):p.current_messages(w)
 def test_source_actor_time_boundary_no_cross_document_or_later_knowledge(self):
  w,p=self.entry('Mara heard the gate is safe. Mara said, "I know the gate is safe."');c=json.loads(p.messages[-1]['content'])['checked_epistemic'];self.assertEqual(c['comparisons'],[]);self.assertIn('Narrative order does not establish event or receipt time',p.messages[0]['content'])
  w.put_source('other',SOURCE);q=w.prepare_reader_entry(QUERY,source_ids=('other',));self.assertTrue(all(r['source_id']=='other' for r in json.loads(q.messages[-1]['content'])['checked_epistemic']['comparisons']))
 def test_composition_does_not_use_narrator_attribution_as_own_plan_belief(self):
  source=SOURCE+' Mara said, "I plan to cross the gate in order to inspect the station if the gate is safe."';w,p=self.entry(source);d=json.loads(p.messages[-1]['content']);self.assertTrue(d['checked_agency']);self.assertTrue(d['checked_plan_feasibility']);self.assertEqual(d['checked_epistemic']['comparisons'][0]['relation'],'DIFFERS_FROM_SUBJECT_REPORT')
  plans=d['checked_plan_feasibility'][0]['plans'];self.assertEqual(plans[0]['subjective_condition'],'NOT_AFFIRMED_NOT_NEGATION');self.assertEqual(plans[0]['world_feasibility'],'NOT_ESTABLISHED');self.assertEqual(plans[0]['deliberate_impossibility'],'NOT_INFERRED')
 def test_ordinary_source_cited_smoke_no_raw_rewrite_or_retry(self):
  w,_=self.entry();raw=json.dumps(dict(answer='The narrator attribution differs from the expressed claim; actual belief is unresolved.',source_citations=[dict(source_id='report',quote='Mara believes the gate is safe.',version=1)],uncertainty='No contemporaneous/private/world truth.',assumptions='Source reports only.'));r=w.answer_reader_entry(QUERY,lambda _:raw,source_ids=('report',),backend=NoCall());self.assertEqual(r['answer_raw'],raw);self.assertTrue(r['source_citation_audit']['deliverable']);self.assertEqual(r['preparation_provider_calls'],0)
if __name__=='__main__':unittest.main()
