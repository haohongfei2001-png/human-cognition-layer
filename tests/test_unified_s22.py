"""Ordinary-source fixtures propose IR; real kernels compute every outcome."""

import asyncio
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from hcl import HCL, RevisionIssue
from hcl.kernel.types import BudgetSlice, Principal, TaskRequest
from hcl.memory.store import StateStore
from hcl.models.gateway import ModelGateway, OfflineModelPort
from hcl.semantics.revision import KINDS, qualified
from hcl.semantics.segments import segment_snapshot


def ref(source, name):
    return [source, name]


class RevisionExecutionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "state.sqlite"
        self.owner = Principal("tenant", "alice")
        self.store = StateStore.sqlite(self.path, revision=True)
        self.store.create_session("s", self.owner, {"bob"})
        self.handle = self.store.put_source(
            "s", self.owner, "source", "张三收到通知。如果收到通知，就会出席。"
        )
        self.request = TaskRequest(
            "first",
            "现在可支持什么？",
            (self.handle,),
            "s",
            self.owner,
            budget=BudgetSlice(
                max_mock_calls=1, max_output_bytes=262144, max_request_bytes=262144, max_local_evaluations=33
            ),
            issue=RevisionIssue("revision"),
        )

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def source(self, handle=None, known_at=None):
        handle = handle or self.handle
        source = handle.source_id
        snapshot = self.store.revision_snapshot("s", self.owner, (handle,), known_at=known_at)
        anchors = [
            item.segment_id
            for item in segment_snapshot(snapshot, self.request.question)
            if item.kind == "SOURCE"
        ]
        result = {key: [] for key in KINDS}
        result.update(source_id=source, nogoods=[], unparsed_segments=[])

        def add(category, identity, **fields):
            row = dict(id=identity, segment_ids=anchors, **fields)
            result[category].append(row)
            return row

        add("frames", "frame", kind="SOURCE_DISCOURSE", parent=None)
        add("entities", "person", label="张三")
        add(
            "perspectives",
            "view",
            agent=None,
            nested=[],
            at=ref(source, "t"),
            observation_model="source-report",
            belief_model="NOT_COMPUTED",
        )
        add(
            "scopes",
            "scope",
            frame=ref(source, "frame"),
            perspective=ref(source, "view"),
            at=ref(source, "t"),
        )
        add("points", "t", axis="EVENT", scope=ref(source, "scope"), agent=None)
        for identity, predicate, negative in [
            ("p", "received", False),
            ("q", "attends", False),
            ("not-q", "attends", True),
        ]:
            add(
                "claims",
                identity,
                predicate=predicate,
                arguments=[ref(source, "person")],
                negated=negative,
                scope=ref(source, "scope"),
                index=None,
            )
        add(
            "roots",
            "report",
            claim=ref(source, "p"),
            assumptions=[],
            event_end=ref(source, "t"),
            access=[],
            origin="DIRECT_REPORT",
        )
        add("rules", "conditional", premises=[ref(source, "p")], conclusion=ref(source, "q"), assumptions=[])
        return result, add

    def candidate(self, *sources, query_source="source", positive="q", negative="not-q"):
        return {
            "schema": "hcl-revision-candidates-1",
            "sources": list(sources),
            "query": {"positive": ref(query_source, positive), "negative": ref(query_source, negative)},
        }

    def run_candidate(self, candidate, request=None, port=None):
        port = port or OfflineModelPort(json.dumps(candidate, ensure_ascii=False))
        hcl = HCL(self.store, principal=self.owner, gateway=ModelGateway(self.store, port))
        return hcl.run_sync(request or self.request), port

    def values(self, result):
        self.assertIn(result.status, ("COMPLETED", "PARTIAL"), result.diagnostics)
        return next(iter(result.execution_receipt["inference_values"].values()))

    def test_normal_source_to_actual_rooted_result_and_answer_fields(self):
        source, _ = self.source()
        result, port = self.run_candidate(self.candidate(source))
        values = self.values(result)
        self.assertEqual(result.status, "COMPLETED", result.diagnostics)
        self.assertTrue(values["support_bits"]["positive_support"])
        self.assertFalse(values["support_bits"]["negative_support"])
        self.assertIn("positive support only", result.answer)
        self.assertGreater(result.usage["truth_work"], 0)
        self.assertEqual(port.attempts, 1)
        fields = {field.field: field.value for field in result.claim_records[0].used_result_fields}
        self.assertEqual(fields["support_bits"], values["support_bits"])
        self.assertFalse(values["semantic_certified"])
        self.assertEqual(result.usage["provider_calls"], 0)

    def test_negation_both_polarities_and_rootless_cycle_do_not_explode(self):
        for n, mode in enumerate(("negative", "both", "cycle")):
            source, add = self.source()
            if mode != "both":
                source["roots"] = []
            if mode in ("negative", "both"):
                add(
                    "roots",
                    "negative-report",
                    claim=ref("source", "not-q"),
                    assumptions=[],
                    event_end=ref("source", "t"),
                    access=[],
                    origin="DIRECT_REPORT",
                )
            else:
                add(
                    "rules",
                    "cycle",
                    premises=[ref("source", "q")],
                    conclusion=ref("source", "p"),
                    assumptions=[],
                )
            result, _ = self.run_candidate(
                self.candidate(source), replace(self.request, request_id="contrast" + str(n))
            )
            bits = self.values(result)["support_bits"]
            self.assertEqual(
                (bits["positive_support"], bits["negative_support"]),
                {"negative": (False, True), "both": (True, True), "cycle": (False, False)}[mode],
            )
            if mode == "both":
                self.assertIn("no explosion", result.answer)

    def timed_source(self, late, handle=None, known_at=None):
        source, add = self.source(handle, known_at)
        sid = source["source_id"]
        source["rules"] = []
        source["roots"][0]["claim"] = ref(sid, "q")
        source["perspectives"][0]["agent"] = ref(sid, "person")
        add("points", "event", axis="EVENT", scope=ref(sid, "scope"), agent=None)
        add("points", "receipt", axis="AGENT_ACCESS", scope=ref(sid, "scope"), agent=ref(sid, "person"))
        source["roots"][0].update(
            event_end=ref(sid, "event"), access=[{"agent": ref(sid, "person"), "point": ref(sid, "receipt")}]
        )
        add("assumptions", "clock")
        add(
            "clock_bridges",
            "clock-map",
            left_axis="EVENT" if late else "AGENT_ACCESS",
            right_axis="AGENT_ACCESS" if late else "EVENT",
            source_scope=ref(sid, "scope"),
            target_scope=ref(sid, "scope"),
            assumptions=[ref(sid, "clock")],
            evidence_roots=[ref(sid, "report")],
        )
        add(
            "constraints",
            "event-before",
            left=ref(sid, "event"),
            right=ref(sid, "t"),
            numerator=0,
            denominator=1,
            strict=True,
            assumptions=[],
            evidence_roots=[ref(sid, "report")],
            clock_bridge=None,
        )
        add(
            "constraints",
            "receipt-time",
            left=ref(sid, "t" if late else "receipt"),
            right=ref(sid, "receipt" if late else "t"),
            numerator=0,
            denominator=1,
            strict=True,
            assumptions=[],
            evidence_roots=[ref(sid, "report")],
            clock_bridge=ref(sid, "clock-map"),
        )
        return source

    def test_late_publication_and_corrected_receipt_keep_fixed_old_view(self):
        first, _ = self.run_candidate(self.candidate(self.timed_source(True)))
        self.assertFalse(self.values(first)["support_bits"]["positive_support"])
        cutoff = first.state_revision
        self.handle = self.store.put_source(
            "s", self.owner, "source", "后来披露一份报告，但人物仍在所问时点之后才收到。"
        )
        second, _ = self.run_candidate(
            self.candidate(self.timed_source(True)),
            replace(self.request, request_id="late-report", source_handles=(self.handle,)),
        )
        self.assertFalse(self.values(second)["support_bits"]["positive_support"])
        self.handle = self.store.put_source(
            "s", self.owner, "source", "新证据明确证明人物其实在所问时点之前收到。"
        )
        third, _ = self.run_candidate(
            self.candidate(self.timed_source(False)),
            replace(self.request, request_id="earlier-receipt", source_handles=(self.handle,)),
        )
        self.assertTrue(self.values(third)["support_bits"]["positive_support"])
        historic = replace(
            self.request,
            request_id="historical",
            source_handles=(),
            issue=RevisionIssue("revision", known_at=cutoff),
        )
        old, port = self.run_candidate(self.candidate(), historic)
        self.assertFalse(self.values(old)["support_bits"]["positive_support"])
        self.assertEqual(self.values(old)["known_at"], cutoff)
        self.assertEqual(self.values(old)["source_bindings"][0]["source_version"], 1)
        self.store.close()
        self.store = StateStore.sqlite(self.path)
        replay, new_port = self.run_candidate(self.candidate(), historic)
        self.assertEqual(replay.answer, old.answer)
        self.assertEqual(new_port.attempts, 0)
        self.assertTrue(replay.execution_receipt["replayed"])
        self.assertEqual(port.attempts, 1)

    def test_one_support_withdrawal_keeps_independent_or_path_and_unrelated_source(self):
        unrelated = self.store.put_source("s", self.owner, "other", "李四独立收到通知并出席。")
        other, _ = self.source(unrelated)
        result, _ = self.run_candidate(
            self.candidate(other, query_source="other"),
            replace(self.request, request_id="other", source_handles=(unrelated,)),
        )
        self.values(result)
        source, add = self.source()
        add(
            "roots",
            "independent",
            claim=ref("source", "q"),
            assumptions=[],
            event_end=ref("source", "t"),
            access=[],
            origin="DIRECT_REPORT",
        )
        first, _ = self.run_candidate(self.candidate(source))
        before = self.values(first)
        self.handle = self.store.put_source(
            "s", self.owner, "source", "第一个支持已撤回，第二个独立支持仍在。"
        )
        source, add = self.source()
        source["roots"] = []
        add(
            "roots",
            "independent",
            claim=ref("source", "q"),
            assumptions=[],
            event_end=ref("source", "t"),
            access=[],
            origin="DIRECT_REPORT",
        )
        second, _ = self.run_candidate(
            self.candidate(source),
            replace(self.request, request_id="withdraw-one", source_handles=(self.handle,)),
        )
        after = self.values(second)
        self.assertTrue(after["support_bits"]["positive_support"])
        q = qualified("source", "q")
        p = qualified("source", "p")
        other_q = qualified("other", "q")
        self.assertFalse(after["kernel_state"]["supports"][p])
        self.assertEqual(len(after["kernel_state"]["supports"][q]), 1)
        self.assertEqual(before["semantic_hashes"][other_q], after["semantic_hashes"][other_q])
        self.assertIn(other_q, after["retained_claims"])
        self.assertNotIn(other_q, after["recomputed_claims"])
        self.handle = self.store.put_source("s", self.owner, "source", "全部相关支持被撤回。")
        source, _ = self.source()
        source["roots"] = []
        third, _ = self.run_candidate(
            self.candidate(source),
            replace(self.request, request_id="withdraw-all", source_handles=(self.handle,)),
        )
        self.assertFalse(self.values(third)["support_bits"]["positive_support"])

    def test_injected_answer_labels_foreign_spans_and_implicit_cross_scope_are_rejected(self):
        source, _ = self.source()
        for n, mutate in enumerate(
            (
                lambda data: data.update(answer="precomputed"),
                lambda data: data["sources"][0]["roots"][0].update(segment_ids=["unknown-segment"]),
                lambda data: data["sources"][0]["roots"][0].update(computed_support=True),
            )
        ):
            candidate = self.candidate(deepcopy(source))
            mutate(candidate)
            result, _ = self.run_candidate(candidate, replace(self.request, request_id="invalid" + str(n)))
            self.assertEqual(result.status, "INVALID_REQUEST")
            self.assertFalse(result.answer)
            self.assertNotIn("inference_values", result.execution_receipt)

    def bridged_source(self):
        source, add = self.source()
        sid = "source"
        source["rules"] = []
        add("entities", "alias", label="张三")
        add("frames", "target-frame", kind="INTERPRETATION", parent=ref(sid, "frame"))
        add(
            "perspectives",
            "target-view",
            agent=ref(sid, "alias"),
            nested=[],
            at=ref(sid, "target-time"),
            observation_model="receipt",
            belief_model="NOT_COMPUTED",
        )
        add(
            "scopes",
            "target-scope",
            frame=ref(sid, "target-frame"),
            perspective=ref(sid, "target-view"),
            at=ref(sid, "target-time"),
        )
        add("points", "target-time", axis="EVENT", scope=ref(sid, "target-scope"), agent=None)
        add("points", "access-time", axis="AGENT_ACCESS", scope=ref(sid, "scope"), agent=ref(sid, "alias"))
        source["roots"][0]["access"] = [{"agent": ref(sid, "alias"), "point": ref(sid, "access-time")}]
        for claim in source["claims"][1:]:
            claim.update(predicate="received", arguments=[ref(sid, "alias")], scope=ref(sid, "target-scope"))
        for identity in ("same-assumption", "clock-assumption", "bridge-assumption"):
            add("assumptions", identity)
        add(
            "identities",
            "same",
            left=ref(sid, "person"),
            right=ref(sid, "alias"),
            assumptions=[ref(sid, "same-assumption")],
            evidence_roots=[ref(sid, "report")],
        )
        for name, left, axis in (("event-map", "t", "EVENT"), ("access-map", "access-time", "AGENT_ACCESS")):
            add(
                "clock_bridges",
                name,
                left_axis=axis,
                right_axis="EVENT",
                source_scope=ref(sid, "scope"),
                target_scope=ref(sid, "target-scope"),
                assumptions=[ref(sid, "clock-assumption")],
                evidence_roots=[ref(sid, "report")],
            )
            add(
                "constraints",
                name + "-edge",
                left=ref(sid, left),
                right=ref(sid, "target-time"),
                numerator=0,
                denominator=1,
                strict=True,
                assumptions=[],
                evidence_roots=[ref(sid, "report")],
                clock_bridge=ref(sid, name),
            )
        add(
            "bridges",
            "project",
            source_claim=ref(sid, "p"),
            target_claim=ref(sid, "q"),
            entity_mapping=[[ref(sid, "person"), ref(sid, "alias")]],
            temporal_mapping=[[ref(sid, "t"), ref(sid, "target-time")]],
            assumptions=[ref(sid, "bridge-assumption")],
            evidence_roots=[ref(sid, "report")],
        )
        return source

    def test_real_identity_time_and_access_bridge_then_identity_withdrawal(self):
        source = self.bridged_source()
        first, _ = self.run_candidate(self.candidate(source))
        before = self.values(first)
        self.assertTrue(before["support_bits"]["positive_support"])
        self.assertGreater(first.usage["identity_path_work"], 0)
        self.assertTrue(
            any(row["status"] == "CONDITIONAL_INFORMATION_PROJECTION" for row in before["bridge_proofs"])
        )
        source["identities"] = []
        withdrawn, _ = self.run_candidate(
            self.candidate(source), replace(self.request, request_id="withdraw-identity")
        )
        after = self.values(withdrawn)
        self.assertFalse(after["support_bits"]["positive_support"])
        self.assertTrue(after["support_bits"]["frontier_unexplored"])
        self.assertTrue(after["kernel_state"]["supports"][qualified("source", "p")])
        self.assertEqual(withdrawn.status, "PARTIAL")
        self.assertIn("IDENTITY_ALIGNMENT_UNRESOLVED", withdrawn.unresolved_issues)

    def default_source(self):
        source, add = self.source()
        source["roots"] = []
        source["rules"] = []
        add("entities", "message", label="通知 m")
        for claim in source["claims"]:
            claim["arguments"].append(ref("source", "message"))
            claim["predicate"] = "receipt" if claim["id"] == "p" else "no-indexed-receipt"
        filters = {
            "kind": "receipt",
            "agent_id": ref("source", "person"),
            "message_id": ref("source", "message"),
        }
        source["claims"][0]["index"] = filters
        add("assumptions", "closed-scope")
        add(
            "defaults",
            "absence",
            claim=ref("source", "q"),
            query=filters,
            assumptions=[ref("source", "closed-scope")],
        )
        add(
            "rules",
            "receipt-rebuts",
            premises=[ref("source", "p")],
            conclusion=ref("source", "not-q"),
            assumptions=[],
        )
        return source

    def late_receipt_source(self, handle):
        source, add = self.source(handle)
        sid = handle.source_id
        source["rules"] = []
        add("entities", "message", label="通知 m")
        for claim in source["claims"]:
            claim["arguments"].append(ref(sid, "message"))
            if claim["id"] == "p":
                claim["predicate"] = "receipt"
        for name in ("identity-assumption", "clock-assumption", "bridge-assumption"):
            add("assumptions", name)
        for name in ("person", "message"):
            add(
                "identities",
                "same-" + name,
                left=ref(sid, name),
                right=ref("source", name),
                assumptions=[ref(sid, "identity-assumption")],
                evidence_roots=[ref(sid, "report")],
            )
        add(
            "clock_bridges",
            "earlier-event",
            left_axis="EVENT",
            right_axis="EVENT",
            source_scope=ref(sid, "scope"),
            target_scope=ref("source", "scope"),
            assumptions=[ref(sid, "clock-assumption")],
            evidence_roots=[ref(sid, "report")],
        )
        add(
            "constraints",
            "earlier-event-edge",
            left=ref(sid, "t"),
            right=ref("source", "t"),
            numerator=0,
            denominator=1,
            strict=True,
            assumptions=[],
            evidence_roots=[ref(sid, "report")],
            clock_bridge=ref(sid, "earlier-event"),
        )
        add(
            "bridges",
            "receipt-project",
            source_claim=ref(sid, "p"),
            target_claim=ref("source", "p"),
            entity_mapping=[[ref(sid, name), ref("source", name)] for name in ("person", "message")],
            temporal_mapping=[[ref(sid, "t"), ref("source", "t")]],
            assumptions=[ref(sid, "bridge-assumption")],
            evidence_roots=[ref(sid, "report")],
        )
        return source

    def test_absence_watch_pending_then_actual_late_receipt_rebuts_default_and_old_view_survives(self):
        first, _ = self.run_candidate(self.candidate(self.default_source()))
        before = self.values(first)
        cutoff = first.state_revision
        self.assertTrue(before["support_bits"]["positive_support"])
        self.assertIn("CONDITIONAL_INDEXED_ABSENCE", before["default_results"].values())
        late = self.store.put_source("s", self.owner, "late", "新的独立证据说明，同一人此前收到同一通知。")
        replay, port = self.run_candidate(self.candidate(), self.request)
        self.assertEqual(replay.status, "STALE_STATE")
        self.assertEqual(port.attempts, 0)
        pending, _ = self.run_candidate(
            self.candidate(), replace(self.request, request_id="pending", source_handles=())
        )
        self.assertEqual(pending.status, "PARTIAL")
        self.assertFalse(self.values(pending)["support_bits"]["positive_support"])
        self.assertTrue(self.values(pending)["support_bits"]["frontier_unexplored"])
        update, _ = self.run_candidate(
            self.candidate(self.late_receipt_source(late)),
            replace(self.request, request_id="late-compiled", source_handles=(late,)),
        )
        after = self.values(update)
        self.assertEqual(
            (after["support_bits"]["positive_support"], after["support_bits"]["negative_support"]),
            (False, True),
        )
        self.assertIn("REBUTTED_BY_SUPPORTED_RECORD", after["default_results"].values())
        self.assertTrue(after["absence_watches"])
        old_request = replace(
            self.request,
            request_id="old-default",
            source_handles=(),
            issue=RevisionIssue("revision", known_at=cutoff),
        )
        old, _ = self.run_candidate(self.candidate(), old_request)
        self.assertTrue(self.values(old)["support_bits"]["positive_support"])
        self.assertFalse(self.values(old)["support_bits"]["negative_support"])
        from hcl.runtime.budget import task_key

        row = self.store._db.execute(
            "SELECT result_hash FROM tasks WHERE task_key=?",
            (task_key(self.owner, "s", self.request.request_id),),
        ).fetchone()
        self.assertEqual(self.store._get_object(row["result_hash"]), first)
        replay, _ = self.run_candidate(self.candidate(), old_request)
        self.assertEqual(replay.answer, old.answer)

    def test_known_unrelated_compilation_retains_default_semantic_hash(self):
        first, _ = self.run_candidate(self.candidate(self.default_source()))
        before = self.values(first)
        unrelated = self.store.put_source("s", self.owner, "other", "李四的独立事件。")
        other, _ = self.source(unrelated)
        second, _ = self.run_candidate(
            self.candidate(other), replace(self.request, request_id="unrelated", source_handles=(unrelated,))
        )
        after = self.values(second)
        key = qualified("source", "q")
        self.assertTrue(after["support_bits"]["positive_support"])
        self.assertEqual(before["semantic_hashes"][key], after["semantic_hashes"][key])
        self.assertIn(key, after["retained_claims"])

    def test_32_unseen_graph_combinations_match_independent_boolean_closure(self):
        import random

        randomizer = random.Random(2291)
        names = ("p", "q", "not-q")
        possible = ((("p",), "q"), (("q",), "p"), (("not-q",), "p"), (("p", "q"), "not-q"), (("not-q",), "q"))
        for number in range(32):
            roots = {key for key in names if randomizer.randrange(2)}
            rules = [rule for rule in possible if randomizer.randrange(2)]
            text = (
                "当前报告："
                + ",".join(sorted(roots))
                + "。条件："
                + "；".join("且".join(premises) + "推出" + target for premises, target in rules)
                + "。"
            )
            self.handle = self.store.put_source("s", self.owner, "source", text)
            source, add = self.source()
            source["roots"] = []
            source["rules"] = []
            for key in roots:
                add(
                    "roots",
                    "root-" + key,
                    claim=ref("source", key),
                    assumptions=[],
                    event_end=ref("source", "t"),
                    access=[],
                    origin="DIRECT_REPORT",
                )
            for i, (premises, target) in enumerate(rules):
                add(
                    "rules",
                    "rule-" + str(i),
                    premises=[ref("source", key) for key in premises],
                    conclusion=ref("source", target),
                    assumptions=[],
                )
            expected = set(roots)
            while True:
                next_values = expected | {target for premises, target in rules if set(premises) <= expected}
                if next_values == expected:
                    break
                expected = next_values
            result, _ = self.run_candidate(
                self.candidate(source),
                replace(self.request, request_id="oracle-" + str(number), source_handles=(self.handle,)),
            )
            bits = self.values(result)["support_bits"]
            self.assertEqual(
                (bits["positive_support"], bits["negative_support"]), ("q" in expected, "not-q" in expected)
            )

    def test_default_cycles_and_unknown_time_do_not_become_negative_certainty(self):
        source = self.default_source()
        # A default would cause its own defeating receipt: no unique negative
        # fixed point may be invented by repeatedly flipping this bit.
        source["rules"].append(
            dict(
                id="self-defeat",
                segment_ids=source["frames"][0]["segment_ids"],
                premises=[ref("source", "q")],
                conclusion=ref("source", "p"),
                assumptions=[],
            )
        )
        result, _ = self.run_candidate(self.candidate(source))
        self.assertEqual(result.status, "PARTIAL")
        self.assertIn("NONSTRATIFIED_DEFAULT_UNRESOLVED", result.unresolved_issues)
        self.assertFalse(self.values(result)["support_bits"]["positive_support"])
        source = self.default_source()
        source["roots"].append(
            dict(
                id="undated-receipt",
                segment_ids=source["frames"][0]["segment_ids"],
                claim=ref("source", "p"),
                assumptions=[],
                event_end=None,
                access=[],
                origin="DIRECT_REPORT",
            )
        )
        result, _ = self.run_candidate(self.candidate(source), replace(self.request, request_id="undated"))
        self.assertEqual(result.status, "PARTIAL")
        self.assertFalse(self.values(result)["support_bits"]["positive_support"])
        self.assertIn("COVERAGE_OR_SEARCH_UNRESOLVED", self.values(result)["default_results"].values())

    def test_budget_partial_keeps_last_executed_graph_and_replays_without_new_call(self):
        request = replace(self.request, budget=replace(self.request.budget, max_local_evaluations=1))
        result, port = self.run_candidate(self.candidate(self.default_source()), request)
        self.assertEqual(result.status, "PARTIAL")
        values = self.values(result)
        self.assertFalse(values["support_bits"]["positive_support"])
        self.assertTrue(values["support_bits"]["frontier_unexplored"])
        self.assertIn("DEFAULT_WORK_UNEXPLORED", values["default_results"].values())
        self.assertEqual(result.usage["local_evaluations"], 1)
        self.store.close()
        self.store = StateStore.sqlite(self.path)
        replay, new_port = self.run_candidate(self.candidate(), request)
        self.assertEqual(replay.answer, result.answer)
        self.assertEqual(replay.status, "PARTIAL")
        self.assertEqual(new_port.attempts, 0)
        self.assertEqual(port.attempts, 1)

    def test_late_revocation_strips_run_stream_and_restarted_replay_receipts(self):
        peer = StateStore.sqlite(self.path)
        try:
            for stream in (False, True):
                self.store.set_readers("s", self.owner, "source", {"alice", "bob"})
                source, _ = self.source()
                for claim in source["claims"][1:]:
                    claim["predicate"] = "PRIVATE_ATOM_CANARY"
                request = replace(self.request, request_id="revoke-" + str(stream))
                port = OfflineModelPort(json.dumps(self.candidate(source), ensure_ascii=False))
                hcl = HCL(self.store, principal=self.owner, gateway=ModelGateway(self.store, port))
                original = self.store._checkpoint

                def checkpoint(stage):
                    if stage == "task_finished":
                        peer.set_readers("s", self.owner, "source", {"bob"})
                    original(stage)

                with patch.object(self.store, "_checkpoint", side_effect=checkpoint):
                    if stream:

                        async def collect():
                            return [event async for event in hcl.stream(request)]

                        result = asyncio.run(collect())[-1].result
                    else:
                        result = hcl.run_sync(request)
                self.assertEqual(result.status, "DENIED")
                self.assertNotIn("PRIVATE_ATOM_CANARY", str(result))
                self.assertNotIn("inference_values", result.execution_receipt)
                self.assertFalse(result.claim_records)
                self.store.close()
                self.store = StateStore.sqlite(self.path)
                replay, _ = self.run_candidate(self.candidate(), request)
                self.assertEqual(replay.status, "DENIED")
                self.assertNotIn("PRIVATE_ATOM_CANARY", str(replay))
                self.assertEqual(replay.usage["held_mock_calls"], 1)
        finally:
            peer.close()

    def test_cached_replay_fresh_query_check_catches_new_pending_evidence(self):
        first, _ = self.run_candidate(self.candidate(self.default_source()))
        self.values(first)
        peer = StateStore.sqlite(self.path)
        original = self.store._get_object
        changed = False
        from hcl.kernel.types import TaskResult

        def read(digest):
            nonlocal changed
            value = original(digest)
            if isinstance(value, TaskResult) and not changed:
                changed = True
                peer.put_source("s", self.owner, "new-pending", "A new potentially relevant receipt.")
            return value

        try:
            with patch.object(self.store, "_get_object", side_effect=read):
                replay, port = self.run_candidate(self.candidate(), self.request)
            self.assertEqual(replay.status, "STALE_STATE")
            self.assertEqual(port.attempts, 0)
            self.assertFalse(replay.answer)
            self.assertNotIn("inference_values", replay.execution_receipt)
            self.assertEqual(replay.usage["held_mock_calls"], 1)
            self.assertEqual(replay.usage["replay_new_mock_calls"], 0)
        finally:
            peer.close()

    def test_source_index_cannot_disclose_other_inputs_of_its_extraction_call(self):
        secret = self.store.put_source(
            "s", self.owner, "PRIVATE_SOURCE_CANARY", "PRIVATE_TEXT_CANARY", readers={"alice"}
        )
        public, _ = self.source()
        for claim in public["claims"][1:]:
            claim["predicate"] = "PRIVATE_TEXT_CANARY"
        result, _ = self.run_candidate(
            self.candidate(public), replace(self.request, source_handles=(self.handle, secret))
        )
        self.values(result)
        from hcl.kernel.dependencies import IndexQuery

        bob = Principal("tenant", "bob")
        view = self.store.query_snapshot("s", bob, (), (IndexQuery({"kind": "program"}, history=True),))
        self.assertFalse(view.query_views["0"]["matches"])
        self.assertEqual(view.query_views["0"]["pending"], (("source", 1, "UNCOMPILED"),))
        self.assertNotIn("PRIVATE_SOURCE_CANARY", str(view))
        self.assertNotIn("PRIVATE_TEXT_CANARY", str(view))

    def test_bad_cutoff_duplicate_handles_and_query_scope_are_safe_failures(self):
        source, _ = self.source()
        requests = (
            replace(self.request, issue=RevisionIssue("revision", known_at=1000000)),
            replace(self.request, source_handles=(self.handle, self.handle)),
            replace(
                self.request,
                source_handles=(self.handle, self.handle),
                issue=RevisionIssue("revision", known_at=2),
            ),
        )
        for request in requests:
            with self.subTest(request=request):
                result, port = self.run_candidate(self.candidate(source), request)
                self.assertEqual(result.status, "INVALID_REQUEST")
                self.assertEqual(port.attempts, 0)
                self.assertFalse(result.answer)

    def test_invalid_unicode_identifier_is_rejected_before_model_or_sqlite(self):
        from hcl.kernel.types import SourceHandle

        source, _ = self.source()
        for request in (
            replace(self.request, source_handles=(SourceHandle("\ud800", 1),)),
            replace(self.request, issue=RevisionIssue("\ud800")),
            replace(self.request, issue=RevisionIssue("revision", source_id="\ud800")),
        ):
            result, port = self.run_candidate(self.candidate(source), request)
            self.assertEqual(result.status, "INVALID_REQUEST")
            self.assertEqual(result.diagnostics[0].code, "INVALID_TEXT_ENCODING")
            self.assertEqual(port.attempts, 0)

    def test_historical_uncompiled_source_is_explicitly_compiled_after_newer_version(self):
        old_handle = self.handle
        cutoff = self.store.revision_snapshot("s", self.owner, (old_handle,)).revision
        self.handle = self.store.put_source("s", self.owner, "source", "新版本撤回了原始报告。")
        new, _ = self.source()
        new["roots"] = []
        current, _ = self.run_candidate(
            self.candidate(new), replace(self.request, source_handles=(self.handle,))
        )
        self.assertFalse(self.values(current)["support_bits"]["positive_support"])
        old, _ = self.source(old_handle, cutoff)
        historical = replace(
            self.request,
            request_id="old-uncompiled",
            source_handles=(old_handle,),
            issue=RevisionIssue("revision", known_at=cutoff),
        )
        result, _ = self.run_candidate(self.candidate(old), historical)
        values = self.values(result)
        self.assertTrue(values["support_bits"]["positive_support"])
        self.assertEqual(values["source_bindings"][0]["source_version"], 1)
        self.assertLessEqual(values["source_bindings"][0]["recorded_at"], cutoff)
        indexed = self.store.revision_snapshot("s", self.owner, (), known_at=cutoff).query_views["0"][
            "matches"
        ]
        self.assertGreater(indexed[0]["indexed_at"], cutoff)
        replay, port = self.run_candidate(self.candidate(), historical)
        self.assertEqual(replay.answer, result.answer)
        self.assertEqual(port.attempts, 0)
        altered, port = self.run_candidate(
            self.candidate(), replace(historical, issue=RevisionIssue("revision", known_at=cutoff + 1))
        )
        self.assertEqual(altered.status, "INVALID_REQUEST")
        self.assertEqual(port.attempts, 0)
        self.assertIn("FINGERPRINT", altered.diagnostics[0].code)

    def test_hypothetical_frame_and_perspective_remain_visible_in_consumed_answer(self):
        source, _ = self.source()
        source["frames"][0]["kind"] = "HYPOTHETICAL"
        result, _ = self.run_candidate(self.candidate(source))
        values = self.values(result)
        self.assertIn("[HYPOTHETICAL]", result.answer)
        metadata = values["claim_metadata"][qualified("source", "q")]
        self.assertEqual(metadata["frame_kind"], "HYPOTHETICAL")
        self.assertIn(metadata["perspective_id"], result.answer)
        self.assertIn(metadata["at_point"], result.answer)
        self.assertFalse(values["semantic_certified"])

    def test_structurally_valid_wrong_meaning_is_not_semantically_certified(self):
        source, _ = self.source()
        for claim in source["claims"][1:]:
            claim["predicate"] = "a deliberately wrong candidate meaning"
        result, _ = self.run_candidate(self.candidate(source))
        values = self.values(result)
        self.assertTrue(values["support_bits"]["positive_support"])
        self.assertFalse(values["semantic_certified"])
        self.assertEqual(values["candidate_completeness"], "NOT_ESTABLISHED")
        self.assertIn("not established world truth", result.answer)

    def test_unparsed_coverage_cannot_license_conditional_absence(self):
        source = self.default_source()
        source["unparsed_segments"] = list(source["frames"][0]["segment_ids"])
        result, _ = self.run_candidate(self.candidate(source))
        values = self.values(result)
        self.assertEqual(result.status, "PARTIAL")
        self.assertTrue(values["coverage_pending"])
        self.assertFalse(values["support_bits"]["positive_support"])
        self.assertIn("COVERAGE_OR_SEARCH_UNRESOLVED", values["default_results"].values())

    def test_derived_root_bound_retains_last_actual_state_and_exposes_frontier(self):
        from hcl.kernel.truth import TruthProfile

        def bounded(**kwargs):
            return TruthProfile(**dict(kwargs, max_roots=1))

        with patch("hcl.operators.revision.TruthProfile", side_effect=bounded):
            result, _ = self.run_candidate(self.candidate(self.default_source()))
        values = self.values(result)
        self.assertEqual(result.status, "PARTIAL")
        self.assertFalse(values["support_bits"]["positive_support"])
        self.assertTrue(values["support_bits"]["frontier_unexplored"])
        self.assertIn("DEFAULT_ROOT_BOUND_UNEXPLORED", values["default_results"].values())
        self.assertEqual(len(values["kernel_program"]["roots"]), 1)

    def root_environment_fixture(self, *, absent=False):
        if absent:
            source = self.default_source()
            anchors = source["frames"][0]["segment_ids"]

            def add(category, identity, **fields):
                row = dict(id=identity, segment_ids=anchors, **fields)
                source[category].append(row)
                return row

            add(
                "roots",
                "report",
                claim=ref("source", "p"),
                assumptions=[ref("source", "A")],
                event_end=ref("source", "event"),
                access=[],
                origin="INTERPRETATION",
            )
        else:
            source, add = self.source()
            source["rules"] = []
            source["roots"][0].update(
                claim=ref("source", "q"), assumptions=[ref("source", "A")], event_end=ref("source", "event")
            )
        for key in ("A", "B"):
            add("assumptions", key)
        add("points", "event", axis="EVENT", scope=ref("source", "scope"), agent=None)
        add(
            "claims",
            "clock-only",
            predicate="clock-evidence",
            arguments=[ref("source", "person")],
            negated=False,
            scope=ref("source", "scope"),
            index=None,
        )
        add(
            "roots",
            "clock-evidence",
            claim=ref("source", "clock-only"),
            assumptions=[ref("source", "B")],
            event_end=ref("source", "t"),
            access=[],
            origin="INTERPRETATION",
        )
        add(
            "constraints",
            "before",
            left=ref("source", "event"),
            right=ref("source", "t"),
            numerator=0,
            denominator=1,
            strict=True,
            assumptions=[],
            evidence_roots=[ref("source", "clock-evidence")],
            clock_bridge=None,
        )
        return source

    def test_temporal_proof_inherits_root_hypotheses_and_rejects_nogood_union(self):
        source = self.root_environment_fixture()
        first, _ = self.run_candidate(self.candidate(source))
        supports = self.values(first)["kernel_state"]["supports"][qualified("source", "q")]
        self.assertEqual(
            set(supports[0]["assumptions"]), {qualified("source", "A"), qualified("source", "B")}
        )
        source["nogoods"] = [[ref("source", "A"), ref("source", "B")]]
        conflict, _ = self.run_candidate(
            self.candidate(source), replace(self.request, request_id="nogood-time")
        )
        values = self.values(conflict)
        self.assertEqual(conflict.status, "PARTIAL")
        self.assertFalse(values["support_bits"]["positive_support"])
        self.assertTrue(values["support_bits"]["frontier_unexplored"])
        self.assertTrue(values["kernel_state"]["supports"][qualified("source", "clock-only")])

    def test_environment_conflict_cannot_license_a_watched_absence(self):
        source = self.root_environment_fixture(absent=True)
        source["nogoods"] = [[ref("source", "A"), ref("source", "B")]]
        result, _ = self.run_candidate(self.candidate(source))
        values = self.values(result)
        self.assertEqual(result.status, "PARTIAL")
        self.assertFalse(values["support_bits"]["positive_support"])
        self.assertIn("COVERAGE_OR_SEARCH_UNRESOLVED", values["default_results"].values())

    def test_identity_and_bridge_evidence_inherit_original_root_hypotheses(self):
        for number, mechanism in enumerate(("identities", "bridges", "clock_bridges")):
            source = self.bridged_source()
            anchors = source["frames"][0]["segment_ids"]
            for key in ("A", "B"):
                source["assumptions"].append(dict(id=key, segment_ids=anchors))
            source["roots"][0]["assumptions"] = [ref("source", "A")]
            source["claims"].append(
                dict(
                    id="evidence-only",
                    segment_ids=anchors,
                    predicate="proof-evidence",
                    arguments=[ref("source", "person")],
                    negated=False,
                    scope=ref("source", "scope"),
                    index=None,
                )
            )
            source["roots"].append(
                dict(
                    id="other-evidence",
                    segment_ids=anchors,
                    claim=ref("source", "evidence-only"),
                    assumptions=[ref("source", "B")],
                    event_end=ref("source", "t"),
                    access=[],
                    origin="INTERPRETATION",
                )
            )
            source[mechanism][0]["evidence_roots"] = [ref("source", "other-evidence")]
            request = replace(self.request, request_id="environment-" + str(number))
            positive, _ = self.run_candidate(self.candidate(source), request)
            values = self.values(positive)
            self.assertTrue(values["support_bits"]["positive_support"], (mechanism, positive.diagnostics))
            supports = values["kernel_state"]["supports"][qualified("source", "q")]
            self.assertTrue(
                all(
                    {qualified("source", "A"), qualified("source", "B")} <= set(row["assumptions"])
                    for row in supports
                ),
                mechanism,
            )
            source["nogoods"] = [[ref("source", "A"), ref("source", "B")]]
            conflict, _ = self.run_candidate(
                self.candidate(source), replace(request, request_id=request.request_id + "-conflict")
            )
            values = self.values(conflict)
            self.assertEqual(conflict.status, "PARTIAL", mechanism)
            self.assertFalse(values["support_bits"]["positive_support"], mechanism)
            self.assertTrue(values["kernel_state"]["supports"][qualified("source", "p")], mechanism)

    def test_rule_derived_material_proof_can_cross_explicit_character_bridge(self):
        source = self.bridged_source()
        prior = deepcopy(source["claims"][0])
        prior["id"] = "pre-p"
        source["claims"].append(prior)
        source["roots"][0]["claim"] = ref("source", "pre-p")
        source["rules"].append(
            dict(
                id="derive-p",
                segment_ids=source["frames"][0]["segment_ids"],
                premises=[ref("source", "pre-p")],
                conclusion=ref("source", "p"),
                assumptions=[],
            )
        )
        result, _ = self.run_candidate(self.candidate(source))
        values = self.values(result)
        self.assertTrue(values["support_bits"]["positive_support"], result.unresolved_issues)
        support = values["kernel_state"]["supports"][qualified("source", "q")][0]
        self.assertTrue(any(root.startswith("program:") for root in support["roots"]))
        self.assertTrue(
            any(row["status"] == "CONDITIONAL_INFORMATION_PROJECTION" for row in values["bridge_proofs"])
        )
        # Removing actual material receipt must still refuse the projection.
        source["roots"][0]["access"] = []
        denied, _ = self.run_candidate(
            self.candidate(source), replace(self.request, request_id="missing-rule-receipt")
        )
        self.assertFalse(self.values(denied)["support_bits"]["positive_support"])

    def test_receipt_from_incompatible_environment_does_not_settle_default_branch(self):
        source = self.default_source()
        anchors = source["frames"][0]["segment_ids"]
        source["assumptions"].append(dict(id="A", segment_ids=anchors))
        source["roots"].append(
            dict(
                id="receipt-A",
                segment_ids=anchors,
                claim=ref("source", "p"),
                assumptions=[ref("source", "A")],
                event_end=ref("source", "t"),
                access=[],
                origin="INTERPRETATION",
            )
        )
        source["nogoods"] = [[ref("source", "A"), ref("source", "closed-scope")]]
        result, _ = self.run_candidate(self.candidate(source))
        values = self.values(result)
        self.assertEqual(result.status, "PARTIAL")
        self.assertIn("DEFAULT_ENVIRONMENT_BRANCHING_UNEXPLORED", values["default_results"].values())
        self.assertTrue(values["support_bits"]["frontier_unexplored"])
        self.assertTrue(values["support_bits"]["negative_support"])
        self.assertFalse(values["support_bits"]["positive_support"])

    def test_query_watch_binding_race_returns_safe_failure_for_run_and_stream(self):
        peer = StateStore.sqlite(self.path)
        try:
            for stream in (False, True):
                source = self.default_source()
                request = replace(self.request, request_id="watch-race-" + str(stream))
                port = OfflineModelPort(json.dumps(self.candidate(source), ensure_ascii=False))
                engine = HCL(self.store, principal=self.owner, gateway=ModelGateway(self.store, port))
                original = self.store.query_snapshot
                changed = False

                def racing(session, principal, handles, queries):
                    nonlocal changed
                    if len(queries) > 1 and not changed:
                        changed = True
                        peer.put_source(
                            "s", self.owner, "PRIVATE_RACE_SOURCE_" + str(stream), "PRIVATE_RACE_TEXT_CANARY"
                        )
                    return original(session, principal, handles, queries)

                with patch.object(self.store, "query_snapshot", side_effect=racing):
                    if stream:

                        async def collect():
                            return [event async for event in engine.stream(request)]

                        events = asyncio.run(collect())
                        self.assertEqual([event.kind for event in events], ["status", "result"])
                        result = events[-1].result
                    else:
                        result = engine.run_sync(request)
                self.assertTrue(changed)
                self.assertEqual(result.status, "STALE_STATE")
                self.assertEqual(result.diagnostics[0].stage, "revision")
                self.assertEqual(result.diagnostics[0].code, "QUERY_DEPENDENCY_CHANGED")
                self.assertFalse(result.answer)
                self.assertNotIn("PRIVATE_RACE", repr(result))
                self.assertNotIn("inference_values", result.execution_receipt)
                self.assertEqual(port.attempts, 1)
                self.assertEqual(result.usage["held_mock_calls"], 1)
                replay = engine.run_sync(request)
                self.assertFalse(replay.answer)
                self.assertEqual(port.attempts, 1)
                self.assertEqual(replay.usage["held_mock_calls"], 1)
        finally:
            peer.close()

    def test_runtime_failure_constructors_supply_every_safe_diagnostic_field(self):
        import ast

        root = Path(__file__).resolve().parents[1] / "hcl"
        count = 0
        for path in root.rglob("*.py"):
            for node in ast.walk(ast.parse(path.read_text())):
                if (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Name)
                    and node.func.id == "HCLFailure"
                ):
                    self.assertFalse(any(isinstance(value, ast.Starred) for value in node.args), str(path))
                    provided = len(node.args) + sum(
                        item.arg in {"status", "stage", "code", "field_path", "message"}
                        for item in node.keywords
                    )
                    self.assertEqual(provided, 5, (str(path), node.lineno))
                    count += 1
        self.assertGreater(count, 20)
