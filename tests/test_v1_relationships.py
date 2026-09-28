import json
import unittest
from hcl.cognition import CognitionWorkspace
from hcl.cognition.relationships import prepare_relationship

SOURCE = '\n'.join(('Narrator: In coding, Noor found the bug.',
    'Mira said, "In coding, I trust Noor\'s competence because Noor found the bug."',
    'Mira said, "In coding, I am unsure about Noor\'s honesty because the accounts differ."'))
QUERY = "How does Mira regard Noor's competence in coding?"


class RelationshipTests(unittest.TestCase):
    def prepare(self, source=SOURCE, query=QUERY, observer=None):
        w = CognitionWorkspace()
        w.put_source('scene', source)
        return w, prepare_relationship(w, query, source_id='scene', observer=observer)

    def test_positive_scoped_regard_and_basis(self):
        w, result = self.prepare()
        self.assertEqual(result.payload['status'], 'TRUST')
        self.assertEqual(result.payload['current_reports'][0]['basis_current']['status'], 'SOURCE_SUPPORTED_BASIS')
        self.assertEqual(result.payload['actual_trait'], 'NOT_ESTABLISHED')
        self.assertIn('assessor_access', result.messages(w)[1]['content'])

    def test_competence_does_not_become_honesty_or_other_domain(self):
        _, honest = self.prepare(query=QUERY.replace('competence', 'honesty'))
        self.assertEqual(honest.payload['status'], 'CHARACTER_UNCERTAIN')
        _, other = self.prepare(query=QUERY.replace('coding', 'finance'))
        self.assertEqual(other.payload['status'], 'SYSTEM_INSUFFICIENT')

    def test_direction_not_reciprocal(self):
        _, reverse = self.prepare(query="How does Noor regard Mira's competence in coding?")
        self.assertEqual(reverse.payload['status'], 'SYSTEM_INSUFFICIENT')

    def test_counterevidence_changes_basis_not_persons_report(self):
        _, result = self.prepare(SOURCE + '\nNarrator: In coding, it is false that Noor found the bug.')
        self.assertEqual(result.payload['status'], 'TRUST')
        report = result.payload['current_reports'][0]
        self.assertEqual(report['basis_current']['status'], 'CONTESTED_SOURCE_BASIS')
        self.assertEqual(report['basis_at_report']['status'], 'SOURCE_SUPPORTED_BASIS')

    def test_explicit_local_revision_retains_old_report(self):
        _, result = self.prepare(SOURCE + '\nNarrator: In coding, Noor missed the bug.\nMira said, "In coding, I now distrust Noor\'s competence instead of trusting it because Noor missed the bug."')
        self.assertEqual(result.payload['status'], 'DISTRUST')
        self.assertEqual(len(result.payload['historical_reports']), 1)
        self.assertTrue(result.payload['current_reports'][0]['revises_source_claim_id'])

    def test_unanchored_revision_does_not_delete_old_report(self):
        _, result = self.prepare(SOURCE + '\nMira said, "In coding, I now trust Noor\'s competence instead of distrusting it because Noor found the bug."')
        self.assertEqual(result.payload['status'], 'TRUST')
        self.assertEqual(result.payload['historical_reports'], [])
        self.assertTrue(result.payload['diagnostics'])

    def test_unmarked_opposite_report_is_conflict(self):
        _, result = self.prepare(SOURCE + '\nMira said, "In coding, I distrust Noor\'s competence because Noor missed the bug."')
        self.assertEqual(result.payload['status'], 'CONFLICTING_REPORTED_REGARD')

    def test_third_party_attribution_not_direct_regard(self):
        _, result = self.prepare('Kai said, "In coding, Mira trusts Noor\'s competence because Noor found the bug."')
        self.assertEqual(result.payload['status'], 'ATTRIBUTED_ONLY')
        self.assertEqual(result.payload['current_reports'], [])

    def test_later_source_basis_not_backdated(self):
        source = '\n'.join(SOURCE.splitlines()[1:]) + '\n' + SOURCE.splitlines()[0]
        _, result = self.prepare(source)
        self.assertEqual(result.payload['current_reports'][0]['basis_at_report']['status'], 'SELF_REPORTED_REASON_ONLY')
        self.assertEqual(result.payload['current_reports'][0]['basis_current']['status'], 'SOURCE_SUPPORTED_BASIS')

    def test_hidden_source_source_revision_and_support(self):
        w, result = self.prepare(observer='Kai')
        self.assertNotIn('Mira said', json.dumps(result.messages(w)))
        w, old = self.prepare()
        w.put_source('scene', SOURCE.replace('found the bug', 'reviewed the patch'))
        with self.assertRaisesRegex(ValueError, 'source changed'):
            old.messages(w)
        new = prepare_relationship(w, QUERY, source_id='scene')
        w.core.withdraw(new.claim_ids[-1])
        with self.assertRaisesRegex(ValueError, 'support changed'):
            new.messages(w)

    def test_negative_and_budget(self):
        _, result = self.prepare('Mira said, "In coding, I do not trust Noor\'s competence because Noor missed the bug."')
        self.assertEqual(result.payload['status'], 'SYSTEM_INSUFFICIENT')
        w, result = self.prepare()
        with self.assertRaisesRegex(ValueError, 'budget'):
            result.messages(w, max_chars=1000)


if __name__ == '__main__':
    unittest.main()
