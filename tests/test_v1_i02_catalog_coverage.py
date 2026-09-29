"""Restricted coverage cannot bypass the frozen I01 case boundary."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from scripts.serious_eval_catalog_coverage import audit_catalog_coverage
from scripts.serious_eval_contract import FAMILIES, validate_catalog
from tests.test_v1_i01_eval_contract import FREEZE, case


class CatalogCoverageTests(unittest.TestCase):
    def test_restricted_catalog_reports_observed_scope_without_maturity(self):
        items = [case(0, FAMILIES[0]), case(1, FAMILIES[1])]
        report = audit_catalog_coverage(FREEZE, items)
        self.assertEqual(report['case_count'], 2)
        self.assertEqual(report['task_families_present'], list(FAMILIES[:2]))
        self.assertEqual(report['task_families_missing'], list(FAMILIES[2:]))
        self.assertEqual(report['independent_writing_system_count'], 2)
        self.assertFalse(report['full_maturity_source_coverage'])
        self.assertFalse(report['provider_approved'])
        self.assertFalse(report['efficacy_claim_qualified'])
        with self.assertRaisesRegex(ValueError, 'prespecified task family'):
            validate_catalog(FREEZE, items)

    def test_full_scope_is_structural_only(self):
        report = audit_catalog_coverage(FREEZE,
            [case(i, family) for i, family in enumerate(FAMILIES)])
        self.assertTrue(report['full_maturity_source_coverage'])
        self.assertFalse(report['provider_approved'])
        self.assertFalse(report['efficacy_claim_qualified'])

    def test_restricted_catalog_rejects_unfairness_and_split_leakage(self):
        item = case(0, FAMILIES[0])
        item['arm_inputs']['H']['source_text'] = 'different'
        with self.assertRaisesRegex(ValueError, 'same question and source'):
            audit_catalog_coverage(FREEZE, [item])
        items = [case(0, FAMILIES[0]), case(3, FAMILIES[1], 'CALIBRATION')]
        with self.assertRaisesRegex(ValueError, 'writing_system_id crosses'):
            audit_catalog_coverage(FREEZE, items)

    def test_cli_reports_scope_without_echoing_source_or_approval(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'catalog.json'
            path.write_text(json.dumps([case(0, FAMILIES[0])]))
            cmd = [sys.executable, '-m', 'scripts.serious_eval_catalog_coverage',
                '--catalog', str(path)]
            result = subprocess.run(cmd, text=True, capture_output=True, check=True)
            report = json.loads(result.stdout)
            self.assertEqual(report['task_families_present'], [FAMILIES[0]])
            self.assertNotIn('Witness 0', result.stdout)
            self.assertFalse(report['provider_approved'])
            denied = subprocess.run(cmd + ['--require-full-coverage'],
                text=True, capture_output=True)
            self.assertNotEqual(denied.returncode, 0)
