"""Ordinary HCL entry executes real shared perspectives and interaction models."""

from copy import deepcopy
from dataclasses import replace
import json
import math
import unittest

from hcl import HCL, ExecutionIssue
from hcl.kernel.types import Issue, thaw, HCLFailure
from hcl.models.gateway import ModelGateway, OfflineModelPort
from hcl.runtime.answer import AnswerAssembler
from tests import test_unified_s3_scene as scene_fixtures
from tests import test_unified_s3_interaction_math as math_fixtures


class InteractionExecutionTests(unittest.TestCase):
    def setUp(self):
        self.scene = scene_fixtures.SceneExecutionTests()
        self.scene.setUp()
        self.store, self.owner = self.scene.store, self.scene.owner
        self.request = self.scene.request(
            issue=ExecutionIssue(
                "root", goals=(Issue("interact", "interaction.evaluate"),)
            ),
            budget=replace(
                self.scene.budget,
                max_local_evaluations=4096,
                max_output_bytes=1048576,
                max_request_bytes=1048576,
                max_total_output_bytes=16777216,
                max_context_tokens=1048576,
                max_visible_output_tokens=1048576,
            ),
        )

    def tearDown(self):
        self.scene.tearDown()

    def candidate(self):
        mental = self.scene.candidate(self.request)["models"][0]
        refs = mental["variables"][0]["segment_ids"]
        typed = math_fixtures.MessageGameTests.plan()
        graph = dict(
            states=list(typed.states),
            terminal=list(typed.terminal),
            utilities=dict(typed.utilities),
            horizon=1,
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
        mental["events"] = []
        mental["variables"][0]["initial"] = False
        mental["variables"][0]["observed_by"] = []
        mental["active_assumptions"] = list(mental["assumptions"])
        mental["plans"] = [
            dict(
                id="listener-plan",
                actor="b",
                at=1,
                graph=graph,
                bindings=[
                    dict(state="r", when={"op": "atom", "name": "open"}),
                    dict(
                        state="b",
                        when={"op": "not", "arg": {"op": "atom", "name": "open"}},
                    ),
                ],
                weights={"r": "1/2", "b": "1/2"},
                policy=None,
                segment_ids=refs,
            )
        ]
        prior = {
            state: "1/2" if state in ("r", "b") else "0" for state in graph["states"]
        }
        game = dict(
            id="signal",
            at=1,
            speaker="a",
            listener="b",
            plan_id="listener-plan",
            messages=[
                dict(id="R", meaning=["r"], cost="1", segment_ids=refs),
                dict(id="B", meaning=["b"], cost="0", segment_ids=refs),
                dict(id="V", meaning=["r", "b"], cost="0", segment_ids=refs),
            ],
            prior=prior,
            speaker_prior=prior,
            beta="1",
            listener_beta="1",
            depth=1,
            goal="IDENTIFY",
            utilities={},
            sincere=True,
            segment_ids=refs,
        )
        return dict(
            schema="hcl-interaction-candidates-1",
            models=[
                dict(
                    mental=mental,
                    utterances=[],
                    acts=[],
                    commitments=[],
                    games=[game],
                    through=6,
                    max_ack_depth=4,
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

    def acknowledgment_candidate(self):
        candidate = self.candidate()
        row = candidate["models"][0]
        mental = row["mental"]
        refs = mental["variables"][0]["segment_ids"]
        row["games"], mental["plans"] = [], []
        mental["queries"] = [
            dict(
                id="early", at=0, formula=dict(op="atom", name="open"), segment_ids=refs
            )
        ]
        for identity, at, speaker, recipient, kind, parent in (
            ("offer", 1, "a", "b", None, None),
            ("meaning", 2, "b", "a", "INTERPRET", "offer"),
            ("ack", 3, "a", "b", "ACK", "meaning"),
        ):
            event = dict(
                id=identity + "-receipt",
                at=at,
                kind="message",
                effects={"open": True},
                seen_by=[],
                received_by=[recipient],
                understood_by=[recipient],
                trusted_by=[],
                assumptions=["ack-receipt-assumption"] if identity == "ack" else [],
                segment_ids=refs,
            )
            mental["events"].append(event)
            row["utterances"].append(
                dict(
                    id=identity,
                    at=at,
                    speaker=speaker,
                    audience=[recipient],
                    version="v1",
                    literal={"open": True},
                    segment_ids=refs,
                    deliveries=[
                        dict(
                            event_id=event["id"],
                            segment_ids=refs,
                            readings=[
                                dict(
                                    actor=recipient,
                                    contents=[{"open": True}],
                                    versions=["v1"],
                                    segment_ids=refs,
                                )
                            ],
                        )
                    ],
                )
            )
            if kind:
                row["acts"].append(
                    dict(
                        id=identity,
                        at=at,
                        actor=speaker,
                        audience=[recipient],
                        kind=kind,
                        refers_to=parent,
                        version="v1",
                        segment_ids=refs,
                    )
                )
        mental["active_assumptions"].append("ack-receipt-assumption")
        return candidate

    def test_ack_receipts_require_actual_m03_time_and_active_environment(self):
        import asyncio
        from hcl.memory.store import StateStore

        for active in (False, True):
            for streamed in (False, True):
                with self.subTest(active=active, streamed=streamed):
                    candidate = self.acknowledgment_candidate()
                    if not active:
                        candidate["models"][0]["mental"]["active_assumptions"].remove(
                            "ack-receipt-assumption"
                        )
                    request = replace(
                        self.request, request_id="ack-" + str((active, streamed))
                    )
                    port = OfflineModelPort(json.dumps(candidate))
                    client = HCL(
                        self.store,
                        principal=self.owner,
                        gateway=ModelGateway(self.store, port),
                    )

                    async def collect():
                        return [event async for event in client.stream(request)]

                    result = (
                        asyncio.run(collect())[-1].result
                        if streamed
                        else client.run_sync(request)
                    )
                    self.assertEqual(
                        result.status,
                        "COMPLETED" if active else "PARTIAL",
                        result.diagnostics,
                    )
                    actual = self.actual(result)
                    model = actual.values["models"][0]
                    events = model["actual_mental"]["values"]["models"][0]["events"]
                    self.assertEqual(len(events), 3 if active else 2)
                    if active:
                        chain = model["acknowledgments"]["chains"][-1]
                        self.assertEqual(chain["participants"], ("a", "b"))
                        self.assertTrue(chain["complete"])
                        self.assertIn(
                            "ack-receipt-assumption", chain["assumption_environments"]
                        )
                        first = model["acknowledgments"]["chains"][0]
                        self.assertNotIn(
                            "ack-receipt-assumption", first["assumption_environments"]
                        )
                        self.assertTrue(
                            all(
                                e["result_id"] == model["actual_mental"]["result_id"]
                                for e in chain["evidence"]
                            )
                        )
                        self.assertIn("ack-receipt-assumption", result.answer)
                        bad = thaw(actual.values)
                        bad["models"][0]["acknowledgments"]["chains"][-1][
                            "assumption_environments"
                        ] = []
                        with self.assertRaises(HCLFailure):
                            AnswerAssembler()._claim(replace(actual, values=bad))
                    else:
                        self.assertFalse(model["acknowledgments"])
                        self.assertIn("EVENT_ASSUMPTION_RETRACTED", result.answer)
                    path = self.store.path
                    self.store.close()
                    self.store = StateStore.sqlite(path, revision=True)
                    self.scene.store = self.store
                    port = OfflineModelPort("NO_NEW_SEND")
                    replay = HCL(
                        self.store,
                        principal=self.owner,
                        gateway=ModelGateway(self.store, port),
                    ).run_sync(request)
                    self.assertEqual(
                        (replay.status, replay.answer, replay.claim_records),
                        (result.status, result.answer, result.claim_records),
                    )
                    self.assertEqual(port.attempts, 0)

    def test_ack_fixed_participants_and_root_content_cannot_be_switched(self):
        for change in ("participant", "content"):
            candidate = self.acknowledgment_candidate()
            row = candidate["models"][0]
            mental = row["mental"]
            if change == "participant":
                third = deepcopy(mental["agents"][0])
                third["id"] = "c"
                mental["agents"].append(third)
                row["utterances"][1]["audience"] = ["a", "c"]
                row["acts"][0]["audience"] = ["a", "c"]
                mental["events"][1]["received_by"] = ["c"]
                mental["events"][1]["understood_by"] = ["c"]
                row["utterances"][1]["deliveries"][0]["readings"][0]["actor"] = "c"
                row["utterances"][2]["speaker"] = "c"
                row["acts"][1]["actor"] = "c"
                diagnostic = "ACKNOWLEDGMENT_PARTICIPANT_CHANGED"
            else:
                for index in (1, 2):
                    row["utterances"][index]["literal"] = {"open": False}
                    row["utterances"][index]["deliveries"][0]["readings"][0][
                        "contents"
                    ] = [{"open": False}]
                    mental["events"][index]["effects"] = {"open": False}
                diagnostic = "ACKNOWLEDGMENT_ROOT_CONTENT_MISMATCH"
            result, _ = self.run_candidate(
                candidate, replace(self.request, request_id="ack-change-" + change)
            )
            self.assertEqual(result.status, "COMPLETED", result.diagnostics)
            ack = self.actual(result).values["models"][0]["acknowledgments"]
            self.assertFalse(any(c["complete"] for c in ack["chains"]))
            self.assertIn(diagnostic, str(ack["diagnostics"]))
            self.assertIn(diagnostic, result.answer)

    def test_real_entry_consumes_recursive_listener_and_m05_action_values(self):
        result, port = self.run_candidate()
        self.assertEqual(result.status, "COMPLETED", result.diagnostics)
        self.assertEqual(port.attempts, 1)
        model = self.actual(result).values["models"][0]
        game = model["games"][0]
        predicted = game["computation"]["expected_listener"]["predictions"]["V"]
        expected = 1 / (1 + math.exp(-0.5))
        self.assertAlmostEqual(predicted["posterior"]["r"], expected, places=14)
        self.assertAlmostEqual(
            predicted["actions"]["q"]["cross"], 3 * (2 * expected - 1), places=14
        )
        self.assertEqual(predicted["actions"]["best_actions"], ("cross",))
        self.assertIn("expected_listener after V", result.answer)
        self.assertIn("actual one-step Q", result.answer)
        fields = [
            f for f in result.claim_records[0].used_result_fields if f.field == "models"
        ]
        self.assertEqual(
            fields[0].value["games"][0]["computation"], game["computation"]
        )

    def test_ambiguous_interpretation_flows_through_real_m03_and_final_claim(self):
        candidate = self.candidate()
        row = candidate["models"][0]
        mental = row["mental"]
        row["games"] = []
        refs = mental["variables"][0]["segment_ids"]
        question_refs = mental["queries"][0]["segment_ids"]
        mental["variables"][0].update(initial=True, observed_by=["a", "b"])
        mental["queries"] = [
            dict(
                id="ambiguous-recipient",
                at=2,
                formula=dict(
                    op="believes", agent="b", arg=dict(op="atom", name="open")
                ),
                segment_ids=question_refs,
            )
        ]
        mental["events"] = [
            dict(
                id="delivery",
                at=1,
                kind="message",
                effects={"open": True},
                seen_by=[],
                received_by=["b"],
                understood_by=["b"],
                trusted_by=["b"],
                assumptions=[],
                segment_ids=refs,
            )
        ]
        row["utterances"] = [
            dict(
                id="message",
                at=1,
                speaker="a",
                audience=["b"],
                version="v1",
                literal={"open": True},
                segment_ids=refs,
                deliveries=[
                    dict(
                        event_id="delivery",
                        segment_ids=refs,
                        readings=[
                            dict(
                                actor="b",
                                contents=[{"open": True}, {"open": False}],
                                versions=["v1", "v2"],
                                segment_ids=refs,
                            )
                        ],
                    )
                ],
            )
        ]
        result, _ = self.run_candidate(candidate)
        self.assertEqual(result.status, "COMPLETED", result.diagnostics)
        actual = self.actual(result)
        beliefs = actual.values["models"][0]["actual_mental"]["values"]["models"][0][
            "beliefs"
        ]
        self.assertEqual(beliefs[0]["possible_values"], (False,))
        self.assertIn("ambiguous-recipient", result.answer)
        self.assertIn("possible=(False,)", result.answer)
        self.assertIn("ambiguous-recipient", str(result.claim_records))

    def test_later_event_assumptions_do_not_backfill_earlier_commitment_facts(self):
        candidate = self.commitment_candidate()
        mental = candidate["models"][0]["mental"]
        refs = mental["variables"][0]["segment_ids"]
        mental["active_assumptions"].append("late-event-assumption")
        mental["events"].append(
            dict(
                id="late",
                at=4,
                kind="change",
                effects={"done": True},
                seen_by=["a", "b"],
                received_by=[],
                understood_by=[],
                trusted_by=[],
                assumptions=["late-event-assumption"],
                segment_ids=refs,
            )
        )
        result, _ = self.run_candidate(candidate)
        self.assertEqual(result.status, "COMPLETED", result.diagnostics)
        actual = self.actual(result)
        c = actual.values["models"][0]["commitments"][0]
        for fact in c["facts"]:
            self.assertEqual(
                "late-event-assumption" in fact["assumption_environments"],
                fact["at"] >= 4,
            )
        for history in c["history"]:
            self.assertEqual(
                "late-event-assumption" in history["assumption_environments"],
                history["at"] >= 4,
            )
        self.assertIn("late-event-assumption", str(result.claim_records))
        bad = thaw(actual.values)
        bad["models"][0]["commitments"][0]["facts"][0][
            "assumption_environments"
        ].append("late-event-assumption")
        with self.assertRaises(HCLFailure):
            AnswerAssembler()._claim(replace(actual, values=bad))

    def test_missing_prior_stays_partial_without_hidden_uniform(self):
        candidate = self.candidate()
        candidate["models"][0]["games"][0]["prior"] = None
        result, _ = self.run_candidate(candidate)
        self.assertEqual(result.status, "PARTIAL", result.diagnostics)
        computed = self.actual(result).values["models"][0]["games"][0]["computation"]
        self.assertFalse(computed["actual_listener"]["predictions"])
        self.assertIn("PRIOR_UNSPECIFIED", result.answer)

    def commitment_candidate(self):
        candidate = self.candidate()
        row = candidate["models"][0]
        mental = row["mental"]
        refs = mental["variables"][0]["segment_ids"]
        row["games"] = []
        mental["variables"] += [
            dict(id="done", initial=False, observed_by=["a", "b"], segment_ids=refs),
            dict(
                id="condition", initial=True, observed_by=["a", "b"], segment_ids=refs
            ),
        ]
        for identity, at, speaker, audience, version in (
            ("offer", 1, "a", ["b"], "v1"),
            ("accept", 2, "b", ["a"], "v1"),
        ):
            event_id = identity + "-delivery"
            mental["events"].append(
                dict(
                    id=event_id,
                    at=at,
                    kind="message",
                    effects={},
                    seen_by=[],
                    received_by=audience,
                    understood_by=audience,
                    trusted_by=[],
                    assumptions=[],
                    segment_ids=refs,
                )
            )
            row["utterances"].append(
                dict(
                    id=identity,
                    at=at,
                    speaker=speaker,
                    audience=audience,
                    version=version,
                    literal={},
                    segment_ids=refs,
                    deliveries=[
                        dict(
                            event_id=event_id,
                            segment_ids=refs,
                            readings=[
                                dict(
                                    actor=a,
                                    contents=[{}],
                                    versions=[version],
                                    segment_ids=refs,
                                )
                                for a in audience
                            ],
                        )
                    ],
                )
            )
        row["acts"] = [
            dict(
                id="accept",
                at=2,
                actor="b",
                audience=["a"],
                kind="ACCEPT",
                refers_to="offer",
                version="v1",
                segment_ids=refs,
            )
        ]
        row["commitments"] = [
            dict(
                id="promise",
                offer_id="offer",
                speaker="a",
                recipient="b",
                version="v1",
                condition={"op": "atom", "name": "condition"},
                outcome={"op": "atom", "name": "done"},
                deadline=5,
                requires_acceptance=True,
                acceptance="RECEIVED_BY_OFFEROR",
                activation="LATCHED",
                withdrawal="RECEIVED_RELEASE",
                segment_ids=refs,
            )
        ]
        return candidate

    def test_actual_m03_condition_and_outcome_drive_commitment_not_report_label(self):
        first, _ = self.run_candidate(self.commitment_candidate())
        self.assertEqual(first.status, "COMPLETED", first.diagnostics)
        c = self.actual(first).values["models"][0]["commitments"][0]
        self.assertEqual(c["status"], "BREACHED")
        self.assertTrue(
            c["facts"][-1]["result_refs"]["outcome"]["query_id"].startswith(
                "interaction:"
            )
        )
        candidate = self.commitment_candidate()
        mental = candidate["models"][0]["mental"]
        mental["events"].append(
            dict(
                id="performance",
                at=4,
                kind="change",
                effects={"done": True},
                seen_by=["a", "b"],
                received_by=[],
                understood_by=[],
                trusted_by=[],
                assumptions=[],
                segment_ids=mental["variables"][0]["segment_ids"],
            )
        )
        second, _ = self.run_candidate(
            candidate, replace(self.request, request_id="fulfilled")
        )
        self.assertEqual(second.status, "COMPLETED", second.diagnostics)
        self.assertEqual(
            self.actual(second).values["models"][0]["commitments"][0]["status"],
            "FULFILLED",
        )
        self.assertIn("FULFILLED", second.answer)

    def strategic_candidate(self, private_listener=False, late_listener=False):
        candidate = self.candidate()
        row = candidate["models"][0]
        mental = row["mental"]
        mental["variables"][0]["observed_by"] = ["a"]
        game = row["games"][0]
        game["goal"] = "ACTION"
        game["speaker_prior"] = None
        game["utilities"] = {
            state: {
                action["id"]: "2" if action["id"] == "cross" else "0"
                for action in mental["plans"][0]["graph"]["actions"]
            }
            for state in mental["plans"][0]["graph"]["states"]
        }
        if private_listener:
            # The separate original M05 plan must use its exact current support.
            # This listener-local weight does not become the speaker's prior.
            mental["plans"][0]["weights"] = {"b": "1"}
        if private_listener or late_listener:
            mental["events"].append(
                dict(
                    id="private-listener-observation",
                    at=2 if late_listener else 1,
                    kind="change",
                    effects={"open": False},
                    seen_by=["b"],
                    received_by=[],
                    understood_by=[],
                    trusted_by=[],
                    assumptions=[],
                    segment_ids=mental["variables"][0]["segment_ids"],
                )
            )
        return candidate

    def test_actual_listener_private_update_does_not_replace_speaker_expected_view(
        self,
    ):
        baseline, _ = self.run_candidate(self.strategic_candidate())
        changed, _ = self.run_candidate(
            self.strategic_candidate(private_listener=True),
            replace(self.request, request_id="private-listener"),
        )
        late, _ = self.run_candidate(
            self.strategic_candidate(late_listener=True),
            replace(self.request, request_id="late-listener"),
        )
        for result in (baseline, changed, late):
            self.assertEqual(result.status, "COMPLETED", result.diagnostics)
        before = self.actual(baseline).values["models"][0]["games"][0]["computation"]
        after = self.actual(changed).values["models"][0]["games"][0]["computation"]
        later = self.actual(late).values["models"][0]["games"][0]["computation"]
        self.assertEqual(before["speaker"], after["speaker"])
        self.assertEqual(before["expected_listener"], after["expected_listener"])
        self.assertNotEqual(before["actual_listener"], after["actual_listener"])
        self.assertEqual(before, later)
        self.assertEqual(after["speaker"]["best_messages"], ("V",))
        self.assertEqual(
            after["actual_listener"]["predictions"]["V"]["actions"]["best_actions"],
            ("wait",),
        )
        condition = next(
            c for c in after["message_conditions"] if c["message_id"] == "V"
        )
        self.assertEqual(condition["actual_literal_values"], (True,))
        self.assertEqual(condition["speaker_literal_values"], (True,))
        self.assertIn("not establish actual intent", changed.answer)

    def test_material_source_anchor_and_no_proposed_scores(self):
        candidate = self.commitment_candidate()
        candidate["models"][0]["utterances"][0]["segment_ids"] = candidate["models"][0][
            "mental"
        ]["queries"][0]["segment_ids"]
        first, _ = self.run_candidate(candidate)
        self.assertEqual(first.status, "INVALID_REQUEST")
        candidate = self.candidate()
        candidate["models"][0]["games"][0]["posterior"] = {"r": 1}
        second, _ = self.run_candidate(
            candidate, replace(self.request, request_id="injected-score")
        )
        self.assertEqual(second.status, "INVALID_REQUEST")
        self.assertFalse(first.claim_records or second.claim_records)

    def test_exhausted_local_budget_preserves_frontier_without_strategy_values(self):
        request = replace(
            self.request, budget=replace(self.request.budget, max_local_evaluations=0)
        )
        result, _ = self.run_candidate(self.candidate(), request)
        self.assertEqual(result.status, "BUDGET_EXHAUSTED", result.diagnostics)
        self.assertEqual(result.usage["local_evaluations"], 0)
        self.assertFalse(result.claim_records)
        request = replace(
            request,
            request_id="one-local-step",
            budget=replace(request.budget, max_local_evaluations=1),
        )
        limited, _ = self.run_candidate(self.candidate(), request)
        self.assertEqual(limited.status, "PARTIAL", limited.diagnostics)
        self.assertEqual(limited.usage["local_evaluations"], 1)
        model = self.actual(limited).values["models"][0]
        self.assertTrue(model["frontier"])
        self.assertFalse(any(game["computation"] for game in model["games"]))
        self.assertIn("FRONTIER", limited.answer)

    def test_stream_reopen_and_explicit_checkpoint_recovery_never_resend(self):
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
            with self.subTest(seam=seam):
                request = replace(
                    self.request,
                    request_id=seam,
                    issue=ExecutionIssue(
                        "root", goals=(Issue(seam, "interaction.evaluate"),)
                    ),
                )
                port = OfflineModelPort(json.dumps(self.candidate()))
                client = HCL(
                    self.store,
                    principal=self.owner,
                    gateway=ModelGateway(self.store, port),
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
                self.assertTrue(hit)
                self.assertEqual(port.attempts, 1)
                old_owner = self.store.owner_id
                path = self.store.path
                self.store.close()
                self.store = StateStore.sqlite(path, revision=True)
                self.scene.store = self.store
                RecoveryManager(self.store).resume_execution(
                    request, expected_owner_id=old_owner
                )
                port = OfflineModelPort("NO_NEW_SEND")
                client = HCL(
                    self.store,
                    principal=self.owner,
                    gateway=ModelGateway(self.store, port),
                )

                async def collect():
                    return [event async for event in client.stream(request)]

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

    def test_tampered_strategy_and_lifecycle_fail_actual_consumption(self):
        for kind in ("game", "commitment"):
            result, _ = self.run_candidate(
                self.candidate() if kind == "game" else self.commitment_candidate(),
                replace(self.request, request_id=kind),
            )
            self.assertEqual(result.status, "COMPLETED", result.diagnostics)
            actual = self.actual(result)
            bad = thaw(actual.values)
            if kind == "game":
                bad["models"][0]["games"][0]["computation"]["expected_listener"][
                    "predictions"
                ]["V"]["posterior"]["r"] = 1.0
            else:
                bad["models"][0]["commitments"][0]["status"] = "FULFILLED"
            with self.assertRaises(HCLFailure):
                AnswerAssembler()._claim(replace(actual, values=bad))


if __name__ == "__main__":
    unittest.main()
