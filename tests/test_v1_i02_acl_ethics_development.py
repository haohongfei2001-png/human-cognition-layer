"""ACL tutorial external-author development source and exposure boundary."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.i02_acl_ethics_development_preflight import audit
from scripts.i02_acl_ethics_exposure_overlay import (
    require_acl_development_input, require_confirmation_disjoint_acl_overlay,
    require_qualified_confirmation_source_v5)
from tests.test_v1_i02_source_qualification_v3 import audit as sample_audit, case


class AclEthicsDevelopmentTests(unittest.TestCase):
    def setUp(self):
        self.source = json.loads(Path(
            'reports/HCL_I02_ACL_ETHICS_DEVELOPMENT_SOURCE.json').read_text())

    def test_positive_source_first_ordinary_input_and_direct_h_boundary(self):
        result = audit()
        self.assertTrue(result['source_valid'])
        self.assertTrue(result['full_ordinary_input_equal_for_cpg'])
        self.assertTrue(result['g_final_original_source_present'])
        self.assertEqual(result['source_first_obligation_count'], 4)
        self.assertTrue(result['h_direct'])
        self.assertFalse(result['h_specialized_treatment_present'])
        self.assertFalse(result['h_hnew_calls_allowed'])
        self.assertFalse(result['independent_confirmation_qualified'])
        self.assertEqual(result['provider_calls'], 0)

    def test_negative_source_and_lineage_inference(self):
        candidate = dict(split='CONFIRMATION', source_text=self.source['source_text'],
            writing_system_id=self.source['source_system'],
            author_id='new-author-name', template_id='new-template-name',
            source_group_id='new-group-name')
        with self.assertRaisesRegex(ValueError, 'writing_system_id reuses'):
            require_confirmation_disjoint_acl_overlay(candidate)
        candidate['writing_system_id'] = 'new-system-name'
        with self.assertRaisesRegex(ValueError, 'source_text reuses'):
            require_confirmation_disjoint_acl_overlay(candidate)
        bad = dict(split='CALIBRATION', source_text=self.source['source_text'] + ' ',
            writing_system_id=self.source['source_system'],
            author_id='acl-eacl-2023-ethics-tutorial-organizers',
            template_id='acl-eacl-2023-synthetic-problematic-abstracts',
            source_group_id='127cf23ee554c575b5c35c94c4d5468f5f1abae14d7cb15195f31ca22e602bc1',
            source_license_status='VERIFIED_FOR_THIS_EVALUATION',
            source_access_status='AUTHORIZED_FOR_EVERY_ARM')
        with self.assertRaisesRegex(ValueError, 'not approved'):
            require_acl_development_input(bad)
        altered = dict(self.source, ordinary_question='What did the authors intend?')
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'source.json'
            path.write_text(json.dumps(altered))
            with patch('scripts.i02_acl_ethics_development_preflight.SOURCE', path):
                with self.assertRaisesRegex(ValueError, 'source drift'):
                    audit()

    def test_v5_composes_historical_and_new_exposure_without_old_receipt_edit(self):
        freeze = json.loads(Path('reports/HCL_I01_EVALUATION_FREEZE.json').read_text())
        self.assertTrue(require_qualified_confirmation_source_v5(
            freeze, case(), sample_audit()))
        bad = case()
        bad['writing_system_id'] = self.source['source_system']
        with self.assertRaisesRegex(ValueError, 'writing_system_id reuses ACL'):
            require_qualified_confirmation_source_v5(
                freeze, bad, sample_audit())


if __name__ == '__main__':
    unittest.main()
