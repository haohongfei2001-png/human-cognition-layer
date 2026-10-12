"""Independent permutation/position checks and ordinary narrative consumption."""

import asyncio
from copy import deepcopy
from dataclasses import replace
from hashlib import sha256
import itertools
import json
import random
import unittest

from hcl import HCL
from hcl.kernel.types import HCLFailure, thaw, freeze
from hcl.memory.store import StateStore
from hcl.models.gateway import ModelGateway, OfflineModelPort
from hcl.operators.narrative_variants import reorder_text, reorder_discourse
from hcl.runtime.answer import AnswerAssembler
from tests import test_unified_s4_literature as literature


def parts_of(chunks):
    result, start = [], 0
    for i, text in enumerate(chunks):
        result.append(
            dict(segment_id=str(i), start=start, end=start + len(text), quote=text)
        )
        start += len(text)
    return result


def mention(name, start, end):
    return dict(
        fragment=0,
        mention_id=name,
        event=dict(fragment=0, id=name),
        frame=dict(fragment=0, id="narrator"),
        source_id="book",
        anchor=dict(segment_id="original", start=start, end=end, quote=""),
        attribution_resolved=True,
    )


class ReorderMathTests(unittest.TestCase):
    def test_independent_permutation_and_position_oracle(self):
        rng = random.Random(101213)
        for _ in range(150):
            chunks = [
                "".join(rng.choice("a文🙂!?\n") for _ in range(rng.randint(1, 8)))
                for i in range(4)
            ]
            text, parts = "".join(chunks), parts_of(chunks)
            order = rng.sample(range(4), 4)
            changed, offsets = reorder_text(text, parts, order)
            self.assertEqual(changed, "".join(chunks[i] for i in order))
            self.assertEqual(sorted(text), sorted(changed))
            ms = [mention(str(i), p["start"], p["end"]) for i, p in enumerate(parts)]
            actual = reorder_discourse(ms, "book", offsets, 16384)
            self.assertEqual(
                actual["status"], "COMPLETE_DECLARED_OCCURRENCE_COMPARISON"
            )
            for projected in actual["projected_mentions"]:
                index = int(projected["mention"][1])
                expected = sum(len(chunks[i]) for i in order[: order.index(index)])
                self.assertEqual(
                    projected["generated_range"],
                    (expected, expected + len(chunks[index])),
                )
                self.assertEqual(
                    changed[expected : expected + len(chunks[index])], chunks[index]
                )
            wanted = {
                (str(i), str(j))
                for i, j in itertools.combinations(range(4), 2)
                if order.index(i) > order.index(j)
            }
            got = {(r["left"][1], r["right"][1]) for r in actual["changed_pairs"]}
            self.assertEqual(got, wanted)
            self.assertTrue(
                all(
                    r["original_relation"] == "BEFORE"
                    and r["hypothetical_relation"] == "AFTER"
                    for r in actual["changed_pairs"]
                )
            )

    def test_original_characters_exact_even_for_repeated_or_unicode_pieces(self):
        text = "前🙂前🙂尾"
        parts = parts_of(["前🙂", "前🙂", "尾"])
        changed, trace = reorder_text(text, parts, [1, 0, 2])
        self.assertEqual(changed, text)
        self.assertEqual([r["part_index"] for r in trace["pieces"]], [1, 0, 2])
        # Identical surface text does not merge provenance/occurrence identities.
        actual = reorder_discourse(
            [mention("first", 0, 2), mention("second", 2, 4)], "book", trace, 16384
        )
        self.assertEqual(len(actual["changed_pairs"]), 1)

    def test_invalid_permutation_gaps_overlaps_and_unoriginal_words_rejected(self):
        for mode in (
            "duplicate",
            "bool",
            "missing",
            "gap",
            "overlap",
            "quote",
            "reverse-source",
        ):
            parts = parts_of(["abc", "def", "ghi"])
            order = [2, 0, 1]
            if mode == "duplicate":
                order = [0, 0, 2]
            elif mode == "bool":
                order = [False, 1, 2]
            elif mode == "missing":
                order = [1, 0]
            elif mode == "gap":
                parts[1]["start"] += 1
                parts[1]["quote"] = "ef"
            elif mode == "overlap":
                parts[1]["start"] -= 1
                parts[1]["quote"] = "cdef"
            elif mode == "quote":
                parts[1]["quote"] = "XYZ"
            else:
                parts.reverse()
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                reorder_text("abcdefghi", parts, order)

    def test_cut_crossing_and_budget_exhaustion_remain_unresolved(self):
        changed, trace = reorder_text("abcdef", parts_of(["ab", "cd", "ef"]), [2, 1, 0])
        ms = [mention("first", 0, 1), mention("crossing", 1, 3), mention("last", 5, 6)]
        full = reorder_discourse(ms, "book", trace, 16384)
        self.assertEqual(full["status"], "PARTIAL")
        self.assertEqual(
            full["unresolved_mentions"][0]["reason"], "MENTION_CROSSES_REORDER_CUT"
        )
        self.assertEqual(len(full["changed_pairs"]), 1)
        for budget in range(full["work"]):
            value = reorder_discourse(ms, "book", trace, budget)
            self.assertEqual(value["work"], budget)
            self.assertIn("REORDER_DISCOURSE_WORK_FRONTIER", value["frontier"])
            self.assertTrue(
                all(pair in full["changed_pairs"] for pair in value["changed_pairs"])
            )


class ReorderExecutionTests(unittest.TestCase):
    def fixture(self):
        f = literature.LiteratureExecutionTests()
        f.setUp()
        self.addCleanup(f.tearDown)
        candidate = f.simple()
        parts = [
            dict(segment_id=s.segment_id, start=s.start, end=s.end, quote=s.text)
            for s in f.parts()[0].segments
        ]
        self.assertGreaterEqual(len(parts), 2)
        order = list(range(len(parts)))
        order[0], order[1] = order[1], order[0]
        candidate["variants"] = [
            dict(
                id="exchange-presentations",
                kind="REORDER",
                parts=parts,
                order=order,
                segment_ids=[p["segment_id"] for p in parts],
            )
        ]
        return f, candidate

    @staticmethod
    def result(f, delivery):
        return next(
            r
            for r in f.store.inferences("s", f.owner)
            if r.result_id in delivery.execution_receipt["result_ids"]
        )

    def test_reorder_changes_discourse_not_story_and_replays_run_stream(self):
        for stream in (False, True):
            f, candidate = self.fixture()
            original = f.store.snapshot("s", f.owner, (f.handle,))
            request = f.request()
            if stream:
                port = OfflineModelPort(json.dumps(candidate))
                client = HCL(
                    f.store, principal=f.owner, gateway=ModelGateway(f.store, port)
                )

                async def run():
                    return [event async for event in client.stream(request)]

                delivery = asyncio.run(run())[-1].result
            else:
                delivery, port = f.run_candidate([candidate])
            self.assertEqual(delivery.status, "PARTIAL", delivery.diagnostics)
            self.assertEqual(port.attempts, 1)
            inference = self.result(f, delivery)
            self.assertEqual(inference.values["story_queries"][0]["relation"], "BEFORE")
            variant = inference.values["variants"][0]
            self.assertEqual(len(variant["discourse_contrast"]["changed_pairs"]), 1)
            self.assertIn("BEFORE -> AFTER", delivery.answer)
            self.assertIn("chronology is unchanged", delivery.answer)
            expected, trace = reorder_text(
                f.text,
                candidate["variants"][0]["parts"],
                candidate["variants"][0]["order"],
            )
            self.assertEqual(
                variant["variant_sha256"], sha256(expected.encode()).hexdigest()
            )
            self.assertEqual(
                thaw(variant["offset_map"]),
                thaw(freeze(trace)),
            )
            self.assertEqual(
                dict(original.immutable_views),
                dict(f.store.snapshot("s", f.owner, (f.handle,)).immutable_views),
            )
            f.store.close()
            f.store = StateStore.sqlite(f.path)
            replay, port = f.run_candidate([candidate])
            self.assertEqual(replay.answer, delivery.answer)
            self.assertEqual(port.attempts, 0)
            f.store.set_readers("s", f.owner, "book", {"bob"})
            denied, port = f.run_candidate([candidate])
            self.assertEqual(denied.status, "DENIED")
            self.assertFalse(denied.answer or denied.claim_records)
            self.assertEqual(port.attempts, 0)

    def test_each_durable_checkpoint_recovers_the_same_generated_contrast(self):
        from unittest.mock import patch
        from hcl.runtime.recovery import RecoveryManager
        from hcl.operators.local_model import LocalModelOperator

        for seam in (
            "return_persisted",
            "execution_computed",
            "execution_effects_committed",
        ):
            f, candidate = self.fixture()
            owner = f.store.owner_id

            def crash(stage):
                if stage == seam:
                    raise literature.Crash()

            with patch.object(
                f.store, "_checkpoint", side_effect=crash
            ), self.assertRaises(literature.Crash):
                f.run_candidate([candidate])
            f.store.close()
            f.store = StateStore.sqlite(f.path)
            RecoveryManager(f.store).resume_execution(
                f.request(), expected_owner_id=owner
            )
            if seam == "return_persisted":
                result, port = f.run_candidate([candidate])
            else:
                with patch.object(
                    LocalModelOperator,
                    "run",
                    side_effect=AssertionError("accepted effect cannot recompute"),
                ):
                    result, port = f.run_candidate([candidate])
            self.assertEqual(result.status, "PARTIAL", result.diagnostics)
            self.assertEqual(port.attempts, 0)
            self.assertIn("BEFORE -> AFTER", result.answer)

    def test_invalid_sources_or_permutation_never_commit(self):
        f, candidate = self.fixture()
        for mode in (
            "duplicate",
            "quote",
            "question",
            "gap",
            "replacement",
            "invalid-row",
        ):
            bad = deepcopy(candidate)
            v = bad["variants"][0]
            if mode == "duplicate":
                v["order"][0] = v["order"][1]
            elif mode == "quote":
                v["parts"][0]["quote"] = "invented sentence"
            elif mode == "question":
                v["parts"][0]["segment_id"] = "QUESTION"
            elif mode == "gap":
                v["parts"][1]["start"] += 1
                v["parts"][1]["quote"] = v["parts"][1]["quote"][1:]
            elif mode == "invalid-row":
                bad["variants"] = [[]]
            else:
                v["replacement"] = "not permitted"
            result, port = f.run_candidate(
                [bad],
                request=f.request(
                    request_id=mode,
                    budget=replace(f.budget, max_mock_calls=1, max_feedback=0),
                ),
            )
            self.assertEqual(result.status, "INVALID_REQUEST", result.diagnostics)
            self.assertFalse(result.claim_records)

    def test_two_authorized_sources_cannot_be_mixed_into_one_permutation(self):
        from hcl.runtime.context import ContextCompiler

        f, candidate = self.fixture()
        second = f.store.put_source("s", f.owner, "other", "Other source.")
        request = f.request(
            source_handles=(f.handle, second),
            budget=replace(
                f.budget,
                max_request_bytes=1048576,
                max_context_tokens=1048576,
                max_feedback=0,
                max_mock_calls=1,
            ),
        )
        snapshot = f.store.snapshot("s", f.owner, request.source_handles)
        chunks = ContextCompiler().chunks(
            snapshot,
            request.question,
            "literature_compile",
            request.budget,
            OfflineModelPort().describe(),
        )
        self.assertEqual(len(chunks), 1)
        segment = next(s for s in chunks[0].segments if s.source_id == "other")
        candidate["unmodeled_segments"] = [segment.segment_id]
        v = candidate["variants"][0]
        v["parts"][1] = dict(
            segment_id=segment.segment_id,
            start=segment.start,
            end=segment.end,
            quote=segment.text,
        )
        v["segment_ids"].append(segment.segment_id)
        delivery, _ = f.run_candidate([candidate], request=request)
        self.assertEqual(delivery.status, "INVALID_REQUEST", delivery.diagnostics)
        self.assertFalse(delivery.claim_records)

    def test_plain_and_reorder_source_certificates_bind_original_versions(self):
        f, candidate = self.fixture()
        for reorder in (False, True):
            selected = candidate if reorder else f.simple()
            delivery, _ = f.run_candidate(
                [selected], request=f.request(request_id="source-cert-" + str(reorder))
            )
            self.assertEqual(delivery.status, "PARTIAL", delivery.diagnostics)
            actual = self.result(f, delivery)
            self.assertFalse(actual.values["comparisons"] or actual.values["analogies"])
            for version in (
                {"foreign-not-used": 999},
                {"book": 2},
                {"book": True},
                {},
                [["book", 1]],
            ):
                values = thaw(actual.values)
                values["source_versions"] = version
                with self.subTest(reorder=reorder, version=version), self.assertRaises(
                    HCLFailure
                ):
                    AnswerAssembler().compact_claim(replace(actual, values=values))
            for keys in (("foreign-not-used",), ("book", "book"), (), ["book"]):
                with self.subTest(reorder=reorder, keys=keys), self.assertRaises(
                    HCLFailure
                ):
                    AnswerAssembler().compact_claim(replace(actual, premise_ids=keys))

    def test_variants_and_frontiers_are_verified_not_just_displayed(self):
        f, candidate = self.fixture()
        result, _ = f.run_candidate([candidate])
        actual = self.result(f, result)
        for mode in ("offset", "order", "hash", "relation", "status"):
            values = thaw(actual.values)
            v = values["variants"][0]
            if mode == "offset":
                v["offset_map"]["pieces"][0]["generated_range"] = [999, 1000]
            elif mode == "order":
                v["offset_map"]["order"].reverse()
            elif mode == "hash":
                v["variant_sha256"] = "bad"
            elif mode == "relation":
                v["discourse_contrast"]["changed_pairs"][0][
                    "hypothetical_relation"
                ] = "BEFORE"
            else:
                v["discourse_contrast"]["status"] = "REAL_STORY_FACT"
            with self.subTest(mode=mode), self.assertRaises(HCLFailure):
                AnswerAssembler().compact_claim(replace(actual, values=values))
        for budget in range(6):
            delivery, _ = f.run_candidate(
                [candidate],
                request=f.request(
                    request_id=str(budget),
                    budget=replace(f.budget, max_local_evaluations=budget),
                ),
            )
            self.assertLessEqual(delivery.usage["local_evaluations"], budget)
            if budget == 0:
                self.assertEqual(
                    delivery.status, "BUDGET_EXHAUSTED", delivery.diagnostics
                )
                self.assertFalse(delivery.claim_records)
            else:
                self.assertEqual(delivery.status, "PARTIAL", delivery.diagnostics)
                if budget < 5:
                    self.assertIn("FRONTIER", delivery.answer)


if __name__ == "__main__":
    unittest.main()
