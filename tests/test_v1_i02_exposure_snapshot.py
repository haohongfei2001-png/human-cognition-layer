import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.i02_exposure_snapshot import audit_snapshot
from scripts.i02_source_qualification_v5 import require_qualified_confirmation_source_v5


SOURCE = ('A researcher told a colleague about the warning before the meeting '
          'but the director learned about it only after the meeting ended.')


def git(repo, *args):
    return subprocess.run(['git', '-C', str(repo), *args], check=True,
                          capture_output=True).stdout.decode().strip()


class ExposureSnapshotTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name)
        git(self.repo, 'init', '-q')
        git(self.repo, 'config', 'user.name', 'I02 Test')
        git(self.repo, 'config', 'user.email', 'i02@example.invalid')
        (self.repo / 'eval' / 'longmemeval').mkdir(parents=True)
        (self.repo / 'eval' / 'longmemeval' / 'sealed.txt').write_text(SOURCE)
        (self.repo / 'ordinary.txt').write_text('An unrelated ordinary document.')
        git(self.repo, 'add', '.')
        git(self.repo, 'commit', '-qm', 'initial')
        self.initial = git(self.repo, 'rev-parse', 'HEAD')

    def test_sealed_path_is_never_used_as_an_exposure_match(self):
        receipt = audit_snapshot(self.repo, self.initial, SOURCE)
        self.assertEqual(receipt['status'], 'TEXT_SNAPSHOT_NO_MATCH')
        self.assertEqual(receipt['sealed_paths_not_opened'], 1)
        self.assertEqual(receipt['matches'], [])
        self.assertFalse(receipt['confirmation_qualified'])

    def test_exact_and_partial_overlap_are_detected_at_pinned_commit(self):
        (self.repo / 'copy.txt').write_text('Preface. ' + SOURCE + ' Epilogue.')
        (self.repo / 'exact.txt').write_text(SOURCE)
        git(self.repo, 'add', '.')
        git(self.repo, 'commit', '-qm', 'expose source')
        current = git(self.repo, 'rev-parse', 'HEAD')
        old = audit_snapshot(self.repo, self.initial, SOURCE)
        new = audit_snapshot(self.repo, current, SOURCE)
        self.assertEqual(old['status'], 'TEXT_SNAPSHOT_NO_MATCH')
        self.assertEqual(new['status'], 'REVIEW_REQUIRED')
        self.assertEqual([row['path'] for row in new['matches']],
                         ['copy.txt', 'exact.txt'])
        self.assertFalse(new['matches'][0]['exact_file_match'])
        self.assertTrue(new['matches'][1]['exact_file_match'])

    def test_too_short_source_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'fewer than 12 words'):
            audit_snapshot(self.repo, self.initial, 'too short')

    def test_v5_gate_checks_snapshot_before_older_source_assertions(self):
        (self.repo / 'copy.txt').write_text(SOURCE)
        git(self.repo, 'add', '.')
        git(self.repo, 'commit', '-qm', 'expose source')
        current = git(self.repo, 'rev-parse', 'HEAD')
        with patch('scripts.i02_source_qualification_v5.'
                   'require_qualified_confirmation_source_v4') as older:
            with self.assertRaisesRegex(ValueError, 'snapshot exposure'):
                require_qualified_confirmation_source_v5({}, {'source_text': SOURCE},
                                                         {}, self.repo, current)
            older.assert_not_called()
            receipt = require_qualified_confirmation_source_v5(
                {}, {'source_text': SOURCE}, {}, self.repo, self.initial)
            self.assertEqual(receipt['repository_commit'], self.initial)
            older.assert_called_once()


if __name__ == '__main__':
    unittest.main()
