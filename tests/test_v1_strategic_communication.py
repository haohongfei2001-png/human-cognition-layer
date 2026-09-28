import json
import unittest
from hcl.cognition import CognitionWorkspace
from hcl.cognition.strategic_communication import prepare_strategic_communication

SOURCE = '\n'.join(('Mira said, "I want to make Noor believe the train is running."',
    'Mira said, "I believe the train is running."',
    'Mira said, "Noor, the train is running."',
    "Narrator: Mira's statement that the train is running is false."))
QUERY = "How might Mira's statement to Noor that the train is running be explained?"
TRUE_SOURCE = '\n'.join(('Mira said, "I want to keep Noor from learning that the bridge is closed."',
    'Mira said, "I know the bridge is closed."',
    'Noor said, "I need to know whether the bridge is closed."',
    "Narrator: Mira heard Noor's last statement.",
    'Mira said, "Noor, the bridge has lights."',
    "Narrator: Mira's statement that the bridge has lights is true.",
    "Narrator: Mira's statement that the bridge has lights omitted that the bridge is closed."))
TRUE_QUERY = "How might Mira's statement to Noor that the bridge has lights be explained?"


class StrategicCommunicationTests(unittest.TestCase):
    def prepare(self, source=SOURCE, query=QUERY, observer=None, acl=()):
        w = CognitionWorkspace()
        w.put_source('scene', source, permitted_observers=acl)
        return w, prepare_strategic_communication(w, query, source_id='scene', observer=observer)

    def states(self, result):
        return {e['hypothesis']: e['disposition'] for e in result.payload['explanations']}

    def test_belief_change_revises_competing_explanations(self):
        _, benign = self.prepare()
        self.assertEqual(self.states(benign)['BENIGN_ERROR'], 'CONDITIONALLY_SUPPORTED')
        self.assertEqual(self.states(benign)['DELIBERATE_FALSEHOOD'], 'WEAKENED_BY_COUNTEREVIDENCE')
        _, contrary = self.prepare(SOURCE.replace('I believe the train is running.', 'I believe it is false that the train is running.'))
        self.assertEqual(self.states(contrary)['DELIBERATE_FALSEHOOD'], 'CONDITIONALLY_SUPPORTED')
        self.assertEqual(self.states(contrary)['BENIGN_ERROR'], 'WEAKENED_BY_COUNTEREVIDENCE')
        self.assertEqual(contrary.payload['actual_deception'], 'NOT_ESTABLISHED')

    def test_false_content_alone_is_not_deception(self):
        _, result = self.prepare('\n'.join(SOURCE.splitlines()[2:]))
        self.assertEqual(self.states(result)['DELIBERATE_FALSEHOOD'], 'UNRESOLVED')
        self.assertEqual(self.states(result)['BENIGN_ERROR'], 'UNRESOLVED')

    def test_true_content_can_support_conditional_concealment(self):
        _, result = self.prepare(TRUE_SOURCE, TRUE_QUERY)
        self.assertEqual(self.states(result)['LITERALLY_TRUE_POTENTIALLY_MISLEADING'], 'CONDITIONALLY_SUPPORTED')
        self.assertEqual(self.states(result)['CONCEALMENT'], 'CONDITIONALLY_SUPPORTED')
        self.assertEqual(result.payload['moral_verdict'], 'NOT_INFERRED')

    def test_omission_alone_not_concealment(self):
        _, result = self.prepare('\n'.join(TRUE_SOURCE.splitlines()[4:]), TRUE_QUERY)
        self.assertEqual(self.states(result)['CONCEALMENT'], 'UNRESOLVED')

    def test_unscoped_omission_not_bound_to_arbitrary_statement(self):
        _, result = self.prepare(TRUE_SOURCE.replace('statement that the bridge has lights omitted', 'statement omitted'), TRUE_QUERY)
        self.assertEqual(self.states(result)['CONCEALMENT'], 'UNRESOLVED')

    def test_truth_report_does_not_grant_character_access(self):
        from hcl.cognition.communication import CommunicationScene
        source = "Narrator: Mira's statement that the bridge has lights is true."
        self.assertEqual(CommunicationScene(source).view('Noor').visible_text, '')

    def test_recipient_need_not_received_stays_unresolved(self):
        _, result = self.prepare(TRUE_SOURCE.replace('Mira heard', 'Mira did not hear'), TRUE_QUERY)
        self.assertEqual(self.states(result)['LITERALLY_TRUE_POTENTIALLY_MISLEADING'], 'UNRESOLVED')

    def test_later_belief_or_goal_not_backfilled(self):
        source = '\n'.join(SOURCE.splitlines()[2:]) + '\n' + SOURCE.splitlines()[0] + '\nMira said, "I believe it is false that the train is running."'
        _, result = self.prepare(source)
        self.assertEqual(self.states(result)['DELIBERATE_FALSEHOOD'], 'UNRESOLVED')

    def test_unknown_belief_not_negative_belief(self):
        _, result = self.prepare(SOURCE.replace('I believe the train is running.', 'I do not believe the train is running.'))
        self.assertEqual(self.states(result)['DELIBERATE_FALSEHOOD'], 'UNRESOLVED')

    def test_third_party_belief_does_not_fill_speaker_mind(self):
        _, result = self.prepare(SOURCE.replace('Mira said, "I believe', 'Kai said, "I believe'))
        self.assertEqual(self.states(result)['BENIGN_ERROR'], 'UNRESOLVED')

    def test_conflicting_source_truth_and_uncertain_belief(self):
        _, result = self.prepare(SOURCE + "\nNarrator: Mira's statement that the train is running is true.")
        self.assertEqual(self.states(result)['BENIGN_ERROR'], 'CONFLICTING_PREMISES')
        _, result = self.prepare(SOURCE.replace('I believe', 'I am unsure whether'))
        self.assertEqual(self.states(result)['BENIGN_ERROR'], 'UNRESOLVED')

    def test_hidden_source_and_wrong_addressee(self):
        w, result = self.prepare(observer='Kai')
        self.assertNotIn('Mira said', json.dumps(result.messages(w)))
        _, result = self.prepare(SOURCE.replace('Noor, the train', 'Kai, the train'))
        self.assertEqual(result.payload['status'], 'SYSTEM_INSUFFICIENT')

    def test_source_revision_and_support_withdrawal(self):
        w, old = self.prepare()
        w.put_source('scene', SOURCE.replace('I believe the train is running.', 'I believe it is false that the train is running.'))
        with self.assertRaisesRegex(ValueError, 'source changed'):
            old.messages(w)
        result = prepare_strategic_communication(w, QUERY, source_id='scene')
        self.assertIn('DELIBERATE_FALSEHOOD', result.messages(w)[1]['content'])
        w.core.withdraw(result.claim_ids[0])
        with self.assertRaisesRegex(ValueError, 'support changed'):
            result.messages(w)

    def test_ambiguous_action_and_budget_refused(self):
        with self.assertRaisesRegex(ValueError, 'multiple statement'):
            self.prepare(SOURCE + '\n' + SOURCE.splitlines()[2])
        w, result = self.prepare()
        with self.assertRaisesRegex(ValueError, 'budget'):
            result.messages(w, max_chars=1000)


if __name__ == '__main__':
    unittest.main()
