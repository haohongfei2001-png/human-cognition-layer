"""G-HC gate checks are cross-operation behavior, not just package labels."""
import unittest

from scripts.witness_g_hc import witness


class GHCReadinessTests(unittest.TestCase):
    def test_source_correction_propagates_only_relevant_paths(self):
        row = witness()
        self.assertEqual(row['before']['focal_choice_argument']['premise_checks'][0]['status'],
                         'REPORTED_FACT_NOT_WORLD_VERIFIED')
        self.assertEqual(row['after']['focal_choice_argument']['premise_checks'][0]['status'],
                         'UNRESOLVED_PREMISE')
        self.assertEqual(row['before']['concept']['relations'], row['after']['concept']['relations'])
        self.assertEqual(row['before']['unrelated_work_argument']['premise_checks'][0]['status'],
                         row['after']['unrelated_work_argument']['premise_checks'][0]['status'])
        self.assertNotEqual(row['before']['unrelated_work_argument']['source']['version'],
                            row['after']['unrelated_work_argument']['source']['version'])
        self.assertTrue(row['checks']['access_denied'])
        self.assertTrue(row['checks']['oversize_refused'])


if __name__ == '__main__':
    unittest.main()
