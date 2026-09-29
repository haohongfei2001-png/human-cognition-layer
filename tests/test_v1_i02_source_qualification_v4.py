"""Mirror-safe exact-content exposure guard, preserving historical v3."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from scripts.i02_source_qualification_v3 import require_qualified_confirmation_source
from scripts.i02_source_qualification_v4 import (
    load_fingerprints, require_qualified_confirmation_source_v4)
from tests.test_v1_i02_source_qualification_v3 import audit, case


class SourceQualificationV4Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.freeze = json.loads(Path(
            'reports/HCL_I01_EVALUATION_FREEZE.json').read_text())

    def test_positive_synthetic_composition_and_historical_guard(self):
        self.assertEqual(len(load_fingerprints()['exposed']), 1)
        self.assertTrue(require_qualified_confirmation_source_v4(
            self.freeze, case(), audit()))
        blocked = case()
        blocked['source_url'] = (
            'https://kpu.pressbooks.pub/businesscomms/chapter/case-conflict-management/')
        blocked_audit = audit()
        blocked_audit['source_url'] = blocked['source_url']
        with self.assertRaisesRegex(ValueError, 'screened source system'):
            require_qualified_confirmation_source_v4(
                self.freeze, blocked, blocked_audit)

    def test_exact_exposed_content_rejected_under_mirror_and_renamed_ids(self):
        source = json.loads(Path(
            'reports/HCL_I02_KPU_CONFLICT_DEVELOPMENT_SOURCE.json').read_text())
        mirrored = case()
        mirrored['source_text'] = source['source_text']
        mirrored['source_url'] = 'https://example.org/new-publisher-mirror'
        mirrored['source_group_id'] = 'newly-named-source-group'
        for arm_input in mirrored['arm_inputs'].values():
            arm_input['source_text'] = mirrored['source_text']
        mirrored_audit = audit()
        mirrored_audit['source_url'] = mirrored['source_url']
        mirrored_audit['source_sha256'] = hashlib.sha256(
            mirrored['source_text'].encode()).hexdigest()
        # v3 recognizes neither this URL nor these invented lineage IDs.
        self.assertTrue(require_qualified_confirmation_source(
            self.freeze, mirrored, mirrored_audit))
        with self.assertRaisesRegex(ValueError, 'exact exposed source content'):
            require_qualified_confirmation_source_v4(
                self.freeze, mirrored, mirrored_audit)

    def test_fingerprint_receipt_cannot_be_silently_relabelled(self):
        manifest = load_fingerprints()
        manifest['exposed'][0]['source_text_sha256'] = '0' * 64
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'manifest.json'
            path.write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, 'exposure identity drift'):
                load_fingerprints(path)
        with self.assertRaises(TypeError):
            require_qualified_confirmation_source_v4(
                self.freeze, case(), audit(), fingerprints={'exposed': []})


if __name__ == '__main__':
    unittest.main()
