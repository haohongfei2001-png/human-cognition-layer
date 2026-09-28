"""Provider-free treatment-presence and frozen package assertions."""
import json
import unittest

from scripts.cg02_external_package import PACKAGE, build_package, score_answer
from scripts.run_cg02_external_once import load_frozen_package


class CG02ExternalPackageTests(unittest.TestCase):
    def test_every_case_exercises_checker_and_frozen_inputs_match(self):
        built = build_package()
        self.assertEqual(json.loads(PACKAGE.read_text()), built)
        self.assertEqual(len(built['cases']), 4)
        self.assertEqual(built['maximum_provider_calls'], 20)
        self.assertFalse(built['execution_authorized'])
        self.assertEqual(built['provider'], 'deepseek')
        self.assertEqual(built['actions_secret_name'], 'DEEPSEEK_API_KEY')
        self.assertEqual(built['model'], 'deepseek-v4-pro')
        self.assertEqual(built['model_version'], 'DeepSeek-V4-Pro-0813')
        self.assertEqual(built['provider_request']['thinking'], {'type': 'disabled'})
        self.assertEqual(built['provider_request']['response_format'], {'type': 'json_object'})
        self.assertEqual(built['estimated_worst_case_usd'], 0.2517504)
        self.assertEqual(built['proposed_hard_cap_usd'], 0.30)
        self.assertLessEqual(
            built['estimated_worst_case_usd'],
            built['proposed_hard_cap_usd'],
        )
        self.assertEqual(load_frozen_package(), built)
        for case in built['cases']:
            self.assertTrue(all(case['preflight'].values()), case['case_id'])
            self.assertNotEqual(case['messages']['H'], case['messages']['H-new'])
            self.assertEqual(case['preparation_receipt']['extraction_provider_calls'], 0)

    def test_strict_score_accepts_gold_and_rejects_invalid_or_moral_claim(self):
        case = build_package()['cases'][0]
        self.assertTrue(score_answer(case, json.dumps(case['gold']))['all_fields_correct'])
        self.assertFalse(score_answer(case, 'not json')['valid'])
        wrong = dict(case['gold'], unsupported_moral_claim=True)
        self.assertFalse(score_answer(case, json.dumps(wrong))['all_fields_correct'])


if __name__ == '__main__':
    unittest.main()
