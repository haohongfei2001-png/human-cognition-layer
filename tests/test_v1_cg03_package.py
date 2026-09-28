"""CG03-E provider-free package and treatment-presence checks."""
import json
import unittest

from scripts.cg03_external_package import (PACKAGE, QUESTION, STATES, RESULTS,
    build_package, score_answer)


class FrozenCG03Package(unittest.TestCase):
    def test_exact_frozen_package_and_fair_five_arm_inputs(self):
        frozen = json.loads(PACKAGE.read_text())
        self.assertEqual(frozen, build_package())
        self.assertEqual(frozen['arms'], ['C', 'P', 'G', 'H', 'H-new'])
        self.assertEqual(len(frozen['cases']), 4)
        self.assertFalse(frozen['execution_authorized'])
        self.assertEqual(frozen['provider_calls_executed'], 0)
        self.assertEqual(frozen['maximum_provider_calls_if_separately_authorized'], 20)
        self.assertEqual(frozen['retries_if_authorized'], 0)
        self.assertEqual(frozen['model'], 'deepseek-v4-pro')
        self.assertEqual(frozen['provider_request']['thinking'], {'type': 'disabled'})
        self.assertLess(frozen['estimated_worst_case_usd_at_repository_frozen_rate'],
                        frozen['proposed_new_hard_cap_usd'])
        self.assertEqual(frozen['historical_budget_transfer_usd'], 0)
        self.assertEqual(frozen['evidence_class'],
                         'HCL_AUTHORED_SYNTHETIC_DEVELOPMENT_ONLY')
        self.assertEqual(len(set(case['case_id'] for case in frozen['cases'])), 4)
        for case in frozen['cases']:
            self.assertTrue(all(case['preflight'].values()), case['case_id'])
            messages = case['messages']
            self.assertEqual(set(messages), set(frozen['arms']))
            self.assertIn(QUESTION, messages['C'][-1]['content'])
            self.assertIn(QUESTION, messages['P'][-1]['content'])
            self.assertIn(QUESTION, messages['G'][-1]['content'])
            self.assertIn(QUESTION, messages['H'][-1]['content'])
            self.assertIn(QUESTION, messages['H-new'][-1]['content'])
            self.assertEqual(messages['H'][0], messages['H-new'][0])
            self.assertEqual(case['preparation_receipt']['extraction_provider_calls'], 0)
            for factor in ('causal_contribution', 'knowledge', 'foreseeability',
                           'control', 'stated_intention'):
                self.assertIn(case['gold'][factor], STATES)
            self.assertIn(case['gold']['premise_result'], RESULTS)
            self.assertFalse(case['gold']['unsupported_moral_claim'])
            self.assertTrue(score_answer(case, json.dumps(case['gold']))[
                            'all_fields_correct'])

    def test_scorer_rejects_extra_claim_or_wrong_enum(self):
        case = build_package()['cases'][0]
        extra = dict(case['gold'], broad_moral_verdict=True)
        self.assertFalse(score_answer(case, json.dumps(extra))['valid'])
        wrong = dict(case['gold'], control='MORALLY_RESPONSIBLE')
        self.assertFalse(score_answer(case, json.dumps(wrong))['all_fields_correct'])
        self.assertFalse(score_answer(case, 'not json')['valid'])


if __name__ == '__main__':
    unittest.main()
