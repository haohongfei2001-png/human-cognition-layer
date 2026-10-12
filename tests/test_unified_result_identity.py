"""Fresh accepted operations bind current authority without changing historical effects."""

import asyncio
from dataclasses import fields, replace
import json
import unittest
from unittest.mock import patch

from hcl import HCL
from hcl.kernel.execution import LocalModel, ModelIssue
from hcl.kernel.types import Delta, Principal
from hcl.kernel.dependencies import QueryDelta, IndexQuery, QueryDependency
from hcl.models.gateway import OfflineModelPort, ModelGateway
from hcl.operators.logic import FiniteLogicOperator
from hcl.operators.local_model import LocalModelOperator
from tests import test_unified_s23 as graph_fixtures
from tests import test_unified_s3_relationship as relationship_fixtures


class ResultIdentityTests(unittest.TestCase):
    def test_exact_delta_context_changes_identity_but_unrelated_revision_does_not(self):
        fixture = graph_fixtures.ExecutionGraphTests()
        fixture.setUp()
        try:
            snapshot = fixture.store.snapshot("s", fixture.owner, (fixture.handle,))
            model = LocalModel(
                "pure",
                "finite-interpretation-1",
                {"source_id": "source"},
                snapshot.source_versions,
            )
            issue = ModelIssue("same", "logic.check_interpretation", "source", model)
            pure = FiniteLogicOperator().run(snapshot, issue, fixture.budget)
            delta = pure.candidate_delta

            def wrap(effect):
                # This tests identity, not authorization: altered synthetic Delta
                # metadata are never submitted to a store and grant no access.
                with patch.object(
                    FiniteLogicOperator,
                    "run",
                    return_value=replace(
                        pure, candidate_delta=effect, read_set=effect.read_set
                    ),
                ):
                    return LocalModelOperator().run(snapshot, issue, fixture.budget)

            original = wrap(delta)
            self.assertEqual(
                original.result_refs,
                wrap(
                    replace(delta, base_revision=delta.base_revision + 99)
                ).result_refs,
            )
            for name, value in (
                ("access_epoch", delta.access_epoch + 1),
                ("session_id", "other-session"),
                ("principal", Principal("tenant", "bob")),
                ("principal", Principal("foreign", "alice")),
                ("read_set", {"source": 2}),
                ("rule_version", "another-explicit-rule"),
            ):
                with self.subTest(name=name, value=value):
                    changed = wrap(replace(delta, **{name: value}))
                    self.assertNotEqual(changed.result_refs, original.result_refs)
                    self.assertEqual(
                        changed.candidate_delta.new_inferences[0].values,
                        original.candidate_delta.new_inferences[0].values,
                    )
            args = {f.name: getattr(delta, f.name) for f in fields(Delta)}
            query = IndexQuery({"kind": "claims"}, ("source",))
            first = QueryDelta(
                **args, query_dependencies=(QueryDependency(query, "0" * 64),)
            )
            second = replace(
                first, query_dependencies=(QueryDependency(query, "1" * 64),)
            )
            narrowed = replace(
                first,
                query_dependencies=(
                    QueryDependency(
                        IndexQuery({"kind": "roots"}, ("source",)), "0" * 64
                    ),
                ),
            )
            self.assertEqual(
                len(
                    {
                        original.result_refs,
                        wrap(first).result_refs,
                        wrap(second).result_refs,
                        wrap(narrowed).result_refs,
                    }
                ),
                4,
            )
        finally:
            fixture.tearDown()

    def test_same_issue_after_acl_expansion_and_regrant_gets_new_effect_and_safe_replay(
        self,
    ):
        for family in ("finite", "semantic", "relationship"):
            for streamed in (False, True):
                with self.subTest(family=family, stream=streamed):
                    fixture = (
                        relationship_fixtures.RelationshipExecutionTests()
                        if family == "relationship"
                        else graph_fixtures.ExecutionGraphTests()
                    )
                    fixture.setUp()
                    try:
                        store, owner = fixture.store, fixture.owner
                        session, source = (
                            ("scene", "story")
                            if family == "relationship"
                            else ("s", "source")
                        )
                        store.set_readers(session, owner, source, {owner.subject_id})
                        request = (
                            fixture.request
                            if family == "relationship"
                            else (
                                fixture.semantic_request()
                                if family == "semantic"
                                else fixture.request()
                            )
                        )
                        candidate = (
                            fixture.relational_candidate()
                            if family == "relationship"
                            else fixture.candidate() if family == "semantic" else None
                        )

                        def run(req):
                            port = OfflineModelPort(
                                "unused" if candidate is None else json.dumps(candidate)
                            )
                            client = HCL(
                                store,
                                principal=owner,
                                gateway=ModelGateway(store, port),
                            )

                            async def collect():
                                return [e async for e in client.stream(req)]

                            answer = (
                                asyncio.run(collect())[-1].result
                                if streamed
                                else client.run_sync(req)
                            )
                            return answer, port, client

                        initial, _, _ = run(request)
                        self.assertEqual(
                            initial.status, "COMPLETED", initial.diagnostics
                        )
                        initial_task = dict(
                            store._db.execute(
                                "SELECT * FROM tasks WHERE request_id=?",
                                (request.request_id,),
                            ).fetchone()
                        )
                        initial_result = store._get_object(initial_task["result_hash"])
                        old_rows = [
                            dict(r)
                            for r in store._db.execute("SELECT * FROM inferences")
                        ]
                        old_objects = {
                            r["object_hash"]: store._get_object(r["object_hash"])
                            for r in old_rows
                        }
                        for change in ("expand", "regrant"):
                            if change == "regrant":
                                store.set_readers(session, owner, source, {"bob"})
                                denied = HCL(store, principal=owner).run_sync(request)
                                self.assertEqual(denied.status, "DENIED")
                                self.assertFalse(denied.answer or denied.claim_records)
                                store.set_readers(
                                    session, owner, source, {owner.subject_id}
                                )
                            else:
                                store.set_readers(
                                    session, owner, source, {owner.subject_id, "bob"}
                                )
                            fresh = replace(request, request_id="fresh-" + change)
                            result, port, client = run(fresh)
                            self.assertEqual(
                                result.status, "COMPLETED", result.diagnostics
                            )
                            self.assertNotEqual(
                                result.execution_receipt["result_ids"],
                                initial.execution_receipt["result_ids"],
                            )
                            self.assertEqual(
                                port.attempts, 0 if family == "finite" else 1
                            )
                            with patch.object(
                                LocalModelOperator,
                                "run",
                                side_effect=AssertionError(
                                    "cached result must not be recomputed"
                                ),
                            ):
                                replay = client.run_sync(fresh)
                            self.assertEqual(
                                (replay.answer, replay.claim_records),
                                (result.answer, result.claim_records),
                            )
                            self.assertEqual(
                                port.attempts, 0 if family == "finite" else 1
                            )
                            self.assertEqual(
                                dict(
                                    store._db.execute(
                                        "SELECT * FROM tasks WHERE request_id=?",
                                        (request.request_id,),
                                    ).fetchone()
                                ),
                                initial_task,
                            )
                            self.assertEqual(
                                store._get_object(initial_task["result_hash"]),
                                initial_result,
                            )
                            for row in old_rows:
                                self.assertEqual(
                                    dict(
                                        store._db.execute(
                                            "SELECT * FROM inferences WHERE session_id=? AND result_id=?",
                                            (row["session_id"], row["result_id"]),
                                        ).fetchone()
                                    ),
                                    row,
                                )
                            for digest, value in old_objects.items():
                                self.assertEqual(store._get_object(digest), value)
                    finally:
                        fixture.tearDown()

    def test_same_context_new_request_reuses_exact_effect_after_unrelated_write(self):
        fixture = relationship_fixtures.RelationshipExecutionTests()
        fixture.setUp()
        try:
            request = fixture.request
            candidate = fixture.relational_candidate()
            first, _ = fixture.run_candidate(candidate, request)
            fixture.store.put_source(
                "scene", fixture.owner, "unrelated", "irrelevant information"
            )
            later, _ = fixture.run_candidate(
                candidate, replace(request, request_id="another")
            )
            self.assertEqual(later.status, "COMPLETED", later.diagnostics)
            self.assertEqual(
                first.execution_receipt["result_ids"],
                later.execution_receipt["result_ids"],
            )
            self.assertEqual(len(fixture.store.inferences("scene", fixture.owner)), 1)
        finally:
            fixture.tearDown()


if __name__ == "__main__":
    unittest.main()
