import unittest
from hcl.cognition.narrative_time import parse_narrative_episodes


class NarrativeTimeParserTests(unittest.TestCase):
    def test_recall_preserves_four_axes_and_source(self):
        text='Narrator: On 2026-01-05, Noor disclosed a recollection from 2026-01-03 of Mira saying on 2026-01-01, "I believe the bridge is open."'
        events,diagnostics=parse_narrative_episodes('chapter',text,recorded_at='2026-01-06T00:00:00Z')
        self.assertEqual(diagnostics,())
        row=events[0]
        self.assertEqual((row.story_time,row.recall_time,row.disclosure_time,row.narrative_order),('2026-01-01','2026-01-03','2026-01-05',1))
        self.assertEqual(text[row.start:row.end],row.quote)
        self.assertEqual(row.authority,'ATTRIBUTED_RECOLLECTION_NOT_DIRECT_SELF_REPORT')

    def test_ambiguous_reference_not_resolved_by_recollection(self):
        text='Narrator: On 2026-01-05, Noor disclosed a recollection from 2026-01-03 of she saying on 2026-01-01, "The bridge is open."'
        events,_=parse_narrative_episodes('chapter',text,recorded_at='2026-01-06T00:00:00Z')
        self.assertEqual(events[0].reference_status,'UNRESOLVED_REFERENCE')

    def test_impossible_order_is_diagnostic_not_repaired(self):
        text='Narrator: On 2026-01-02, Noor disclosed a recollection from 2026-01-03 of Mira saying on 2026-01-01, "The bridge is open."'
        events,diagnostics=parse_narrative_episodes('chapter',text,recorded_at='2026-01-06T00:00:00Z')
        self.assertEqual(diagnostics[0]['status'],'CONFLICTING_DECLARED_TIMES')
        self.assertEqual(events[0].disclosure_time,'2026-01-02')

    def test_undated_source_not_given_source_order_timestamp(self):
        events,diagnostics=parse_narrative_episodes('chapter','Mira said, "The bridge is open."',recorded_at='2026-01-06T00:00:00Z')
        self.assertEqual(events,())
        self.assertEqual(diagnostics[0]['status'],'UNRESOLVED_TEMPORAL_FORM')

from hcl.cognition.narrative_time import NarrativeTimeline

DIRECT='Narrator: On 2026-01-02, Mira said, "I believe the bridge is closed."'
RECALL='Narrator: On 2026-01-05, Noor disclosed a recollection from 2026-01-03 of Mira saying on 2026-01-01, "I believe the bridge is open."'
CHALLENGE="Narrator: On 2026-01-06, Kai challenged Noor's recollection from 2026-01-03 of Mira's statement on 2026-01-01."
RECEIPT="Narrator: On 2026-01-07, Mira heard Noor's disclosure from 2026-01-05."


class NarrativeTimelineTests(unittest.TestCase):
    def timeline(self):
        t=NarrativeTimeline()
        t.put_chapter('chapter',DIRECT+'\n'+RECALL+'\n'+CHALLENGE+'\n'+RECEIPT,
            recorded_at='2026-01-08T00:00:00Z',permitted_observers=('Analyst',))
        return t

    def test_late_recall_preserves_old_story_time_and_new_disclosure(self):
        t=self.timeline()
        early=t.snapshot(story_through='2026-01-03',disclosed_through='2026-01-03',known_at='2026-01-08T00:00:00Z',observer='Analyst')
        self.assertEqual(len(early.payload['narrative_order_events']),1)
        later=t.snapshot(story_through='2026-01-03',disclosed_through='2026-01-05',known_at='2026-01-08T00:00:00Z',observer='Analyst')
        events=later.payload['narrative_order_events']
        self.assertEqual([r['story_time'] for r in events],['2026-01-02','2026-01-01'])
        self.assertEqual([r['disclosure_time'] for r in events],['2026-01-02','2026-01-05'])
        self.assertEqual(later.payload['story_order_event_ids'],[events[1]['episode_id'],events[0]['episode_id']])
        self.assertIn('ATTRIBUTED_RECOLLECTION',later.messages(t,'What was reported about the bridge?')[1]['content'])
        self.assertEqual(events[1]['character_knowledge'],'NOT_INFERRED')

    def test_challenge_contests_recollection_without_declaring_falsity(self):
        t=self.timeline()
        before=t.snapshot(story_through='2026-01-03',disclosed_through='2026-01-05',known_at='2026-01-08T00:00:00Z')
        after=t.snapshot(story_through='2026-01-03',disclosed_through='2026-01-06',known_at='2026-01-08T00:00:00Z')
        old=next(r for r in before.payload['narrative_order_events'] if r['authority'].startswith('ATTRIBUTED'))
        new=next(r for r in after.payload['narrative_order_events'] if r['authority'].startswith('ATTRIBUTED'))
        self.assertEqual(old['challenge_status'],'NO_EXPLICIT_CHALLENGE_IN_VIEW')
        self.assertEqual(new['challenge_status'],'CONTESTED_SOURCE_RECOLLECTION_NOT_FALSIFIED')
        self.assertEqual(after.payload['world_truth'],'NOT_ESTABLISHED')

    def test_source_reported_receipt_changes_character_access_only_after_date(self):
        t=self.timeline()
        early=t.snapshot(story_through='2026-01-03',disclosed_through='2026-01-06',known_at='2026-01-08T00:00:00Z',character='Mira')
        self.assertEqual(early.payload['narrative_order_events'],[])
        later=t.snapshot(story_through='2026-01-03',disclosed_through='2026-01-07',known_at='2026-01-08T00:00:00Z',character='Mira')
        rows=later.payload['narrative_order_events']
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]['quote'],RECALL)
        self.assertEqual(rows[0]['receipt_source']['quote'],RECEIPT)
        self.assertEqual(rows[0]['character_receipt'],'EXPLICIT_REPORTED_RECEIPT_NOT_BELIEF')
        self.assertEqual(rows[0]['character_knowledge'],'NOT_INFERRED')

    def test_ambiguous_receipt_anchor_withholds_character_view(self):
        t=NarrativeTimeline()
        t.put_chapter('c',RECALL+'\n'+RECALL+'\n'+RECEIPT,
            recorded_at='2026-01-08T00:00:00Z')
        view=t.snapshot(story_through='2026-01-03',disclosed_through='2026-01-07',known_at='2026-01-08T00:00:00Z',character='Mira')
        self.assertEqual(view.payload['narrative_order_events'],[])

    def test_system_record_cutoff_keeps_late_source_out_of_earlier_analysis(self):
        t=NarrativeTimeline()
        t.put_chapter('early',DIRECT,recorded_at='2026-01-03T00:00:00Z')
        t.put_chapter('late',RECALL,recorded_at='2026-01-08T00:00:00Z')
        before=t.snapshot(story_through='2026-01-05',disclosed_through='2026-01-05',known_at='2026-01-04T00:00:00Z')
        self.assertEqual(len(before.payload['narrative_order_events']),1)
        after=t.snapshot(story_through='2026-01-05',disclosed_through='2026-01-05',known_at='2026-01-08T00:00:00Z')
        self.assertEqual(len(after.payload['narrative_order_events']),2)
        self.assertIn('late',dict(after.payload['source_versions']))

    def test_source_correction_does_not_backfill_old_record_view(self):
        t=NarrativeTimeline()
        t.put_chapter('c',DIRECT,recorded_at='2026-01-03T00:00:00Z')
        prior=t.snapshot(story_through='2026-01-05',disclosed_through='2026-01-05',known_at='2026-01-04T00:00:00Z')
        t.put_chapter('c',DIRECT.replace('closed','open'),recorded_at='2026-01-08T00:00:00Z')
        current=t.snapshot(story_through='2026-01-05',disclosed_through='2026-01-05',known_at='2026-01-08T00:00:00Z')
        self.assertIn('closed',prior.messages(t,'What was reported?')[1]['content'])
        self.assertIn('open',current.messages(t,'What was reported?')[1]['content'])
        self.assertEqual(current.payload['narrative_order_events'][0]['source_version'],2)
        self.assertNotEqual(prior.payload['narrative_order_events'][0]['source_span_id'],current.payload['narrative_order_events'][0]['source_span_id'])

    def test_new_backdated_record_invalidates_cached_historical_view(self):
        t=NarrativeTimeline()
        t.put_chapter('c',DIRECT,recorded_at='2026-01-03T00:00:00Z')
        prior=t.snapshot(story_through='2026-01-05',disclosed_through='2026-01-05',known_at='2026-01-04T00:00:00Z')
        t.put_chapter('other',RECALL,recorded_at='2026-01-02T00:00:00Z')
        with self.assertRaisesRegex(ValueError,'selection'):prior.messages(t,'What was reported?')

    def test_access_revocation_prevents_old_source_material(self):
        t=NarrativeTimeline()
        t.put_chapter('c',DIRECT,recorded_at='2026-01-03T00:00:00Z',permitted_observers=('Analyst',))
        prior=t.snapshot(story_through='2026-01-05',disclosed_through='2026-01-05',known_at='2026-01-04T00:00:00Z',observer='Analyst')
        t.put_chapter('c',DIRECT,recorded_at='2026-01-08T00:00:00Z',permitted_observers=())
        with self.assertRaisesRegex(ValueError,'access changed'):prior.messages(t,'What was reported?')
        current=t.snapshot(story_through='2026-01-05',disclosed_through='2026-01-05',known_at='2026-01-08T00:00:00Z',observer='Analyst')
        self.assertEqual(current.payload['narrative_order_events'],[])

    def test_wrong_challenge_anchor_does_not_mark_report_contested(self):
        t=NarrativeTimeline()
        t.put_chapter('c',RECALL+'\n'+CHALLENGE.replace('Noor','Kai'),recorded_at='2026-01-08T00:00:00Z')
        result=t.snapshot(story_through='2026-01-03',disclosed_through='2026-01-06',known_at='2026-01-08T00:00:00Z')
        row=next(r for r in result.payload['narrative_order_events'] if r['authority'].startswith('ATTRIBUTED'))
        self.assertEqual(row['challenge_status'],'NO_EXPLICIT_CHALLENGE_IN_VIEW')

    def test_budget_and_missing_chronology_remain_explicit(self):
        t=self.timeline()
        with self.assertRaisesRegex(ValueError,'budget'):
            t.snapshot(story_through='2026-01-08',disclosed_through='2026-01-08',known_at='2026-01-08T00:00:00Z',max_events=1)
        result=t.snapshot(story_through='2026-01-08',disclosed_through='2026-01-08',known_at='2026-01-08T00:00:00Z')
        with self.assertRaisesRegex(ValueError,'budget'):
            result.messages(t,'What was reported?',max_chars=1000)

    def test_same_names_across_chapters_do_not_create_recall_alias(self):
        t=NarrativeTimeline()
        t.put_chapter('recollection',RECALL,recorded_at='2026-01-08T00:00:00Z')
        t.put_chapter('other',CHALLENGE+'\n'+RECEIPT,recorded_at='2026-01-08T00:00:00Z')
        reader=t.snapshot(story_through='2026-01-03',disclosed_through='2026-01-07',known_at='2026-01-08T00:00:00Z')
        row=next(r for r in reader.payload['narrative_order_events'] if r['authority'].startswith('ATTRIBUTED'))
        self.assertEqual(row['challenge_status'],'NO_EXPLICIT_CHALLENGE_IN_VIEW')
        character=t.snapshot(story_through='2026-01-03',disclosed_through='2026-01-07',known_at='2026-01-08T00:00:00Z',character='Mira')
        self.assertEqual(character.payload['narrative_order_events'],[])

    def test_ambiguous_pronoun_recollection_cannot_anchor_receipt(self):
        t=NarrativeTimeline()
        t.put_chapter('c',RECALL.replace('of Mira saying','of she saying')+'\n'+RECEIPT,
            recorded_at='2026-01-08T00:00:00Z')
        view=t.snapshot(story_through='2026-01-03',disclosed_through='2026-01-07',known_at='2026-01-08T00:00:00Z',character='Mira')
        self.assertEqual(view.payload['narrative_order_events'],[])

    def test_conflicting_dates_not_promoted_to_story_order(self):
        t=NarrativeTimeline()
        text=RECALL.replace('from 2026-01-03','from 2026-01-07')
        t.put_chapter('c',text,recorded_at='2026-01-08T00:00:00Z')
        view=t.snapshot(story_through='2026-01-07',disclosed_through='2026-01-07',known_at='2026-01-08T00:00:00Z')
        self.assertEqual(len(view.payload['narrative_order_events']),1)
        self.assertEqual(view.payload['story_order_event_ids'],[])
        self.assertEqual(len(view.payload['unresolved_temporal_event_ids']),1)

    def test_hidden_chapter_does_not_enter_other_observer_view(self):
        t=NarrativeTimeline()
        t.put_chapter('shared',DIRECT,recorded_at='2026-01-03T00:00:00Z',permitted_observers=('Analyst',))
        first=t.snapshot(story_through='2026-01-05',disclosed_through='2026-01-05',known_at='2026-01-08T00:00:00Z',observer='Analyst')
        t.put_chapter('private',RECALL,recorded_at='2026-01-08T00:00:00Z',permitted_observers=('Kai',))
        second=t.snapshot(story_through='2026-01-05',disclosed_through='2026-01-05',known_at='2026-01-08T00:00:00Z',observer='Analyst')
        self.assertEqual(first.messages(t,'What was reported?'),second.messages(t,'What was reported?'))
        self.assertNotIn('private',second.messages(t,'What was reported?')[1]['content'])

    def test_f01_reference_recovers_exact_source_for_f02_view(self):
        from hcl.cognition.workspace import CognitionWorkspace
        from hcl.cognition.episodic import EpisodicIndex
        t=self.timeline();result=t.snapshot(story_through='2026-01-03',disclosed_through='2026-01-05',known_at='2026-01-08T00:00:00Z',observer='Analyst')
        w=CognitionWorkspace();w.put_source('chapter',t._chapters['chapter'][0]['text'],permitted_observers=('Analyst',))
        index=EpisodicIndex(w);index.refresh(observer='Analyst')
        for row in result.payload['narrative_order_events']:
            recovered=index.fetch(row['episodic_event_ref'],observer='Analyst')
            self.assertEqual(recovered['excerpt'],row['quote'])
            self.assertEqual(recovered['source_span_id'],row['source_span_id'])
