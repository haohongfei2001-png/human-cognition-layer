"""C03 belief/model separation and plan revision without value attribution."""
import unittest
from hcl.cognition import CognitionWorkspace, CommunicationScene
from hcl.cognition.plan_feasibility import prepare_plan_feasibility

G = 'Mira said, "I want to reach shelter."'
P = 'Mira said, "I plan to cross the bridge in order to reach shelter if the gate is open."'
O = 'Mira said, "I have an opportunity to cross the bridge."'
B = 'Mira said, "I believe the gate is open."'
M = 'Narrator: In the declared model, it is false that the gate is open.'
Q = "Could Mira's plans work under their beliefs and the declared model?"


class PlanFeasibilityTests(unittest.TestCase):
    def prepare(self, lines):
        w = CognitionWorkspace()
        w.put_source('story', '\n'.join(lines))
        r = prepare_plan_feasibility(w, Q, source_id='story')
        return w, r, r.payload

    def test_false_belief_can_support_plan_subjectively_without_knowing_model_failure(self):
        w, result, row = self.prepare((G, P, O, B, M))
        plan = row['plans'][0]
        self.assertEqual(plan['subjective_feasibility'], 'SUPPORTED_UNDER_REPORTED_BELIEFS')
        self.assertEqual(plan['model_condition_check'], 'MODEL_CONDITION_CONTRADICTED')
        self.assertEqual(plan['relation'], 'BELIEF_MODEL_DIVERGENCE_NOT_KNOWING_INFEASIBILITY')
        self.assertEqual(plan['deliberate_impossibility'], 'NOT_INFERRED')
        self.assertGreaterEqual(len(next(iter(w.core.dependencies[plan['claim_id']]))), 3)
        self.assertIn('SOURCE_ORDER', str(result.payload))

    def test_explicit_belief_revision_changes_dependent_plan_condition(self):
        w, old, _ = self.prepare((G, P, O, B, M))
        revision = 'Mira said, "I now believe it is false that the gate is open instead of the gate is open."'
        w.put_source('story', '\n'.join((G, P, O, B, M, revision)))
        result = prepare_plan_feasibility(w, Q, source_id='story')
        self.assertEqual(result.payload['plans'][0]['subjective_feasibility'], 'CONTRADICTED_UNDER_REPORTED_BELIEFS')
        self.assertEqual(result.payload['plans'][0]['model_condition_check'], 'MODEL_CONDITION_CONTRADICTED')
        with self.assertRaises(ValueError):
            old.messages(w)

    def test_not_believing_condition_is_not_believing_negation(self):
        _, _, denied = self.prepare((G, P, O, B.replace('I believe', 'I do not believe'), M))
        self.assertEqual(denied['plans'][0]['subjective_condition'], 'NOT_AFFIRMED_NOT_NEGATION')
        self.assertEqual(denied['plans'][0]['subjective_feasibility'], 'BELIEF_CONDITION_UNRESOLVED')
        _, _, negative = self.prepare((G, P, O, B.replace('I believe ', 'I believe it is false that '), M))
        self.assertEqual(negative['plans'][0]['subjective_condition'], 'AFFIRMED_OPPOSITE_CONDITION')

    def test_plan_revision_preserves_goal_without_inventing_value_change(self):
        replacement = ('Mira said, "I abandoned the plan to cross the bridge."',
            'Mira said, "I plan to take the trail in order to reach shelter if the trail is clear."',
            'Mira said, "I have an opportunity to take the trail."',
            'Mira said, "I believe the trail is clear."',
            'Narrator: In the declared model, it is true that the trail is clear.')
        _, _, row = self.prepare((G, P, O, B, M, *replacement))
        plans = {p['action']: p for p in row['plans']}
        self.assertEqual(plans['cross the bridge']['subjective_feasibility'], 'NOT_CURRENTLY_PURSUED')
        self.assertEqual(plans['take the trail']['subjective_feasibility'], 'SUPPORTED_UNDER_REPORTED_BELIEFS')
        self.assertTrue(all(p['goal_status'] == 'ACTIVE' for p in plans.values()))
        self.assertTrue(all(p['values_change'] == 'NOT_INFERRED' for p in plans.values()))

    def test_source_model_never_fills_missing_character_belief(self):
        _, _, row = self.prepare((G, P, O, M.replace('false', 'true')))
        self.assertEqual(row['plans'][0]['declared_model_condition'], 'DECLARED_CONDITION_MET')
        self.assertEqual(row['plans'][0]['subjective_condition'], 'UNKNOWN')
        self.assertEqual(row['plans'][0]['subjective_feasibility'], 'BELIEF_CONDITION_UNRESOLVED')

    def test_other_person_or_knowledge_claim_cannot_supply_target_belief(self):
        for belief in (B.replace('Mira', 'Noor'), B.replace('I believe', 'I know'),
                'Noor said, "Mira believes the gate is open."'):
            _, _, row = self.prepare((G, P, O, belief, M))
            self.assertEqual(row['plans'][0]['subjective_condition'], 'UNKNOWN')

    def test_conflicting_model_and_belief_reports_remain_unresolved(self):
        _, _, row = self.prepare((G, P, O, B, B.replace('I believe ', 'I believe it is false that '),
            M, M.replace('false', 'true')))
        self.assertEqual(row['plans'][0]['subjective_condition'], 'CONFLICT')
        self.assertEqual(row['plans'][0]['declared_model_condition'], 'CONFLICT')
        self.assertEqual(row['plans'][0]['subjective_feasibility'], 'BELIEF_CONDITION_UNRESOLVED')

    def test_character_uncertainty_and_missing_opportunity_are_not_feasible(self):
        _, _, uncertain = self.prepare((G, P, O, B.replace('I believe', 'I am unsure whether'), M))
        self.assertEqual(uncertain['plans'][0]['subjective_condition'], 'UNRESOLVED')
        _, _, unavailable = self.prepare((G, P, B, M))
        self.assertEqual(unavailable['plans'][0]['subjective_feasibility'], 'OPPORTUNITY_UNRESOLVED')

    def test_actor_view_and_earlier_snapshot_do_not_import_unseen_model_or_revision(self):
        source = '\n'.join((G, P, O, B, M,
            'Mira said, "I now believe it is false that the gate is open instead of the gate is open."'))
        view = CommunicationScene(source).view('Mira', through_line=4)
        w = view.workspace()
        r = prepare_plan_feasibility(w, Q, source_id=view.source_id, observer='Mira')
        self.assertEqual(r.payload['plans'][0]['subjective_condition'], 'AFFIRMED_REQUIRED_CONDITION')
        self.assertEqual(r.payload['plans'][0]['declared_model_condition'], 'UNKNOWN')
        self.assertNotIn('In the declared model', str(r.messages(w)))

    def test_exposure_and_hypothetical_sources_do_not_become_belief(self):
        for belief in (B.replace('I believe', 'I heard'), 'If ' + B):
            _, _, row = self.prepare((G, P, O, belief, M))
            self.assertEqual(row['plans'][0]['subjective_condition'], 'UNKNOWN')

    def test_budget_and_stale_support_rejected_before_final_input(self):
        w, r, row = self.prepare((G, P, O, B, M))
        with self.assertRaises(ValueError):
            r.messages(w, max_chars=1000)
        w.core.withdraw(row['plans'][0]['claim_id'])
        with self.assertRaises(ValueError):
            r.messages(w)


if __name__ == '__main__':
    unittest.main()
