import json
import unittest
from hcl.cognition.agency_chain import SemanticWorkspace
from hcl.cognition.joint_plan import prepare_joint_plan

SOURCE = '\n'.join(('Mira said, "I want to publish the report."',
    'Mira said, "I plan to draft the report in order to publish the report."',
    'Mira said, "I have an opportunity to draft the report."',
    'Noor said, "I want to publish the report."',
    'Noor said, "I plan to publish the report in order to publish the report."',
    'Noor said, "I have an opportunity to publish the report."',
    'Kai said, "I want to publish the report."',
    'Kai said, "I plan to review the report in order to publish the report."',
    'Kai said, "I have an opportunity to review the report."',
    'Mira said, "In team, I propose the joint plan to publish the report."',
    "Narrator: Noor and Kai heard Mira's last statement.",
    'Noor said, "I accept Mira\'s joint plan in team to publish the report."',
    "Narrator: Mira and Kai heard Noor's last statement.",
    'Kai said, "I accept Mira\'s joint plan in team to publish the report."',
    "Narrator: Mira and Noor heard Kai's last statement.",
    'Narrator: In team, only editor may authorize the plan to publish the report.',
    'Narrator: In team, Mira is editor.',
    'Mira said, "In team, I authorize Noor to publish the report."',
    "Narrator: Noor heard Mira's last statement."))
QUERY = 'Can Mira, Noor and Kai carry out the joint plan to publish the report in team?'


class JointPlanTests(unittest.TestCase):
    def prepare(self, source=SOURCE, observer=None):
        w = SemanticWorkspace()
        w.put_source('scene', source)
        return w, prepare_joint_plan(w, QUERY, source_id='scene', observer=observer)

    def test_positive_joint_plan_authority_and_views(self):
        w, result = self.prepare()
        self.assertEqual(result.payload['status'], 'COORDINATION_PREMISES_SUPPORTED')
        self.assertEqual(result.payload['source_authorized_and_informed_executors'], ['Noor'])
        self.assertEqual(len(result.payload['participants']), 3)
        self.assertEqual(result.payload['group_private_state'], 'NOT_CREATED')
        self.assertEqual(result.payload['world_feasibility'], 'NOT_ESTABLISHED')
        self.assertIn('peer_endorsement_receipts', result.messages(w)[1]['content'])

    def test_missing_one_person_receipt_not_group_access(self):
        _, result = self.prepare(SOURCE.replace("Narrator: Noor and Kai heard Mira's last statement.", "Narrator: Noor heard Mira's last statement."))
        self.assertEqual(result.payload['status'], 'PARTICIPANT_PLAN_OR_ENDORSEMENT_UNRESOLVED')
        actors = {p['actor']: p for p in result.payload['participants']}
        self.assertTrue(actors['Noor']['proposal_receipt_at_endorsement']['received'])
        self.assertFalse(actors['Kai']['proposal_receipt_at_endorsement']['received'])

    def test_peer_acceptance_receipt_required(self):
        _, result = self.prepare(SOURCE.replace("Narrator: Mira and Noor heard Kai's last statement.", "Narrator: Mira heard Kai's last statement."))
        self.assertEqual(result.payload['status'], 'PEER_COORDINATION_RECEIPTS_INCOMPLETE')

    def test_missing_and_late_role_not_grant_authority(self):
        role = 'Narrator: In team, Mira is editor.'
        _, result = self.prepare(SOURCE.replace(role + '\n', '') + '\n' + role)
        self.assertEqual(result.payload['status'], 'FINAL_ACTION_AUTHORIZATION_UNRESOLVED')
        self.assertEqual(result.payload['grants'][0]['status'], 'ROLE_UNRESOLVED')

    def test_role_wrong_context_not_authority(self):
        _, result = self.prepare(SOURCE.replace('In team, Mira is editor', 'In club, Mira is editor'))
        self.assertEqual(result.payload['grants'][0]['status'], 'ROLE_UNRESOLVED')

    def test_third_party_report_not_authorization(self):
        _, result = self.prepare(SOURCE.replace('Mira said, "In team, I authorize Noor to publish the report."', 'Kai said, "Mira authorized Noor to publish the report in team."'))
        self.assertEqual(result.payload['grants'], [])
        self.assertEqual(result.payload['status'], 'FINAL_ACTION_AUTHORIZATION_UNRESOLVED')

    def test_grant_not_received_prevents_coordination(self):
        _, result = self.prepare('\n'.join(SOURCE.splitlines()[:-1]))
        self.assertEqual(result.payload['grants'][0]['status'], 'AUTHORIZED_UNDER_SOURCE_RULE')
        self.assertEqual(result.payload['status'], 'FINAL_ACTION_AUTHORIZATION_UNRESOLVED')

    def test_revocation_changes_permission_not_goals(self):
        _, result = self.prepare(SOURCE + '\nMira said, "I revoke my authorization for Noor to publish the report in team."')
        self.assertEqual(result.payload['grants'][0]['status'], 'REPORTED_REVOKED')
        self.assertEqual(result.payload['status'], 'FINAL_ACTION_AUTHORIZATION_UNRESOLVED')
        self.assertTrue(all(p['individually_supported'] for p in result.payload['participants']))

    def test_all_planned_executors_require_their_own_grant(self):
        source = SOURCE.replace('I plan to review the report', 'I plan to publish the report').replace('I have an opportunity to review the report', 'I have an opportunity to publish the report')
        _, result = self.prepare(source)
        self.assertEqual(result.payload['final_action_executors'], ['Noor', 'Kai'])
        self.assertEqual(result.payload['status'], 'FINAL_ACTION_AUTHORIZATION_UNRESOLVED')

    def test_permission_does_not_confer_delegating_authority(self):
        source = SOURCE.replace('I plan to review the report', 'I plan to publish the report').replace('I have an opportunity to review the report', 'I have an opportunity to publish the report')
        source += '\nNoor said, "In team, I authorize Kai to publish the report."'
        _, result = self.prepare(source)
        self.assertEqual(result.payload['grants'][-1]['status'], 'ROLE_UNRESOLVED')
        self.assertEqual(result.payload['status'], 'FINAL_ACTION_AUTHORIZATION_UNRESOLVED')

    def test_other_person_cannot_revoke_grant(self):
        _, result = self.prepare(SOURCE + '\nKai said, "I revoke my authorization for Noor to publish the report in team."')
        self.assertEqual(result.payload['grants'][0]['status'], 'AUTHORIZED_UNDER_SOURCE_RULE')

    def test_different_person_goal_not_shared_goal(self):
        _, result = self.prepare(SOURCE.replace('Kai said, "I want to publish the report."', 'Kai said, "I want to delay the report."'))
        self.assertEqual(result.payload['status'], 'PARTICIPANT_PLAN_OR_ENDORSEMENT_UNRESOLVED')

    def test_late_receipt_not_past_acceptance(self):
        source = SOURCE.replace("Narrator: Noor and Kai heard Mira's last statement.", "Narrator: Noor heard Mira's last statement.")
        source = source.replace("Narrator: Mira and Noor heard Kai's last statement.", "Narrator: Mira and Noor heard Kai's last statement.\nNarrator: Kai later heard Mira's last statement.")
        _, result = self.prepare(source)
        self.assertFalse(result.payload['participants'][2]['proposal_receipt_at_endorsement']['received'])

    def test_hidden_and_source_revision(self):
        w, hidden = self.prepare(observer='Kai')
        self.assertNotIn('Mira said', json.dumps(hidden.messages(w)))
        w, result = self.prepare()
        w.put_source('scene', '\n'.join(SOURCE.splitlines()[:-1]))
        with self.assertRaisesRegex(ValueError, 'source changed'):
            result.messages(w)

    def test_support_withdrawal_and_budget(self):
        w, result = self.prepare()
        with self.assertRaisesRegex(ValueError, 'budget'):
            result.messages(w, max_chars=1000)
        w.core.withdraw(result.claim_ids[-1])
        with self.assertRaisesRegex(ValueError, 'support changed'):
            result.messages(w)


if __name__ == '__main__':
    unittest.main()
