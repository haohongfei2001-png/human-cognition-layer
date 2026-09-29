"""The completed G-ARCH entry receipt stays auditable without reopening its freeze."""
import json
import unittest

from pathlib import Path

from scripts.audit_g_arch_entry import audit


class GArchEntryTests(unittest.TestCase):
    def test_source_first_receipt_is_closed_and_anchored(self):
        receipt = audit()
        self.assertEqual(receipt['operational_input'], 'PASS_BOUNDED_AUTHORED_FUNCTIONAL_SMOKE')
        self.assertEqual(receipt['source_derived_offset_repairs'], 5)
        self.assertEqual(len(receipt['raw_extraction_anchors']), 6)
        self.assertTrue(receipt['final_model_input_equals_prepared_state'])
        self.assertEqual(receipt['historical_e03'], 'FAILED_CLOSED_UNCHANGED')
        self.assertEqual(receipt['authorization_remaining_usd'], 0)

    def test_bound_budget_and_closed_old_grant(self):
        package = json.loads(Path('reports/HCL_G_ARCH_ENTRY_PACKAGE.json').read_text())
        self.assertEqual(package['maximum_provider_calls'], 2)
        self.assertEqual(package['budget_cap_usd'], 0.04)
        self.assertEqual(package['provider_request']['max_retries'], 0)
        self.assertFalse(package['historical_budget_transfer'])
        self.assertEqual(package['model'], 'deepseek-flash')
        self.assertEqual(package['longmemeval'], 'SEALED_NOT_ACCESSED')


if __name__ == '__main__':
    unittest.main()
