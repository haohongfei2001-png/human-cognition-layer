"""Additive counterexample candidates are actual conditional judgments, not adoption."""
from copy import deepcopy
from dataclasses import replace
import unittest
from unittest.mock import patch
from hcl import HCL, ExecutionIssue, ConceptAdoptionIssue, ConceptFollowIssue, ConceptBinding
from hcl.kernel.types import thaw, HCLFailure
from hcl.memory import codec
from hcl.operators.concept_judgment import decision_key
from hcl.runtime.answer import AnswerAssembler
from scripts.witness_unified_concept_repairs import propose, SCENE, PRINCIPLES, term
from tests import test_unified_s4_judgment as runtime


class ConceptRepairTests(unittest.TestCase):
    def setUp(self):
        self.f=runtime.JudgmentExecutionTests();self.f.setUp();self.addCleanup(self.f.tearDown)
        self.f.handle=self.f.store.put_source("s",self.f.owner,"scene",SCENE)
        self.f.norm=self.f.store.put_source("s",self.f.owner,"principles",PRINCIPLES)
        self.f.request=replace(self.f.request,source_handles=(self.f.handle,self.f.norm))
        self.key=decision_key("scene","notice","notification")

    def candidate(self):
        return propose(self.f.store.snapshot("s",self.f.owner,self.f.request.source_handles),self.f.request.question)

    def run_candidate(self,data=None,request=None):
        result,port=self.f.run_candidate(data or self.candidate(),request=request or self.f.request)
        self.assertEqual(result.status,"PARTIAL",result.diagnostics)
        proof=self.results(result)[0]
        return thaw(proof.values),result,port,proof

    def results(self,result):
        from hcl.runtime.execution_ledger import ExecutionLedger
        request=replace(self.f.request,request_id=result.execution_receipt["request_id"])
        return ExecutionLedger(self.f.store).delivery_inferences(request,tuple(result.execution_receipt.get("result_ids",())))

    def issue(self,name,goal,**kwargs):
        request=replace(self.f.request,request_id=name,source_handles=(),budget=replace(self.f.request.budget,max_mock_calls=0,**kwargs),issue=ExecutionIssue("root",goals=(goal,)))
        return HCL(self.f.store,principal=self.f.owner).run_sync(request),request

    def test_real_generated_alternatives_change_m13_m14_without_adoption(self):
        values,result,port,proof=self.run_candidate()
        self.assertTrue(values["complete"])
        self.assertEqual(proof.kind,"CONDITIONAL_CONCEPT_REPAIR_JUDGMENT")
        repair=values["repairs"][0]
        self.assertEqual(len(repair["candidates"]),14)
        self.assertEqual(sum(len(c["equivalent_partitions"]) for c in repair["candidates"]),15)
        self.assertFalse(repair["adopted"])
        best=next(c for c in repair["candidates"] if c["id"] in repair["minimum_consistent_candidate_ids"])
        branch=next(b for b in values["branches"] if b["selections"]["meaning"]==best["version_label"])
        self.assertEqual(branch["classifications"]["current"]["actual"]["status"],"MEMBER")
        self.assertEqual(branch["decision_projection"][self.key]["recommended"],["protect"])
        specific=next(c for c in repair["candidates"] if len(c["patterns"])==4)
        other=next(b for b in values["branches"] if b["selections"]["meaning"]==specific["version_label"])
        self.assertEqual(other["classifications"]["current"]["actual"]["status"],"EXCLUDED")
        self.assertEqual(other["decision_projection"][self.key]["recommended"],["ignore"])
        self.assertTrue(any(s["changed_recommendations"] for s in values["sensitivity"]))
        for b in values["branches"]:
            self.assertEqual(b["classifications"]["promise-scope"],values["branches"][0]["classifications"]["promise-scope"])
        self.assertEqual(port.attempts,1)
        self.assertTrue(any(f.field=="repairs" for c in result.claim_records for f in c.used_result_fields))
        self.assertEqual(self.f.store._db.execute("SELECT count(*) FROM inferences WHERE result_id LIKE 'concept-adoption:%'").fetchone()[0],0)

    def test_explicit_generated_adoption_reuses_persistent_successors_and_old_bytes(self):
        values,original,_,proof=self.run_candidate()
        start,_=self.issue("A",ConceptAdoptionIssue("a",stream_id="institution",support_result_ids=(proof.result_id,),version_labels=("original",)))
        self.assertEqual(start.status,"COMPLETED",start.diagnostics)
        head=self.results(start)[0].result_id
        follow=ConceptFollowIssue("follow",base_result_id=proof.result_id,bindings=(ConceptBinding("meaning","institution"),))
        b,_=self.issue("B",follow);c,_=self.issue("C",replace(follow,issue_id="follow-c"))
        self.assertEqual(b.status,"PARTIAL",b.diagnostics)
        before=self.results(b)[0]
        old={r["request_id"]:dict(r) for r in self.f.store._db.execute("SELECT * FROM tasks WHERE request_id IN ('B','C')")}
        repair=values["repairs"][0]
        label=next(x["version_label"] for x in repair["candidates"] if x["id"] in repair["minimum_consistent_candidate_ids"])
        from hcl.operators.persistent_concepts import compute_persistent
        with patch("hcl.operators.persistent_concepts.compute_persistent",wraps=compute_persistent) as compute:
            d,_=self.issue("D",ConceptAdoptionIssue("d",stream_id="institution",support_result_ids=(proof.result_id,),version_labels=(label,),expected_head=head))
        self.assertEqual(d.status,"PARTIAL",d.diagnostics)
        self.assertEqual(compute.call_count,2)
        successors=[r for r in self.results(d) if r.kind=="CONDITIONAL_PERSISTENT_CONCEPT_REPAIR_JUDGMENT"]
        self.assertEqual(len(successors),2)
        for r in successors:
            self.assertEqual(r.values["schema"],"hcl-persistent-concept-judgment-2")
            self.assertEqual(r.values["branches"][0]["decision_projection"][self.key]["recommended"],("protect",))
            self.assertEqual(r.values["branches"][0]["classifications"]["promise-scope"],before.values["branches"][0]["classifications"]["promise-scope"])
            AnswerAssembler().compact_claim(r)
        self.assertEqual(old,{r["request_id"]:dict(r) for r in self.f.store._db.execute("SELECT * FROM tasks WHERE request_id IN ('B','C')")})
        replay=HCL(self.f.store,principal=self.f.owner).run_sync(self.f.request)
        self.assertEqual((original.answer,original.claim_records),(replay.answer,replay.claim_records))
        self.assertEqual(d.usage["mock_calls"],0)

    def test_small_budgets_withhold_full_robust_and_minimum(self):
        full,_,_,_=self.run_candidate()
        for budget in (1,20,500,1500,full["local_evaluations"]-1):
            request=replace(self.f.request,request_id="budget"+str(budget),budget=replace(self.f.request.budget,max_local_evaluations=budget))
            values,result,_,_=self.run_candidate(request=request)
            self.assertFalse(values["complete"])
            self.assertEqual(values["robust_recommended"],{})
            self.assertLessEqual(result.usage["local_evaluations"],budget)
            if not values["repairs"][0]["complete"]:
                self.assertFalse(values["repairs"][0]["minimum_consistent_candidate_ids"])

    def test_forged_repair_and_or_certificate_layers_fail_delivery(self):
        values,_,_,proof=self.run_candidate()
        mutations=[lambda v:v["repairs"][0].update(adopted=True),
            lambda v:v["repairs"][0].update(minimum_consistent_candidate_ids=["invented"]),
            lambda v:v["generated_concepts"]["versions"][-1]["criteria"][0].update(partition=[]),
            lambda v:v["program"]["repairs"][0].update(version_id="original"),
            lambda v:v["branches"][-1]["classifications"]["current"]["actual"].update(possible_values=[True]),
            lambda v:v["local_model"].update(dialect="judgment-model-2")]
        for mutate in mutations:
            changed=deepcopy(values);mutate(changed)
            with self.assertRaises(HCLFailure):AnswerAssembler().compact_claim(replace(proof,values=changed))

    def test_direction_withdrawal_conflict_and_invalid_supplied_prediction(self):
        for direction in ("NECESSARY","SUFFICIENT","TYPICAL"):
            data=self.candidate();data["concepts"]["versions"][1]["criteria"][0]["direction"]=direction
            values,_,_,_=self.run_candidate(data,replace(self.f.request,request_id=direction))
            self.assertTrue(all(d["criteria"][0]["direction"]==direction for d in values["concepts"]["definitions"] if d["id"].startswith("repair:")))
            if direction in ("NECESSARY","TYPICAL"):
                self.assertTrue(all(b["classifications"]["current"]["actual"]["status"]!="MEMBER" for b in values["branches"]))
        data=self.candidate();data["concepts"]["versions"][1]["active_assumptions"]=[]
        values,_,_,_=self.run_candidate(data,replace(self.f.request,request_id="withdrawn"))
        self.assertFalse(values["complete"]);self.assertEqual(values["repairs"][0]["candidates"],[])
        data=self.candidate();data["repairs"][0]["score"]=1
        result,_=self.f.run_candidate(data,request=replace(self.f.request,request_id="fake"))
        self.assertEqual(result.status,"INVALID_REQUEST")

    def test_returned_computed_committed_and_unknown_keep_single_send(self):
        from tests.test_unified_s4_concept_judgment import ConceptJudgmentTests
        # This inherited scenario dynamically uses this v3 candidate and store.
        ConceptJudgmentTests.test_returned_computed_committed_resume_and_unknown_do_not_resend(self)

    def test_source_revocation_and_erasure_gate_compressed_successors(self):
        from tests.test_unified_s4_concept_judgment import ConceptJudgmentTests
        ConceptJudgmentTests.test_secondary_source_revocation_and_erasure_invalidate_stable_versions(self)

    def test_foreign_host_cannot_deliver_or_adopt_new_result_kind(self):
        from hcl.kernel.types import Principal
        _,result,_,proof=self.run_candidate()
        foreign=Principal(self.f.owner.tenant_id,"bob")
        from hcl.runtime.execution_ledger import ExecutionLedger
        request=replace(self.f.request,request_id="foreign",principal=foreign)
        with self.assertRaises(HCLFailure):
            ExecutionLedger(self.f.store).delivery_inferences(request,(proof.result_id,))
        request=replace(request,source_handles=(),budget=replace(request.budget,max_mock_calls=0),
            issue=ExecutionIssue("root",goals=(ConceptAdoptionIssue("foreign",stream_id="x",support_result_ids=(proof.result_id,),version_labels=("original",)),)))
        denied=HCL(self.f.store,principal=foreign).run_sync(request)
        self.assertEqual(denied.status,"DENIED");self.assertFalse(denied.answer)

    def test_lossless_capsule_is_bounded_canonical_and_not_old_envelope(self):
        from hcl.operators.concept_proof import pack_proof,unpack_proof,MAX_BYTES
        import base64,zlib
        _,_,_,proof=self.run_candidate()
        packed=pack_proof(proof)
        self.assertEqual(codec.dumps(unpack_proof(packed)),codec.dumps(proof))
        self.assertLess(len(codec.dumps(packed)),len(codec.dumps(proof))//5)
        corruptions=[dict(packed,uncompressed_bytes=MAX_BYTES+1),dict(packed,sha256="0"*64),
            dict(packed,zlib_base64=base64.b64encode(b"broken").decode()),
            dict(packed,zlib_base64=packed["zlib_base64"]+"!!!!"),
            dict(packed,zlib_base64=base64.b64encode(zlib.compress(b"x"*200000)).decode(),uncompressed_bytes=2),
            dict(packed,extra=True)]
        for bad in corruptions:
            with self.assertRaises(ValueError):unpack_proof(bad)

    def test_duplicate_examples_and_labels_do_not_change_generated_meanings(self):
        before,_,_,_=self.run_candidate()
        candidate=self.candidate()
        c=candidate["concepts"]["versions"][1]["criteria"][0]
        extra=deepcopy(c["positive"][0]);extra["id"]="another-report";c["positive"].append(extra)
        after,_,_,_=self.run_candidate(candidate,replace(self.f.request,request_id="duplicate"))
        old={d["id"]:d["definition_version"] for d in before["concepts"]["definitions"] if d["id"].startswith("repair:")}
        new={d["id"]:d["definition_version"] for d in after["concepts"]["definitions"] if d["id"].startswith("repair:")}
        self.assertEqual(old,new)

    def test_conflicting_case_cannot_be_repaired_by_discarding_counterexample(self):
        candidate=self.candidate();c=candidate["concepts"]["versions"][1]["criteria"][0]
        c["negative"].append(dict(deepcopy(c["positive"][0]),id="conflicting-label"))
        values,_,_,_=self.run_candidate(candidate)
        repair=values["repairs"][0]
        self.assertTrue(repair["complete"])
        self.assertEqual(repair["status"],"NO_REPAIR_IN_FINITE_LANGUAGE")
        self.assertFalse(repair["minimum_consistent_candidate_ids"])
        self.assertFalse(any(d["id"].startswith("repair:") for d in values["concepts"]["definitions"]))
        self.assertTrue(all(any(e["id"]=="conflicting-label" and e["status"]=="MATCH" for e in c["examples"]) for c in repair["candidates"]))


    def test_source_edit_requires_recompile_without_any_new_call(self):
        _,_,_,proof=self.run_candidate()
        a,_=self.issue("A",ConceptAdoptionIssue("a",stream_id="institution",support_result_ids=(proof.result_id,),version_labels=("original",)))
        self.assertEqual(a.status,"COMPLETED")
        self.f.store.put_source("s",self.f.owner,"principles","A different meaning needs new source interpretation.")
        count=self.f.store._db.execute("SELECT count(*) FROM calls").fetchone()[0]
        denied,_=self.issue("B",ConceptFollowIssue("b",base_result_id=proof.result_id,bindings=(ConceptBinding("meaning","institution"),)))
        self.assertEqual(denied.status,"NEEDS_RECOMPILE",denied.diagnostics)
        self.assertFalse(denied.answer)
        self.assertEqual(count,self.f.store._db.execute("SELECT count(*) FROM calls").fetchone()[0])

    def test_independent_generated_support_survives_primary_erasure(self):
        import json
        from hcl.semantics.segments import segment_snapshot
        from hcl.kernel.concept_registry import ConceptQuery
        values,_,_,proof=self.run_candidate()
        snapshot=self.f.store.snapshot("s",self.f.owner,self.f.request.source_handles)
        renames={"scene":"independent-scene","principles":"independent-principles"}
        handles=tuple(self.f.store.put_source("s",self.f.owner,renames[k],v.text) for k,v in snapshot.immutable_views.items())
        independent=self.f.store.snapshot("s",self.f.owner,handles)
        old=[s for s in segment_snapshot(snapshot,self.f.request.question) if s.kind=="SOURCE"]
        new=[s for s in segment_snapshot(independent,self.f.request.question) if s.kind=="SOURCE"]
        for key in snapshot.immutable_views:
            a=[s for s in old if s.source_id==key];b=[s for s in new if s.source_id==renames[key]]
            self.assertEqual([s.text for s in a],[s.text for s in b])
            renames.update({x.segment_id:y.segment_id for x,y in zip(a,b,strict=True)})
        def rename(v):
            if isinstance(v,dict):return {k:rename(x) for k,x in v.items()}
            if isinstance(v,list):return [rename(x) for x in v]
            return renames.get(v,v) if isinstance(v,str) else v
        data=rename(json.loads(proof.values["program"]["candidate"]))
        _,_,_,second=self.run_candidate(data,replace(self.f.request,request_id="independent",source_handles=handles))
        repair=values["repairs"][0]
        label=next(c["version_label"] for c in repair["candidates"] if c["id"] in repair["minimum_consistent_candidate_ids"])
        a,_=self.issue("A",ConceptAdoptionIssue("a",stream_id="institution",support_result_ids=(proof.result_id,second.result_id),version_labels=(label,label)))
        self.assertEqual(a.status,"COMPLETED",a.diagnostics)
        query=ConceptQuery("SELECTION","institution",2)
        self.f.store.set_readers("s",self.f.owner,"principles",{"bob"})
        view=self.f.store.query_snapshot("s",self.f.owner,(),(query,)).query_views["0"]
        self.assertEqual(view["origin_result_ids"],(second.result_id,))
        self.f.store.set_readers("s",self.f.owner,"principles",{"alice"})
        plan=self.f.store.plan_source_erasure("s",self.f.owner,"principles",expected_version=self.f.norm.version)
        self.f.store.begin_source_erasure("s",self.f.owner,"principles",expected_version=self.f.norm.version,plan_hash=plan["plan_hash"],erasure_id="f"*32)
        self.assertTrue(self.f.store.resume_source_erasure("s",self.f.owner,"f"*32)["database_scrubbed"])
        now=self.f.store.query_snapshot("s",self.f.owner,(),(query,)).query_views["0"]
        self.assertEqual(now["origin_result_ids"],(second.result_id,))
        self.f.store.rebuild_projections()
        self.assertEqual(self.f.store.query_snapshot("s",self.f.owner,(),(query,)).query_views["0"],now)

    def test_interrupted_repair_successor_resumes_without_reexecution(self):
        from hcl.memory.store import StateStore
        from hcl.runtime.recovery import RecoveryManager
        from hcl.operators.persistent_concepts import compute_persistent
        class Crash(BaseException):pass
        values,_,_,proof=self.run_candidate()
        repair=values["repairs"][0]
        label=next(c["version_label"] for c in repair["candidates"] if c["id"] in repair["minimum_consistent_candidate_ids"])
        for ordinal,seam in ((1,"execution_effects_committed"),(2,"execution_computed"),(2,"execution_effects_committed")):
            suffix=seam+str(ordinal);stream="s-"+suffix
            a,_=self.issue("A-"+suffix,ConceptAdoptionIssue("a",stream_id=stream,support_result_ids=(proof.result_id,),version_labels=("original",)))
            head=self.results(a)[0].result_id
            b,_=self.issue("B-"+suffix,ConceptFollowIssue("b",base_result_id=proof.result_id,bindings=(ConceptBinding("meaning",stream),)))
            self.assertEqual(b.status,"PARTIAL",b.diagnostics)
            goal=ConceptAdoptionIssue("d",stream_id=stream,support_result_ids=(proof.result_id,),version_labels=(label,),expected_head=head)
            request=replace(self.f.request,request_id="D-"+suffix,source_handles=(),budget=replace(self.f.request.budget,max_mock_calls=0),issue=ExecutionIssue("root",goals=(goal,)))
            owner=self.f.store.owner_id;count=0
            def stop(stage):
                nonlocal count
                if stage==seam:
                    count+=1
                    if count==ordinal:raise Crash()
            with patch.object(self.f.store,"_checkpoint",side_effect=stop),self.assertRaises(Crash):
                HCL(self.f.store,principal=self.f.owner).run_sync(request)
            self.f.store.close();self.f.store=StateStore.sqlite(self.f.path)
            RecoveryManager(self.f.store).resume_execution(request,expected_owner_id=owner)
            with patch("hcl.operators.persistent_concepts.compute_persistent",wraps=compute_persistent) as compute:
                result=HCL(self.f.store,principal=self.f.owner).run_sync(request)
            self.assertEqual(result.status,"PARTIAL",result.diagnostics)
            self.assertEqual(compute.call_count,1 if ordinal==1 else 0)
            self.assertEqual(result.usage["mock_calls"],0)
            replay=HCL(self.f.store,principal=self.f.owner).run_sync(request)
            self.assertEqual((replay.answer,replay.claim_records),(result.answer,result.claim_records))


    def test_equal_cost_reflections_both_reach_real_judgment(self):
        candidate=self.candidate();c=candidate["concepts"]["versions"][1]["criteria"][0]
        def triple(letters):
            return term("request",*(dict(kind="TERM",sort="Slot"+str(i),symbol=str(i)+x,arguments=[]) for i,x in enumerate(letters)))
        def row(key,letters):
            return dict(id=key,term=triple(letters),assumptions=["reading"],segment_ids=c["segment_ids"])
        c["positive"]=[row(str(i),letters) for i,letters in enumerate(("aaa","abb","bab"))]
        c["negative"]=[row("n","aba")]
        candidate["concepts"]["cases"][0]["term"]=triple("baa")
        values,_,_,_=self.run_candidate(candidate)
        repair=values["repairs"][0]
        tied=[c for c in repair["candidates"] if c["id"] in repair["minimum_consistent_candidate_ids"]]
        self.assertEqual(len(tied),2)
        self.assertEqual({(c["complexity"],c["work"]) for c in tied},{(41,35)})
        labels={c["version_label"] for c in tied}
        actual=[b for b in values["branches"] if b["selections"]["meaning"] in labels]
        self.assertEqual(len(actual),2)
        self.assertEqual({b["classifications"]["current"]["actual"]["status"] for b in actual},{"MEMBER","EXCLUDED"})
        self.assertEqual({tuple(b["decision_projection"][self.key]["recommended"]) for b in actual},{("protect",),("ignore",)})
        self.assertFalse(repair["adopted"])


if __name__=="__main__":unittest.main()
