"""V4 default input reaches full long text without consuming outcomes."""
import json
from pathlib import Path
import tempfile
import unittest

from scripts.i02_long_source_default_coverage import audit
from scripts.i02_runtime_amendment_v4 import validate_current
from scripts.serious_eval_contract import runtime_digest


RECEIPT = json.loads(Path('reports/HCL_I02_LONG_SOURCE_DEFAULT_COVERAGE_V4.json').read_text())


class LongSourceDefaultCoverageTests(unittest.TestCase):
    def test_complete_development_coverage_receipt(self):
        self.assertTrue(validate_current())
        self.assertEqual(RECEIPT['runtime_sha256'], runtime_digest())
        self.assertEqual(RECEIPT['complete_source_count'], 25)
        self.assertEqual(len({r['passage_id'] for r in RECEIPT['rows']}), 25)
        self.assertTrue(all(r['full_source_present'] and 16000 < r['source_chars'] < 48000
                            for r in RECEIPT['rows']))
        self.assertEqual(sum(r['candidate_count'] == 0 for r in RECEIPT['rows']), 6)
        self.assertFalse(RECEIPT['specialized_cognition_treatment'])
        self.assertFalse(RECEIPT['confirmation_qualified'])
        self.assertEqual(RECEIPT['provider_calls'], 0)
        self.assertNotIn('source_text', json.dumps(RECEIPT))
        self.assertNotIn('gold', json.dumps(RECEIPT))

    def test_unpinned_dataset_is_refused_before_any_input(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'dataset.jsonl'
            path.write_text('{"document":"invented"}\n')
            with self.assertRaisesRegex(ValueError, 'bytes changed'):
                audit(path)


if __name__ == '__main__':
    unittest.main()
