"""C02 conditional alternatives, mixed goals and source/time boundaries."""
import unittest
from hcl.cognition import CognitionWorkspace, CommunicationScene
from hcl.cognition.action_explanations import prepare_explanations

K = 'Mira said, "At the time, I knew about the meeting."'
O = 'Mira said, "At the time, I could skip the meeting."'
A = 'Mira said, "I skipped the meeting."'
Q = 'Why did Mira skip the meeting?'


class ActionExplanationTests(unittest.TestCase):
    def prepare(self, lines):
        w = CognitionWorkspace()
        w.put_source('scene', '\n'.join(lines))
        r = prepare_explanations(w, Q, source_id='scene')
        return w, r, r.payload

    def test_positive_ignorance_update_weakens_choice_without_proving_another_motive(self):
        w, old, before = self.prepare((K, O, A))
        self.assertEqual(before['explanations'][0]['disposition'], 'CONDITIONALLY_SUPPORTED')
        w.put_source('scene', '\n'.join((K.replace('I knew', 'I did not know'), O, A)))
        new = prepare_explanations(w, Q, source_id='scene')
        self.assertEqual(new.payload['explanations'][0]['disposition'], 'WEAKENED_BY_COUNTEREVIDENCE')
        self.assertEqual(new.payload['explanations'][1]['disposition'], 'CONDITIONALLY_SUPPORTED')
        self.assertTrue(all(row['actual_motive'] == 'NOT_ESTABLISHED' for row in new.payload['explanations']))
        self.assertEqual(new.payload['winning_motive'], 'NOT_INFERRED')
        with self.assertRaises(ValueError):
            old.messages(w)

    def test_mixed_source_goals_remain_two_conditional_candidates(self):
        goals = ('Mira said, "I want to avoid the noise."',
            'Mira said, "I plan to skip the meeting in order to avoid the noise."',
            'Mira said, "I want to finish the report."',
            'Mira said, "I plan to skip the meeting in order to finish the report."')
        _, _, result = self.prepare((*goals, K, O, A))
        supported = [r for r in result['explanations'] if r['disposition'] == 'CONDITIONALLY_SUPPORTED']
        self.assertEqual(len(supported), 2)
        self.assertTrue(all(r['hypothesis'].startswith('goal-directed') for r in supported))
        self.assertTrue(all(r['exclusive'] == 'NOT_ASSUMED' for r in supported))
        by_id = {e['event_id']: e['raw_text'] for e in result['source_events']}
        for fact in result['conditions']:
            if fact['condition']['kind'] == 'GOAL':
                self.assertIn(fact['condition']['key'], by_id[fact['source_event_id']])

    def test_goal_after_action_cannot_become_action_time_motive_support(self):
        _, _, row = self.prepare((K, O, A, 'Mira said, "I want to avoid the noise."',
            'Mira said, "I plan to skip the meeting in order to avoid the noise."'))
        self.assertFalse(any(r['hypothesis'].startswith('goal-directed') for r in row['explanations']))
        self.assertFalse(any(f['condition']['kind'] == 'GOAL' for f in row['conditions']))

    def test_current_or_later_knowledge_without_action_time_reference_is_not_backfilled(self):
        _, _, row = self.prepare((O, A, 'Mira said, "I now know about the meeting."'))
        self.assertEqual(row['explanations'][0]['disposition'], 'UNRESOLVED')
        self.assertEqual(row['explanations'][1]['disposition'], 'UNRESOLVED')
        self.assertFalse(any(f['condition']['kind'] == 'KNOWLEDGE' for f in row['conditions']))

    def test_explicit_retrospective_action_time_claim_can_revise_reader_estimate(self):
        _, _, row = self.prepare((O, A, K.replace('I knew', 'I did not know')))
        self.assertEqual(row['explanations'][0]['disposition'], 'WEAKENED_BY_COUNTEREVIDENCE')
        self.assertIn('CONDITIONAL_NOT_VERIFIED_CHRONOLOGY', str(row))

    def test_missing_evidence_is_not_negative_evidence(self):
        _, _, row = self.prepare((A,))
        self.assertTrue(all(r['disposition'] == 'UNRESOLVED' for r in row['explanations']))
        self.assertFalse(row['conditions'])

    def test_conflicting_claims_do_not_silently_pick_narrator_or_majority(self):
        _, _, row = self.prepare((K, 'Narrator: At the time, Mira did not know about the meeting.', O, A))
        self.assertEqual(row['explanations'][0]['disposition'], 'CONFLICTING_PREMISES')
        self.assertEqual(row['explanations'][1]['disposition'], 'CONFLICTING_PREMISES')
        self.assertNotEqual(row['winning_motive'], 'lack of awareness')

    def test_other_actor_and_third_party_knowledge_do_not_become_target_knowledge(self):
        _, _, row = self.prepare((K.replace('Mira', 'Noor'), O, A,
            'Noor said, "At the time, Mira knew about the meeting."'))
        self.assertEqual(row['explanations'][0]['disposition'], 'UNRESOLVED')
        self.assertFalse(any(f['condition']['kind'] == 'KNOWLEDGE' for f in row['conditions']))

    def test_actor_view_and_prior_snapshot_exclude_later_reception(self):
        source = '\n'.join((A, "Narrator: Noor heard Mira's last statement.", K,
            "Narrator: Noor missed Mira's last statement.", O, "Narrator: Noor heard Mira's last statement."))
        view = CommunicationScene(source).view('Noor')
        w = view.workspace()
        row = prepare_explanations(w, Q, source_id=view.source_id, observer='Noor').payload
        self.assertEqual(row['explanations'][0]['disposition'], 'UNRESOLVED')
        self.assertNotIn('I knew', str(row))
        hidden = prepare_explanations(w, Q, source_id=view.source_id, observer='Kai').payload
        self.assertEqual(hidden['reason'], 'no_unambiguous_visible_action')
        self.assertNotIn('I skipped', str(hidden))

    def test_hypothetical_negated_and_ambiguous_actions_not_recorded_as_occurrence(self):
        for action in ('If ' + A, 'Mira said, "I did not skip the meeting."',
                'She said, "I skipped the meeting."'):
            _, _, row = self.prepare((K, O, action))
            self.assertEqual(row['reason'], 'no_unambiguous_visible_action')
            self.assertFalse(row['explanations'])

    def test_inaction_does_not_turn_inability_into_a_deliberate_option(self):
        w = CognitionWorkspace()
        text = '\n'.join((K, 'Mira said, "At the time, I could not attend the meeting."',
            'Mira said, "I did not attend the meeting."'))
        w.put_source('s', text)
        query = 'Why did Mira not attend the meeting?'
        row = prepare_explanations(w, query, source_id='s').payload
        self.assertFalse(any(f['condition']['kind'] == 'OPPORTUNITY' for f in row['conditions']))
        self.assertEqual(row['explanations'][0]['disposition'], 'UNRESOLVED')
        w.put_source('s', text.replace('I could not attend', 'I could choose to not attend'))
        row = prepare_explanations(w, query, source_id='s').payload
        self.assertEqual(row['explanations'][0]['disposition'], 'CONDITIONALLY_SUPPORTED')
        self.assertEqual(row['explanations'][0]['actual_motive'], 'NOT_ESTABLISHED')

    def test_no_opportunity_counterevidence_keeps_goal_candidate_conditional(self):
        _, _, row = self.prepare((K, O.replace('I could', 'I could not'), A))
        self.assertEqual(row['explanations'][0]['disposition'], 'WEAKENED_BY_COUNTEREVIDENCE')
        self.assertEqual(row['explanations'][2]['disposition'], 'CONDITIONALLY_SUPPORTED')
        self.assertEqual(row['explanations'][2]['actual_motive'], 'NOT_ESTABLISHED')

    def test_ambiguous_action_budget_and_stale_support_fail_closed(self):
        with self.assertRaises(ValueError):
            self.prepare((A, A))
        w, result, row = self.prepare((K, O, A))
        with self.assertRaises(ValueError):
            result.messages(w, max_chars=1000)
        claim = row['explanations'][0]['claim_id']
        w.core.withdraw(claim)
        with self.assertRaises(ValueError):
            result.messages(w)


if __name__ == '__main__':
    unittest.main()
