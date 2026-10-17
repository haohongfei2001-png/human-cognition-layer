"""M09 actually changes ordinary M11 answers; no supplied trajectory verdicts."""
import asyncio
from copy import deepcopy
from dataclasses import replace
import json
import unittest
from unittest.mock import patch

from hcl import HCL, ExecutionIssue
from hcl.kernel.types import HCLFailure, Issue, thaw
from hcl.memory import codec
from hcl.models.gateway import ModelGateway, OfflineModelPort
from hcl.runtime.answer import AnswerAssembler
from hcl.runtime.context import ContextCompiler
from hcl.semantics.literature_compiler import LiteratureCompiler, CHARACTER_SCHEMA
from tests import test_unified_s3_relationship as relationship
from tests import test_unified_s4_literature as literature


class NarrativeCharacterTests(unittest.TestCase):
    def setUp(self):
        self.f = relationship.RelationshipExecutionTests()
        self.f.setUp()
        self.store, self.owner = self.f.store, self.f.owner
        self.request = replace(self.f.request, question="Compare this character's conditional arc.",
            issue=ExecutionIssue("root", goals=(Issue("arc", "literature.analyze"),)),
            budget=replace(self.f.request.budget, max_local_evaluations=100000,
                max_mock_calls=20, max_output_bytes=1048576, max_visible_output_tokens=1048576,
                max_total_output_bytes=16777216, max_context_tokens=12000, max_request_bytes=12000, max_steps=64))
        self.snapshot = self.store.snapshot(self.request.session_id, self.owner, self.request.source_handles)
        self.chunk = ContextCompiler().chunks(self.snapshot, self.request.question, "literature_compile",
            self.request.budget, OfflineModelPort().describe())[0]

    def tearDown(self):
        self.f.tearDown()

    def candidate(self):
        data = literature.LiteratureExecutionTests.candidate(self.chunk)
        data.update(schema=CHARACTER_SCHEMA, character_arcs=[], unmodeled_segments=[])
        refs = [s.segment_id for s in self.chunk.segments]
        task = self.f.candidate()
        def bind(value):
            if isinstance(value, dict):
                for key, item in value.items():
                    if key == "segment_ids": value[key] = refs
                    else: bind(item)
            elif isinstance(value, list):
                for item in value: bind(item)
        bind(task)
        frame = dict(fragment=0, id="reading")
        data["frames"] = [dict(id="reading", parent=None, kind="INTERPRETATION", narrator="analyst",
            focalizer="b", segment_ids=refs)]
        episodes = task["models"][0]["affect"]["episodes"]
        data["events"] = [dict(id=e["id"], frame=frame, description="Declared character episode",
            assumptions=[], segment_ids=refs) for e in episodes]
        data["character_arcs"] = [dict(id="b-arc", source_id=task["models"][0]["mental"]["source_id"],
            actor="b", assumptions=[], bindings=[dict(episode_id=e["id"], event=dict(fragment=0,id=e["id"]),
            at=e["at"]) for e in episodes], task=task)]
        return data

    def run_candidate(self, candidate=None, *, request=None, stream=False):
        port = OfflineModelPort(responses=(json.dumps(candidate or self.candidate()),))
        client = HCL(self.store, principal=self.owner, gateway=ModelGateway(self.store, port))
        request = request or self.request
        if stream:
            async def collect():
                events = [event async for event in client.stream(request)]
                return events
            events = asyncio.run(collect())
            result = events[-1].result
        else:
            result = client.run_sync(request)
        self.assertIn(result.status, ("COMPLETED", "PARTIAL"), result.diagnostics)
        proof = next(r for r in self.store.inferences(request.session_id,self.owner)
            if r.result_id in result.execution_receipt["result_ids"] and r.kind=="CONDITIONAL_NARRATIVE_MODEL")
        return result, proof, port

    def test_actual_arc_answer_and_late_counterevidence(self):
        before, proof, _ = self.run_candidate()
        first=proof.values["character_arcs"][0]["values"]["models"][0]
        candidate=self.candidate()
        candidate["character_arcs"][0]["task"]["models"][0]["observations"][-1]["action"]="wait"
        after, changed, _=self.run_candidate(candidate,request=replace(self.request,request_id="late"))
        second=changed.values["character_arcs"][0]["values"]["models"][0]
        self.assertEqual(first["prediction_matrix"],second["prediction_matrix"])
        self.assertNotEqual(first["longitudinal"]["pareto_explored"],second["longitudinal"]["pareto_explored"])
        self.assertNotEqual(before.answer,after.answer)
        for text in ("Actual candidate trajectory", "evidence factors=", "constant safety priority with changing information", "CROSS_PACKET_CHARACTER_COMPOSITION_UNCOMPUTED", "Hypothetical future predictions"):
            self.assertIn(text,before.answer)
        self.assertNotIn("CHARACTER_MECHANISM_COMPOSITION_UNCOMPUTED",before.answer)
        self.assertTrue(any(t["change_points"] for t in second["preferred_forecasts"]))
        self.assertEqual(first["identity_narratives"],second["identity_narratives"])
        self.assertTrue(any(f.field=="character_arcs" for c in before.claim_records for f in c.used_result_fields))

    def test_unrelated_paragraph_and_discourse_do_not_change_arc(self):
        before,proof,_=self.run_candidate()
        candidate=self.candidate()
        candidate["events"].append(dict(id="unrelated",frame=dict(fragment=0,id="reading"),description="Unrelated paragraph",
            assumptions=[],segment_ids=[s.segment_id for s in self.chunk.segments]))
        after,changed,_=self.run_candidate(candidate,request=replace(self.request,request_id="unrelated"))
        self.assertEqual(proof.values["character_arcs"],changed.values["character_arcs"])

    def test_explicit_join_rejects_actor_source_time_frame_and_cross_packet(self):
        mutations=(lambda a:a.update(actor="a"),lambda a:a.update(source_id="other"),
            lambda a:a["bindings"][0].update(at=99),lambda a:a["bindings"][0]["event"].update(fragment=1),
            lambda a:a["bindings"].pop(),lambda a:a.update(assumptions=["undeclared"]))
        for mutate in mutations:
            candidate=self.candidate();mutate(candidate["character_arcs"][0])
            with self.assertRaises(HCLFailure):
                LiteratureCompiler().compile_fragment(self.snapshot,self.chunk,json.dumps(candidate),self.request.budget)

    def test_indirect_story_time_conflict_is_rejected(self):
        candidate=self.candidate();refs=[s.segment_id for s in self.chunk.segments]
        candidate["events"].append(dict(id="middle",frame=dict(fragment=0,id="reading"),description="middle",assumptions=[],segment_ids=refs))
        candidate["orders"]=[dict(id=str(i),left=dict(fragment=0,id=l),right=dict(fragment=0,id=r),strict=True,assumptions=[],segment_ids=refs)
            for i,(l,r) in enumerate((("episode-4","middle"),("middle","episode-1")))]
        with self.assertRaises(HCLFailure):
            LiteratureCompiler().compile_fragment(self.snapshot,self.chunk,json.dumps(candidate),self.request.budget)

    def test_forged_nested_actual_binding_and_resource_rejected(self):
        _,proof,_=self.run_candidate()
        for mutate in (lambda v:v["character_arcs"][0].update(actor="a"),
            lambda v:v["character_arcs"][0]["bindings"][0].update(at=77),
            lambda v:v["character_arcs"][0]["values"].update(execution_allowance=1),
            lambda v:v["character_arcs"][0].update(issues=[]),
            lambda v:v["character_arcs"][0]["values"]["models"][0]["longitudinal"].update(pareto_explored=[])):
            value=thaw(proof.values);mutate(value)
            if value==thaw(proof.values):continue
            with self.assertRaises(HCLFailure):AnswerAssembler()._claim(replace(proof,values=value))

    def test_bounded_work_and_replay(self):
        result,proof,port=self.run_candidate(request=replace(self.request,budget=replace(self.request.budget,max_local_evaluations=8)))
        self.assertLessEqual(result.usage["local_evaluations"],8)
        self.assertIn("NOT_ESTABLISHED",result.answer)
        self.assertIn("FRONTIER",result.answer)
        replay,again,port=self.run_candidate(request=replace(self.request,budget=replace(self.request.budget,max_local_evaluations=8)))
        self.assertEqual(port.attempts,0)
        self.assertEqual(codec.dumps(proof),codec.dumps(again))
        self.assertEqual(result.answer,replay.answer)

    def test_stream_matches_run_and_expression_budget_never_certifies_omitted_arc(self):
        streamed,proof,port=self.run_candidate(stream=True)
        replay,_,again=self.run_candidate()
        self.assertEqual(streamed.answer,replay.answer)
        self.assertEqual(again.attempts,0)
        small=replace(self.request,request_id="small-delivery",budget=replace(self.request.budget,max_visible_output_tokens=40))
        port=OfflineModelPort(responses=(json.dumps(self.candidate()),))
        result=HCL(self.store,principal=self.owner,gateway=ModelGateway(self.store,port)).run_sync(small)
        self.assertNotEqual(result.status,"COMPLETED")
        self.assertFalse(result.claim_records)
        self.assertNotIn("Actual candidate trajectory",result.answer)

    def test_duplicate_reports_share_factors_and_same_time_has_no_turn(self):
        _,proof,_=self.run_candidate()
        candidate=self.candidate();model=candidate["character_arcs"][0]["task"]["models"][0]
        duplicate=deepcopy(model["observations"][-1]);duplicate.update(id="repeat",context_id="reported-again")
        model["observations"].append(duplicate)
        _,changed,_=self.run_candidate(candidate,request=replace(self.request,request_id="duplicate"))
        old=proof.values["character_arcs"][0]["values"]["models"][0]["longitudinal"]
        new=changed.values["character_arcs"][0]["values"]["models"][0]["longitudinal"]
        self.assertEqual(old["evidence_factor_ids"],new["evidence_factor_ids"])
        self.assertTrue(all(t["path"][-1]==t["path"][-2] for t in new["trajectories"]))
        self.assertEqual({codec.canonical(thaw(t["profile"])) for t in old["trajectories"]},
                         {codec.canonical(thaw(t["profile"])) for t in new["trajectories"]})

    def test_returned_computed_and_committed_recovery_has_zero_resend(self):
        from hcl.memory.store import StateStore
        from hcl.runtime.recovery import RecoveryManager
        for seam in ("return_persisted","execution_computed","execution_effects_committed"):
            request=replace(self.request,request_id=seam,issue=ExecutionIssue("root",goals=(Issue(seam,"literature.analyze"),)))
            owner=self.store.owner_id;path=self.store.path
            def fault(stage):
                if stage==seam:raise literature.Crash()
            with patch.object(self.store,"_checkpoint",fault),self.assertRaises(literature.Crash):
                self.run_candidate(request=request)
            self.store.close();self.store=StateStore.sqlite(path)
            self.f.store=self.f.f.store=self.f.f.fixture.store=self.f.f.fixture.scene.store=self.store
            RecoveryManager(self.store).resume_execution(request,expected_owner_id=owner)
            result,proof,port=self.run_candidate(request=request)
            self.assertEqual(port.attempts,0)
            self.assertIn("Actual candidate trajectory",result.answer)
            self.assertEqual(result.usage["mock_calls"],1)

    def test_hypothetical_variant_keeps_original_character_evidence(self):
        _,proof,_=self.run_candidate()
        candidate=self.candidate();segment=self.chunk.segments[0]
        candidate["variants"]=[dict(id="hypothetical-change",kind="REPLACE",anchor=dict(segment_id=segment.segment_id,
            start=segment.start,end=segment.start+1,quote=segment.text[:1]),replacement="Changed character!",segment_ids=[segment.segment_id])]
        _,changed,_=self.run_candidate(candidate,request=replace(self.request,request_id="variant"))
        left=proof.values["character_arcs"][0]["values"]["models"][0]
        right=changed.values["character_arcs"][0]["values"]["models"][0]
        for field in ("longitudinal", "observations", "preferred_forecasts", "identity_narratives", "mechanisms"):
            self.assertEqual(left[field],right[field])
        self.assertEqual(proof.values["source_versions"],changed.values["source_versions"])

    def test_nested_and_binding_assumptions_are_delivered(self):
        candidate=self.candidate()
        candidate["assumptions"]=candidate["active_assumptions"]=["actor-alignment"]
        candidate["character_arcs"][0]["assumptions"]=["actor-alignment"]
        mental=candidate["character_arcs"][0]["task"]["models"][0]["mental"]
        mental["assumptions"].append("conditional-scene");mental["active_assumptions"].append("conditional-scene")
        result,proof,_=self.run_candidate(candidate)
        self.assertIn("conditional-scene",proof.assumption_environments)
        self.assertTrue(proof.values["character_arcs"][0]["binding_assumptions"])
        self.assertIn("binding assumptions=",result.answer)
        self.assertTrue(set(proof.values["character_arcs"][0]["binding_assumptions"]) <= set(proof.assumption_environments))

    def test_v1_cannot_smuggle_unverified_character_fields(self):
        _,proof,_=self.run_candidate()
        value=thaw(proof.values)
        value["inputs"]["program"]["schema"]="hcl-literature-composed-1"
        with self.assertRaises(HCLFailure):AnswerAssembler()._claim(replace(proof,values=value))

    def test_later_packet_clock_constraint_is_not_ignored(self):
        from hcl.semantics.narrative_characters import validate_arc_clock
        first=self.candidate();first["fragment"]=0
        second=dict(fragment=1,events=[],active_assumptions=[],orders=[dict(id="late-order",
            left=dict(fragment=0,id="episode-4"),right=dict(fragment=0,id="episode-1"),strict=True,assumptions=[])])
        with self.assertRaises(HCLFailure):
            validate_arc_clock(LiteratureCompiler(),[first,second],first["character_arcs"][0])
