import unittest

from hcl.cognition.character_development import compare_character_development
from hcl.cognition.narrative_time import NarrativeTimeline


EARLY='''Narrator: On 2026-01-01, Mira said, "I did not know that the report was ready."
Narrator: On 2026-01-01, Mira said, "I want to protect the report."
Narrator: On 2026-01-01, Mira said, "As reviewer in team, I prefer safety over speed."
Narrator: On 2026-01-02, Mira did not submit the report.'''
LATER='''Narrator: On 2026-01-03, Mira said, "I now know that the report was ready."
Narrator: On 2026-01-03, Mira became reviewer in team.
Narrator: On 2026-01-04, Mira said, "As reviewer in team, I faced pressure to submit the report."
Narrator: On 2026-01-04, Mira said, "I now want to submit the report instead of protect the report."
Narrator: On 2026-01-04, Mira said, "As reviewer in team, I now prefer speed over safety instead of safety over speed."
Narrator: On 2026-01-04, Mira said, "I told Noor I wanted to submit the report so Noor would approve my plan."
Narrator: On 2026-01-05, Mira did submit the report.'''
SOURCE=EARLY+'\n'+LATER


class CharacterDevelopmentTests(unittest.TestCase):
    def timeline(self,text=SOURCE,acl=('Analyst',)):
        t=NarrativeTimeline();t.put_chapter('chapter',text,recorded_at='2026-01-08T00:00:00Z',permitted_observers=acl)
        return t

    def compare(self,t,**kw):
        return compare_character_development(t,'chapter','Mira','submit the report',through_date='2026-01-05',known_at='2026-01-08T00:00:00Z',observer='Analyst',**kw)

    def test_ordinary_positive_has_five_rival_factors_and_complete_sources(self):
        t=self.timeline();result=self.compare(t)
        p=result.payload
        self.assertEqual(p['status'],'COMPARABLE_ACTION_CHANGE')
        self.assertEqual({c['kind'] for c in p['candidates']},{'NEW_REPORTED_INFORMATION','EXPLICIT_REPORTED_GOAL_REVISION','EXPLICIT_REPORTED_VALUE_REVISION','REPORTED_ROLE_PRESSURE','EXPLICIT_REPORTED_AUDIENCE_STRATEGY'})
        self.assertEqual([r['story_time'] for r in p['action_pair']],['2026-01-02','2026-01-05'])
        self.assertEqual([r['quote'] for r in p['action_pair']],['Narrator: On 2026-01-02, Mira did not submit the report.','Narrator: On 2026-01-05, Mira did submit the report.'])
        closure=p['recorded_evidence_closure']
        self.assertEqual(closure['selection'],'FULL_RECORDED_GRAPH_CLOSURE')
        self.assertEqual(len(closure['claim_nodes']),6)
        self.assertEqual(len(closure['source_spans']),len(SOURCE.splitlines()))
        self.assertEqual(closure['target_status'],'SUPPORT_AVAILABLE')
        for candidate in p['candidates']:
            self.assertEqual(candidate['causal_status'],'NOT_ESTABLISHED')
            for factor in candidate['factor_sources']:
                self.assertIn(factor['quote'],SOURCE)
        self.assertIn('NEW_REPORTED_INFORMATION',result.messages(t,'What might explain the change?')[1]['content'])
        self.assertIn('private_knowledge',p['unsupported_inferences'])

    def test_later_knowledge_never_backfills_early_action(self):
        p=self.compare(self.timeline()).payload
        candidate=next(c for c in p['candidates'] if c['kind']=='NEW_REPORTED_INFORMATION')
        self.assertGreater(candidate['factor_sources'][1]['story_time'],p['action_pair'][0]['story_time'])
        self.assertEqual(candidate['private_state'],'NOT_INFERRED')

    def test_stated_continuing_goal_is_context_not_a_new_cause(self):
        text=SOURCE.replace('Narrator: On 2026-01-04, Mira said, "I now want to submit the report instead of protect the report."',
            'Narrator: On 2026-01-04, Mira said, "I still want to protect the report."')
        p=self.compare(self.timeline(text)).payload
        self.assertEqual(len(p['continuing_goal_reports']),1)
        self.assertNotIn('EXPLICIT_REPORTED_GOAL_REVISION',{c['kind'] for c in p['candidates']})
        self.assertIn('NEW_REPORTED_INFORMATION',{c['kind'] for c in p['candidates']})

    def test_same_day_factor_order_is_unresolved(self):
        text=SOURCE.replace('On 2026-01-03, Mira said, "I now know','On 2026-01-02, Mira said, "I now know')
        p=self.compare(self.timeline(text)).payload
        self.assertNotIn('NEW_REPORTED_INFORMATION',{c['kind'] for c in p['candidates']})

    def test_behavior_without_explicit_reports_does_not_infer_motive(self):
        text='Narrator: On 2026-01-02, Mira did not submit the report.\nNarrator: On 2026-01-05, Mira did submit the report.'
        p=self.compare(self.timeline(text)).payload
        self.assertEqual(p['status'],'COMPARABLE_ACTION_CHANGE')
        self.assertEqual(p['candidates'],[])

    def test_no_change_or_ambiguous_multiple_actions_refused(self):
        t=self.timeline(SOURCE.replace('did not submit','did submit'))
        self.assertEqual(self.compare(t).payload['status'],'NO_UNAMBIGUOUS_COMPARABLE_ACTION_CHANGE')
        t=self.timeline(SOURCE+'\nNarrator: On 2026-01-06, Mira did not submit the report.')
        result=compare_character_development(t,'chapter','Mira','submit the report',through_date='2026-01-06',known_at='2026-01-08T00:00:00Z',observer='Analyst')
        self.assertEqual(result.payload['status'],'NO_UNAMBIGUOUS_COMPARABLE_ACTION_CHANGE')

    def test_other_actor_or_different_action_cannot_supply_factor(self):
        text=SOURCE.replace('Mira said, "I now know','Noor said, "I now know').replace('Mira became reviewer','Noor became reviewer')
        p=self.compare(self.timeline(text)).payload
        self.assertNotIn('NEW_REPORTED_INFORMATION',{c['kind'] for c in p['candidates']})
        self.assertNotIn('REPORTED_ROLE_PRESSURE',{c['kind'] for c in p['candidates']})

    def test_role_report_without_appointment_does_not_prove_role_pressure(self):
        text=SOURCE.replace('Narrator: On 2026-01-03, Mira became reviewer in team.\n','')
        p=self.compare(self.timeline(text)).payload
        self.assertNotIn('REPORTED_ROLE_PRESSURE',{c['kind'] for c in p['candidates']})

    def test_report_without_explicit_revision_does_not_infer_goal_or_value_change(self):
        text=SOURCE.replace('I now want to submit the report instead of protect the report.','I want to submit the report.').replace('I now prefer speed over safety instead of safety over speed.','I prefer speed over safety.')
        kinds={c['kind'] for c in self.compare(self.timeline(text)).payload['candidates']}
        self.assertNotIn('EXPLICIT_REPORTED_GOAL_REVISION',kinds)
        self.assertNotIn('EXPLICIT_REPORTED_VALUE_REVISION',kinds)

    def test_access_and_source_revision_invalidate_final_input(self):
        t=self.timeline();prior=self.compare(t)
        t.put_chapter('chapter',SOURCE.replace('ready','complete'),recorded_at='2026-01-09T00:00:00Z',permitted_observers=('Analyst',))
        self.assertIn('ready',prior.messages(t,'Explain the earlier record')[1]['content'])
        updated=compare_character_development(t,'chapter','Mira','submit the report',through_date='2026-01-05',known_at='2026-01-09T00:00:00Z',observer='Analyst')
        self.assertIn('complete',updated.messages(t,'Explain the change')[1]['content'])
        t.put_chapter('chapter',SOURCE,recorded_at='2026-01-10T00:00:00Z',permitted_observers=())
        with self.assertRaisesRegex(ValueError,'access changed'):prior.messages(t,'Explain the earlier record')
        with self.assertRaisesRegex(ValueError,'access changed'):updated.messages(t,'Explain the change')
        with self.assertRaisesRegex(ValueError,'not authorized'):
            compare_character_development(t,'chapter','Mira','submit the report',through_date='2026-01-05',known_at='2026-01-10T00:00:00Z',observer='Analyst')

    def test_other_source_not_aliased_and_unrecorded_private_state_remains_unknown(self):
        t=self.timeline(EARLY+'\nNarrator: On 2026-01-05, Mira did submit the report.')
        t.put_chapter('other',LATER,recorded_at='2026-01-08T00:00:00Z',permitted_observers=('Analyst',))
        result=self.compare(t)
        self.assertEqual(result.payload['candidates'],[])
        self.assertNotIn('I now know',result.messages(t,'Explain the change')[1]['content'])

    def test_unrelated_source_revision_keeps_selected_comparison(self):
        t=self.timeline();prior=self.compare(t)
        t.put_chapter('unrelated','Narrator: On 2026-01-03, Noor said, "I believe the gate is closed."',
            recorded_at='2026-01-04T00:00:00Z',permitted_observers=('Analyst',))
        self.assertEqual(prior.messages(t,'Explain the change')[1]['content'],
            self.compare(t).messages(t,'Explain the change')[1]['content'])

    def test_f02_snapshot_accepts_action_role_with_exact_source_spans(self):
        t=self.timeline()
        view=t.snapshot(story_through='2026-01-05',disclosed_through='2026-01-05',known_at='2026-01-08T00:00:00Z',observer='Analyst')
        rows=[r for r in view.payload['narrative_order_events'] if r['authority'].startswith('NARRATED_ACTION') or r['authority'].startswith('NARRATED_ROLE')]
        self.assertEqual(len(rows),3)
        self.assertTrue(all(r['source_span_id'] and r['episodic_event_ref'] is None for r in rows))

    def test_excess_competing_candidates_refuse_instead_of_dropping_rivals(self):
        old='Narrator: On 2026-01-01, Mira said, "I did not know that the report was ready."'
        new='Narrator: On 2026-01-03, Mira said, "I now know that the report was ready."'
        text='\n'.join([old]*5+['Narrator: On 2026-01-02, Mira did not submit the report.']+
            [new]*5+['Narrator: On 2026-01-05, Mira did submit the report.'])
        with self.assertRaisesRegex(ValueError,'candidate budget'):self.compare(self.timeline(text))


if __name__=='__main__':unittest.main()
