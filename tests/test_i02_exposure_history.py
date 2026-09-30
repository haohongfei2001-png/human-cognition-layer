"""Historical exposure catches removed sources while sealed blobs stay unopened."""
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from scripts.i02_exposure_history import audit_history
from scripts.i02_source_qualification_v6 import require_qualified_confirmation_source_v6


SOURCE = ' '.join(f'independentword{i}' for i in range(20))


def git(root, *args):
    return subprocess.run(['git', '-C', str(root), *args], check=True,
                          capture_output=True, text=True).stdout.strip()


class HistoryExposureTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        git(self.root, 'init', '-q')
        git(self.root, 'config', 'user.email', 'history-test@example.invalid')
        git(self.root, 'config', 'user.name', 'History Test')

    def commit(self, name, text):
        (self.root / name).write_text(text)
        git(self.root, 'add', name)
        git(self.root, 'commit', '-q', '-m', name)

    def test_deleted_source_remains_a_history_match(self):
        self.commit('once.txt', SOURCE)
        git(self.root, 'rm', 'once.txt')
        git(self.root, 'commit', '-q', '-m', 'remove')
        receipt = audit_history(self.root, SOURCE)
        self.assertEqual(receipt['status'], 'REVIEW_REQUIRED')
        self.assertTrue(any(row['exact_blob_match'] for row in receipt['matches']))
        self.assertFalse(receipt['confirmation_qualified'])
        self.assertNotIn(SOURCE, str(receipt))

    def test_sealed_object_is_identified_from_metadata_and_skipped(self):
        self.commit('LongMemEval-sealed.txt', SOURCE)
        self.commit('ordinary.txt', ' '.join(f'otherword{i}' for i in range(20)))
        receipt = audit_history(self.root, SOURCE)
        self.assertEqual(receipt['status'], 'REACHABLE_HISTORY_NO_TEXT_MATCH')
        self.assertGreaterEqual(receipt['sealed_blob_ids_not_opened'], 1)
        self.assertEqual(receipt['matches'], [])
        self.assertEqual(receipt['longmemeval'], 'SEALED_NOT_ACCESSED')

    def test_revision_and_short_candidate_bounds(self):
        self.commit('ordinary.txt', ' '.join(f'otherword{i}' for i in range(20)))
        first = audit_history(self.root, SOURCE)
        self.commit('later.txt', SOURCE)
        second = audit_history(self.root, SOURCE)
        self.assertEqual(first['status'], 'REACHABLE_HISTORY_NO_TEXT_MATCH')
        self.assertEqual(second['status'], 'REVIEW_REQUIRED')
        self.assertNotEqual(first['checkout_head'], second['checkout_head'])
        with self.assertRaisesRegex(ValueError, 'fewer than 12 words'):
            audit_history(self.root, 'too short')

    def test_v6_refuses_deleted_exposure_before_older_qualification(self):
        self.commit('once.txt', SOURCE)
        old = git(self.root, 'rev-parse', 'HEAD')
        git(self.root, 'rm', 'once.txt')
        git(self.root, 'commit', '-q', '-m', 'remove')
        with patch('scripts.i02_source_qualification_v6.'
                   'require_qualified_confirmation_source_v5') as older:
            with self.assertRaisesRegex(ValueError, 'reachable Git history exposure'):
                require_qualified_confirmation_source_v6({}, {'source_text': SOURCE},
                                                        {}, self.root, 'HEAD')
            older.assert_not_called()
            with self.assertRaisesRegex(ValueError, 'current checkout HEAD'):
                require_qualified_confirmation_source_v6({}, {'source_text': SOURCE},
                                                        {}, self.root, old)
            older.assert_not_called()
            unseen = ' '.join(f'freshword{i}' for i in range(20))
            receipt = require_qualified_confirmation_source_v6(
                {}, {'source_text': unseen}, {}, self.root, 'HEAD')
            self.assertEqual(receipt['history']['status'],
                             'REACHABLE_HISTORY_NO_TEXT_MATCH')
            older.assert_called_once()


if __name__ == '__main__':
    unittest.main()
