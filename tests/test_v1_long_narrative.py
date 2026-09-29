import unittest

from hcl.cognition.long_narrative import NarrativeCorpus


OPEN='Narrator: On 2026-01-02, Mira said, "I believe the gate is open."'
CLOSED='Narrator: On 2026-01-02, Mira said, "I do not believe the gate is open."'
LATE='Narrator: On 2026-01-05, Mira said, "I now know that the report was ready."'
STAMP='2026-01-08T00:00:00Z'


class LongNarrativeTests(unittest.TestCase):
    def corpus(self):
        c=NarrativeCorpus()
        c.put_chapter('alpha',OPEN,branch='main',recorded_at=STAMP,permitted_observers=('Analyst',))
        c.put_chapter('beta',CLOSED+'\n'+LATE,branch='main',recorded_at=STAMP,permitted_observers=('Analyst',))
        return c

    def replay(self,c,**kw):
        return c.replay('Mira',branch='main',story_through='2026-01-05',disclosed_through='2026-01-05',known_at=STAMP,observer='Analyst',**kw)

    def test_ordinary_multi_source_conflict_keeps_both_exact_sources(self):
        c=self.corpus();view=self.replay(c);p=view.payload
        self.assertEqual(len(p['events']),3)
        self.assertEqual(len(p['source_conflicts']),1)
        conflict=p['source_conflicts'][0]
        self.assertEqual(conflict['status'],'SAME_DAY_OPPOSED_SOURCE_REPORTS_NOT_WORLD_CONTRADICTION')
        closure=conflict['recorded_evidence_closure']
        self.assertEqual(closure['selection'],'FULL_RECORDED_GRAPH_CLOSURE')
        self.assertEqual({r['quote'] for r in closure['source_spans']},{OPEN,CLOSED})
        self.assertEqual(p['source_local_identity'],'SAME_SURFACE_ACROSS_CHAPTERS_NOT_PROVED_SAME_PERSON')
        self.assertIn('source_conflicts',view.messages(c,'What was reported about the gate?')[1]['content'])

    def test_three_time_slices_do_not_backfill_late_report(self):
        c=self.corpus()
        early=c.replay('Mira',branch='main',story_through='2026-01-02',disclosed_through='2026-01-02',known_at=STAMP,observer='Analyst')
        middle=c.replay('Mira',branch='main',story_through='2026-01-05',disclosed_through='2026-01-02',known_at=STAMP,observer='Analyst')
        late=self.replay(c)
        self.assertEqual(len(early.payload['events']),2)
        self.assertEqual(len(middle.payload['events']),2)
        self.assertEqual(len(late.payload['events']),3)
        self.assertNotIn(LATE,early.messages(c,'What was visible?')[1]['content'])
        self.assertEqual(late.payload['events'][-1]['character_knowledge'],'NOT_INFERRED')

    def test_late_recollection_challenge_remains_disputed_report(self):
        c=self.corpus()
        recall='Narrator: On 2026-01-05, Noor disclosed a recollection from 2026-01-03 of Mira saying on 2026-01-01, "I believe the gate is closed."'
        challenge="Narrator: On 2026-01-06, Kai challenged Noor's recollection from 2026-01-03 of Mira's statement on 2026-01-01."
        c.put_chapter('memory',recall+'\n'+challenge,branch='main',recorded_at=STAMP,permitted_observers=('Analyst',))
        before=c.replay('Mira',branch='main',story_through='2026-01-02',disclosed_through='2026-01-02',known_at=STAMP,observer='Analyst')
        after=c.replay('Mira',branch='main',story_through='2026-01-02',disclosed_through='2026-01-06',known_at=STAMP,observer='Analyst')
        self.assertNotIn(recall,[r['quote'] for r in before.payload['events']])
        remembered=next(r for r in after.payload['events'] if r['quote']==recall)
        self.assertEqual(remembered['challenge_status'],'CONTESTED_SOURCE_RECOLLECTION_NOT_FALSIFIED')
        self.assertEqual(remembered['character_knowledge'],'NOT_INFERRED')

    def test_branch_comparison_preserves_separate_possible_paths(self):
        c=NarrativeCorpus()
        c.put_chapter('main-copy',OPEN,branch='main',recorded_at=STAMP,permitted_observers=('Analyst',))
        c.put_chapter('alternate-copy',CLOSED,branch='alternate',recorded_at=STAMP,permitted_observers=('Analyst',))
        result=c.compare_branches('Mira','main','alternate',story_through='2026-01-02',disclosed_through='2026-01-02',known_at=STAMP,observer='Analyst')
        self.assertEqual(len(result.payload['divergences']),1)
        self.assertEqual(result.payload['divergences'][0]['status'],'CROSS_BRANCH_DIVERGENCE_NOT_SAME_WORLD_CONTRADICTION')
        self.assertEqual(result.payload['left']['source_conflicts'],[])
        self.assertEqual(result.payload['right']['source_conflicts'],[])
        self.assertIn('SEPARATE_POSSIBLE_PATHS',result.messages(c,'Compare the branches')[1]['content'])

    def test_correction_preserves_old_system_record_view_and_revocation_blocks_it(self):
        c=self.corpus();old=self.replay(c)
        c.put_chapter('alpha',OPEN.replace('open','closed'),branch='main',recorded_at='2026-01-09T00:00:00Z',permitted_observers=('Analyst',))
        self.assertIn(OPEN,[r['quote'] for r in old.payload['events']])
        self.assertEqual(len(old.payload['source_conflicts']),1)
        old.messages(c,'Earlier record')
        new=c.replay('Mira',branch='main',story_through='2026-01-05',disclosed_through='2026-01-05',known_at='2026-01-09T00:00:00Z',observer='Analyst')
        self.assertNotIn(OPEN,[r['quote'] for r in new.payload['events']])
        self.assertEqual(new.payload['source_conflicts'],[])
        new.messages(c,'Current record')
        c.put_chapter('alpha',OPEN,branch='main',recorded_at='2026-01-10T00:00:00Z',permitted_observers=())
        with self.assertRaisesRegex(ValueError,'access changed'):old.messages(c,'Earlier record')
        with self.assertRaisesRegex(ValueError,'access changed'):new.messages(c,'Current record')

    def test_unrelated_branch_does_not_change_selected_final_input(self):
        c=self.corpus();old=self.replay(c)
        c.put_chapter('alt','Narrator: On 2026-01-02, Noor said, "I believe the gate is closed."',branch='alternate',recorded_at='2026-01-01T00:00:00Z',permitted_observers=('Analyst',))
        self.assertEqual(old.messages(c,'What was reported?'),self.replay(c).messages(c,'What was reported?'))

    def test_other_actor_and_ambiguous_pronoun_not_assigned_to_mira(self):
        c=self.corpus()
        c.put_chapter('other','Narrator: On 2026-01-02, Noor said, "I believe the gate is open."\nNarrator: On 2026-01-02, she said, "I believe the gate is closed."',branch='main',recorded_at=STAMP,permitted_observers=('Analyst',))
        p=self.replay(c).payload
        self.assertEqual(len(p['events']),3)
        self.assertNotIn('Noor said',str(p['events']))
        self.assertNotIn('she said',str(p['events']))

    def test_f04_character_change_can_be_selected_inside_multi_source_replay(self):
        c=self.corpus()
        change='\n'.join([
            'Narrator: On 2026-01-01, Mira said, "I did not know that the report was ready."',
            'Narrator: On 2026-01-02, Mira did not submit the report.',
            'Narrator: On 2026-01-03, Mira said, "I now know that the report was ready."',
            'Narrator: On 2026-01-05, Mira did submit the report.'])
        c.put_chapter('change',change,branch='main',recorded_at=STAMP,permitted_observers=('Analyst',))
        result=self.replay(c,development_source='change',development_action='submit the report')
        self.assertIn('NEW_REPORTED_INFORMATION',{r['kind'] for r in result.payload['development']['candidates']})
        self.assertEqual(result.payload['development']['source_id'],'change')
        self.assertEqual(len(result.payload['source_conflicts']),1)

    def test_budgets_refuse_without_silent_event_or_conflict_drop(self):
        c=self.corpus()
        with self.assertRaisesRegex(ValueError,'person projection budget'):
            self.replay(c,max_person_events=2)
        c.put_chapter('gamma',CLOSED,branch='main',recorded_at=STAMP,permitted_observers=('Analyst',))
        with self.assertRaisesRegex(ValueError,'source conflict budget'):
            self.replay(c,max_conflicts=1)
        with self.assertRaisesRegex(ValueError,'context exceeds budget'):
            self.replay(c).messages(c,'What happened?',max_chars=1000)

    def test_branch_identity_and_authorization_boundaries(self):
        c=self.corpus()
        with self.assertRaisesRegex(ValueError,'another branch'):
            c.put_chapter('alpha',OPEN,branch='alternate',recorded_at='2026-01-09T00:00:00Z')
        with self.assertRaisesRegex(ValueError,'known branch'):
            c.replay('Mira',branch='missing',story_through='2026-01-02',disclosed_through='2026-01-02',known_at=STAMP)
        hidden=c.replay('Mira',branch='main',story_through='2026-01-05',disclosed_through='2026-01-05',known_at=STAMP,observer='Visitor')
        self.assertEqual(hidden.payload['events'],[])
        self.assertEqual(hidden.payload['source_versions'],[])

    def test_provider_free_twelve_actor_120_event_long_source_smoke(self):
        c=NarrativeCorpus()
        filler=' '.join(f'detail{n}' for n in range(160))
        total_chars=0
        for actor_index in range(12):
            actor=f'Actor{actor_index}'
            lines=[f'Narrator: On 2026-01-{day:02d}, {actor} said, "I believe event {day} for {actor} is recorded with {filler}."'
                for day in range(1,11)]
            chapter='\n'.join(lines);total_chars+=len(chapter)
            c.put_chapter(f'chapter-{actor_index}',chapter,branch='main',recorded_at=STAMP,
                permitted_observers=('Analyst',))
        self.assertGreater(total_chars,100000)
        early=c.replay('Actor0',branch='main',story_through='2026-01-03',disclosed_through='2026-01-03',known_at=STAMP,observer='Analyst')
        middle=c.replay('Actor0',branch='main',story_through='2026-01-06',disclosed_through='2026-01-06',known_at=STAMP,observer='Analyst')
        late=c.replay('Actor0',branch='main',story_through='2026-01-10',disclosed_through='2026-01-10',known_at=STAMP,observer='Analyst')
        self.assertEqual((len(early.payload['events']),len(middle.payload['events']),len(late.payload['events'])),(3,6,10))
        self.assertEqual(len(late.payload['source_versions']),12)
        self.assertEqual(len(late.messages(c,'What was reported by Actor0?')[1]['content'])>10000,True)
        self.assertNotIn('Actor11 said',str(late.payload['events']))


if __name__=='__main__':unittest.main()
