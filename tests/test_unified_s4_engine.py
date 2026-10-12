"""Ordinary source proposals reach actual argument semantics in the one engine."""

from dataclasses import replace
from pathlib import Path
import asyncio
import json
import tempfile
import unittest
from unittest.mock import patch

from hcl import HCL, ExecutionBudget, ExecutionIssue
from hcl.kernel.types import Principal, TaskRequest, Issue, HCLFailure, thaw
from hcl.memory.store import StateStore
from hcl.models.gateway import ModelGateway, OfflineModelPort
from hcl.semantics.segments import segment_snapshot


class ArgumentExecutionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "state.sqlite"
        self.owner = Principal("tenant", "reader")
        self.store = StateStore.sqlite(self.path, revision=True)
        self.store.create_session("s", self.owner)
        self.handle = self.store.put_source(
            "s",
            self.owner,
            "text",
            "甲引用一位目击者，认为有可靠见证便通常应当相信该事件。乙否认该事件。记录也提到双方约在星期二见面。",
        )
        self.request = TaskRequest(
            "argument",
            "按照这些前提和规则，哪一论证可接受？什么改变能动摇它？",
            (self.handle,),
            "s",
            self.owner,
            budget=ExecutionBudget(
                max_mock_calls=3,
                max_output_bytes=65536,
                max_visible_output_tokens=65536,
                max_total_output_bytes=524288,
            ),
            issue=ExecutionIssue("root", goals=(Issue("debate", "argument.evaluate"),)),
        )

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def candidate(self, request=None, prefer=True, undercut=False):
        request = request or self.request
        segments = segment_snapshot(
            self.store.snapshot("s", self.owner, request.source_handles),
            request.question,
        )
        refs = [s.segment_id for s in segments if s.kind == "SOURCE"]
        questions = [s.segment_id for s in segments if s.kind == "QUESTION"]
        literals = [
            dict(id=key, atom=atom, negative=negative, kind=kind, segment_ids=refs)
            for key, atom, negative, kind in [
                ("witness", "witness", False, "CLAIM"),
                ("event", "event", False, "CLAIM"),
                ("not-event", "event", True, "CLAIM"),
                ("meeting", "meeting", False, "CLAIM"),
                ("undercut", "from-witness", True, "RULE_APPLICABLE"),
            ]
        ]
        premises = [
            dict(
                id=key,
                literal=literal,
                ordinary=ordinary,
                assumptions=[],
                segment_ids=refs,
            )
            for key, literal, ordinary in [
                ("witness-report", "witness", False),
                ("denial", "not-event", True),
                ("meeting-report", "meeting", False),
            ]
        ]
        if undercut:
            premises.append(
                dict(
                    id="credibility-defeater",
                    literal="undercut",
                    ordinary=False,
                    assumptions=[],
                    segment_ids=refs,
                )
            )
        model = dict(
            id="debate-model",
            source_id="text",
            frame_kind="SOURCE_DISCOURSE",
            assumptions=["reconstruction"],
            active_assumptions=["reconstruction", "normally-reliable"],
            unmodeled_segments=[],
            literals=literals,
            premises=premises,
            rules=[
                dict(
                    id="from-witness",
                    premises=["witness"],
                    conclusion="event",
                    strict=False,
                    assumptions=["normally-reliable"],
                    segment_ids=refs,
                )
            ],
            priorities=[
                dict(
                    better="from-witness" if prefer else "denial",
                    worse="denial" if prefer else "from-witness",
                    segment_ids=refs,
                )
            ],
            queries=[
                dict(
                    id="event-query",
                    literal="event",
                    preferred=True,
                    critical_candidates=["witness-report", "from-witness", "denial"],
                    segment_ids=questions,
                ),
                dict(
                    id="meeting-query",
                    literal="meeting",
                    preferred=False,
                    critical_candidates=[],
                    segment_ids=questions,
                ),
            ],
        )
        return dict(schema="hcl-argument-candidates-1", models=[model])

    def run_candidate(self, candidate=None, request=None):
        request = request or self.request
        port = OfflineModelPort(
            json.dumps(candidate or self.candidate(request), ensure_ascii=False)
        )
        result = HCL(
            self.store, principal=self.owner, gateway=ModelGateway(self.store, port)
        ).run_sync(request)
        return result, port

    def inference(self, result):
        identity = result.execution_receipt["result_ids"][0]
        with self.store._transaction() as db:
            session = self.store._session(db, "s", self.owner)
            row = db.execute(
                "SELECT * FROM inferences WHERE session_id=? AND result_id=?",
                ("s", identity),
            ).fetchone()
            self.store._validate_dependencies(
                db,
                session,
                self.owner,
                json.loads(row["read_set"]),
                row["epoch"],
                session["rule"],
            )
            return self.store._get_object(row["object_hash"])

    def test_actual_rule_defeat_and_critical_edit_values_are_consumed(self):
        result, port = self.run_candidate()
        self.assertEqual(result.status, "COMPLETED", result.diagnostics)
        model = self.inference(result).values["models"][0]
        self.assertTrue(model["queries"][0]["positive_accepted"])
        self.assertFalse(model["queries"][0]["opposed_accepted"])
        self.assertEqual(model["queries"][0]["critical"]["minimum_cardinality"], 1)
        self.assertEqual(model["queries"][0]["preferred"]["status"], "COMPLETE")
        fields = [
            f
            for c in result.claim_records
            for f in c.used_result_fields
            if getattr(f, "path", ()) == ("0", "queries", "0")
        ]
        self.assertEqual(len(fields), 1)
        self.assertEqual(fields[0].value["positive_accepted"], True)
        self.assertIn("grounded accepted=True", result.answer)
        self.assertIn("not premise truth", result.answer)
        self.assertEqual(port.attempts, 1)

    def test_changed_priority_and_undercut_recompute_and_preserve_unrelated_claim(self):
        first, _ = self.run_candidate()
        before = self.inference(first).values["models"][0]
        for name, prefer, undercut in [
            ("reversed", False, False),
            ("undercut", True, True),
        ]:
            request = replace(self.request, request_id=name)
            result, _ = self.run_candidate(
                self.candidate(request, prefer, undercut), request
            )
            self.assertEqual(result.status, "COMPLETED", result.diagnostics)
            model = self.inference(result).values["models"][0]
            self.assertFalse(model["queries"][0]["positive_accepted"])
            self.assertTrue(model["queries"][0]["opposed_accepted"])
            self.assertEqual(
                before["queries"][1]["positive_accepted"],
                model["queries"][1]["positive_accepted"],
            )
            if undercut:
                self.assertIn("UNDERCUTTING", {row["kind"] for row in model["attacks"]})

    def test_withdraw_rule_assumption_removes_acceptance_without_rewriting_source(self):
        candidate = self.candidate()
        candidate["models"][0]["active_assumptions"].remove("normally-reliable")
        result, _ = self.run_candidate(candidate)
        self.assertEqual(result.status, "COMPLETED", result.diagnostics)
        model = self.inference(result).values["models"][0]
        self.assertFalse(model["queries"][0]["positive_accepted"])
        self.assertTrue(model["queries"][1]["positive_accepted"])
        self.assertEqual(
            self.store.snapshot("s", self.owner, (self.handle,)).source_versions[
                "text"
            ],
            1,
        )

    def test_answer_cannot_replace_actual_acceptance_with_a_supplied_label(self):
        from hcl.runtime.answer import AnswerAssembler

        result, _ = self.run_candidate()
        inference = self.inference(result)
        values = thaw(inference.values)
        values["models"][0]["queries"][0]["positive_accepted"] = False
        with self.assertRaises(HCLFailure) as caught:
            AnswerAssembler()._claim(replace(inference, values=values))
        self.assertEqual(
            caught.exception.diagnostic.code, "ARGUMENT_ACCEPTANCE_MISMATCH"
        )
        candidate = self.candidate()
        candidate["models"][0]["answer"] = "accepted"
        request = replace(
            self.request,
            request_id="preencoded",
            budget=replace(self.request.budget, max_feedback=0),
        )
        result, port = self.run_candidate(candidate, request)
        self.assertEqual(result.status, "INVALID_REQUEST")
        self.assertEqual(port.attempts, 1)

    def test_grounded_acceptance_is_not_a_count_of_supports_or_forced_choice(self):
        candidate = self.candidate()
        candidate["models"][0]["priorities"] = []
        result, _ = self.run_candidate(candidate)
        self.assertEqual(result.status, "COMPLETED", result.diagnostics)
        model = self.inference(result).values["models"][0]
        query = model["queries"][0]
        self.assertEqual(
            (query["positive_accepted"], query["opposed_accepted"]), (False, False)
        )
        self.assertEqual(len(query["preferred"]["preferred"]), 2)
        self.assertTrue(any(row["top"] == "from-witness" for row in model["arguments"]))
        self.assertTrue(model["queries"][1]["positive_accepted"])

    def test_budget_and_argument_explosion_keep_unknown_labels_not_partial_certainty(
        self,
    ):
        request = replace(
            self.request,
            budget=replace(
                self.request.budget, max_local_evaluations=1, max_feedback=0
            ),
        )
        result, _ = self.run_candidate(self.candidate(request), request)
        self.assertEqual(result.status, "PARTIAL", result.diagnostics)
        self.assertEqual(result.usage["local_evaluations"], 1)
        model = self.inference(result).values["models"][0]
        self.assertTrue(model["queries"][0]["positive_accepted"])
        self.assertEqual(
            model["queries"][0]["preferred"]["status"], "FRONTIER_UNEXPLORED"
        )
        self.assertIsNone(model["queries"][0]["critical"]["minimum_cardinality"])
        request = replace(
            self.request,
            request_id="argument-frontier",
            budget=replace(self.request.budget, max_feedback=0),
        )
        candidate = self.candidate(request)
        m = candidate["models"][0]
        base = m["premises"][0]
        m["premises"] = [dict(base, id="witness-" + str(i)) for i in range(16)]
        m["rules"][0]["premises"] = ["witness", "witness", "witness"]
        m["priorities"] = []
        for query in m["queries"]:
            query["critical_candidates"] = []
        result, _ = self.run_candidate(candidate, request)
        self.assertEqual(result.status, "PARTIAL", result.diagnostics)
        model = self.inference(result).values["models"][0]
        self.assertEqual(model["labels"], {})
        self.assertIsNone(model["queries"][0]["positive_accepted"])
        self.assertIn("ARGUMENT_COUNT_BOUND", model["frontier"])

    def test_unknown_unicode_anchor_priority_cycles_and_question_facts_fail_safely(
        self,
    ):
        for index, mutation in enumerate(("foreign", "question", "cycle", "unicode")):
            request = replace(
                self.request,
                request_id="invalid-" + str(index),
                budget=replace(self.request.budget, max_feedback=0),
            )
            candidate = self.candidate(request)
            model = candidate["models"][0]
            if mutation == "foreign":
                model["premises"][0]["segment_ids"] = ["private-foreign"]
            elif mutation == "question":
                model["premises"][0]["segment_ids"] = model["queries"][0]["segment_ids"]
            elif mutation == "cycle":
                model["priorities"].append(
                    dict(model["priorities"][0], better="denial", worse="from-witness")
                )
            else:
                model["literals"][0]["atom"] = "\ud800"
            if mutation == "unicode":
                port = OfflineModelPort(json.dumps(candidate, ensure_ascii=True))
                result = HCL(
                    self.store,
                    principal=self.owner,
                    gateway=ModelGateway(self.store, port),
                ).run_sync(request)
            else:
                result, port = self.run_candidate(candidate, request)
            self.assertEqual(result.status, "INVALID_REQUEST", result.diagnostics)
            self.assertFalse(result.answer)
            self.assertEqual(port.attempts, 1)
        self.assertEqual(self.store.inferences("s", self.owner), ())

    def test_returned_candidate_recovers_without_send_and_stream_replay_matches(self):
        from hcl.runtime.recovery import RecoveryManager
        from tests.test_unified_s23_recovery import Crash

        owner_id = self.store.owner_id
        candidate = self.candidate()
        first = OfflineModelPort(json.dumps(candidate))
        client = HCL(
            self.store, principal=self.owner, gateway=ModelGateway(self.store, first)
        )

        def crash(stage):
            if stage == "return_persisted":
                raise Crash()

        with patch.object(self.store, "_checkpoint", crash), self.assertRaises(Crash):
            client.run_sync(self.request)
        self.store.close()
        self.store = StateStore.sqlite(self.path)
        RecoveryManager(self.store).resume_execution(
            self.request, expected_owner_id=owner_id
        )
        second = OfflineModelPort()
        client = HCL(
            self.store, principal=self.owner, gateway=ModelGateway(self.store, second)
        )

        async def stream():
            return [event async for event in client.stream(self.request)]

        events = asyncio.run(stream())
        result = events[-1].result
        self.assertEqual(result.status, "COMPLETED", result.diagnostics)
        self.assertEqual((first.attempts, second.attempts), (1, 0))
        self.assertEqual(
            client.run_sync(self.request).claim_records, result.claim_records
        )

    def test_revoke_after_computation_clears_every_argument_projection_and_replay(self):
        peer = StateStore.sqlite(self.path)

        def revoke(stage):
            if stage == "task_finished":
                peer.set_readers("s", self.owner, "text", {"other"})

        try:
            with patch.object(self.store, "_checkpoint", revoke):
                result, port = self.run_candidate()
            self.assertEqual(result.status, "DENIED")
            self.assertFalse(result.answer)
            self.assertEqual(result.claim_records, ())
            self.assertNotIn("result_ids", result.execution_receipt)
            self.store.close()
            self.store = StateStore.sqlite(self.path)
            port = OfflineModelPort()
            client = HCL(
                self.store, principal=self.owner, gateway=ModelGateway(self.store, port)
            )

            async def stream():
                return [event async for event in client.stream(self.request)]

            repeated = asyncio.run(stream())[-1].result
            self.assertEqual(repeated.status, "DENIED")
            self.assertFalse(repeated.answer)
            self.assertEqual(port.attempts, 0)
        finally:
            peer.close()

    def test_model_scopes_and_root_assumptions_survive_actual_proof_construction(self):
        from copy import deepcopy

        candidate = self.candidate()
        other = deepcopy(candidate["models"][0])
        other["id"] = "competing-reading"
        other["priorities"][0]["better"], other["priorities"][0]["worse"] = (
            "denial",
            "from-witness",
        )
        candidate["models"].append(other)
        result, _ = self.run_candidate(candidate)
        self.assertEqual(result.status, "COMPLETED", result.diagnostics)
        models = self.inference(result).values["models"]
        self.assertTrue(models[0]["queries"][0]["positive_accepted"])
        self.assertFalse(models[1]["queries"][0]["positive_accepted"])
        self.assertNotEqual(
            models[0]["queries"][0]["literal"]["scope"],
            models[1]["queries"][0]["literal"]["scope"],
        )
        self.assertFalse(
            set(row["argument_id"] for row in models[0]["arguments"])
            & set(row["argument_id"] for row in models[1]["arguments"])
        )
        for model in models:
            self.assertTrue(
                all(
                    "reconstruction" in row["assumptions"] for row in model["arguments"]
                )
            )
        candidate["models"][0]["active_assumptions"].remove("reconstruction")
        updated, _ = self.run_candidate(
            candidate, replace(self.request, request_id="withdraw-reading")
        )
        self.assertEqual(updated.status, "PARTIAL")
        new = self.inference(updated).values["models"]
        self.assertEqual(new[0]["arguments"], ())
        self.assertEqual(new[1]["queries"], models[1]["queries"])

    def test_strict_contradiction_is_visible_partial_and_does_not_explode(self):
        candidate = self.candidate()
        model = candidate["models"][0]
        model["rules"][0]["strict"] = True
        model["premises"][1]["ordinary"] = False
        result, _ = self.run_candidate(candidate)
        self.assertEqual(result.status, "PARTIAL", result.diagnostics)
        computed = self.inference(result).values["models"][0]
        self.assertEqual(computed["theory_consistency"], "INCONSISTENT_STRICT_CORE")
        self.assertEqual(
            (
                computed["queries"][0]["positive_accepted"],
                computed["queries"][0]["opposed_accepted"],
            ),
            (True, True),
        )
        self.assertIn("strict reconstructed core is inconsistent", result.answer)

    def test_cycle_scope_iterations_and_exclusion_survive_compact_replay(self):
        candidate = self.candidate()
        model = candidate["models"][0]
        model["rules"].append(
            dict(
                id="event-witness",
                premises=["event"],
                conclusion="witness",
                strict=True,
                assumptions=[],
                segment_ids=model["rules"][0]["segment_ids"],
            )
        )
        result, _ = self.run_candidate(candidate)
        self.assertEqual(result.status, "PARTIAL", result.diagnostics)
        computed = self.inference(result).values["models"][0]
        self.assertEqual(computed["excluded_circular_rules"], ("event-witness",))
        self.assertTrue(computed["iterations"])
        self.assertIn("finite acyclic proofs", result.answer)
        self.assertIn("declared retraction set", result.answer)
        self.assertIn("Excluded circular proof rules: event-witness", result.answer)
        projection = next(
            f.value
            for c in result.claim_records
            for f in c.used_result_fields
            if getattr(f, "path", ()) == ("0",)
        )
        for key in ("iterations", "excluded_circular_rules", "acceptance_scope"):
            self.assertEqual(projection[key], computed[key])
        self.store.close()
        self.store = StateStore.sqlite(self.path, revision=True)
        port = OfflineModelPort("NEVER_SEND")
        client = HCL(
            self.store, principal=self.owner, gateway=ModelGateway(self.store, port)
        )

        async def replay():
            return [e async for e in client.stream(self.request)]

        repeated = asyncio.run(replay())[-1].result
        self.assertEqual(repeated.answer, result.answer)
        self.assertEqual(repeated.claim_records, result.claim_records)
        self.assertEqual(port.attempts, 0)

    def test_multisource_proof_attribution_is_exact_and_secondary_acl_still_gates(self):
        other = self.store.put_source(
            "s", self.owner, "other", "另一份独立记录否认该事件。"
        )
        candidate = self.candidate()
        request = replace(self.request, source_handles=(self.handle, other))
        other_refs = [
            s.segment_id
            for s in segment_snapshot(
                self.store.snapshot("s", self.owner, request.source_handles),
                request.question,
            )
            if s.source_id == "other"
        ]
        model = candidate["models"][0]
        model["premises"][1]["segment_ids"] = other_refs
        model["literals"][2]["segment_ids"] = other_refs
        result, _ = self.run_candidate(candidate, request)
        self.assertEqual(result.status, "COMPLETED", result.diagnostics)
        computed = self.inference(result).values["models"][0]
        self.assertEqual(computed["namespace_source_id"], "text")
        self.assertEqual(
            dict(computed["input_source_versions"]), {"text": 1, "other": 1}
        )
        for row in computed["arguments"]:
            expected = {"other"} if row["top"] == "denial" else {"text"}
            self.assertEqual(
                {
                    computed["source_bindings"][key]["source_id"]
                    for key in row["source_segment_ids"]
                },
                expected,
            )
        projection = next(
            f.value
            for c in result.claim_records
            for f in c.used_result_fields
            if getattr(f, "path", ()) == ("0",)
        )
        self.assertEqual(projection["source_bindings"], computed["source_bindings"])
        self.assertEqual(projection["source_records"], computed["source_records"])
        self.assertIn("actual input sources: other, text", result.answer)
        self.store.set_readers("s", self.owner, "other", {"someone-else"})
        port = OfflineModelPort("NEVER_SEND")
        denied = HCL(
            self.store, principal=self.owner, gateway=ModelGateway(self.store, port)
        ).run_sync(request)
        self.assertEqual(denied.status, "DENIED")
        self.assertFalse(denied.answer)
        self.assertFalse(denied.claim_records)
        self.assertNotIn("source_bindings", str(denied.execution_receipt))
        self.assertEqual(port.attempts, 0)

    def test_unanchored_namespace_and_tampered_proof_or_scope_fail_closed(self):
        from copy import deepcopy
        from hcl.runtime.answer import AnswerAssembler

        other = self.store.put_source(
            "s", self.owner, "other", "此源没有参与模型中的任何一条主张。"
        )
        candidate = self.candidate()
        request = replace(
            self.request,
            source_handles=(self.handle, other),
            budget=replace(self.request.budget, max_feedback=0),
        )
        other_refs = [
            s.segment_id
            for s in segment_snapshot(
                self.store.snapshot("s", self.owner, request.source_handles),
                request.question,
            )
            if s.source_id == "other"
        ]
        candidate["models"][0]["source_id"] = "other"
        candidate["models"][0]["unmodeled_segments"] = other_refs
        result, _ = self.run_candidate(candidate, request)
        self.assertEqual(result.status, "INVALID_REQUEST")
        normal, _ = self.run_candidate(
            request=replace(self.request, request_id="normal")
        )
        inference = self.inference(normal)
        for corruption in ("scope", "provenance", "unfinished"):
            values = thaw(inference.values)
            model = values["models"][0]
            if corruption == "scope":
                model["acceptance_scope"] = "UNRESTRICTED_TRUTH"
            elif corruption == "provenance":
                model["arguments"][0]["source_segment_ids"] = other_refs
            else:
                model["queries"][0]["status"] = "FRONTIER_UNEXPLORED"
            with self.assertRaises(HCLFailure):
                AnswerAssembler()._claim(replace(inference, values=values))
