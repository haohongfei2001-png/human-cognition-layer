"""Reuse C01 on actual complete-source H input; no source oracle or new mechanism."""
import copy,json,unittest
from hcl.v1 import HCLCognitionLayer,prepare_person_context,PerspectiveMode
from hcl.v1.person_question import answer_person_context
from hcl.v1.long_source_question import prepare_long_source_context
from hcl.cognition.workspace import CognitionWorkspace
from hcl.cognition.semantic import AuthorizedText,prepare_semantics
from hcl.cognition.agency import check_agency_candidates
Q='Which reported goals and plans are supported, and what prevents pursuit?'
G='Mina said: "I want to protect the gate."'
P='Mina said: "I plan to call Noor in order to protect the gate."'
O='Mina said: "I have no opportunity to call Noor."'
def source(*lines):return 'Ordinary authored archive record.\n'*700+'\n'+'\n'.join(lines)
def prepare(s,**kw):return prepare_person_context(HCLCognitionLayer(lambda _:None),Q,s,**kw)
def payload(p):return json.loads(p.messages[-1]['content'])
def agency(p):return payload(p)['checked_agency'][0]['cognition']
class LongAgencyIntegrationTests(unittest.TestCase):
    def test_positive_actual_goal_plan_opportunity_join_not_private_truth(self):
        s=source(G,P,O);p=prepare(s);a=agency(p)
        self.assertEqual(a['goals'][0]['status'],'ACTIVE')
        plan=a['plans'][0];self.assertEqual(plan['selection'],'REPORTED_SELECTED')
        self.assertEqual(plan['pursuit_check'],'OPPORTUNITY_CONTRADICTED')
        self.assertEqual(plan['success'],'NOT_ESTABLISHED');self.assertEqual(plan['private_intention'],'NOT_VERIFIED')
        self.assertTrue(p.preparation_receipt['specialized_cognition_treatment'])
        self.assertEqual(payload(p)['sources'][0]['text'],s);self.assertNotIn('original_sources',a)
        self.assertEqual(a['shared_source_references'][0]['source_id'],'ordinary-source')
        evidence=payload(p)['checked_agency'][0]['evidence']
        self.assertTrue(all(span['quote'] in s for span in evidence['spans']))
    def test_positive_available_and_abandoned_goal_changes_pursuit_without_plan_revocation(self):
        initial=source(G,P,O.replace('no opportunity','an opportunity'));old=prepare(initial)
        self.assertEqual(agency(old)['plans'][0]['pursuit_check'],'SOURCE_SUPPORTED_PURSUIT_NOT_WORLD_FEASIBILITY')
        saved=copy.deepcopy(old.messages)
        new=prepare(initial+'\nMina said: "I abandoned my goal to protect the gate."')
        self.assertEqual(old.messages,saved);self.assertEqual(agency(new)['goals'][0]['status'],'ABANDONED')
        self.assertEqual(agency(new)['plans'][0]['pursuit_check'],'GOAL_NOT_REPORTED_ACTIVE')
        self.assertEqual(agency(new)['plans'][0]['selection'],'REPORTED_SELECTED')
    def test_consideration_condition_actor_and_outcome_stay_separate(self):
        p=prepare(source(G,P.replace('plan to','am considering a plan to'),O))
        self.assertEqual(agency(p)['plans'][0]['pursuit_check'],'NO_SELECTED_PLAN')
        p=prepare(source(G,P.replace('gate.','gate if the bridge is clear.'),O.replace('no opportunity','an opportunity')))
        self.assertEqual(agency(p)['plans'][0]['pursuit_check'],'CONDITION_REQUIRES_CHECK')
        p=prepare(source(G,P,O.replace('Mina','Noor'),'Mina said: "I protected the gate."'))
        rows=payload(p)['checked_agency'];mina=next(r['cognition'] for r in rows if r['cognition']['actor']=='Mina')
        self.assertEqual(mina['plans'][0]['pursuit_check'],'OPPORTUNITY_UNRESOLVED')
        self.assertEqual(mina['goals'][0]['status'],'ACTIVE');self.assertFalse(mina['intentions'])
    def test_ordinary_typographic_selection_retains_c01_events_in_both_arms(self):
        s=source('\n\n'.join(['_Mina._ We wait by the gate.']*60+['_Mina._ I want to protect the gate.','_Mina._ I plan to call Noor in order to protect the gate.','_Mina._ I have no opportunity to call Noor.','_Noor._ I believe the gate is open.']))
        h=prepare_long_source_context(Q,s);n=prepare_long_source_context(Q,s,agency_checks=False)
        left,right=payload(h),payload(n);left.pop('checked_agency');self.assertEqual(left,right)
        self.assertEqual(h.preparation_receipt['dialogue_selection'],n.preparation_receipt['dialogue_selection'])
        self.assertIn('checked_epistemic',right);self.assertNotIn('checked_agency',right)
        self.assertEqual(agency(h)['plans'][0]['pursuit_check'],'OPPORTUNITY_CONTRADICTED')
        self.assertEqual(payload(h)['sources'][0]['text'],s)
    def test_conditional_pronoun_and_private_access_do_not_create_agency_state(self):
        for line in (G.replace('Mina','She'),'If '+G,'_Mina._ [imagining] I want to protect the gate.'):
            p=prepare(source(line));self.assertNotIn('checked_agency',payload(p))
        p=prepare(source(G,P,O),perspective_mode=PerspectiveMode.OBSERVER_ABOUT_TARGET,observer_actor='Noor')
        self.assertNotIn('protect the gate',json.dumps(p.messages))
    def test_grounded_core_version_and_support_revisions_require_recompute(self):
        w=CognitionWorkspace();w.put_source('s',G)
        sem=w.prepare_semantic(Q,source_ids=('s',))
        other=CognitionWorkspace();other.put_source('s',G)
        with self.assertRaisesRegex(ValueError,'grounded core'):check_agency_candidates(other,Q,sem,source_id='s',actor='Mina')
        r=check_agency_candidates(w,Q,sem,source_id='s',actor='Mina');self.assertTrue(r.payload['goals'])
        w.put_source('s',G.replace('protect','open'))
        with self.assertRaisesRegex(ValueError,'version changed'):check_agency_candidates(w,Q,sem,source_id='s',actor='Mina')
        with self.assertRaises(ValueError):r.messages(w,include_sources=False)
    def test_statement_actor_and_final_context_caps_never_silently_drop(self):
        with self.assertRaisesRegex(ValueError,'agency statement budget'):
            prepare(source(*[f'Mina said: "I want to task{i}."' for i in range(17)]))
        with self.assertRaisesRegex(ValueError,'actor budget'):
            prepare(source(*[f'{actor} said: "I want to protect the gate."' for actor in ('Mina','Noor','Kai','Sora','Ari')]))
        with self.assertRaises(ValueError):prepare(source(G,P,O),max_context_chars=1000)
    def test_b01_composition_and_one_final_call_without_extraction(self):
        s=source(G,P,O,'Noor said: "I do not believe Mina believes the gate is safe."')
        calls=[];r=answer_person_context(HCLCognitionLayer(lambda m:calls.append(m) or 'development stub'),Q,s,debug=True)
        self.assertEqual(len(calls),1);self.assertIn('checked_epistemic',payload(r.prepared));self.assertIn('checked_agency',payload(r.prepared))
        self.assertEqual(r.prepared.preparation_receipt['extraction_provider_calls'],0)
        self.assertFalse(r.prepared.preparation_receipt['agency_treatment']['answer_gain_established'])
if __name__=='__main__':unittest.main()
