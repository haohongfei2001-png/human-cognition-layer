"""Provider-free treatment-presence and frozen package assertions."""
import json
import unittest

from scripts.cg02_external_package import PACKAGE, build_package, score_answer


class CG02ExternalPackageTests(unittest.TestCase):
    def test_every_case_exercises_checker_and_frozen_inputs_match(self):
        built = build_package()
        self.assertEqual(json.loads(PACKAGE.read_text()), built)
        self.assertEqual(len(built['cases']), 4)
        self.assertEqual(built['maximum_provider_calls'], 20)
        self.assertFalse(built['execution_authorized'])
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
