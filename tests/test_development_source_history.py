"""Synthetic-only checks for the current full-ID zero-authority entry."""
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from scripts import development_source_history as entry
from scripts import i02_exposure_history_v3 as history

SOURCE = ' '.join('inventedcurrentword' + str(i) for i in range(20))
OTHER = ' '.join('unrelatedpublicword' + str(i) for i in range(20))


def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args], text=True,
                                   stderr=subprocess.DEVNULL).strip()


class DevelopmentSourceHistoryTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        git(self.root, 'init', '-q')
        git(self.root, 'config', 'user.email', 'synthetic-test@example.invalid')
        git(self.root, 'config', 'user.name', 'Synthetic Test')
        git(self.root, 'config', 'core.abbrev', '4')

    def commit(self, name, value):
        (self.root / name).write_text(value)
        git(self.root, 'add', '.')
        git(self.root, 'commit', '-qm', 'synthetic fixture')

    def test_renamed_sealed_blob_stays_unopened_through_current_entry(self):
        self.commit('LongMemEval-synthetic-only.txt', SOURCE)
        oid = git(self.root, 'rev-parse', 'HEAD:LongMemEval-synthetic-only.txt')
        git(self.root, 'mv', 'LongMemEval-synthetic-only.txt', 'ordinary.txt')
        git(self.root, 'commit', '-qm', 'synthetic rename')
        original = history._git
        def guarded(repo, *args, **kwargs):
            if args == ('cat-file', 'blob', oid):
                self.fail('protected synthetic blob must not be read')
            return original(repo, *args, **kwargs)
        with patch.object(history, '_git', side_effect=guarded):
            result = entry.screen_development_source(self.root, OTHER)
        self.assertEqual(result['history']['sealed_blob_ids_not_opened'], 1)
        self.assertEqual(result['history']['unique_utf8_blobs_scanned'], 0)
        self.assertTrue(result['history_clear'])
        self.assertNotIn(SOURCE, str(result))

    def test_clear_history_never_grants_rights_qualification_or_spending(self):
        self.commit('ordinary.txt', OTHER)
        result = entry.screen_development_source(self.root, SOURCE)
        self.assertTrue(result['history_clear'])
        for field in ('rights_verified', 'source_qualified', 'confirmation_qualified', 'live_execution_enabled'):
            self.assertIs(result[field], False)
        for field in ('provider_calls', 'maximum_authorized_calls', 'authorized_spend_usd'):
            self.assertEqual(result[field], 0)
        self.assertEqual(len(result['remaining_gates']), 3)
        self.assertNotIn(SOURCE, str(result))

    def test_removed_ordinary_source_remains_an_exposure_match(self):
        self.commit('ordinary.txt', SOURCE)
        git(self.root, 'rm', 'ordinary.txt')
        git(self.root, 'commit', '-qm', 'synthetic deletion')
        result = entry.screen_development_source(self.root, SOURCE)
        self.assertFalse(result['history_clear'])
        self.assertTrue(any(m['exact_blob_match'] for m in result['history']['matches']))
        self.assertFalse(result['source_qualified'])

    def test_shallow_or_unknown_history_refuses_before_content_scan(self):
        for status in (b'true\n', b'unknown\n'):
            with patch.object(entry, '_git', return_value=status), patch.object(entry, 'audit_history') as scan:
                with self.assertRaisesRegex(ValueError, 'complete reachable history'):
                    entry.screen_development_source(self.root, SOURCE)
                scan.assert_not_called()

    def test_merge_resolution_introduced_sealed_blob_stays_unopened_after_copy(self):
        self.commit('seed.txt', OTHER)
        main = git(self.root, 'symbolic-ref', '--short', 'HEAD')
        git(self.root, 'checkout', '-qb', 'synthetic-side')
        self.commit('side.txt', 'independent side branch')
        git(self.root, 'checkout', '-q', main)
        self.commit('main.txt', 'independent main branch')
        git(self.root, 'merge', '--no-commit', '--no-ff', 'synthetic-side')
        self.commit('LongMemEval-synthetic-only.txt', SOURCE)
        oid = git(self.root, 'rev-parse', 'HEAD:LongMemEval-synthetic-only.txt')
        self.assertEqual(len(git(self.root, 'show', '-s', '--format=%P').split()), 2)
        self.commit('0ordinary.txt', SOURCE)
        self.assertIn(oid, history._sealed_object_ids(self.root))
        original = history._git
        def guarded(repo, *args, **kwargs):
            if args == ('cat-file', 'blob', oid):
                self.fail('merge-introduced protected synthetic blob must not be read')
            return original(repo, *args, **kwargs)
        with patch.object(history, '_git', side_effect=guarded):
            result = entry.screen_development_source(self.root, SOURCE)
        self.assertEqual(result['history']['sealed_blob_ids_not_opened'], 1)
        self.assertEqual(result['history']['matches'], [])
        self.assertNotIn(SOURCE, str(result))

    def test_real_shallow_clone_is_rejected_before_opening_renamed_blob(self):
        self.commit('LongMemEval-synthetic-only.txt', SOURCE)
        git(self.root, 'mv', 'LongMemEval-synthetic-only.txt', 'ordinary.txt')
        git(self.root, 'commit', '-qm', 'synthetic rename')
        with tempfile.TemporaryDirectory() as target:
            clone = Path(target) / 'shallow'
            subprocess.run(['git', 'clone', '--quiet', '--depth=1',
                            self.root.as_uri(), str(clone)], check=True,
                           stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            self.assertEqual(git(clone, 'rev-parse', '--is-shallow-repository'), 'true')
            with patch.object(entry, 'audit_history') as scan:
                with self.assertRaisesRegex(ValueError, 'complete reachable history'):
                    entry.screen_development_source(clone, OTHER)
                scan.assert_not_called()

    def test_partial_repository_configuration_refuses_before_blob_inventory(self):
        self.commit('ordinary.txt', OTHER)
        for key, value in (('remote.origin.promisor', 'true'),
                           ('remote.origin.partialclonefilter', 'blob:none'),
                           ('extensions.partialClone', 'origin')):
            with self.subTest(key=key):
                git(self.root, 'config', key, value)
                with patch.object(entry, 'audit_history') as scan:
                    with self.assertRaisesRegex(ValueError, 'partial/promisor'):
                        entry.screen_development_source(self.root, SOURCE)
                    scan.assert_not_called()
                git(self.root, 'config', '--unset', key)

    def test_replaced_protected_history_refuses_before_blob_inventory(self):
        self.commit('LongMemEval-synthetic-only.txt', SOURCE)
        original = git(self.root, 'rev-parse', 'HEAD')
        git(self.root, 'mv', 'LongMemEval-synthetic-only.txt', 'ordinary.txt')
        git(self.root, 'commit', '-qm', 'synthetic rename')
        tree = git(self.root, 'rev-parse', 'HEAD^{tree}')
        replacement = subprocess.check_output(
            ['git', '-C', str(self.root), 'commit-tree', tree],
            input='synthetic replacement root\n', text=True).strip()
        git(self.root, 'replace', original, replacement)
        with patch.object(entry, 'audit_history') as scan:
            with self.assertRaisesRegex(ValueError, 'replacement history'):
                entry.screen_development_source(self.root, OTHER)
            scan.assert_not_called()

    def test_grafted_protected_history_refuses_before_blob_inventory(self):
        self.commit('LongMemEval-synthetic-only.txt', SOURCE)
        git(self.root, 'mv', 'LongMemEval-synthetic-only.txt', 'ordinary.txt')
        git(self.root, 'commit', '-qm', 'synthetic rename')
        graft = self.root / '.git' / 'info' / 'grafts'
        graft.write_text(git(self.root, 'rev-parse', 'HEAD') + '\n')
        with patch.object(entry, 'audit_history') as scan:
            with self.assertRaisesRegex(ValueError, 'grafted history'):
                entry.screen_development_source(self.root, OTHER)
            scan.assert_not_called()


if __name__ == '__main__':
    unittest.main()
