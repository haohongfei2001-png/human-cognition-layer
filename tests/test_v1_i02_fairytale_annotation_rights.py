"""Publisher provenance does not release a source or an unreviewed question."""

import hashlib
import json
import unittest
from unittest.mock import patch

from scripts.i02_fairytale_annotation_rights import audit_annotation_rights


README = (b'Questions and answers developed by educational experts. '
          b'Education experts labeled QA-pairs.')
LICENSE = b'Apache License\nVersion 2.0, January 2004\n'


def fixture(readme=README, license_text=LICENSE, supplied_license=None):
    package = {'author_team_commit': 'a' * 40,
               'author_team_license_sha256': hashlib.sha256(license_text).hexdigest()}
    blob = lambda raw: hashlib.sha1(f'blob {len(raw)}\0'.encode() + raw).hexdigest()
    with patch('scripts.i02_fairytale_annotation_rights.PACKAGE') as path, patch(
            'scripts.i02_fairytale_annotation_rights.LICENSE') as license_copy, patch(
            'scripts.i02_fairytale_annotation_rights.validate_metadata_only'), patch(
            'scripts.i02_fairytale_annotation_rights.README_SHA256',
            hashlib.sha256(readme).hexdigest()), patch(
            'scripts.i02_fairytale_annotation_rights.README_BLOB', blob(readme)), patch(
            'scripts.i02_fairytale_annotation_rights.LICENSE_BLOB', blob(license_text)):
        path.read_text.return_value = json.dumps(package)
        license_copy.read_bytes.return_value = license_text
        return audit_annotation_rights(readme,
            license_text if supplied_license is None else supplied_license)


class AnnotationRightsTests(unittest.TestCase):
    def test_authorship_and_license_evidence_does_not_qualify_item(self):
        receipt = fixture()
        self.assertTrue(receipt['expert_authored_questions_reported_by_publisher'])
        self.assertTrue(receipt['root_apache_2_license_pinned'])
        self.assertFalse(receipt['model_input_allowed'])
        self.assertFalse(receipt['confirmation_qualified'])
        self.assertEqual(receipt['provider_calls'], 0)
        self.assertNotIn('Questions and answers', str(receipt))

    def test_wrong_readme_or_missing_authorship_fails(self):
        with self.assertRaisesRegex(ValueError, 'README differs'):
            audit_annotation_rights(b'changed', LICENSE)
        with self.assertRaisesRegex(ValueError, 'authorship statement missing'):
            fixture(b'Other metadata only.')

    def test_license_drift_fails(self):
        with self.assertRaisesRegex(ValueError, 'LICENSE differs'):
            fixture(supplied_license=b'changed')


if __name__ == '__main__':
    unittest.main()
