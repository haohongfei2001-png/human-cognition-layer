"""C01 real source-dependent pursuit joins, without outcome-to-intention inference."""
import unittest
from hcl.cognition import CognitionWorkspace, CommunicationScene
from hcl.cognition.agency import prepare_agency

G = 'Mira said, "I want to reach shelter."'
P = 'Mira said, "I plan to cross the bridge in order to reach shelter."'
O = 'Mira said, "I have an opportunity to cross the bridge."'


class AgencyTests(unittest.TestCase):
    def prepare(self, lines, actor='Mira'):
        w = CognitionWorkspace()
        w.put_source('story', '\n'.join(lines))
        r = prepare_agency(w, f"What are {actor}'s goals and plans?", source_id='story')
        return w, r, r.payload

    def test_goal_is_not_a_selected_plan_and_consideration_is_not_selection(self):
        _, _, goal = self.prepare((G,))
        self.assertEqual(goal['goals'][0]['status'], 'ACTIVE')
        self.assertFalse(goal['plans'])
        _, _, considered = self.prepare((G, P.replace('plan to', 'am considering a plan to'), O))
        self.assertEqual(considered['plans'][0]['pursuit_check'], 'NO_SELECTED_PLAN')
        self.assertFalse(considered['intentions'])

    def test_selection_and_opportunity_create_supported_pursuit_join(self):
        w, r, p = self.prepare((G, P.replace('plan to', 'am considering a plan to'), P, O))
        plan = p['plans'][0]
        self.assertEqual(plan['selection'], 'REPORTED_SELECTED')
        self.assertEqual(plan['pursuit_check'], 'SOURCE_SUPPORTED_PURSUIT_NOT_WORLD_FEASIBILITY')
        self.assertEqual(plan['success'], 'NOT_ESTABLISHED')
        self.assertGreater(len(next(iter(w.core.dependencies[plan['claim_id']]))), 2)
        self.assertIn('cross the bridge', str(r.messages(w)))

    def test_goal_abandonment_updates_dependent_plan_without_automatic_plan_revocation(self):
        w, old, _ = self.prepare((G, P, O))
        w.put_source('story', '\n'.join((G, P, O, 'Mira said, "I abandoned my goal to reach shelter."')))
        with self.assertRaises(ValueError):
            old.messages(w)
        new = prepare_agency(w, "What are Mira's goals and plans?", source_id='story').payload
        self.assertEqual(new['goals'][0]['status'], 'ABANDONED')
        self.assertEqual(new['plans'][0]['selection'], 'REPORTED_SELECTED')
        self.assertEqual(new['plans'][0]['pursuit_check'], 'GOAL_NOT_REPORTED_ACTIVE')

    def test_outcome_or_action_does_not_complete_goal_or_establish_intended_causation(self):
        _, _, action = self.prepare((G, 'Mira said, "I reached shelter."'))
        self.assertEqual(action['goals'][0]['status'], 'ACTIVE')
        self.assertEqual(action['goals'][0]['intended_causation'], 'NOT_ESTABLISHED')
        _, _, done = self.prepare((G, 'Mira said, "I completed my goal to reach shelter."'))
        self.assertEqual(done['goals'][0]['status'], 'COMPLETED')
        self.assertEqual(done['goals'][0]['intended_causation'], 'NOT_ESTABLISHED')
        _, _, alone = self.prepare(('Mira said, "I reached shelter."',))
        self.assertFalse(alone['goals'])
        self.assertFalse(alone['intentions'])

    def test_subgoal_completion_does_not_complete_parent(self):
        _, _, row = self.prepare((G, 'Mira said, "To reach shelter, my subgoal is to find the path."',
            'Mira said, "I completed my goal to find the path."'))
        states = {g['goal']: g['status'] for g in row['goals']}
        self.assertEqual(states, {'find the path': 'COMPLETED', 'reach shelter': 'ACTIVE'})
        self.assertEqual(row['subgoal_relations'][0]['parent_goal'], 'reach shelter')

    def test_conditions_opportunity_and_selection_remain_separate(self):
        _, _, row = self.prepare((G, P.replace('shelter.', 'shelter if the gate is open.'), O))
        self.assertEqual(row['plans'][0]['pursuit_check'], 'CONDITION_REQUIRES_CHECK')
        _, _, blocked = self.prepare((G, P, O.replace('an opportunity', 'no opportunity')))
        self.assertEqual(blocked['plans'][0]['pursuit_check'], 'OPPORTUNITY_CONTRADICTED')
        self.assertEqual(blocked['goals'][0]['status'], 'ACTIVE')
        _, _, missing = self.prepare((G, P))
        self.assertEqual(missing['plans'][0]['pursuit_check'], 'OPPORTUNITY_UNRESOLVED')

    def test_opportunity_conflict_and_goal_uncertainty_do_not_become_permission(self):
        _, _, conflict = self.prepare((G, P, O, O.replace('an opportunity', 'no opportunity')))
        self.assertEqual(conflict['plans'][0]['opportunity'], 'CONFLICTING_CLAIMS')
        _, _, uncertain = self.prepare((G, P, O, 'Mira said, "I am unsure whether to reach shelter."'))
        self.assertEqual(uncertain['goals'][0]['status'], 'CHARACTER_UNCERTAIN')
        self.assertEqual(uncertain['plans'][0]['pursuit_check'], 'GOAL_NOT_REPORTED_ACTIVE')

    def test_plan_lifecycle_does_not_change_goal_or_guess_ambiguous_reference(self):
        _, _, row = self.prepare((G, P, O, 'Mira said, "I abandoned the plan to cross the bridge."'))
        self.assertEqual(row['plans'][0]['selection'], 'REPORTED_ABANDONED')
        self.assertEqual(row['goals'][0]['status'], 'ACTIVE')
        _, _, ambiguous = self.prepare((G, P, P.replace('reach shelter', 'find food'),
            'Mira said, "I abandoned the plan to cross the bridge."'))
        self.assertTrue(all(p['selection'] == 'REPORTED_SELECTED' for p in ambiguous['plans']))
        self.assertIn('PLAN_LIFECYCLE_REFERENCE_MISSING_OR_AMBIGUOUS', str(ambiguous['diagnostics']))

    def test_actor_access_and_source_boundaries_preserved(self):
        view = CommunicationScene(G + "\nNarrator: Noor missed Mira's last statement.\n" +
            'Noor said, "I want to find food."').view('Noor')
        w = view.workspace()
        result = prepare_agency(w, "What are Mira's goals and plans?", source_id=view.source_id, observer='Noor')
        self.assertFalse(result.payload['goals'])
        self.assertNotIn('reach shelter', str(result.messages(w)))
        noor = prepare_agency(w, "What are Noor's goals and plans?", source_id=view.source_id, observer='Noor')
        self.assertEqual(noor.payload['goals'][0]['goal'], 'find food')

    def test_earlier_source_snapshot_cannot_use_later_abandonment(self):
        text = '\n'.join((G, P, O, 'Mira said, "I abandoned my goal to reach shelter."'))
        view = CommunicationScene(text).view('Mira', through_line=3)
        w = view.workspace()
        result = prepare_agency(w, "What are Mira's goals and plans?", source_id=view.source_id, observer='Mira')
        self.assertEqual(result.payload['goals'][0]['status'], 'ACTIVE')
        self.assertNotIn('abandoned', str(result.messages(w)))

    def test_hypothetical_third_party_and_ambiguous_speech_do_not_create_direct_goals(self):
        for text in ('If ' + G, 'Noor said, "Mira wants to reach shelter."',
                'She said, "I want to reach shelter."', 'Mira said, "I want to reach shelter if it rains."'):
            _, _, row = self.prepare((text,))
            self.assertFalse(row['goals'])

    def test_explicit_intention_does_not_establish_result_and_budget_fails_closed(self):
        w, result, row = self.prepare(('Mira said, "I intend to open the gate."',))
        self.assertEqual(row['intentions'][0]['action'], 'open the gate')
        self.assertEqual(row['intentions'][0]['causation'], 'NOT_ESTABLISHED')
        self.assertFalse(row['goals'])
        with self.assertRaises(ValueError):
            result.messages(w, max_chars=1000)
        with self.assertRaises(ValueError):
            prepare_agency(w, 'Guess her motives.', source_id='story')


if __name__ == '__main__':
    unittest.main()
