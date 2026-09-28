import json
import unittest
from hcl.cognition import CognitionWorkspace
from hcl.cognition.mutual_understanding import prepare_mutual_understanding

SOURCE = '\n'.join(('Mira said, "I mean that the meeting is at noon."',
    "Narrator: Noor heard Mira's last statement.",
    'Noor said, "I understand Mira to mean that the meeting is at noon."',
    "Narrator: Mira heard Noor's last statement.",
    'Mira said, "I confirm Noor\'s understanding that the meeting is at noon."',
    "Narrator: Noor heard Mira's last statement."))
QUERY = 'Do Mira and Noor share an acknowledged understanding that the meeting is at noon?'


class MutualUnderstandingTests(unittest.TestCase):
    def prepare(self, source=SOURCE, query=QUERY, observer=None, acl=()):
        w = CognitionWorkspace()
        w.put_source('scene', source, permitted_observers=acl)
        return w, prepare_mutual_understanding(w, query, source_id='scene', observer=observer)

    def test_positive_finite_acknowledgment(self):
        w, result = self.prepare()
        self.assertEqual(result.payload['status'], 'BOUNDED_MUTUALLY_ACKNOWLEDGED')
        self.assertEqual(result.payload['actual_comprehension'], 'NOT_ESTABLISHED')
        self.assertEqual(result.payload['infinite_common_knowledge'], 'NOT_INFERRED')
        self.assertIn('interpretation_receipt_at_confirmation', result.messages(w)[1]['content'])

    def test_hearing_and_okay_not_acknowledgment(self):
        _, result = self.prepare('\n'.join(SOURCE.splitlines()[:2]) + '\nNoor said, "Okay."')
        self.assertEqual(result.payload['status'], 'NO_COMPLETE_ACKNOWLEDGMENT_CHAIN')

    def test_final_confirmation_must_be_received(self):
        _, result = self.prepare('\n'.join(SOURCE.splitlines()[:-1]))
        self.assertEqual(result.payload['status'], 'ACKNOWLEDGMENT_DELIVERY_INCOMPLETE')

    def test_speaker_must_receive_interpretation_before_confirming(self):
        source = SOURCE.replace("Narrator: Mira heard Noor's last statement.\n", '')
        _, result = self.prepare(source + "\nNarrator: Mira later heard Noor's last statement.")
        self.assertEqual(result.payload['status'], 'ACKNOWLEDGMENT_DELIVERY_INCOMPLETE')
        self.assertFalse(result.payload['acknowledgment_chains'][0]['interpretation_receipt_at_confirmation']['received'])

    def test_later_original_receipt_does_not_backfill(self):
        source = SOURCE.replace("Narrator: Noor heard Mira's last statement.", "Narrator: Noor did not hear Mira's last statement.", 1)
        # Insert later receipt before Mira's next statement changes the reference.
        source = source.replace('Narrator: Mira heard', "Narrator: Noor later heard Mira's last statement.\nNarrator: Mira heard")
        _, result = self.prepare(source)
        self.assertEqual(result.payload['status'], 'ACKNOWLEDGMENT_DELIVERY_INCOMPLETE')
        self.assertFalse(result.payload['acknowledgment_chains'][0]['original_receipt_at_interpretation']['received'])

    def test_explicit_revision_retires_old_acknowledgment(self):
        _, result = self.prepare(SOURCE + '\nMira said, "I revise my meaning from the meeting is at noon to the meeting is at one."')
        self.assertEqual(result.payload['status'], 'SUPERSEDED_MEANING')
        self.assertEqual(result.payload['current_meaning']['content'], 'the meeting is at one')
        self.assertEqual(result.payload['acknowledgment_chains'][0]['status'], 'SUPERSEDED_MEANING_HISTORICAL_ACKNOWLEDGMENT')
        self.assertEqual(result.payload['trust_restoration'], 'NOT_INFERRED')

    def test_new_meaning_requires_new_chain(self):
        source = SOURCE + '\nMira said, "I revise my meaning from the meeting is at noon to the meeting is at one."'
        new_query = QUERY.replace('noon', 'one')
        _, result = self.prepare(source, new_query)
        self.assertEqual(result.payload['status'], 'NO_COMPLETE_ACKNOWLEDGMENT_CHAIN')
        source += '\n' + '\n'.join(SOURCE.replace('noon', 'one').splitlines()[1:])
        _, result = self.prepare(source, new_query)
        self.assertEqual(result.payload['status'], 'BOUNDED_MUTUALLY_ACKNOWLEDGED')

    def test_explicit_doubt_prevents_certainty(self):
        _, result = self.prepare(SOURCE + '\nNoor said, "I am unsure whether I understand Mira to mean that the meeting is at noon."')
        self.assertEqual(result.payload['status'], 'EXPLICIT_UNCERTAINTY_OR_CONFLICT')

    def test_third_party_confirmation_not_speakers_confirmation(self):
        _, result = self.prepare(SOURCE.replace('Mira said, "I confirm', 'Kai said, "I confirm'))
        self.assertEqual(result.payload['status'], 'NO_COMPLETE_ACKNOWLEDGMENT_CHAIN')

    def test_higher_order_belief_preserved_not_common_ground(self):
        source = '\n'.join(SOURCE.splitlines()[:2]) + '\nNoor said, "I believe Mira believes the meeting is at noon."'
        _, result = self.prepare(source)
        self.assertEqual(result.payload['status'], 'NO_COMPLETE_ACKNOWLEDGMENT_CHAIN')
        tree = result.payload['reported_higher_order'][0]['public_expression']
        self.assertEqual(tree['holder'], 'Noor')
        self.assertEqual(tree['content']['holder'], 'Mira')

    def test_hidden_source_does_not_leak(self):
        w, result = self.prepare(observer='Kai')
        self.assertNotIn('Mira said', json.dumps(result.messages(w)))
        self.assertEqual(result.payload['status'], 'NO_COMPLETE_ACKNOWLEDGMENT_CHAIN')

    def test_revision_requires_old_anchor(self):
        _, result = self.prepare(SOURCE + '\nMira said, "I revise my meaning from the meeting is at ten to the meeting is at one."')
        self.assertEqual(result.payload['current_meaning']['content'], 'the meeting is at noon')
        self.assertTrue(result.payload['diagnostics'])

    def test_source_support_and_budget(self):
        w, result = self.prepare()
        with self.assertRaisesRegex(ValueError, 'budget'):
            result.messages(w, max_chars=1000)
        w.core.withdraw(result.claim_ids[0])
        with self.assertRaisesRegex(ValueError, 'support changed'):
            result.messages(w)
        w, result = self.prepare()
        w.put_source('scene', SOURCE + '\nNoor said, "Okay."')
        with self.assertRaisesRegex(ValueError, 'source changed'):
            result.messages(w)


if __name__ == '__main__':
    unittest.main()
