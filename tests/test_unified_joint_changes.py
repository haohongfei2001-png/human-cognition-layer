"""Ordinary runtime, certificate, budget and isolation contracts for v4 joint edits."""
from copy import deepcopy
from dataclasses import replace
import json
import unittest
from unittest.mock import patch

from hcl import HCL, ExecutionIssue, ConceptAdoptionIssue
from hcl.kernel.types import HCLFailure, Issue, thaw
from hcl.memory import codec
from hcl.models.gateway import ModelGateway, OfflineModelPort
from hcl.operators.joint_changes import JointChangeOperator, verify_joint_changes
from hcl.runtime.answer import AnswerAssembler
from hcl.runtime.execution_ledger import ExecutionLedger
from hcl.runtime.recovery import RecoveryManager
from hcl.semantics.joint_change_compiler import JointChangeCompiler
from hcl.semantics.segments import segment_snapshot
from scripts.witness_unified_joint_changes import propose, SCENE, PRINCIPLES
from tests import test_unified_s4_judgment as runtime


class JointChangeRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.f = runtime.JudgmentExecutionTests(); self.f.setUp(); self.addCleanup(self.f.tearDown)
        scene = self.f.store.put_source("s", self.f.owner, "scene", SCENE)
        principles = self.f.store.put_source("s", self.f.owner, "principles", PRINCIPLES)
        self.f.request = replace(self.f.request, source_handles=(scene, principles),
            budget=replace(self.f.request.budget, max_local_evaluations=300000))

    def candidate(self):
        return propose(self.f.store.snapshot("s", self.f.owner, self.f.request.source_handles), self.f.request.question)

    def run_candidate(self, candidate=None, request=None, *, stream=False):
        result, port = self.f.run_candidate(candidate or self.candidate(), request or self.f.request, stream=stream)
        self.assertEqual(result.status, "PARTIAL", result.diagnostics)
        results = ExecutionLedger(self.f.store).delivery_inferences(request or self.f.request,
            tuple(result.execution_receipt["result_ids"]))
        self.assertEqual(len(results), 1)
        proof = results[0]
        return thaw(proof.values), result, port, proof

    def pure(self, candidate, limit=300000):
        snapshot = self.f.store.snapshot("s", self.f.owner, self.f.request.source_handles)
        budget = replace(self.f.request.budget, max_local_evaluations=limit)
        program = JointChangeCompiler().compile(snapshot, segment_snapshot(snapshot, self.f.request.question), json.dumps(candidate), budget)
        return JointChangeOperator().run(snapshot, Issue("joint", "judgment.evaluate"), budget, program).candidate_delta.new_inferences[0]

    def test_mixed_joint_changes_recompute_actual_m13_m14_and_preserve_facts(self):
        values, result, port, proof = self.run_candidate()
        search = values["joint_search"]
        self.assertTrue(search["complete"])
        self.assertEqual(search["minimum_cardinality"], 2)
        self.assertEqual(len(search["minimum_witnesses"]), 1)
        self.assertEqual(len(values["evaluations"]), 4)
        before, after = values["evaluations"][0], values["evaluations"][-1]
        self.assertEqual(before["target"]["semantics"]["recommended"], ["protect"])
        self.assertEqual(after["target"]["semantics"]["recommended"], ["ignore"])
        for evaluation in values["evaluations"]:
            model = evaluation["actual_judgment"]["models"][0]
            original = before["actual_judgment"]["models"][0]
            for name in ("cognition", "actual_interaction", "opportunities"):
                self.assertEqual(model[name], original[name])
            for fact in ("knowledge", "control", "promise", "concept:promise-scope"):
                self.assertEqual(model["facts"][fact], original["facts"][fact])
            self.assertEqual(evaluation["classifications"]["promise-scope"], before["classifications"]["promise-scope"])
            self.assertEqual(model["actual_argument"]["values"]["models"][0]["source_records"]["rules"][-1]["id"], "independent-care")
        self.assertEqual(port.attempts, 1)
        self.assertEqual(codec.loads(codec.dumps(proof)), proof)
        self.assertTrue(any(f.field == "joint_search" for c in result.claim_records for f in c.used_result_fields))
        self.assertIn("All minimum-cardinality witnesses", result.answer)
        self.assertFalse(search["adoption_authorized"])

    def test_real_m13_target_has_joint_acceptance_not_proof_changes(self):
        data = self.candidate()
        data["joint_changes"]["target"] = dict(kind="M13_ACCEPTANCE", source_id="scene", model_id="notice", argument_id="norms", query_id="duty")
        value = thaw(self.pure(data).values)
        self.assertEqual(value["joint_search"]["minimum_cardinality"], 2)
        semantics = [e["target"]["semantics"] for e in value["evaluations"]]
        self.assertTrue(semantics[0]["positive_accepted"])
        self.assertFalse(semantics[-1]["positive_accepted"])
        self.assertTrue(semantics[-1]["opposed_accepted"])

    def test_unrelated_model_is_reused_without_m13_recomputation(self):
        data = self.candidate()
        from scripts.witness_unified_judgment import propose as base
        other = base(self.f.store.snapshot("s", self.f.owner, self.f.request.source_handles), self.f.request.question)["models"][0]
        other["mental"]["id"] = "unrelated"
        other["argument"]["id"] = "unrelated-norms"
        other["concept_bindings"] = []
        data["models"].append(other)
        value = thaw(self.pure(data).values)
        self.assertTrue(value["complete"])
        self.assertEqual(value["evaluations"][0]["actual_judgment"]["joint_model_computations"], [0, 1])
        untouched = value["evaluations"][0]["actual_judgment"]["models"][1]
        for evaluation in value["evaluations"][1:]:
            self.assertEqual(evaluation["actual_judgment"]["joint_model_computations"], [0])
            self.assertEqual(evaluation["actual_judgment"]["joint_model_reuses"], [1])
            self.assertEqual(evaluation["actual_judgment"]["models"][1], untouched)

    def test_trace_only_rename_is_no_change_but_usability_is_not_assumed_false(self):
        data = self.candidate()
        alias = deepcopy(data["concepts"]["versions"][1]); alias["id"] = "same-meaning"
        data["concepts"]["versions"].append(alias); data["concepts"]["choices"][0]["versions"].append(alias["id"])
        data["joint_changes"]["edits"] = [dict(kind="CHOICE_REPLACE", choice_id="meaning", version_id=alias["id"], segment_ids=alias["segment_ids"])]
        value = thaw(self.pure(data).values)
        self.assertEqual(value["joint_search"]["status"], "NO_EXPRESSIBLE_CHANGE")
        alias["active_assumptions"] = []
        value = thaw(self.pure(data).values)
        self.assertFalse(value["joint_search"]["complete"])
        self.assertEqual(value["joint_search"]["minimum_witnesses"], [])

    def test_duplicate_atoms_noops_and_order_cannot_change_minimum(self):
        data = self.candidate(); first = thaw(self.pure(data).values)
        data["joint_changes"]["edits"].extend(deepcopy(data["joint_changes"]["edits"]))
        data["joint_changes"]["edits"].append(dict(kind="CHOICE_REPLACE", choice_id="meaning", version_id="revised", segment_ids=data["concepts"]["choices"][0]["segment_ids"]))
        data["joint_changes"]["edits"].reverse()
        second = thaw(self.pure(data).values)
        self.assertEqual(first["joint_search"], second["joint_search"])
        self.assertEqual(len(second["program"]["joint_changes"]["atoms"]), 2)
        self.assertEqual(len(second["program"]["joint_changes"]["ignored_edits"]), 1)

    def test_budget_at_generation_legality_reasoning_and_final_compare_withholds_certificate(self):
        data = self.candidate(); full = self.pure(data); used = full.values["local_evaluations"]
        for limit in (0, 1, 100, 1000, 5000, used // 2, used - 1):
            with self.subTest(limit=limit):
                value = self.pure(data, limit).values
                self.assertLessEqual(value["local_evaluations"], limit)
                self.assertFalse(value["complete"])
                self.assertIsNone(value["joint_search"]["minimum_cardinality"])
                self.assertFalse(value["joint_search"]["minimum_witnesses"])
                self.assertNotIn("robust_recommended", value)
                verify_joint_changes(value)
        exact = self.pure(data, used)
        self.assertTrue(exact.values["complete"])

    def test_every_certificate_layer_is_replayed_before_compact_delivery(self):
        values, _, _, proof = self.run_candidate()
        mutations = [
            lambda v: v["joint_search"].update(minimum_cardinality=1),
            lambda v: v["joint_search"].update(minimum_witnesses=[]),
            lambda v: v["joint_search"]["layers"][1].update(generated=0),
            lambda v: v["program"]["joint_changes"]["atoms"][0].update(cost=0),
            lambda v: v["program"]["joint_changes"]["target"].update(model_id="another"),
            lambda v: v["program"]["host_context"].update(session_id="another"),
            lambda v: v["evaluations"][-1]["target"]["semantics"].update(recommended=["protect"]),
            lambda v: v["evaluations"][-1]["actual_judgment"]["models"][0]["facts"]["knowledge"].update(possible_values=[False]),
            lambda v: v["evaluations"][-1]["classifications"]["promise-scope"].update(definition_version="new-terms"),
            lambda v: v["local_model"].update(dialect="judgment-model-3"),
            lambda v: v["source_versions"].update(principles=99),
        ]
        AnswerAssembler().compact_claim(proof)
        for mutate in mutations:
            forged = deepcopy(values); mutate(forged)
            with self.assertRaises(HCLFailure):
                AnswerAssembler().compact_claim(replace(proof, values=forged))
        for forged in (replace(proof, kind="CONDITIONAL_CONCEPT_JUDGMENT"), replace(proof, premise_ids=()), replace(proof, counterevidence_ids=("fake",))):
            with self.assertRaises(HCLFailure):
                AnswerAssembler().compact_claim(forged)

    def test_malformed_forged_source_or_scope_or_prediction_is_rejected(self):
        mutations = [
            lambda d: d["joint_changes"].update(target=[]),
            lambda d: d["joint_changes"].update(edits=[None]),
            lambda d: d["joint_changes"]["baseline"].update(meaning="absent"),
            lambda d: d["joint_changes"]["edits"][1].update(source_id="principles"),
            lambda d: d["joint_changes"]["edits"][1].update(model_id="another"),
            lambda d: d["joint_changes"]["edits"][1].update(argument_id="another"),
            lambda d: d["joint_changes"]["edits"][1].update(item_id="absent"),
            lambda d: d["joint_changes"]["edits"][0].update(segment_ids=d["concepts"]["cases"][0]["segment_ids"]),
            lambda d: d["joint_changes"].update(minimum=1),
            lambda d: d["joint_changes"]["edits"][0].update(cost=0),
            lambda d: d["concepts"]["uses"][1].update(selector=dict(kind="CHOICE", id="meaning")),
        ]
        for index, mutate in enumerate(mutations):
            data = self.candidate(); mutate(data)
            result, _ = self.f.run_candidate(data, replace(self.f.request, request_id="invalid" + str(index)))
            self.assertEqual(result.status, "INVALID_REQUEST", (index, result.diagnostics))
            self.assertFalse(result.answer)

    def test_joint_result_cannot_silently_authorize_concept_only_adoption_or_capsule1(self):
        _, _, _, proof = self.run_candidate()
        before = self.f.store._db.execute("SELECT count(*) FROM inferences WHERE result_id LIKE 'concept-adoption:%' ").fetchone()[0]
        request = replace(self.f.request, request_id="forged-adopt", source_handles=(),
            budget=replace(self.f.request.budget, max_mock_calls=0),
            issue=ExecutionIssue("root", goals=(ConceptAdoptionIssue("adopt", stream_id="policy", support_result_ids=(proof.result_id,), version_labels=("original",)),)))
        result = HCL(self.f.store, principal=self.f.owner).run_sync(request)
        self.assertNotIn(result.status, ("PARTIAL", "COMPLETED"))
        self.assertEqual(self.f.store._db.execute("SELECT count(*) FROM inferences WHERE result_id LIKE 'concept-adoption:%' ").fetchone()[0], before)
        from hcl.operators.concept_proof import pack_proof, unpack_proof, SCHEMA
        self.assertNotEqual(pack_proof(proof).get("schema"), SCHEMA)
        import base64, zlib
        from hashlib import sha256
        body = codec.dumps(proof)
        forged = dict(schema=SCHEMA, uncompressed_bytes=len(body), sha256=sha256(body).hexdigest(), zlib_base64=base64.b64encode(zlib.compress(body, 9)).decode())
        with self.assertRaises(ValueError):
            unpack_proof(forged)

    def test_returned_computed_committed_and_unknown_restore_without_resend(self):
        from hcl.memory.store import StateStore
        from hcl.operators.local_model import LocalModelOperator
        class Crash(BaseException):
            pass
        for seam in ("return_persisted", "execution_computed", "execution_effects_committed", "send_started"):
            request = replace(self.f.request, request_id=seam,
                issue=ExecutionIssue("root", goals=(Issue(seam, "judgment.evaluate"),)))
            candidate = self.candidate(); owner_id = self.f.store.owner_id; fired = False
            def stop(stage):
                nonlocal fired
                if stage == seam and not fired:
                    fired = True; raise Crash()
            with patch.object(self.f.store, "_checkpoint", side_effect=stop), self.assertRaises(Crash):
                self.f.run_candidate(candidate, request)
            self.assertTrue(fired)
            self.f.store.close(); self.f.store = StateStore.sqlite(self.f.path)
            if seam == "send_started":
                with self.assertRaises(HCLFailure):
                    RecoveryManager(self.f.store).resume_execution(request, expected_owner_id=owner_id)
                result, port = self.f.run_candidate(candidate, request)
                self.assertIsNone(result.usage["mock_calls"])
                self.assertEqual(result.usage["held_mock_calls"], 1)
            else:
                RecoveryManager(self.f.store).resume_execution(request, expected_owner_id=owner_id)
                if seam == "return_persisted":
                    result, port = self.f.run_candidate(candidate, request)
                else:
                    with patch.object(LocalModelOperator, "run", side_effect=AssertionError("accepted computation cannot repeat")):
                        result, port = self.f.run_candidate(candidate, request)
                self.assertEqual(result.status, "PARTIAL", result.diagnostics)
            self.assertEqual(port.attempts, 0)

    def test_stream_compat_completed_replay_and_current_acl(self):
        data = self.candidate(); _, first, _, _ = self.run_candidate(data, stream=True)
        data["joint_changes"]["edits"] = []
        replay, port = self.f.run_candidate(data, stream=True)
        self.assertEqual((first.answer, first.claim_records), (replay.answer, replay.claim_records))
        self.assertEqual(port.attempts, 0)
        from hcl.compat.workspace import CognitionWorkspace
        workspace = CognitionWorkspace(self.f.store, principal=self.f.owner, session_id="s",
            gateway=ModelGateway(self.f.store, OfflineModelPort(json.dumps(self.candidate()))))
        import asyncio
        result = asyncio.run(workspace.run(replace(self.f.request, request_id="compat-joint")))
        self.assertEqual(result.status, "PARTIAL", result.diagnostics)
        self.f.store.set_readers("s", self.f.owner, "principles", {"bob"})
        denied = HCL(self.f.store, principal=self.f.owner).run_sync(self.f.request)
        self.assertEqual(denied.status, "DENIED")
        self.assertFalse(denied.answer or denied.claim_records)

    def test_source_change_and_erasure_cannot_deliver_cached_minimum(self):
        _, _, _, proof = self.run_candidate()
        updated = self.f.store.put_source("s", self.f.owner, "principles", "A genuinely different source cannot inherit an old minimum proof.")
        replay = HCL(self.f.store, principal=self.f.owner).run_sync(self.f.request)
        self.assertFalse(replay.answer or replay.claim_records)
        plan = self.f.store.plan_source_erasure("s", self.f.owner, "principles", expected_version=updated.version)
        self.f.store.begin_source_erasure("s", self.f.owner, "principles", expected_version=updated.version, plan_hash=plan["plan_hash"], erasure_id="b" * 32)
        receipt = self.f.store.resume_source_erasure("s", self.f.owner, "b" * 32)
        self.assertTrue(receipt["database_scrubbed"])
        erased = HCL(self.f.store, principal=self.f.owner).run_sync(self.f.request)
        self.assertFalse(erased.answer or erased.claim_records)

    def preferred_only_candidate(self):
        """Five-vertex undercut graph: A->B->C->A, A->D, D<->E."""
        data = self.candidate(); model = data["models"][0]; argument = model["argument"]
        refs = sorted({s for literal in argument["literals"] for s in literal["segment_ids"]})
        data["concepts"]["uses"] = data["concepts"]["uses"][:1]
        model["concept_bindings"] = []; model["fact_bindings"] = []
        argument["assumptions"] = ["norm-reconstruction"]
        argument["active_assumptions"] = ["norm-reconstruction"]
        argument["literals"] = [dict(id=k, atom=k, negative=False, kind="CLAIM", segment_ids=refs) for k in ("seed", "A", "B", "C", "D", "E")]
        argument["premises"] = [dict(id="root", literal="seed", ordinary=False, assumptions=[], segment_ids=refs)]
        argument["rules"] = [dict(id="r" + k, premises=["seed"], conclusion=k, strict=False, assumptions=[], segment_ids=refs) for k in "ABCDE"]
        for left, right in (("A", "B"), ("B", "C"), ("C", "A"), ("A", "D"), ("D", "E"), ("E", "D")):
            key = "u" + left + right
            argument["literals"].append(dict(id=key, atom="r" + right, negative=True, kind="RULE_APPLICABLE", segment_ids=refs))
            argument["rules"].append(dict(id=key, premises=[left], conclusion=key, strict=True, assumptions=[], segment_ids=refs))
        argument["priorities"] = []
        argument["queries"] = [dict(id="queryD", literal="D", preferred=False, critical_candidates=[], segment_ids=refs)]
        decision = model["decisions"][0]; decision["responsibility_queries"] = []
        decision["frameworks"][0]["norms"] = decision["frameworks"][0]["norms"][:1]
        decision["frameworks"][0]["norms"][0]["argument_query_id"] = None
        data["joint_changes"] = dict(baseline={"meaning": "revised"},
            target=dict(kind="M13_ACCEPTANCE", source_id="scene", model_id="notice", argument_id="norms", query_id="queryD"),
            edits=[dict(kind="RULE_RETRACT", source_id="scene", model_id="notice", argument_id="norms", item_id="rA", segment_ids=refs)])
        return data

    def test_m13_target_forces_preferred_and_detects_preferred_only_change(self):
        # Independent complete-labelling enumeration over the small abstract
        # graph confirms a change invisible to support and grounded acceptance.
        from tests.test_unified_joint_change_oracle import complete_labellings
        vertices = set("ABCDE")
        edges = {("A", "B"), ("B", "C"), ("C", "A"), ("A", "D"), ("D", "E"), ("E", "D")}
        grounded, preferred = complete_labellings(vertices, edges)
        self.assertEqual(grounded, set()); self.assertEqual(preferred, {frozenset("E")})
        other_grounded, other_preferred = complete_labellings(vertices - {"A"}, {e for e in edges if "A" not in e})
        self.assertEqual(other_grounded, {"B"})
        self.assertEqual(other_preferred, {frozenset("BD"), frozenset("BE")})
        data = self.preferred_only_candidate()
        value = thaw(self.pure(data, 1000000).values)
        self.assertTrue(value["complete"])
        self.assertEqual(value["joint_search"]["minimum_cardinality"], 1)
        before, after = [e["target"]["semantics"] for e in value["evaluations"]]
        for name in ("positive_supported", "opposed_supported", "positive_accepted", "opposed_accepted"):
            self.assertEqual(before[name], after[name])
        self.assertEqual(before["preferred_acceptance"], [[False, False]])
        self.assertEqual(after["preferred_acceptance"], [[False, False], [True, False]])
        self.assertFalse(value["program"]["base_program"]["models"][0]["argument"]["queries"][0]["preferred"])
        self.assertTrue(value["evaluations"][0]["actual_judgment"]["models"][0]["argument_input"]["queries"][0]["preferred"])
        self.assertGreater(value["local_evaluations"], 10000)
        verify_joint_changes(value)
        delivered, result, port, _ = self.run_candidate(data)
        self.assertEqual(delivered["joint_search"]["status"], "FOUND_ALL_MINIMUM")
        self.assertEqual(delivered["joint_search"]["minimum_cardinality"], 1)
        self.assertIn("All minimum-cardinality witnesses", result.answer)
        self.assertNotIn("none changes the target semantics", result.answer)
        self.assertEqual(port.attempts, 1)
        replay = HCL(self.f.store, principal=self.f.owner).run_sync(self.f.request)
        self.assertEqual(replay.answer, result.answer)
        self.assertEqual(port.attempts, 1)
        # The required preferred search is part of the same bounded work count.
        short = self.pure(data, value["local_evaluations"] - 1).values
        self.assertFalse(short["complete"])
        self.assertEqual(short["joint_search"]["status"], "PARTIAL")
        self.assertLessEqual(short["local_evaluations"], value["local_evaluations"] - 1)

    def test_m13_missing_or_bounded_preferred_never_certifies_no_change(self):
        data = self.preferred_only_candidate()
        value = thaw(self.pure(data, 1000000).values)
        from hcl.operators.joint_changes import target_projection
        actual = deepcopy(value["evaluations"][0]["actual_judgment"])
        actual["models"][0]["actual_argument"]["values"]["models"][0]["queries"][0]["preferred"] = None
        self.assertFalse(target_projection(actual, data["joint_changes"]["target"])["resolved"])
        argument = data["models"][0]["argument"]
        for index in range(24):
            key = "unrelated" + str(index); refs = argument["premises"][0]["segment_ids"]
            argument["literals"].append(dict(id=key, atom=key, negative=False, kind="CLAIM", segment_ids=refs))
            argument["premises"].append(dict(id=key, literal=key, ordinary=False, assumptions=[], segment_ids=refs))
        bounded = thaw(self.pure(data, 1000000).values)
        self.assertFalse(bounded["complete"])
        self.assertIsNone(bounded["joint_search"]["minimum_cardinality"])
        self.assertEqual(bounded["joint_search"]["minimum_witnesses"], [])
        self.assertIn("JOINT_CHANGE_TARGET_UNRESOLVED", bounded["joint_search"]["frontier"])
        self.assertTrue(any("PREFERRED_ARGUMENT_BOUND" in a["frontier"] for e in bounded["evaluations"]
            for m in e["actual_judgment"]["models"] for a in m["actual_argument"]["values"]["models"]))
