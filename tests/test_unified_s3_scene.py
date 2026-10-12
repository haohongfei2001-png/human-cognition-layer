"""Ordinary sources -> proposed mechanisms -> actual mental/planning values."""

from dataclasses import replace
from pathlib import Path
import json
import asyncio
from unittest.mock import patch
import tempfile
import unittest

from hcl import HCL, ExecutionIssue, ExecutionBudget
from hcl.kernel.types import Principal, TaskRequest, Issue
from hcl.memory.store import StateStore
from hcl.models.gateway import ModelGateway, OfflineModelPort
from hcl.semantics.segments import segment_snapshot
from tests.test_unified_s3_agency import route_model


class SceneExecutionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "state.sqlite"
        self.owner = Principal("tenant", "alice-host")
        self.store = StateStore.sqlite(self.path, revision=True)
        self.store.create_session("scene", self.owner)
        self.handle = self.store.put_source(
            "scene",
            self.owner,
            "story",
            "安和柏看见通道开放。安离开后，柏关上通道。安准备去会场。",
        )
        self.question = "安会选择直走还是绕行？她与柏的信息有何不同？"
        self.budget = ExecutionBudget(
            max_mock_calls=3,
            max_output_bytes=65536,
            max_visible_output_tokens=65536,
            max_total_output_bytes=524288,
        )

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def request(self, **kw):
        return replace(
            TaskRequest(
                "scene-request",
                self.question,
                (self.handle,),
                "scene",
                self.owner,
                budget=self.budget,
                issue=ExecutionIssue(
                    "task", goals=(Issue("mental", "mental.simulate"),)
                ),
            ),
            **kw
        )

    def candidate(self, request=None, seen=False, message=None):
        request = request or self.request()
        segments = segment_snapshot(
            self.store.snapshot("scene", self.owner, request.source_handles),
            request.question,
        )
        sources = [s.segment_id for s in segments if s.kind == "SOURCE"]
        questions = [s.segment_id for s in segments if s.kind == "QUESTION"]
        source_refs = {
            s.source_id: [
                item.segment_id for item in segments if item.source_id == s.source_id
            ]
            for s in segments
            if s.kind == "SOURCE"
        }

        def query(identity, agent, at):
            return dict(
                id=identity,
                at=at,
                formula={
                    "op": "believes",
                    "agent": agent,
                    "arg": {"op": "atom", "name": "open"},
                },
                segment_ids=questions,
            )

        typed = route_model()
        graph = dict(
            states=list(typed.states),
            terminal=list(typed.terminal),
            utilities=dict(typed.utilities),
            horizon=2,
            actions=[
                dict(
                    id=a.action_id,
                    cost=a.cost,
                    enabled=list(a.enabled),
                    feasible=list(a.feasible),
                    transitions=dict(a.transitions),
                    observations=dict(a.observations),
                )
                for a in typed.actions
            ],
        )

        def plan(identity, at):
            return dict(
                id=identity,
                actor="a",
                at=at,
                graph=graph,
                bindings=[
                    dict(state="open", when={"op": "atom", "name": "open"}),
                    dict(
                        state="closed",
                        when={"op": "not", "arg": {"op": "atom", "name": "open"}},
                    ),
                ],
                weights=None,
                policy=None,
                segment_ids=sources,
            )

        events = [
            dict(
                id="closure",
                at=1,
                kind="change",
                effects={"open": False},
                seen_by=["a", "b"] if seen else ["b"],
                received_by=[],
                understood_by=[],
                trusted_by=[],
                assumptions=["unobserved-change-not-automatically-known"],
                segment_ids=source_refs["story"],
            )
        ]
        if message is not None:
            events.append(
                dict(
                    id="message",
                    at=2,
                    kind="message",
                    effects={"open": False},
                    seen_by=[],
                    received_by=["a"] if message else [],
                    understood_by=["a"] if message else [],
                    trusted_by=["a"] if message else [],
                    assumptions=["message-meaning-and-trust"],
                    segment_ids=source_refs["late"],
                )
            )
        model = dict(
            id="route-scene",
            source_id="story",
            frame_kind="SOURCE_DISCOURSE",
            assumptions=["local-observation-model", "persistence-unless-update"],
            active_assumptions=[
                "local-observation-model",
                "persistence-unless-update",
                "unobserved-change-not-automatically-known",
                *(["message-meaning-and-trust"] if message is not None else []),
            ],
            unmodeled_segments=[],
            agents=[
                dict(
                    id=identity,
                    label=label,
                    source_id="story",
                    segment_ids=source_refs["story"],
                )
                for identity, label in (("a", "安"), ("b", "柏"))
            ],
            variables=[
                dict(
                    id="open",
                    initial=True,
                    observed_by=["a", "b"],
                    segment_ids=source_refs["story"],
                )
            ],
            events=events,
            queries=[query("a-at-action", "a", 1), query("b-at-action", "b", 1)],
            plans=[plan("route-at-action", 1)],
            causal=[],
        )
        if message is not None:
            model["queries"].append(query("a-after-message", "a", 2))
            model["plans"].append(plan("route-after-message", 2))
        return dict(schema="hcl-mental-scene-candidates-1", models=[model])

    def run_model(self, request=None, candidate=None):
        request = request or self.request()
        candidate = candidate or self.candidate(request)
        port = OfflineModelPort(json.dumps(candidate, ensure_ascii=False))
        result = HCL(
            self.store, principal=self.owner, gateway=ModelGateway(self.store, port)
        ).run_sync(request)
        return result, port

    def test_normal_source_implicit_wrong_belief_drives_actual_action_values(self):
        result, port = self.run_model()
        self.assertEqual(result.status, "COMPLETED", result.diagnostics)
        self.assertEqual(port.attempts, 1)
        stored = self.store.inferences("scene", self.owner)[0]
        model = stored.values["models"][0]
        self.assertEqual(model["beliefs"][0]["possible_values"], (True,))
        self.assertEqual(model["beliefs"][1]["possible_values"], (False,))
        self.assertEqual(
            dict(model["plans"][0]["q"]), {"direct": "5", "detour-start": "3"}
        )
        self.assertEqual(
            model["plans"][0]["belief_variable_id"],
            model["shared_variables"][0]["variable_id"],
        )
        self.assertIn('"direct": "5"', result.answer)
        self.assertIn("not private mental truth", result.answer)
        used = result.claim_records[0].used_result_fields
        plans = [
            field for field in used if getattr(field, "path", ()) == ("0", "plans", "0")
        ]
        self.assertEqual(len(plans), 1)
        self.assertEqual(plans[0].value["q"], model["plans"][0]["q"])
        self.assertEqual(
            plans[0].value["belief_variable_id"],
            model["shared_variables"][0]["variable_id"],
        )

    def test_late_message_changes_future_prediction_but_not_action_time_or_analyst_only_view(
        self,
    ):
        late = self.store.put_source(
            "scene", self.owner, "late", "稍后，安收到并采信柏的通道关闭消息。"
        )
        request = self.request(source_handles=(self.handle, late))
        result, port = self.run_model(request, self.candidate(request, message=True))
        self.assertEqual(result.status, "COMPLETED", result.diagnostics)
        model = self.store.inferences("scene", self.owner)[0].values["models"][0]
        self.assertEqual(model["plans"][0]["best_actions"], ("direct",))
        self.assertEqual(model["plans"][1]["best_actions"], ("detour-start",))
        other = replace(request, request_id="analyst-only")
        result, _ = self.run_model(other, self.candidate(other, message=False))
        self.assertEqual(result.status, "COMPLETED", result.diagnostics)
        current = [
            r
            for r in self.store.inferences("scene", self.owner)
            if r.result_id in result.execution_receipt["result_ids"]
        ][0]
        model = current.values["models"][0]
        self.assertEqual(model["plans"][0]["best_actions"], ("direct",))
        self.assertEqual(model["plans"][1]["best_actions"], ("direct",))

    def test_observation_only_change_reverses_q_and_retains_goal(self):
        result, _ = self.run_model(candidate=self.candidate(seen=True))
        self.assertEqual(result.status, "COMPLETED", result.diagnostics)
        model = self.store.inferences("scene", self.owner)[0].values["models"][0]
        self.assertEqual(
            dict(model["plans"][0]["q"]), {"direct": "-1", "detour-start": "3"}
        )
        self.assertEqual(model["plans"][0]["best_actions"], ("detour-start",))
        self.assertIn(
            "unobserved-change-not-automatically-known",
            model["beliefs"][0]["assumptions"],
        )
        self.assertEqual(
            model["shared_variables"][0]["assumptions"],
            model["beliefs"][0]["assumptions"],
        )

    def test_withdrawn_persistence_or_event_assumption_cannot_keep_its_belief(self):
        for index, name in enumerate(
            ("persistence-unless-update", "unobserved-change-not-automatically-known")
        ):
            candidate = self.candidate()
            candidate["models"][0]["active_assumptions"].remove(name)
            result, _ = self.run_model(
                replace(self.request(), request_id="withdraw-" + str(index)), candidate
            )
            self.assertEqual(result.status, "PARTIAL", result.diagnostics)
            self.assertIn("Withdrawn model assumptions", result.answer)
            self.assertNotIn('"direct": "5"', result.answer)
            stored = next(
                row
                for row in self.store.inferences("scene", self.owner)
                if row.result_id in result.execution_receipt["result_ids"]
            )
            self.assertNotIn(name, stored.assumption_environments)

    def test_precomputed_answers_foreign_anchors_and_nonfinite_costs_are_rejected(self):
        for index, field in enumerate(
            ("belief_answer", "foreign_anchor", "rational_cost")
        ):
            candidate = self.candidate()
            model = candidate["models"][0]
            if field == "belief_answer":
                model["result"] = {"alice_believes_open": True}
            elif field == "foreign_anchor":
                model["events"][0]["segment_ids"] = ["foreign-private-segment"]
            else:
                model["plans"][0]["graph"]["actions"][0]["cost"] = "1/0"
            request = replace(
                self.request(),
                request_id="invalid-" + str(index),
                budget=replace(self.budget, max_feedback=0),
            )
            result, port = self.run_model(request, candidate)
            self.assertEqual(result.status, "INVALID_REQUEST", result.diagnostics)
            self.assertEqual(port.attempts, 1)
            self.assertFalse(result.answer)
            self.assertEqual(self.store.inferences("scene", self.owner), ())

    def test_live_source_text_cannot_make_character_access_equal_system_acl(self):
        self.store.set_readers("scene", self.owner, "story", {"other-reader"})
        port = OfflineModelPort("never-called")
        result = HCL(
            self.store, principal=self.owner, gateway=ModelGateway(self.store, port)
        ).run_sync(self.request())
        self.assertEqual(result.status, "DENIED")
        self.assertEqual(port.attempts, 0)
        self.assertFalse(result.answer)
        self.assertNotIn("model_id", str(dict(result.execution_receipt)))

    def test_known_candidate_return_recovers_without_resending_and_stream_matches(self):
        from hcl.runtime.recovery import RecoveryManager
        from tests.test_unified_s23_recovery import Crash

        request = self.request()
        candidate = self.candidate()
        old_owner = self.store.owner_id
        port = OfflineModelPort(json.dumps(candidate, ensure_ascii=False))
        client = HCL(
            self.store, principal=self.owner, gateway=ModelGateway(self.store, port)
        )

        def stop(stage):
            if stage == "return_persisted":
                raise Crash()

        with patch.object(self.store, "_checkpoint", stop), self.assertRaises(Crash):
            client.run_sync(request)
        self.store.close()
        self.store = StateStore.sqlite(self.path)
        RecoveryManager(self.store).resume_execution(
            request, expected_owner_id=old_owner
        )
        second = OfflineModelPort()
        client = HCL(
            self.store, principal=self.owner, gateway=ModelGateway(self.store, second)
        )

        async def stream():
            return [event async for event in client.stream(request)]

        events = asyncio.run(stream())
        result = events[-1].result
        self.assertEqual(result.status, "COMPLETED", result.diagnostics)
        self.assertEqual((port.attempts, second.attempts), (1, 0))
        self.assertEqual([event.kind for event in events], ["status", "result"])
        self.assertEqual(client.run_sync(request).claim_records, result.claim_records)

    def test_late_delivery_revoke_clears_all_cognitive_values_and_cached_replay(self):
        peer = StateStore.sqlite(self.path)
        request = self.request()
        candidate = self.candidate()

        def revoke(stage):
            if stage == "task_finished":
                peer.set_readers("scene", self.owner, "story", {"other-reader"})

        try:
            with patch.object(self.store, "_checkpoint", revoke):
                result, port = self.run_model(request, candidate)
            self.assertEqual(result.status, "DENIED")
            self.assertFalse(result.answer)
            self.assertEqual(result.claim_records, ())
            self.assertNotIn("result_ids", result.execution_receipt)
            self.store.close()
            self.store = StateStore.sqlite(self.path)
            repeated = HCL(self.store, principal=self.owner).run_sync(request)
            self.assertEqual(repeated.status, "DENIED")
            self.assertFalse(repeated.answer)
        finally:
            peer.close()

    def current_model(self, result):
        ids = tuple(result.execution_receipt["result_ids"])
        self.assertEqual(len(ids), 1)
        with self.store._transaction() as db:
            session = self.store._session(db, "scene", self.owner)
            row = db.execute(
                "SELECT * FROM inferences WHERE session_id=? AND result_id=?",
                ("scene", ids[0]),
            ).fetchone()
            self.store._validate_dependencies(
                db,
                session,
                self.owner,
                json.loads(row["read_set"]),
                row["epoch"],
                session["rule"],
            )
            return self.store._get_object(row["object_hash"]).values["models"][0]

    def test_causal_observation_do_and_retraction_reach_actual_claim_fields(self):
        source = self.store.put_source(
            "scene",
            self.owner,
            "causal",
            "The upstream switch drives X. Y lights only when X and the upstream switch differ.",
        )
        request = self.request(source_handles=(self.handle, source))
        candidate = self.candidate(request)
        segments = segment_snapshot(
            self.store.snapshot("scene", self.owner, request.source_handles),
            request.question,
        )
        refs = [s.segment_id for s in segments if s.source_id == "causal"]
        structural = dict(
            id="switch-model",
            source_event_id="switch-event",
            variables=["U", "X", "Y"],
            exogenous=["U"],
            rules=[
                dict(
                    target="X",
                    expression="U",
                    evidence_text="The upstream switch drives X.",
                ),
                dict(
                    target="Y",
                    expression="X ^ U",
                    evidence_text="Y lights only when X and the upstream switch differ.",
                ),
            ],
        )
        candidate["models"][0]["causal"] = [
            dict(
                id=name,
                model=structural,
                target="Y",
                observations=observed,
                interventions=intervention,
                segment_ids=refs,
            )
            for name, observed, intervention in [
                ("observe", {"X": 0}, {}),
                ("do", {}, {"X": 0}),
                ("abduct-do", {"X": 1}, {"X": 0}),
                ("withdraw", {}, {}),
            ]
        ]
        result, port = self.run_model(request, candidate)
        self.assertEqual(result.status, "COMPLETED", result.diagnostics)
        values = self.current_model(result)["causal"]
        self.assertEqual(
            [row["possible_values"] for row in values], [(0,), (0, 1), (1,), (0,)]
        )
        fields = [
            field
            for claim in result.claim_records
            for field in claim.used_result_fields
            if getattr(field, "path", ())[:2] == ("0", "causal")
        ]
        self.assertEqual(len(fields), 4)
        self.assertEqual(
            [field.value["possible_values"] for field in fields],
            [(0,), (0, 1), (1,), (0,)],
        )
        self.assertEqual(port.attempts, 1)
        # Source excerpts are checked, not accepted just because an ID exists.
        candidate["models"][0]["causal"][0]["model"]["rules"][0][
            "evidence_text"
        ] = "Invented source rule"
        invalid, _ = self.run_model(
            replace(
                request,
                request_id="invented-cause",
                budget=replace(self.budget, max_feedback=0),
            ),
            candidate,
        )
        self.assertEqual(invalid.status, "INVALID_REQUEST")

    def test_uncertain_belief_never_gets_implicit_uniform_weights(self):
        candidate = self.candidate()
        model = candidate["models"][0]
        model["variables"][0]["observed_by"] = ["b"]
        result, _ = self.run_model(candidate=candidate)
        self.assertEqual(result.status, "PARTIAL")
        calculated = self.current_model(result)
        self.assertEqual(calculated["plans"][0]["status"], "UNSPECIFIED_BELIEF_WEIGHTS")
        self.assertEqual(calculated["plans"][0]["q"], {})
        self.assertEqual(
            set(
                [
                    "open" if row["open"] else "closed"
                    for row in calculated["shared_variables"][0]["remaining_states"]
                ]
            ),
            {"open", "closed"},
        )
        model["plans"][0]["weights"] = {"open": "1/4", "closed": "3/4"}
        weighted, _ = self.run_model(
            replace(self.request(), request_id="weighted"), candidate
        )
        self.assertEqual(weighted.status, "COMPLETED", weighted.diagnostics)
        self.assertEqual(
            dict(self.current_model(weighted)["plans"][0]["q"]),
            {"direct": "1/2", "detour-start": "3"},
        )

    def test_private_message_preserves_unrelated_agent_and_old_time(self):
        source = self.store.put_source(
            "scene", self.owner, "late", "安稍后收到并采信通道关闭的消息。"
        )
        request = self.request(source_handles=(self.handle, source))
        candidate = self.candidate(request, message=True)
        q = dict(candidate["models"][0]["queries"][1], id="b-after-message", at=2)
        candidate["models"][0]["queries"].append(q)
        result, _ = self.run_model(request, candidate)
        beliefs = {
            row["query_id"]: row for row in self.current_model(result)["beliefs"]
        }
        self.assertEqual(beliefs["a-at-action"]["possible_values"], (True,))
        self.assertEqual(beliefs["a-after-message"]["possible_values"], (False,))
        self.assertEqual(
            beliefs["b-at-action"]["possible_values"],
            beliefs["b-after-message"]["possible_values"],
        )
        self.assertNotIn(
            "message-meaning-and-trust", beliefs["a-at-action"]["assumptions"]
        )
        self.assertIn(
            "message-meaning-and-trust", beliefs["a-after-message"]["assumptions"]
        )

    def test_batch_exhaustion_returns_no_fabricated_q_and_retains_usage(self):
        request = self.request(
            budget=replace(self.budget, max_local_evaluations=2, max_feedback=0)
        )
        result, port = self.run_model(request, self.candidate(request))
        self.assertEqual(result.status, "PARTIAL", result.diagnostics)
        self.assertLessEqual(result.usage["local_evaluations"], 2)
        self.assertEqual(port.attempts, 1)
        model = self.current_model(result)
        self.assertEqual(model["plans"][0]["q"], {})
        self.assertEqual(model["plans"][0]["status"], "FRONTIER_UNEXPLORED")
        self.assertIn("COGNITIVE_BATCH_BUDGET_FRONTIER", model["frontier"])

    def test_new_observation_revises_same_shared_variable_without_old_cache_reuse(self):
        request = self.request()
        before, _ = self.run_model(request)
        original = self.current_model(before)
        updated = self.store.put_source(
            "scene",
            self.owner,
            "story",
            "安和柏看见通道开放。柏关上通道时安一直在场。安准备去会场。",
        )
        stale = HCL(self.store, principal=self.owner).run_sync(request)
        self.assertEqual(stale.status, "STALE_STATE")
        current = replace(
            request, request_id="new-observation", source_handles=(updated,)
        )
        after, _ = self.run_model(current, self.candidate(current, seen=True))
        changed = self.current_model(after)
        self.assertEqual(
            original["shared_variables"][0]["variable_id"],
            changed["shared_variables"][0]["variable_id"],
        )
        self.assertNotEqual(original["plans"][0]["q"], changed["plans"][0]["q"])
        self.assertEqual(
            original["beliefs"][1]["possible_values"],
            changed["beliefs"][1]["possible_values"],
        )

    def test_two_plan_mappings_cannot_overwrite_one_shared_mental_variable(self):
        from copy import deepcopy

        candidate = self.candidate()
        second = deepcopy(candidate["models"][0]["plans"][0])
        second["id"] = "different-state-codebook"
        second["bindings"][0]["state"], second["bindings"][1]["state"] = (
            "closed",
            "open",
        )
        candidate["models"][0]["plans"].append(second)
        result, _ = self.run_model(candidate=candidate)
        self.assertEqual(result.status, "COMPLETED", result.diagnostics)
        model = self.current_model(result)
        self.assertEqual(len(model["shared_variables"]), 1)
        variable = model["shared_variables"][0]
        self.assertNotIn("planning_states", variable)
        self.assertEqual(
            [dict(row) for row in variable["remaining_states"]], [{"open": True}]
        )
        self.assertEqual(model["plans"][0]["planning_states"], ("open",))
        self.assertEqual(model["plans"][1]["planning_states"], ("closed",))
        self.assertEqual(
            model["plans"][0]["belief_variable_id"],
            model["plans"][1]["belief_variable_id"],
        )
        self.assertEqual(model["plans"][0]["q"]["direct"], "5")
        self.assertEqual(model["plans"][1]["q"]["direct"], "-1")
        fields = [
            f
            for c in result.claim_records
            for f in c.used_result_fields
            if getattr(f, "path", ())[:2] == ("0", "plans")
        ]
        self.assertEqual(
            [f.value["planning_states"] for f in fields], [("open",), ("closed",)]
        )
        # Completed graph replay and stream consume the same distinct bindings.
        client = HCL(self.store, principal=self.owner)

        async def stream():
            return [event async for event in client.stream(self.request())]

        self.assertEqual(
            asyncio.run(stream())[-1].result.claim_records, result.claim_records
        )
        self.store.close()
        self.store = StateStore.sqlite(self.path)
        self.assertEqual(
            HCL(self.store, principal=self.owner)
            .run_sync(self.request())
            .claim_records,
            result.claim_records,
        )

    def test_large_valid_accumulated_q_is_not_an_invalid_policy_input(self):
        candidate = self.candidate()
        plan = candidate["models"][0]["plans"][0]
        graph = plan["graph"]
        graph["utilities"] = {state: 0 for state in graph["states"]}
        for action in graph["actions"]:
            action["cost"] = 1000000
            action["transitions"] = {state: state for state in graph["states"]}
        plan["policy"] = dict(
            beta=1,
            rational_weight=1,
            habit_weight=0,
            error_weight=0,
            habit={"direct": "1/2", "detour-start": "1/2"},
        )
        result, _ = self.run_model(candidate=candidate)
        self.assertEqual(result.status, "COMPLETED", result.diagnostics)
        calculated = self.current_model(result)["plans"][0]
        self.assertEqual(
            dict(calculated["q"]), {"direct": "-2000000", "detour-start": "-2000000"}
        )
        self.assertEqual(
            dict(calculated["policy"]["probabilities"]),
            {"direct": 0.5, "detour-start": 0.5},
        )

    def test_answer_rejects_plan_binding_that_only_reuses_a_shared_variable_id(self):
        from hcl.kernel.types import HCLFailure, thaw
        from hcl.runtime.answer import AnswerAssembler

        result, _ = self.run_model()
        inference = next(
            row
            for row in self.store.inferences("scene", self.owner)
            if row.result_id in result.execution_receipt["result_ids"]
        )
        for edit in ("mapping", "states", "weights", "actor", "formula"):
            values = thaw(inference.values)
            plan = values["models"][0]["plans"][0]
            if edit == "mapping":
                plan["belief_world_bindings"] = {
                    key: "closed" for key in plan["belief_world_bindings"]
                }
            elif edit == "states":
                plan["planning_states"] = ["closed"]
            elif edit == "weights":
                plan["belief"] = {"closed": "1"}
            elif edit == "actor":
                plan["actor"] = "b"
            else:
                plan["state_bindings"][0]["when"] = False
            with self.assertRaises(HCLFailure) as caught:
                AnswerAssembler()._claim(replace(inference, values=values))
            self.assertEqual(
                caught.exception.diagnostic.code, "COGNITIVE_DEPENDENCY_MISSING"
            )
