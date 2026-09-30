import json,unittest
from hcl.v1 import HCLCognitionLayer,prepare_person_context,NarrativePremise,FactorRequirement,ResponsibilityFactor
from hcl.v1.person_question import answer_person_context
from hcl.v1.router import PerspectiveMode
from hcl.v1.long_source_question import prepare_reader_cognition
QUERY='Which actions are supported and what limits remain?'
SOURCE='\n\n'.join(['_Dana._ I want to protect the gate.','_Dana._ I plan to call Noor in order to protect the gate if the gate is clear.','_Dana._ I have an opportunity to call Noor.','_Dana._ I believe the gate is clear.','Narrator: In the declared model, it is false that the gate is clear.'])
def layer():return HCLCognitionLayer(lambda _: (_ for _ in ()).throw(AssertionError('no extraction transport')))
def payload(p):return json.loads(p.messages[-1]['content'])
class ReaderCognitionEntry(unittest.TestCase):
 def test_positive_short_ordinary_unmatched_question_composes_existing_checks(self):
  h=prepare_person_context(layer(),QUERY,SOURCE);p=payload(h)
  self.assertEqual(p['sources'][0]['text'],SOURCE)
  self.assertEqual(h.preparation_receipt['extraction_provider_calls'],0)
  self.assertTrue(h.preparation_receipt['specialized_cognition_treatment'])
  plan=p['checked_plan_feasibility'][0]['plans'][0]
  self.assertEqual(plan['subjective_feasibility'],'SUPPORTED_UNDER_REPORTED_BELIEFS')
  self.assertEqual(plan['model_condition_check'],'MODEL_CONDITION_CONTRADICTED')
  self.assertEqual(plan['relation'],'BELIEF_MODEL_DIVERGENCE_NOT_KNOWING_INFEASIBILITY')
  self.assertEqual(plan['deliberate_impossibility'],'NOT_INFERRED')
 def test_generic_entry_no_checked_treatment_preserves_unmatched_prose(self):
  source='A visitor arrived and the gate fell. Neighbors blamed Dana.'
  h=prepare_person_context(layer(),'Was this fair and what did Dana mean?',source)
  self.assertEqual(payload(h)['sources'][0]['text'],source)
  self.assertFalse(h.preparation_receipt['specialized_cognition_treatment'])
  self.assertNotIn('checked_agency',payload(h));self.assertNotIn('checked_plan_feasibility',payload(h))
  self.assertIn('not sincerity',h.messages[0]['content'])
 def test_focal_actor_not_guessed_from_question_or_aliased_other_actor(self):
  source=SOURCE+'\n\n_Lee._ I believe the gate is closed.'
  p=payload(prepare_person_context(layer(),'What could Lee do?',source))
  self.assertEqual(p['checked_plan_feasibility'][0]['actor'],'Dana')
  self.assertEqual(p['checked_plan_feasibility'][0]['plans'][0]['world_feasibility'],'NOT_ESTABLISHED')
 def test_narrator_report_never_becomes_subject_own_expression(self):
  h=prepare_person_context(layer(),'How are the accounts different?','Dana does not believe that Lee believes the gate is safe.')
  row=payload(h)['checked_epistemic']['epistemic_objects'][0]
  self.assertEqual(row['public_expression']['channel'],'SOURCE_NARRATOR_ATTRIBUTION')
  self.assertIsNone(row['private_interpretation'])
 def test_explicit_statement_scope_excludes_future_model_before_preparation(self):
  source='_Dana._ I believe the gate is clear.\nNarrator: In the declared model, it is false that the gate is clear.'
  h=prepare_person_context(layer(),'At statement 1, Which limits remain?',source)
  p=payload(h);self.assertEqual(p['sources'][0]['text'],source.splitlines()[0])
  self.assertNotIn('declared model',json.dumps(p))
  self.assertEqual(p['source_order_scope']['calendar_time'],'NOT_ESTABLISHED')
 def test_private_modes_do_not_leak_reader_source_even_with_access_flag(self):
  for mode,observer in ((PerspectiveMode.CHARACTER_PERSPECTIVE,None),(PerspectiveMode.OBSERVER_ABOUT_TARGET,'Lee')):
   h=prepare_person_context(layer(),QUERY,SOURCE,perspective_mode=mode,observer_actor=observer,narrative_access=True)
   self.assertEqual(h.preparation_receipt['failure'],'private_question_requires_explicit_source_access_preparation')
   self.assertNotIn(SOURCE,json.dumps(h.messages))
 def test_local_revision_changes_condition_without_changing_declared_model(self):
  h=prepare_person_context(layer(),QUERY,SOURCE+'\n\n_Dana._ I now believe it is false that the gate is clear instead of the gate is clear.')
  plan=payload(h)['checked_plan_feasibility'][0]['plans'][0]
  self.assertEqual(plan['subjective_feasibility'],'CONTRADICTED_UNDER_REPORTED_BELIEFS')
  self.assertEqual(plan['model_condition_check'],'MODEL_CONDITION_CONTRADICTED')
 def test_hnew_only_removes_existing_plan_join(self):
  h,n=(prepare_reader_cognition(QUERY,SOURCE,plan_checks=x) for x in (True,False))
  hp,np=payload(h),payload(n);self.assertTrue(hp.pop('checked_plan_feasibility'));self.assertEqual(hp,np)
  self.assertNotEqual(h.messages,n.messages)
 def test_budget_no_silent_truncation(self):
  h=prepare_person_context(layer(),QUERY,SOURCE,max_context_chars=512)
  self.assertEqual(h.preparation_receipt['method'],'bounded_ordinary_question_refusal')
  self.assertIn('context budget',h.preparation_receipt['failure'])
  self.assertNotIn('checked_plan_feasibility',json.dumps(h.messages))
 def test_generic_reader_cannot_silently_adopt_caller_normative_premise(self):
  rule=NarrativePremise('rule','This caller rule requires knowledge.',(FactorRequirement(ResponsibilityFactor.KNOWLEDGE,True),))
  h=prepare_person_context(layer(),QUERY,SOURCE,responsibility_premises=(rule,))
  self.assertEqual(h.preparation_receipt['failure'],'explicit_responsibility_question_required_for_caller_premises')
  self.assertNotIn('checked_plan_feasibility',json.dumps(h.messages))
  self.assertNotIn('This caller rule',json.dumps(h.messages))
 def test_actual_ordinary_answer_smoke_one_final_call_with_checked_state(self):
  calls=[]
  receipt=answer_person_context(HCLCognitionLayer(lambda m:calls.append(m) or 'development stub'),QUERY,SOURCE,debug=True)
  self.assertEqual(len(calls),1);self.assertEqual(calls[0],list(receipt.prepared.messages))
  self.assertIn('checked_plan_feasibility',payload(receipt.prepared))
if __name__=='__main__':unittest.main()
