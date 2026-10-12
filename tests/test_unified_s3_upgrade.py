"""Exact S2.3 -> current side-copy with live old writers and execution checkpoints.

The fixture exports only the explicitly hashed 168 Python runtime members. No
historical grant, sealed benchmark, model provider or repository test is copied.
"""

from dataclasses import fields
from pathlib import Path
import json
import sqlite3
from unittest.mock import patch

from hcl import HCL
from hcl.kernel.types import HCLFailure
from hcl.memory import codec
from hcl.memory.store import StateStore
from hcl.memory.migrations.revision_upgrade import RevisionCutover, S23_CODE_HASH
from hcl.models.gateway import ModelGateway, OfflineModelPort
from hcl.operators.local_model import LocalModelOperator
from hcl.runtime.recovery import RecoveryManager
from tests import test_unified_s23_upgrade as previous

EXTRA_PROGRAM = r"""
from dataclasses import fields
from unittest.mock import patch
from hcl.kernel.execution import ExecutionBudget, ExecutionIssue
from hcl.kernel.types import Issue, FormalProblem
from hcl.models.gateway import OfflineModelPort, ModelGateway
from hcl.semantics.segments import segment_snapshot


class GraphCrash(BaseException):
    pass


graphs = {}
if schema in (3, 4):
    g_handle = store.put_source(
        session,
        owner,
        "exec-source",
        "A received a notice. A attends.",
        formal_problem=FormalProblem(
            ("Fa",),
            "Ga",
            {"domain": [0], "constants": {"a": 0}, "predicates": {"F": [0], "G": []}},
        ),
    )
    store.put_source(
        session, owner, "exec-private", "BOB_ONLY_SYNTHETIC", readers={"bob"}
    )
    g_question = "Does A attend?"
    g_segments = segment_snapshot(
        store.snapshot(session, owner, (g_handle,)), g_question
    )
    g_sources = [s.segment_id for s in g_segments if s.kind == "SOURCE"]
    g_questions = [s.segment_id for s in g_segments if s.kind == "QUESTION"]
    g_atom = {"op": "atom", "predicate": "attends", "args": [{"entity": "person"}]}

    def meaning(identity, question=False):
        return {
            "id": identity,
            "natural_reading": "Synthetic proposed meaning",
            "ast": g_atom,
            "frame": "source-reading",
            "segment_ids": g_questions if question else g_sources,
            "origin": "INTERPRETATION",
        }

    g_candidate = {
        "schema": "hcl-semantic-candidates-1",
        "frames": [
            {
                "id": "source-reading",
                "kind": "SOURCE_DISCOURSE",
                "parent": None,
                "segment_ids": g_sources,
            }
        ],
        "entities": [
            {
                "id": "person",
                "label": "A",
                "source_id": "exec-source",
                "segment_ids": g_sources,
            }
        ],
        "predicates": [
            {
                "id": "attends",
                "label": "attends",
                "arity": 1,
                "segment_ids": g_sources + g_questions,
            }
        ],
        "readings": [
            {
                "id": "reading",
                "frame": "source-reading",
                "assumptions": [],
                "premises": [meaning("p")],
                "query": meaning("q", True),
                "unparsed_segments": [],
                "alignment": {
                    "judgment": "SUPPORTED",
                    "explanation": "Synthetic injected proposal only",
                },
            }
        ],
    }
    for g_name, g_kind, g_seam in [
        ("completed", "logic.check_interpretation", None),
        ("semantic_completed", "logic.compare_semantic_readings", None),
        ("returned", "logic.compare_semantic_readings", "return_persisted"),
        ("unknown", "logic.compare_semantic_readings", "send_started"),
        ("computed", "logic.check_interpretation", "execution_computed"),
        ("committed", "logic.check_interpretation", "execution_effects_committed"),
        ("acl_pending", "logic.check_interpretation", "execution_computed"),
    ]:
        g_request = TaskRequest(
            "graph-" + g_name,
            g_question,
            (g_handle,),
            session,
            owner,
            budget=ExecutionBudget(
                max_mock_calls=4, max_output_bytes=32768, max_total_output_bytes=262144
            ),
            issue=ExecutionIssue(
                "root", goals=(Issue("check", g_kind, "exec-source"),)
            ),
        )
        g_port = OfflineModelPort(json.dumps(g_candidate))
        g_client = HCL(store, principal=owner, gateway=ModelGateway(store, g_port))
        g_crashed = False

        def fault(stage):
            global g_crashed
            if stage == g_seam and not g_crashed:
                g_crashed = True
                raise GraphCrash()

        try:
            with patch.object(store, "_checkpoint", fault):
                g_result = g_client.run_sync(g_request)
        except GraphCrash:
            pass
        if g_seam:
            assert g_crashed, g_name
        else:
            assert g_result.status == "COMPLETED", (g_name, g_result.diagnostics)
        graphs[g_name] = {
            "request": codec.dumps(g_request).decode(),
            "attempts": g_port.attempts,
        }
shapes = {name: [f.name for f in fields(cls)] for name, cls in codec.CLASSES.items()}
"""
INSERTION = "ledger=TaskBudgetLedger(store);snap="
assert previous.OLD_PROGRAM.count(INSERTION) == 1
OLD_PROGRAM = previous.OLD_PROGRAM.replace(
    INSERTION, EXTRA_PROGRAM + "\n" + INSERTION
).replace(
    "'bundle':version_bundle(schema=schema)",
    "'bundle':version_bundle(schema=schema),'graphs':graphs,'shapes':shapes",
)


class S23RuntimeUpgradeTests(previous.RuntimeUpgradeTests):
    baseline = "421e895562227141eb60b3e123363c1708685ee3"
    code_hash = S23_CODE_HASH
    file_count = 168
    old_program = previous.OLD_PROGRAM

    def test_real_graph_replays_known_returns_unknown_holds_and_committed_effects(self):
        self.old_program = OLD_PROGRAM
        for schema in (3, 4):
            with self.subTest(schema=schema):
                source, old, process = self.old(schema, str(schema))
                current_shapes = {
                    name: [f.name for f in fields(cls)]
                    for name, cls in codec.CLASSES.items()
                }
                # M10 adds four disjoint tagged contracts; it must not change
                # any historical class/field or silently allow arbitrary growth.
                self.assertEqual(set(current_shapes) - set(old["shapes"]), {
                    "RetrievalQuery", "RetrievalDependency", "RetrievalIssue", "EvidenceNode",
                })
                self.assertEqual(old["shapes"], {
                    name: current_shapes[name] for name in old["shapes"]
                })
                target = RevisionCutover.upgrade(
                    source, self.root / ("graph" + str(schema)), self.owner
                )
                store = target.open_store()
                try:
                    requests = {
                        name: codec.loads(row["request"].encode())
                        for name, row in old["graphs"].items()
                    }
                    for name, request in requests.items():
                        self.assertEqual(
                            codec.dumps(request).decode(),
                            old["graphs"][name]["request"],
                        )
                        if name == "acl_pending":
                            continue
                        port = OfflineModelPort()
                        client = HCL(
                            store,
                            principal=self.owner,
                            gateway=ModelGateway(store, port),
                        )
                        if name in ("completed", "semantic_completed"):
                            result = client.run_sync(request)
                            self.assertTrue(result.execution_receipt["replayed"])
                        elif name == "unknown":
                            with self.assertRaises(HCLFailure) as caught:
                                RecoveryManager(store).resume_execution(
                                    request, expected_owner_id=old["owner_id"]
                                )
                            self.assertEqual(
                                caught.exception.diagnostic.code,
                                "UNKNOWN_SEND_NO_RESUME",
                            )
                            result = client.run_sync(request)
                            self.assertEqual(
                                result.diagnostics[0].code, "TASK_INTERRUPTED_NO_RESEND"
                            )
                            self.assertIsNone(result.usage["mock_calls"])
                            self.assertEqual(result.usage["held_mock_calls"], 1)
                        else:
                            self.assertEqual(
                                client.run_sync(request).diagnostics[0].code,
                                "TASK_IN_PROGRESS",
                            )
                            RecoveryManager(store).resume_execution(
                                request, expected_owner_id=old["owner_id"]
                            )
                            if name in ("computed", "committed"):
                                with patch.object(
                                    LocalModelOperator,
                                    "run",
                                    side_effect=AssertionError("no recomputation"),
                                ):
                                    result = client.run_sync(request)
                                self.assertEqual(result.usage["local_evaluations"], 2)
                            else:
                                result = client.run_sync(request)
                                self.assertEqual(result.usage["mock_calls"], 1)
                        if name != "unknown":
                            self.assertEqual(
                                result.status, "COMPLETED", result.diagnostics
                            )
                        self.assertEqual(port.attempts, 0)
                    for action in ("snapshot", "write"):
                        self.assertFalse(self.command(process, action=action)["ok"])
                    # Replay only needs actual dependencies; raw audit additionally
                    # contains a private branch and cannot bypass its host ACL.
                    with self.assertRaises(HCLFailure) as caught:
                        RecoveryManager(store).execution_audit(requests["completed"])
                    self.assertEqual(caught.exception.status, "DENIED")
                    store.set_readers(
                        old["session"], self.owner, "exec-source", {"bob"}
                    )
                    with self.assertRaises(HCLFailure) as caught:
                        RecoveryManager(store).resume_execution(
                            requests["acl_pending"], expected_owner_id=old["owner_id"]
                        )
                    self.assertEqual(caught.exception.status, "DENIED")
                    for name in ("completed", "semantic_completed", "acl_pending"):
                        port = OfflineModelPort()
                        result = HCL(
                            store,
                            principal=self.owner,
                            gateway=ModelGateway(store, port),
                        ).run_sync(requests[name])
                        self.assertEqual(result.status, "DENIED")
                        self.assertEqual(result.claim_records, ())
                        self.assertFalse(result.answer)
                        self.assertEqual(port.attempts, 0)
                finally:
                    store.close()

    def test_schema4_two_controls_must_bind_the_same_exact_runtime(self):
        source, _, _ = self.old(4)
        db = sqlite3.connect(source)
        bundle = json.loads(
            db.execute("SELECT versions FROM namespace_control").fetchone()[0]
        )
        bundle["code_sha256"] = "0" * 64
        db.execute("UPDATE namespace_control SET versions=?", (json.dumps(bundle),))
        db.commit()
        db.close()
        with self.assertRaises(ValueError):
            RevisionCutover.upgrade(source, self.root / "new", self.owner)
        db = sqlite3.connect(source)
        self.assertEqual(db.execute("PRAGMA user_version").fetchone()[0], 4)
        db.close()
