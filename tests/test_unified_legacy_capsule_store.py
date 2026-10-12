"""Scoped read/cleanup of newly constructed, disposable legacy fixtures only."""
from hashlib import sha256
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from hcl.kernel.types import HCLFailure, Principal
from hcl.memory import codec
from hcl.memory.governance import verify_inventory
from hcl.memory.migrations.compile import source_key
from hcl.memory.migrations.namespace import MigrationNamespace
from hcl.memory.migrations.revision_upgrade import RevisionCutover
from hcl.memory.migrations.types import LegacyRecord, LegacySnapshot, LegacySource
from hcl.memory.retention_objects import pending


class Crash(BaseException):
    pass


class LegacyCapsuleStoreTests(unittest.TestCase):
    def fixture(self, *, unknown=False, a_status='CURRENT'):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        owner = Principal('t', 'alice')
        sources = (LegacySource('A', 1, 'A_OLD_CANARY', 'HISTORICAL'),
                   LegacySource('A', 2, 'A_CURRENT_CANARY', a_status),
                   LegacySource('B', 1, 'B_ONLY_ORIGINAL\r\n秘密𝄞', 'WITHDRAWN'))
        records = (LegacyRecord('opaque', 'SYSTEM_INTERPRETATION', dict(supports=[], challenges=[], content='UNKNOWN_CANARY')),) if unknown else ()
        imported = MigrationNamespace.import_snapshot(root/'old', LegacySnapshot(sources, records),
                            namespace_id='legacy', owner=owner)
        receipt = imported.receipt(owner)
        session = receipt['session_id']
        ids = {key: receipt['source_mapping'][source_key(key, version)]['source_id'] for key, version in [('A',2),('B',1)]}
        target = RevisionCutover.upgrade(imported.path, root/'new', owner)
        store = target.open_store()
        self.addCleanup(store.close)
        return store, target, owner, session, ids

    def erase(self, store, owner, session, source_id, *, version=2):
        plan = store.plan_source_erasure(session, owner, source_id, expected_version=version)
        store.begin_source_erasure(session, owner, source_id, expected_version=version,
                                  plan_hash=plan['plan_hash'], erasure_id='a'*32)
        return store.resume_source_erasure(session, owner, 'a'*32)

    def test_prepared_originals_survive_other_source_erasure_rebuild_retry_and_rollback(self):
        store, target, owner, session, ids = self.fixture()
        old_hash = store._db.execute('SELECT package_hash FROM namespace_control').fetchone()[0]
        prepared = store.prepare_legacy_capsules(session, owner)
        self.assertIn('A_CURRENT_CANARY', str(target.legacy_view(owner)))
        before = store.legacy_source_view(session, owner, (ids['B'],))
        count = store._db.execute('SELECT count(*) FROM events').fetchone()[0]
        self.assertEqual(store.prepare_legacy_capsules(session, owner), prepared)
        self.assertEqual(store._db.execute('SELECT count(*) FROM events').fetchone()[0], count)
        self.assertIn('B_ONLY_ORIGINAL', str(before))
        self.assertNotIn('A_CURRENT_CANARY', str(before))
        self.assertIn('WITHDRAWN', str(before))
        result = self.erase(store, owner, session, ids['A'])
        self.assertEqual(result['limitations'], ['PREDECESSOR_COPY_RETAINED'])
        self.assertFalse((store.object_root/old_hash).exists())
        for path in target.directory.rglob('*'):
            if path.is_file():
                self.assertNotIn(b'A_CURRENT_CANARY', path.read_bytes(), str(path))
                self.assertNotIn(b'A_OLD_CANARY', path.read_bytes(), str(path))
        with self.assertRaises(HCLFailure):
            store.legacy_source_view(session, owner, (ids['A'],))
        store.rebuild_projections()
        verify_inventory(store._db)
        self.assertEqual(store.legacy_source_view(session, owner, (ids['B'],)), before)
        RevisionCutover.upgrade(target.source, target.directory, owner)
        target.rollback(owner)
        self.assertEqual(store.legacy_source_view(session, owner, (ids['B'],)), before)
        with self.assertRaises(HCLFailure):
            target.legacy_view(owner)
        self.assertEqual(store.resume_source_erasure(session, owner, 'a'*32), result)

    def test_unknown_records_are_retained_and_named_not_guessed_or_delivered(self):
        store, _, owner, session, ids = self.fixture(unknown=True)
        store.prepare_legacy_capsules(session, owner)
        unknown_hash = store._db.execute("SELECT object_hash FROM legacy_capsules WHERE kind='UNKNOWN_PROVENANCE'").fetchone()[0]
        result = self.erase(store, owner, session, ids['A'])
        self.assertIn('UNKNOWN_LEGACY_PROVENANCE_RETAINED', result['limitations'])
        self.assertEqual(result['status'], 'PARTIAL_ERASURE_RETAINED_COPIES')
        self.assertIn('UNKNOWN_CANARY', str(store._get_object(unknown_hash)))
        self.assertNotIn('UNKNOWN_CANARY', str(store.legacy_source_view(session, owner, (ids['B'],))))

    def test_historical_only_source_can_be_erased_without_invented_current_record(self):
        store, _, owner, session, ids = self.fixture(a_status='WITHDRAWN')
        store.prepare_legacy_capsules(session, owner)
        self.assertEqual(store._db.execute('SELECT count(*) FROM sources').fetchone()[0], 0)
        self.erase(store, owner, session, ids['A'])
        with self.assertRaises(HCLFailure):
            store.legacy_source_view(session, owner, (ids['A'],))
        self.assertIn('B_ONLY_ORIGINAL', str(store.legacy_source_view(session, owner, (ids['B'],))))

    def test_every_staging_checkpoint_retries_without_duplicate_events(self):
        for seam in ('retention_journal_persisted','object_persisted','event_appended','projection_updated',
                     'legacy_capsules_before_commit','legacy_capsules_committed'):
            with self.subTest(seam=seam):
                store, target, owner, session, ids = self.fixture()
                fired = False
                def crash(at):
                    nonlocal fired
                    if at == seam and not fired:
                        fired = True
                        raise Crash()
                with patch.object(store, '_checkpoint', side_effect=crash), self.assertRaises(Crash):
                    store.prepare_legacy_capsules(session, owner)
                self.assertTrue(fired)
                peer = target.open_store()
                self.addCleanup(peer.close)
                peer.prepare_legacy_capsules(session, owner)
                count = peer._db.execute('SELECT count(*) FROM events').fetchone()[0]
                peer.prepare_legacy_capsules(session, owner)
                self.assertEqual(peer._db.execute('SELECT count(*) FROM events').fetchone()[0], count)
                self.assertIn('B_ONLY_ORIGINAL', str(peer.legacy_source_view(session, owner, (ids['B'],))))
                self.erase(peer, owner, session, ids['A'])
                self.assertIn('B_ONLY_ORIGINAL', str(peer.legacy_source_view(session, owner, (ids['B'],))))

    def test_old_wal_read_rechecks_source_tombstone_and_current_acl(self):
        for action in ('erase','revoke'):
            with self.subTest(action=action):
                store, target, owner, session, ids = self.fixture()
                store.prepare_legacy_capsules(session, owner)
                peer = target.open_store()
                self.addCleanup(peer.close)
                original, fired = store._get_object, False
                def race(digest):
                    nonlocal fired
                    value = original(digest)
                    if type(value) is dict and value.get('kind') == 'SOURCE' and not fired:
                        fired = True
                        if action == 'erase':
                            plan = peer.plan_source_erasure(session, owner, ids['B'], expected_version=1)
                            peer.begin_source_erasure(session, owner, ids['B'], expected_version=1,
                                                      plan_hash=plan['plan_hash'], erasure_id='b'*32)
                        else:
                            peer.set_legacy_readers(session, owner, ids['B'], ())
                    return value
                with patch.object(store, '_get_object', side_effect=race), self.assertRaises(HCLFailure):
                    store.legacy_source_view(session, owner, (ids['B'],))
                self.assertTrue(fired)
                with patch.object(store, '_get_object', side_effect=AssertionError('must check ACL before content')):
                    with self.assertRaises(HCLFailure):
                        store.legacy_source_view(session, owner, (ids['B'],))

    def test_import_ceiling_current_acl_and_nonowner_are_independent_gates(self):
        store, target, owner, session, ids = self.fixture()
        store.prepare_legacy_capsules(session, owner)
        with self.assertRaises(HCLFailure):
            store.set_legacy_readers(session, owner, ids['B'], ('alice', 'new-reader'))
        store.set_legacy_readers(session, owner, ids['B'], ())
        with self.assertRaises(HCLFailure):
            store.legacy_source_view(session, owner, (ids['B'],))
        store.set_legacy_readers(session, owner, ids['B'], ('alice',))
        self.assertIn('B_ONLY_ORIGINAL', str(store.legacy_source_view(session, owner, (ids['B'],))))
        store.set_readers(session, owner, ids['A'], set())
        with patch.object(store, '_get_object', side_effect=AssertionError('ACL before content')):
            with self.assertRaises(HCLFailure):
                store.legacy_source_view(session, owner, (ids['A'],))
            with self.assertRaises(HCLFailure):
                store.legacy_source_view(session, Principal('other-tenant', 'alice'), (ids['B'],))

    def test_unprepared_quarantine_import_acl_cannot_be_bypassed_by_owner(self):
        store, target, owner, session, ids = self.fixture()
        # The migration's original host policy is immutable package data; a
        # second synthetic import covers the quarantined-only inaccessible case.
        old = MigrationNamespace.import_snapshot(target.directory.parent/'private-old',
            LegacySnapshot((LegacySource('Q', 1, 'PRIVATE', 'WITHDRAWN'),)),
            namespace_id='private', owner=owner, readers={'Q': ('bob',)})
        upgraded = RevisionCutover.upgrade(old.path, target.directory.parent/'private-new', owner)
        private = upgraded.open_store()
        self.addCleanup(private.close)
        session = private._db.execute('SELECT session_id FROM sessions').fetchone()[0]
        with self.assertRaises(HCLFailure):
            private.prepare_legacy_capsules(session, owner)
        self.assertEqual(private._db.execute('SELECT count(*) FROM legacy_capsules').fetchone()[0], 0)

    def test_prepared_root_remains_integrity_checked_before_and_after_erasure(self):
        for erased in (False, True):
            with self.subTest(erased=erased):
                store, target, owner, session, ids = self.fixture()
                store.prepare_legacy_capsules(session, owner)
                if erased:
                    self.erase(store, owner, session, ids['A'])
                digest = store._db.execute('SELECT package_hash FROM namespace_control').fetchone()[0]
                path = store.object_root / digest
                original = path.read_bytes()
                path.write_bytes(b'CORRUPT_SYNTHETIC_ROOT')
                for operation in (lambda: RevisionCutover.upgrade(target.source, target.directory, owner),
                                  lambda: store.legacy_source_view(session, owner, (ids['B'],)),
                                  lambda: store.prepare_legacy_capsules(session, owner)):
                    with self.assertRaises(HCLFailure) as error:
                        operation()
                    self.assertEqual(error.exception.diagnostic.code, 'STATE_CORRUPT')
                path.write_bytes(original)  # Restore this test fixture, not production data.
                self.assertIn('B_ONLY_ORIGINAL', str(store.legacy_source_view(session, owner, (ids['B'],))))


if __name__ == '__main__':
    unittest.main()
