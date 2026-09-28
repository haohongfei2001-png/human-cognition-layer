import json
import unittest
from hcl.cognition import CognitionWorkspace
from hcl.cognition.misunderstanding import prepare_misunderstanding

SOURCE = '\n'.join(('Mira said, "In team, by ready I mean permit is true."',
    'Noor said, "In team, by ready I mean draft is true."',
    'Mira said, "I promise Noor to deliver the ready report if the permit arrives."',
    "Narrator: Noor did not hear Mira's last statement.",
    'Noor said, "As reviewer in team, I expect Mira to deliver the ready report."',
    'Noor said, "I expect Mira to deliver the ready report."'))
CLARIFY = '\nMira said, "I clarify to Noor that my promise to deliver the ready report still requires that the permit arrives."'
RECEIPT = "\nNarrator: Noor heard Mira's last statement."
REVISION = '\nNoor said, "I now expect Mira to deliver the ready report if the permit arrives."'
QUERY = "Explain Noor's expectation of Mira's promise to deliver the ready report in team, using ready for report."


class MisunderstandingTests(unittest.TestCase):
    def prepare(self, source=SOURCE, observer=None):
        w = CognitionWorkspace()
        w.put_source('scene', source)
        return w, prepare_misunderstanding(w, QUERY, source_id='scene', observer=observer)

    def test_positive_multi_factor_localization(self):
        _, result = self.prepare()
        factors = result.payload['initial_factors']
        self.assertTrue(factors['condition_omitted'])
        self.assertEqual(factors['original_condition_receipt']['status'], 'REPORTED_NON_EXPOSURE')
        self.assertEqual(factors['local_meaning']['status'], 'DIFFERING_SOURCE_LOCAL_CRITERIA')
        self.assertEqual(factors['role_expectations'][0]['role'], 'reviewer')
        self.assertEqual(factors['role_expectations'][0]['authority'], 'SELF_REPORTED_ROLE_EXPECTATION_NOT_INSTITUTIONAL_RULE')

    def test_receipt_does_not_automatically_repair(self):
        _, result = self.prepare(SOURCE + CLARIFY + RECEIPT)
        self.assertEqual(result.payload['status'], 'CLARIFICATION_RECEIVED_EXPECTATION_UNREVISED')
        self.assertEqual(result.payload['expectation_revisions'], [])

    def test_explicit_revision_replaces_explanation_not_promise(self):
        w, result = self.prepare(SOURCE + CLARIFY + RECEIPT + REVISION)
        self.assertEqual(result.payload['status'], 'REVISED_EXPECTATION_ALIGNS_CLARIFICATION_AVAILABLE')
        change = result.payload['explanation_revision']
        self.assertIn(change['old'], w.core.withdrawn)
        self.assertIn(change['new'], w.core.grounded())
        self.assertFalse(result.payload['promise_rewritten'])
        self.assertEqual(result.payload['original_promise']['conditions'][0]['key'], 'the permit arrives')
        self.assertEqual(result.payload['trust_restoration'], 'NOT_INFERRED')
        self.assertIn('REVISED_EXPECTATION_ALIGNS', result.messages(w)[1]['content'])
        repeated = prepare_misunderstanding(w, QUERY, source_id='scene')
        self.assertEqual(repeated.payload['status'], result.payload['status'])

    def test_unreceived_clarification_not_revision_cause(self):
        _, result = self.prepare(SOURCE + CLARIFY + REVISION)
        self.assertEqual(result.payload['status'], 'REVISED_EXPECTATION_ALIGNS_CAUSE_UNRESOLVED')

    def test_later_receipt_not_backfilled_into_revision(self):
        _, result = self.prepare(SOURCE + CLARIFY + REVISION + RECEIPT)
        self.assertEqual(result.payload['status'], 'REVISED_EXPECTATION_ALIGNS_CAUSE_UNRESOLVED')

    def test_new_condition_not_silently_replacing_original(self):
        _, result = self.prepare(SOURCE + CLARIFY.replace('the permit arrives', 'the draft arrives') + RECEIPT)
        self.assertEqual(result.payload['status'], 'INITIAL_EXPECTATION_FACTORS_ONLY')
        self.assertEqual(len(result.payload['changed_condition_reports']), 1)
        self.assertEqual(result.payload['original_promise']['conditions'][0]['key'], 'the permit arrives')

    def test_revision_can_still_disagree(self):
        _, result = self.prepare(SOURCE + CLARIFY + RECEIPT + REVISION.replace('the permit arrives', 'the draft arrives'))
        self.assertEqual(result.payload['status'], 'REVISED_EXPECTATION_STILL_DIFFERS')

    def test_third_party_cannot_supply_clarification(self):
        _, result = self.prepare(SOURCE + CLARIFY.replace('Mira said', 'Kai said') + REVISION)
        self.assertEqual(result.payload['status'], 'REVISED_EXPECTATION_ALIGNS_CAUSE_UNRESOLVED')

    def test_future_definition_not_original_misunderstanding(self):
        source = '\n'.join(SOURCE.splitlines()[2:]) + '\n' + '\n'.join(SOURCE.splitlines()[:2])
        _, result = self.prepare(source)
        self.assertEqual(result.payload['initial_factors']['local_meaning']['status'], 'NO_LOCAL_DEFINITION')
        self.assertEqual(result.payload['current_local_meaning']['status'], 'DIFFERING_SOURCE_LOCAL_CRITERIA')

    def test_unrelated_context_not_shared_meaning(self):
        _, result = self.prepare(SOURCE.replace('Noor said, "In team, by ready', 'Noor said, "In club, by ready'))
        self.assertEqual(result.payload['initial_factors']['local_meaning']['status'], 'NO_ESTABLISHED_DIFFERENCE')

    def test_hidden_source_and_revision_guard(self):
        w, hidden = self.prepare(observer='Kai')
        self.assertNotIn('Mira said', json.dumps(hidden.messages(w)))
        w, old = self.prepare()
        w.put_source('scene', SOURCE + CLARIFY + RECEIPT + REVISION)
        with self.assertRaisesRegex(ValueError, 'source changed'):
            old.messages(w)

    def test_ambiguous_anchor_and_budget(self):
        with self.assertRaisesRegex(ValueError, 'multiple unlinked'):
            self.prepare(SOURCE + '\nNoor said, "I expect Mira to deliver the ready report if the permit arrives."')
        w, result = self.prepare()
        with self.assertRaisesRegex(ValueError, 'budget'):
            result.messages(w, max_chars=1000)


if __name__ == '__main__':
    unittest.main()
