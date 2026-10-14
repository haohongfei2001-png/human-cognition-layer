"""Structural byte reuse must never cache file, source, ACL or capsule truth."""
from hashlib import sha256
from pathlib import Path
import os
import tempfile
import unittest
from unittest.mock import patch

from hcl import HCL
from hcl.kernel.types import HCLFailure, Principal, TaskRequest
from hcl.memory import codec
from hcl.memory.store import StateStore
from hcl.memory.migrations import revision_upgrade as migration
from tests import test_unified_legacy_capsule_store as capsule_tests


class MigrationDecodeCacheTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.owner=Principal('test','alice')
        self.store=StateStore.sqlite(self.root/'state.sqlite',revision=True);self.addCleanup(self.store.close)
        self.store.create_session('s',self.owner,{'bob'})
        self.handle=self.store.put_source('s',self.owner,'source','SYNTHETIC_CACHE_BOUNDARY')
        self.request=TaskRequest('plain','report',(self.handle,),'s',self.owner)
        self.result=HCL(self.store,principal=self.owner).run_sync(self.request)
        self.cache=migration._HistoryDecodeCache()

    def history(self,cache=True):
        return migration._history(self.store._db,self.store.object_root,decode_cache=self.cache if cache else None)

    def test_exact_history_unchanged_and_only_duplicate_decode_omitted(self):
        original=codec.loads
        with patch.object(codec,'loads',wraps=original) as decode:
            first=self.history();count=decode.call_count;self.assertGreater(count,0)
            self.assertEqual(self.history(),first);self.assertEqual(decode.call_count,count)
            self.assertEqual(self.history(False),first);self.assertGreater(decode.call_count,count)
        self.assertTrue(self.cache._validated)
        self.assertTrue(all(type(body) is bytes for body in self.cache._validated))

    def test_fresh_cache_and_failed_decode_are_never_reused(self):
        original=codec.loads;body=codec.dumps({'x':[1,2]})
        with patch.object(codec,'loads',wraps=original) as decode:
            self.cache.validate(body);self.cache.validate(body);self.assertEqual(decode.call_count,1)
            migration._HistoryDecodeCache().validate(body);self.assertEqual(decode.call_count,2)
            self.cache.validate(codec.dumps({'x':[1,3]}));self.assertEqual(decode.call_count,3)
        with patch.object(codec,'loads',side_effect=ValueError('malformed')) as decode:
            for _ in range(2):
                with self.assertRaises(ValueError):self.cache.validate(b'MALFORMED')
            self.assertEqual(decode.call_count,2)
        self.assertNotIn(b'MALFORMED',self.cache._validated)

    def test_file_bytes_change_hash_rechecked_after_cache(self):
        self.history();path=next(self.store.object_root.iterdir());body=path.read_bytes();path.write_bytes(body+b' ')
        with self.assertRaises(HCLFailure):self.history()
        path.write_bytes(body);self.history()

    def test_size_and_symlink_rechecked_after_cache(self):
        self.history();path=next(self.store.object_root.iterdir());original=Path.stat
        def enlarged(p,*args,**kwargs):
            value=original(p,*args,**kwargs)
            if p==path:
                fields=list(value);fields[6]=4*1024*1024+1;return os.stat_result(fields)
            return value
        with patch.object(Path,'stat',new=enlarged),self.assertRaises(HCLFailure):self.history()
        other=self.root/'same-bytes';path.rename(other);path.symlink_to(other)
        with self.assertRaises(HCLFailure):self.history()
        path.unlink();other.rename(path)

    def test_database_projection_and_current_acl_never_cached(self):
        self.history()
        self.store._db.execute("UPDATE sources SET readers='[\"bob\"]'")
        with self.assertRaises(HCLFailure):self.history()
        self.store.rebuild_projections();self.history()
        self.store.set_readers('s',self.owner,'source',{'bob'});self.history()
        denied=HCL(self.store,principal=self.owner).run_sync(self.request)
        self.assertEqual(denied.status,'DENIED');self.assertFalse(denied.answer or denied.claim_records)

    def test_erasure_never_resurrects_cached_content(self):
        self.history();plan=self.store.plan_source_erasure('s',self.owner,'source',expected_version=1)
        self.store.begin_source_erasure('s',self.owner,'source',expected_version=1,plan_hash=plan['plan_hash'],erasure_id='b'*32)
        self.store.resume_source_erasure('s',self.owner,'b'*32)
        self.history()
        denied=HCL(self.store,principal=self.owner).run_sync(self.request)
        self.assertFalse(denied.answer or denied.claim_records)
        self.assertTrue(all(not (self.store.object_root/key).exists() for key in plan['objects_to_unlink']))

    def test_capsule_root_semantics_revalidated_on_every_history(self):
        f=capsule_tests.LegacyCapsuleStoreTests();self.addCleanup(f.doCleanups)
        store,target,owner,session,ids=f.fixture();store.prepare_legacy_capsules(session,owner)
        from hcl.memory.migrations.capsules import validate_root
        cache=migration._HistoryDecodeCache()
        with patch('hcl.memory.migrations.capsules.validate_root',wraps=validate_root) as validate:
            migration._history(store._db,store.object_root,decode_cache=cache)
            count=validate.call_count;self.assertGreater(count,0)
            migration._history(store._db,store.object_root,decode_cache=cache)
            self.assertEqual(validate.call_count,2*count)
        with patch('hcl.memory.migrations.capsules.validate_root',side_effect=ValueError('changed capsule meaning')):
            with self.assertRaises(ValueError):migration._history(store._db,store.object_root,decode_cache=cache)

    def test_cache_bytes_capped_without_skipping_validation(self):
        self.cache._size=128*1024*1024
        body=codec.dumps({'small':'value'})
        with patch.object(codec,'loads',wraps=codec.loads) as decode:
            self.cache.validate(body);self.cache.validate(body);self.assertEqual(decode.call_count,2)
        self.assertFalse(self.cache._validated)


if __name__=='__main__':unittest.main()
