"""Synthetic independent requests prove actual persisted local revision."""
from dataclasses import replace
from copy import deepcopy
import unittest
from unittest.mock import patch

from hcl import HCL, ExecutionIssue, ConceptAdoptionIssue, ConceptFollowIssue, ConceptBinding
from hcl.kernel.types import Issue, thaw
from hcl.memory import codec
from hcl.operators.concept_judgment import decision_key
from tests import test_unified_s4_concept_judgment as prior


class PersistentConceptPropagationTests(unittest.TestCase):
    def setUp(self):
        self.fixture=prior.ConceptJudgmentTests();self.fixture.setUp();self.addCleanup(self.fixture.doCleanups)
        self.f=self.fixture.f
        _,self.original,_=self.fixture.run_candidate()
        self.base=self.f.inference()
        self.key=decision_key("scene","notice","notification")

    def run_issue(self,name,goal,**budget):
        request=replace(self.f.request,request_id=name,source_handles=(),
            budget=replace(self.f.request.budget,max_mock_calls=0,**budget),
            issue=ExecutionIssue("root",goals=(goal,)))
        result=HCL(self.f.store,principal=self.f.owner).run_sync(request)
        return result,request

    def adopt(self,name,label="original",head=None,stream="institution",proof=None):
        return self.run_issue(name,ConceptAdoptionIssue("adopt-"+name,stream_id=stream,
            support_result_ids=((proof or self.base).result_id,),version_labels=(label,),expected_head=head))

    def follow(self,name,stream="institution"):
        return self.run_issue(name,ConceptFollowIssue("follow-"+name,base_result_id=self.base.result_id,
            bindings=(ConceptBinding("meaning",stream),)))

    def results(self,result,kind=None):
        ids=set(result.execution_receipt.get("result_ids",()))
        from hcl.runtime.execution_ledger import ExecutionLedger
        request=replace(self.f.request,request_id=result.execution_receipt["request_id"])
        return [r for r in ExecutionLedger(self.f.store).delivery_inferences(request,tuple(ids)) if kind is None or r.kind==kind]

    def test_two_prior_requests_are_discovered_and_recomputed_without_resending(self):
        adopted,_=self.adopt("A")
        self.assertEqual(adopted.status,"COMPLETED",adopted.diagnostics)
        head=self.results(adopted)[0].result_id
        b,b_request=self.follow("B");c,c_request=self.follow("C")
        self.assertEqual(b.status,"PARTIAL",b.diagnostics)
        before=self.results(b)[0]
        self.assertEqual(before.values["branches"][0]["decision_projection"][self.key]["recommended"],("ignore",))
        with self.f.store._transaction() as db:
            old_tasks={row["request_id"]:dict(row) for row in db.execute("SELECT * FROM tasks WHERE request_id IN ('B','C')")}
        from hcl.operators.persistent_concepts import compute_persistent
        with patch("hcl.operators.persistent_concepts.compute_persistent",wraps=compute_persistent) as execute:
            revision,_=self.adopt("D","revised",head)
        self.assertEqual(execute.call_count,2)
        self.assertEqual(revision.status,"PARTIAL",revision.diagnostics)
        successors=self.results(revision,"CONDITIONAL_PERSISTENT_CONCEPT_JUDGMENT")
        self.assertEqual(len(successors),2)
        self.assertEqual({r["original_request_id"] for r in revision.execution_receipt["concept_successors"]},{"B","C"})
        for value in successors:
            actual=value.values["branches"][0]
            self.assertEqual(actual["classifications"]["current"]["actual"]["status"],"MEMBER")
            self.assertEqual(actual["decision_projection"][self.key]["recommended"],("protect",))
            self.assertEqual(actual["classifications"]["promise-scope"],before.values["branches"][0]["classifications"]["promise-scope"])
            for field in ("cognition","actual_interaction","opportunities"):
                self.assertEqual(actual["actual_judgment"]["models"][0][field],before.values["branches"][0]["actual_judgment"]["models"][0][field])
        self.assertEqual(revision.usage["mock_calls"],0)
        with self.f.store._transaction() as db:
            for row in db.execute("SELECT * FROM tasks WHERE request_id IN ('B','C')"):
                self.assertEqual(dict(row),old_tasks[row["request_id"]])
        self.assertTrue(any(f.field=="branches" for c in revision.claim_records for f in c.used_result_fields))
        stale=HCL(self.f.store,principal=self.f.owner).run_sync(b_request)
        self.assertFalse(stale.answer);self.assertEqual(stale.status,"STALE_STATE")
        # Legacy v2 request remains explicitly finite/pinned, never subscribed.
        replay=HCL(self.f.store,principal=self.f.owner).run_sync(self.f.request)
        self.assertEqual((replay.answer,replay.claim_records),(self.original.answer,self.original.claim_records))

    def test_unrelated_stream_and_future_adoption_do_not_execute_consumers(self):
        a,_=self.adopt("A");head=self.results(a)[0].result_id
        b,_=self.follow("B");self.assertEqual(b.status,"PARTIAL",b.diagnostics)
        from hcl.operators.persistent_concepts import compute_persistent
        with patch("hcl.operators.persistent_concepts.compute_persistent",wraps=compute_persistent) as execute:
            unrelated,_=self.adopt("other",stream="other")
        self.assertEqual(execute.call_count,0)
        self.assertNotIn("concept_successors",unrelated.execution_receipt)
        candidate=self.fixture.candidate()
        candidate["concepts"]["versions"][1]["effective_at"]=3
        candidate["concepts"]["choices"][0]["versions"]=["original"]
        compiled,_=self.f.run_candidate(candidate,request=replace(self.f.request,request_id="future-proof"))
        proof=self.results(compiled)[0]
        with patch("hcl.operators.persistent_concepts.compute_persistent",wraps=compute_persistent) as execute:
            future,_=self.adopt("future","revised",head,proof=proof)
        self.assertEqual(future.status,"COMPLETED",future.diagnostics)
        self.assertEqual(execute.call_count,0)
        self.assertNotIn("concept_successors",future.execution_receipt)

    def test_explicit_compare_and_adopt_refuses_competing_parent(self):
        a,_=self.adopt("A");head=self.results(a)[0].result_id
        first,_=self.adopt("D","revised",head)
        self.assertEqual(first.status,"COMPLETED",first.diagnostics)
        second,_=self.adopt("competing","original",head)
        self.assertEqual(second.status,"STALE_STATE",second.diagnostics)
        self.assertFalse(second.answer)
        from hcl.kernel.concept_registry import ConceptQuery
        snapshot=self.f.store.query_snapshot("s",self.f.owner,(),(ConceptQuery("SELECTION","institution",2),))
        self.assertEqual(snapshot.query_views["0"]["selection"]["version_label"],"revised")

    def test_changed_source_requires_recompile_without_provider_replay(self):
        a,_=self.adopt("A");head=self.results(a)[0].result_id
        self.follow("B")
        self.f.store.put_source("s",self.f.owner,"scene","Different facts require new interpretation.")
        from hcl.kernel.concept_registry import ConceptQuery
        snapshot=self.f.store.query_snapshot("s",self.f.owner,(),(ConceptQuery("SELECTION","institution",2),))
        self.assertEqual(snapshot.query_views["0"]["status"],"NEEDS_RECOMPILE")
        before=self.f.store._db.execute("SELECT count(*) FROM calls").fetchone()[0]
        changed,_=self.follow("new-follow")
        self.assertEqual(changed.status,"NEEDS_RECOMPILE",changed.diagnostics)
        self.assertFalse(changed.answer)
        self.assertEqual(self.f.store._db.execute("SELECT count(*) FROM calls").fetchone()[0],before)

    def test_foreign_principal_cannot_read_or_adopt_same_stream(self):
        from hcl.kernel.types import Principal
        from hcl.kernel.concept_registry import ConceptQuery
        self.adopt("A")
        bob=Principal(self.f.owner.tenant_id,"bob")
        snapshot=self.f.store.query_snapshot("s",bob,(),(ConceptQuery("SELECTION","institution",2),))
        self.assertEqual(snapshot.query_views["0"]["status"],"NO_ADOPTED_VERSION")
        request=replace(self.f.request,request_id="foreign",principal=bob,source_handles=(),
            budget=replace(self.f.request.budget,max_mock_calls=0),
            issue=ExecutionIssue("root",goals=(ConceptAdoptionIssue("foreign",stream_id="institution",
                support_result_ids=(self.base.result_id,),version_labels=("revised",)),)))
        result=HCL(self.f.store,principal=bob).run_sync(request)
        self.assertEqual(result.status,"DENIED",result.diagnostics);self.assertFalse(result.answer)

    def test_local_budget_frontier_does_not_claim_successful_propagation(self):
        a,_=self.adopt("A");head=self.results(a)[0].result_id
        self.follow("B")
        result,_=self.run_issue("D",ConceptAdoptionIssue("adopt-D",stream_id="institution",
            support_result_ids=(self.base.result_id,),version_labels=("revised",),expected_head=head),max_local_evaluations=10)
        self.assertEqual(result.status,"PARTIAL",result.diagnostics)
        self.assertLessEqual(result.usage["observed_local_evaluations"],10)
        value=self.results(result,"CONDITIONAL_PERSISTENT_CONCEPT_JUDGMENT")[0]
        self.assertFalse(value.values["complete"]);self.assertFalse(value.values["robust_recommended"])
        self.assertEqual(result.usage["mock_calls"],0)

    def independent_proof(self):
        import json
        from hcl.semantics.segments import segment_snapshot
        handles=[];renames={"scene":"independent-scene","principles":"independent-principles"}
        old=self.f.store.snapshot("s",self.f.owner,self.f.request.source_handles)
        for key,source in old.immutable_views.items():
            handles.append(self.f.store.put_source("s",self.f.owner,renames[key],source.text))
        current=self.f.store.snapshot("s",self.f.owner,tuple(handles))
        prior_segments=[s for s in segment_snapshot(old,self.f.request.question) if s.kind=="SOURCE"]
        new_segments=[s for s in segment_snapshot(current,self.f.request.question) if s.kind=="SOURCE"]
        for source in old.immutable_views:
            left=[s for s in prior_segments if s.source_id==source]
            right=[s for s in new_segments if s.source_id==renames[source]]
            self.assertEqual([s.text for s in left],[s.text for s in right])
            renames.update({a.segment_id:b.segment_id for a,b in zip(left,right,strict=True)})
        def rename(value):
            if isinstance(value,dict):return {k:rename(v) for k,v in value.items()}
            if isinstance(value,list):return [rename(v) for v in value]
            return renames.get(value,value) if isinstance(value,str) else value
        candidate=rename(json.loads(self.base.values["program"]["candidate"]))
        request=replace(self.f.request,request_id="independent",source_handles=tuple(handles))
        result,_=self.f.run_candidate(candidate,request=request)
        self.assertEqual(result.status,"PARTIAL",result.diagnostics)
        return self.results(result)[0]

    def test_independent_live_support_survives_other_support_erasure(self):
        from hcl.kernel.concept_registry import ConceptQuery
        independent=self.independent_proof()
        a,_=self.run_issue("A",ConceptAdoptionIssue("A",stream_id="institution",
            support_result_ids=(self.base.result_id,independent.result_id),version_labels=("original","original")))
        self.assertEqual(a.status,"COMPLETED",a.diagnostics)
        query=ConceptQuery("SELECTION","institution",2)
        self.f.store.set_readers("s",self.f.owner,"principles",{"bob"})
        view=self.f.store.query_snapshot("s",self.f.owner,(),(query,)).query_views["0"]
        self.assertEqual(view["status"],"AVAILABLE")
        self.assertEqual(view["origin_result_ids"],(independent.result_id,))
        self.assertNotIn("principles",view["source_versions"])
        self.f.store.set_readers("s",self.f.owner,"principles",{"alice"})
        plan=self.f.store.plan_source_erasure("s",self.f.owner,"principles",expected_version=self.f.norm.version)
        self.f.store.begin_source_erasure("s",self.f.owner,"principles",expected_version=self.f.norm.version,
            plan_hash=plan["plan_hash"],erasure_id="e"*32)
        receipt=self.f.store.resume_source_erasure("s",self.f.owner,"e"*32)
        self.assertTrue(receipt["database_scrubbed"])
        view=self.f.store.query_snapshot("s",self.f.owner,(),(query,)).query_views["0"]
        self.assertEqual(view["status"],"AVAILABLE")
        self.assertEqual(view["origin_result_ids"],(independent.result_id,))
        self.f.store.rebuild_projections()
        self.assertEqual(self.f.store.query_snapshot("s",self.f.owner,(),(query,)).query_views["0"],view)

    def test_interrupted_adoption_and_successor_recover_without_reexecution(self):
        from hcl.memory.store import StateStore
        from hcl.runtime.recovery import RecoveryManager
        from hcl.operators.persistent_concepts import compute_persistent
        class Crash(BaseException):pass
        for ordinal,seam in ((1,"execution_effects_committed"),(2,"execution_computed"),(2,"execution_effects_committed")):
            suffix=seam+str(ordinal);stream="stream-"+suffix
            a,_=self.adopt("A-"+suffix,stream=stream);head=self.results(a)[0].result_id
            b,_=self.follow("B-"+suffix,stream=stream)
            self.assertEqual(b.status,"PARTIAL",b.diagnostics)
            goal=ConceptAdoptionIssue("D-"+suffix,stream_id=stream,support_result_ids=(self.base.result_id,),
                version_labels=("revised",),expected_head=head)
            request=replace(self.f.request,request_id="D-"+suffix,source_handles=(),
                budget=replace(self.f.request.budget,max_mock_calls=0),issue=ExecutionIssue("root",goals=(goal,)))
            old_owner=self.f.store.owner_id;count=0
            def crash(stage):
                nonlocal count
                if stage==seam:
                    count+=1
                    if count==ordinal:raise Crash()
            with patch.object(self.f.store,"_checkpoint",side_effect=crash),self.assertRaises(Crash):
                HCL(self.f.store,principal=self.f.owner).run_sync(request)
            self.f.store.close();self.f.store=StateStore.sqlite(self.f.path)
            RecoveryManager(self.f.store).resume_execution(request,expected_owner_id=old_owner)
            with patch("hcl.operators.persistent_concepts.compute_persistent",wraps=compute_persistent) as execute:
                result=HCL(self.f.store,principal=self.f.owner).run_sync(request)
            self.assertEqual(result.status,"PARTIAL",result.diagnostics)
            self.assertEqual(execute.call_count,1 if ordinal==1 else 0)
            values=self.results(result,"CONDITIONAL_PERSISTENT_CONCEPT_JUDGMENT")
            self.assertEqual(len(values),1)
            self.assertEqual(values[0].values["branches"][0]["decision_projection"][self.key]["recommended"],("protect",))
            self.assertEqual(result.usage["mock_calls"],0)
            before=self.f.store._db.execute("SELECT count(*) FROM inferences").fetchone()[0]
            replay=HCL(self.f.store,principal=self.f.owner).run_sync(request)
            self.assertEqual(replay.answer,result.answer)
            self.assertEqual(self.f.store._db.execute("SELECT count(*) FROM inferences").fetchone()[0],before)

    def test_fresh_delivery_revocation_never_exports_computed_successor(self):
        a,_=self.adopt("A");head=self.results(a)[0].result_id
        self.follow("B")
        fired=False
        from hcl.runtime.execution import ExecutionRunner
        original=ExecutionRunner._check_delivery
        def gate(request,result):
            nonlocal fired
            if request.request_id=="D" and not fired:
                fired=True
                self.f.store.set_readers("s",self.f.owner,"principles",{"bob"})
            return original(request,result)
        with patch.object(ExecutionRunner,"_check_delivery",staticmethod(gate)):
            result,_=self.adopt("D","revised",head)
        self.assertTrue(fired)
        self.assertEqual(result.status,"DENIED",result.diagnostics)
        self.assertFalse(result.answer or result.claim_records)

    def test_atomic_batch_rejects_same_stream_fork_and_allows_distinct_streams(self):
        from hcl.kernel.types import Delta,InferenceResult,HCLFailure
        from hcl.kernel.concept_registry import ConceptQuery
        from hcl.memory.concept_registry import adoption_value,prefix
        from hcl.semantics.concept_version_compiler import digest
        snapshot=self.f.store.snapshot("s",self.f.owner,())
        def value(label,stream):
            issue=ConceptAdoptionIssue("batch-"+label,stream_id=stream,support_result_ids=(self.base.result_id,),version_labels=(label,))
            with self.f.store._transaction() as db:
                session=self.f.store._session(db,"s",self.f.owner)
                body=adoption_value(self.f.store,db,session,self.f.owner,issue)
            return InferenceResult(prefix("s",self.f.owner,stream)+digest(body),"CONCEPT_ADOPTION",body,
                (),(),(),snapshot.rule_version,"EXPLICIT_HOST_ADOPTION_NOT_GLOBAL_TRUTH")
        def rows():
            return {table:[tuple(row) for row in self.f.store._db.execute("SELECT * FROM "+table)]
                    for table in ("sessions","events","inferences","tasks","calls")}
        before=rows()
        rejected=Delta("s",self.f.owner,snapshot.revision,snapshot.access_epoch,snapshot.rule_version,{},
                       (value("original","batch"),value("revised","batch")))
        with self.assertRaises(HCLFailure) as caught:
            self.f.store.commit(snapshot.revision,{},snapshot.access_epoch,rejected)
        self.assertEqual(caught.exception.diagnostic.code,"CONCEPT_ADOPTION_BATCH_FORK")
        self.assertEqual(rows(),before)
        empty=self.f.store.query_snapshot("s",self.f.owner,(),(ConceptQuery("SELECTION","batch",2),))
        self.assertEqual(empty.query_views["0"]["status"],"NO_ADOPTED_VERSION")
        accepted=replace(rejected,new_inferences=(value("original","left"),value("revised","right")))
        commit=self.f.store.commit(snapshot.revision,{},snapshot.access_epoch,accepted)
        self.assertEqual(len(commit.result_ids),2)
        for stream,label in (("left","original"),("right","revised")):
            selected=self.f.store.query_snapshot("s",self.f.owner,(),(ConceptQuery("SELECTION",stream,2),))
            self.assertEqual(selected.query_views["0"]["selection"]["version_label"],label)

    def test_explicit_withdrawn_alias_is_not_replaced_by_live_semantic_twin(self):
        from hcl.kernel.concept_registry import ConceptQuery
        from hcl.semantics.concept_version_compiler import digest
        for alias_name,reverse in (("aaa-withdrawn",False),("zzz-withdrawn",True)):
            with self.subTest(alias_name=alias_name):
                data=self.fixture.candidate()
                alias=deepcopy(data["concepts"]["versions"][0])
                alias.update(id=alias_name,active_assumptions=[])
                data["concepts"]["versions"].append(alias)
                if reverse:data["concepts"]["versions"].reverse()
                compiled,_=self.f.run_candidate(data,request=replace(self.f.request,request_id="proof-"+alias_name))
                proof=self.results(compiled)[0]
                defs={d["id"]:d for d in proof.values["concepts"]["definitions"]}
                self.assertEqual(defs["original"]["definition_version"],defs[alias_name]["definition_version"])
                self.assertTrue(defs[alias_name]["withdrawn"])
                self.assertFalse(defs["original"]["withdrawn"])
                adopted,_=self.adopt("adopt-"+alias_name,alias_name,stream=alias_name,proof=proof)
                self.assertEqual(adopted.status,"COMPLETED",adopted.diagnostics)
                header=self.results(adopted)[0]
                self.assertEqual(header.values["usability_hash"],digest(thaw(defs[alias_name]["withdrawn"])))
                view=self.f.store.query_snapshot("s",self.f.owner,(),(ConceptQuery("SELECTION",alias_name,2),)).query_views["0"]
                self.assertEqual(view["status"],"AVAILABLE")
                self.assertEqual(view["selection"]["version_label"],alias_name)
                followed,_=self.follow("follow-"+alias_name,stream=alias_name)
                self.assertEqual(followed.status,"PARTIAL",followed.diagnostics)
                successor=self.results(followed,"CONDITIONAL_PERSISTENT_CONCEPT_JUDGMENT")[0]
                classification=successor.values["branches"][0]["classifications"]["current"]["actual"]
                self.assertEqual(classification["status"],"UNRESOLVED")
                self.assertEqual(classification["possible_values"],(False,True))
                self.assertIn("VERSION_ASSUMPTION_RETRACTED",classification["uncertain"])

    def test_step_frontier_claim_records_adoption_without_claiming_consumers_ran(self):
        a,_=self.adopt("A");head=self.results(a)[0].result_id
        self.follow("B")
        from hcl.operators.persistent_concepts import compute_persistent
        with patch("hcl.operators.persistent_concepts.compute_persistent",wraps=compute_persistent) as execute:
            result,_=self.run_issue("D",ConceptAdoptionIssue("D",stream_id="institution",
                support_result_ids=(self.base.result_id,),version_labels=("revised",),expected_head=head),max_steps=2)
        self.assertEqual(result.status,"PARTIAL",result.diagnostics)
        self.assertEqual(execute.call_count,0)
        self.assertEqual([r.kind for r in self.results(result)],["CONCEPT_ADOPTION"])
        self.assertIn("Recorded the explicit concept adoption",result.answer)
        self.assertNotIn("consumers are revised",result.answer)
        self.assertNotIn("Conditional persistent concept revision",result.answer)
        self.assertTrue(any(d.code=="EXECUTION_STEP_BUDGET" for d in result.diagnostics))
        self.assertEqual(result.usage["mock_calls"],0)

    def test_wrapped_successor_and_cached_follow_never_cross_principal(self):
        from hcl.kernel.types import Principal,HCLFailure
        from hcl.runtime.execution_ledger import ExecutionLedger
        self.adopt("A")
        result,request=self.follow("B")
        successor=self.results(result,"CONDITIONAL_PERSISTENT_CONCEPT_JUDGMENT")[0]
        self.assertTrue(successor.result_id.startswith("concept-successor:"))
        bob=Principal(self.f.owner.tenant_id,"bob")
        shared=self.f.store.snapshot("s",bob,self.f.request.source_handles)
        self.assertEqual(dict(shared.source_versions),dict(successor.values["source_versions"]))
        ledger=ExecutionLedger(self.f.store)
        self.assertEqual(ledger.delivery_inferences(request,(successor.result_id,)),(successor,))
        with self.assertRaises(HCLFailure) as caught:
            ledger.delivery_inferences(replace(request,principal=bob),(successor.result_id,))
        self.assertIn(caught.exception.status,("DENIED","STALE_STATE"))
        foreign=HCL(self.f.store,principal=bob).run_sync(replace(request,principal=bob))
        self.assertEqual(foreign.status,"DENIED",foreign.diagnostics)
        self.assertFalse(foreign.answer or foreign.claim_records)
        replay=HCL(self.f.store,principal=self.f.owner).run_sync(request)
        self.assertEqual((replay.answer,replay.claim_records),(result.answer,result.claim_records))
