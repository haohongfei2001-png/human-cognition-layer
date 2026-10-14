"""Provider-free real concept classification -> argumentation -> action choices."""
from copy import deepcopy
from dataclasses import replace
import unittest
from unittest.mock import patch

from hcl.kernel.types import HCLFailure, thaw
from hcl.runtime.answer import AnswerAssembler
from hcl.operators.concept_judgment import decision_key
from tests import test_unified_s4_judgment as runtime
from scripts.witness_unified_concept_judgment import propose, term, SCENE, PRINCIPLES


class ConceptJudgmentTests(unittest.TestCase):
    def setUp(self):
        self.f = runtime.JudgmentExecutionTests(); self.f.setUp(); self.addCleanup(self.f.tearDown)
        self.f.handle=self.f.store.put_source("s",self.f.owner,"scene",SCENE)
        self.f.norm=self.f.store.put_source("s",self.f.owner,"principles",PRINCIPLES)
        self.f.request=replace(self.f.request,source_handles=(self.f.handle,self.f.norm))

    def candidate(self):
        return propose(self.f.store.snapshot("s", self.f.owner, self.f.request.source_handles), self.f.request.question)

    def run_candidate(self, candidate=None, **kwargs):
        result, port = self.f.run_candidate(candidate or self.candidate(), **kwargs)
        self.assertEqual(result.status, "PARTIAL", result.diagnostics)
        return thaw(self.f.inference().values), result, port

    def test_real_classification_changes_argument_and_action_preserves_promise(self):
        values, result, port = self.run_candidate()
        self.assertTrue(values["complete"])
        self.assertEqual(port.attempts, 1)
        old, new = values["branches"]
        self.assertEqual(old["classifications"]["current"]["actual"]["status"], "EXCLUDED")
        self.assertEqual(new["classifications"]["current"]["actual"]["status"], "MEMBER")
        key = decision_key("scene","notice","notification")
        self.assertEqual(old["decision_projection"][key]["recommended"], ["ignore"])
        self.assertEqual(new["decision_projection"][key]["recommended"], ["protect"])
        self.assertEqual(values["robust_recommended"][key], [])
        before, after = (b["actual_judgment"]["models"][0] for b in (old,new))
        for field in ("cognition", "actual_interaction", "opportunities"):
            self.assertEqual(before[field], after[field])
        self.assertEqual(old["classifications"]["promise-scope"], new["classifications"]["promise-scope"])
        self.assertEqual(before["facts"]["concept:promise-scope"], after["facts"]["concept:promise-scope"])
        self.assertEqual(before["facts"]["knowledge"], after["facts"]["knowledge"])
        self.assertIn("current", values["sensitivity"][0]["changed_classifications"])
        self.assertIn("recommended=('protect',)", result.answer)
        self.assertTrue(any(f.field == "branches" for c in result.claim_records for f in c.used_result_fields))

    def test_v1_still_replays(self):
        result, _ = self.f.run_candidate()
        self.assertEqual(result.status,"PARTIAL",result.diagnostics)
        AnswerAssembler()._claim(self.f.inference())

    def test_unknown_and_typical_cannot_enable_unsafe_permission(self):
        for mode in ("missing", "typical", "withdrawn", "counterexample", "boundary"):
            data=self.candidate();c=data["concepts"]
            c["choices"][0]["versions"]=["revised"]
            if mode=="missing":c["cases"][0]["term"]=None
            elif mode=="typical":c["versions"][1]["criteria"][0]["direction"]="TYPICAL"
            elif mode=="withdrawn":c["versions"][1]["active_assumptions"]=[]
            else:
                example=deepcopy(c["versions"][1]["criteria"][0]["positive"][0])
                example.update(id="challenge",term=deepcopy(c["cases"][0]["term"]))
                c["versions"][1]["criteria"][0]["negative" if mode=="counterexample" else "boundary"]=[example]
            values,result,_=self.run_candidate(data,request=replace(self.f.request,request_id=mode))
            branch=values["branches"][0]
            self.assertEqual(branch["classifications"]["current"]["actual"]["possible_values"],[False,True])
            m=branch["actual_judgment"]["models"][0]
            self.assertIn("concept:current",m["argument_dependency_gaps"]["duty"])
            eligibility=m["decisions"][0]["frameworks"][0]["branches"][0]["result"]["eligibility"]
            self.assertEqual(next(r for r in eligibility if r["action_id"]=="ignore")["status"],"PERMISSION_UNRESOLVED")

    def test_joint_version_constraints_prevent_impossible_marginal_combinations(self):
        data=self.candidate();c=data["concepts"]
        choice=deepcopy(c["choices"][0]);choice["id"]="linked";c["choices"].append(choice)
        use=deepcopy(c["uses"][0]);use.update(id="linked-case",selector=dict(kind="CHOICE",id="linked"));c["uses"].append(use)
        c["constraints"]=[dict(left="meaning",right="linked",allowed_pairs=[["original","original"],["revised","revised"]],segment_ids=choice["segment_ids"])]
        values,_,_=self.run_candidate(data)
        self.assertEqual([b["selections"] for b in values["branches"]],[dict(meaning="original",linked="original"),dict(meaning="revised",linked="revised")])
        self.assertTrue(values["complete"])
        # Both choices must change together: no false single-variable sensitivity.
        self.assertEqual(values["sensitivity"],[])
        c["constraints"].append(dict(left="meaning",right="linked",allowed_pairs=[["original","revised"]],segment_ids=choice["segment_ids"]))
        values,_,_=self.run_candidate(data,request=replace(self.f.request,request_id="empty-joint"))
        self.assertFalse(values["complete"]);self.assertFalse(values["robust_recommended"])

    def test_no_cross_definition_alias_or_namespace_oracle_is_accepted(self):
        mutations=[
            lambda d:d["concepts"].update(namespace="forged"),
            lambda d:d["concepts"]["versions"][0].update(definition_version="forged"),
            lambda d:d["concepts"]["versions"][1].update(effective_at=3),
            lambda d:d["concepts"]["uses"][0].update(scope="another-scope"),
            lambda d:d["concepts"]["uses"][0].update(frame_kind="COUNTERFACTUAL"),
            lambda d:d["concepts"]["uses"][1]["commitment"].update(terms_version="v2"),
            lambda d:d["concepts"]["uses"][1]["commitment"].update(id="absent"),
            lambda d:d["concepts"]["uses"][1].update(selector=dict(kind="CHOICE",id="meaning")),
            lambda d:d["models"][0]["argument"]["premises"].append(dict(d["models"][0]["argument"]["premises"][-1],id="unbound-alias")),
            lambda d:d["models"][0]["concept_bindings"][-1].update(use_id="current"),
            lambda d:d["concepts"]["cases"][0].update(term=term("pair",term("c"))),
        ]
        for i,mutate in enumerate(mutations):
            data=self.candidate();mutate(data)
            result,_=self.f.run_candidate(data,request=replace(self.f.request,request_id="invalid-concept"+str(i)))
            self.assertEqual(result.status,"INVALID_REQUEST",(i,result.diagnostics));self.assertFalse(result.answer)

    def test_all_certificate_layers_are_verified_before_compact_delivery(self):
        values,_,_=self.run_candidate();original=self.f.inference()
        AnswerAssembler().compact_claim(original)
        mutations=[lambda v:v["concepts"]["definitions"][0].update(definition_version="forged"),
            lambda v:v["program"]["host_context"].update(session_id="someone-else"),
            lambda v:v["program"]["concepts"].update(namespace="forged"),
            lambda v:v["branches"][0]["classifications"]["current"]["actual"].update(possible_values=[True]),
            lambda v:v["branches"][0]["actual_judgment"]["models"][0]["facts"]["concept:promise-scope"]["actual"]["original_commitment"]["terms"].update(version="changed"),
            lambda v:v["branches"][0]["decision_projection"][decision_key("scene","notice","notification")].update(recommended=["protect"]),
            lambda v:v["program"]["base_program"]["segments"][0].update(text="tampered"),
            lambda v:v["robust_recommended"].update(fake=["ignore"]),
            lambda v:v["local_model"].update(dialect="judgment-model-1")]
        for mutate in mutations:
            value=thaw(original.values);mutate(value)
            with self.assertRaises(HCLFailure):AnswerAssembler().compact_claim(replace(original,values=value))

    def test_actual_m13_work_and_partial_version_frontier(self):
        values,_,_=self.run_candidate()
        actual_work=sum(b["actual_judgment"]["models"][0]["actual_argument"]["values"]["local_evaluations"] for b in values["branches"])
        self.assertGreater(actual_work,100)
        self.assertGreater(values["local_evaluations"],actual_work)
        for budget in (1,10,50,200,values["local_evaluations"]-1):
            request=replace(self.f.request,request_id="limited"+str(budget),budget=replace(self.f.request.budget,max_local_evaluations=budget))
            limited,result,_=self.run_candidate(request=request)
            self.assertLessEqual(result.usage["local_evaluations"],budget)
            self.assertFalse(limited["complete"]);self.assertFalse(limited["robust_recommended"])

    def test_unrelated_source_and_concept_do_not_change_semantic_versions(self):
        before,_,_=self.run_candidate()
        unrelated=self.f.store.put_source("s",self.f.owner,"unrelated","A separate recipe mentions a blue plate.")
        request=replace(self.f.request,request_id="unrelated",source_handles=(*self.f.request.source_handles,unrelated))
        snapshot=self.f.store.snapshot("s",self.f.owner,request.source_handles)
        data=propose(snapshot,request.question)
        from hcl.semantics.segments import segment_snapshot
        extra=[s.segment_id for s in segment_snapshot(snapshot,request.question) if s.source_id=="unrelated"]
        for model in data["models"]:
            model["mental"]["unmodeled_segments"].extend(extra);model["argument"]["unmodeled_segments"].extend(extra)
        data["concepts"]["unmodeled_segments"].extend(extra)
        version=deepcopy(data["concepts"]["versions"][0]);version.update(id="unrelated",concept_key="recipe",purpose="a different use")
        data["concepts"]["versions"].append(version)
        after,_,_=self.run_candidate(data,request=request)
        for old,new in zip(before["concepts"]["definitions"],after["concepts"]["definitions"]):
            self.assertEqual(old["definition_version"],new["definition_version"])
            self.assertNotEqual(old["evidence_fingerprint"],new["evidence_fingerprint"])
        self.assertEqual(before["robust_recommended"],after["robust_recommended"])

    def test_original_scope_is_a_real_constraint_not_only_pin_metadata(self):
        data=self.candidate();c=data["concepts"]
        historical=deepcopy(c["cases"][0]);historical.update(id="historical-case",term=term("pair",term("c"),term("c")))
        c["cases"].append(historical);c["uses"][1]["case_id"]="historical-case"
        values,_,_=self.run_candidate(data)
        for branch in values["branches"]:
            self.assertEqual(branch["classifications"]["promise-scope"]["actual"]["status"],"MEMBER")
            m=branch["actual_judgment"]["models"][0]
            self.assertEqual(m["decisions"][0]["frameworks"][0]["branches"][0]["states"]["original-scope"],"ACTIVE")
            self.assertEqual(m["decisions"][0]["robust_across_frameworks"],["protect"])

    def test_unbound_original_commitment_claim_is_rejected(self):
        data=self.candidate();use=deepcopy(data["concepts"]["uses"][1])
        use.update(id="unbound-pin",commitment=dict(id="nonexistent",terms_version="imaginary"))
        data["concepts"]["uses"].append(use)
        result,_=self.f.run_candidate(data)
        self.assertEqual(result.status,"INVALID_REQUEST");self.assertFalse(result.answer)

    def test_run_stream_compat_and_immutable_completed_replay(self):
        import json
        from hcl.compat.workspace import CognitionWorkspace
        from hcl.models.gateway import ModelGateway,OfflineModelPort
        data=self.candidate();values,first,port=self.run_candidate(data,stream=True)
        data["concepts"]["versions"][0]["purpose"]="new meaning"
        replay,port=self.f.run_candidate(data,stream=True)
        self.assertEqual((first.answer,first.claim_records),(replay.answer,replay.claim_records));self.assertEqual(port.attempts,0)
        port=OfflineModelPort(json.dumps(self.candidate()))
        workspace=CognitionWorkspace(self.f.store,principal=self.f.owner,session_id="s",gateway=ModelGateway(self.f.store,port))
        import asyncio
        from hcl import ExecutionIssue
        from hcl.kernel.types import Issue
        result=asyncio.run(workspace.run(replace(self.f.request,request_id="compat-concept",
            issue=ExecutionIssue("root",goals=(Issue("compat-concept","judgment.evaluate"),)))))
        self.assertEqual(result.status,"PARTIAL",result.diagnostics)
        self.assertIn("Joint version selection",result.answer)

    def test_returned_computed_committed_resume_and_unknown_do_not_resend(self):
        from hcl import HCL
        from hcl.memory.store import StateStore
        from hcl.operators.local_model import LocalModelOperator
        from hcl.runtime.recovery import RecoveryManager
        class Crash(BaseException):pass
        for seam in ("return_persisted","execution_computed","execution_effects_committed","send_started"):
            from hcl import ExecutionIssue
            from hcl.kernel.types import Issue
            request=replace(self.f.request,request_id="v2-"+seam,
                issue=ExecutionIssue("root",goals=(Issue("v2-"+seam,"judgment.evaluate"),)))
            candidate=self.candidate();owner=self.f.store.owner_id;fired=False
            def stop(stage):
                nonlocal fired
                if stage==seam and not fired:fired=True;raise Crash()
            with patch.object(self.f.store,"_checkpoint",side_effect=stop),self.assertRaises(Crash):
                self.f.run_candidate(candidate,request=request)
            self.assertTrue(fired)
            self.f.store.close();self.f.store=StateStore.sqlite(self.f.path)
            if seam=="send_started":
                with self.assertRaises(HCLFailure):RecoveryManager(self.f.store).resume_execution(request,expected_owner_id=owner)
                result,port=self.f.run_candidate(candidate,request=request)
                self.assertIsNone(result.usage["mock_calls"]);self.assertEqual(result.usage["held_mock_calls"],1)
            else:
                RecoveryManager(self.f.store).resume_execution(request,expected_owner_id=owner)
                if seam=="return_persisted":result,port=self.f.run_candidate(candidate,request=request)
                else:
                    with patch.object(LocalModelOperator,"run",side_effect=AssertionError("accepted effect cannot recompute")):
                        result,port=self.f.run_candidate(candidate,request=request)
                self.assertEqual(result.status,"PARTIAL",result.diagnostics)
            self.assertEqual(port.attempts,0)

    def test_secondary_source_revocation_and_erasure_invalidate_stable_versions(self):
        from hcl import HCL
        data=self.candidate();self.run_candidate(data)
        self.f.store.set_readers("s",self.f.owner,"principles",{"bob"})
        denied,port=self.f.run_candidate(data)
        self.assertEqual(denied.status,"DENIED");self.assertFalse(denied.answer);self.assertEqual(port.attempts,0)
        self.f.store.set_readers("s",self.f.owner,"principles",{"alice"})
        plan=self.f.store.plan_source_erasure("s",self.f.owner,"principles",expected_version=2)
        self.f.store.begin_source_erasure("s",self.f.owner,"principles",expected_version=2,plan_hash=plan["plan_hash"],erasure_id="e"*32)
        receipt=self.f.store.resume_source_erasure("s",self.f.owner,"e"*32)
        self.assertTrue(receipt["database_scrubbed"])
        denied=HCL(self.f.store,principal=self.f.owner).run_sync(self.f.request)
        self.assertFalse(denied.answer or denied.claim_records)

    def test_delimiter_containing_model_ids_do_not_collapse_decisions(self):
        data=self.candidate();model=data["models"][0];model["decisions"][0]["id"]="notification:other"
        other=deepcopy(model);other["mental"]["id"]="notice:notification";other["decisions"][0]["id"]="other"
        data["models"].append(other)
        values,result,_=self.run_candidate(data)
        self.assertTrue(values["complete"])
        for branch in values["branches"]:
            self.assertEqual(len(branch["decision_projection"]),2)
            self.assertEqual({v["decision_id"] for v in branch["decision_projection"].values()},{"notification:other","other"})
        self.assertEqual(len(values["robust_recommended"]),2)

    def test_proof_or_label_changes_are_not_reported_as_semantic_sensitivity(self):
        data=self.candidate()
        original=deepcopy(data["concepts"]["versions"][0]);original["id"]="revised";original["criteria"][0]["id"]="renamed-criterion"
        data["concepts"]["versions"][1]=original
        values,_,_=self.run_candidate(data)
        self.assertEqual(values["concepts"]["definitions"][0]["definition_version"],values["concepts"]["definitions"][1]["definition_version"])
        sensitivity=values["sensitivity"][0]
        self.assertEqual(sensitivity["changed_classifications"],[])
        self.assertEqual(sensitivity["changed_decisions"],[])
        self.assertEqual(sensitivity["changed_recommendations"],[])
        self.assertTrue(sensitivity["classification_trace_changes"])
        data=self.candidate();data["concepts"]["cases"][0]["term"]=term("pair",term("c"),term("c"))
        values,_,_=self.run_candidate(data,request=replace(self.f.request,request_id="same-judgment-new-proof"))
        sensitivity=values["sensitivity"][0]
        self.assertEqual(sensitivity["changed_classifications"],[])
        self.assertEqual(sensitivity["changed_decisions"],[])
        self.assertEqual(sensitivity["changed_recommendations"],[])
        self.assertTrue(sensitivity["decision_trace_changes"])
        data["models"][0]["argument"]["priorities"]=[]
        data["concepts"]["versions"][1]["purpose"]="Scope variant 2"
        values,_,_=self.run_candidate(data,request=replace(self.f.request,request_id="same-extensions-reordered"))
        self.assertTrue(values["complete"])
        sensitivity=values["sensitivity"][0]
        self.assertEqual(sensitivity["changed_classifications"],[])
        self.assertEqual(sensitivity["changed_decisions"],[])
        self.assertEqual(sensitivity["changed_recommendations"],[])
        self.assertTrue(sensitivity["decision_trace_changes"])
