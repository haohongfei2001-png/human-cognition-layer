"""The exposed native input cannot be paid-scored as a treated H arm."""
import json
import unittest
from pathlib import Path

from scripts.i02_native_treatment_preflight import require_treatment


RECEIPT = json.loads(Path('reports/HCL_I02_MUSR_NATIVE_TREATMENT_PREFLIGHT.json').read_text())


class NativeTreatmentTests(unittest.TestCase):
    def test_recorded_external_calibration_entry_has_no_cognition_treatment(self):
        self.assertEqual(RECEIPT['disposition'], 'FAIL_TREATMENT_ABSENT_NO_PAID_COMPARISON')
        self.assertEqual(RECEIPT['provider_calls'], 0)
        self.assertEqual(RECEIPT['selected_capabilities'], [])
        self.assertFalse(RECEIPT['cognition_context_present'])
        self.assertTrue(RECEIPT['source_and_question_preserved_in_final_input'])
        with self.assertRaisesRegex(ValueError, 'no paid comparison'):
            require_treatment(RECEIPT)

    def test_a_treated_case_still_cannot_use_native_gold_or_provider_preflight(self):
        row = dict(RECEIPT, specialized_treatment_present=True,
            cognition_context_present=True, native_gold_used=True)
        with self.assertRaisesRegex(ValueError, 'no paid comparison'):
            require_treatment(row)
        row['native_gold_used'] = False
        row['provider_calls'] = 1
        with self.assertRaisesRegex(ValueError, 'no paid comparison'):
            require_treatment(row)
        row['provider_calls'] = 0
        self.assertTrue(require_treatment(row))


if __name__ == '__main__':
    unittest.main()
