import unittest

from hcl.cognition.normative_premises import NormativePremiseWorkspace
from hcl.v1.cg03 import NarrativePremise, ResponsibilityFactor


STAMP='2026-01-08T00:00:00Z'
SOURCE='''Institution team policy: responsibility requires knowledge and control.
Mira said, "I believe responsibility requires intention."
Narrator: On 2026-01-03, Noor said, "I endorse responsibility requires foreseeability."'''


class NormativePremisesTests(unittest.TestCase):
    def workspace(self,text=SOURCE,acl=('Analyst',),**kwargs):
        w=NormativePremiseWorkspace()
        w.put_source('story',text,recorded_at=STAMP,permitted_observers=acl,**kwargs)
        return w

    def test_ordinary_user_character_institution_and_analyst_origins_separate(self):
        w=self.workspace()
        result=w.prepare('For this analysis, responsibility requires knowledge and control. Was Mira responsible?',
            observer='Analyst',known_at='2026-01-09T00:00:00Z',
            adopted_framework_text='a person is responsible only if they knew about the risk and could prevent the harm')
        rows=result.payload['candidates']
        self.assertEqual([r['origin'] for r in rows],['USER_SUPPLIED','ANALYST_ADOPTED','INSTITUTION_REPORTED','CHARACTER_REPORTED_ENDORSEMENT','CHARACTER_REPORTED_ENDORSEMENT'])
        self.assertEqual([r['executable_as_caller_condition'] for r in rows],[True,True,False,False,False])
        self.assertEqual(len(result.typed_premises),2)
        self.assertTrue(all(isinstance(p,NarrativePremise) for p in result.typed_premises))
        self.assertEqual({r.factor for r in result.typed_premises[0].requirements},{ResponsibilityFactor.KNOWLEDGE,ResponsibilityFactor.CONTROL})
        self.assertEqual([r['actor'] for r in rows[3:]],['Mira','Noor'])
        for row in rows[2:]:
            self.assertEqual(SOURCE[row['source']['start']:row['source']['end']],row['source']['quote'])
        self.assertEqual(result.payload['conclusion'],'NO_MORAL_OR_LEGAL_VERDICT')
        self.assertIn('CHARACTER_REPORTED_ENDORSEMENT',result.messages(w)[1]['content'])

    def test_unadopted_automatic_framework_is_never_executable(self):
        w=self.workspace('Mira did the action.')
        r=w.prepare('Was Mira responsible?',observer='Analyst')
        self.assertEqual([c['origin'] for c in r.payload['candidates']],['ANALYST_PROPOSED_UNADOPTED'])
        self.assertEqual(r.typed_premises,())
        self.assertFalse(r.payload['candidates'][0]['executable_as_caller_condition'])

    def test_source_only_rules_never_become_caller_rules(self):
        w=self.workspace();r=w.prepare('What rules are reported?',observer='Analyst')
        self.assertEqual(r.typed_premises,())
        self.assertEqual(len(r.payload['candidates']),3)
        self.assertTrue(all(c['authority']=='CONDITIONAL_NOT_MORAL_TRUTH' for c in r.payload['candidates']))

    def test_third_party_attribution_does_not_create_character_endorsement(self):
        w=self.workspace('Noor said, "Mira believes responsibility requires knowledge."')
        r=w.prepare('What does the source say about responsibility?',observer='Analyst')
        self.assertEqual([c['origin'] for c in r.payload['candidates']],['ANALYST_PROPOSED_UNADOPTED'])
        self.assertEqual(r.payload['diagnostics'][0]['status'],'UNRESOLVED_NORMATIVE_SOURCE_FORM')

    def test_disjunction_and_unknown_terms_refuse_typed_requirement(self):
        w=self.workspace('Institution team policy: responsibility requires knowledge or control.')
        r=w.prepare('For this analysis, responsibility requires knowledge or control. Was Mira responsible?',observer='Analyst')
        self.assertEqual(r.typed_premises,())
        self.assertEqual(r.payload['candidates'][0]['parse_status'],'UNRESOLVED_RULE_LOGIC')
        w=self.workspace('Institution team policy: responsibility requires knowledge and kindness.')
        r=w.prepare('For this analysis, responsibility requires knowledge and kindness. Was Mira responsible?',observer='Analyst')
        self.assertEqual(r.typed_premises,())
        self.assertEqual(r.payload['candidates'][0]['parse_status'],'UNRESOLVED_RULE_TERM')

    def test_source_actor_date_is_reported_not_normative_truth(self):
        w=self.workspace();r=w.prepare('What does Noor endorse?',observer='Analyst')
        noor=next(c for c in r.payload['candidates'] if c['actor']=='Noor')
        self.assertEqual(noor['declared_day'],'2026-01-03')
        self.assertEqual(noor['private_endorsement'],'SOURCE_REPORTED_NOT_VERIFIED')
        self.assertFalse(noor['executable_as_caller_condition'])

    def test_access_event_and_record_cutoffs_filter_source_before_parsing(self):
        w=self.workspace(event_time='2026-01-05T00:00:00Z',access_time='2026-01-06T00:00:00Z')
        kwargs=dict(observer='Analyst',event_through='2026-01-06T00:00:00Z',
            access_through='2026-01-07T00:00:00Z',known_at='2026-01-09T00:00:00Z')
        self.assertEqual(len(w.prepare('What rules are reported?',**kwargs).payload['candidates']),3)
        self.assertEqual(w.prepare('What rules are reported?',**{**kwargs,'event_through':'2026-01-04T00:00:00Z'}).payload['candidates'],[])
        self.assertEqual(w.prepare('What rules are reported?',**{**kwargs,'access_through':'2026-01-05T00:00:00Z'}).payload['candidates'],[])
        self.assertEqual(w.prepare('What rules are reported?',**{**kwargs,'known_at':'2026-01-07T00:00:00Z'}).payload['candidates'],[])
        self.assertEqual(w.prepare('What rules are reported?',observer='Visitor',known_at='2026-01-09T00:00:00Z').payload['candidates'],[])

    def test_revision_and_revocation_invalidate_prepared_model_input(self):
        w=self.workspace();old=w.prepare('What rules are reported?',observer='Analyst')
        w.put_source('story',SOURCE.replace('knowledge and control','knowledge'),recorded_at='2026-01-09T00:00:00Z',permitted_observers=('Analyst',))
        with self.assertRaisesRegex(ValueError,'changed'):old.messages(w)
        current=w.prepare('What rules are reported?',observer='Analyst')
        self.assertNotEqual(old.payload['selected_versions'],current.payload['selected_versions'])
        w.put_source('story',SOURCE,recorded_at='2026-01-10T00:00:00Z',permitted_observers=())
        with self.assertRaisesRegex(ValueError,'access changed'):current.messages(w)

    def test_hidden_source_addition_does_not_change_authorized_view(self):
        w=self.workspace();old=w.prepare('What rules are reported?',observer='Analyst')
        w.put_source('hidden','Institution team policy: responsibility requires intention.',recorded_at=STAMP,permitted_observers=('Noor',))
        self.assertEqual(old.messages(w),w.prepare('What rules are reported?',observer='Analyst').messages(w))

    def test_visible_source_addition_invalidates_selection(self):
        w=self.workspace();old=w.prepare('What rules are reported?',observer='Analyst')
        w.put_source('new','Institution home policy: responsibility requires control.',recorded_at=STAMP,permitted_observers=('Analyst',))
        with self.assertRaisesRegex(ValueError,'changed'):old.messages(w)

    def test_budget_and_unsupported_rule_do_not_truncate_into_truth(self):
        w=self.workspace('\n'.join(['Institution team policy: responsibility requires knowledge.']*3))
        with self.assertRaisesRegex(ValueError,'candidate budget'):
            w.prepare('What rules are reported?',observer='Analyst',max_candidates=2)
        with self.assertRaisesRegex(ValueError,'context exceeds budget'):
            w.prepare('What rules are reported?',observer='Analyst').messages(w,max_chars=1000)


if __name__=='__main__':unittest.main()
