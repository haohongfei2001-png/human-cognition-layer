from dataclasses import replace
from pathlib import Path
import asyncio
import json
import tempfile
import unittest
from unittest.mock import patch

from hcl import HCL, ExecutionBudget, ExecutionIssue, RetrievalIssue, RetrievalQuery
from hcl.kernel.types import Principal, TaskRequest, thaw
from hcl.memory.store import StateStore
from hcl.models.gateway import ModelGateway, OfflineModelPort
from hcl.memory import codec


class RetrievalExecutionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "state.sqlite"
        self.store = StateStore.sqlite(self.path, revision=True)
        self.owner = Principal("tenant", "reader")
        self.store.create_session("s", self.owner, frozenset({"other"}))
        self.handle = self.store.put_source("s", self.owner, "book", "A witness supports the event.\n" + "The weather was mild.\n"*300 + "The witness was absent: denial of the event.\nAnother causal explanation exists.\n")
        self.query = RetrievalQuery(dict(support="witness supports event", challenge="absent denial", alternative="causal explanation"), max_hits_per_route=1)
        self.request = TaskRequest("retrieve", "What bears on the event?", (), "s", self.owner,
                                   budget=ExecutionBudget(max_mock_calls=0, max_output_bytes=65536),
                                   issue=ExecutionIssue("root", goals=(RetrievalIssue("search",query=self.query),)))

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def client(self):
        return HCL(self.store, principal=self.owner)

    def run_request(self, request=None, stream=False):
        request = request or self.request
        if stream:
            async def collect():
                return [event async for event in self.client().stream(request)]
            return asyncio.run(collect())[-1].result
        return self.client().run_sync(request)

    def test_entry_exact_packet_claim_and_restart_replay(self):
        result = self.run_request()
        self.assertEqual(result.status, "COMPLETED", result.diagnostics)
        self.assertIn("witness was absent", result.answer)
        self.assertNotIn("weather was mild", result.answer)
        self.assertIn("whole selected source scope read=False", result.answer)
        fields = result.claim_records[0].used_result_fields
        self.assertEqual([f.field for f in fields], ["retrieval"])
        self.assertEqual(result.usage["mock_calls"], 0)
        self.store.close(); self.store = StateStore.sqlite(self.path)
        replay = self.run_request(stream=True)
        self.assertEqual(replay.answer, result.answer)
        self.assertEqual(replay.claim_records, result.claim_records)
        self.assertTrue(replay.execution_receipt["replayed"])

    def test_frontier_is_partial_and_zero_budget_not_success(self):
        request = replace(self.request, issue=ExecutionIssue("root", goals=(RetrievalIssue("search",query=replace(self.query,max_characters=30)),)))
        result = self.run_request(request)
        self.assertEqual(result.status, "PARTIAL")
        self.assertIn("RETRIEVAL_CLOSURE_FRONTIER", result.unresolved_issues)
        self.assertIn("RETRIEVAL_CLOSURE_FRONTIER", result.answer)
        zero = replace(self.request, request_id="zero", budget=replace(self.request.budget, max_local_evaluations=0))
        self.assertEqual(self.run_request(zero).status, "BUDGET_EXHAUSTED")

    def test_current_revocation_blocks_complete_and_partial_replay(self):
        full = self.run_request()
        partial_request = replace(self.request, request_id="partial", issue=ExecutionIssue("root", goals=(RetrievalIssue("search",query=replace(self.query,max_characters=30)),)))
        self.assertEqual(self.run_request(partial_request).status, "PARTIAL")
        self.store.set_readers("s",self.owner,"book",frozenset({"other"}))
        for request in (self.request, partial_request):
            for stream in (False,True):
                denied = self.run_request(request, stream)
                self.assertEqual(denied.status, "DENIED")
                self.assertEqual(denied.answer, "")
                self.assertFalse(denied.claim_records)
                self.assertNotIn("witness", codec.dumps(denied).decode())

    def test_new_counterevidence_invalidates_only_search_scope(self):
        first = self.run_request()
        self.store.put_source("s",self.owner,"late","New denial: the witness was absent.")
        replay = self.run_request()
        self.assertEqual(replay.status, "STALE_STATE")
        self.assertFalse(replay.claim_records)
        current = self.run_request(replace(self.request,request_id="new"))
        self.assertEqual(current.status, "COMPLETED")
        view = current.claim_records[0].used_result_fields[0].value
        self.assertEqual(set(view["search_scope"]), {"book", "late"})
        bounded = replace(self.request,request_id="bounded",issue=ExecutionIssue("root",goals=(RetrievalIssue("search",query=replace(self.query,source_scope=("book",))),)))
        stable = self.run_request(bounded)
        self.store.put_source("s",self.owner,"irrelevant","Other material.")
        self.assertEqual(self.run_request(bounded).answer, stable.answer)

    def test_computed_and_committed_recovery_does_not_repeat_search_effect(self):
        from hcl.runtime.recovery import RecoveryManager
        class Crash(BaseException): pass
        for seam in ("execution_computed", "execution_effects_committed"):
            with self.subTest(seam=seam):
                request=replace(self.request,request_id=seam,issue=ExecutionIssue("root",goals=(RetrievalIssue(seam,query=self.query),)))
                old_owner=self.store.owner_id
                fired=False
                def crash(stage):
                    nonlocal fired
                    if stage==seam and not fired:
                        fired=True
                        raise Crash()
                with patch.object(self.store,"_checkpoint",crash),self.assertRaises(Crash):
                    self.run_request(request)
                self.store.close();self.store=StateStore.sqlite(self.path)
                RecoveryManager(self.store).resume_execution(request,expected_owner_id=old_owner)
                from hcl.operators.retrieval import RetrievalOperator
                with patch.object(RetrievalOperator,"run",side_effect=AssertionError("computed effect must not run twice")):
                    result=self.run_request(request,stream=True)
                self.assertEqual(result.status,"COMPLETED",result.diagnostics)
                self.assertEqual(result.usage["local_evaluations"],1)
                self.assertEqual(result.usage["mock_calls"],0)

    def test_unbound_retrieval_values_never_become_accepted_claims(self):
        from hcl.operators.retrieval import RetrievalOperator
        original=RetrievalOperator.run
        def changed(operator,snapshot,issue,budget):
            operation=original(operator,snapshot,issue,budget)
            value=operation.candidate_delta.new_inferences[0]
            projection=thaw(value.values['retrieval'])
            projection['packet']['segments'][0]['text']='UNCOMMITTED_PRIVATE_CANARY'
            value=replace(value,values=dict(retrieval=projection))
            return replace(operation,candidate_delta=replace(operation.candidate_delta,new_inferences=(value,)))
        with patch.object(RetrievalOperator,'run',changed):
            result=self.run_request()
        self.assertEqual(result.status,'FAILED')
        self.assertEqual(result.diagnostics[0].code,'RETRIEVAL_EFFECT_BINDING_MISMATCH')
        self.assertFalse(result.answer or result.claim_records)
        self.assertNotIn('UNCOMMITTED_PRIVATE_CANARY',codec.dumps(result).decode())
        self.assertEqual(self.store._db.execute('SELECT count(*) FROM inferences').fetchone()[0],0)

    def test_commit_race_locally_retrieves_again_without_model(self):
        peer=StateStore.sqlite(self.path)
        fired=False
        try:
            def checkpoint(stage):
                nonlocal fired
                if stage == "execution_computed" and not fired:
                    fired=True
                    peer.put_source("s", self.owner, "late", "New denial and other causal explanation.")
            with patch.object(self.store,"_checkpoint",checkpoint):
                result=self.run_request()
            self.assertEqual(result.status,"COMPLETED",result.diagnostics)
            self.assertEqual(result.usage["mock_calls"],0)
            self.assertEqual(result.usage["local_evaluations"],2)
            self.assertIn("late", result.claim_records[0].used_result_fields[0].value["search_scope"])
        finally:
            peer.close()

class RetrievalCompositionTests(unittest.TestCase):
    def test_actual_fol_uses_remote_packet_and_new_counterevidence_changes_result(self):
        from tests.test_unified_s21 import SemanticExecutionTests, atom, binary, unary
        from hcl.semantics.segments import SourceSegment, question_segments
        from hcl.memory.query_store import QueryStore
        with tempfile.TemporaryDirectory() as folder:
            store=StateStore.sqlite(Path(folder)/"state.sqlite",revision=True)
            owner=Principal("t","a");store.create_session("s",owner)
            store.put_source("s",owner,"source","If Ada is notified she attends.\n"+"Background weather detail.\n"*1500+"Ada is notified.\n")
            query=RetrievalQuery(dict(support="Ada notified attends",challenge="not attend denial",alternative="alternative cause"),max_hits_per_route=4)
            request=TaskRequest("initial","Does Ada attend?",(),"s",owner,budget=ExecutionBudget(max_mock_calls=1,max_feedback=0,max_request_bytes=16384,max_context_tokens=16384,max_output_bytes=131072,max_visible_output_tokens=131072,max_total_output_bytes=524288),
                                issue=ExecutionIssue("root",goals=(RetrievalIssue("reason",kind="logic.compare_semantic_readings",query=query),)))
            def execute(request, negative=False):
                snapshot=QueryStore(store).search("s",owner,query)
                f=SemanticExecutionTests();f.segments=tuple(SourceSegment(**row) for row in snapshot.query_views["0"]["packet"]["segments"])+question_segments(request.question)
                f.p,f.q=atom("received"),atom("attends")
                premises=[binary("implies",f.p,f.q),f.p]
                if negative: premises.append(unary("not",f.q))
                candidate=f.fixture([(premises,f.q)])
                candidate["entities"][0]["label"]="Ada"
                candidate["entities"][0]["segment_ids"]=[row.segment_id for row in f.segments if row.source_id == "source"]
                port=OfflineModelPort(json.dumps(candidate))
                result=HCL(store,principal=owner,gateway=ModelGateway(store,port)).run_sync(request)
                self.assertEqual(port.attempts,1)
                self.assertNotIn("Background weather detail",port.contexts[0])
                self.assertLess(len(port.contexts[0].encode()),16384)
                self.assertIn("retrieval_coverage",json.loads(port.contexts[0]))
                return result
            try:
                first=execute(request)
                self.assertEqual(first.status,"COMPLETED",first.diagnostics)
                self.assertIn("conditional label=True",first.answer)
                self.assertIn("whole selected source scope read=False",first.answer)
                self.assertIn("retrieval",{field.field for claim in first.claim_records for field in claim.used_result_fields})
                store.put_source("s",owner,"counter","A denial: Ada does not attend.\n")
                second=execute(replace(request,request_id="counterevidence"),True)
                self.assertEqual(second.status,"PARTIAL",second.diagnostics)
                self.assertIn("INCONSISTENT_PREMISES",second.answer)
                self.assertNotIn("conditional label=True",second.answer)
                replay=HCL(store,principal=owner).run_sync(request)
                self.assertEqual(replay.status,"STALE_STATE")
                self.assertFalse(replay.claim_records)
            finally:
                store.close()

    def test_actual_argument_graph_recursively_brings_recorded_attack(self):
        from tests.test_unified_s4_engine import ArgumentExecutionTests
        from hcl.memory.query_store import QueryStore
        fixture=ArgumentExecutionTests();fixture.setUp()
        try:
            result,_=fixture.run_candidate()
            self.assertEqual(result.status,"COMPLETED",result.diagnostics)
            inference=fixture.inference(result)
            source=fixture.store.snapshot("s",fixture.owner,(fixture.handle,)).immutable_views["text"]
            fixture.store.put_source("s",fixture.owner,"noise","Unrelated background.\n"*500)
            query=RetrievalQuery(dict(support="目击者",challenge="unseenword",alternative="unknownword"),max_hits_per_route=1,evidence_result_ids=(inference.result_id,))
            snapshot=QueryStore(fixture.store).search("s",fixture.owner,query)
            view=snapshot.query_views["0"]
            self.assertTrue(view["packet"]["recorded_nodes"])
            self.assertTrue(any(edge[2]=="CHALLENGES" for edge in view["packet"]["edges"]))
            self.assertTrue(view["coverage"]["recorded_closure_complete"])
            self.assertFalse(view["coverage"]["whole_source_read"])
            request=replace(fixture.request,request_id="graph-read",source_handles=(),issue=ExecutionIssue("root",goals=(RetrievalIssue("search",query=query),)))
            delivered=HCL(fixture.store,principal=fixture.owner).run_sync(request)
            self.assertEqual(delivered.status,"COMPLETED",delivered.diagnostics)
            self.assertNotIn("Unrelated background",delivered.answer)
            self.assertIn("乙否认该事件",delivered.answer)
        finally:
            fixture.tearDown()


if __name__ == "__main__":
    unittest.main()
