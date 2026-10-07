"""Current code identity cannot reauthorize historical paid experiments."""
from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import development_final_context_amendment as amendment
from scripts import run_two_stage_once as historical


class FinalContextAmendmentTests(unittest.TestCase):
    def test_exact_current_runtime_and_only_reviewed_file_are_accepted(self):
        self.assertTrue(amendment.validate_current())
        self.assertEqual(set(amendment.REVIEWED_FILES), {'hcl/cognition/universal_entry.py'})
        self.assertTrue(amendment.validate_current(current_digest=amendment.CURRENT_RUNTIME))
        for wrong in ('0' * 64, amendment.PREVIOUS_RUNTIME, ''):
            with self.assertRaisesRegex(ValueError, 'amendment drift'):
                amendment.validate_current(current_digest=wrong)

    def test_runtime_mutation_and_missing_membership_cannot_be_covered_by_supplied_digest(self):
        original = Path.read_bytes
        for target in ('hcl/cognition/universal_entry.py', 'hcl/cognition/retained.py',
                       'hcl/cognition/deepseek_metered.py'):
            def changed(path):
                raw = original(path)
                return raw + b' ' if str(path) == target else raw
            with patch.object(Path, 'read_bytes', changed), self.assertRaisesRegex(ValueError, 'outside reviewed scope'):
                amendment.validate_current(current_digest=amendment.CURRENT_RUNTIME)
        rglob = Path.rglob
        with patch.object(Path, 'rglob', lambda path, pattern: (
                p for p in rglob(path, pattern) if str(p) != 'hcl/cognition/universal_entry.py')):
            with self.assertRaises(ValueError):
                amendment.validate_current()

    def test_history_manifest_and_every_consumed_artifact_are_pinned(self):
        original = Path.read_bytes
        for target in (str(amendment.PINS), *json.loads(amendment.PINS.read_text())['files_sha256']):
            def changed(path):
                raw = original(path)
                return raw + b' ' if str(path) == target else raw
            with self.subTest(target=target), patch.object(Path, 'read_bytes', changed):
                with self.assertRaisesRegex(ValueError, 'historical'):
                    amendment.validate_current()

    def test_new_runtime_refuses_both_closed_historical_packages_before_client_or_output(self):
        try:
            for stage in (1, 2):
                historical.configure(stage)
                package = json.loads(historical.PACKAGE.read_text())
                grant = json.loads(historical.GRANT.read_text())
                self.assertEqual(grant['status'], 'CLOSED_NO_TRANSFER_NO_RETRY')
                self.assertEqual(grant['remaining_authorized_calls'], 0)
                self.assertEqual(grant['remaining_authorized_cny'], '0')
                self.assertEqual(historical.RUNTIME, amendment.PREVIOUS_RUNTIME)
                self.assertNotEqual(historical.RUNTIME, amendment.CURRENT_RUNTIME)
                with tempfile.TemporaryDirectory() as directory:
                    destination = Path(directory) / 'must-not-exist'
                    with patch.object(historical, 'Port', side_effect=AssertionError('CLIENT_MUST_NOT_BE_CONSTRUCTED')):
                        with self.assertRaisesRegex(ValueError, '^RUNTIME_DRIFT$'):
                            historical.run(None, package, grant, destination,
                                clock=lambda: datetime(2026, 10, 6, 19, tzinfo=timezone.utc))
                    self.assertFalse(destination.exists())
        finally:
            historical.configure(1)


if __name__ == '__main__':
    unittest.main()
