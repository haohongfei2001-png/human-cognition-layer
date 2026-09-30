"""Existing B01 actually reaches ordinary long H input; no private truth oracle."""
import copy,json,unittest
from hcl.v1 import HCLCognitionLayer,prepare_person_context,PerspectiveMode
from hcl.v1.person_question import answer_person_context
from hcl.v1.long_source_question import prepare_long_source_context
from hcl.cognition.core import EvidenceCore,Scope
from hcl.cognition.semantic import AuthorizedText,prepare_semantics
from hcl.cognition.epistemic import check_epistemic_candidates,MentalProposition
from scripts.serious_eval_full_source_arms_v9 import prepare_primary_arms_v9

Q='How do the reported positions differ and what remains unproved?'
def source(report):return 'Neutral ordinary archive record.\r\n'*1800+report
def prepare(text,**kw):return prepare_person_context(HCLCognitionLayer(lambda _:None),Q,text,**kw)
def payload(prepared):return json.loads(prepared.messages[-1]['content'])
def objects(prepared):return payload(prepared)['checked_epistemic']['epistemic_objects']
class LongEpistemicIntegrationTests(unittest.TestCase):
    def test_positive_nested_modal_channels_in_actual_final_input(self):
        text=source('Mina said: "I believe the gate is open."\nNoor said: "Mina believes the gate is closed."\nKai said: "I know the gate is open."\nKai said: "I heard the gate is open."')
        p=prepare(text);rows=objects(p)
        self.assertEqual(payload(p)['sources'][0]['text'],text)
        self.assertEqual(len(rows),4);self.assertTrue(p.preparation_receipt['specialized_cognition_treatment'])
        direct=rows[0]['public_expression']['expressed_content'];attributed=rows[1]['public_expression']['expressed_content']
        self.assertEqual(direct['holder'],'Mina');self.assertEqual(attributed['holder'],'Noor')
        self.assertEqual(attributed['attitude'],'REPORTED_ATTRIBUTION');self.assertEqual(attributed['content']['holder'],'Mina')
        self.assertEqual(rows[2]['public_expression']['expressed_content']['attitude'],'KNOWLEDGE_CLAIM')
        self.assertEqual(rows[3]['public_expression']['expressed_content']['attitude'],'EXPOSURE_CLAIM')
        self.assertIsNone(rows[2]['private_interpretation']);self.assertIsNone(rows[3]['private_interpretation'])
        self.assertEqual(rows[0]['private_interpretation']['hypothesis']['epistemic_status'],'DEFEASIBLE_NOT_CONFIRMED')
        self.assertTrue(rows[0]['private_interpretation']['assumptions'])
        self.assertEqual(rows[0]['support_status'],'SUPPORT_AVAILABLE')
    def test_hnew_removes_only_checked_mechanism_equal_task_source_candidates(self):
        text=source('Mina said: "I believe the gate is open."')
        h=prepare_long_source_context(Q,text);n=prepare_long_source_context(Q,text,epistemic_checks=False)
        left,right=payload(h),payload(n);left.pop('checked_epistemic')
        self.assertEqual(left,right);self.assertTrue(h.messages[0]['content'].startswith(n.messages[0]['content']))
        self.assertFalse(n.preparation_receipt['specialized_cognition_treatment'])
        arms=prepare_primary_arms_v9(Q,'ordinary-source',text)
        for name in ('C','P','G_map'):
            row=json.loads(arms[name][-1]['content']);self.assertEqual(row['sources'][0]['text'],text);self.assertEqual(row['question'],Q)
    def test_outer_denial_never_detaches_inner_denial_or_private_state(self):
        text=source('Mina said: "I do not believe Noor believes the gate is open."')
        p=prepare_person_context(HCLCognitionLayer(lambda _:None),'What does Mina believe Noor believes?',text)
        checked=payload(p)['checked_epistemic'];projection=checked['query_projection'][0]
        self.assertEqual(projection['result'],'OUTER_ATTRIBUTION_DENIED')
        self.assertEqual(projection['unprojected_inner_state'],'NO_INNER_POLARITY_INFERENCE')
        self.assertEqual(projection['private_state'],'NOT_ESTABLISHED');self.assertEqual(projection['world_truth'],'NOT_ESTABLISHED')
        self.assertEqual(projection['chain'][1]['polarity'],'AFFIRM')
    def test_unresolved_conditional_and_plain_action_have_no_treatment(self):
        for report in ('She said: "I believe the gate is open."','If Mina said: "I believe the gate is open."','Mina said: "I opened the gate."'):
            p=prepare(source(report));self.assertNotIn('checked_epistemic',payload(p));self.assertFalse(p.preparation_receipt['specialized_cognition_treatment'])
        p=prepare(source('Mina said: "I believe the gate is open."'),perspective_mode=PerspectiveMode.OBSERVER_ABOUT_TARGET,observer_actor='Noor')
        self.assertNotIn('checked_epistemic',payload(p));self.assertNotIn('gate',json.dumps(p.messages))
    def test_local_revision_keeps_previous_input_and_other_actor_expression(self):
        first=source('Noor said: "I am unsure whether the gate is open."\nMina said: "I believe the gate is open."')
        old=prepare(first);old_messages=copy.deepcopy(old.messages)
        new=prepare(first.replace('Mina said: "I believe','Mina said: "I do not believe'))
        self.assertEqual(old.messages,old_messages)
        # Source hashes/offset identities are versioned; compare unaffected semantics.
        for key in ('expressed_content','original_quote','semantics'):
            self.assertEqual(objects(old)[0]['public_expression'][key],objects(new)[0]['public_expression'][key])
        self.assertEqual(objects(old)[0]['support_status'],objects(new)[0]['support_status'])
        self.assertEqual(objects(old)[1]['public_expression']['expressed_content']['polarity'],'AFFIRM')
        self.assertEqual(objects(new)[1]['public_expression']['expressed_content']['polarity'],'DENY')
        self.assertIn('Narrative order does not establish',new.messages[0]['content'])
    def test_grounded_core_boundary_and_unverified_semantics(self):
        core=EvidenceCore();result=prepare_semantics(Q,(AuthorizedText('s','Mina said: "I believe the gate is open."'),),core=core)
        with self.assertRaisesRegex(ValueError,'grounded core'):check_epistemic_candidates(EvidenceCore(),Q,result)
        self.assertIsInstance(check_epistemic_candidates(core,Q,result).records[0].tree,MentalProposition)
        core.withdraw(result.root_ids[0])
        self.assertFalse(check_epistemic_candidates(core,Q,result).records)
        class Backend:
            def complete_json(self,*a,**kw):return json.dumps({'candidates':[dict(source_id='s',quote='Mina said: "I believe the gate is open."',kind='event',content=dict(speaker_surface='Noor',utterance='I believe the gate is open.'))]})
        c=EvidenceCore();r=prepare_semantics(Q,(AuthorizedText('s','Mina said: "I believe the gate is open."'),),core=c,backend=Backend())
        checked=check_epistemic_candidates(c,Q,r);self.assertFalse(checked.records);self.assertTrue(checked.diagnostics)
    def test_ordinary_answer_is_one_call_with_checked_state_not_extraction(self):
        calls=[];text=source('Mina said: "I believe the gate is open."')
        def final(messages):calls.append(messages);return 'not a semantic evaluation'
        answer=answer_person_context(HCLCognitionLayer(final),Q,text,debug=True)
        p=answer.prepared
        self.assertEqual(len(calls),1);self.assertIn('checked_epistemic',payload(p));self.assertEqual(p.preparation_receipt['extraction_provider_calls'],0)
        self.assertFalse(p.preparation_receipt['epistemic_treatment']['answer_gain_established'])
if __name__=='__main__':unittest.main()
