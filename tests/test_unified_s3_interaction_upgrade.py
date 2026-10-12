"""Preserve the actual published qualified M04 runtime and recovery boundary."""

from unittest.mock import patch
from hcl import HCL
from hcl.kernel.types import HCLFailure
from hcl.memory import codec
from hcl.memory.migrations.revision_upgrade import (
    RevisionCutover,
    M04_QUALIFIED_CODE_HASH,
)
from hcl.models.gateway import OfflineModelPort, ModelGateway
from hcl.operators.local_model import LocalModelOperator
from hcl.runtime.recovery import RecoveryManager
from tests import test_unified_s3_discovery_upgrade as previous
from tests import test_unified_discovery_upgrade as qualified

# Execute only the allowlisted historical runtime in its own Python process.
# The same actual domain caveats are already qualified in this predecessor.
DISCOVERY_PROGRAM = qualified.DISCOVERY_PROGRAM.replace(
    "assert result.status=='COMPLETED'", "assert result.status=='PARTIAL'"
).replace(
    "assert cap_result.status=='COMPLETED'", "assert cap_result.status=='PARTIAL'"
)
OLD_PROGRAM = previous.OLD_PROGRAM.replace(
    previous.INSERTION, DISCOVERY_PROGRAM + "\n" + previous.INSERTION
).replace(
    "'argument_requests':argument_requests",
    "'argument_requests':argument_requests,'discovery_requests':discovery_requests",
)


class QualifiedM04UpgradeTests(previous.S4RuntimeUpgradeTests):
    baseline = "e3a73062ebcb011b2db7b4ad4ece8136a9e655c8"
    code_hash = M04_QUALIFIED_CODE_HASH
    file_count = 179

    def test_real_qualified_discovery_delivery_and_accepted_operations_remain_qualified(
        self,
    ):
        self.old_program = OLD_PROGRAM
        for schema in (3, 4):
            with self.subTest(schema=schema):
                source, old, process = self.old(schema, str(schema))
                store = RevisionCutover.upgrade(
                    source, self.root / ("new" + str(schema)), self.owner
                ).open_store()
                try:
                    for name, metadata in old["discovery_requests"].items():
                        with self.subTest(name=name):
                            request = codec.loads(metadata["request"].encode())
                            port = OfflineModelPort("NEVER_SEND")
                            client = HCL(
                                store,
                                principal=self.owner,
                                gateway=ModelGateway(store, port),
                            )
                            if name.endswith("unknown"):
                                with self.assertRaises(HCLFailure) as caught:
                                    RecoveryManager(store).resume_execution(
                                        request, expected_owner_id=old["owner_id"]
                                    )
                                self.assertEqual(
                                    caught.exception.diagnostic.code,
                                    "UNKNOWN_SEND_NO_RESUME",
                                )
                                result = client.run_sync(request)
                                self.assertIsNone(result.usage["mock_calls"])
                                self.assertEqual(result.usage["held_mock_calls"], 1)
                                self.assertFalse(result.answer)
                                continue
                            cached = name.endswith("completed") or "-capacity-" in name
                            if cached:
                                row = store._db.execute(
                                    "SELECT * FROM tasks WHERE request_id=?",
                                    (request.request_id,),
                                ).fetchone()
                                original = store._get_object(row["result_hash"])
                            else:
                                RecoveryManager(store).resume_execution(
                                    request, expected_owner_id=old["owner_id"]
                                )
                            if not name.endswith("returned"):
                                with patch.object(
                                    LocalModelOperator,
                                    "run",
                                    side_effect=AssertionError("no recomputation"),
                                ):
                                    result = client.run_sync(request)
                            else:
                                result = client.run_sync(request)
                            self.assertEqual(
                                result.status, "PARTIAL", result.diagnostics
                            )
                            code = (
                                "CYCLIC_PROOF_FRAGMENT_EXCLUDED"
                                if name.startswith("cycle")
                                else "INCONSISTENT_STRICT_CORE"
                            )
                            self.assertIn(code, result.answer)
                            self.assertIn(code, str(result.claim_records))
                            self.assertEqual(result.usage["mock_calls"], 1)
                            if cached:
                                self.assertEqual(result.answer, original.answer)
                                self.assertEqual(
                                    result.claim_records, original.claim_records
                                )
                                self.assertEqual(
                                    store._get_object(row["result_hash"]), original
                                )
                            self.assertEqual(port.attempts, 0)
                    self.assertFalse(self.command(process, action="write")["ok"])
                    store.set_readers(
                        old["session"], self.owner, "discovery-source", {"bob"}
                    )
                    request = codec.loads(
                        old["discovery_requests"]["cycle-probe-completed"][
                            "request"
                        ].encode()
                    )
                    result = HCL(store, principal=self.owner).run_sync(request)
                    self.assertEqual(result.status, "DENIED")
                    self.assertFalse(result.answer or result.claim_records)
                finally:
                    store.close()
