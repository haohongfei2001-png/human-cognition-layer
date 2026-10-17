"""Formal-entry and adversarial M03→M06→M08→M05 contracts; original finite source."""

from copy import deepcopy
from dataclasses import replace
from itertools import product
from pathlib import Path
import asyncio
import json
import tempfile
import unittest
from unittest.mock import patch

from hcl import HCL
from hcl.kernel.types import HCLFailure, Principal, thaw
from hcl.memory import codec
from hcl.memory.store import StateStore
from hcl.models.gateway import ModelGateway, OfflineModelPort
from hcl.operators.affect_attribution import derive_attributions, attribution_semantics
from hcl.operators.affect_model import verify_affect
from hcl.runtime.answer import AnswerAssembler
from hcl.runtime.recovery import RecoveryManager
from hcl.semantics.affect_compiler import AffectCompiler
from hcl.semantics.segments import segment_snapshot
from scripts import witness_unified_causal_affect as fixture


class CausalAffectTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.store=StateStore.sqlite(Path(self.tmp.name)/"state.sqlite",revision=True)
        self.addCleanup(self.store.close)
        self.owner=Principal("test","owner");self.store.create_session("s",self.owner,{"other"})
        self.request=fixture.request(self.store,self.owner,"s","test")
        self.snapshot=self.store.snapshot("s",self.owner,self.request.source_handles)

    def candidate(self,mode="received"):
        return fixture.candidate(self.snapshot,self.request.question,mode)

    def run_candidate(self,candidate=None,*,name="test",budget=None):
        request=replace(self.request,request_id=name,budget=budget or self.request.budget)
        port=OfflineModelPort(json.dumps(candidate or self.candidate()))
        result=HCL(self.store,principal=self.owner,gateway=ModelGateway(self.store,port)).run_sync(request)
        proofs=[r for r in self.store.inferences("s",self.owner) if r.result_id in result.execution_receipt.get("result_ids",())]
        return result, proofs[-1] if proofs else None, port

    def compile(self,candidate):
        return AffectCompiler().compile(self.snapshot,segment_snapshot(self.snapshot,self.request.question),json.dumps(candidate),self.request.budget)

    def test_received_cause_alone_changes_attribution_hypotheses_and_real_q(self):
        result,proof,port=self.run_candidate()
        self.assertEqual(result.status,"COMPLETED",result.diagnostics);self.assertEqual(port.attempts,1)
        before,after=thaw(proof.values)["models"][0]["episodes"]
        for key in ("goals","mappings","coping"):
            self.assertEqual(before["input"][key],after["input"][key])
        self.assertEqual(before["plan"]["graph"],after["plan"]["graph"])
        for goal in (0,1):
            for dimension in ("appraisal","control","goal_model"):
                self.assertEqual(before["derived"]["profiles"][goal][dimension],after["derived"]["profiles"][goal][dimension])
        a,b=[e["derived"] for e in (before,after)]
        self.assertEqual(a["profiles"][0]["attribution"]["candidates"][0]["possibilities"],["CONTRIBUTES"])
        self.assertEqual(b["profiles"][0]["attribution"]["candidates"][0]["possibilities"],["CAUSE_NOT_ACTUAL"])
        self.assertEqual([h["status"] for h in a["hypotheses"]],["SUPPORTED_CONDITIONAL","REFUTED"])
        self.assertEqual([h["status"] for h in b["hypotheses"]],["REFUTED","SUPPORTED_CONDITIONAL"])
        # Independent arithmetic, not the implementation's solver/priority helper.
        for derived,weights,expected in ((a,(3/4,1/4),"wait"),(b,(1/4,3/4),"cross")):
            row=derived["coping"][0]["branches"][0]
            expected_q={"cross":weights[0]*-5+weights[1]*5,"wait":weights[0]*-1+weights[1]}
            from fractions import Fraction
            self.assertEqual({k:float(Fraction(v)) for k,v in row["computation"]["q"].items()},expected_q)
            self.assertEqual(row["computation"]["best_actions"],[expected])
        changes={r["goal_id"]:r for r in b["reappraisal"]["changes"]}
        self.assertEqual(changes["safety"]["changed_dimensions"],["attribution"])
        self.assertEqual(changes["duty"]["change"],"UNCHANGED")
        for p in b["profiles"]:
            self.assertEqual(p["normative_relevance"],dict(status="NOT_MODELED"))
            self.assertEqual(p["identity_relevance"],dict(status="NOT_MODELED"))

    def test_unreceived_ununderstood_untrusted_late_and_analyst_do_not_update_character(self):
        for mode in ("unreceived","ununderstood","untrusted","late","analyst"):
            with self.subTest(mode=mode):
                result,proof,_=self.run_candidate(self.candidate(mode),name=mode)
                self.assertEqual(result.status,"COMPLETED",result.diagnostics)
                before,after=thaw(proof.values)["models"][0]["episodes"]
                a,b=[e["derived"] for e in (before,after)]
                self.assertEqual(attribution_semantics(a["profiles"][0]["attribution"]),attribution_semantics(b["profiles"][0]["attribution"]))
                self.assertEqual([(h["status"],h["antecedent_results"]) for h in a["hypotheses"]],
                                 [(h["status"],h["antecedent_results"]) for h in b["hypotheses"]])
                self.assertEqual(a["coping"],b["coping"])
                self.assertTrue(all(r["change"]=="UNCHANGED" for r in b["reappraisal"]["changes"]))
                if mode=="analyst":self.assertEqual(b["reappraisal"]["character_reappraisal"],"NOT_ESTABLISHED_ANALYST_ALTERNATIVE")

    def test_late_received_information_changes_only_later_version_not_history_or_other_actor(self):
        candidate=self.candidate("late");model=candidate["models"][0]
        later=deepcopy(model["episodes"][1]);later.update(id="late-version",at=4,plan_id="late-plan",previous_id="updated")
        later["attributions"][0]["at"]=4;model["episodes"].append(later)
        plan=deepcopy(model["mental"]["plans"][1]);plan.update(id="late-plan",at=4);model["mental"]["plans"].append(plan)
        for at in (2,3):
            other=deepcopy(model["episodes"][0]);other.update(id="other-"+str(at),episode_id="other-loss",actor="a",at=at,plan_id="other-plan-"+str(at))
            other["attributions"][0].update(actor="a",at=at);model["episodes"].append(other)
            plan=deepcopy(plan);plan.update(id=other["plan_id"],actor="a",at=at);model["mental"]["plans"].append(plan)
        result,proof,_=self.run_candidate(candidate);self.assertEqual(result.status,"COMPLETED",result.diagnostics)
        eps=thaw(proof.values)["models"][0]["episodes"]
        possibilities=[e["derived"]["profiles"][0]["attribution"]["candidates"][0]["possibilities"] for e in eps]
        self.assertEqual(possibilities,[["CONTRIBUTES"],["CONTRIBUTES"],["CAUSE_NOT_ACTUAL"],["CAUSE_NOT_ACTUAL"],["CAUSE_NOT_ACTUAL"]])

    def test_unknown_inconsistent_multistructure_and_frontier_keep_competing_coping(self):
        for mode in ("unknown","competing","inconsistent","frontier","structure_unavailable","gate_unknown"):
            with self.subTest(mode=mode):
                result,proof,_=self.run_candidate(self.candidate(mode),name=mode)
                self.assertEqual(result.status,"COMPLETED" if mode=="competing" else "PARTIAL",result.diagnostics)
                first=thaw(proof.values)["models"][0]["episodes"][0]
                branches=first["derived"]["coping"][0]["branches"]
                self.assertEqual(len(branches),2)
                self.assertEqual({b["computation"]["best_actions"][0] for b in branches},{"cross","wait"})
                row=first["attribution"]["candidates"][0]
                if mode=="competing":self.assertEqual(row["possibilities"],["CONTRIBUTES","NO_BUT_FOR_DIFFERENCE"])
                else:self.assertIn("UNRESOLVED",row["possibilities"])

    def test_breaking_actual_m06_or_m05_edge_changes_results(self):
        for mode in ("received","disconnected_m06","disconnected_m05"):
            result,proof,_=self.run_candidate(self.candidate(mode),name=mode)
            first=thaw(proof.values)["models"][0]["episodes"][0]["derived"]
            actions={b["computation"]["best_actions"][0] for b in first["coping"][0]["branches"]}
            self.assertEqual(actions,{"wait"} if mode=="received" else {"cross","wait"} if mode=="disconnected_m06" else {"cross"})

    def test_source_revision_and_acl_revoke_previously_completed_delivery(self):
        result,proof,_=self.run_candidate();self.assertEqual(result.status,"COMPLETED")
        self.store.put_source("s",self.owner,"valve",fixture.SOURCE+" A revised source.")
        stale=HCL(self.store,principal=self.owner).run_sync(self.request)
        self.assertNotEqual(stale.status,"COMPLETED");self.assertFalse(stale.answer or stale.claim_records)
        self.store.set_readers("s",self.owner,"valve",{"other"})
        denied=HCL(self.store,principal=self.owner).run_sync(self.request)
        self.assertEqual(denied.status,"DENIED");self.assertFalse(denied.answer or denied.claim_records)

    def test_stream_same_checked_attribution_and_coping(self):
        candidate=self.candidate();port=OfflineModelPort(json.dumps(candidate))
        client=HCL(self.store,principal=self.owner,gateway=ModelGateway(self.store,port))
        async def collect():return [e async for e in client.stream(self.request)]
        events=asyncio.run(collect());result=events[-1].result
        self.assertEqual(result.status,"COMPLETED",result.diagnostics)
        replay=client.run_sync(self.request)
        self.assertEqual((result.answer,result.claim_records),(replay.answer,replay.claim_records));self.assertEqual(port.attempts,1)
        self.assertIn("Character-conditional but-for attribution",result.answer)

    def test_independent_boolean_oracle_over_all_information_projections(self):
        # Independent Python Boolean world enumeration across 16 character views,
        # including inconsistent views. No production causal/attribution helper
        # supplies the expected answers.
        for a,e,loss,gate in product((False,True),repeat=4):
            candidate=self.candidate();model=candidate["models"][0]
            model["episodes"]=model["episodes"][:1]
            model["mental"]["plans"]=model["mental"]["plans"][:1]
            marker=deepcopy(model["mental"]["events"][1]);marker.update(at=0,effects={})
            model["mental"]["events"]=[marker]
            initial=dict(open=not loss,action=a,external=e,theory=gate)
            for variable in model["mental"]["variables"]:variable["initial"]=initial[variable["id"]]
            state="closed" if loss else "open"
            model["mental"]["plans"][0]["weights"]={state:"1"}
            model["episodes"][0].update(previous_weights={state:"1"},current_weights={state:"1"})
            result,proof,_=self.run_candidate(candidate,name="oracle-"+str((a,e,loss,gate)))
            self.assertIsNotNone(proof,result.diagnostics)
            observed={"action":int(a),"external":int(e),"loss":int(loss)}
            expected=set()
            if gate:
                for x,z in product((0,1),repeat=2):
                    if dict(action=x,external=z,loss=int(bool(x or z)))!=observed:continue
                    expected.add("OUTCOME_UNESTABLISHED" if not loss else "CAUSE_NOT_ACTUAL" if not x else "CONTRIBUTES" if not z else "NO_BUT_FOR_DIFFERENCE")
            if not expected:expected={"UNRESOLVED"}
            row=proof.values["models"][0]["episodes"][0]["attribution"]["candidates"][0]
            self.assertEqual(set(row["possibilities"]),expected)

    def test_actual_and_target_tests_are_never_added_to_observations(self):
        _,proof,_=self.run_candidate(self.candidate("competing"))
        row=proof.values["models"][0]["episodes"][0]["attribution"]["candidates"][0]
        for case in row["cases"]:
            self.assertNotIn("external",case["observations"])
            for s in case["structures"]:self.assertNotIn("external",s["computation"]["observations"])
        self.assertEqual(set(row["possibilities"]),{"CONTRIBUTES","NO_BUT_FOR_DIFFERENCE"})

    def test_confounded_same_background_counterfactual_not_observation(self):
        c=self.candidate();m=c["models"][0];causal=m["mental"]["causal"][0]
        causal["model"].update(variables=["action","external","loss"],exogenous=["external"],rules=[
            dict(target="action",expression="external",evidence_text="external"),
            dict(target="loss",expression="action ^ external",evidence_text="external")])
        # At the earlier version B's causal belief action=1,external=0 is
        # inconsistent; expose only action=1 and loss=0 to abduce external=1.
        for ep in m["episodes"]:
            b=ep["attributions"][0];b["observations"].pop("external");b["observations"]["loss"]["positive"]=True;b["outcome_value"]=0
        _,proof,_=self.run_candidate(c)
        first=proof.values["models"][0]["episodes"][0]["attribution"]["candidates"][0]
        t=first["cases"][0]["structures"][0]["computation"]["traces"][0]
        self.assertEqual(t["exogenous"],dict(external=1));self.assertEqual(t["alternative"]["loss"],1)
        self.assertEqual(first["possibilities"],("CONTRIBUTES",))

    def test_irrelevant_world_duplication_never_becomes_probability_or_extra_work(self):
        _,proof,_=self.run_candidate()
        c=self.candidate();c["models"][0]["mental"]["variables"].append(dict(id="irrelevant",initial=None,observed_by=[],segment_ids=c["models"][0]["mental"]["variables"][0]["segment_ids"]))
        _,other,_=self.run_candidate(c,name="irrelevant")
        left,right=[thaw(p.values)["models"][0]["episodes"][0] for p in (proof,other)]
        self.assertEqual(left["attribution"],right["attribution"])
        self.assertEqual(left["derived"]["coping"],right["derived"]["coping"])

    def test_compile_rejects_wrong_actor_time_projection_condition_and_theory_swap(self):
        mutations=[lambda b:b.update(event_id="unknown"),lambda b:b.update(event_id="cause-report"),lambda b:b.update(actor="a"),lambda b:b.update(at=True),lambda b:b.update(at=9),
                   lambda b:b.update(contributor="stranger"),lambda b:b.update(cause_variable="loss"),
                   lambda b:b.update(contrast_value=1),lambda b:b.update(actual_value=True),
                   lambda b:b.update(max_world_evaluations=4097),lambda b:b.update(observations={}),
                   lambda b:b["observations"]["action"].update(atom="hidden"),
                   lambda b:b["structures"][0].update(available_when={}),
                   lambda b:b["structures"][0].update(available_when=dict(theory=1)),
                   lambda b:b["structures"][0].update(causal_id="foreign")]
        for change in mutations:
            c=self.candidate();change(c["models"][0]["episodes"][0]["attributions"][0])
            with self.assertRaises(HCLFailure):self.compile(c)
        for c in (self.candidate(),self.candidate()):
            c["models"][0]["episodes"][1]["attributions"][0]["contributor"]=None
            with self.assertRaises(HCLFailure):self.compile(c)
        c=self.candidate();c["models"][0]["episodes"][0]["mappings"][0]["conditions"][1]["attribution_id"]="missing"
        with self.assertRaises(HCLFailure):self.compile(c)

    def test_v1_and_v2_malformed_condition_container_is_typed_failure(self):
        for version in (1,2):
            for value in (None,[],1):
                c=self.candidate();c["schema"]="hcl-affect-candidates-"+str(version)
                if version==1:
                    for e in c["models"][0]["episodes"]:e.pop("attributions")
                c["models"][0]["episodes"][0]["mappings"][0]["conditions"]=[value]
                with self.assertRaises(HCLFailure):self.compile(c)

    def test_v1_rejects_v2_input_and_dialect_must_match(self):
        c=self.candidate();c["schema"]="hcl-affect-candidates-1"
        with self.assertRaises(HCLFailure):self.compile(c)
        _,proof,_=self.run_candidate()
        bad=thaw(proof.values);bad["local_model"]["dialect"]="affect-model-1"
        with self.assertRaises(HCLFailure):AnswerAssembler()._claim(replace(proof,values=bad))

    def test_independent_consumer_recomputes_every_edge_and_budget_certificate(self):
        _,proof,_=self.run_candidate();original=thaw(proof.values)
        def ep(data):return data["models"][0]["episodes"][0]
        mutations=[lambda d:d.update(local_evaluations=d["local_evaluations"]+1),
                   lambda d:ep(d).update(attribution_allowance=9999),lambda d:ep(d).update(derived_allowance=9999),
                   lambda d:ep(d)["coping_solver_calls"][0].update(allowance=9999),
                   lambda d:ep(d)["attribution"]["candidates"][0].update(contributor="b"),
                   lambda d:ep(d)["attribution"]["candidates"][0].update(target_variable="other"),
                   lambda d:ep(d)["attribution"]["candidates"][0].update(possibilities=["CAUSE_NOT_ACTUAL"]),
                   lambda d:ep(d)["attribution"]["candidates"][0]["cases"][0].update(observations={}),
                   lambda d:ep(d)["attribution"]["candidates"][0]["cases"][0]["structures"][0]["computation"]["traces"][0]["alternative"].update(loss=1),
                   lambda d:ep(d)["derived"]["hypotheses"][0].update(status="REFUTED"),
                   lambda d:ep(d)["derived"]["coping"][0]["branches"][0]["computation"]["q"].update(cross="999")]
        for change in mutations:
            bad=deepcopy(original);change(bad)
            with self.assertRaises(HCLFailure):AnswerAssembler()._claim(replace(proof,values=bad))

    def test_target_identity_is_part_of_reappraisal_semantics(self):
        _,proof,_=self.run_candidate();a=thaw(proof.values)["models"][0]["episodes"][0]["derived"]["profiles"][0]["attribution"]
        b=deepcopy(a);b["candidates"][0]["target_variable"]="different-outcome"
        self.assertNotEqual(attribution_semantics(a),attribution_semantics(b))

    def test_shared_budget_and_per_bridge_bound_do_not_certify_explored_prefix(self):
        c=self.candidate("competing")
        for e in c["models"][0]["episodes"]:e["attributions"][0]["max_world_evaluations"]=6
        result,proof,_=self.run_candidate(c)
        self.assertEqual(result.status,"PARTIAL")
        for e in proof.values["models"][0]["episodes"]:
            self.assertLessEqual(e["attribution"]["world_evaluations"],6)
            self.assertIn("UNRESOLVED",e["attribution"]["candidates"][0]["possibilities"])
        verify_affect(proof.values)
        self.assertLessEqual(proof.values["local_evaluations"],proof.values["local_evaluation_limit"])

    def test_low_global_budget_preserves_uncomputed_rows_without_fabricated_attribution(self):
        for bound in (0,1,7,11,18,25):
            with self.subTest(bound=bound):
                result,proof,_=self.run_candidate(name="bound-"+str(bound),budget=replace(self.request.budget,max_local_evaluations=bound))
                if proof is not None:
                    verify_affect(proof.values)
                    self.assertLessEqual(proof.values["local_evaluations"],bound)
                    for e in proof.values["models"][0]["episodes"]:
                        if e["status"]!="COMPUTED":self.assertNotIn("attribution",e)

    def test_current_durable_completed_returned_unknown_computed_committed_never_resend(self):
        class Crash(BaseException):pass
        for state,seam in (("completed",None),("returned","return_persisted"),("unknown","send_started"),("computed","execution_computed"),("committed","execution_effects_committed")):
            req=replace(self.request,request_id="seam-"+state,issue=fixture.ExecutionIssue("root",goals=(fixture.Issue("affect-"+state,"affect.evaluate"),)));port=OfflineModelPort(json.dumps(self.candidate()));client=HCL(self.store,principal=self.owner,gateway=ModelGateway(self.store,port))
            reached=[]
            def stop(stage):
                if stage==seam:
                    reached.append(stage)
                    raise Crash()
            try:
                with patch.object(self.store,"_checkpoint",stop):result=client.run_sync(req)
            except Crash:pass
            self.assertEqual(reached,[] if seam is None else [seam])
            owner_id=self.store.owner_id
            if state=="unknown":
                with self.assertRaises(HCLFailure):RecoveryManager(self.store).resume_execution(req,expected_owner_id=owner_id)
            elif state!="completed":RecoveryManager(self.store).resume_execution(req,expected_owner_id=owner_id)
            no_send=OfflineModelPort("NO_RESEND")
            resumed=HCL(self.store,principal=self.owner,gateway=ModelGateway(self.store,no_send)).run_sync(req)
            self.assertEqual(no_send.attempts,0)
            if state=="unknown":self.assertFalse(resumed.answer or resumed.claim_records)
            else:self.assertEqual(resumed.status,"COMPLETED",resumed.diagnostics)

    def test_theory_source_chronology_never_backfills_and_receipt_can_unlock_later(self):
        for initially_available in (False, True):
            c=self.candidate();m=c["models"][0]
            m["mental"]["variables"][3]["initial"]=initially_available
            m["mental"]["causal"][0]["model"]["source_event_id"]="cause-report"
            m["mental"]["events"][-1]["effects"]={"theory":True}
            result,proof,_=self.run_candidate(c,name="theory-"+str(initially_available))
            self.assertEqual(result.status,"PARTIAL")
            before,after=proof.values["models"][0]["episodes"]
            self.assertEqual(before["attribution"]["candidates"][0]["possibilities"],("UNRESOLVED",))
            self.assertEqual(after["attribution"]["candidates"][0]["possibilities"],("CONTRIBUTES",))
            self.assertEqual(before["attribution"]["world_evaluations"],0)
            self.assertEqual(before["attribution"]["candidates"][0]["cases"][0]["unavailable_structures"][0]["reason"],"SOURCE_EVENT_NOT_YET_AVAILABLE")

    def test_foreign_structural_source_is_rejected(self):
        c=self.candidate();c["models"][0]["mental"]["causal"][0]["model"]["source_event_id"]="not-a-declared-source-event"
        with self.assertRaises(HCLFailure):self.compile(c)

    def test_event_identity_change_is_analyst_reinterpretation_not_same_appraisal(self):
        c=self.candidate("unreceived");m=c["models"][0]
        other=deepcopy(m["mental"]["events"][1]);other.update(id="different-damage",at=0,effects={})
        m["mental"]["events"].insert(0,other)
        m["episodes"][1]["revision_kind"]="ANALYST_REINTERPRETATION"
        m["episodes"][1]["attributions"][0]["event_id"]="different-damage"
        _,proof,_=self.run_candidate(c)
        after=proof.values["models"][0]["episodes"][1]["derived"]
        safety=next(r for r in after["reappraisal"]["changes"] if r["goal_id"]=="safety")
        self.assertEqual(safety["changed_dimensions"],("attribution",))
        self.assertEqual(after["reappraisal"]["character_reappraisal"],"NOT_ESTABLISHED_ANALYST_ALTERNATIVE")

    def test_correlated_nested_mental_charge_forgery_is_independently_rejected(self):
        _,proof,_=self.run_candidate();bad=thaw(proof.values)
        model=bad["models"][0];charge=model["mental_evaluation_charge"]
        self.assertGreater(charge,0)
        model["mental_evaluation_charge"]=0
        model["actual_mental"]["values"]["batch_evaluations"]=0
        bad["local_evaluation_limit"]-=charge;bad["local_evaluations"]-=charge
        # All downstream recorded remaining allowances still appear consistent.
        with self.assertRaises(HCLFailure):AnswerAssembler()._claim(replace(proof,values=bad))
