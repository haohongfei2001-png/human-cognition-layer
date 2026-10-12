"""Exact 194-file retrieval predecessor -> governed retention and scoped erasure.

Historical and current predecessors are remote-readable exact runtime projections.
Only allowlisted Python runtime members are materialized; source snapshots do not
constitute releases or acceptance evidence. See the historical snapshot inventory.
"""
import unittest
from pathlib import Path
from unittest.mock import patch

from hcl import HCL
from hcl.memory import codec
from hcl.memory.governance import verify_inventory
from hcl.memory.migrations.revision_upgrade import RevisionCutover, M10_RETRIEVAL_CODE_HASH
from hcl.runtime.recovery import RecoveryManager
from tests import test_unified_s23_upgrade as fixtures

EXTRA = r'''
from hcl import ExecutionBudget,ExecutionIssue,RetrievalIssue,RetrievalQuery
from unittest.mock import patch
class RetrievalCrash(BaseException):pass
query=RetrievalQuery(dict(support='ORIGINAL',challenge='SOURCE',alternative='ORIGINAL'))
retrieval_requests={}
for name,seam in [('completed',None),('partial',None),('computed','execution_computed'),('committed','execution_effects_committed')]:
 q=replace(query,max_characters=1) if name=='partial' else query
 r=TaskRequest('retrieval-'+name,'Inspect the source.',(),session,owner,budget=ExecutionBudget(max_mock_calls=0,max_output_bytes=65536),issue=ExecutionIssue('root',goals=(RetrievalIssue(name,query=q),)))
 fired=False
 def fault(stage):
  global fired
  if stage==seam and not fired:fired=True;raise RetrievalCrash()
 try:
  with patch.object(store,'_checkpoint',fault):out=HCL(store,principal=owner).run_sync(r)
 except RetrievalCrash:pass
 if seam:assert fired,name
 else:assert out.status==('PARTIAL' if name=='partial' else 'COMPLETED'),out.diagnostics
 retrieval_requests[name]=codec.dumps(r).decode()
'''
OLD_PROGRAM = fixtures.OLD_PROGRAM.replace("ledger=TaskBudgetLedger(store);snap=", EXTRA + "\nledger=TaskBudgetLedger(store);snap=").replace(
    "'bundle':version_bundle(schema=schema)", "'bundle':version_bundle(schema=schema),'retrieval_requests':retrieval_requests"
).replace(
    "elif command['action']=='close': break",
    "elif command['action']=='legacy_view': RevisionCutover(command['source'],command['target']).legacy_view(owner)\n  elif command['action']=='own_legacy_view': ns.legacy_view(owner)\n  elif command['action']=='close': break",
)


class GovernanceUpgradeTests(unittest.TestCase):
    baseline = "c80d48eca23147e31802614f249dbbf7ac25e9d7"  # exact 09ff Python projection
    code_hash = M10_RETRIEVAL_CODE_HASH
    file_count = 194
    @classmethod
    def setUpClass(cls):
        class OldRetrieval(fixtures.RuntimeUpgradeTests):
            baseline = cls.baseline
            code_hash = cls.code_hash
            file_count = cls.file_count
            old_program = OLD_PROGRAM
        cls.old_fixture = OldRetrieval
        cls.old_fixture.setUpClass()

    @classmethod
    def tearDownClass(cls):
        cls.old_fixture.tearDownClass()

    def test_actual_old_retrieval_and_control_fence_both_schemas(self):
        fixture = self.old_fixture()
        fixture.setUp()
        try:
            for schema in (3, 4):
                source, metadata, process = fixture.old(schema, str(schema))
                target = RevisionCutover.upgrade(source, fixture.root / ("governed" + str(schema)), fixture.owner)
                store = target.open_store()
                try:
                    self.assertEqual(store._revision_control["governance_protocol"], "hcl-memory-governance-1")
                    verify_inventory(store._db)
                    for name, encoded in metadata["retrieval_requests"].items():
                        request = codec.loads(encoded.encode())
                        if name in ("computed", "committed"):
                            RecoveryManager(store).resume_execution(request, expected_owner_id=metadata["owner_id"])
                        result = HCL(store, principal=fixture.owner).run_sync(request)
                        self.assertEqual(result.status, "PARTIAL" if name == "partial" else "COMPLETED", result.diagnostics)
                        self.assertEqual(result.usage["mock_calls"], 0)
                    request = codec.loads(metadata["request"].encode())
                    handle = request.source_handles[0]
                    plan = store.plan_source_erasure(metadata["session"], fixture.owner, handle.source_id, expected_version=handle.version)
                    self.assertGreaterEqual(plan["accounting_to_preserve"]["unknown_calls"], 2)
                    self.assertEqual(plan["readiness"], "PLAN_ONLY_NO_ERASURE_PERFORMED")
                    verify_inventory(store._db)
                    store.rebuild_projections()
                    self.assertEqual(store.plan_source_erasure(metadata["session"], fixture.owner, handle.source_id, expected_version=handle.version), plan)
                    # The old legacy helper checked fields rather than codehash.
                    # Its actual old code must fail on the mandatory new fields.
                    old_export = fixture.command(process, action="legacy_view", source=str(source), target=str(target.directory))
                    self.assertFalse(old_export["ok"])
                    self.assertEqual(old_export["error"], "ValueError")
                    self.assertFalse(fixture.command(process, action="write")["ok"])
                finally:
                    store.close()
        finally:
            fixture.tearDown()

    def test_recovered_cutover_and_repeated_upgrade_never_resurrect_erased_history(self):
        class Crash(BaseException):
            pass
        fixture = self.old_fixture()
        fixture.setUp()
        try:
            for schema in (3, 4):
                source, metadata, process = fixture.old(schema, "erase" + str(schema))
                directory = fixture.root / ("erased" + str(schema))
                def crash(at):
                    if at == "target_activated_unpublished":
                        raise Crash()
                with patch.object(RevisionCutover, "_checkpoint", side_effect=crash), self.assertRaises(Crash):
                    RevisionCutover.upgrade(source, directory, fixture.owner)
                target = RevisionCutover.upgrade(source, directory, fixture.owner)
                store = target.open_store()
                try:
                    request = codec.loads(metadata["request"].encode())
                    handle = request.source_handles[0]
                    plan = store.plan_source_erasure(metadata["session"], fixture.owner, handle.source_id,
                                                    expected_version=handle.version)
                    store.begin_source_erasure(metadata["session"], fixture.owner, handle.source_id,
                        expected_version=handle.version, plan_hash=plan["plan_hash"], erasure_id="b" * 32)
                    receipt = store.resume_source_erasure(metadata["session"], fixture.owner, "b" * 32)
                    self.assertIn("PREDECESSOR_COPY_RETAINED", receipt["limitations"])
                    self.assertEqual(receipt["status"], "PARTIAL_ERASURE_RETAINED_COPIES")
                    for _ in range(2):
                        RevisionCutover.upgrade(source, directory, fixture.owner)
                        replay = HCL(store, principal=fixture.owner).run_sync(request)
                        self.assertEqual(replay.status, "DENIED")
                        self.assertEqual(replay.diagnostics[0].code, "CONTENT_ERASED")
                    store.rebuild_projections()
                    from hcl.kernel.types import HCLFailure
                    with self.assertRaises(HCLFailure):
                        target.legacy_view(fixture.owner)
                    target.rollback(fixture.owner)
                    with self.assertRaises(HCLFailure):
                        target.legacy_view(fixture.owner)
                    # Read-only execution does not strand authenticated erasure
                    # maintenance or force reactivation of an old writer.
                    self.assertEqual(store.source_erasure_receipt(metadata["session"], fixture.owner, "b" * 32), receipt)
                    self.assertEqual(store.resume_source_erasure(metadata["session"], fixture.owner, "b" * 32), receipt)
                    self.assertEqual(HCL(store, principal=fixture.owner).run_sync(request).status, "DENIED")
                finally:
                    store.close()
        finally:
            fixture.tearDown()

    def test_exact_old_chained_export_is_terminally_fenced_not_vacuously_denied(self):
        fixture = self.old_fixture()
        fixture.setUp()
        # This scenario needs a genuinely authorized old whole-ledger export.
        # It is not the separate bob-only quarantine ACL test fixture.
        fixture.old_program = fixture.old_program.replace(
            "readers={'source':('alice',),'private':('bob',)}",
            "readers={'source':('alice',),'private':('alice',)}")
        try:
            source, metadata, process = fixture.old(4, "old-chain")
            self.assertTrue(fixture.command(process, action="own_legacy_view")["ok"])
            target = RevisionCutover.upgrade(source, fixture.root / "new-chain", fixture.owner)
            blocked = fixture.command(process, action="own_legacy_view")
            self.assertFalse(blocked["ok"])
            self.assertEqual(blocked["error"], "ValueError")
            store = target.open_store()
            try:
                request = codec.loads(metadata["request"].encode())
                handle = request.source_handles[0]
                plan = store.plan_source_erasure(metadata["session"], fixture.owner, handle.source_id,
                                                expected_version=handle.version)
                store.begin_source_erasure(metadata["session"], fixture.owner, handle.source_id,
                    expected_version=handle.version, plan_hash=plan["plan_hash"], erasure_id="c" * 32)
                self.assertFalse(fixture.command(process, action="own_legacy_view")["ok"])
                self.assertFalse(fixture.command(process, action="write")["ok"])
            finally:
                store.close()
        finally:
            fixture.tearDown()


if __name__ == "__main__":
    unittest.main()


class QualifiedGovernanceUpgradeTests(GovernanceUpgradeTests):
    """Same original assertions on the distinct qualified retrieval predecessor.

    The reviewed predecessor is bound to the same-runtime published PR437 main merge.
    """
    baseline = "542e2ea5c91bca24dd8983cf6a6b0c701f843fc8"
    from hcl.memory.migrations.revision_upgrade import M10_QUALIFIED_RETRIEVAL_CODE_HASH as code_hash
    file_count = 195
