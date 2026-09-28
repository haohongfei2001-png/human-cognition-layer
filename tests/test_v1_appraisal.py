"""C04 goal-sensitive appraisal, mixed reports and explicit reappraisal."""
import unittest
from hcl.cognition import CognitionWorkspace, CommunicationScene
from hcl.cognition.appraisal import prepare_appraisal

G = 'Mira said, "I want to rest."'
H = 'Mira said, "I want to finish the report."'
P = 'Mira said, "The delay helps my goal to rest."'
N = 'Mira said, "The delay hinders my goal to finish the report."'
E = 'Mira said, "I feel relieved and worried about the delay."'
Q = 'How does Mira appraise the delay?'


class AppraisalTests(unittest.TestCase):
    def prepare(self, lines, query=Q):
        w = CognitionWorkspace()
        w.put_source('scene', '\n'.join(lines))
        r = prepare_appraisal(w, query, source_id='scene')
        return w, r, r.payload

    def test_positive_mixed_goal_congruence_keeps_reported_feelings_separate(self):
        w, r, row = self.prepare((G, H, P, N, E))
        self.assertEqual(row['appraisal']['goal_congruence'], 'MIXED_GOAL_CONGRUENCE')
        self.assertEqual(set(row['appraisal']['reported_emotions']), {'relieved', 'worried'})
        self.assertTrue(row['appraisal']['multiple_reported_feelings'])
        self.assertEqual(row['appraisal']['inferred_actual_emotion'], 'NOT_ESTABLISHED')
        self.assertIn('SOURCE_ORDER', str(r.messages(w)))

    def test_same_episode_different_goal_reports_change_appraisal_not_emotion_truth(self):
        lines = (G, P, 'Noor said, "I want to finish the report."',
            'Noor said, "The delay hinders my goal to finish the report."')
        _, _, mira = self.prepare(lines)
        _, _, noor = self.prepare(lines, 'How does Noor appraise the delay?')
        self.assertEqual(mira['appraisal']['goal_congruence'], 'SUPPORTS_EVIDENCED_GOALS')
        self.assertEqual(noor['appraisal']['goal_congruence'], 'HINDERS_EVIDENCED_GOALS')
        self.assertFalse(mira['appraisal']['reported_emotions'])
        self.assertFalse(noor['appraisal']['reported_emotions'])

    def test_explicit_reappraisal_supersedes_only_matching_prior_appraisal(self):
        revision = 'Mira said, "I now see the delay as harmful for my goal to rest."'
        _, _, row = self.prepare((G, H, P, N, E, revision))
        self.assertEqual(row['appraisal']['goal_congruence'], 'HINDERS_EVIDENCED_GOALS')
        self.assertEqual(len(row['retained_v08']['historical_evidence']), 1)
        old = row['retained_v08']['historical_evidence'][0]
        self.assertEqual(old['goal_key'], 'rest')
        self.assertEqual(old['value'], 'helps')
        self.assertEqual(set(row['appraisal']['reported_emotions']), {'relieved', 'worried'})

    def test_goal_abandonment_changes_conditional_relevance_not_reported_feeling(self):
        w, old, before = self.prepare((G, H, P, N, E))
        w.put_source('scene', '\n'.join((G, H, P, N, E, 'Mira said, "I abandoned my goal to finish the report."')))
        new = prepare_appraisal(w, Q, source_id='scene').payload
        self.assertEqual(new['appraisal']['goal_congruence'], 'SUPPORTS_EVIDENCED_GOALS')
        self.assertEqual(len(new['appraisal']['suspended_goal_links']), 1)
        self.assertEqual(new['appraisal']['reported_emotions'], before['appraisal']['reported_emotions'])
        self.assertFalse(new['retained_v08']['historical_evidence'])
        with self.assertRaises(ValueError):
            old.messages(w)

    def test_completed_goal_can_remain_relevant_without_inferred_emotion(self):
        _, _, row = self.prepare((G, P, 'Mira said, "I completed my goal to rest."'))
        self.assertEqual(row['appraisal']['goal_congruence'], 'SUPPORTS_EVIDENCED_GOALS')
        self.assertFalse(row['appraisal']['reported_emotions'])

    def test_expression_and_third_party_feeling_are_not_direct_emotion(self):
        _, _, row = self.prepare(('Narrator: Mira smiled during the delay.',
            'Noor said, "Mira seems worried about the delay."'))
        self.assertEqual(row['retained_v08']['emotion_status'], 'SYSTEM_INSUFFICIENT')
        self.assertFalse(row['appraisal']['reported_emotions'])
        self.assertEqual({e['strength'] for e in row['retained_v08']['current_evidence']}, {'INFERRED', 'ATTRIBUTED'})
        self.assertEqual(row['appraisal']['inferred_actual_emotion'], 'NOT_ESTABLISHED')

    def test_control_and_certainty_reports_do_not_establish_control_or_knowledge(self):
        _, _, row = self.prepare(('Mira said, "About the delay, I feel in control."',
            'Mira said, "About the delay, I am uncertain about the outcome."'))
        self.assertEqual({e['dimension'] for e in row['retained_v08']['current_evidence']}, {'CONTROL', 'CERTAINTY'})
        self.assertEqual(row['appraisal']['actual_control'], 'NOT_ESTABLISHED')
        self.assertEqual(row['appraisal']['actual_knowledge'], 'NOT_ESTABLISHED')

    def test_character_uncertainty_is_not_missing_feeling(self):
        _, _, row = self.prepare(('Mira said, "I am unsure how I feel about the delay."',))
        self.assertEqual(row['retained_v08']['emotion_status'], 'CHARACTER_UNCERTAIN')
        self.assertEqual(row['appraisal']['inferred_actual_emotion'], 'NOT_ESTABLISHED')

    def test_missing_or_future_goal_cannot_ground_appraisal(self):
        for lines in ((P,), (P, G)):
            _, _, row = self.prepare(lines)
            self.assertEqual(row['appraisal']['goal_congruence'], 'NO_CURRENT_GOAL_LINKED_APPRAISAL')
            self.assertIn('APPRAISAL_LACKS_PRIOR_SOURCE_GOAL', str(row['diagnostics']))

    def test_unanchored_reappraisal_does_not_fabricate_prior_state(self):
        _, _, row = self.prepare((G, 'Mira said, "I now see the delay as harmful for my goal to rest."'))
        self.assertFalse(row['retained_v08']['current_evidence'])
        self.assertIn('REAPPRAISAL_ANCHOR_MISSING_OR_AMBIGUOUS', str(row['diagnostics']))

    def test_same_goal_conflict_is_not_mixed_independent_goals(self):
        _, _, row = self.prepare((G, P, P.replace('helps', 'hinders')))
        self.assertEqual(row['appraisal']['goal_congruence'], 'GOAL_APPRAISAL_CONFLICT')

    def test_actor_access_episode_and_past_boundaries(self):
        source = '\n'.join((G, P, E, "Narrator: Noor missed Mira's last statement.",
            'Mira said, "I now see the delay as harmful for my goal to rest."'))
        early = CommunicationScene(source).view('Mira', through_line=2)
        w = early.workspace()
        result = prepare_appraisal(w, Q, source_id=early.source_id, observer='Mira').payload
        self.assertFalse(result['appraisal']['reported_emotions'])
        self.assertEqual(result['appraisal']['goal_congruence'], 'SUPPORTS_EVIDENCED_GOALS')
        hidden = prepare_appraisal(w, Q, source_id=early.source_id, observer='Noor').payload
        self.assertFalse(hidden['retained_v08']['current_evidence'])
        _, _, different = self.prepare((G, P, E), 'How does Mira appraise the arrival?')
        self.assertFalse(different['retained_v08']['current_evidence'])

    def test_hypothetical_and_ambiguous_source_does_not_create_feelings(self):
        for line in ('If ' + E, 'She said, "I feel relieved about the delay."',
                'Mira said, "I feel not relieved about the delay."'):
            _, _, row = self.prepare((line,))
            self.assertFalse(row['appraisal']['reported_emotions'])

    def test_resource_budget_and_source_support_fail_closed(self):
        w, result, _ = self.prepare((G, P, E))
        with self.assertRaises(ValueError):
            result.messages(w, max_chars=1000)
        w.core.withdraw(result.claim_ids[-1])
        with self.assertRaises(ValueError):
            result.messages(w)


if __name__ == '__main__':
    unittest.main()
