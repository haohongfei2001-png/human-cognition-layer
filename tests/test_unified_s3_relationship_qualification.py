"""Bookkeeping lifecycle labels cannot manufacture relationship evidence."""

import asyncio
from dataclasses import replace
import json
import unittest
from unittest.mock import patch
from hcl import HCL, ExecutionIssue
from hcl.kernel.types import HCLFailure, Issue, thaw
from hcl.memory.store import StateStore
from hcl.models.gateway import ModelGateway, OfflineModelPort
from hcl.runtime.answer import AnswerAssembler
from tests import test_unified_s3_relationship as fixtures


class RelationshipQualificationTests(unittest.TestCase):
    def setUp(self):
        self.f = fixtures.RelationshipExecutionTests()
        self.f.setUp()
        self.addCleanup(self.f.tearDown)
        # The existing material has many nested model/trajectory proofs. Keep all
        # actual delivery limits; explicitly provision this synthetic test task.
        self.f.request = replace(
            self.f.request,
            budget=replace(self.f.request.budget, max_output_bytes=4194304),
        )

    def candidate(self, initial=None, *, history=False):
        c = self.f.relational_candidate()
        m = c["models"][0]
        mental = m["mental"]
        refs = mental["variables"][0]["segment_ids"]
        mental["variables"].append(
            dict(
                id="done",
                initial=False if history else initial,
                observed_by=["a", "b"],
                segment_ids=refs,
            )
        )
        terms = m["interaction"]["commitments"][0]
        terms.update(condition=True, outcome=dict(op="atom", name="done"), deadline=5)
        relation = m["relationships"][0]
        relation["updates"] = relation["updates"][:1]
        relation["updates"][0].update(commitment_status="ACTIVE")
        if history:
            mental["variables"].append(
                dict(
                    id="activation",
                    initial=initial,
                    observed_by=["a", "b"],
                    segment_ids=refs,
                )
            )
            terms["condition"] = dict(op="atom", name="activation")
            next(e for e in mental["events"] if e["id"] == "change-1")["effects"][
                "activation"
            ] = False
        return c

    def test_unknown_fulfillment_and_latched_activation_are_not_established_factors(
        self,
    ):
        for history in (False, True):
            outputs = {}
            for initial in (False, True, None):
                request = replace(self.f.request, request_id=str((history, initial)))
                result, _ = self.f.run_candidate(
                    self.candidate(initial, history=history), request
                )
                self.assertEqual(
                    result.status,
                    "PARTIAL" if initial is None else "COMPLETED",
                    result.diagnostics,
                )
                actual = self.f.actual(result)
                row = actual.values["models"][0]["relationships"][0]["history"][0]
                outputs[initial] = row
                if initial is None:
                    self.assertEqual(row["qualification"], "UNRESOLVED")
                    self.assertEqual(row["update"], "UNRESOLVED_NOT_APPLIED")
                    self.assertEqual(
                        dict(row["weights"]), {"supportive": "1/2", "limited": "1/2"}
                    )
                    proof = row["commitment_qualification"]
                    self.assertTrue(proof["state_completion_complete"])
                    self.assertEqual(proof["possible_values"], (False, True))
                    self.assertEqual(
                        proof["history_reference"]["result_id"],
                        actual.values["models"][0]["actual_interaction"]["result_id"],
                    )
                    self.assertIn("bookkeeping prefix", result.answer)
                    responsive = [
                        v
                        for v in actual.values["models"][0]["forecasts"].values()
                        if any(r["relation_conditions"] for r in v)
                    ]
                    self.assertTrue(responsive)
                    self.assertTrue(all(not r["values"] for v in responsive for r in v))
            self.assertNotEqual(
                outputs[False]["qualification"], outputs[True]["qualification"]
            )

    def test_between_query_times_preserves_actual_current_prefix_in_both_directions(
        self,
    ):
        for initial in (False, True, None):
            for target in ("ACTIVE", "CONDITION_UNRESOLVED"):
                c = self.candidate(initial)
                m = c["models"][0]
                m["mental"]["events"] = [
                    e for e in m["mental"]["events"] if e["id"] != "change-1"
                ]
                m["relationships"][0]["updates"][0].update(
                    at=1,
                    event_id="offer-event",
                    condition=True,
                    commitment_status=target,
                )
                m["interaction"]["commitments"][0]["activation"] = "CURRENT"
                result, _ = self.f.run_candidate(
                    c,
                    replace(self.f.request, request_id="gap-" + str((initial, target))),
                )
                actual = self.f.actual(result).values["models"][0]
                commitment = actual["actual_interaction"]["values"]["models"][0][
                    "commitments"
                ][0]
                self.assertNotIn(1, [fact["at"] for fact in commitment["facts"]])
                row = actual["relationships"][0]["history"][0]
                expected = (
                    "UNRESOLVED"
                    if initial is None and target == "ACTIVE"
                    else (
                        "ESTABLISHED_IN_CONDITIONAL_MODEL"
                        if initial is False and target == "ACTIVE"
                        else "INAPPLICABLE"
                    )
                )
                self.assertEqual(
                    row["qualification"],
                    expected,
                    (initial, target, result.diagnostics),
                )
                self.assertEqual(
                    row["weights"]["supportive"],
                    "1/4" if expected == "ESTABLISHED_IN_CONDITIONAL_MODEL" else "1/2",
                )
                self.assertEqual(
                    result.status,
                    "PARTIAL" if expected == "UNRESOLVED" else "COMPLETED",
                )
                if initial is None:
                    proof = row["commitment_qualification"]
                    self.assertEqual(
                        proof["possible_statuses"], ("ACTIVE", "FULFILLED")
                    )
                    self.assertNotIn("CONDITION_UNRESOLVED", proof["possible_statuses"])

    def test_unresolved_nonreceipt_and_false_conditions_do_not_apply_likelihoods(self):
        for mode in ("not-received", "false-condition"):
            c = self.candidate()
            m = c["models"][0]
            if mode == "not-received":
                next(e for e in m["mental"]["events"] if e["id"] == "change-1")[
                    "seen_by"
                ] = []
            else:
                m["relationships"][0]["updates"][0]["condition"] = False
            result, _ = self.f.run_candidate(
                c, replace(self.f.request, request_id=mode)
            )
            self.assertIn(result.status, ("COMPLETED", "PARTIAL"), result.diagnostics)
            row = self.f.actual(result).values["models"][0]["relationships"][0][
                "history"
            ][0]
            self.assertEqual(row["qualification"], "INAPPLICABLE")
            self.assertEqual(
                dict(row["weights"]), {"supportive": "1/2", "limited": "1/2"}
            )

    def test_budget_frontier_is_not_a_known_zero_effect_or_completed_posterior(self):
        for limit in (1, 2, 4, 8, 16, 32, 48, 64, 96, 128, 192, 256, 512):
            request = replace(
                self.f.request,
                request_id="budget-" + str(limit),
                budget=replace(self.f.request.budget, max_local_evaluations=limit),
            )
            result, _ = self.f.run_candidate(self.candidate(), request)
            self.assertIn(
                result.status, ("PARTIAL", "BUDGET_EXHAUSTED"), result.diagnostics
            )
            if result.status == "BUDGET_EXHAUSTED":
                continue
            actual = self.f.actual(result)
            self.assertLessEqual(actual.values["local_evaluations"], limit)
            for relation in actual.values["models"][0]["relationships"]:
                if relation["relationship_id"] == "reliability":
                    for row in relation["history"]:
                        self.assertNotEqual(
                            row["qualification"], "ESTABLISHED_IN_CONDITIONAL_MODEL"
                        )

    def test_current_proof_and_old_unsafe_factor_cannot_be_consumed_after_tampering(
        self,
    ):
        result, _ = self.f.run_candidate(self.candidate())
        actual = self.f.actual(result)
        for mode in ("known", "completion", "weight", "strip"):
            values = thaw(actual.values)
            row = values["models"][0]["relationships"][0]["history"][0]
            if mode == "known":
                row["commitment_qualification"]["possible_values"] = [True]
            elif mode == "completion":
                row["commitment_qualification"]["explored_completions"] += 1
            elif mode == "weight":
                row["weights"] = {"limited": "3/4", "supportive": "1/4"}
            else:
                row.pop("commitment_qualification")
                row["qualification"] = "ESTABLISHED_IN_CONDITIONAL_MODEL"
                row["update"] = "CONDITIONAL_LIKELIHOOD_APPLIED"
            with self.subTest(mode=mode), self.assertRaises(HCLFailure):
                AnswerAssembler().compact_claim(replace(actual, values=values))

    def test_unknown_returned_computed_and_committed_states_recover_without_resend(
        self,
    ):
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
                self.f.request,
                request_id=seam,
                issue=ExecutionIssue(
                    "root", goals=(Issue(seam, "relationship.evaluate"),)
                ),
            )
            port = OfflineModelPort(json.dumps(self.candidate()))
            client = HCL(
                self.f.store,
                principal=self.f.owner,
                gateway=ModelGateway(self.f.store, port),
            )
            hit = []

            def crash(stage):
                if stage == seam and not hit:
                    hit.append(True)
                    raise Crash()

            with patch.object(self.f.store, "_checkpoint", crash), self.assertRaises(
                Crash
            ):
                client.run_sync(request)
            path, owner = self.f.store.path, self.f.store.owner_id
            self.f.store.close()
            self.f.store = self.f.f.store = self.f.f.fixture.store = (
                self.f.f.fixture.scene.store
            ) = StateStore.sqlite(path, revision=True)
            RecoveryManager(self.f.store).resume_execution(
                request, expected_owner_id=owner
            )
            port = OfflineModelPort("NO_RESEND")
            client = HCL(
                self.f.store,
                principal=self.f.owner,
                gateway=ModelGateway(self.f.store, port),
            )

            async def collect():
                return [e async for e in client.stream(request)]

            if seam == "return_persisted":
                result = client.run_sync(request)
            else:
                with patch.object(
                    LocalModelOperator,
                    "run",
                    side_effect=AssertionError("recomputed accepted effect"),
                ):
                    result = asyncio.run(collect())[-1].result
            self.assertEqual(result.status, "PARTIAL", result.diagnostics)
            self.assertEqual(port.attempts, 0)
            replay = asyncio.run(collect())[-1].result
            self.assertEqual(
                (result.answer, result.claim_records, result.usage),
                (replay.answer, replay.claim_records, replay.usage),
            )
        self.f.store.set_readers("scene", self.f.owner, "story", {"other"})
        denied = client.run_sync(request)
        self.assertEqual(denied.status, "DENIED")
        self.assertFalse(denied.answer or denied.claim_records)
        self.assertEqual(port.attempts, 0)

    def test_original_delivery_bound_still_fails_closed_instead_of_omitting_qualification(
        self,
    ):
        request = replace(
            self.f.request,
            request_id="unknown-None",
            budget=replace(self.f.request.budget, max_output_bytes=1048576),
        )
        result, port = self.f.run_candidate(self.candidate(), request)
        self.assertEqual(result.status, "BUDGET_EXHAUSTED", result.diagnostics)
        self.assertIn("DELIVERY_CAPACITY", {d.code for d in result.diagnostics})
        self.assertFalse(result.answer or result.claim_records)
        self.assertEqual(port.attempts, 1)
        actual = self.f.store.inferences("scene", self.f.owner)[-1]
        factor = actual.values["models"][0]["relationships"][0]["history"][0]
        self.assertEqual(factor["qualification"], "UNRESOLVED")
        self.assertEqual(factor["weights"]["supportive"], "1/2")


class HistoricalRelationshipCertificateTests(unittest.TestCase):
    """Actual pre-fix runtime outputs, without pretending its code is current."""

    baseline = "52c3ba6c54efee2b8196edc3c5360e915d695242"
    code_hash = "c11fe822eee9df604ec02887638f8b7af323489317097a9b4ecf9375bcbcd510"
    file_count = 189

    @classmethod
    def setUpClass(cls):
        from tests import test_unified_s23_upgrade as materializer

        materializer.RuntimeUpgradeTests.setUpClass.__func__(cls)

    @classmethod
    def tearDownClass(cls):
        cls.projection.cleanup()

    def test_actual_old_known_certificates_pass_but_unknown_posterior_and_cache_fail_closed(
        self,
    ):
        from pathlib import Path
        import os, subprocess, sys, tempfile
        from hcl.memory import codec
        from hcl.runtime.engine import Engine
        from hcl.runtime.execution import ExecutionRunner

        root = Path(__file__).resolve().parents[1]
        program = r"""
import json,sys
from pathlib import Path
from dataclasses import replace
from tests.test_unified_s3_relationship import RelationshipExecutionTests
from hcl.memory import codec
from hcl.memory.migrations.control import version_bundle
assert version_bundle()['code_sha256']=='c11fe822eee9df604ec02887638f8b7af323489317097a9b4ecf9375bcbcd510'
f=RelationshipExecutionTests();f.setUp();outputs={}
try:
 for initial in (False,True,None):
  c=f.relational_candidate();m=c['models'][0];refs=m['mental']['variables'][0]['segment_ids']
  m['mental']['variables'].append(dict(id='done',initial=initial,observed_by=['a','b'],segment_ids=refs))
  m['interaction']['commitments'][0].update(condition=True,outcome=dict(op='atom',name='done'),deadline=5)
  relation=m['relationships'][0];relation['updates']=relation['updates'][:1];relation['updates'][0]['commitment_status']='ACTIVE'
  request=replace(f.request,request_id=str(initial),budget=replace(f.request.budget,max_output_bytes=4194304))
  result,_=f.run_candidate(c,request);assert result.status=='COMPLETED',result.diagnostics
  actual=f.actual(result)
  if initial is None:
   h=actual.values['models'][0]['relationships'][0]['history'][0]
   assert h['qualification']=='ESTABLISHED_IN_CONDITIONAL_MODEL' and h['weights']['supportive']=='1/4'
  outputs[str(initial)]={k:codec.dumps(v).decode() for k,v in dict(request=request,result=result,actual=actual).items()}
finally:f.tearDown()
Path(sys.argv[1]).write_text(json.dumps(outputs))
"""
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "historical.json"
            env = dict(
                os.environ,
                PYTHONPATH=str(self.runtime) + os.pathsep + str(root),
                PYTHONDONTWRITEBYTECODE="1",
            )
            subprocess.run(
                [sys.executable, "-B", "-c", program, str(destination)],
                cwd=directory,
                env=env,
                check=True,
                capture_output=True,
                text=True,
                timeout=90,
            )
            original = destination.read_bytes()
            rows = json.loads(original)
            fixture = fixtures.RelationshipExecutionTests()
            fixture.setUp()
            try:
                runner = ExecutionRunner(Engine(fixture.store, fixture.owner))
                for name, data in rows.items():
                    actual = codec.loads(data["actual"].encode())
                    replay = codec.loads(data["result"].encode())
                    request = codec.loads(data["request"].encode())
                    before = codec.dumps(actual)
                    if name == "None":
                        with self.assertRaises(HCLFailure) as caught:
                            AnswerAssembler().compact_claim(actual)
                        self.assertEqual(
                            caught.exception.diagnostic.code,
                            "RELATIONSHIP_RESULT_MISMATCH",
                        )
                        with patch.object(
                            runner.ledger, "delivery_inferences", return_value=(actual,)
                        ), self.assertRaises(HCLFailure) as caught:
                            runner._qualify_replay(request, replay)
                        self.assertEqual(
                            dict(caught.exception.resource_usage), dict(replay.usage)
                        )
                    else:
                        AnswerAssembler().compact_claim(actual)
                        with patch.object(
                            runner.ledger, "delivery_inferences", return_value=(actual,)
                        ):
                            self.assertIs(
                                runner._qualify_replay(request, replay), replay
                            )
                    self.assertEqual(codec.dumps(actual), before)
                self.assertEqual(destination.read_bytes(), original)
            finally:
                fixture.tearDown()
