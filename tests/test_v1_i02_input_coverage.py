"""I02 complete-source coverage and negative outcome cannot be hidden."""
import json
import unittest
from pathlib import Path

from scripts.i02_input_coverage import audit_ordinary_input, require_recorded_outcome
from scripts.serious_eval_contract import runtime_digest


RECEIPT = json.loads(Path('reports/HCL_I02_LONG_INPUT_COVERAGE.json').read_text())


class InputCoverageTests(unittest.TestCase):
    def test_short_source_keeps_exact_complete_input(self):
        source = 'Mara said the plan changed. The narrator reports no private motive.'
        result = audit_ordinary_input('What happened?', 'synthetic-source', source)
        self.assertEqual(result['h_entry'], 'ACCEPTED_PROVIDER_FREE')
        self.assertTrue(result['h_complete_source_in_final_input'])
        self.assertTrue(require_recorded_outcome(result))

    def test_long_source_rejection_is_recorded_as_outcome(self):
        source = ('An ordinary source sentence. ' * 700).strip()
        self.assertGreater(len(source), 16000)
        self.assertLess(len(source), 64000)
        result = audit_ordinary_input('What happened?', 'synthetic-source', source)
        self.assertEqual(result['h_entry'], 'REJECTED_OBSERVED_OUTCOME')
        self.assertEqual(result['h_failure_reason'], 'bounded narrative text required')
        self.assertTrue(result['c_p_g_complete_source'])
        self.assertTrue(require_recorded_outcome(result))
        with self.assertRaisesRegex(ValueError, 'coverage outcome'):
            require_recorded_outcome(dict(result, h_entry='ACCEPTED_PROVIDER_FREE'))

    def test_pinned_dev_metadata_is_long_without_semantic_promotion(self):
        self.assertEqual(RECEIPT['dataset_file_sha256'],
            'e9cbb1daff74b70a6cd15641ba2f602a925761759200a17c9225aca90018a42b')
        self.assertEqual(len(RECEIPT['dev_source_lengths']), 25)
        self.assertTrue(all(16000 < length < 64000
                            for length in RECEIPT['dev_source_lengths']))
        self.assertEqual(RECEIPT['hcl_runtime_sha256'], runtime_digest())
        self.assertEqual(RECEIPT['qualified_cases'], 0)
        self.assertEqual(RECEIPT['provider_calls'], 0)


if __name__ == '__main__':
    unittest.main()
