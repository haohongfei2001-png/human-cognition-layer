"""The one-use EPC calibration cannot drift into a different experiment."""
import json
import unittest
from unittest.mock import patch

from scripts.run_i02_epc_cpg_v5_once import (
    CAP_USD, GLOBAL_OBLIGATIONS, OBLIGATIONS, PACKAGE, QUESTION_SHA256, SOURCE_SHA256,
    build_package, load_package)


class EpcCpgV5FreezeTests(unittest.TestCase):
    def test_current_package_pins_one_development_case_and_execution(self):
        package = json.loads(PACKAGE.read_text())
        with patch('scripts.run_i02_epc_cpg_v5_once.runtime_digest',
                   return_value=package['hcl_runtime_sha256']):
            self.assertEqual(package, build_package())
        # Consumed v5 remains pinned to its historical runtime; it must not be
        # silently executable against a later I02 runtime amendment.
        with self.assertRaisesRegex(ValueError, 'drift'):
            load_package()
        self.assertEqual(package['source_sha256'], SOURCE_SHA256)
        self.assertEqual(package['question_sha256'], QUESTION_SHA256)
        self.assertEqual(package['source_first_obligation_anchors'], list(OBLIGATIONS))
        self.assertEqual(package['global_source_first_obligations'],
                         list(GLOBAL_OBLIGATIONS))
        self.assertEqual(package['phases'], ['C', 'P', 'G_map', 'G_final'])
        self.assertEqual(package['maximum_provider_calls'], 4)
        self.assertEqual(package['budget_cap_usd'], CAP_USD)
        self.assertEqual(package['retries'], 0)
        self.assertEqual(package['h_arm_calls'], 0)
        self.assertEqual(package['confirmation_items_inspected'], 0)
        self.assertFalse(package['historical_budget_transfer'])
        self.assertEqual(package['longmemeval'], 'SEALED_NOT_ACCESSED')


if __name__ == '__main__':
    unittest.main()
