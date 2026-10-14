"""Provider-free persisted CHOICE replacement and independently replayed evidence."""
from copy import deepcopy
from dataclasses import replace
import json
import unittest
from unittest.mock import patch

from hcl.kernel.types import HCLFailure, Issue, thaw
from hcl.memory import codec
from hcl.operators.concept_judgment import ConceptJudgmentOperator, decision_key
from hcl.operators.persistent_concepts import (
    compute_persistent, verify_persistent, verify_persistent_inference, digest,
)
from hcl.semantics.judgment_concept_compiler import ConceptJudgmentCompiler
from hcl.semantics.segments import segment_snapshot
from scripts.witness_unified_concept_judgment import propose, SCENE, PRINCIPLES
from tests import test_unified_s4_judgment as judgment_fixture


class PersistentConceptSolverTests(unittest.TestCase):
    def setUp(self):
        self.f = judgment_fixture.JudgmentExecutionTests()
        self.f.setUp()
        self.addCleanup(self.f.tearDown)
        self.handles = (
            self.f.store.put_source("s", self.f.owner, "scene", SCENE),
            self.f.store.put_source("s", self.f.owner, "principles", PRINCIPLES))
        self.snapshot = self.f.store.snapshot("s", self.f.owner, self.handles)
        self.allowance = self.f.request.budget
        self.key = decision_key("scene", "notice", "notification")

    def compile(self, candidate, snapshot=None, issue_id="original"):
        snapshot = snapshot or self.snapshot
        issue = Issue(issue_id, "judgment.evaluate")
        compiled = ConceptJudgmentCompiler().compile(snapshot, segment_snapshot(snapshot, self.f.request.question),
            json.dumps(candidate, ensure_ascii=False), self.allowance)
        return ConceptJudgmentOperator().run(snapshot, issue, self.allowance, compiled).candidate_delta.new_inferences[0]

    def candidate(self, *, original_only=False):
        candidate = propose(self.snapshot, self.f.request.question)
        if original_only:
            candidate["concepts"]["choices"][0]["versions"] = ["original"]
        return candidate

    def selection(self, proof, version="revised", choice="meaning", adoption="adoption-1"):
        definition = next(v for v in proof.values["concepts"]["definitions"] if v["id"] == version)
        return dict(choice_id=choice, stream_id="approved-same-host-reading", adoption_id=adoption,
            definition_version=definition["definition_version"], version_label=version, proof=codec.encode(proof))

    def compute(self, base, selections, *, snapshot=None, previous=None, allowance=None):
        return compute_persistent(snapshot or self.snapshot, Issue("successor", "judgment.evaluate"),
            allowance or self.allowance, base, tuple(selections), previous_result=previous).candidate_delta.new_inferences[0]

    def test_real_new_classification_recommendation_and_byte_identical_pins(self):
        base = self.compile(self.candidate(original_only=True))
        proof = self.compile(self.candidate(), issue_id="adopt-definition")
        before = codec.dumps(base)
        result = self.compute(base, [self.selection(proof)])
        value = thaw(result.values)
        old = thaw(base.values["branches"][0])
        new = value["branches"][0]
        self.assertTrue(value["complete"])
        self.assertEqual(old["decision_projection"][self.key]["recommended"], ["ignore"])
        self.assertEqual(new["decision_projection"][self.key]["recommended"], ["protect"])
        self.assertEqual(new["classifications"]["current"]["actual"]["status"], "MEMBER")
        self.assertEqual(codec.dumps(new["classifications"]["promise-scope"]), codec.dumps(old["classifications"]["promise-scope"]))
        a, b = old["actual_judgment"]["models"][0], new["actual_judgment"]["models"][0]
        for field in ("cognition", "actual_interaction", "opportunities"):
            self.assertEqual(codec.dumps(a[field]), codec.dumps(b[field]))
        for key in a["facts"]:
            if key != "concept:current":
                self.assertEqual(codec.dumps(a["facts"][key]), codec.dumps(b["facts"][key]))
        self.assertEqual(before, codec.dumps(base))
        self.assertEqual(codec.decode(value["base_result"]), base)
        self.assertTrue(value["semantics_changed"])
        self.assertEqual(value["comparison_basis"], "ORIGINAL_BASE_BUNDLE")
        self.assertGreater(value["local_evaluations"], 100)
        verify_persistent_inference(result)

    def test_execution_reuses_old_fixed_work_and_recomputes_real_argument(self):
        base = self.compile(self.candidate(original_only=True))
        proof = self.compile(self.candidate())
        from hcl.operators.argument_model import ArgumentModelOperator
        from hcl.operators.judgment_model import JudgmentModelOperator
        original = ArgumentModelOperator.run
        calls = []
        def run(*args, **kwargs):
            calls.append(1)
            return original(*args, **kwargs)
        with patch("hcl.operators.judgment_model.compute_shared_cognition", side_effect=AssertionError("old M03 rerun")), \
             patch("hcl.operators.judgment_model.InteractionModelOperator._run", side_effect=AssertionError("old M07 rerun")), \
             patch("hcl.operators.judgment_model.solve_action_values", side_effect=AssertionError("old M05 rerun")), \
             patch("hcl.operators.judgment_model.commitment_condition", side_effect=AssertionError("old fixed fact rerun")), \
             patch.object(ArgumentModelOperator, "run", run):
            result = self.compute(base, [self.selection(proof)])
        self.assertEqual(len(calls), 1)
        self.assertEqual(result.values["reused_fixed_models"], 1)
        self.assertEqual(result.values["robust_recommended"][self.key], ("protect",))

    def test_different_source_handles_keep_entire_original_proof_and_sources(self):
        base = self.compile(self.candidate(original_only=True))
        handles = (
            self.f.store.put_source("s", self.f.owner, "adopt-scene", SCENE),
            self.f.store.put_source("s", self.f.owner, "adopt-principles", PRINCIPLES))
        adopted_snapshot = self.f.store.snapshot("s", self.f.owner, handles)
        original_segments = segment_snapshot(self.snapshot, self.f.request.question)
        adopted_segments = segment_snapshot(adopted_snapshot, self.f.request.question)
        mapping = {"scene": "adopt-scene", "principles": "adopt-principles"}
        for old in original_segments:
            if old.kind == "SOURCE":
                matched = next(new for new in adopted_segments if new.source_id == mapping[old.source_id]
                    and new.start == old.start and new.end == old.end)
                mapping[old.segment_id] = matched.segment_id
        def rename(value):
            if isinstance(value, dict):
                return {k: rename(v) for k, v in value.items()}
            if isinstance(value, list):
                return [rename(v) for v in value]
            return mapping.get(value, value) if isinstance(value, str) else value
        proof = self.compile(rename(self.candidate()), adopted_snapshot, "external-source-definition")
        snapshot = self.f.store.snapshot("s", self.f.owner, (*self.handles, *handles))
        result = self.compute(base, [self.selection(proof)], snapshot=snapshot)
        self.assertEqual(dict(result.values["source_versions"]), dict(snapshot.source_versions))
        self.assertEqual(codec.decode(thaw(result.values["base_result"])), base)
        old = base.values["branches"][0]["actual_judgment"]["models"][0]
        new = result.values["branches"][0]["actual_judgment"]["models"][0]
        self.assertEqual(new["actual_interaction"], old["actual_interaction"])
        self.assertEqual(new["facts"]["concept:promise-scope"], old["facts"]["concept:promise-scope"])
        self.assertEqual(result.values["robust_recommended"][self.key], ("protect",))
        verify_persistent_inference(result)

    def test_incompatible_family_frame_time_signature_and_selected_identity_rejected(self):
        base = self.compile(self.candidate(original_only=True))
        for change in ("family", "future", "signature", "frame"):
            candidate = self.candidate()
            # Remove revised from original uses, so the independent adopted
            # definition is valid even when unsuitable for this base consumer.
            candidate["concepts"]["choices"][0]["versions"] = ["original"]
            revised = candidate["concepts"]["versions"][1]
            if change == "family":
                revised["concept_key"] = "another-family"
            elif change == "future":
                revised["effective_at"] = 3
            elif change == "frame":
                revised["frame_kind"] = "COUNTERFACTUAL"
            else:
                for example in revised["criteria"][0]["positive"]:
                    example["term"]["arguments"].append(deepcopy(example["term"]["arguments"][0]))
            proof = self.compile(candidate, issue_id=change)
            with self.subTest(change=change), self.assertRaises(HCLFailure) as raised:
                self.compute(base, [self.selection(proof)])
            self.assertEqual(raised.exception.diagnostic.code, "PERSISTENT_CONCEPT_NEEDS_RECOMPILE")
        proof = self.compile(self.candidate())
        selection = self.selection(proof)
        selection["definition_version"] = "forged"
        with self.assertRaises(HCLFailure):
            self.compute(base, [selection])

    def test_new_meaning_never_inherits_pairwise_constraint_without_evidence(self):
        candidate = self.candidate()
        concepts = candidate["concepts"]
        concepts["choices"].append(dict(concepts["choices"][0], id="linked"))
        concepts["constraints"] = [dict(left="meaning", right="linked",
            allowed_pairs=[["original", "original"], ["revised", "revised"]],
            segment_ids=concepts["choices"][0]["segment_ids"])]
        base = self.compile(candidate)
        proof_candidate = self.candidate()
        proof_candidate["concepts"]["versions"][1]["purpose"] = "Genuinely new meaning."
        proof = self.compile(proof_candidate)
        with self.assertRaises(HCLFailure) as raised:
            self.compute(base, [self.selection(proof)])
        self.assertEqual(raised.exception.diagnostic.code, "PERSISTENT_CONCEPT_NEEDS_RECOMPILE")
        # Exact already-declared meaning may relabel its explicitly allowed
        # constraint pairs, leaving only the genuinely compatible joint branch.
        proof = self.compile(self.candidate())
        result = self.compute(base, [self.selection(proof)])
        self.assertTrue(result.values["complete"])
        self.assertEqual(len(result.values["branches"]), 1)
        self.assertEqual(result.values["branches"][0]["selections"]["linked"], "revised")
        verify_persistent_inference(result)

    def test_fresh_labels_cannot_capture_existing_pinned_version(self):
        proof = self.compile(self.candidate())
        selection = self.selection(proof)
        label = "adopted:" + digest(["meaning", selection["stream_id"], selection["adoption_id"],
            selection["definition_version"], proof.result_id])[:56]
        candidate = self.candidate(original_only=True)
        original = candidate["concepts"]["versions"][0]
        original["id"] = label
        candidate["concepts"]["choices"][0]["versions"] = [label]
        candidate["concepts"]["uses"][1]["selector"]["id"] = label
        base = self.compile(candidate)
        result = self.compute(base, [selection])
        branch = result.values["branches"][0]
        self.assertNotEqual(branch["selections"]["meaning"], label)
        self.assertEqual(branch["classifications"]["promise-scope"]["version_label"], label)
        self.assertEqual(branch["classifications"]["promise-scope"], base.values["branches"][0]["classifications"]["promise-scope"])
        verify_persistent_inference(result)

    def test_prior_projection_is_bounded_replayed_and_separates_trace_change(self):
        base = self.compile(self.candidate(original_only=True))
        proof = self.compile(self.candidate())
        first = self.compute(base, [self.selection(proof)])
        second = self.compute(base, [self.selection(proof, adoption="adoption-2")], previous=first)
        self.assertFalse(second.values["semantics_changed"])
        self.assertEqual(second.values["comparison_basis"], "PRIOR_PERSISTENT_PROJECTION")
        self.assertTrue(second.values["trace_changed"])
        previous = codec.decode(thaw(second.values["previous_result"]))
        self.assertNotIn("base_result", previous)
        self.assertNotIn("previous_result", previous)
        verify_persistent_inference(second)
        third = self.compute(base, [self.selection(proof, adoption="adoption-3")], previous=second)
        self.assertLess(abs(len(codec.dumps(second)) - len(codec.dumps(third))), 1000)
        verify_persistent_inference(third)
        tampered = thaw(second.values)
        previous["projection"]["semantics"]["complete"] = False
        tampered["previous_result"] = codec.encode(previous)
        with self.assertRaises(ValueError):
            verify_persistent(tampered)

    def test_all_fields_proofs_and_metadata_are_replay_checked(self):
        base = self.compile(self.candidate(original_only=True))
        proof = self.compile(self.candidate())
        result = self.compute(base, [self.selection(proof)])
        verify_persistent_inference(result)
        mutations = [
            lambda v: v.update(complete=False),
            lambda v: v.update(semantics_changed=False),
            lambda v: v["branches"][0]["classifications"]["current"]["actual"].update(status="EXCLUDED"),
            lambda v: v["branches"][0]["decision_projection"][self.key].update(recommended=["ignore"]),
            lambda v: v["branches"][0]["actual_judgment"]["models"][0]["facts"]["concept:promise-scope"]["actual"]["original_commitment"]["terms"].update(version="changed"),
            lambda v: v.update(local_evaluations=0),
        ]
        for mutate in mutations:
            data = thaw(result.values)
            mutate(data)
            with self.assertRaises(ValueError):
                verify_persistent(data)
        for kwargs in (dict(kind="CONDITIONAL_ACTION_JUDGMENT"), dict(result_id="persistent-concept:forged"),
            dict(assumption_environments=()), dict(premise_ids=()), dict(counterevidence_ids=("forged",)),
            dict(rule_version="forged"), dict(coverage="forged")):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                verify_persistent_inference(replace(result, **kwargs))
        wrapped = replace(result, result_id="concept-successor:" + "a" * 64 + ":" + "b" * 64)
        verify_persistent_inference(wrapped)

    def test_bounded_work_never_reports_complete_robust_recommendation(self):
        base = self.compile(self.candidate(original_only=True))
        proof = self.compile(self.candidate())
        for budget in (0, 1, 10, 100):
            with self.subTest(budget=budget):
                result = self.compute(base, [self.selection(proof)], allowance=replace(self.allowance, max_local_evaluations=budget))
                self.assertFalse(result.values["complete"])
                self.assertFalse(result.values["robust_recommended"])
                self.assertLessEqual(result.values["local_evaluations"], budget)
                verify_persistent_inference(result)

    def test_unknown_adopted_reading_does_not_turn_missing_evidence_into_permission(self):
        base = self.compile(self.candidate(original_only=True))
        candidate = self.candidate()
        candidate["concepts"]["versions"][1]["criteria"][0]["direction"] = "TYPICAL"
        proof = self.compile(candidate)
        result = self.compute(base, [self.selection(proof)])
        branch = result.values["branches"][0]
        self.assertEqual(branch["classifications"]["current"]["actual"]["possible_values"], (False, True))
        model = branch["actual_judgment"]["models"][0]
        self.assertIn("concept:current", model["argument_dependency_gaps"]["duty"])
        permission = model["decisions"][0]["frameworks"][0]["branches"][0]["result"]["eligibility"]
        self.assertEqual(next(v for v in permission if v["action_id"] == "ignore")["status"], "PERMISSION_UNRESOLVED")
        verify_persistent_inference(result)

    def test_different_proof_host_and_conflicting_source_versions_need_recompile(self):
        base = self.compile(self.candidate(original_only=True))
        other_host = replace(self.snapshot, session_id="other-host")
        proof = self.compile(self.candidate(), other_host)
        with self.assertRaises(HCLFailure) as raised:
            self.compute(base, [self.selection(proof)])
        self.assertEqual(raised.exception.status, "NEEDS_RECOMPILE")
        changed = self.f.store.put_source("s", self.f.owner, "principles", PRINCIPLES + " Additional evidence.")
        snapshot = self.f.store.snapshot("s", self.f.owner, (self.handles[0], changed))
        candidate = propose(snapshot, self.f.request.question)
        proof = self.compile(candidate, snapshot)
        with self.assertRaises(HCLFailure) as raised:
            self.compute(base, [self.selection(proof)], snapshot=snapshot)
        self.assertEqual(raised.exception.status, "NEEDS_RECOMPILE")
        self.assertEqual(raised.exception.diagnostic.field_path, "conflicting_source_versions")

    def test_original_host_source_and_base_are_never_silently_rewritten(self):
        base = self.compile(self.candidate(original_only=True))
        proof = self.compile(self.candidate())
        other = replace(self.snapshot, session_id="other-session")
        with self.assertRaises(HCLFailure):
            self.compute(base, [self.selection(proof)], snapshot=other)
        incomplete_sources = replace(self.snapshot, source_versions={"scene": self.handles[0].version})
        with self.assertRaises(HCLFailure):
            self.compute(base, [self.selection(proof)], snapshot=incomplete_sources)

    def test_native_persistent_delivery_enforces_same_principal_with_shared_sources(self):
        from hcl.kernel.types import Principal
        from hcl.runtime.execution_ledger import ExecutionLedger
        base = self.compile(self.candidate(original_only=True))
        proof = self.compile(self.candidate())
        op = compute_persistent(self.snapshot, Issue("native-successor", "judgment.evaluate"),
                                self.allowance, base, (self.selection(proof),))
        delta = op.candidate_delta
        self.f.store.commit(delta.base_revision, delta.read_set, delta.access_epoch, delta)
        result = delta.new_inferences[0]
        self.assertTrue(result.result_id.startswith("persistent-concept:"))
        bob = Principal(self.f.owner.tenant_id, "bob")
        shared = self.f.store.snapshot("s", bob, self.handles)
        self.assertEqual(dict(shared.source_versions), dict(self.snapshot.source_versions))
        self.assertEqual(self.f.store.inferences("s", self.f.owner), (result,))
        ledger = ExecutionLedger(self.f.store)
        self.assertEqual(ledger.delivery_inferences(self.f.request, (result.result_id,)), (result,))
        for read in (lambda: self.f.store.inferences("s", bob),
                     lambda: ledger.delivery_inferences(replace(self.f.request, principal=bob), (result.result_id,))):
            with self.subTest(read=read), self.assertRaises(HCLFailure) as caught:
                read()
            self.assertEqual(caught.exception.status, "DENIED")
            self.assertEqual(caught.exception.diagnostic.code, "CONCEPT_RESULT_NAMESPACE_DENIED")


if __name__ == "__main__":
    unittest.main()
