import json
import unittest
from hcl.cognition.agency_chain import SemanticWorkspace
from hcl.cognition.relational_conflict import prepare_relational_conflict

SOURCE = '\n'.join(('Noor said, "I failed to deliver the report in coding."',
    'Noor said, "For the attempt to deliver the report in coding, at the time I did not know the requirements."',
    'Noor said, "For the attempt to deliver the report in coding, at the time I could not prevent the failure."',
    'Mira said, "In coding, I distrust Noor\'s reliability because Noor failed to deliver the report."'))
QUERY = "Explain Mira's response to Noor's failure to deliver the report in coding."
APOLOGY = '\nNoor said, "I apologize to Mira for failing to deliver the report in coding."'
RECEIPT = "\nNarrator: Mira heard Noor's last statement."
FORGIVE = '\nMira said, "In coding, I forgive Noor for failing to deliver the report."'


class RelationalConflictTests(unittest.TestCase):
    def prepare(self, source=SOURCE, observer=None):
        w = SemanticWorkspace()
        w.put_source('scene', source)
        return w, prepare_relational_conflict(w, QUERY, source_id='scene', observer=observer)

    def states(self, result):
        return {e['hypothesis']: e['status'] for e in result.payload['explanations']}

    def test_positive_information_and_control_alternatives(self):
        _, result = self.prepare()
        states = self.states(result)
        self.assertEqual(states['INFORMATION_GAP'], 'CONDITIONALLY_SUPPORTED')
        self.assertEqual(states['CONTROL_CONSTRAINT'], 'CONDITIONALLY_SUPPORTED')
        self.assertEqual(states['INFORMED_CONTROLLABLE_STATED_CHOICE'], 'WEAKENED_BY_COUNTEREVIDENCE')
        self.assertEqual(result.payload['relationship']['status'], 'DISTRUST')
        self.assertFalse(result.payload['automatic_relationship_change'])

    def test_changed_evidence_updates_attribution_not_attitude(self):
        source = SOURCE.replace('did not know', 'knew').replace('could not prevent', 'could prevent')
        source += '\nNoor said, "For the attempt to deliver the report in coding, at the time I intended to fail to deliver the report."'
        _, result = self.prepare(source)
        self.assertEqual(self.states(result)['INFORMED_CONTROLLABLE_STATED_CHOICE'], 'CONDITIONALLY_SUPPORTED')
        self.assertEqual(result.payload['relationship']['status'], 'DISTRUST')
        self.assertEqual(result.payload['moral_blame'], 'NOT_INFERRED')

    def test_failure_alone_not_bad_intention(self):
        _, result = self.prepare(SOURCE.splitlines()[0])
        self.assertTrue(all(s == 'UNRESOLVED' for s in self.states(result).values()))
        self.assertEqual(result.payload['factor_checks']['STATED_INTENTION']['state'], 'UNKNOWN')

    def test_apology_receipt_not_forgiveness(self):
        _, unheard = self.prepare(SOURCE + APOLOGY)
        self.assertEqual(unheard.payload['repair_status'], 'APOLOGY_RECEIPT_UNKNOWN')
        _, heard = self.prepare(SOURCE + APOLOGY + RECEIPT)
        self.assertEqual(heard.payload['repair_status'], 'APOLOGY_RECEIVED_FORGIVENESS_UNKNOWN')

    def test_accepting_apology_not_forgiveness(self):
        _, result = self.prepare(SOURCE + APOLOGY + RECEIPT + '\nMira said, "I accept Noor\'s apology."')
        self.assertEqual(result.payload['repair_status'], 'APOLOGY_RECEIVED_FORGIVENESS_UNKNOWN')

    def test_explicit_forgiveness_remains_report(self):
        _, result = self.prepare(SOURCE + APOLOGY + RECEIPT + FORGIVE)
        self.assertEqual(result.payload['repair_status'], 'REPORTED_FORGIVENESS')
        self.assertEqual(result.payload['actual_forgiveness'], 'NOT_ESTABLISHED')
        self.assertEqual(result.payload['relationship']['status'], 'DISTRUST')

    def test_conflicting_forgiveness_and_factor_reports(self):
        source = SOURCE + FORGIVE + FORGIVE.replace('I forgive', 'I do not forgive')
        source += '\nNoor said, "For the attempt to deliver the report in coding, at the time I knew the requirements."'
        _, result = self.prepare(source)
        self.assertEqual(result.payload['repair_status'], 'CONFLICTING_FORGIVENESS_REPORTS')
        self.assertEqual(self.states(result)['INFORMATION_GAP'], 'CONFLICTING_PREMISES')

    def test_wrong_domain_or_action_not_factor_evidence(self):
        source = SOURCE.replace('For the attempt to deliver the report in coding', 'For the attempt to deliver the report in finance')
        _, result = self.prepare(source)
        self.assertEqual(result.payload['factor_checks']['KNOWLEDGE']['state'], 'UNKNOWN')
        _, result = self.prepare(SOURCE.replace('For the attempt to deliver the report', 'For the attempt to review the report'))
        self.assertEqual(result.payload['factor_checks']['CONTROL']['state'], 'UNKNOWN')

    def test_later_learning_not_action_time_knowledge(self):
        source = SOURCE.splitlines()[0] + '\nNoor said, "For the attempt to deliver the report in coding, I later learned the requirements."'
        _, result = self.prepare(source)
        self.assertEqual(result.payload['factor_checks']['KNOWLEDGE']['state'], 'UNKNOWN')

    def test_intention_of_success_not_intention_of_failure(self):
        source = SOURCE + '\nNoor said, "For the attempt to deliver the report in coding, at the time I intended to deliver the report."'
        _, result = self.prepare(source)
        self.assertEqual(result.payload['factor_checks']['STATED_INTENTION']['state'], 'UNKNOWN')

    def test_third_party_factor_or_apology_not_direct(self):
        source = SOURCE.replace('Noor said, "For the attempt', 'Kai said, "For the attempt') + APOLOGY.replace('Noor said', 'Kai said')
        _, result = self.prepare(source)
        self.assertEqual(result.payload['factor_checks']['KNOWLEDGE']['state'], 'UNKNOWN')
        self.assertEqual(result.payload['apologies'], [])

    def test_hidden_source_and_ambiguous_failure(self):
        w, result = self.prepare(observer='Kai')
        self.assertNotIn('Noor said', json.dumps(result.messages(w)))
        with self.assertRaisesRegex(ValueError, 'multiple failure'):
            self.prepare(SOURCE + '\n' + SOURCE.splitlines()[0])

    def test_source_update_support_and_final_input(self):
        w, result = self.prepare()
        state = json.loads(result.messages(w)[1]['content'])
        self.assertTrue(state['factor_source_bindings'])
        self.assertEqual(state['relationship']['status'], 'DISTRUST')
        w.put_source('scene', SOURCE + APOLOGY)
        with self.assertRaisesRegex(ValueError, 'source changed'):
            result.messages(w)
        fresh = prepare_relational_conflict(w, QUERY, source_id='scene')
        w.core.withdraw(fresh.claim_ids[-1])
        with self.assertRaisesRegex(ValueError, 'support changed'):
            fresh.messages(w)


if __name__ == '__main__':
    unittest.main()
