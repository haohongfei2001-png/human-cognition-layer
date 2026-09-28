import json
import unittest
from hcl.cognition import CognitionWorkspace
from hcl.cognition.commitments import prepare_commitment

SOURCE = '\n'.join(('Mira said, "I promise Noor to deliver the report if the permit arrives."',
    "Narrator: Noor heard Mira's last statement.",
    'Noor said, "I accept Mira\'s promise to deliver the report."',
    'Noor said, "I expect Mira to deliver the report."'))
QUERY = "What is the status of Mira's promise to Noor to deliver the report?"


class CommitmentTests(unittest.TestCase):
    def prepare(self, source=SOURCE, observer=None, acl=()):
        w = CognitionWorkspace()
        w.put_source('scene', source, permitted_observers=acl)
        return w, prepare_commitment(w, QUERY, source_id='scene', observer=observer)

    def test_condition_lifecycle_positive(self):
        _, unknown = self.prepare()
        self.assertEqual(unknown.payload['commitment']['lifecycle'], 'CONDITION_UNRESOLVED')
        _, false = self.prepare(SOURCE + '\nNarrator: It is false that the permit arrives.')
        self.assertEqual(false.payload['commitment']['lifecycle'], 'CONDITION_NOT_MET_IN_SOURCE')
        _, true = self.prepare(SOURCE + '\nNarrator: It is true that the permit arrives.')
        self.assertEqual(true.payload['commitment']['lifecycle'], 'CONDITIONALLY_TRIGGERED_IN_SOURCE')
        self.assertEqual(true.payload['commitment']['obligation'], 'NOT_ESTABLISHED')

    def test_receipt_acceptance_and_expectation_separate(self):
        _, result = self.prepare()
        p = result.payload
        self.assertTrue(p['commitment']['conditions_received'])
        self.assertEqual(p['commitment']['acceptance'], 'REPORTED_ACCEPTANCE')
        self.assertEqual(p['cg02_source_check']['checked_expectation_count'], 1)
        self.assertEqual(p['cg02_source_check']['expectation_comparisons'][0]['omitted_condition_keys'], ['the permit arrives'])
        self.assertEqual(p['commitment']['private_understanding'], 'NOT_ESTABLISHED')

    def test_no_receipt_differs_from_false_condition(self):
        _, result = self.prepare(SOURCE.replace('Noor heard', 'Noor did not hear'))
        self.assertEqual(result.payload['commitment']['receipt'], 'REPORTED_NON_EXPOSURE')
        self.assertFalse(result.payload['commitment']['conditions_received'])
        self.assertEqual(result.payload['commitment']['condition_status'], 'UNKNOWN')
        self.assertEqual(result.payload['commitment']['acceptance'], 'REPORTED_ACCEPTANCE')

    def test_withdrawal_preserves_original_and_expectation(self):
        _, result = self.prepare(SOURCE + '\nMira said, "I withdraw my promise to Noor to deliver the report."')
        self.assertEqual(result.payload['commitment']['lifecycle'], 'REPORTED_WITHDRAWN')
        self.assertEqual(len(result.payload['commitment']['original_promise']['conditions']), 1)
        self.assertEqual(result.payload['cg02_source_check']['checked_expectation_count'], 1)
        self.assertEqual(result.payload['cg02_source_check']['expectation_comparisons'][0]['withdrawal_order'], 'AFTER_REPORTED_EXPECTATION')

    def test_later_receipt_does_not_backfill_earlier_expectation(self):
        source = SOURCE.replace("Narrator: Noor heard Mira's last statement.", "Narrator: Noor did not hear Mira's last statement.")
        _, result = self.prepare(source + "\nNarrator: Noor later heard Mira's last statement.")
        self.assertEqual(result.payload['commitment']['receipt'], 'REPORTED_LATER_EXPOSURE')
        comparison = result.payload['cg02_source_check']['expectation_comparisons'][0]
        self.assertEqual(comparison['condition_receipt_at_expectation'], 'REPORTED_NON_EXPOSURE')
        self.assertEqual(comparison['condition_access']['the permit arrives'], 'UNKNOWN_ACCESS')

    def test_fulfillment_is_report(self):
        _, result = self.prepare(SOURCE + '\nMira said, "I fulfilled my promise to Noor to deliver the report."')
        self.assertEqual(result.payload['commitment']['lifecycle'], 'REPORTED_FULFILLED')
        self.assertEqual(result.payload['commitment']['fulfillment'], 'SOURCE_REPORT_NOT_VERIFIED_OUTCOME')

    def test_other_actor_cannot_withdraw(self):
        _, result = self.prepare(SOURCE + '\nKai said, "I withdraw my promise to Noor to deliver the report."')
        self.assertEqual(result.payload['commitment']['lifecycle'], 'CONDITION_UNRESOLVED')

    def test_conflicting_conditions_and_responses(self):
        _, result = self.prepare(SOURCE + '\nNarrator: It is true that the permit arrives.\nNarrator: It is false that the permit arrives.\nNoor said, "I refuse Mira\'s promise to deliver the report."')
        self.assertEqual(result.payload['commitment']['condition_status'], 'CONFLICTING_SOURCE_CLAIMS')
        self.assertEqual(result.payload['commitment']['acceptance'], 'CONFLICTING_RESPONSE_REPORTS')

    def test_addressing_not_receipt(self):
        _, result = self.prepare(SOURCE.replace("Narrator: Noor heard Mira's last statement.", 'Narrator: Mira sent their last statement privately to Noor.'))
        self.assertEqual(result.payload['commitment']['receipt'], 'ADDRESSED_RECEIPT_UNKNOWN')
        self.assertFalse(result.payload['commitment']['conditions_received'])

    def test_hidden_source_and_source_revision(self):
        w, result = self.prepare(observer='Kai')
        self.assertNotIn('permit', json.dumps(result.messages(w)))
        w, result = self.prepare()
        w.put_source('scene', SOURCE + '\nNarrator: It is true that the permit arrives.')
        with self.assertRaisesRegex(ValueError, 'source changed'):
            result.messages(w)
        new = prepare_commitment(w, QUERY, source_id='scene')
        self.assertEqual(new.payload['commitment']['condition_status'], 'SOURCE_REPORTED_TRUE')

    def test_prefix_no_future_withdrawal(self):
        _, before = self.prepare()
        _, after = self.prepare(SOURCE + '\nMira said, "I withdraw my promise to Noor to deliver the report."')
        self.assertNotEqual(before.payload['commitment']['lifecycle'], after.payload['commitment']['lifecycle'])

    def test_missing_ambiguous_or_negative_promise(self):
        _, result = self.prepare('Mira said, "I do not promise Noor to deliver the report if the permit arrives."')
        self.assertEqual(result.payload['status'], 'SYSTEM_INSUFFICIENT')
        with self.assertRaisesRegex(ValueError, 'multiple matching'):
            self.prepare(SOURCE + '\n' + SOURCE.splitlines()[0])

    def test_early_response_has_no_anchor(self):
        _, result = self.prepare('Noor said, "I accept Mira\'s promise to deliver the report."\n' + SOURCE.splitlines()[0])
        self.assertEqual(result.payload['commitment']['acceptance'], 'NO_EXPLICIT_RESPONSE')
        self.assertTrue(result.payload['diagnostics'])

    def test_support_withdrawal_and_context_budget(self):
        w, result = self.prepare()
        self.assertIn('original_promise', result.messages(w)[1]['content'])
        with self.assertRaisesRegex(ValueError, 'budget'):
            result.messages(w, max_chars=1000)
        w.core.withdraw(result.claim_ids[0])
        with self.assertRaisesRegex(ValueError, 'support changed'):
            result.messages(w)


if __name__ == '__main__':
    unittest.main()
