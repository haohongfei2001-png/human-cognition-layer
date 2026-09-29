"""G-ARCH entry repair and one-shot package stay provider-free in CI."""
import json
import unittest

from scripts.run_g_arch_entry_once import build_package, load_package, preflight


class GArchEntryTests(unittest.TestCase):
    def test_package_preflight_replays_actual_failed_response_without_call(self):
        package = load_package()
        receipt = preflight(package)
        self.assertEqual(receipt['status'], 'PASS_PROVIDER_FREE')
        self.assertEqual(receipt['provider_calls'], 0)
        self.assertEqual(len(receipt['safe_unique_source_offset_repairs']), 5)
        self.assertEqual(receipt['live_entry'], 'NOT_YET_VERIFIED')
        self.assertEqual(receipt['historical_run'], 'FAILED_CLOSED_NO_NEW_CALL')
        self.assertEqual(receipt['historical_actual_response_replay']['cognition_state']['role_status'],
            'REPORTED_OCCUPANT')

    def test_bound_budget_and_closed_old_grant(self):
        package = build_package()
        self.assertEqual(package['maximum_provider_calls'], 2)
        self.assertEqual(package['budget_cap_usd'], 0.04)
        self.assertEqual(package['provider_request']['max_retries'], 0)
        self.assertFalse(package['historical_budget_transfer'])
        self.assertEqual(package['model'], 'deepseek-flash')
        self.assertEqual(package['longmemeval'], 'SEALED_NOT_ACCESSED')


if __name__ == '__main__':
    unittest.main()
