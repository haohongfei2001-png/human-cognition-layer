"""Residual claim review supplements, never changes, frozen source-first scores."""

import copy
import unittest

from scripts.i02_residual_claim_audit import audit_residual_claims
from tests.test_v1_i02_semantic_score import answer, case, review


def residual(claims=None):
    return {'schema': 'hcl-i02-residual-claim-audit-v1',
        'case_id': 'synthetic-garden', 'opaque_output_id': 'opaque-001',
        'coverage_attestation': True, 'claims': [] if claims is None else claims}


def claim(excerpt, judgment='UNSUPPORTED', kind='OTHER', quotes=None):
    return {'excerpt': excerpt, 'judgment': judgment, 'kind': kind,
        'rationale': 'Audited against the entire authorized source.',
        'source_quotes': [] if quotes is None else quotes}


class ResidualAuditTests(unittest.TestCase):
    def test_positive_full_answer_review_preserves_historical_score(self):
        output = answer()
        row = claim('Ari says she wants to make the garden safe.', 'SUPPORTED',
            quotes=[{'source_id': 'story',
                'quote': 'Ari says she wants to make the garden safe.'}])
        result = audit_residual_claims(case(), output, review(), residual([row]))
        self.assertEqual((result['source_first_score']['earned'],
            result['source_first_score']['possible']), (11, 11))
        self.assertTrue(result['eligible'])
        self.assertFalse(result['full_answer_semantics_qualified'])

    def test_extra_unsupported_intent_defeats_perfect_obligation_score(self):
        output = answer(answer()['answer'] + ' Ari secretly planned the injury.')
        result = audit_residual_claims(case(), output, review(),
            residual([claim('Ari secretly planned the injury.',
                kind='INFERENCE_BOUNDARY')]))
        self.assertEqual(result['source_first_score']['semantic_fraction'], 1)
        self.assertFalse(result['eligible'])
        self.assertEqual(result['severe_unsupported_excerpts'],
            ['Ari secretly planned the injury.'])

    def test_unresolved_severity_and_fake_evidence_fail_closed(self):
        output = answer(answer()['answer'] + ' The fence was illegal.')
        row = claim('The fence was illegal.', 'UNRESOLVED', 'NORMATIVE_PREMISE')
        result = audit_residual_claims(case(), output, review(), residual([row]))
        self.assertFalse(result['eligible'])
        fake = claim('The fence was illegal.', 'SUPPORTED',
            'NORMATIVE_PREMISE', [{'source_id': 'story', 'quote': 'illegal'}])
        with self.assertRaisesRegex(ValueError, 'exact authorized source'):
            audit_residual_claims(case(), output, review(), residual([fake]))

    def test_nonsevere_unsupported_claim_also_prevents_eligibility(self):
        output = answer(answer()['answer'] + ' The garden is in Paris.')
        result = audit_residual_claims(case(), output, review(),
            residual([claim('The garden is in Paris.')]))
        self.assertFalse(result['eligible'])
        self.assertEqual(result['severe_unsupported_excerpts'], [])

    def test_identity_coverage_excerpt_and_duplicate_guards(self):
        output = answer()
        row = claim('Bo reports a community rule.')
        for mutation in ('coverage', 'identity', 'excerpt', 'duplicate'):
            audit = residual([copy.deepcopy(row)])
            if mutation == 'coverage':
                audit['coverage_attestation'] = False
            elif mutation == 'identity':
                audit['opaque_output_id'] = 'another-output'
            elif mutation == 'excerpt':
                audit['claims'][0]['excerpt'] = 'Invented output sentence.'
            else:
                audit['claims'].append(copy.deepcopy(row))
            with self.assertRaises(ValueError):
                audit_residual_claims(case(), output, review(), audit)


if __name__ == '__main__':
    unittest.main()
