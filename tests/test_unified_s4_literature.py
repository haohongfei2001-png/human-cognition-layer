"""Ordinary HCL entry over injected proposals and actual narrative computation.

These are conditional offline fixtures, not evidence of model comprehension.
"""

import asyncio
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from hcl import HCL, ExecutionBudget, ExecutionIssue
from hcl.kernel.types import HCLFailure, Issue, Principal, TaskRequest, thaw
from hcl.memory.store import StateStore
from hcl.models.gateway import ModelGateway, OfflineModelPort
from hcl.runtime.context import ContextCompiler
from hcl.runtime.recovery import RecoveryManager
from hcl.semantics.literature_compiler import LiteratureCompiler, SCHEMA


class Crash(BaseException):
    pass


class LiteratureExecutionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "state.sqlite"
        self.owner = Principal("tenant", "alice")
        self.store = StateStore.sqlite(self.path, revision=True)
        self.store.create_session("s", self.owner, frozenset({"bob"}))
        self.text = "She arrived. Three days earlier, she left. The door, the door!"
        self.handle = self.store.put_source("s", self.owner, "book", self.text)
        self.budget = ExecutionBudget(
            max_mock_calls=20,
            max_output_bytes=200000,
            max_visible_output_tokens=200000,
            max_total_output_bytes=1048576,
            max_request_bytes=12000,
            max_context_tokens=12000,
            max_steps=64,
        )
        self.question = "Compare story and presentation."

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def request(self, **changes):
        value = TaskRequest(
            "literature",
            self.question,
            (self.handle,),
            "s",
            self.owner,
            budget=self.budget,
            issue=ExecutionIssue(
                "root", goals=(Issue("read", "literature.analyze", "book"),)
            ),
        )
        return replace(value, **changes)

    def parts(self):
        snapshot = self.store.snapshot("s", self.owner, (self.handle,))
        return ContextCompiler().chunks(
            snapshot,
            self.question,
            "literature_compile",
            self.budget,
            OfflineModelPort().describe(),
        )

    @staticmethod
    def candidate(chunk):
        segments = [s.segment_id for s in chunk.segments]
        return dict(
            schema=SCHEMA,
            assumptions=[],
            active_assumptions=[],
            frames=[],
            events=[],
            mentions=[],
            orders=[],
            queries=[],
            motifs=[],
            variants=[],
            comparisons=[],
            analogies=[],
            unmodeled_segments=segments,
        )

    def simple(self):
        chunks = self.parts()
        self.assertEqual(len(chunks), 1)
        chunk = chunks[0]
        s = chunk.segments[0]
        refs = [s.segment_id for s in chunk.segments]
        frame = dict(fragment=0, id="narrator")
        data = self.candidate(chunk)
        data["unmodeled_segments"] = []
        data["frames"] = [
            dict(
                id="narrator",
                parent=None,
                kind="NARRATION",
                narrator="proposed voice",
                focalizer=None,
                segment_ids=refs,
            )
        ]
        data["events"] = [
            dict(
                id=name, frame=frame, description=name, assumptions=[], segment_ids=refs
            )
            for name in ("arrive", "depart")
        ]

        def mention(name, quote):
            start = self.text.index(quote)
            s = next(
                s
                for s in chunk.segments
                if s.start <= start < start + len(quote) <= s.end
            )
            return dict(
                id=name,
                event=dict(fragment=0, id=name),
                frame=frame,
                anchor=dict(
                    segment_id=s.segment_id,
                    start=start,
                    end=start + len(quote),
                    quote=quote,
                ),
            )

        data["mentions"] = [mention("arrive", "arrived"), mention("depart", "left")]
        data["orders"] = [
            dict(
                id="earlier",
                left=dict(fragment=0, id="depart"),
                right=dict(fragment=0, id="arrive"),
                strict=True,
                assumptions=[],
                segment_ids=refs,
            )
        ]
        data["queries"] = [
            dict(
                id="chronology",
                left=dict(fragment=0, id="depart"),
                right=dict(fragment=0, id="arrive"),
                segment_ids=refs,
            )
        ]
        data["motifs"] = [dict(id="door", literal="door", segment_ids=refs)]
        start = self.text.index("door")
        s = next(s for s in chunk.segments if s.start <= start < start + 4 <= s.end)
        data["variants"] = [
            dict(
                id="remove-first",
                kind="DELETE",
                anchor=dict(
                    segment_id=s.segment_id, start=start, end=start + 4, quote="door"
                ),
                replacement="",
                segment_ids=refs,
            )
        ]
        return data

    def run_candidate(self, candidates=None, request=None):
        candidates = candidates or [self.simple()]
        responses = tuple(
            row if type(row) is str else json.dumps(row) for row in candidates
        )
        port = OfflineModelPort(responses=responses)
        client = HCL(
            self.store, principal=self.owner, gateway=ModelGateway(self.store, port)
        )
        self.last_result = client.run_sync(request or self.request())
        return self.last_result, port

    def values(self):
        ids = self.last_result.execution_receipt["result_ids"]
        return next(
            row.values
            for row in self.store.inferences("s", self.owner)
            if row.result_id in ids
        )

    def test_reflexive_story_query_preserves_event_assumption_and_withdrawal(self):
        data = self.simple()
        data["assumptions"] = data["active_assumptions"] = ["event-reading"]
        data["events"][0]["assumptions"] = ["event-reading"]
        data["queries"][0].update(
            left=dict(fragment=0, id="arrive"), right=dict(fragment=0, id="arrive")
        )
        result, _ = self.run_candidate([data])
        actual = next(
            v
            for v in self.store.inferences("s", self.owner)
            if v.result_id in result.execution_receipt["result_ids"]
        )
        query = actual.values["story_queries"][0]
        self.assertEqual(query["relation"], "SAME_EVENT")
        self.assertEqual(len(query["assumptions"]), 1)
        self.assertIn(query["assumptions"][0], result.answer)
        from hcl.runtime.answer import AnswerAssembler

        changed = thaw(actual.values)
        changed["story_queries"][0]["assumptions"] = []
        with self.assertRaises(HCLFailure):
            AnswerAssembler().compact_claim(replace(actual, values=changed))
        data["active_assumptions"] = []
        withdrawn, _ = self.run_candidate(
            [data], request=self.request(request_id="withdrawn")
        )
        actual = next(
            v
            for v in self.store.inferences("s", self.owner)
            if v.result_id in withdrawn.execution_receipt["result_ids"]
        )
        self.assertEqual(
            actual.values["story_queries"][0]["relation"], "EVENT_OR_FRAME_UNRESOLVED"
        )
        self.assertNotIn("SAME_EVENT", withdrawn.answer)

    def test_actual_story_reversed_presentation_exact_form_and_hypothetical_deletion(
        self,
    ):
        result, port = self.run_candidate()
        self.assertEqual(result.status, "PARTIAL", result.diagnostics)
        self.assertEqual(port.attempts, 1)
        value = self.values()
        self.assertEqual(value["story_queries"][0]["relation"], "BEFORE")
        self.assertEqual(value["discourse_edges"][0]["left"], (0, "arrive"))
        self.assertEqual(value["discourse_edges"][0]["right"], (0, "depart"))
        self.assertEqual(value["discourse_edges"][0]["relation"], "BEFORE")
        positions = next(iter(value["form"]["passages"][0]["motif_positions"].values()))
        self.assertEqual(len(positions), 2)
        variant = value["variants"][0]
        self.assertIs(variant["hypothetical"], True)
        self.assertEqual(
            len(next(iter(variant["form"]["passages"][0]["motif_positions"].values()))),
            1,
        )
        self.assertEqual(
            self.store.snapshot("s", self.owner, (self.handle,))
            .immutable_views["book"]
            .text,
            self.text,
        )
        self.assertIn("THEME_MECHANISM_COMPARISON_UNCOMPUTED", result.answer)
        self.assertEqual(result.usage["local_evaluations"], 4)
        replay, second = self.run_candidate()
        self.assertTrue(replay.execution_receipt["replayed"])
        self.assertEqual(second.attempts, 0)

    def test_uncertain_equality_and_withdrawn_order_are_not_after_or_second_event(self):
        base = self.simple()
        base["variants"] = []
        for case in ("equal", "withdrawn", "unknown"):
            data = deepcopy(base)
            if case == "equal":
                data["orders"][0]["strict"] = False
                reverse = deepcopy(data["orders"][0])
                reverse["id"] = "reverse"
                reverse["left"], reverse["right"] = reverse["right"], reverse["left"]
                data["orders"].append(reverse)
            elif case == "withdrawn":
                data["assumptions"] = ["narrator-is-trusted"]
                data["orders"][0]["assumptions"] = ["narrator-is-trusted"]
            else:
                data["orders"] = []
            result, _ = self.run_candidate(
                [data], replace(self.request(), request_id=case)
            )
            self.assertEqual(result.status, "PARTIAL", result.diagnostics)
            expected = (
                "SAME_TIME_IDENTITY_UNPROVED" if case == "equal" else "UNRESOLVED"
            )
            self.assertEqual(self.values()["story_queries"][0]["relation"], expected)

    def test_source_anchor_and_duplicate_fields_rejected_then_shared_repair(self):
        good = self.simple()
        bad = deepcopy(good)
        bad["mentions"][0]["anchor"]["quote"] = "fabricated"
        result, port = self.run_candidate([bad, good])
        self.assertEqual(result.status, "PARTIAL", result.diagnostics)
        self.assertEqual(port.attempts, 2)
        self.assertEqual(result.usage["repair_calls"], 1)
        self.assertEqual(
            json.loads(port.contexts[-1])["repair_obligation"]["field"],
            "original_anchor",
        )

    def long_candidates(self):
        self.text = "First event. " + ("x" * 8000) + "\nLate counterevidence."
        self.handle = self.store.put_source("s", self.owner, "book", self.text)
        chunks = self.parts()
        self.assertGreater(len(chunks), 1)
        candidates = []
        for chunk in chunks:
            d = self.candidate(chunk)
            refs = [s.segment_id for s in chunk.segments]
            d["frames"] = [
                dict(
                    id="same-label",
                    parent=None,
                    kind="NARRATION",
                    narrator="voice",
                    focalizer=None,
                    segment_ids=refs,
                )
            ]
            d["unmodeled_segments"] = []
            d["events"] = [
                dict(
                    id="same-label",
                    frame=dict(fragment=chunk.ordinal, id="same-label"),
                    description="local proposed event",
                    assumptions=[],
                    segment_ids=refs,
                )
            ]
            candidates.append(d)
        return chunks, candidates

    def test_full_packet_reading_keeps_same_names_separate_and_missing_bridge_unresolved(
        self,
    ):
        chunks, candidates = self.long_candidates()
        candidates[-1]["queries"] = [
            dict(
                id="different-events",
                left=dict(fragment=0, id="same-label"),
                right=dict(fragment=len(chunks) - 1, id="same-label"),
                segment_ids=[chunks[-1].segments[-1].segment_id],
            )
        ]
        candidates[-1]["orders"] = [
            dict(
                id="unproved-clock",
                left=dict(fragment=0, id="same-label"),
                right=dict(fragment=len(chunks) - 1, id="same-label"),
                strict=True,
                assumptions=[],
                segment_ids=[chunks[-1].segments[-1].segment_id],
            )
        ]
        result, port = self.run_candidate(candidates)
        self.assertEqual(result.status, "PARTIAL", result.diagnostics)
        self.assertEqual(port.attempts, len(chunks))
        value = self.values()
        self.assertEqual(value["coverage"]["read_fragments"], len(chunks))
        self.assertEqual(value["story_queries"][0]["relation"], "UNRESOLVED")
        self.assertIn("CROSS_FRAME_OR_EVENT_ORDER_UNRESOLVED", result.unresolved_issues)
        self.assertEqual(
            sum(r["end"] - r["start"] for r in value["coverage"]["read_regions"]),
            len(self.text),
        )
        self.assertFalse(value["semantic_certified"])

    def test_form_budget_frontier_is_partial_and_does_not_claim_unread_absence(self):
        result, _ = self.run_candidate(
            request=replace(
                self.request(), budget=replace(self.budget, max_local_evaluations=2)
            )
        )
        self.assertEqual(result.status, "PARTIAL", result.diagnostics)
        form = self.values()["form"]["passages"][0]
        self.assertEqual(form["scanned_characters"], 0)
        self.assertEqual(form["unread_range"], (0, len(self.text)))
        self.assertEqual(result.usage["local_evaluations"], 2)
        self.assertIn("FORM_PATTERN_PREPARATION_FRONTIER", result.unresolved_issues)

    def test_second_return_crash_reopens_without_replaying_prefix(self):
        chunks, candidates = self.long_candidates()
        request = self.request()
        owner = self.store.owner_id
        count = 0

        def fault(stage):
            nonlocal count
            if stage == "return_persisted":
                count += 1
                if count == 2:
                    raise Crash()

        with patch.object(self.store, "_checkpoint", fault), self.assertRaises(Crash):
            self.run_candidate(candidates, request)
        self.store.close()
        self.store = StateStore.sqlite(self.path)
        RecoveryManager(self.store).resume_execution(request, expected_owner_id=owner)
        result, port = self.run_candidate(candidates[2:] or ["unused"], request)
        self.assertEqual(result.status, "PARTIAL", result.diagnostics)
        self.assertEqual(port.attempts, len(chunks) - 2)
        self.assertEqual(result.usage["mock_calls"], len(chunks))

    def test_all_fragment_composition_is_not_equivalent_to_semantic_completeness(self):
        chunks, candidates = self.long_candidates()
        candidates[-1]["events"][0]["frame"] = dict(fragment=0, id="missing-frame")
        result, _ = self.run_candidate(candidates)
        self.assertEqual(result.status, "PARTIAL", result.diagnostics)
        self.assertIn("CROSS_FRAGMENT_REFERENCE_UNRESOLVED", result.answer)
        self.assertTrue(self.values()["coverage"]["supplied_scope_read"])
        self.assertEqual(
            self.values()["coverage"]["semantic_completeness"], "NOT_ESTABLISHED"
        )

    def test_late_anchored_order_revises_earlier_query_without_name_merging(self):
        chunks, base = self.long_candidates()
        root = dict(fragment=0, id="same-label")
        for data in base:
            data["events"][0][
                "frame"
            ] = root  # Explicit frame reference, not label matching.
        first = dict(fragment=0, id="same-label")
        last = dict(fragment=len(chunks) - 1, id="same-label")
        base[0]["queries"] = [
            dict(
                id="early-question",
                left=first,
                right=last,
                segment_ids=[chunks[0].segments[0].segment_id],
            )
        ]
        for case in ("no-clock", "late-clock"):
            data = deepcopy(base)
            if case == "late-clock":
                data[-1]["orders"] = [
                    dict(
                        id="late-revelation",
                        left=last,
                        right=first,
                        strict=True,
                        assumptions=[],
                        segment_ids=[chunks[-1].segments[-1].segment_id],
                    )
                ]
            result, port = self.run_candidate(
                data, replace(self.request(), request_id=case)
            )
            self.assertEqual(result.status, "PARTIAL", result.diagnostics)
            self.assertEqual(
                self.values()["story_queries"][0]["relation"],
                "AFTER" if case == "late-clock" else "UNRESOLVED",
            )
            self.assertEqual(port.attempts, len(chunks))

    def test_stream_budget_and_complete_result_replay_keep_delivery_permission(self):
        candidate = self.simple()
        request = self.request()
        port = OfflineModelPort(json.dumps(candidate))
        client = HCL(
            self.store, principal=self.owner, gateway=ModelGateway(self.store, port)
        )

        async def collect():
            return [event async for event in client.stream(request)]

        events = asyncio.run(collect())
        result = events[-1].result
        self.assertEqual(result.status, "PARTIAL", result.diagnostics)
        self.assertEqual(len(events), 2)
        self.store.set_readers("s", self.owner, "book", frozenset({"bob"}))
        denied = asyncio.run(collect())[-1].result
        self.assertEqual(denied.status, "DENIED")
        self.assertEqual(denied.answer, "")
        self.assertFalse(denied.claim_records)
        self.assertEqual(port.attempts, 1)
        self.assertNotIn("book", repr(denied.execution_receipt))

    def test_computed_and_committed_restart_reuse_checked_effects(self):
        candidate = self.simple()
        for seam in ("execution_computed", "execution_effects_committed"):
            request = replace(
                self.request(),
                request_id=seam,
                issue=ExecutionIssue(
                    "root", goals=(Issue(seam, "literature.analyze", "book"),)
                ),
            )
            owner = self.store.owner_id

            def fault(stage):
                if stage == seam:
                    raise Crash()

            with patch.object(self.store, "_checkpoint", fault), self.assertRaises(
                Crash
            ):
                self.run_candidate([candidate], request)
            self.store.close()
            self.store = StateStore.sqlite(self.path)
            RecoveryManager(self.store).resume_execution(
                request, expected_owner_id=owner
            )
            result, port = self.run_candidate(["no new proposal"], request)
            self.assertEqual(result.status, "PARTIAL", result.diagnostics)
            self.assertEqual(port.attempts, 0)
            self.assertEqual(result.usage["mock_calls"], 1)
            self.assertEqual(result.usage["local_evaluations"], 4)

    def test_exact_result_verifier_rejects_changed_form_story_coverage_or_variant(self):
        from hcl.runtime.answer import AnswerAssembler

        result, _ = self.run_candidate()
        inference = self.store.inferences("s", self.owner)[0]
        for field in ("form", "story", "coverage", "variant"):
            values = thaw(inference.values)
            if field == "form":
                values["form"]["passages"][0]["scanned_characters"] += 1
            elif field == "story":
                values["story_queries"][0]["relation"] = "AFTER"
            elif field == "coverage":
                values["coverage"]["supplied_scope_read"] = False
            else:
                values["variants"][0]["hypothetical"] = False
            with self.subTest(field=field), self.assertRaises(HCLFailure):
                AnswerAssembler().compact_claim(replace(inference, values=values))

    def test_compile_failure_never_publishes_partial_packet_as_whole_narrative(self):
        chunks, candidates = self.long_candidates()
        request = replace(
            self.request(),
            budget=replace(self.budget, max_mock_calls=1, max_feedback=0),
        )
        result, port = self.run_candidate(candidates, request)
        self.assertEqual(result.status, "BUDGET_EXHAUSTED", result.diagnostics)
        self.assertFalse(result.answer)
        self.assertFalse(result.claim_records)
        self.assertEqual(self.store.inferences("s", self.owner), ())
        self.assertEqual(port.attempts, 1)
        self.assertEqual(result.usage["held_mock_calls"], 1)

    def test_all_three_event_acyclic_orders_match_independent_permutation_oracle(self):
        from itertools import permutations, product
        from hcl.operators.literature import compute_narrative

        snapshot = self.store.snapshot("s", self.owner, (self.handle,))
        chunk = self.parts()[0]
        nodes = ("a", "b", "c")
        pairs = tuple((a, b) for a in nodes for b in nodes if a != b)
        base = self.simple()
        base["mentions"] = []
        base["motifs"] = []
        base["variants"] = []
        refs = [segment.segment_id for segment in chunk.segments]
        base["events"] = [
            dict(
                id=name,
                frame=dict(fragment=0, id="narrator"),
                description=name,
                assumptions=[],
                segment_ids=refs,
            )
            for name in nodes
        ]
        base["queries"] = [
            dict(
                id=a + b,
                left=dict(fragment=0, id=a),
                right=dict(fragment=0, id=b),
                segment_ids=refs,
            )
            for a, b in pairs
        ]
        count = 0
        for enabled in product((False, True), repeat=len(pairs)):
            edges = [pair for pair, yes in zip(pairs, enabled) if yes]
            legal = [
                order
                for order in permutations(nodes)
                if all(order.index(a) < order.index(b) for a, b in edges)
            ]
            if not legal:
                continue
            candidate = deepcopy(base)
            candidate["orders"] = [
                dict(
                    id=a + b,
                    left=dict(fragment=0, id=a),
                    right=dict(fragment=0, id=b),
                    strict=True,
                    assumptions=[],
                    segment_ids=refs,
                )
                for a, b in edges
            ]
            program = LiteratureCompiler().compose(
                snapshot, ((chunk, json.dumps(candidate)),), self.budget
            )
            computed = compute_narrative(program, {"book": self.text}, 33)
            for (a, b), row in zip(pairs, computed["story_queries"]):
                before = [order.index(a) < order.index(b) for order in legal]
                expected = (
                    "BEFORE"
                    if all(before)
                    else "AFTER" if not any(before) else "UNRESOLVED"
                )
                self.assertEqual(row["relation"], expected, (edges, a, b))
                count += 1
        self.assertEqual(count, 150)


if __name__ == "__main__":
    unittest.main()
