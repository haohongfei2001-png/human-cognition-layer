"""Source-bound synthetic candidates execute real M03/M05/M07/M13/M14 through HCL."""

import asyncio
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from hcl import HCL, ExecutionBudget, ExecutionIssue
from hcl.kernel.types import Principal, TaskRequest, Issue, HCLFailure, thaw
from hcl.memory.store import StateStore
from hcl.models.gateway import ModelGateway, OfflineModelPort
from hcl.runtime.answer import AnswerAssembler
from hcl.runtime.recovery import RecoveryManager
from hcl.semantics.segments import segment_snapshot


def atom(name):
    return dict(op="atom",name=name)


class JudgmentExecutionTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.path=Path(self.tmp.name)/"state.sqlite"
        self.owner=Principal("tenant","alice")
        self.store=StateStore.sqlite(self.path, revision=True)
        self.store.create_session("s",self.owner,{"bob"})
        self.handle=self.store.put_source("s",self.owner,"scene",
            "宁负责通知演出风险。青告知宁场地存在风险。宁承诺在期限前完成核验，核验尚未完成。保护观众可减少伤害，但会损失便利。")
        self.norm=self.store.put_source("s",self.owner,"principles",
            "The analyst conditionally proposes care and convenience weights. A known risk creates a duty to protect; a conflicting liberty principle is disputed. The meeting is on Tuesday.")
        self.request=TaskRequest("judgment","应如何行动？请区分知情、机会、承诺与规范争议。",(self.handle,self.norm),"s",self.owner,
            budget=ExecutionBudget(max_mock_calls=1,max_feedback=0,max_local_evaluations=100000,
                max_request_bytes=1048576,max_context_tokens=1048576,max_output_bytes=1048576,
                max_total_output_bytes=8000000,max_visible_output_tokens=1048576),
            issue=ExecutionIssue("root",goals=(Issue("choice","judgment.evaluate"),)))

    def tearDown(self):
        self.store.close();self.tmp.cleanup()

    def candidate(self, request=None):
        from scripts.witness_unified_judgment import propose
        request=request or self.request
        return propose(self.store.snapshot("s",self.owner,request.source_handles),request.question)

    def run_candidate(self,candidate=None,request=None,stream=False):
        port=OfflineModelPort(json.dumps(candidate or self.candidate(request),ensure_ascii=False))
        client=HCL(self.store,principal=self.owner,gateway=ModelGateway(self.store,port))
        if stream:
            async def run(): return [e async for e in client.stream(request or self.request)]
            result=asyncio.run(run())[-1].result
        else: result=client.run_sync(request or self.request)
        self.last=result
        return result,port

    def inference(self):
        ids=self.last.execution_receipt["result_ids"]
        return next(r for r in self.store.inferences("s",self.owner) if r.result_id in ids)

    def decision(self): return self.inference().values["models"][0]["decisions"][0]

    def test_real_shared_facts_duty_and_recommendation_reach_answer(self):
        result,port=self.run_candidate()
        self.assertEqual(result.status,"PARTIAL",result.diagnostics)
        self.assertEqual(port.attempts,1)
        model=self.inference().values["models"][0]
        self.assertEqual(model["facts"]["knowledge"]["possible_values"],(True,))
        self.assertEqual(model["facts"]["promise"]["possible_values"],(True,))
        self.assertEqual(self.decision()["robust_across_frameworks"],("protect",))
        self.assertIn("recommended=('protect',)",result.answer)
        tradeoff=self.decision()["frameworks"][0]["branches"][0]["result"]["constraint_tradeoffs"][0]
        self.assertEqual(tradeoff["excluded_alternative"],"ignore")
        self.assertEqual(tradeoff["foregone_gains"][0]["foregone_value"],"8")
        self.assertTrue(any(f.field=="models" for c in result.claim_records for f in c.used_result_fields))

    def test_knowledge_revision_changes_duty_but_not_independent_person_or_meeting(self):
        first,_=self.run_candidate(); self.assertEqual(first.status,"PARTIAL",first.diagnostics)
        before=thaw(self.inference().values["models"][0])
        candidate=self.candidate(); event=candidate["models"][0]["mental"]["events"][0]
        for key in ("received_by","understood_by","trusted_by"): event[key]=[]
        result,_=self.run_candidate(candidate,replace(self.request,request_id="unknown-risk"))
        self.assertEqual(result.status,"PARTIAL",result.diagnostics)
        after=thaw(self.inference().values["models"][0])
        self.assertEqual(after["facts"]["knowledge"]["possible_values"],[False])
        self.assertEqual(self.decision()["robust_across_frameworks"],("ignore",))
        def query(model,qid):return next(q for q in model["cognition"]["actual"]["values"]["models"][0]["beliefs"] if q["query_id"]==qid)
        self.assertEqual({k:v for k,v in query(before,"qing-risk").items() if k != "witnesses"}, {k:v for k,v in query(after,"qing-risk").items() if k != "witnesses"})
        b=before["actual_argument"]["values"]["models"][0]; a=after["actual_argument"]["values"]["models"][0]
        self.assertEqual(next(q for q in b["queries"] if q["query_id"]=="meeting"),next(q for q in a["queries"] if q["query_id"]=="meeting"))

    def test_principle_priority_changes_choice_without_rewriting_cognition_or_promise(self):
        first,_=self.run_candidate();self.assertEqual(first.status,"PARTIAL",first.diagnostics)
        before=self.inference().values["models"][0]
        candidate=self.candidate(); candidate["models"][0]["argument"]["priorities"][0].update(better="liberty",worse="care-duty")
        result,_=self.run_candidate(candidate,replace(self.request,request_id="priority"))
        self.assertEqual(result.status,"PARTIAL",result.diagnostics)
        after=self.inference().values["models"][0]
        self.assertEqual(before["cognition"],after["cognition"])
        self.assertEqual(before["actual_interaction"],after["actual_interaction"])
        self.assertEqual(self.decision()["robust_across_frameworks"],("ignore",))

    def test_tampered_results_and_conditions_never_reach_delivery(self):
        result,_=self.run_candidate();self.assertEqual(result.status,"PARTIAL",result.diagnostics)
        original=self.inference()
        # Positive control: a persisted untouched certificate must pass before
        # any mutation can count as a successful rejection.
        AnswerAssembler()._claim(original)
        mutations=[lambda v:v["models"][0]["decisions"][0].update(robust_across_frameworks=["ignore"]),
                   lambda v:v["models"][0]["facts"]["knowledge"].update(possible_values=[False]),
                   lambda v:v["models"][0]["decisions"][0]["frameworks"][0]["origin"].update(declarer="authenticated owner"),
                   lambda v:v["models"][0]["actual_argument"]["values"]["models"][0]["queries"][0].update(positive_accepted=False),
                   lambda v:v["models"][0]["actual_interaction"].update(result_id="other"),
                   lambda v:next(iter(v["program"]["source_bindings"].values())).update(source_id="unauthorized",version=999),
                   lambda v:v["program"]["models"][0]["decisions"][0]["frameworks"][0]["origin"].update(declarer="forged adopter"),
                   lambda v:v["source_versions"].update(principles=999),
                   lambda v:v["local_model"]["domain_assumptions"].__setitem__(0,"forged condition"),
                   lambda v:v["local_model"].update(unmodeled_observations=[]),
                   lambda v:v["local_model"].update(version="forged")]
        for mutate in mutations:
            values=thaw(original.values);mutate(values)
            with self.assertRaises(HCLFailure):AnswerAssembler()._claim(replace(original,values=values))
        for kwargs in [dict(assumption_environments=()),dict(premise_ids=("scene",)),dict(counterevidence_ids=("forged",)),dict(rule_version="forged")]:
            with self.assertRaises(HCLFailure):AnswerAssembler()._claim(replace(original,**kwargs))

    def test_unknown_weights_do_not_silently_choose_uniform_tradeoff(self):
        candidate=self.candidate();frame=candidate["models"][0]["decisions"][0]["frameworks"][0]
        frame.update(weights=None,decision_rule="PARETO",norms=[])
        result,_=self.run_candidate(candidate)
        self.assertEqual(result.status,"PARTIAL",result.diagnostics)
        value=self.decision()["frameworks"][0]["branches"][0]["result"]
        self.assertEqual(value["pareto"],("ignore","protect"))
        self.assertEqual(value["recommended"],())
        self.assertEqual(value["scenario_scores"],{})
        self.assertIn("UNKNOWN_NOT_UNIFORM",result.answer)
        self.assertTrue(value["value_change_conditions"])

    def test_unknown_commitment_is_not_inferred_as_breach_or_absent_duty(self):
        candidate=self.candidate();m=candidate["models"][0]
        m["mental"]["variables"][1]["initial"]=None
        frame=m["decisions"][0]["frameworks"][0]
        frame["norms"][0].update(guard_fact_ids=["promise"],argument_query_id=None)
        result,_=self.run_candidate(candidate)
        self.assertEqual(result.status,"PARTIAL",result.diagnostics)
        fact=self.inference().values["models"][0]["facts"]["promise"]
        self.assertEqual(fact["possible_values"],(False,True))
        self.assertIn("NOT_JOINT_TRAJECTORIES",fact["actual"]["completion_scope"])
        branch=self.decision()["frameworks"][0]["branches"][0]
        self.assertEqual(branch["states"]["protect-known-risk"],"UNRESOLVED")
        self.assertEqual(self.decision()["robust_across_frameworks"],("protect",))
        self.assertEqual(branch["result"]["eligibility"][1]["status"],"PERMISSION_UNRESOLVED")

    def test_unknown_bound_fact_cannot_make_opposing_norm_win_by_absence(self):
        candidate=self.candidate();m=candidate["models"][0]
        m["mental"]["variables"][0].update(initial=None,observed_by=["ning","qing"])
        for key in ("received_by","understood_by","trusted_by"):m["mental"]["events"][0][key]=[]
        frame=m["decisions"][0]["frameworks"][0]
        frame["norms"][0]["guard_fact_ids"]=[]
        frame["decision_rule"]="MAXIMIN"
        result,_=self.run_candidate(candidate)
        self.assertEqual(result.status,"PARTIAL",result.diagnostics)
        model=self.inference().values["models"][0]
        self.assertEqual(model["facts"]["knowledge"]["possible_values"],(False,True))
        self.assertEqual(model["argument_dependency_gaps"]["duty"],("knowledge",))
        self.assertNotIn("meeting",model["argument_dependency_gaps"])
        self.assertEqual(self.decision()["frameworks"][0]["branches"][0]["states"]["protect-known-risk"],"UNRESOLVED")
        self.assertEqual(self.decision()["robust_across_frameworks"],("protect",))
        self.assertEqual(self.decision()["responsibility"][0]["status"],"UNRESOLVED_FACT_DEPENDENCY")

    def test_preferred_dispute_uses_joint_extensions_and_retains_dissent(self):
        candidate=self.candidate();candidate["models"][0]["argument"]["priorities"]=[]
        result,_=self.run_candidate(candidate)
        self.assertEqual(result.status,"PARTIAL",result.diagnostics)
        frame=self.decision()["frameworks"][0]
        self.assertEqual(len(frame["branches"]),2)
        self.assertEqual({b["basis"] for b in frame["branches"]},{"PREFERRED_CONDITIONAL"})
        self.assertEqual({tuple(b["result"]["recommended"]) for b in frame["branches"]},{("protect",),("ignore",)})
        self.assertEqual(frame["robust_recommended"],())

    def test_world_infeasible_high_reward_cannot_enter_frontier(self):
        candidate=self.candidate();m=candidate["models"][0]
        m["mental"]["plans"][0]["graph"]["actions"][1]["feasible"]=[]
        m["decisions"][0]["frameworks"][0]["norms"]=[]
        result,_=self.run_candidate(candidate)
        self.assertEqual(result.status,"PARTIAL",result.diagnostics)
        opportunity=self.inference().values["models"][0]["opportunities"]["choice"]
        self.assertEqual(opportunity["actual_plan"]["best_actions"],("ignore",))
        self.assertEqual(self.decision()["robust_across_frameworks"],("protect",))
        self.assertFalse(self.decision()["outcomes"][1]["world_feasible"])

    def test_later_message_does_not_backfill_action_time_knowledge(self):
        candidate=self.candidate();m=candidate["models"][0]
        m["mental"]["events"][0]["at"]=3;m["interaction"]["through"]=3
        result,_=self.run_candidate(candidate)
        self.assertEqual(result.status,"PARTIAL",result.diagnostics)
        self.assertEqual(self.inference().values["models"][0]["facts"]["knowledge"]["possible_values"],(False,))
        self.assertEqual(self.decision()["robust_across_frameworks"],("ignore",))

    def test_framework_withdrawal_does_not_retain_recommendation(self):
        candidate=self.candidate();candidate["models"][0]["decisions"][0]["frameworks"][0]["active_assumptions"]=[]
        result,_=self.run_candidate(candidate)
        self.assertEqual(result.status,"PARTIAL",result.diagnostics)
        frame=self.decision()["frameworks"][0]
        self.assertEqual(frame["status"],"FRAMEWORK_ASSUMPTION_RETRACTED")
        self.assertEqual(frame["robust_recommended"],())

    def test_exact_expected_scenario_and_missing_probabilities(self):
        data=self.candidate();m=data["models"][0];decision=m["decisions"][0]
        m["mental"]["variables"][0].update(initial=None,observed_by=["ning","qing"])
        m["mental"]["events"]=[]
        m["mental"]["active_assumptions"]=["interpretation"]
        actions=m["mental"]["plans"][0]["graph"]["actions"]
        actions[0]["transitions"]["clear"]="ignored"
        actions[1]["transitions"]["clear"]="protected"
        frame=decision["frameworks"][0];frame.update(norms=[],weights=dict(care="1/2",convenience="1/2"))
        result,_=self.run_candidate(data)
        self.assertEqual(self.decision()["frameworks"][0]["status"],"EXPECTED_PROBABILITIES_UNSPECIFIED")
        self.assertFalse(self.decision()["robust_across_frameworks"])
        decision["scenarios"]=[dict(id="declared",distribution=dict(risk="1/3",clear="2/3"),segment_ids=decision["segment_ids"])]
        result,_=self.run_candidate(data,replace(self.request,request_id="explicit-probabilities"))
        self.assertEqual(result.status,"PARTIAL",result.diagnostics)
        branch=self.decision()["frameworks"][0]["branches"][0]["result"]
        self.assertEqual(branch["scenario_scores"]["protect"]["declared"],"13/3")
        self.assertEqual(branch["scenario_scores"]["ignore"]["declared"],"14/3")
        self.assertEqual(branch["recommended"],("ignore",))

    def test_weights_change_choice_without_rewriting_upstream_facts(self):
        data=self.candidate();frame=data["models"][0]["decisions"][0]["frameworks"][0];frame["norms"]=[]
        self.run_candidate(data);before=thaw(self.inference().values["models"][0])
        self.assertEqual(self.decision()["robust_across_frameworks"],("ignore",))
        frame["weights"]=dict(care="3/4",convenience="1/4")
        self.run_candidate(data,replace(self.request,request_id="care-weights"));after=thaw(self.inference().values["models"][0])
        self.assertEqual(self.decision()["robust_across_frameworks"],("protect",))
        for field in ("cognition","actual_interaction","facts","opportunities","actual_argument"):
            self.assertEqual(before[field],after[field])

    def test_revised_principle_source_recomputes_and_old_dependency_is_stale(self):
        data=self.candidate();self.run_candidate(data)
        before=self.inference().values["models"][0]
        self.norm=self.store.put_source("s",self.owner,"principles","The revised conditional principle prioritizes liberty over the duty. Care and convenience retain their declared values.")
        stale,_=self.run_candidate(data)
        self.assertFalse(stale.answer)
        request=replace(self.request,request_id="new-principle",source_handles=(self.handle,self.norm))
        revised=self.candidate(request)
        revised["models"][0]["argument"]["priorities"][0].update(better="liberty",worse="care-duty")
        result,_=self.run_candidate(revised,request)
        self.assertEqual(result.status,"PARTIAL",result.diagnostics)
        result_id=result.execution_receipt["result_ids"][0]
        row=self.store._db.execute("SELECT * FROM inferences WHERE result_id=?",(result_id,)).fetchone()
        self.store._validate_inference_delivery("s",self.owner,(dict(row),))
        actual=self.store._get_object(row["object_hash"])
        after=actual.values["models"][0]
        self.assertEqual(after["decisions"][0]["robust_across_frameworks"],("ignore",))
        for key in ("knowledge","control","promise"):
            self.assertEqual(before["facts"][key]["possible_values"],after["facts"][key]["possible_values"])
        self.assertEqual(actual.values["source_versions"]["principles"],2)

    def test_budget_between_frameworks_retains_only_qualified_prefix(self):
        data=self.candidate();frames=data["models"][0]["decisions"][0]["frameworks"]
        self.run_candidate(data);one_work=self.inference().values["local_evaluations"]
        second=deepcopy(frames[0]);second["id"]="second";second["norms"]=[];frames.append(second)
        request=replace(self.request,request_id="between-frames",budget=replace(self.request.budget,max_local_evaluations=one_work+1))
        result,_=self.run_candidate(data,request)
        self.assertEqual(result.status,"PARTIAL",result.diagnostics)
        decision=self.decision()
        self.assertEqual(decision["status"],"UNCOMPUTED")
        self.assertEqual(decision["frameworks"][0]["status"],"COMPUTED")
        self.assertFalse(decision["robust_across_frameworks"])
        self.assertLessEqual(result.usage["local_evaluations"],one_work+1)

    def test_compile_rejects_oracles_authority_question_facts_and_wrong_actor(self):
        from hcl.semantics.segments import question_segments
        for index,mutate in enumerate([
            lambda m:m.update(recommended=["ignore"]),
            lambda m:m["argument"].update(frame_kind="COUNTERFACTUAL"),
            lambda m:m["decisions"][0]["frameworks"][0]["origin"].update(kind="USER_ADOPTED"),
            lambda m:m["facts"][0].update(segment_ids=[question_segments(self.request.question)[0].segment_id]),
            lambda m:m["decisions"][0]["frameworks"][0]["weights"].update(care=True),
            lambda m:m["mental"]["queries"][0]["formula"].update(agent="qing"),
            lambda m:m["mental"]["queries"][0].update(at=3),
            lambda m:m["mental"]["plans"][0]["graph"].update(horizon=2),
            lambda m:m["decisions"][0].update(scenarios=[dict(id="bad",distribution={"risk":"-1","clear":"2"},segment_ids=m["decisions"][0]["segment_ids"])]),
        ]):
            candidate=self.candidate();mutate(candidate["models"][0])
            result,_=self.run_candidate(candidate,replace(self.request,request_id="invalid"+str(index)))
            self.assertEqual(result.status,"INVALID_REQUEST",result.diagnostics)
            self.assertFalse(result.claim_records)

    def test_exhausted_prefix_never_claims_complete_recommendation(self):
        for budget in (1,5,15,25,40):
            request=replace(self.request,request_id="budget"+str(budget),budget=replace(self.request.budget,max_local_evaluations=budget))
            result,_=self.run_candidate(request=request)
            self.assertEqual(result.status,"PARTIAL",result.diagnostics)
            self.assertLessEqual(result.usage["local_evaluations"],budget)
            for decision in self.inference().values["models"][0]["decisions"]:
                if decision["status"]=="UNCOMPUTED":
                    self.assertEqual(decision["robust_across_frameworks"],())

    def test_run_stream_reopen_exact_replay_and_source_version_rejection(self):
        data=self.candidate();result,port=self.run_candidate(data,stream=True)
        self.assertEqual(result.status,"PARTIAL",result.diagnostics)
        self.assertEqual(port.attempts,1)
        self.store.close();self.store=StateStore.sqlite(self.path)
        replay,port=self.run_candidate(stream=True)
        self.assertEqual(replay.answer,result.answer);self.assertEqual(port.attempts,0)
        self.store.put_source("s",self.owner,"principles","Revised source principles contradict the old priority.")
        replay,port=self.run_candidate(data,self.request)
        self.assertIn(replay.status,("STALE_STATE","DENIED"))
        self.assertFalse(replay.answer)

    def test_returned_computed_committed_recovery_never_resends(self):
        from hcl.operators.local_model import LocalModelOperator
        class Crash(BaseException):pass
        for seam in ("return_persisted","execution_computed","execution_effects_committed"):
            request=replace(self.request,request_id=seam,issue=ExecutionIssue("root",goals=(Issue(seam,"judgment.evaluate"),)))
            data=self.candidate();owner=self.store.owner_id;fired=False
            def stop(stage):
                nonlocal fired
                if stage==seam and not fired:fired=True;raise Crash()
            with patch.object(self.store,"_checkpoint",side_effect=stop),self.assertRaises(Crash):
                self.run_candidate(data,request)
            self.assertTrue(fired)
            self.store.close();self.store=StateStore.sqlite(self.path)
            RecoveryManager(self.store).resume_execution(request,expected_owner_id=owner)
            if seam=="return_persisted":result,port=self.run_candidate(data,request)
            else:
                with patch.object(LocalModelOperator,"run",side_effect=AssertionError("accepted effect cannot recompute")):
                    result,port=self.run_candidate(data,request)
            self.assertEqual(result.status,"PARTIAL",result.diagnostics);self.assertEqual(port.attempts,0)

    def test_secondary_acl_revocation_and_unknown_send_remain_closed(self):
        class Crash(BaseException):pass
        data=self.candidate();self.run_candidate(data)
        self.store.set_readers("s",self.owner,"principles",{"bob"})
        replay,port=self.run_candidate(data)
        self.assertEqual(replay.status,"DENIED");self.assertFalse(replay.answer);self.assertEqual(port.attempts,0)
        self.store.set_readers("s",self.owner,"principles",{"alice"})
        request=replace(self.request,request_id="unknown")
        def stop(stage):
            if stage=="send_started":raise Crash()
        with patch.object(self.store,"_checkpoint",side_effect=stop),self.assertRaises(Crash):self.run_candidate(data,request)
        owner=self.store.owner_id;self.store.close();self.store=StateStore.sqlite(self.path)
        with self.assertRaises(HCLFailure):RecoveryManager(self.store).resume_execution(request,expected_owner_id=owner)
        replay,port=self.run_candidate(data,request)
        self.assertIsNone(replay.usage["mock_calls"]);self.assertEqual(replay.usage["held_mock_calls"],1);self.assertEqual(port.attempts,0)


if __name__=="__main__": unittest.main()
