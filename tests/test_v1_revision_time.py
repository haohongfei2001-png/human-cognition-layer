"""B03 distinguishes source-record corrections from character self-revision."""
import json
import unittest
from hcl.cognition.revision_time import RevisionTimeline


def t(day):
    return f'2026-01-{day:02d}T12:00:00+00:00'


def state(snapshot, actor='Mira', proposition='the gate is open'):
    return next((r['status'] for r in snapshot.payload['estimates']
        if r['subject_agent_id'] == actor and r['proposition_key'] == proposition), None)


class RevisionTimeTests(unittest.TestCase):
    def base(self):
        scene = RevisionTimeline('story')
        scene.record('one', 'Mira said, "I believe the gate is open."', event_time=t(1), recorded_at=t(1),
            permitted_observers=('Mira',), access_time=t(1))
        scene.record('noor', 'Noor said, "I believe the road is safe."', event_time=t(1), recorded_at=t(1))
        return scene

    def test_character_revision_and_earlier_snapshot(self):
        scene = self.base()
        scene.record('two', 'Mira said, "I now believe the gate is closed instead of the gate is open."',
            event_time=t(2), recorded_at=t(2))
        old = scene.snapshot(event_time=t(1), known_at=t(3))
        new = scene.snapshot(event_time=t(2), known_at=t(3))
        self.assertEqual(state(old), 'AFFIRMED')
        self.assertEqual(state(new), 'SUPERSEDED')
        self.assertEqual(state(new, proposition='the gate is closed'), 'AFFIRMED')
        self.assertEqual(new.payload['transitions'][-1]['operation'], 'REPORTED_CHARACTER_REVISION')
        self.assertIn('CONDITIONAL_ON_ACCURATE_SINCERE_SELF_REPORT', str(new.messages('What changed?')))

    def test_late_source_correction_changes_estimate_not_character_history(self):
        scene = self.base()
        before = scene.snapshot(event_time=t(1), known_at=t(2))
        scene.record('one', 'Mira said, "I am unsure whether the gate is open."', event_time=t(1), recorded_at=t(3))
        after = scene.snapshot(event_time=t(1), known_at=t(3))
        self.assertEqual(state(before), 'AFFIRMED')
        self.assertEqual(state(after), 'CHARACTER_UNCERTAIN')
        self.assertEqual(scene.snapshot(event_time=t(1), known_at=t(2)), before)
        self.assertTrue(after.payload['source_corrections'])
        self.assertNotIn('REPORTED_CHARACTER_REVISION', str(after.payload))
        self.assertEqual([r for r in before.payload['estimates'] if r['subject_agent_id'] == 'Noor'],
                         [r for r in after.payload['estimates'] if r['subject_agent_id'] == 'Noor'])

    def test_newly_disclosed_old_event_is_not_known_early(self):
        scene = RevisionTimeline('late')
        scene.record('one', 'Mira said, "I believe the gate is open."', event_time=t(1), recorded_at=t(3))
        self.assertIsNone(state(scene.snapshot(event_time=t(1), known_at=t(2))))
        self.assertEqual(state(scene.snapshot(event_time=t(1), known_at=t(3))), 'AFFIRMED')

    def test_missing_hidden_or_other_actor_anchor_cannot_create_old_state(self):
        scene = self.base()
        scene.record('two', 'Kai said, "I now believe the gate is closed instead of the gate is open."',
            event_time=t(2), recorded_at=t(2), permitted_observers=('Kai',), access_time=t(2))
        snap = scene.snapshot(event_time=t(3), known_at=t(3), observer='Kai')
        self.assertIsNone(state(snap, actor='Kai'))
        self.assertEqual(state(snap, actor='Kai', proposition='the gate is closed'), 'AFFIRMED')
        self.assertNotIn('Mira', str(snap.payload))
        self.assertIn('WITHOUT_SUPPORTED_OLD_ANCHOR', str(snap.payload))

    def test_uncertain_corrected_anchor_does_not_support_supersession(self):
        scene = self.base()
        scene.record('two', 'Mira said, "I now believe the gate is closed instead of the gate is open."',
            event_time=t(2), recorded_at=t(2))
        scene.record('one', 'Mira said, "I am unsure whether the gate is open."', event_time=t(1), recorded_at=t(3))
        snap = scene.snapshot(event_time=t(2), known_at=t(3))
        self.assertEqual(state(snap), 'CHARACTER_UNCERTAIN')
        self.assertNotIn('REPORTED_CHARACTER_REVISION', str(snap.payload))

    def test_challenge_is_not_acceptance_and_explicit_response_updates(self):
        scene = self.base()
        scene.record('two', 'Mira said, "I have received a challenge to my belief that the gate is open."',
            event_time=t(2), recorded_at=t(2))
        challenge = scene.snapshot(event_time=t(2), known_at=t(2))
        row = next(r for r in challenge.payload['estimates'] if r['subject_agent_id'] == 'Mira')
        self.assertTrue(row['unresolved_challenge_evidence_ids'])
        self.assertNotEqual(row['status'], 'DENIED')
        scene.record('three', 'Mira said, "I reject that the gate is open."', event_time=t(3), recorded_at=t(3))
        self.assertEqual(state(scene.snapshot(event_time=t(3), known_at=t(3))), 'DENIED')
        scene.record('four', 'Mira said, "I accept that the gate is open."', event_time=t(4), recorded_at=t(4))
        self.assertEqual(state(scene.snapshot(event_time=t(4), known_at=t(4))), 'AFFIRMED')

    def test_later_access_cannot_enter_early_view(self):
        scene = RevisionTimeline('access')
        scene.record('one', 'Mira said, "I believe the gate is open."', event_time=t(1), recorded_at=t(1),
            permitted_observers=('Noor',), access_time=t(3))
        self.assertIsNone(state(scene.snapshot(event_time=t(2), known_at=t(4), observer='Noor')))
        self.assertEqual(state(scene.snapshot(event_time=t(3), known_at=t(4), observer='Noor')), 'AFFIRMED')
        self.assertIsNone(state(scene.snapshot(event_time=t(4), known_at=t(4), observer='Kai')))

    def test_unknown_event_time_not_fabricated(self):
        scene = RevisionTimeline('unknown')
        scene.record('one', 'Mira said, "I believe the gate is open."', event_time=None, recorded_at=t(1))
        snap = scene.snapshot(event_time=t(3), known_at=t(3))
        self.assertIsNone(state(snap))
        self.assertIn('UNKNOWN_EVENT_TIME', str(snap.payload))
        self.assertEqual(snap.payload['records'][0]['event_time'], None)

    def test_correction_moved_outside_snapshot_does_not_resurrect_old_version(self):
        scene = self.base()
        scene.record('one', 'Mira said, "I believe the gate is open."', event_time=t(4), recorded_at=t(3))
        self.assertIsNone(state(scene.snapshot(event_time=t(2), known_at=t(3))))
        self.assertEqual(state(scene.snapshot(event_time=t(2), known_at=t(2))), 'AFFIRMED')

    def test_no_exposure_knowledge_action_or_third_party_promotion(self):
        for source in ('Mira said, "I heard the gate is open."',
                'Mira said, "I know the gate is open."',
                'Mira said, "Noor believes the gate is open."',
                'If Mira said, "I believe the gate is open."',
                'She said, "I believe the gate is open."', 'Mira opened the gate.'):
            scene = RevisionTimeline('negative')
            scene.record('one', source, event_time=t(1), recorded_at=t(1))
            self.assertFalse(scene.snapshot(event_time=t(2), known_at=t(2)).payload['estimates'])

    def test_equal_event_time_does_not_anchor_character_revision(self):
        scene = self.base()
        scene.record('two', 'Mira said, "I now believe the gate is closed instead of the gate is open."',
            event_time=t(1), recorded_at=t(2))
        self.assertNotIn('REPORTED_CHARACTER_REVISION', str(scene.snapshot(event_time=t(3), known_at=t(3)).payload))

    def test_disclosure_order_cannot_order_simultaneous_character_expressions(self):
        scene = self.base()
        scene.record('two', 'Mira said, "I do not believe the gate is open."',
            event_time=t(1), recorded_at=t(3))
        snap = scene.snapshot(event_time=t(1), known_at=t(3))
        self.assertEqual(state(snap), 'CONFLICT')
        self.assertEqual(state(scene.snapshot(event_time=t(1), known_at=t(2))), 'AFFIRMED')

    def test_limits_and_invalid_time_do_not_mutate(self):
        scene = self.base()
        before = scene.snapshot(event_time=t(3), known_at=t(3))
        with self.assertRaises(ValueError):
            scene.record('one', 'bad', event_time=t(1), recorded_at=t(1))
        with self.assertRaises(ValueError):
            scene.record('bad', 'bad', event_time='yesterday', recorded_at=t(3))
        self.assertEqual(before, scene.snapshot(event_time=t(3), known_at=t(3)))
        with self.assertRaises(ValueError):
            before.messages('What changed?', max_chars=1000)

    def test_independent_source_domains_and_actual_final_input(self):
        left, right = self.base(), RevisionTimeline('different-story')
        right.record('two', 'Mira said, "I now believe the gate is closed instead of the gate is open."',
            event_time=t(2), recorded_at=t(2))
        self.assertNotIn('REPORTED_CHARACTER_REVISION', str(right.snapshot(event_time=t(3), known_at=t(3)).payload))
        snap = left.snapshot(event_time=t(3), known_at=t(3))
        self.assertEqual(json.loads(snap.messages('What changed?')[-1]['content'])['cognition'], snap.payload)


if __name__ == '__main__':
    unittest.main()
