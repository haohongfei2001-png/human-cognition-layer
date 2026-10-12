"""Long exact Unicode evidence, conservative serialized capacity and coverage."""

from dataclasses import replace
import json
import unittest

from hcl.kernel.types import Issue
from hcl.models.gateway import OfflineModelPort
from hcl.runtime.context import ContextCompiler
from hcl.semantics.segments import segment_snapshot
from tests import test_unified_s23 as graph_fixtures


class ContextExecutionTests(graph_fixtures.ExecutionGraphTests):
    def test_large_unicode_source_is_all_processed_including_late_counterevidence(self):
        text = ("🧪中文证据保持逐字完整。" * 1600) + "最后反证：张三不出席。"
        self.assertGreater(len(text.encode()), 36000)
        self.handle = self.store.put_source("s", self.owner, "source", text)
        snapshot = self.store.snapshot("s", self.owner, (self.handle,))
        budget = replace(
            self.budget,
            max_request_bytes=12000,
            max_context_tokens=12000,
            max_mock_calls=32,
            max_total_output_bytes=2097152,
            max_local_evaluations=100,
            max_steps=128,
        )
        chunks = ContextCompiler().chunks(
            snapshot, self.question, "semantic_compile", budget, OfflineModelPort().describe()
        )
        self.assertGreater(len(chunks), 2)
        self.assertEqual("".join(s.text for c in chunks for s in c.segments), text)
        question = tuple(s for s in segment_snapshot(snapshot, self.question) if s.kind == "QUESTION")
        responses = tuple(
            json.dumps(
                self.candidate(snapshot, (*c.segments, *question), negative=i == len(chunks) - 1),
                ensure_ascii=False,
            )
            for i, c in enumerate(chunks)
        )
        result, port = self.run_request(self.semantic_request(budget=budget), responses)
        self.assertEqual(result.status, "PARTIAL", result.diagnostics)
        self.assertIn("CROSS_CHUNK_COMPOSITION_UNPROVED", result.unresolved_issues)
        self.assertEqual(port.attempts, len(chunks))
        self.assertTrue(all(len(wire.encode()) <= 12000 for wire in port.contexts))
        self.assertIn("最后反证", port.contexts[-1])
        self.assertIn("label=False", result.answer)
        self.assertIn("label=True", result.answer)
        self.assertEqual(
            self.store.snapshot("s", self.owner, (self.handle,)).immutable_views["source"].text, text
        )
        self.assertEqual(len(self.store.inferences("s", self.owner)), len(chunks))

    def test_call_capacity_cannot_silently_drop_late_source_chunks(self):
        text = "证据。" * 12000 + "最后反证。"
        self.handle = self.store.put_source("s", self.owner, "source", text)
        snapshot = self.store.snapshot("s", self.owner, (self.handle,))
        budget = replace(self.budget, max_request_bytes=12000, max_context_tokens=12000, max_mock_calls=1)
        chunks = ContextCompiler().chunks(
            snapshot, self.question, "semantic_compile", budget, OfflineModelPort().describe()
        )
        question = tuple(s for s in segment_snapshot(snapshot, self.question) if s.kind == "QUESTION")
        response = json.dumps(self.candidate(snapshot, (*chunks[0].segments, *question)))
        result, port = self.run_request(self.semantic_request(budget=budget), (response,))
        self.assertEqual(port.attempts, 1)
        self.assertEqual(result.status, "PARTIAL")
        self.assertTrue(any(d.code == "MOCK_CALL_BUDGET" for d in result.diagnostics))
        self.assertIn("CROSS_CHUNK_COMPOSITION_UNPROVED", result.unresolved_issues)

    def test_context_capacity_is_checked_before_any_reservation(self):
        request = self.semantic_request(budget=replace(self.budget, max_context_tokens=100))
        result, port = self.run_request(request, (json.dumps(self.candidate()),))
        self.assertEqual(result.status, "BUDGET_EXHAUSTED")
        self.assertEqual(result.diagnostics[0].code, "CONTEXT_CONTRACT_CAPACITY")
        self.assertEqual(port.attempts, 0)
        self.assertEqual(self.store._db.execute("SELECT count(*) FROM calls").fetchone()[0], 0)

    def test_total_request_budget_is_shared_between_independent_branches(self):
        goals = (
            Issue("a", "logic.compare_semantic_readings", "source"),
            Issue("b", "logic.compare_semantic_readings", "source"),
        )
        request = self.request(goals, budget=replace(self.budget, max_total_request_bytes=10000))
        result, port = self.run_request(
            request, (json.dumps(self.candidate()), json.dumps(self.candidate()))
        )
        self.assertEqual(port.attempts, 1)
        self.assertEqual(result.status, "PARTIAL")
        self.assertEqual(result.diagnostics[0].code, "TOTAL_REQUEST_BYTES_EXCEEDED")


def load_tests(loader, tests, pattern):
    return unittest.TestSuite(
        ContextExecutionTests(name) for name in ContextExecutionTests.__dict__ if name.startswith("test_")
    )
