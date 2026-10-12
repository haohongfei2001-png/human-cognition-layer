"""Real mechanisms discover channel edits, not a fixture lookup of answers."""

from copy import deepcopy
from dataclasses import replace
from itertools import product
import json
import unittest

from hcl import ExecutionIssue, HCL
from hcl.kernel.types import Issue, thaw
from hcl.models.gateway import ModelGateway, OfflineModelPort
from hcl.semantics.segments import segment_snapshot
from tests import test_unified_s3_scene as scene_fixtures


class DiscoveryExecutionTests(unittest.TestCase):
    def setUp(self):
        self.scene = scene_fixtures.SceneExecutionTests()
        self.scene.setUp()
        self.store, self.owner = self.scene.store, self.scene.owner
        self.context_bits = tuple(product((False, True), repeat=3))
        text = "".join(
            f"记录{i}: 通道开放={opened},收到通知={received},亲眼看见={seen}；实际选择={'绕行' if not opened and (received or seen) else '直走'}。\n"
            for i, (opened, received, seen) in enumerate(self.context_bits)
        )
        self.scene.handle = self.store.put_source("scene", self.owner, "story", text)
        self.request = self.scene.request(
            issue=ExecutionIssue(
                "root", goals=(Issue("explain", "hypothesis.discover"),)
            ),
            budget=replace(
                self.scene.budget,
                max_local_evaluations=1024,
                max_request_bytes=1048576,
                max_output_bytes=1048576,
                max_visible_output_tokens=1048576,
                max_total_output_bytes=16777216,
                max_context_tokens=1048576,
            ),
        )

    def tearDown(self):
        self.scene.tearDown()

    def candidate(self):
        base = self.scene.candidate(self.request)
        model = base["models"][0]
        model["queries"] = []
        segments = segment_snapshot(
            self.store.snapshot("scene", self.owner, self.request.source_handles),
            self.request.question,
        )
        source = [s.segment_id for s in segments if s.kind == "SOURCE"]
        query = [s.segment_id for s in segments if s.kind == "QUESTION"]
        contexts, observations = [], []
        for i, (opened, received, seen) in enumerate(self.context_bits):
            template = deepcopy(base)
            template["models"][0]["events"][0]["effects"]["open"] = opened
            features = dict(received=received, seen=seen)
            contexts.append(
                dict(
                    id=f"case-{i}",
                    adapter="mental-scene-1",
                    template=template,
                    features=features,
                    feature_segments={k: [source[i]] for k in features},
                    segment_ids=[source[i]],
                )
            )
            observations.append(
                dict(
                    id=f"observation-{i}",
                    context_id=f"case-{i}",
                    query_id="choice",
                    values=[
                        (
                            "detour-start"
                            if not opened and (received or seen)
                            else "direct"
                        )
                    ],
                    factor_id=f"event-{i}",
                    provenance_group=f"record-{i}",
                    derived_from=[],
                    segment_ids=[source[i]],
                )
            )
        program = dict(
            id="received-only",
            adapter="mental-scene-1",
            latent={"reward": "6"},
            observe=[
                dict(
                    event_id="closure",
                    actor="a",
                    channel="seen_by",
                    when={"feature": "received"},
                )
            ],
            transition=[
                dict(
                    target=dict(
                        kind="utility", plan_id="route-at-action", state="success"
                    ),
                    value={"latent": "reward"},
                )
            ],
            constraint=[],
            predict=[
                dict(
                    id="choice", field="plan.best_actions", record_id="route-at-action"
                )
            ],
        )
        return dict(
            schema="hcl-discovery-candidates-1",
            contexts=contexts,
            observations=observations,
            probes=[],
            programs=[program],
            grammar=dict(
                observation_features=["received", "seen"],
                latent_domains={"reward": ["4", "6", "8"]},
                max_expression_size=40,
            ),
            search=dict(max_rounds=1, beam=12, new_per_round=4, max_candidates=64),
            unmodeled_segments=[],
        )

    def run_candidate(self, candidate=None, request=None):
        port = OfflineModelPort(
            json.dumps(candidate or self.candidate(), ensure_ascii=False)
        )
        result = HCL(
            self.store, principal=self.owner, gateway=ModelGateway(self.store, port)
        ).run_sync(request or self.request)
        return result, port

    def test_real_residual_channel_edit_changes_action_predictions(self):
        from hcl.operators.abduction import program_hash

        candidate = self.candidate()
        original = deepcopy(candidate)
        result, port = self.run_candidate(candidate)
        self.assertIn(result.status, ("PARTIAL", "COMPLETED"), result.diagnostics)
        actual = next(
            r
            for r in self.store.inferences("scene", self.owner)
            if r.result_id in result.execution_receipt["result_ids"]
        )
        values = actual.values
        base = values["prediction_matrix"][program_hash(candidate["programs"][0])]
        self.assertEqual(
            [
                c["observation_id"]
                for c in base["cells"]
                if c["relation"] == "CONTRADICTED"
            ],
            ["observation-1"],
        )
        perfect = [
            key
            for key, col in values["prediction_matrix"].items()
            if len(col["profile"]["explained"]) == 8
        ]
        self.assertTrue(perfect)
        self.assertTrue(set(perfect) & set(values["pareto_programs"]))
        self.assertTrue(
            any(
                p["observe"][0]["when"].get("op") == "or"
                for key, p in values["programs"].items()
                if key in perfect
            )
        )
        for column in values["prediction_matrix"].values():
            for cell in column["cells"]:
                self.assertEqual(cell["prediction"]["status"], "COMPUTED")
                self.assertTrue(cell["prediction"]["result_refs"])
        self.assertEqual(port.attempts, 1)
        self.assertEqual(candidate, original)
        self.assertIn("Actually recomputed mechanism edits", result.answer)

    def test_more_complex_current_equivalent_member_is_still_probed(self):
        candidate = self.candidate()
        candidate["contexts"] = [candidate["contexts"][2]]
        candidate["observations"] = [candidate["observations"][2]]
        candidate["search"]["max_rounds"] = 0
        first = candidate["programs"][0]
        first["latent"]["reward"] = "4"
        second = deepcopy(first)
        second["id"] = "complex-reward-8"
        second["latent"]["reward"] = "8"
        second["constraint"] = [{"const": True}]
        candidate["programs"].append(second)
        probe = deepcopy(candidate["contexts"][0])
        probe["id"] = "counterfactual-cost"
        actions = probe["template"]["models"][0]["plans"][0]["graph"]["actions"]
        next(a for a in actions if a["id"] == "finish")["cost"] = "6"
        candidate["probes"] = [
            dict(
                id="cost-7",
                context=probe,
                query_id="choice",
                segment_ids=probe["segment_ids"],
            )
        ]
        # Keep all original source rows explicitly unmodeled; they are not
        # observations used in this one-context equivalence comparison.
        candidate["unmodeled_segments"] = [
            s.segment_id
            for s in segment_snapshot(
                self.store.snapshot("scene", self.owner, self.request.source_handles),
                self.request.question,
            )
            if s.kind == "SOURCE"
        ]
        result, _ = self.run_candidate(candidate)
        self.assertEqual(result.status, "PARTIAL", result.diagnostics)
        values = self.store.inferences("scene", self.owner)[-1].values
        self.assertEqual(len(values["prediction_classes"]), 1)
        self.assertEqual(len(values["prediction_classes"][0]["members"]), 2)
        self.assertEqual(len(values["pareto_programs"]), 1)
        probe = values["distinguishing_observations"][0]
        self.assertEqual(probe["separated_pairs"], 1)
        self.assertEqual(len(probe["tested_members"]), 2)
        by_name = {
            values["programs"][key]["id"]: row["prediction"]["values"]
            for key, row in probe["predictions"].items()
        }
        self.assertEqual(
            by_name,
            {"received-only": ("direct",), "complex-reward-8": ("detour-start",)},
        )
        self.assertIn("separates 1 computed candidate pairs", result.answer)

    def test_distinct_same_span_obligations_and_duplicate_reports_keep_factors(self):
        from hcl.semantics.discovery_compiler import DiscoveryCompiler

        candidate = self.candidate()
        original = candidate["observations"][0]
        other = deepcopy(original)
        other.update(
            id="distinct-claim",
            query_id="second-choice",
            factor_id="other",
            provenance_group="other",
        )
        candidate["observations"].append(other)
        prediction = deepcopy(candidate["programs"][0]["predict"][0])
        prediction["id"] = "second-choice"
        candidate["programs"][0]["predict"].append(prediction)
        for index in range(20):
            copied = deepcopy(original)
            copied.update(
                id=f"copy-{index}",
                factor_id=f"copy-factor-{index}",
                provenance_group="retelling",
                derived_from=[original["id"]],
            )
            candidate["observations"].append(copied)
        snapshot = self.store.snapshot("scene", self.owner, self.request.source_handles)
        typed = DiscoveryCompiler().compile(
            snapshot,
            segment_snapshot(snapshot, self.request.question),
            json.dumps(candidate),
            self.request.budget,
        )
        factors = {o["id"]: o["factor_id"] for o in typed["observations"]}
        self.assertNotEqual(factors[original["id"]], factors["distinct-claim"])
        self.assertEqual(
            {factors[f"copy-{i}"] for i in range(20)}, {factors[original["id"]]}
        )
        self.assertEqual(len(set(factors.values())), 9)
        # No source group's declared independence is converted into a posterior.
        candidate["search"]["max_rounds"] = 0
        result, _ = self.run_candidate(candidate)
        self.assertEqual(result.status, "COMPLETED", result.diagnostics)
        values = self.store.inferences("scene", self.owner)[-1].values
        self.assertEqual(values["local_evaluations"], 24)
        self.assertEqual(values["factor_independence"], "NOT_ESTABLISHED")

    def test_budget_frontier_is_unknown_and_tampered_comparison_is_rejected(self):
        from hcl.kernel.types import HCLFailure
        from hcl.runtime.answer import AnswerAssembler

        result, _ = self.run_candidate(
            request=replace(
                self.request,
                budget=replace(self.request.budget, max_local_evaluations=1),
            )
        )
        self.assertEqual(result.status, "PARTIAL", result.diagnostics)
        actual = self.store.inferences("scene", self.owner)[-1]
        values = actual.values
        column = next(iter(values["prediction_matrix"].values()))
        self.assertTrue(
            all(cell["relation"] == "UNCOMPUTED" for cell in column["cells"])
        )
        self.assertEqual(values["local_evaluations"], 1)
        self.assertTrue(values["frontier"])
        wrong = thaw(values)
        next(iter(wrong["prediction_matrix"].values()))["cells"][0][
            "relation"
        ] = "EXPLAINED"
        with self.assertRaises(HCLFailure):
            AnswerAssembler()._claim(replace(actual, values=wrong))

    def test_argument_supplier_uses_same_discoverer_and_actual_grounded_recompute(self):
        from tests.test_unified_s4_engine import ArgumentExecutionTests

        fixture = ArgumentExecutionTests()
        fixture.setUp()
        try:
            request = replace(
                fixture.request,
                issue=ExecutionIssue(
                    "root", goals=(Issue("explain", "hypothesis.discover"),)
                ),
                budget=replace(self.request.budget, max_local_evaluations=100),
            )
            template = fixture.candidate(request, prefer=False)
            refs = template["models"][0]["premises"][0]["segment_ids"]
            context = dict(
                id="debate",
                adapter="argument-model-1",
                template=template,
                features={},
                feature_segments={},
                segment_ids=refs,
            )
            candidate = dict(
                schema="hcl-discovery-candidates-1",
                contexts=[context],
                observations=[
                    dict(
                        id="accepted-claim",
                        context_id="debate",
                        query_id="acceptance",
                        values=[dict(positive=True, opposed=False)],
                        factor_id="claim",
                        provenance_group="source",
                        derived_from=[],
                        segment_ids=refs,
                    )
                ],
                probes=[],
                programs=[
                    dict(
                        id="defeasible-reading",
                        adapter="argument-model-1",
                        latent={"strict": False},
                        observe=[],
                        transition=[
                            dict(
                                target=dict(kind="strict", rule_id="from-witness"),
                                value={"latent": "strict"},
                            )
                        ],
                        constraint=[],
                        predict=[
                            dict(
                                id="acceptance",
                                field="argument.acceptance",
                                record_id="event-query",
                            )
                        ],
                    )
                ],
                grammar=dict(
                    observation_features=[],
                    latent_domains={"strict": [False, True]},
                    max_expression_size=128,
                ),
                search=dict(max_rounds=1, beam=12, new_per_round=4, max_candidates=64),
                unmodeled_segments=[],
            )
            port = OfflineModelPort(json.dumps(candidate))
            result = HCL(
                fixture.store,
                principal=fixture.owner,
                gateway=ModelGateway(fixture.store, port),
            ).run_sync(request)
            self.assertEqual(result.status, "COMPLETED", result.diagnostics)
            values = fixture.store.inferences("s", fixture.owner)[-1].values
            self.assertEqual(len(values["edit_history"]), 1)
            self.assertEqual(values["edit_history"][0]["operation"], "replace_latent")
            computed = {
                v["programs"][key]["latent"]["strict"]: col
                for v in (values,)
                for key, col in v["prediction_matrix"].items()
            }
            self.assertEqual(computed[False]["cells"][0]["relation"], "CONTRADICTED")
            self.assertEqual(computed[True]["cells"][0]["relation"], "EXPLAINED")
            self.assertTrue(
                computed[True]["actual_results"][0]["values"]["models"][0]["iterations"]
            )
        finally:
            fixture.tearDown()

    def test_returned_and_computed_recovery_replay_without_another_send(self):
        from unittest.mock import patch
        from hcl.runtime.recovery import RecoveryManager
        from hcl.operators.local_model import LocalModelOperator
        from hcl.memory.store import StateStore

        class Crash(BaseException):
            pass

        for seam in (
            "return_persisted",
            "execution_computed",
            "execution_effects_committed",
        ):
            with self.subTest(seam=seam):
                request = replace(
                    self.request,
                    request_id=seam,
                    issue=ExecutionIssue(
                        "root", goals=(Issue(seam, "hypothesis.discover"),)
                    ),
                )
                port = OfflineModelPort(json.dumps(self.candidate()))
                client = HCL(
                    self.store,
                    principal=self.owner,
                    gateway=ModelGateway(self.store, port),
                )

                def crash(stage):
                    if stage == seam:
                        raise Crash()

                with patch.object(self.store, "_checkpoint", crash), self.assertRaises(
                    Crash
                ):
                    client.run_sync(request)
                self.assertEqual(port.attempts, 1)
                old_owner = self.store.owner_id
                self.store.close()
                self.store = StateStore.sqlite(self.scene.path, revision=True)
                self.scene.store = self.store
                RecoveryManager(self.store).resume_execution(
                    request, expected_owner_id=old_owner
                )
                port = OfflineModelPort("NEVER_SEND")
                client = HCL(
                    self.store,
                    principal=self.owner,
                    gateway=ModelGateway(self.store, port),
                )
                if seam == "return_persisted":
                    result = client.run_sync(request)
                else:
                    with patch.object(
                        LocalModelOperator,
                        "run",
                        side_effect=AssertionError("no recompute"),
                    ):
                        result = client.run_sync(request)
                self.assertEqual(result.status, "PARTIAL", result.diagnostics)
                self.assertEqual(result.usage["mock_calls"], 1)
                self.assertEqual(port.attempts, 0)
                repeated = client.run_sync(request)
                self.assertEqual(repeated.answer, result.answer)

    def test_late_revocation_clears_discovery_matrix_and_cached_stream(self):
        import asyncio
        from unittest.mock import patch
        from hcl.memory.store import StateStore

        peer = StateStore.sqlite(self.scene.path, revision=True)
        try:
            original = self.store._checkpoint

            def revoke(stage):
                original(stage)
                if stage == "task_finished":
                    peer.set_readers("scene", self.owner, "story", {"someone-else"})

            with patch.object(self.store, "_checkpoint", revoke):
                result, _ = self.run_candidate()
            self.assertEqual(result.status, "DENIED")
            self.assertFalse(result.answer)
            self.assertFalse(result.claim_records)
            for key in (
                "programs",
                "observations",
                "prediction_matrix",
                "source_bindings",
            ):
                self.assertNotIn(key, str(result.execution_receipt))
            port = OfflineModelPort("NEVER_SEND")
            client = HCL(
                self.store, principal=self.owner, gateway=ModelGateway(self.store, port)
            )

            async def stream():
                return [e async for e in client.stream(self.request)]

            result = asyncio.run(stream())[-1].result
            self.assertEqual(result.status, "DENIED")
            self.assertEqual(port.attempts, 0)
        finally:
            peer.close()

    def test_invalid_targets_supplied_predictions_and_unbound_features_reject(self):
        request = replace(
            self.request, budget=replace(self.request.budget, max_feedback=0)
        )
        original = self.candidate()
        mutations = []
        c = deepcopy(original)
        c["programs"][0]["predict"][0]["values"] = ["direct"]
        mutations.append(c)
        c = deepcopy(original)
        c["programs"][0]["observe"][0]["when"] = {"feature": "observations.values"}
        mutations.append(c)
        c = deepcopy(original)
        c["contexts"][0]["feature_segments"] = {}
        mutations.append(c)
        c = deepcopy(original)
        c["programs"][0]["transition"][0]["target"] = {
            "kind": "observation",
            "id": "observation-1",
        }
        mutations.append(c)
        c = deepcopy(original)
        c["programs"][0]["constraint"] = [{"op": "eval", "args": [{"const": "code"}]}]
        mutations.append(c)
        c = deepcopy(original)
        c["programs"][0]["transition"][0]["target"]["plan_id"] = "missing"
        mutations.append(c)
        for i, candidate in enumerate(mutations):
            result, port = self.run_candidate(
                candidate, replace(request, request_id=f"invalid-{i}")
            )
            self.assertEqual(result.status, "INVALID_REQUEST", result.diagnostics)
            self.assertEqual(port.attempts, 1)
            self.assertFalse(result.claim_records)

    def test_unexpected_solver_failure_keeps_unknown_local_reservation(self):
        from unittest.mock import patch
        from hcl.kernel.types import HCLFailure
        from hcl.operators.mental_scene import MentalSceneOperator

        original = MentalSceneOperator.run

        def fail_after_actual_work(operator, *args, **kwargs):
            original(operator, *args, **kwargs)
            raise HCLFailure(
                "FAILED",
                "mental_model",
                "LOCAL_TEST_FAILURE",
                "model",
                "The bounded computation could not return a verified result.",
            )

        with patch.object(MentalSceneOperator, "run", fail_after_actual_work):
            result, port = self.run_candidate()
        self.assertEqual(result.status, "FAILED", result.diagnostics)
        self.assertIsNone(result.usage["local_evaluations"])
        self.assertEqual(
            result.usage["held_local_evaluations"],
            self.request.budget.max_local_evaluations,
        )
        self.assertEqual(result.usage["mock_calls"], 1)
        self.assertEqual(port.attempts, 1)
        self.assertFalse(result.claim_records)
        repeated, port = self.run_candidate()
        self.assertEqual(repeated.status, "FAILED")
        self.assertEqual(port.attempts, 0)
        self.assertIsNone(repeated.usage["local_evaluations"])

    def test_probe_separation_and_context_identity_cannot_be_fabricated(self):
        from hcl.kernel.types import HCLFailure
        from hcl.runtime.answer import AnswerAssembler

        candidate = self.candidate()
        candidate["search"]["max_rounds"] = 0
        first = candidate["programs"][0]
        first["observe"][0]["when"] = {
            "op": "or",
            "args": [{"feature": "received"}, {"feature": "seen"}],
        }
        first["latent"]["reward"] = "4"
        second = deepcopy(first)
        second["id"] = "goal8"
        second["latent"]["reward"] = "8"
        second["constraint"] = [{"const": True}]
        candidate["programs"].append(second)
        probe = deepcopy(candidate["contexts"][2])
        probe["id"] = "probe"
        next(
            a
            for a in probe["template"]["models"][0]["plans"][0]["graph"]["actions"]
            if a["id"] == "finish"
        )["cost"] = "6"
        candidate["probes"] = [
            dict(
                id="probe",
                context=probe,
                query_id="choice",
                segment_ids=probe["segment_ids"],
            )
        ]
        result, _ = self.run_candidate(candidate)
        self.assertEqual(result.status, "COMPLETED", result.diagnostics)
        actual = self.store.inferences("scene", self.owner)[-1]
        self.assertEqual(
            actual.values["distinguishing_observations"][0]["separated_pairs"], 1
        )
        for kind in (
            "separation",
            "context",
            "complexity",
            "cost",
            "hypothetical",
            "information_gain",
        ):
            values = thaw(actual.values)
            if kind == "hypothetical":
                values["distinguishing_observations"][0]["hypothetical"] = False
            elif kind == "information_gain":
                values["distinguishing_observations"][0]["information_gain"] = 1
            elif kind == "separation":
                values["distinguishing_observations"][0]["separated_pairs"] = 20
            else:
                column = next(iter(values["prediction_matrix"].values()))
                if kind == "context":
                    column["actual_results"][0]["context_hash"] = "other-context"
                elif kind == "complexity":
                    column["complexity"] = 0
                else:
                    column["work"] = 0
            with self.assertRaises(HCLFailure):
                AnswerAssembler()._claim(replace(actual, values=values))

    def test_context_display_alias_cannot_duplicate_evidence_or_solver_work(self):
        candidate = self.candidate()
        candidate["contexts"] = [candidate["contexts"][2]]
        candidate["observations"] = [candidate["observations"][2]]
        candidate["search"]["max_rounds"] = 0
        candidate["unmodeled_segments"] = [
            s.segment_id
            for s in segment_snapshot(
                self.store.snapshot("scene", self.owner, self.request.source_handles),
                self.request.question,
            )
            if s.kind == "SOURCE"
        ]
        first, _ = self.run_candidate(candidate)
        before = next(
            r
            for r in self.store.inferences("scene", self.owner)
            if r.result_id in first.execution_receipt["result_ids"]
        ).values
        context = deepcopy(candidate["contexts"][0])
        context["id"] = "display-alias"
        observation = deepcopy(candidate["observations"][0])
        observation.update(
            id="renamed-observation",
            context_id="display-alias",
            factor_id="renamed-factor",
            provenance_group="renamed-group",
        )
        candidate["contexts"].append(context)
        candidate["observations"].append(observation)
        second, _ = self.run_candidate(
            candidate, replace(self.request, request_id="alias")
        )
        after = next(
            r
            for r in self.store.inferences("scene", self.owner)
            if r.result_id in second.execution_receipt["result_ids"]
        ).values
        self.assertEqual(len(before["evidence_factor_ids"]), 1)
        self.assertEqual(after["evidence_factor_ids"], before["evidence_factor_ids"])
        self.assertEqual(after["local_evaluations"], before["local_evaluations"])
        self.assertEqual(after["local_evaluations"], 3)

    def test_probe_only_conditions_remain_local_and_survive_run_stream_replay(self):
        import asyncio
        from hcl.memory.store import StateStore

        candidate = self.candidate()
        candidate["search"]["max_rounds"] = 0
        context = deepcopy(candidate["contexts"][2])
        context["id"] = "conditional-probe"
        probe_model = context["template"]["models"][0]
        canary = "PROBE_SPECIAL_ASSUMPTION"
        probe_model["assumptions"].append(canary)
        probe_model["active_assumptions"].append(canary)
        candidate["probes"] = [
            dict(
                id="conditional-probe",
                context=context,
                query_id="choice",
                segment_ids=context["segment_ids"],
            )
        ]
        result, _ = self.run_candidate(candidate)
        self.assertEqual(result.status, "COMPLETED", result.diagnostics)
        actual = next(
            r
            for r in self.store.inferences("scene", self.owner)
            if r.result_id in result.execution_receipt["result_ids"]
        )
        self.assertNotIn(
            canary,
            str(
                [
                    c["domain_conditions"]
                    for c in actual.values["prediction_matrix"].values()
                ]
            ),
        )
        self.assertIn(canary, result.answer)
        self.assertIn(canary, actual.assumption_environments)
        self.assertIn(canary, result.claim_records[0].support_envs)
        from hcl.kernel.types import HCLFailure
        from hcl.runtime.answer import AnswerAssembler

        stripped = thaw(actual.values)
        for predicted in stripped["distinguishing_observations"][0][
            "predictions"
        ].values():
            predicted["domain_conditions"] = []
        with self.assertRaises(HCLFailure):
            AnswerAssembler()._claim(replace(actual, values=stripped))
        fields = [
            f
            for claim in result.claim_records
            for f in claim.used_result_fields
            if f.field == "distinguishing_observations"
        ]
        self.assertIn(canary, str([thaw(f.value) for f in fields]))
        fresh_port = OfflineModelPort(json.dumps(candidate, ensure_ascii=False))
        fresh_client = HCL(
            self.store,
            principal=self.owner,
            gateway=ModelGateway(self.store, fresh_port),
        )
        fresh_request = replace(self.request, request_id="probe-fresh-stream")

        async def fresh_stream():
            return [e async for e in fresh_client.stream(fresh_request)]

        fresh = asyncio.run(fresh_stream())[-1].result
        self.assertEqual(fresh.status, "COMPLETED", fresh.diagnostics)
        self.assertIn(canary, fresh.answer)
        self.assertIn(canary, fresh.claim_records[0].support_envs)
        self.assertEqual(fresh_port.attempts, 1)
        self.store.close()
        self.store = StateStore.sqlite(self.scene.path, revision=True)
        self.scene.store = self.store
        port = OfflineModelPort("NEVER_SEND")
        client = HCL(
            self.store, principal=self.owner, gateway=ModelGateway(self.store, port)
        )

        async def stream():
            return [e async for e in client.stream(self.request)]

        replay = asyncio.run(stream())[-1].result
        self.assertEqual(replay.answer, result.answer)
        self.assertEqual(replay.claim_records, result.claim_records)
        replay_run = client.run_sync(fresh_request)
        self.assertEqual(replay_run.answer, fresh.answer)
        self.assertEqual(replay_run.claim_records, fresh.claim_records)
        self.assertEqual(port.attempts, 0)

    def test_fabricated_edit_history_cannot_claim_recomputed_mechanism(self):
        from hcl.kernel.types import HCLFailure
        from hcl.runtime.answer import AnswerAssembler

        result, _ = self.run_candidate()
        actual = next(
            r
            for r in self.store.inferences("scene", self.owner)
            if r.result_id in result.execution_receipt["result_ids"]
        )
        mutations = []
        values = thaw(actual.values)
        values["edit_history"].append(deepcopy(values["edit_history"][0]))
        mutations.append(values)
        values = thaw(actual.values)
        values["edit_history"][0]["child_hash"] = "uncomputed-child"
        mutations.append(values)
        values = thaw(actual.values)
        values["edit_history"][0]["residual_ids"] = ["invented-observation"]
        mutations.append(values)
        values = thaw(actual.values)
        values["edit_history"][0]["after"] = {"const": True}
        mutations.append(values)
        for values in mutations:
            with self.assertRaises(HCLFailure):
                AnswerAssembler()._claim(replace(actual, values=values))

    def test_uncomputed_edits_are_not_delivered_as_recomputed(self):
        from hcl.kernel.types import HCLFailure
        from hcl.runtime.answer import AnswerAssembler

        result, _ = self.run_candidate(
            request=replace(
                self.request,
                budget=replace(self.request.budget, max_local_evaluations=25),
            )
        )
        self.assertEqual(result.status, "PARTIAL", result.diagnostics)
        actual = next(
            r
            for r in self.store.inferences("scene", self.owner)
            if r.result_id in result.execution_receipt["result_ids"]
        )
        edits = actual.values["edit_history"]
        self.assertTrue(edits)
        self.assertTrue(all(e["evaluation_status"] != "RECOMPUTED" for e in edits))
        self.assertIn("Actually recomputed mechanism edits: 0;", result.answer)
        forged = thaw(actual.values)
        forged["edit_history"][0]["evaluation_status"] = "RECOMPUTED"
        with self.assertRaises(HCLFailure):
            AnswerAssembler()._claim(replace(actual, values=forged))
