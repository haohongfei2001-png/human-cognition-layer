"""Source-bound conditional hypotheses enter real belief, appraisal and action paths."""

from copy import deepcopy
from dataclasses import replace
import json
import unittest
from hcl import HCL, ExecutionIssue
from hcl.kernel.types import Issue, HCLFailure, thaw
from hcl.models.gateway import ModelGateway, OfflineModelPort
from hcl.runtime.answer import AnswerAssembler
from tests import test_unified_s3_interaction as interaction_fixtures


class AffectExecutionTests(unittest.TestCase):
    def setUp(self):
        self.fixture = interaction_fixtures.InteractionExecutionTests()
        self.fixture.setUp()
        self.store, self.owner = self.fixture.store, self.fixture.owner
        source = self.store.put_source(
            "scene",
            self.owner,
            "story",
            "安和柏最初都知道通道开放。时间1，柏看见通道关闭，安不在场。柏原来预想顺利穿过。"
            "柏想保障安全，也想履行一次冒险职责；对这两个目标，关闭的后果相反。"
            "在所提模型中，穿行在开放时成功、关闭时受伤，等待结束本轮。"
            "安全目标给开放3、关闭-3、成功5、受伤-5、等待-1；职责目标取相反值。"
            "两目标起初各占一半；若安全受损，关注安全模型把其相对权重乘3，职责不变。"
            "另一应对模型只考虑穿行，关注职责。二者都只是候选，尚未采取。"
            "柏说自己悲伤，旁观者同时看见柏微笑。这些报告和表现不能直接确定内心。",
        )
        self.fixture.scene.handle = source
        self.request = replace(
            self.fixture.request,
            source_handles=(source,),
            question="这次变化如何影响柏的两个目标？可能怎样应对，后续会怎样？",
            issue=ExecutionIssue("root", goals=(Issue("affect", "affect.evaluate"),)),
        )
        self.fixture.request = self.request

    def tearDown(self):
        self.fixture.tearDown()

    def candidate(self):
        mental = self.fixture.candidate()["models"][0]["mental"]
        refs = mental["variables"][0]["segment_ids"]
        mental["variables"][0].update(initial=True, observed_by=["a", "b"])
        mental["queries"] = [
            dict(
                id="before",
                at=0,
                formula=dict(
                    op="believes", agent="b", arg=dict(op="atom", name="open")
                ),
                segment_ids=refs,
            ),
            dict(
                id="after",
                at=1,
                formula=dict(
                    op="believes", agent="b", arg=dict(op="atom", name="open")
                ),
                segment_ids=refs,
            ),
        ]
        mental["events"] = [
            dict(
                id="closure",
                at=1,
                kind="change",
                effects={"open": False},
                seen_by=["b"],
                received_by=[],
                understood_by=[],
                trusted_by=[],
                assumptions=[],
                segment_ids=refs,
            )
        ]
        plan = mental["plans"][0]
        plan["weights"] = {"b": "1"}
        safety = {"r": "3", "b": "-3", "success": "5", "harm": "-5", "waited": "-1"}
        goals = [
            dict(id="safety", label="保障安全", utilities=safety, segment_ids=refs),
            dict(
                id="duty",
                label="履行风险职责",
                utilities={s: str(-int(v)) for s, v in safety.items()},
                segment_ids=refs,
            ),
        ]
        condition = dict(
            goal_id="safety", dimension="change_direction", value="NEGATIVE"
        )
        mappings = [
            dict(
                id="loss",
                label="loss-related-distress",
                conditions=[condition],
                requires_previous=[],
                segment_ids=refs,
            ),
            dict(
                id="mixed-gain",
                label="duty-related-satisfaction",
                conditions=[
                    dict(goal_id="duty", dimension="change_direction", value="POSITIVE")
                ],
                requires_previous=[],
                segment_ids=refs,
            ),
        ]
        coping = [
            dict(
                id="safety-focus",
                kind="PROBLEM_FOCUSED",
                priorities={"safety": "1/2", "duty": "1/2"},
                horizon=1,
                action_ids=["cross", "wait"],
                observation_overrides={},
                segment_ids=refs,
                adjustments=[
                    dict(
                        id="threat-attention",
                        conditions=[condition],
                        multipliers={"safety": "3", "duty": "1"},
                        segment_ids=refs,
                    )
                ],
            ),
            dict(
                id="duty-focus",
                kind="AVOIDANCE",
                priorities={"safety": "1/4", "duty": "3/4"},
                horizon=1,
                action_ids=["cross"],
                observation_overrides={},
                adjustments=[],
                segment_ids=refs,
            ),
        ]
        episode = dict(
            id="closure-v1",
            episode_id="closure",
            actor="b",
            before=0,
            at=1,
            plan_id=plan["id"],
            previous_weights={"r": "1"},
            current_weights={"b": "1"},
            forecast_action="cross",
            goals=goals,
            mappings=mappings,
            coping=coping,
            previous_id=None,
            revision_kind="INITIAL",
            segment_ids=refs,
        )
        channels = [
            dict(
                id="sad",
                at=1,
                actor="b",
                speaker="b",
                kind="SELF_REPORT",
                content="悲伤",
                segment_ids=refs,
            ),
            dict(
                id="smile",
                at=1,
                actor="b",
                speaker="旁观者",
                kind="EXPRESSION",
                content="微笑",
                segment_ids=refs,
            ),
        ]
        return dict(
            schema="hcl-affect-candidates-1",
            models=[dict(mental=mental, episodes=[episode], channels=channels)],
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

    def test_real_entry_mixed_goals_appraisal_feedback_and_hypothetical_outcomes(self):
        result, port = self.run_candidate()
        self.assertEqual(result.status, "COMPLETED", result.diagnostics)
        self.assertEqual(port.attempts, 1)
        row = self.actual(result).values["models"][0]["episodes"][0]
        profiles = row["derived"]["profiles"]
        self.assertEqual(profiles[0]["appraisal"]["state_change"]["lower"], "-6")
        self.assertEqual(profiles[0]["appraisal"]["expectation_gap"]["lower"], "-8")
        self.assertEqual(profiles[1]["appraisal"]["state_change"]["lower"], "6")
        coping = row["derived"]["coping"]
        self.assertEqual(
            coping[0]["branches"][0]["input"]["priorities"],
            {"safety": "3/4", "duty": "1/4"},
        )
        self.assertEqual(
            coping[0]["branches"][0]["computation"]["best_actions"], ("wait",)
        )
        self.assertEqual(
            coping[1]["branches"][0]["computation"]["best_actions"], ("cross",)
        )
        self.assertTrue(
            all(
                o["hypothetical"]
                for c in coping
                for b in c["branches"]
                for o in b["consequences"]
            )
        )
        self.assertIn("SELF_REPORT", result.answer)
        self.assertIn("EXPRESSION", result.answer)
        self.assertIn("actual M05 Q", result.answer)
        self.assertEqual(
            [
                e["event_id"]
                for e in self.actual(result).values["models"][0]["actual_mental"][
                    "values"
                ]["models"][0]["events"]
            ],
            ["closure"],
        )

    def revised_candidate(
        self, received=True, trusted=True, understood=True, analyst=False
    ):
        candidate = self.candidate()
        model = candidate["models"][0]
        mental = model["mental"]
        original = model["episodes"][0]
        refs = original["segment_ids"]
        constant = dict(
            id="constant",
            label="unaffected concern",
            utilities={s: "1" for s in original["goals"][0]["utilities"]},
            segment_ids=refs,
        )
        original["goals"].append(constant)
        for coping in original["coping"]:
            coping["priorities"]["constant"] = "0"
            for rule in coping["adjustments"]:
                rule["multipliers"]["constant"] = "1"
        target = "b" if received else "a"
        mental["events"].append(
            dict(
                id="new-information",
                at=2,
                kind="message",
                effects={"open": True},
                seen_by=[],
                received_by=[target],
                understood_by=[target] if understood else [],
                trusted_by=[target] if trusted and understood else [],
                assumptions=["new-message-hypothesis"],
                segment_ids=refs,
            )
        )
        mental["active_assumptions"].append("new-message-hypothesis")
        updated = deepcopy(original)
        updated.update(
            id="closure-v2",
            at=2,
            plan_id="new-plan",
            previous_id=original["id"],
            revision_kind="ANALYST_REINTERPRETATION" if analyst else "NEW_INFORMATION",
            current_weights=(
                {"r": "1"} if received and trusted and understood else {"b": "1"}
            ),
        )
        plan = deepcopy(mental["plans"][0])
        plan.update(id="new-plan", at=2, weights=updated["current_weights"])
        mental["plans"].append(plan)
        model["episodes"].append(updated)
        return candidate

    def test_received_understood_trusted_update_changes_only_related_appraisals(self):
        for received, trusted, understood in (
            (True, True, True),
            (False, True, True),
            (True, False, True),
            (True, True, False),
        ):
            with self.subTest(
                received=received, trusted=trusted, understood=understood
            ):
                candidate = self.revised_candidate(received, trusted, understood)
                result, _ = self.run_candidate(
                    candidate,
                    replace(
                        self.request, request_id=str((received, trusted, understood))
                    ),
                )
                self.assertEqual(result.status, "COMPLETED", result.diagnostics)
                first, second = self.actual(result).values["models"][0]["episodes"]
                should_change = received and trusted and understood
                self.assertEqual(
                    second["derived"]["profiles"][0]["appraisal"]["current_value"][
                        "lower"
                    ],
                    "3" if should_change else "-3",
                )
                changes = {
                    r["goal_id"]: r["change"]
                    for r in second["derived"]["reappraisal"]["changes"]
                }
                self.assertEqual(
                    changes["safety"], "REVISED" if should_change else "UNCHANGED"
                )
                self.assertEqual(changes["constant"], "UNCHANGED")
                self.assertNotIn(
                    "new-message-hypothesis", first["assumption_environments"]
                )
                self.assertIn(
                    "new-message-hypothesis", second["assumption_environments"]
                )
                self.assertEqual(
                    first["derived"]["profiles"][0]["appraisal"]["current_value"][
                        "lower"
                    ],
                    "-3",
                )
                self.assertEqual(second["views"]["actual"]["mapping"]["states"], ("b",))
                self.assertEqual(
                    second["views"]["current"]["mapping"]["states"],
                    ("r",) if should_change else ("b",),
                )

    def test_analyst_alternative_does_not_claim_character_reappraisal(self):
        result, _ = self.run_candidate(self.revised_candidate(analyst=True))
        self.assertEqual(result.status, "COMPLETED", result.diagnostics)
        self.assertIn("NOT_ESTABLISHED_ANALYST_ALTERNATIVE", result.answer)

    def test_changed_goals_are_recomputed_and_source_channels_do_not_assign_emotion(
        self,
    ):
        candidate = self.revised_candidate(received=False)
        episode = candidate["models"][0]["episodes"][1]
        episode["revision_kind"] = "GOAL_REVISION"
        episode["goals"][0]["utilities"] = {
            k: str(-int(v)) for k, v in episode["goals"][0]["utilities"].items()
        }
        result, _ = self.run_candidate(candidate)
        self.assertEqual(result.status, "COMPLETED", result.diagnostics)
        actual = self.actual(result)
        first, second = actual.values["models"][0]["episodes"]
        self.assertEqual(
            first["derived"]["profiles"][0]["appraisal"]["current_value"]["lower"], "-3"
        )
        self.assertEqual(
            second["derived"]["profiles"][0]["appraisal"]["current_value"]["lower"], "3"
        )
        self.assertEqual(second["derived"]["reappraisal"]["kind"], "GOAL_REVISION")
        candidate = self.candidate()
        candidate["models"][0]["channels"][0]["content"] = "高兴"
        changed, _ = self.run_candidate(
            candidate, replace(self.request, request_id="report-only")
        )
        baseline, _ = self.run_candidate(
            self.candidate(), replace(self.request, request_id="report-baseline")
        )
        a = self.actual(changed).values["models"][0]["episodes"][0]["derived"]
        b = self.actual(baseline).values["models"][0]["episodes"][0]["derived"]
        for key in ("profiles", "hypotheses", "coping"):
            self.assertEqual(a[key], b[key])
        self.assertNotEqual(a["channels"], b["channels"])

    def test_unknown_distribution_stays_interval_and_no_coping_probability_is_invented(
        self,
    ):
        candidate = self.candidate()
        model = candidate["models"][0]
        mental = model["mental"]
        episode = model["episodes"][0]
        mental["variables"][0]["observed_by"] = []
        mental["events"] = []
        mental["plans"][0]["weights"] = None
        episode["previous_weights"] = episode["current_weights"] = None
        result, _ = self.run_candidate(candidate)
        self.assertEqual(result.status, "PARTIAL", result.diagnostics)
        row = self.actual(result).values["models"][0]["episodes"][0]
        self.assertEqual(
            row["derived"]["profiles"][0]["appraisal"]["current_value"]["status"],
            "UNWEIGHTED_POSSIBILITIES",
        )
        self.assertEqual(
            row["derived"]["profiles"][0]["appraisal"]["current_value"]["lower"], "-3"
        )
        self.assertEqual(
            row["derived"]["profiles"][0]["appraisal"]["current_value"]["upper"], "3"
        )
        self.assertTrue(
            all(
                not b["computation"]
                for c in row["derived"]["coping"]
                for b in c["branches"]
            )
        )
        self.assertIn("COPING_PROBABILITY_UNSPECIFIED", result.answer)

    def test_resources_and_withdrawn_assumptions_keep_frontier_not_invalid_input(self):
        for limit in (1, 2, 4, 8, 12, 16, 24, 32):
            with self.subTest(limit=limit):
                request = replace(
                    self.request,
                    request_id="budget-" + str(limit),
                    budget=replace(self.request.budget, max_local_evaluations=limit),
                )
                result, _ = self.run_candidate(request=request)
                self.assertIn(
                    result.status, ("COMPLETED", "PARTIAL"), result.diagnostics
                )
                self.assertLessEqual(result.usage["local_evaluations"], limit)
                if result.status == "PARTIAL":
                    self.assertIn("FRONTIER", result.answer)
        candidate = self.revised_candidate()
        candidate["models"][0]["mental"]["active_assumptions"].remove(
            "new-message-hypothesis"
        )
        result, _ = self.run_candidate(
            candidate, replace(self.request, request_id="withdrawn")
        )
        self.assertEqual(result.status, "PARTIAL", result.diagnostics)
        first, second = self.actual(result).values["models"][0]["episodes"]
        self.assertEqual(first["status"], "COMPUTED")
        self.assertEqual(second["status"], "UNCOMPUTED")
        self.assertFalse(second["derived"])
        self.assertIn("EVENT_ASSUMPTION_RETRACTED", result.answer)

    def test_actual_world_product_frontier_retains_previous_appraisal(self):
        candidate = self.revised_candidate()
        mental = candidate["models"][0]["mental"]
        refs = mental["variables"][0]["segment_ids"]
        mental["events"] = mental["events"][1:]
        mental["plans"][0]["weights"] = {"r": "1"}
        candidate["models"][0]["episodes"][0]["current_weights"] = {"r": "1"}
        mental["variables"].extend(
            dict(
                id="extra" + str(i),
                initial=False,
                observed_by=["a", "b"],
                segment_ids=refs,
            )
            for i in range(7)
        )
        result, _ = self.run_candidate(candidate)
        self.assertEqual(result.status, "PARTIAL", result.diagnostics)
        first, second = self.actual(result).values["models"][0]["episodes"]
        self.assertEqual(first["status"], "COMPUTED")
        self.assertEqual(second["status"], "UNCOMPUTED")
        self.assertFalse(second["derived"])
        self.assertIn("WORLD_FRONTIER", result.answer)

    def test_material_source_anchor_no_proposed_values_and_revision_binding(self):
        for mutation in ("question", "value", "weights", "previous"):
            candidate = self.candidate()
            row = candidate["models"][0]["episodes"][0]
            if mutation == "question":
                from hcl.semantics.segments import question_segments

                row["goals"][0]["segment_ids"] = [
                    question_segments(self.request.question)[0].segment_id
                ]
            elif mutation == "value":
                row["appraisal"] = {"desirability": "POSITIVE"}
            elif mutation == "weights":
                row["current_weights"] = {"r": "1"}
            else:
                row["previous_id"] = "nonexistent"
            result, _ = self.run_candidate(
                candidate, replace(self.request, request_id=mutation)
            )
            self.assertEqual(result.status, "INVALID_REQUEST", result.diagnostics)
            self.assertFalse(result.claim_records)

    def test_stream_reopen_checkpoint_and_acl_replay_never_resend(self):
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
                issue=ExecutionIssue("root", goals=(Issue(seam, "affect.evaluate"),)),
            )
            port = OfflineModelPort(json.dumps(self.candidate()))
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
            old_owner = self.store.owner_id
            path = self.store.path
            self.store.close()
            self.store = StateStore.sqlite(path, revision=True)
            self.fixture.store = self.fixture.scene.store = self.store
            RecoveryManager(self.store).resume_execution(
                request, expected_owner_id=old_owner
            )
            port = OfflineModelPort("NO_NEW_SEND")
            client = HCL(
                self.store, principal=self.owner, gateway=ModelGateway(self.store, port)
            )

            async def collect():
                return [e async for e in client.stream(request)]

            if seam != "return_persisted":
                with patch.object(
                    LocalModelOperator,
                    "run",
                    side_effect=AssertionError("no recomputation"),
                ):
                    result = asyncio.run(collect())[-1].result
            else:
                result = asyncio.run(collect())[-1].result
            self.assertEqual(result.status, "COMPLETED", result.diagnostics)
            self.assertEqual(result.usage["mock_calls"], 1)
            replay = client.run_sync(request)
            self.assertEqual(
                (replay.answer, replay.claim_records),
                (result.answer, result.claim_records),
            )
            self.assertEqual(port.attempts, 0)
        self.store.set_readers("scene", self.owner, "story", {"bob"})
        denied = client.run_sync(request)
        self.assertEqual(denied.status, "DENIED")
        self.assertFalse(denied.answer or denied.claim_records)

    def test_zero_priority_derived_numeric_and_prior_affect_boundaries(self):
        candidate = self.candidate()
        coping = candidate["models"][0]["episodes"][0]["coping"][0]
        coping["adjustments"][0]["multipliers"] = {"safety": "0", "duty": "0"}
        result, _ = self.run_candidate(candidate)
        self.assertEqual(result.status, "PARTIAL", result.diagnostics)
        branch = self.actual(result).values["models"][0]["episodes"][0]["derived"][
            "coping"
        ][0]["branches"][0]
        self.assertEqual(branch["status"], "UNDEFINED_PRIORITY")
        self.assertFalse(branch["computation"])
        self.assertIn("COPING_ZERO_PRIORITY_UNDEFINED", result.answer)
        candidate = self.candidate()
        coping = candidate["models"][0]["episodes"][0]["coping"][0]
        coping["adjustments"][0]["multipliers"] = {"safety": "999983", "duty": "999978"}
        result, _ = self.run_candidate(
            candidate, replace(self.request, request_id="derived-numeric")
        )
        self.assertEqual(result.status, "PARTIAL", result.diagnostics)
        self.assertIn("AFFECT_DERIVED_NUMERIC_FRONTIER", result.answer)
        candidate = self.revised_candidate()
        episode = candidate["models"][0]["episodes"][1]
        episode["revision_kind"] = "ANALYST_REINTERPRETATION"
        episode["mappings"][0]["requires_previous"] = ["loss-related-distress"]
        episode["mappings"][0]["conditions"] = [
            dict(goal_id="safety", dimension="desirability", value="POSITIVE")
        ]
        result, _ = self.run_candidate(
            candidate, replace(self.request, request_id="prior-affect")
        )
        self.assertEqual(result.status, "COMPLETED", result.diagnostics)
        hypothesis = self.actual(result).values["models"][0]["episodes"][1]["derived"][
            "hypotheses"
        ][0]
        self.assertEqual(hypothesis["status"], "SUPPORTED_CONDITIONAL")
        self.assertIn("loss-related-distress", hypothesis["previous_hypotheses"])
        candidate["models"][0]["episodes"][1]["revision_kind"] = "NEW_INFORMATION"
        result, _ = self.run_candidate(
            candidate, replace(self.request, request_id="hidden-mechanism-revision")
        )
        self.assertEqual(result.status, "INVALID_REQUEST", result.diagnostics)

    def attention_candidate(self, informative=False, override=None):
        candidate = self.candidate()
        model = candidate["models"][0]
        mental = model["mental"]
        episode = model["episodes"][0]
        mental["variables"][0]["observed_by"] = []
        mental["events"] = []
        mental["plans"][0]["weights"] = {"r": "1/2", "b": "1/2"}
        episode["previous_weights"] = episode["current_weights"] = {
            "r": "1/2",
            "b": "1/2",
        }
        graph = mental["plans"][0]["graph"]
        states = graph["states"]
        opposite = deepcopy(graph["actions"][0])
        opposite["id"] = "opposite"
        opposite["transitions"].update(r="harm", b="success")
        probe = deepcopy(graph["actions"][0])
        probe.update(
            id="probe",
            transitions={s: s for s in states},
            observations={s: s if informative else "same" for s in states},
        )
        graph["actions"].extend([opposite, probe])
        coping = episode["coping"][0]
        episode["coping"] = [coping]
        coping.update(
            priorities={"safety": "1", "duty": "0"},
            adjustments=[],
            horizon=2,
            action_ids=[a["id"] for a in graph["actions"]],
        )
        if override is not None:
            coping["observation_overrides"] = {
                "probe": {s: override(s) for s in states}
            }
        return candidate

    def test_coping_attention_cannot_invent_observations_but_can_merge_or_rename(self):
        cases = [
            ("original", False, None, "COMPLETED", "0"),
            ("invented", False, lambda s: s, "INVALID_REQUEST", None),
            ("source-sensor", True, None, "COMPLETED", "5"),
            ("coarsened", True, lambda s: "merged", "COMPLETED", "0"),
            ("renamed", True, lambda s: "renamed-" + s, "COMPLETED", "5"),
        ]
        for name, informative, override, status, expected in cases:
            with self.subTest(name=name):
                result, _ = self.run_candidate(
                    self.attention_candidate(informative, override),
                    replace(self.request, request_id=name),
                )
                self.assertEqual(result.status, status, result.diagnostics)
                if expected is None:
                    self.assertFalse(result.claim_records)
                    continue
                computation = self.actual(result).values["models"][0]["episodes"][0][
                    "derived"
                ]["coping"][0]["branches"][0]["computation"]
                self.assertEqual(computation["q"]["probe"], expected)
                if expected == "5":
                    self.assertEqual(computation["best_actions"], ("probe",))

    def test_actual_opportunity_frontier_preserves_computed_subjective_appraisal(self):
        candidate = self.candidate()
        model = candidate["models"][0]
        model["mental"]["variables"][0]["initial"] = False
        model["mental"]["events"][0].update(effects={"open": True}, seen_by=["a"])
        model["episodes"][0]["previous_weights"] = {"b": "1"}
        witnessed = False
        retained = None
        for limit in range(1, 41):
            with self.subTest(limit=limit):
                request = replace(
                    self.request,
                    request_id="separate-world-budget-" + str(limit),
                    budget=replace(self.request.budget, max_local_evaluations=limit),
                )
                result, _ = self.run_candidate(candidate, request)
                self.assertIn(
                    result.status, ("COMPLETED", "PARTIAL"), result.diagnostics
                )
                self.assertLessEqual(result.usage["local_evaluations"], limit)
                row = self.actual(result).values["models"][0]["episodes"][0]
                for profile in row["derived"].get("profiles", ()):
                    control = profile["control"]
                    if "AFFECT_ACTUAL_OPPORTUNITY_FRONTIER" in control["frontier"]:
                        witnessed = True
                        retained = request, result
                        self.assertEqual(result.status, "PARTIAL")
                        self.assertEqual(control["status"], "COMPUTED")
                        self.assertEqual(
                            profile["appraisal"]["current_value"]["lower"],
                            "-3" if profile["goal_id"] == "safety" else "3",
                        )
                        self.assertTrue(
                            any(
                                v is None
                                for a in control["actions"].values()
                                for v in a["actual_world_feasibility"].values()
                            )
                        )
                        self.assertIn(
                            "AFFECT_ACTUAL_OPPORTUNITY_FRONTIER", result.answer
                        )
        self.assertTrue(witnessed)
        import asyncio
        from hcl.memory.store import StateStore

        request, original = retained
        path = self.store.path
        self.store.close()
        self.store = StateStore.sqlite(path, revision=True)
        self.fixture.store = self.fixture.scene.store = self.store
        port = OfflineModelPort("NO_NEW_SEND")
        client = HCL(
            self.store, principal=self.owner, gateway=ModelGateway(self.store, port)
        )

        async def collect():
            return [event async for event in client.stream(request)]

        for replay in (client.run_sync(request), asyncio.run(collect())[-1].result):
            self.assertEqual(
                (replay.status, replay.answer, replay.claim_records),
                (original.status, original.answer, original.claim_records),
            )
            self.assertEqual(replay.usage["mock_calls"], 1)
        self.assertEqual(port.attempts, 0)

    def test_declared_infeasible_forecast_propagates_named_partial_reason(self):
        import asyncio

        for missing in (False, True):
            candidate = self.candidate()
            model = candidate["models"][0]
            model["mental"]["plans"][0]["graph"]["actions"][0]["feasible"] = ["b"]
            if missing:
                model["episodes"][0]["forecast_action"] = None
            request = replace(self.request, request_id="forecast-" + str(missing))
            port = OfflineModelPort(json.dumps(candidate))
            client = HCL(
                self.store, principal=self.owner, gateway=ModelGateway(self.store, port)
            )

            async def collect():
                return [event async for event in client.stream(request)]

            result = asyncio.run(collect())[-1].result
            self.assertEqual(
                result.status, "COMPLETED" if missing else "PARTIAL", result.diagnostics
            )
            row = self.actual(result).values["models"][0]["episodes"][0]
            self.assertEqual(
                row["derived"]["forecast"]["status"],
                (
                    "NO_PROSPECTIVE_MODEL"
                    if missing
                    else "FORECAST_OPPORTUNITY_UNRESOLVED"
                ),
            )
            self.assertEqual(
                row["derived"]["profiles"][0]["appraisal"]["expectation_gap_direction"],
                ("UNCOMPUTED",),
            )
            if missing:
                self.assertNotIn("FORECAST_OPPORTUNITY_UNRESOLVED", result.answer)
            else:
                self.assertIn("FORECAST_OPPORTUNITY_UNRESOLVED", result.answer)
            replay = client.run_sync(request)
            self.assertEqual(
                (replay.status, replay.answer, replay.claim_records),
                (result.status, result.answer, result.claim_records),
            )
            self.assertEqual(port.attempts, 1)

    def test_affect_claim_checks_appraisal_q_scope_source_and_hypothetical_status(self):
        result, _ = self.run_candidate()
        self.assertEqual(result.status, "COMPLETED", result.diagnostics)
        actual = self.actual(result)
        for field in (
            "appraisal",
            "q",
            "hypothetical",
            "view",
            "assumptions",
            "coverage",
            "outer_environment",
        ):
            bad = thaw(actual.values)
            episode = bad["models"][0]["episodes"][0]
            if field == "appraisal":
                episode["derived"]["profiles"][0]["appraisal"]["state_change"][
                    "lower"
                ] = "0"
            elif field == "q":
                episode["derived"]["coping"][0]["branches"][0]["computation"]["q"][
                    "cross"
                ] = "99"
            elif field == "hypothetical":
                episode["derived"]["coping"][0]["branches"][0]["consequences"][0][
                    "hypothetical"
                ] = False
            elif field == "view":
                episode["views"]["current"]["mapping"]["states"] = ["r"]
            elif field == "coverage":
                bad["models"][0]["episodes"] = []
            elif field == "assumptions":
                episode["assumption_environments"] = []
            with self.subTest(field=field), self.assertRaises(HCLFailure):
                AnswerAssembler()._claim(
                    replace(
                        actual,
                        values=bad,
                        assumption_environments=(
                            ()
                            if field == "outer_environment"
                            else actual.assumption_environments
                        ),
                    )
                )

    def aliased_revision_candidate(self):
        candidate = self.revised_candidate(received=False)
        model = candidate["models"][0]
        episode = model["episodes"][1]
        episode["revision_kind"] = "ANALYST_REINTERPRETATION"
        plan = model["mental"]["plans"][1]
        names = {s: "renamed-" + s for s in plan["graph"]["states"]}

        def rekey(values):
            return {names[s]: v for s, v in values.items()}

        for field in ("previous_weights", "current_weights"):
            episode[field] = rekey(episode[field])
        for goal in episode["goals"]:
            goal["utilities"] = rekey(goal["utilities"])
        plan["weights"] = rekey(plan["weights"])
        for binding in plan["bindings"]:
            binding["state"] = names[binding["state"]]
        graph = plan["graph"]
        for field in ("states", "terminal"):
            graph[field] = [names[s] for s in graph[field]]
        graph["utilities"] = rekey(graph["utilities"])
        for action in graph["actions"]:
            for field in ("enabled", "feasible"):
                action[field] = [names[s] for s in action[field]]
            action["transitions"] = {
                names[s]: names[t] for s, t in action["transitions"].items()
            }
            action["observations"] = {
                names[s]: "observation-alias-" + v
                for s, v in action["observations"].items()
            }
        return candidate

    def test_alias_only_reappraisal_preserves_goals_and_qualifies_replay(self):
        import asyncio
        from hcl.memory.store import StateStore
        from hcl.semantics.segments import segment_snapshot

        original_snapshot = self.store.snapshot(
            "scene", self.owner, self.request.source_handles
        )
        source = next(iter(original_snapshot.immutable_views.values()))
        handle = self.store.put_source(
            "scene",
            self.owner,
            "story",
            source.text + "\nA further report repeats the same goals.",
        )
        self.fixture.scene.handle = handle
        self.request = replace(self.request, source_handles=(handle,))
        self.fixture.request = self.request
        candidate = self.aliased_revision_candidate()
        snapshot = self.store.snapshot("scene", self.owner, self.request.source_handles)
        source_refs = [
            s.segment_id
            for s in segment_snapshot(snapshot, self.request.question)
            if s.kind == "SOURCE"
        ]
        self.assertGreater(len(source_refs), 1)
        for goal in candidate["models"][0]["episodes"][1]["goals"]:
            goal["segment_ids"] = [source_refs[-1]]
        result, port = self.run_candidate(candidate)
        self.assertEqual(result.status, "COMPLETED", result.diagnostics)
        actual = self.actual(result)
        changes = actual.values["models"][0]["episodes"][1]["derived"]["reappraisal"][
            "changes"
        ]
        self.assertEqual({r["change"] for r in changes}, {"UNCHANGED"})
        self.assertTrue(all(r["evidence_changed"] for r in changes))
        self.assertTrue(
            all(r["goal_model_comparison"]["status"] == "EQUIVALENT" for r in changes)
        )
        self.assertTrue(
            all(
                r["goal_model_comparison"]["state_aliases"]["r"] == "renamed-r"
                for r in changes
            )
        )
        for mutation in ("change", "bijection"):
            bad = thaw(actual.values)
            row = bad["models"][0]["episodes"][1]["derived"]["reappraisal"]["changes"][
                0
            ]
            if mutation == "change":
                row["change"] = "REVISED"
            else:
                row["goal_model_comparison"]["state_aliases"]["r"] = "renamed-b"
            with self.subTest(mutation=mutation), self.assertRaises(HCLFailure):
                AnswerAssembler()._claim(replace(actual, values=bad))
        path = self.store.path
        self.store.close()
        self.store = StateStore.sqlite(path, revision=True)
        self.fixture.store = self.fixture.scene.store = self.store
        port = OfflineModelPort("NO_NEW_SEND")
        client = HCL(
            self.store, principal=self.owner, gateway=ModelGateway(self.store, port)
        )

        async def collect():
            return [e async for e in client.stream(self.request)]

        for replay in (
            client.run_sync(self.request),
            asyncio.run(collect())[-1].result,
        ):
            self.assertEqual(
                (replay.status, replay.answer, replay.claim_records),
                (result.status, result.answer, result.claim_records),
            )
        self.assertEqual(port.attempts, 0)

    def test_unreached_goal_consequences_and_transitions_are_not_discarded(self):
        for mutation in ("utility", "transition"):
            candidate = self.aliased_revision_candidate()
            model = candidate["models"][0]
            for episode in model["episodes"]:
                episode["forecast_action"] = None
            if mutation == "utility":
                # Success is unreachable from the current known closed state.
                model["episodes"][1]["goals"][0]["utilities"]["renamed-success"] = "6"
            else:
                model["mental"]["plans"][1]["graph"]["actions"][0]["transitions"][
                    "renamed-r"
                ] = "renamed-harm"
            result, _ = self.run_candidate(
                candidate, replace(self.request, request_id=mutation)
            )
            self.assertEqual(result.status, "COMPLETED", result.diagnostics)
            first, second = self.actual(result).values["models"][0]["episodes"]
            self.assertEqual(
                first["derived"]["profiles"][0]["appraisal"],
                second["derived"]["profiles"][0]["appraisal"],
            )
            change = next(
                r
                for r in second["derived"]["reappraisal"]["changes"]
                if r["goal_id"] == "safety"
            )
            self.assertEqual(change["change"], "REVISED")
            self.assertIn("goal_model", change["changed_dimensions"])
            self.assertEqual(change["goal_model_comparison"]["status"], "DIFFERENT")

    def test_reappraisal_comparison_work_exhaustion_is_visible_and_replayable(self):
        candidate = self.aliased_revision_candidate()
        complete, _ = self.run_candidate(
            candidate, replace(self.request, request_id="measure-comparison")
        )
        row = self.actual(complete).values["models"][0]["episodes"][1]
        comparison_work = row["derived"]["reappraisal"]["comparison_work"]
        self.assertGreater(comparison_work, 1)
        limit = complete.usage["local_evaluations"] - comparison_work
        request = replace(
            self.request,
            request_id="comparison-bound",
            budget=replace(self.request.budget, max_local_evaluations=limit),
        )
        result, port = self.run_candidate(candidate, request)
        self.assertEqual(result.status, "PARTIAL", result.diagnostics)
        self.assertEqual(result.usage["local_evaluations"], limit)
        self.assertIn("AFFECT_GOAL_COMPARISON_FRONTIER", result.answer)
        changes = self.actual(result).values["models"][0]["episodes"][1]["derived"][
            "reappraisal"
        ]["changes"]
        self.assertTrue(all(r["change"] == "UNRESOLVED" for r in changes))
        self.assertTrue(all(r["goal_model_comparison"]["work"] == 0 for r in changes))
        replay = HCL(
            self.store, principal=self.owner, gateway=ModelGateway(self.store, port)
        ).run_sync(request)
        self.assertEqual((replay.status, replay.answer), (result.status, result.answer))
        self.assertEqual(port.attempts, 1)

    def test_composition_capacity_names_exact_operator_before_any_model_send(self):
        import asyncio
        from hcl import RevisionIssue

        handle = self.store.put_source(
            "scene", self.owner, "story", "An actor observes a changed route.\n" * 200
        )
        for kind, prefix in [
            ("revision.evaluate", "REVISION"),
            ("mental.simulate", "MENTAL"),
            ("argument.evaluate", "ARGUMENT"),
            ("hypothesis.discover", "DISCOVERY"),
            ("interaction.evaluate", "INTERACTION"),
            ("affect.evaluate", "AFFECT"),
        ]:
            request = replace(
                self.request,
                request_id=kind,
                source_handles=(handle,),
                issue=ExecutionIssue(
                    "root",
                    goals=(
                        (
                            RevisionIssue(kind)
                            if kind == "revision.evaluate"
                            else Issue(kind, kind)
                        ),
                    ),
                ),
                budget=replace(
                    self.request.budget, max_request_bytes=4000, max_context_tokens=4000
                ),
            )
            port = OfflineModelPort("{}")
            client = HCL(
                self.store, principal=self.owner, gateway=ModelGateway(self.store, port)
            )

            async def collect():
                return [e async for e in client.stream(request)]

            result = asyncio.run(collect())[-1].result
            self.assertEqual(result.status, "BUDGET_EXHAUSTED", result.diagnostics)
            self.assertEqual(
                [d.code for d in result.diagnostics], [prefix + "_COMPOSITION_CAPACITY"]
            )
            self.assertFalse(result.answer or result.claim_records)
            self.assertEqual(port.attempts, 0)
            self.assertEqual(client.run_sync(request).diagnostics, result.diagnostics)


if __name__ == "__main__":
    unittest.main()
