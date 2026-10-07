"""The A02 amendment cannot absorb unrelated code or rewrite prior evidence."""
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.development_explicit_citation_amendment import HISTORICAL_PINS
from scripts.development_entry_readiness_amendment import validate_current


class ScopeAmendmentTests(unittest.TestCase):
    def test_prior_evidence_and_both_scope_fixture_hashes_are_pinned(self):
        self.assertTrue(validate_current())
        self.assertEqual(len(HISTORICAL_PINS), 161)
        original = Path.read_bytes
        for target in ('reports/HCL_B04_COPY_REFERENCE_AMENDMENT.json',
                       'eval/a02_scope_proposal_v1.json',
                       'eval/a02_scope_boundary_review_v1.json'):
            with self.subTest(target=target):
                def drift(path):
                    value = original(path)
                    return value + b' ' if str(path) == target else value
                with patch.object(Path, 'read_bytes', drift):
                    with self.assertRaisesRegex(ValueError, 'historical amendment'):
                        validate_current()

    def test_unrelated_anchor_and_b04_changes_cannot_enter_scope_amendment(self):
        original = Path.read_bytes
        for target, before, after, error in (
            ('hcl/cognition/semantic.py', b'def _anchor(source, proposal):',
             b'def _anchor(source, proposal):\n    # Unreviewed anchor edit', 'outside reviewed scope'),
            ('hcl/cognition/report_provenance.py', b'"""', b'"""Unreviewed change. ', 'unrelated runtime'),
        ):
            with self.subTest(target=target):
                def drift(path):
                    value = original(path)
                    return value.replace(before, after, 1) if str(path) == target else value
                with patch.object(Path, 'read_bytes', drift):
                    with self.assertRaisesRegex(ValueError, error):
                        validate_current()
        with self.assertRaisesRegex(ValueError, 'amendment drift'):
            validate_current(current_digest='0' * 64)


if __name__ == '__main__':
    unittest.main()
