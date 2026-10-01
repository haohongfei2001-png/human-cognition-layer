"""Only invented text: full-ID protection precedes rename/copy content reads."""
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from scripts import i02_exposure_history_v2 as history

SOURCE = ' '.join('inventedprotectedword' + str(i) for i in range(20))


def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args], text=True,
                                   stderr=subprocess.DEVNULL).strip()


class FullSealedObjectIdTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        git(self.root, 'init', '-q')
        git(self.root, 'config', 'user.email', 'synthetic-test@example.invalid')
        git(self.root, 'config', 'user.name', 'Synthetic Test')
        git(self.root, 'config', 'core.abbrev', '4')
        (self.root / 'LongMemEval-synthetic-only.txt').write_text(SOURCE)
        git(self.root, 'add', '.')
        git(self.root, 'commit', '-qm', 'invented fixture')
        self.oid = git(self.root, 'rev-parse', 'HEAD:LongMemEval-synthetic-only.txt')

    def assert_unopened(self):
        original = history._git
        def guarded(repo, *args, **kwargs):
            if args == ('cat-file', 'blob', self.oid):
                self.fail('protected synthetic object must be skipped before reading content')
            return original(repo, *args, **kwargs)
        with patch.object(history, '_git', side_effect=guarded):
            receipt = history.audit_history(self.root, SOURCE)
        self.assertEqual(receipt['matches'], [])
        self.assertEqual(receipt['unique_utf8_blobs_scanned'], 0)
        self.assertEqual(receipt['sealed_blob_ids_not_opened'], 1)

    def test_full_object_id_is_retained_despite_default_abbreviation(self):
        ids = history._sealed_object_ids(self.root)
        self.assertIn(self.oid, ids)
        self.assertNotIn(self.oid[:4], ids)
        self.assert_unopened()

    def test_renamed_protected_object_is_not_opened_under_ordinary_path(self):
        git(self.root, 'mv', 'LongMemEval-synthetic-only.txt', 'ordinary-synthetic.txt')
        git(self.root, 'commit', '-qm', 'rename invented fixture')
        self.assert_unopened()

    def test_copied_protected_object_is_not_opened_under_ordinary_path(self):
        (self.root / '000-ordinary-copy.txt').write_text(SOURCE)
        git(self.root, 'add', '.')
        git(self.root, 'commit', '-qm', 'copy invented fixture')
        self.assert_unopened()


if __name__ == '__main__':
    unittest.main()
