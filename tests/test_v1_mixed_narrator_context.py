import json,unittest
from hcl.cognition import CognitionWorkspace
from hcl.cognition.core import ClaimKind
SOURCE='Elena opened the window. Elena believes the corridor is quiet. Elena said, "I do not believe the corridor is quiet." Tomas arrived.'
QUERY='Compare the source attribution with Elena own expression without treating either as private truth.'
class NoCall:
 def complete_json(self,*a,**kw):raise AssertionError('no paid or hand-entered state')
class MixedNarratorTests(unittest.TestCase):
 def entry(self,source=SOURCE,id='scene'):
  w=CognitionWorkspace();w.put_source(id,source);return w,w.prepare_reader_entry(QUERY,source_ids=(id,),backend=NoCall())
 def test_context_enables_actual_comparison_original_full_text_and_offsets(self):
  w,p=self.entry();d=json.loads(p.messages[-1]['content']);self.assertEqual(d['sources'][0]['text'],SOURCE);c=d['checked_epistemic'];self.assertEqual(c['comparisons'][0]['relation'],'DIFFERS_FROM_SUBJECT_REPORT');self.assertEqual(c['comparisons'][0]['private_belief_truth'],'NOT_ESTABLISHED');self.assertEqual(p.receipt['extraction_calls'],0)
  narrator=[r for r in d['cognitive_candidates'] if r['proposal'].get('reporter_role')=='SOURCE_NARRATOR'];self.assertEqual(len(narrator),1)
  for row in narrator:
   span=w.core.spans[row['source_span_id']];self.assertEqual(span.quote,'Elena believes the corridor is quiet.');self.assertEqual(SOURCE[span.start:span.end],span.quote)
  self.assertFalse(any(r['proposal'].get('utterance') in ('Elena opened the window.','Tomas arrived.') for r in d['cognitive_candidates']))
 def test_qualifier_unknown_context_or_pronoun_refuses_whole_new_admission(self):
  for source in [SOURCE+' The entire scene is hypothetical.',SOURCE.replace('Elena opened the window.','Otherwise opened the window.'),SOURCE.replace('Tomas arrived.','Tomas doubted the account.'),SOURCE.replace('Elena opened the window.','Elena opened the window if Tomas approved.'),SOURCE.replace('Elena opened the window.','She opened the window.'),SOURCE.replace('Tomas arrived.','Tomas arrived because Elena believed the corridor was quiet.'),SOURCE.replace('Tomas arrived.','Tomas arrived in an imaginary story.'),SOURCE.replace('Tomas arrived.','Tomas did not arrive.')]:
   w,p=self.entry(source);d=json.loads(p.messages[-1]['content']);self.assertEqual(d.get('checked_epistemic',{}).get('comparisons',[]),[])
 def test_quoted_context_never_becomes_source_report_or_private_state(self):
  source='Tomas said, "Elena opened the window. Elena believes the corridor is quiet." Elena said, "I do not believe the corridor is quiet."';w,p=self.entry(source);d=json.loads(p.messages[-1]['content']);self.assertEqual(d['checked_epistemic']['comparisons'],[])
 def test_uncertainty_knowledge_and_exposure_not_belief_or_shared_access(self):
  w,p=self.entry(SOURCE.replace('Elena believes','Elena is unsure whether'));c=json.loads(p.messages[-1]['content'])['checked_epistemic'];self.assertEqual(c['comparisons'][0]['relation'],'UNRESOLVED_EXPLICIT_UNCERTAINTY')
  for verb in ('knows','heard','understands'):
   w,p=self.entry(SOURCE.replace('Elena believes',f'Elena {verb}'));c=json.loads(p.messages[-1]['content'])['checked_epistemic'];self.assertEqual(c['comparisons'],[])
 def test_actor_source_and_time_not_merged_by_material_context(self):
  w,p=self.entry(SOURCE.replace('Elena believes','Tomas believes'));c=json.loads(p.messages[-1]['content'])['checked_epistemic'];self.assertEqual(c['comparisons'],[])
  w.put_source('another',SOURCE);q=w.prepare_reader_entry(QUERY,source_ids=('another',));d=json.loads(q.messages[-1]['content']);self.assertTrue(all(r['source_id']=='another' for r in d['checked_epistemic']['comparisons']));self.assertIn('Narrative order does not establish event or receipt time',q.messages[0]['content'])
 def test_conditional_plan_uses_own_expression_not_narrator_or_opened_window(self):
  source=SOURCE+' Elena said, "I plan to enter the corridor in order to inspect the room if the corridor is quiet."';w,p=self.entry(source);d=json.loads(p.messages[-1]['content']);self.assertTrue(d['checked_agency']);plan=d['checked_plan_feasibility'][0]['plans'][0];self.assertEqual(plan['subjective_condition'],'NOT_AFFIRMED_NOT_NEGATION');self.assertEqual(plan['world_feasibility'],'NOT_ESTABLISHED');self.assertEqual(plan['deliberate_impossibility'],'NOT_INFERRED')
 def test_local_revision_and_actual_inner_challenge_invalidate_final_input(self):
  w,p=self.entry();d=json.loads(p.messages[-1]['content']);key=d['checked_epistemic']['comparisons'][0]['claim_id'];scope=w.core.claims[key].scope;counter=w.core.claim(scope,ClaimKind.SOURCE_REPORT,dict(challenge='This interpretation is disputed.'));w.core.support(counter,w._spans['scene']);w.core.challenge(key,counter)
  with self.assertRaises(ValueError):p.current_messages(w)
  w.put_source('scene',SOURCE.replace('Elena believes','Elena does not believe'));q=w.prepare_reader_entry(QUERY,source_ids=('scene',));d=json.loads(q.messages[-1]['content']);self.assertEqual(d['checked_epistemic']['comparisons'][0]['relation'],'CONSISTENT_WITH_SUBJECT_REPORT');self.assertTrue(all(w.core.spans[r['source_span_id']].version==2 for r in d['cognitive_candidates']))
 def test_ordinary_source_cited_smoke_answer_never_rewritten(self):
  w,_=self.entry();raw=json.dumps(dict(answer='Source attribution differs from expressed denial; private truth unknown.',source_citations=[dict(source_id='scene',quote='Elena believes the corridor is quiet.',version=1)],uncertainty='Unknown time and private belief.',assumptions='Source-reported channels only.'));r=w.answer_reader_entry(QUERY,lambda _:raw,source_ids=('scene',),backend=NoCall());self.assertEqual(r['answer_raw'],raw);self.assertTrue(r['source_citation_audit']['deliverable']);self.assertEqual(r['preparation_provider_calls'],0)
if __name__=='__main__':unittest.main()
