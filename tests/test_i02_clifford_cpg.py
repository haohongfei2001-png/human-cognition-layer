"""Archived calibration checks execute under their actual certified runtime only."""
import unittest, tempfile, json
from pathlib import Path
from unittest.mock import patch
from scripts.i02_clifford_certified_replay import replay_provider_free, validate_archive

class CliffordCertifiedReplayTests(unittest.TestCase):
    def test_exact_historical_runtime_and_provider_free_preflight(self):
        receipt = replay_provider_free(tests=True)
        self.assertFalse(receipt['latest_runtime_substituted'])
        self.assertEqual(receipt['provider_calls'], 0)
        self.assertEqual(receipt['hcl_runtime_sha256'], 'c7034fdc97d606867bf6688cc005837033b357155cd649ed187f41a32509579b')
        self.assertFalse(receipt['outputs_rescored'])

    def test_certificate_and_archive_changes_fail_before_replay(self):
        from scripts import i02_clifford_certified_replay as replay
        with tempfile.TemporaryDirectory() as temp:
            bad = Path(temp) / 'bad.json'
            bad.write_text(replay.CERTIFICATE.read_text() + ' ')
            with patch.object(replay, 'CERTIFICATE', bad):
                with self.assertRaisesRegex(ValueError, 'certificate drift'): validate_archive()
            bad.write_bytes(replay.ARCHIVE.read_bytes() + b'x')
            with patch.object(replay, 'ARCHIVE', bad):
                with self.assertRaisesRegex(ValueError, 'archive'): validate_archive()

    def test_reopened_grant_refuses_before_frozen_code(self):
        from scripts import i02_clifford_certified_replay as replay
        with tempfile.TemporaryDirectory() as temp:
            bad = Path(temp) / 'grant.json'
            grant = json.loads(replay.GRANT.read_text())
            grant['status'] = 'READY'; bad.write_text(json.dumps(grant))
            with patch.object(replay, 'GRANT', bad), patch.object(replay.subprocess, 'run') as invoke:
                with self.assertRaisesRegex(ValueError, 'closed grant'): replay_provider_free()
                invoke.assert_not_called()

if __name__ == '__main__': unittest.main()
