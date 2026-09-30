"""Source-narrator reports reach existing B01 without becoming subject expression."""
import copy,json,unittest
from hcl.cognition.core import EvidenceCore,Scope
from hcl.cognition.semantic import AuthorizedText,prepare_semantics
from hcl.cognition.epistemic import check_epistemic_candidates
from hcl.v1 import HCLCognitionLayer,prepare_person_context,PerspectiveMode
from hcl.v1.long_source_question import prepare_long_source_context
from hcl.v1.person_question import answer_person_context
from scripts.serious_eval_full_source_arms_v10 import prepare_primary_arms_v10

Q='Which mental states are reported, by whom, and what remains unproved?'
def text(*rows):return 'Neutral ordinary archive record.\r\n'*750+'\r\n'+'\r\n\r\n'.join(rows)
def payload(p):return json.loads(p.messages[-1]['content'])
def prepare(s,**kw):return prepare_person_context(HCLCognitionLayer(lambda _:None),Q,s,**kw)
def checked(s,**kw):
    core=EvidenceCore();r=prepare_semantics(Q,(AuthorizedText('s',s),),core=core,narrator_reports=True,**kw)
    return core,r,check_epistemic_candidates(core,Q,r)

class NarratorEpistemicTests(unittest.TestCase):
    def test_positive_nested_denial_and_source_report_channel_are_in_actual_final_input(self):
        s=text('Mina does not believe that Jo believes the gate is safe.','Mina said: "I believe the gate is safe."')
        p=prepare(s);x=payload(p);rows=x['checked_epistemic']['epistemic_objects'];a,b=[r['public_expression'] for r in rows]
        self.assertEqual(x['sources'][0]['text'],s);self.assertEqual(a['channel'],'SOURCE_NARRATOR_ATTRIBUTION');self.assertEqual(b['channel'],'PUBLIC_EXPRESSION')
        tree=a['expressed_content'];self.assertEqual(tree['attitude'],'REPORTED_ATTRIBUTION');self.assertNotEqual(tree['holder'],'Mina')
        self.assertEqual((tree['content']['holder'],tree['content']['polarity']),('Mina','DENY'));self.assertEqual(tree['content']['content']['polarity'],'AFFIRM')
        self.assertIsNone(rows[0]['private_interpretation']);self.assertTrue(rows[1]['private_interpretation']['assumptions'])
        self.assertIn(a['original_quote'],s);self.assertTrue(p.preparation_receipt['specialized_cognition_treatment'])
    def test_projection_preserves_reporter_outer_denial_and_no_subject_direct_state(self):
        core,r,b=checked('Mina does not believe that Jo believes the gate is safe.')
        reporter=b.records[0].speaker
        self.assertFalse(b.project(core,('Mina',)))
        row=b.project(core,(reporter,'Mina','Jo'))[0]
        self.assertEqual(row['result'],'OUTER_ATTRIBUTION_DENIED');self.assertEqual(row['unprojected_inner_state'],'NO_INNER_POLARITY_INFERENCE')
        self.assertEqual(row['private_state'],'NOT_ESTABLISHED');self.assertEqual(row['world_truth'],'NOT_ESTABLISHED')
    def test_knowledge_exposure_understanding_and_uncertainty_remain_distinct(self):
        for utterance,attitude,polarity in [('Mina knows the gate is open.','KNOWLEDGE_CLAIM','AFFIRM'),('Mina heard the gate is open.','EXPOSURE_CLAIM','AFFIRM'),('Mina understands the gate is open.','UNDERSTANDING_CLAIM','AFFIRM'),('Mina is unsure whether the gate is open.','BELIEF','UNCERTAIN')]:
            c,r,b=checked(utterance);node=b.records[0].tree.content
            self.assertEqual((node.attitude.value,node.polarity),(attitude,polarity));self.assertIsNone(b.records[0].private_interpretation_id)
            self.assertEqual(b.project(c,(b.records[0].speaker,'Mina'))[0]['world_truth'],'NOT_ESTABLISHED')
    def test_actor_scope_conditional_quoted_stage_and_outcome_only_prose_refuse(self):
        for line in ['She believes the gate is open.','I believe the gate is open.','If Mina believes the gate is open.','Perhaps Mina believes the gate is open.','Later Mina believes the gate is open.','Mina is guilty because the gate broke.','Mina believes the gate is open. She left.','Mina believes [imagining] the gate is open.','Noor said: "Mina believes the gate is open."']:
            c,r,b=checked(line)
            self.assertFalse(any(c.claims[x.expression_id].content['channel']=='SOURCE_NARRATOR_ATTRIBUTION' for x in b.records),line)
    def test_multi_paragraph_embedded_quotes_and_hypothetical_prefix_refuse(self):
        for prefix in ['Hypothetical scene.\n\n','Noor said: "\n\n','“\n\n','[Imagining\n\n','```\n\n']:
            c,r,b=checked(prefix+'Mina believes the gate is open.\n\n')
            self.assertFalse(b.records,prefix)
    def test_source_local_reporters_do_not_merge_equal_names_across_sources(self):
        c=EvidenceCore();sources=(AuthorizedText('a','Mina believes the gate is open.'),AuthorizedText('b','Mina does not believe the gate is open.'))
        r=prepare_semantics(Q,sources,core=c,narrator_reports=True);b=check_epistemic_candidates(c,Q,r)
        self.assertNotEqual(b.records[0].speaker,b.records[1].speaker)
        self.assertFalse(b.compare_attribution(c,b.records[0].speaker,'Mina'))
    def test_source_version_withdrawal_removes_support_without_retroactive_inference(self):
        c,r,b=checked('Mina believes the gate is open.')
        c.withdraw(r.root_ids[0]);self.assertFalse(b.project(c,(b.records[0].speaker,'Mina')))
        self.assertFalse(check_epistemic_candidates(c,Q,r).records)
        c=EvidenceCore();r=prepare_semantics(Q,(AuthorizedText('s','Mina does not believe the gate is open.',version=2),),core=c,narrator_reports=True)
        b=check_epistemic_candidates(c,Q,r);self.assertEqual(b.records[0].tree.content.polarity,'DENY')
        self.assertTrue(all(c.spans[c.claims[k].content['source_span_id']].version==2 for k in r.candidate_ids))
    def test_time_access_order_and_ordinary_private_view_are_filtered_before_extraction(self):
        s=AuthorizedText('s','Mina knows the gate is open.',permitted_observers=('Mina',),event_time='2030-01-01T00:00:00Z',access_time='2030-01-01T00:00:00Z',order=2)
        for scope in (Scope(observer='Jo',source_ids=('s',)),Scope(source_ids=('s',),event_time='2029-01-01T00:00:00Z'),Scope(source_ids=('s',),through_order=1)):
            c=EvidenceCore();r=prepare_semantics(Q,(s,),core=c,scope=scope,narrator_reports=True);self.assertFalse(r.candidate_ids);self.assertNotIn('gate',json.dumps(r.messages))
        p=prepare(text('Mina knows the gate is open.'),perspective_mode=PerspectiveMode.OBSERVER_ABOUT_TARGET,observer_actor='Jo')
        self.assertNotIn('gate',json.dumps(p.messages))
    def test_unknown_time_is_not_character_access_or_chronology(self):
        c,r,b=checked('Mina knows the gate is open.')
        proposal=c.claims[r.candidate_ids[0]].content['proposal'];self.assertIsNone(proposal['event_time']);self.assertIsNone(proposal['access_time'])
        self.assertIn('not earlier character access',prepare(text('Mina knows the gate is open.')).messages[0]['content'])
    def test_hnew_retains_candidates_full_source_and_fair_cpg_input(self):
        s=text('Mina believes Jo does not believe the gate is open.')
        h=prepare_long_source_context(Q,s);n=prepare_long_source_context(Q,s,epistemic_checks=False)
        left,right=payload(h),payload(n);left.pop('checked_epistemic');self.assertEqual(left,right)
        for phase in ('C','P','G_map'):
            arm=json.loads(prepare_primary_arms_v10(Q,'ordinary-source',s)[phase][-1]['content']);self.assertEqual(arm['sources'][0]['text'],s);self.assertEqual(arm['question'],Q)
    def test_reports_do_not_fill_direct_c01_or_c03_belief_premises(self):
        s=text('Mina said: "I want to protect the gate."','Mina said: "I plan to call Jo in order to protect the gate if the gate is clear."','Mina said: "I have an opportunity to call Jo."','Mina believes the gate is clear.','Narrator: In the declared model, it is true that the gate is clear.')
        p=prepare(s);plan=payload(p)['checked_plan_feasibility'][0]['plans'][0]
        self.assertEqual(plan['subjective_condition'],'UNKNOWN');self.assertEqual(plan['subjective_feasibility'],'BELIEF_CONDITION_UNRESOLVED')
        self.assertEqual(plan['declared_model_condition'],'DECLARED_CONDITION_MET');self.assertEqual(plan['deliberate_impossibility'],'NOT_INFERRED')
    def test_local_revision_keeps_historical_input_and_unrelated_channel(self):
        s=text('Mina believes the gate is open.','Jo heard the gate is open.');old=prepare(s);before=copy.deepcopy(old.messages)
        new=prepare(s.replace('Mina believes','Mina does not believe'));self.assertEqual(old.messages,before)
        a=payload(old)['checked_epistemic']['epistemic_objects'];b=payload(new)['checked_epistemic']['epistemic_objects']
        self.assertEqual(a[1]['public_expression']['expressed_content'],b[1]['public_expression']['expressed_content'])
        self.assertEqual(a[0]['public_expression']['expressed_content']['content']['polarity'],'AFFIRM');self.assertEqual(b[0]['public_expression']['expressed_content']['content']['polarity'],'DENY')
    def test_bounded_depth_candidates_and_context_fail_without_silent_slice(self):
        c,r,b=checked('Mina believes Jo believes Kai believes the gate is open.')
        self.assertFalse(b.records);self.assertIn('modal_depth_exceeded_with_reporter',str(b.diagnostics))
        with self.assertRaisesRegex(ValueError,'no_silent_truncation'):prepare(text(*['Mina believes the gate is open.']*65))
        with self.assertRaisesRegex(ValueError,'context budget'):prepare_long_source_context(Q,text('Mina believes the gate is open.'),max_context_chars=512)
    def test_default_a02_and_unverified_backend_do_not_gain_authority(self):
        s=AuthorizedText('s','Mina believes the gate is open.')
        self.assertFalse(prepare_semantics(Q,(s,)).candidate_ids)
        class Backend:
            def complete_json(self,*a,**kw):return json.dumps({'candidates':[{'source_id':'s','quote':s.text,'kind':'event','content':{'speaker_surface':'Mina','utterance':'I believe the gate is open.'}}]})
        c=EvidenceCore();r=prepare_semantics(Q,(s,),core=c,narrator_reports=True,backend=Backend());self.assertFalse(check_epistemic_candidates(c,Q,r).records)
        with self.assertRaises(ValueError):prepare_semantics(Q,(s,),narrator_reports='yes')
    def test_ordinary_answer_is_single_final_call_with_actual_checked_state(self):
        calls=[];s=text('Mina believes the gate is open.')
        a=answer_person_context(HCLCognitionLayer(lambda m:calls.append(m) or 'correctness stub only'),Q,s,debug=True)
        self.assertEqual(len(calls),1);self.assertIn('checked_epistemic',payload(a.prepared));self.assertEqual(a.prepared.preparation_receipt['extraction_provider_calls'],0)
        self.assertFalse(a.prepared.preparation_receipt['epistemic_treatment']['answer_gain_established'])

if __name__=='__main__':unittest.main()
