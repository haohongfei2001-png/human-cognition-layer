"""Ordinary source input to shared actual cognition and longitudinal predictions."""

from copy import deepcopy
from dataclasses import replace
import json
import unittest
from hcl import HCL, ExecutionIssue
from hcl.kernel.types import Issue, thaw, HCLFailure
from hcl.models.gateway import OfflineModelPort, ModelGateway
from hcl.runtime.answer import AnswerAssembler
from tests import test_unified_s3_affect as affect_fixtures


class RelationshipExecutionTests(unittest.TestCase):
    def setUp(self):
        self.f = affect_fixtures.AffectExecutionTests()
        self.f.setUp()
        self.store, self.owner = self.f.store, self.f.owner
        handle = self.store.put_source(
            "scene",
            self.owner,
            "story",
            "柏在家与工作中多次面对通道：第一次关闭时等待，第二次开放时穿行，第三次关闭时等待，第四次开放时穿行。柏每次看见变化，未说自己价值改变。安全与职责具有相反后果，关注安全也可能暂时受评价调节。关于安的能力、善意与可靠性属于不同的有向判断，消息到达不自动证明接受道歉或恢复信任。下列优先级、条件似然、角色义务和行动图是分析候选，并非心理测量。",
        )
        self.f.fixture.scene.handle = handle
        self.request = replace(
            self.f.request,
            source_handles=(handle,),
            issue=ExecutionIssue(
                "root", goals=(Issue("longitudinal", "relationship.evaluate"),)
            ),
            question="这些跨情境选择是否需要价值改变？关系与角色对后续行动有什么条件影响？",
        )
        self.f.request = self.f.fixture.request = self.request

    def tearDown(self):
        self.f.tearDown()

    def candidate(self):
        base = self.f.candidate()["models"][0]
        mental = base["mental"]
        original = base["episodes"][0]
        template = mental["plans"][0]
        refs = original["segment_ids"]
        episodes = []
        plans = []
        events = []
        for at in range(1, 6):
            episode = deepcopy(original)
            episode.update(
                id="episode-" + str(at),
                episode_id="event-" + str(at),
                before=at - 1,
                at=at,
                plan_id="plan-" + str(at),
                previous_weights=None,
                current_weights=None,
                forecast_action=None,
            )
            episodes.append(episode)
            plan = deepcopy(template)
            plan.update(id=episode["plan_id"], at=at, weights=None)
            plans.append(plan)
            if at < 5:
                event = deepcopy(mental["events"][0])
                event.update(
                    id="change-" + str(at),
                    at=at,
                    effects={"open": at % 2 == 0},
                    seen_by=["b"],
                )
                events.append(event)
        mental.update(events=events, plans=plans)
        observations = [
            dict(
                id="choice-" + str(at),
                context_id="home" if at % 2 else "work",
                episode_id="episode-" + str(at),
                action="wait" if at % 2 else "cross",
                segment_ids=refs,
            )
            for at in range(1, 5)
        ]
        mechanisms = [
            dict(
                id="safety",
                label="constant safety priority with changing information",
                priorities={"safety": "1", "duty": "0"},
                coping_id=None,
                goal_multipliers={"safety": "1", "duty": "1"},
                respect_roles=False,
                relationship_effects=[],
                segment_ids=refs,
            ),
            dict(
                id="duty",
                label="constant duty priority",
                priorities={"safety": "0", "duty": "1"},
                coping_id=None,
                goal_multipliers={"safety": "1", "duty": "1"},
                respect_roles=False,
                relationship_effects=[],
                segment_ids=refs,
            ),
            dict(
                id="coping",
                label="appraisal-conditioned attention",
                priorities=None,
                coping_id="safety-focus",
                goal_multipliers={"safety": "1", "duty": "1"},
                respect_roles=False,
                relationship_effects=[],
                segment_ids=refs,
            ),
        ]
        return dict(
            schema="hcl-relationship-candidates-1",
            models=[
                dict(
                    mental=mental,
                    interaction=dict(
                        utterances=[],
                        acts=[],
                        commitments=[],
                        games=[],
                        through=5,
                        max_ack_depth=2,
                    ),
                    affect=dict(episodes=episodes, channels=base["channels"]),
                    relationships=[],
                    roles=[],
                    identities=[
                        dict(
                            id="self",
                            at=1,
                            actor="b",
                            speaker="b",
                            kind="SELF_IDENTIFICATION",
                            content="I consider duty important.",
                            segment_ids=refs,
                        ),
                        dict(
                            id="attributed",
                            at=2,
                            actor="b",
                            speaker="a",
                            kind="OTHER_ATTRIBUTION",
                            content="A calls B cautious.",
                            segment_ids=refs,
                        ),
                    ],
                    observations=observations,
                    forecasts=[
                        dict(
                            id="next",
                            context_id="next-work",
                            episode_id="episode-5",
                            segment_ids=refs,
                        )
                    ],
                    mechanisms=mechanisms,
                    search=dict(max_segments=3, max_candidates=256),
                )
            ],
        )

    def run_candidate(self, candidate=None, request=None):
        port = OfflineModelPort(
            json.dumps(candidate or self.candidate(), ensure_ascii=False)
        )
        result = HCL(
            self.store, principal=self.owner, gateway=ModelGateway(self.store, port)
        ).run_sync(request or self.request)
        return result, port

    def actual(self, result):
        return next(
            r
            for r in self.store.inferences("scene", self.owner)
            if r.result_id in result.execution_receipt["result_ids"]
        )

    def test_actual_shared_domains_and_multi_context_predictions_keep_stable_alternative(
        self,
    ):
        result, port = self.run_candidate()
        self.assertEqual(result.status, "COMPLETED", result.diagnostics)
        self.assertEqual(port.attempts, 1)
        actual = self.actual(result)
        model = actual.values["models"][0]
        self.assertEqual(
            model["actual_interaction"]["values"]["models"][0]["actual_mental"],
            model["actual_affect"]["values"]["models"][0]["actual_mental"],
        )
        self.assertEqual(
            model["cognition"]["actual"],
            model["actual_affect"]["values"]["models"][0]["actual_mental"],
        )
        safety = next(
            m["mechanism_id"]
            for m in model["mechanisms"]
            if m["input"]["id"] == "safety"
        )
        self.assertEqual(
            [r["values"] for r in model["prediction_matrix"][safety]],
            [("wait",), ("cross",), ("wait",), ("cross",)],
        )
        stable = next(
            t
            for t in model["longitudinal"]["trajectories"]
            if t["path"] == (safety,) * 4
        )
        self.assertEqual(stable["change_points"], ())
        self.assertEqual(len(stable["profile"]["explained"]), 4)
        self.assertIn(stable["trajectory_id"], model["longitudinal"]["pareto_explored"])
        self.assertEqual(model["forecasts"][safety][0]["values"], ("cross",))
        self.assertTrue(model["forecasts"][safety][0]["hypothetical"])
        self.assertIn("SELF_IDENTIFICATION", result.answer)
        self.assertIn("OTHER_ATTRIBUTION", result.answer)
        self.assertIn("Zero-change alternatives", result.answer)
        for mutation in ("q", "view", "change_points", "identity"):
            bad = thaw(actual.values)
            row = bad["models"][0]
            if mutation == "q":
                row["prediction_matrix"][safety][0]["branches"][0]["computation"]["q"][
                    "wait"
                ] = "999"
            elif mutation == "view":
                row["cognition"]["actual"]["values"]["models"][0]["events"] = []
            elif mutation == "change_points":
                row["longitudinal"]["trajectories"][0]["change_points"] = [99]
            else:
                row["identity_narratives"][0]["kind"] = "PRIVATE_IDENTITY_TRUTH"
            with self.subTest(mutation=mutation), self.assertRaises(HCLFailure):
                AnswerAssembler()._claim(replace(actual, values=bad))

    def relational_candidate(self):
        candidate = self.candidate()
        model = candidate["models"][0]
        mental = model["mental"]
        refs = model["observations"][0]["segment_ids"]
        offer = dict(
            id="offer-event",
            at=0,
            kind="message",
            effects={"open": True},
            seen_by=[],
            received_by=["b"],
            understood_by=["b"],
            trusted_by=["b"],
            assumptions=[],
            segment_ids=refs,
        )
        mental["events"].insert(0, offer)
        model["interaction"]["utterances"] = [
            dict(
                id="offer",
                at=0,
                speaker="a",
                audience=["b"],
                version="v1",
                literal={"open": True},
                deliveries=[
                    dict(
                        event_id="offer-event",
                        readings=[
                            dict(
                                actor="b",
                                contents=[{"open": True}],
                                versions=["v1"],
                                segment_ids=refs,
                            )
                        ],
                        segment_ids=refs,
                    )
                ],
                segment_ids=refs,
            )
        ]
        model["interaction"]["commitments"] = [
            dict(
                id="terms",
                offer_id="offer",
                speaker="a",
                recipient="b",
                version="v1",
                condition={"op": "not", "arg": {"op": "atom", "name": "open"}},
                outcome={"op": "atom", "name": "open"},
                deadline=1,
                requires_acceptance=False,
                acceptance="QUALIFIED_ACT",
                activation="LATCHED",
                withdrawal="NO_RELEASE",
                segment_ids=refs,
            )
        ]

        def relation(identity, observer, target, dimension):
            return dict(
                id=identity,
                observer=observer,
                target=target,
                domain="route-support",
                dimension=dimension,
                hypotheses=[
                    dict(
                        id="supportive",
                        label="supportive conditional model",
                        segment_ids=refs,
                    ),
                    dict(
                        id="limited",
                        label="limited conditional model",
                        segment_ids=refs,
                    ),
                ],
                prior={"supportive": "1/2", "limited": "1/2"},
                factorization="CONDITIONAL_INDEPENDENCE_MODEL",
                updates=[],
                segment_ids=refs,
            )

        reliability = relation("reliability", "b", "a", "RELIABILITY")
        reliability["updates"] = [
            dict(
                id="breach",
                at=1,
                event_id="change-1",
                condition={"op": "not", "arg": {"op": "atom", "name": "open"}},
                commitment_id="terms",
                commitment_status="BREACHED",
                likelihoods={"supportive": "1/4", "limited": "3/4"},
                segment_ids=refs,
            ),
            dict(
                id="repair",
                at=2,
                event_id="change-2",
                condition={"op": "atom", "name": "open"},
                commitment_id="terms",
                commitment_status="BREACHED_THEN_FULFILLED",
                likelihoods={"supportive": "3/4", "limited": "1/4"},
                segment_ids=refs,
            ),
        ]
        model["relationships"] = [
            reliability,
            relation("ability", "b", "a", "ABILITY"),
            relation("goodwill", "b", "a", "GOODWILL"),
            relation("reverse", "a", "b", "RELIABILITY"),
        ]
        responsive = deepcopy(model["mechanisms"][0])
        responsive.update(
            id="responsive",
            label="relationship-responsive conditional priorities",
            priorities={"safety": "1/2", "duty": "1/2"},
            relationship_effects=[
                dict(
                    relationship_id="reliability",
                    multipliers={
                        "supportive": {"safety": "1", "duty": "3"},
                        "limited": {"safety": "3", "duty": "1"},
                    },
                    segment_ids=refs,
                )
            ],
        )
        model["mechanisms"].append(responsive)
        return candidate

    def test_real_commitment_breach_repair_changes_only_directed_relationship_dimension(
        self,
    ):
        result, _ = self.run_candidate(self.relational_candidate())
        self.assertEqual(result.status, "COMPLETED", result.diagnostics)
        model = self.actual(result).values["models"][0]
        relations = {r["relationship_id"]: r for r in model["relationships"]}
        history = relations["reliability"]["history"]
        self.assertEqual(history[0]["commitment"]["status"], "BREACHED")
        self.assertEqual(history[0]["weights"], {"supportive": "1/4", "limited": "3/4"})
        self.assertEqual(history[1]["commitment"]["status"], "BREACHED_THEN_FULFILLED")
        self.assertEqual(history[1]["weights"], {"supportive": "1/2", "limited": "1/2"})
        for key in ("ability", "goodwill", "reverse"):
            self.assertEqual(
                relations[key]["weights"], {"supportive": "1/2", "limited": "1/2"}
            )
            self.assertFalse(relations[key]["history"])
        responsive = next(
            m["mechanism_id"]
            for m in model["mechanisms"]
            if m["input"]["id"] == "responsive"
        )
        self.assertEqual(
            model["prediction_matrix"][responsive][0]["branches"][0]["priorities"],
            {"safety": "5/8", "duty": "3/8"},
        )
        self.assertEqual(
            model["prediction_matrix"][responsive][1]["branches"][0]["priorities"],
            {"safety": "1/2", "duty": "1/2"},
        )
        self.assertIn(
            ":conditional-independence",
            str(self.actual(result).assumption_environments),
        )
        # Another person's knowledge is not this observer's received evidence.
        candidate = self.relational_candidate()
        candidate["models"][0]["mental"]["events"][1]["seen_by"] = ["a"]
        # B's actual perspective remains open at t1; declared weights are absent.
        changed, _ = self.run_candidate(
            candidate, replace(self.request, request_id="not-seen")
        )
        self.assertIn(changed.status, ("COMPLETED", "PARTIAL"), changed.diagnostics)
        row = self.actual(changed).values["models"][0]["relationships"][0]["history"][0]
        self.assertFalse(row["event_received"])
        self.assertEqual(row["qualification"], "INAPPLICABLE")
        self.assertEqual(row["weights"], {"supportive": "1/2", "limited": "1/2"})

    def test_roles_conflict_and_reconciliation_are_not_identity_reports(self):
        for reconciled in (False, True):
            candidate = self.candidate()
            model = candidate["models"][0]
            refs = model["observations"][0]["segment_ids"]
            model["roles"] = [
                dict(
                    id="friend",
                    actor="b",
                    from_time=3,
                    through_time=3,
                    condition=True,
                    episode_actions={
                        "episode-3": ["cross", "wait"] if reconciled else ["cross"]
                    },
                    segment_ids=refs,
                ),
                dict(
                    id="worker",
                    actor="b",
                    from_time=3,
                    through_time=3,
                    condition=True,
                    episode_actions={"episode-3": ["wait"]},
                    segment_ids=refs,
                ),
            ]
            sensitive = deepcopy(model["mechanisms"][0])
            sensitive.update(id="role-sensitive", respect_roles=True)
            model["mechanisms"].append(sensitive)
            result, _ = self.run_candidate(
                candidate, replace(self.request, request_id="roles-" + str(reconciled))
            )
            self.assertEqual(result.status, "COMPLETED", result.diagnostics)
            actual = self.actual(result).values["models"][0]
            role = next(r for r in actual["roles"] if r["at"] == 3)
            self.assertEqual(
                role["branches"][0]["feasible_reconciliation_actions"],
                ("wait",) if reconciled else (),
            )
            self.assertEqual(
                role["branches"][0]["minimal_incompatible_role_sets"],
                () if reconciled else (("friend", "worker"),),
            )
            sensitive = next(
                m["mechanism_id"]
                for m in actual["mechanisms"]
                if "role-sensitive" in m["source_aliases"]
            )
            self.assertEqual(
                actual["prediction_matrix"][sensitive][2]["values"],
                ("wait",) if reconciled else (None,),
            )
            self.assertEqual(len(actual["identity_narratives"]), 2)

    def test_null_relationship_prior_retains_predictions_without_uniform_probabilities(
        self,
    ):
        candidate = self.relational_candidate()
        candidate["models"][0]["relationships"][0]["prior"] = None
        result, _ = self.run_candidate(candidate)
        self.assertEqual(result.status, "COMPLETED", result.diagnostics)
        model = self.actual(result).values["models"][0]
        self.assertIsNone(model["relationships"][0]["weights"])
        responsive = next(
            m["mechanism_id"]
            for m in model["mechanisms"]
            if m["input"]["id"] == "responsive"
        )
        first = model["prediction_matrix"][responsive][0]
        self.assertEqual(first["values"], ("cross", "wait"))
        self.assertEqual(len(first["branches"]), 2)
        self.assertIsNone(first["relation_conditions"][0]["state"]["weights"])

    def test_budget_frontiers_never_become_invalid_models_or_fabricated_conflicts(self):
        for limit in (1, 2, 5, 12, 24, 48, 96, 192, 384, 768):
            with self.subTest(limit=limit):
                request = replace(
                    self.request,
                    request_id="budget-" + str(limit),
                    budget=replace(self.request.budget, max_local_evaluations=limit),
                )
                result, _ = self.run_candidate(self.relational_candidate(), request)
                self.assertIn(
                    result.status, ("COMPLETED", "PARTIAL"), result.diagnostics
                )
                self.assertLessEqual(result.usage["local_evaluations"], limit)
                if result.status == "PARTIAL":
                    self.assertTrue(
                        "FRONTIER" in result.answer or "UNRESOLVED" in result.answer
                    )

    def test_counterevidence_adds_competing_turn_and_changes_qualified_future_predictions(
        self,
    ):
        before, _ = self.run_candidate()
        first = self.actual(before).values["models"][0]
        self.assertEqual(
            {
                tuple(p["values"])
                for t in first["preferred_forecasts"]
                for p in t["predictions"]
            },
            {("cross",)},
        )
        candidate = self.candidate()
        candidate["models"][0]["observations"][-1]["action"] = "wait"
        after, _ = self.run_candidate(
            candidate, replace(self.request, request_id="counterevidence")
        )
        self.assertEqual(after.status, "COMPLETED", after.diagnostics)
        second = self.actual(after).values["models"][0]
        self.assertEqual(first["cognition"], second["cognition"])
        self.assertTrue(any(t["change_points"] for t in second["preferred_forecasts"]))
        self.assertIn(
            ("wait",),
            {
                tuple(p["values"])
                for t in second["preferred_forecasts"]
                for p in t["predictions"]
            },
        )
        self.assertEqual(first["prediction_matrix"], second["prediction_matrix"])
        self.assertNotEqual(
            first["longitudinal"]["pareto_explored"],
            second["longitudinal"]["pareto_explored"],
        )

    def test_exact_aliases_do_not_add_mechanisms_evidence_or_simultaneous_turns(self):
        candidate = self.candidate()
        model = candidate["models"][0]
        alias = deepcopy(model["mechanisms"][0])
        alias.update(id="renamed", label="another display label")
        model["mechanisms"].append(alias)
        duplicate = deepcopy(model["observations"][-1])
        duplicate.update(id="duplicate-report", context_id="renamed-context")
        model["observations"].append(duplicate)
        result, _ = self.run_candidate(candidate)
        self.assertEqual(result.status, "COMPLETED", result.diagnostics)
        actual = self.actual(result).values["models"][0]
        self.assertEqual(len(actual["mechanisms"]), 3)
        self.assertEqual(len(actual["longitudinal"]["evidence_factor_ids"]), 4)
        self.assertTrue(
            all(
                t["path"][-1] == t["path"][-2]
                for t in actual["longitudinal"]["trajectories"]
            )
        )
        self.assertTrue(
            any(
                set(m["source_aliases"]) == {"safety", "renamed"}
                for m in actual["mechanisms"]
            )
        )

    def test_coping_action_attention_and_horizon_are_consumed_not_only_priorities(self):
        candidate = self.candidate()
        model = candidate["models"][0]
        for episode in model["affect"]["episodes"]:
            coping = next(c for c in episode["coping"] if c["id"] == "safety-focus")
            coping.update(action_ids=["wait"], horizon=2)
        result, _ = self.run_candidate(candidate)
        self.assertEqual(result.status, "COMPLETED", result.diagnostics)
        actual = self.actual(result).values["models"][0]
        key = next(
            m["mechanism_id"]
            for m in actual["mechanisms"]
            if m["input"]["id"] == "coping"
        )
        for row in actual["prediction_matrix"][key]:
            self.assertEqual(row["values"], ("wait",))
            for branch in row["branches"]:
                self.assertEqual(branch["actions"], ("wait",))
                self.assertEqual(branch["computation"]["horizon"], 2)
                self.assertEqual(branch["coping_basis"]["coping_id"], "safety-focus")

    def test_source_only_parameters_actor_isolation_and_no_answer_injection(self):
        from hcl.semantics.segments import question_segments

        for mutation in (
            "question",
            "values",
            "actor",
            "forecast_past",
            "factorization",
        ):
            candidate = self.relational_candidate()
            model = candidate["models"][0]
            if mutation == "question":
                model["relationships"][0]["segment_ids"] = [
                    question_segments(self.request.question)[0].segment_id
                ]
            elif mutation == "values":
                model["mechanisms"][0]["q"] = {"wait": "999"}
            elif mutation == "actor":
                model["affect"]["episodes"][1]["actor"] = "a"
            elif mutation == "forecast_past":
                model["forecasts"][0]["episode_id"] = "episode-4"
            else:
                model["relationships"][0]["factorization"] = "VERIFIED_HUMAN_TRUST_LAW"
            result, _ = self.run_candidate(
                candidate, replace(self.request, request_id=mutation)
            )
            self.assertEqual(result.status, "INVALID_REQUEST", result.diagnostics)
            self.assertFalse(result.claim_records or result.answer)

    def test_stream_crash_recovery_and_late_acl_replay_do_not_resend(self):
        import asyncio
        from unittest.mock import patch
        from hcl.memory.store import StateStore
        from hcl.runtime.recovery import RecoveryManager
        from hcl.operators.local_model import LocalModelOperator

        class Crash(BaseException):
            pass

        for seam in (
            "return_persisted",
            "execution_computed",
            "execution_effects_committed",
        ):
            request = replace(
                self.request,
                request_id=seam,
                issue=ExecutionIssue(
                    "root", goals=(Issue(seam, "relationship.evaluate"),)
                ),
            )
            port = OfflineModelPort(json.dumps(self.relational_candidate()))
            client = HCL(
                self.store, principal=self.owner, gateway=ModelGateway(self.store, port)
            )
            hit = []

            def fail(stage):
                if stage == seam and not hit:
                    hit.append(True)
                    raise Crash()

            with patch.object(self.store, "_checkpoint", fail), self.assertRaises(
                Crash
            ):
                client.run_sync(request)
            self.assertEqual(port.attempts, 1)
            owner_id = self.store.owner_id
            path = self.store.path
            self.store.close()
            self.store = StateStore.sqlite(path, revision=True)
            self.f.store = self.f.fixture.store = self.f.fixture.scene.store = (
                self.store
            )
            RecoveryManager(self.store).resume_execution(
                request, expected_owner_id=owner_id
            )
            port = OfflineModelPort("NO_NEW_SEND")
            client = HCL(
                self.store, principal=self.owner, gateway=ModelGateway(self.store, port)
            )

            async def collect():
                return [event async for event in client.stream(request)]

            if seam != "return_persisted":
                with patch.object(
                    LocalModelOperator,
                    "run",
                    side_effect=AssertionError("do not recompute durable operation"),
                ):
                    result = asyncio.run(collect())[-1].result
            else:
                result = asyncio.run(collect())[-1].result
            self.assertEqual(result.status, "COMPLETED", result.diagnostics)
            replay = client.run_sync(request)
            self.assertEqual(
                (result.answer, result.claim_records),
                (replay.answer, replay.claim_records),
            )
            self.assertEqual(port.attempts, 0)
            self.assertEqual(replay.usage["mock_calls"], 1)
        self.store.set_readers("scene", self.owner, "story", {"bob"})
        denied = client.run_sync(request)
        self.assertEqual(denied.status, "DENIED")
        self.assertFalse(denied.answer or denied.claim_records)
        self.assertEqual(denied.usage["mock_calls"], 1)

    def test_contradicted_relationship_does_not_erase_unrelated_explanations(self):
        candidate = self.relational_candidate()
        model = candidate["models"][0]
        model["relationships"][0]["updates"][0]["likelihoods"] = {
            "supportive": "0",
            "limited": "0",
        }
        request = replace(
            self.request, budget=replace(self.request.budget, max_output_bytes=4194304)
        )
        result, _ = self.run_candidate(candidate, request)
        self.assertEqual(result.status, "PARTIAL", result.diagnostics)
        actual = self.actual(result).values["models"][0]
        relation = actual["relationships"][0]
        self.assertFalse(relation["compatible_hypotheses"])
        self.assertIsNone(relation["weights"])
        self.assertIn("RELATIONSHIP_MODEL_CONTRADICTED", result.answer)
        for mechanism in actual["mechanisms"]:
            row = actual["prediction_matrix"][mechanism["mechanism_id"]][0]
            if mechanism["input"]["id"] == "responsive":
                self.assertEqual(row["status"], "UNCOMPUTED")
                self.assertFalse(row["values"])
            else:
                self.assertEqual(row["status"], "COMPUTED")
        self.assertTrue(actual["longitudinal"]["trajectories"])

    def test_world_frontier_keeps_relationship_and_role_dependencies_unknown(self):
        candidate = self.relational_candidate()
        mental = candidate["models"][0]["mental"]
        for i in range(7):
            variable = deepcopy(mental["variables"][0])
            variable.update(id="additional-" + str(i), initial=False)
            mental["variables"].append(variable)
        request = replace(
            self.request,
            budget=replace(
                self.request.budget,
                max_output_bytes=4194304,
                max_visible_output_tokens=1048576,
            ),
        )
        result, port = self.run_candidate(candidate, request)
        self.assertEqual(result.status, "PARTIAL", result.diagnostics)
        self.assertIn("WORLD_FRONTIER", result.answer)
        actual = self.actual(result).values["models"][0]
        for row in actual["relationships"][0]["history"]:
            self.assertEqual(row["qualification"], "UNRESOLVED")
            self.assertEqual(row["weights"], {"supportive": "1/2", "limited": "1/2"})
            self.assertEqual(row["condition"]["possible_values"], (False, True))
        for row in actual["roles"]:
            self.assertEqual(row["status"], "UNCOMPUTED")
            self.assertFalse(row["branches"])
        replay = HCL(
            self.store, principal=self.owner, gateway=ModelGateway(self.store, port)
        ).run_sync(request)
        self.assertEqual(replay.status, "PARTIAL")
        self.assertEqual(replay.answer, result.answer)
        self.assertEqual(port.attempts, 1)

    def test_cached_delivery_late_revocation_has_safe_receipt_and_preserves_usage(self):
        import asyncio
        from unittest.mock import patch
        from hcl.memory.store import StateStore
        from hcl.kernel.types import TaskResult

        peer = StateStore.sqlite(self.store.path, revision=True)
        original = self.store._get_object
        try:
            for stream in (False, True):
                self.store.set_readers(
                    "scene", self.owner, "story", {self.owner.subject_id}
                )
                request = replace(
                    self.request,
                    request_id="late-replay-" + str(stream),
                    issue=ExecutionIssue(
                        "root",
                        goals=(Issue("late-" + str(stream), "relationship.evaluate"),),
                    ),
                )
                result, _ = self.run_candidate(self.relational_candidate(), request)
                self.assertEqual(result.status, "COMPLETED", result.diagnostics)
                hit = []

                def read_then_revoke(digest):
                    value = original(digest)
                    if (
                        type(value) is TaskResult
                        and value.status == "COMPLETED"
                        and not hit
                    ):
                        peer.set_readers("scene", self.owner, "story", {"bob"})
                        hit.append(True)
                    return value

                client = HCL(self.store, principal=self.owner)

                async def collect():
                    return [e async for e in client.stream(request)]

                with patch.object(self.store, "_get_object", read_then_revoke):
                    denied = (
                        asyncio.run(collect())[-1].result
                        if stream
                        else client.run_sync(request)
                    )
                self.assertTrue(hit)
                self.assertEqual(denied.status, "DENIED")
                self.assertFalse(denied.answer or denied.claim_records)
                self.assertNotIn("story", str(denied.execution_receipt))
                for key, value in result.usage.items():
                    self.assertEqual(denied.usage.get(key), value, key)
        finally:
            peer.close()


if __name__ == "__main__":
    unittest.main()
