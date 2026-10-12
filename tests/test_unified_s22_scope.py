"""Retractable identity, conditional bridges, and information-access contrasts."""

from dataclasses import replace
import itertools
import unittest

from hcl.kernel.identity import IdentityGraph, IdentityHypothesis, SourceLocalEntity
from hcl.kernel.scope import Bridge, CognitiveScope, Perspective, evaluate_bridge
from hcl.kernel.temporal import TemporalConstraint, TemporalNetwork, TemporalRecord, TimePoint
from hcl.kernel.truth import Support


def entities(*names):
    return tuple(
        SourceLocalEntity(name, "source:" + name, 1, "same display name", ("segment:" + name,))
        for name in names
    )


def graph(hypotheses=(), **kwargs):
    return IdentityGraph(entities("a", "b", "c", "d"), hypotheses, **kwargs)


def hypothesis(identity, left, right):
    return IdentityHypothesis(identity, left, right, {"evidence:" + identity})


class IdentityKernelTests(unittest.TestCase):
    def test_equal_names_do_not_merge_and_identity_is_retractable(self):
        ab, bc, ac = hypothesis("ab", "a", "b"), hypothesis("bc", "b", "c"), hypothesis("ac", "a", "c")
        self.assertFalse(graph().paths("a", "b").supports)
        active = graph((ab, bc, ac), active_assumptions={"ab", "bc", "ac"})
        self.assertEqual(
            {s.assumptions for s in active.paths("a", "c").supports},
            {frozenset({"ab", "bc"}), frozenset({"ac"})},
        )
        withdrawn = graph((replace(ab, active=False), bc, ac), active_assumptions={"ab", "bc", "ac"})
        self.assertEqual({s.assumptions for s in withdrawn.paths("a", "c").supports}, {frozenset({"ac"})})
        self.assertEqual(active.entities, withdrawn.entities)
        self.assertEqual(active.entities["a"].source_id, "source:a")
        with self.assertRaises(TypeError):
            active.entities["a"] = active.entities["c"]

    def test_64_graphs_match_independent_simple_path_oracle(self):
        pairs = tuple(itertools.combinations("abcd", 2))
        for mask in range(64):
            hypotheses = tuple(
                hypothesis(a + b, a, b) for bit, (a, b) in enumerate(pairs) if mask & (1 << bit)
            )
            active = {row.hypothesis_id for row in hypotheses}
            actual = graph(hypotheses, active_assumptions=active).paths("a", "d")
            expected = set()
            for n in range(3):
                for middle in itertools.permutations("bc", n):
                    nodes = ("a",) + middle + ("d",)
                    needed = frozenset("".join(sorted(pair)) for pair in zip(nodes, nodes[1:]))
                    if needed <= active:
                        expected.add(needed)
            self.assertFalse(actual.frontier_unexplored)
            self.assertEqual({s.assumptions for s in actual.supports}, expected)

    def test_nogood_and_bounds_preserve_uncertainty(self):
        hypotheses = (hypothesis("ab", "a", "b"), hypothesis("bc", "b", "c"), hypothesis("ac", "a", "c"))
        active = {"ab", "bc", "ac"}
        self.assertEqual(
            {
                s.assumptions
                for s in graph(hypotheses, active_assumptions=active, nogoods=({"ab", "bc"},))
                .paths("a", "c")
                .supports
            },
            {frozenset({"ac"})},
        )
        self.assertTrue(
            graph(hypotheses, active_assumptions=active, max_paths=1).paths("a", "c").frontier_unexplored
        )
        bounded = graph(hypotheses, active_assumptions=active, max_work=1).paths("a", "c")
        self.assertEqual(bounded.work, 1)
        self.assertTrue(bounded.frontier_unexplored)
        self.assertEqual(graph().paths("a", "a").supports, (Support(frozenset(), frozenset()),))

    def test_invalid_candidates_fail_before_sort_or_traversal(self):
        for args in ({"hypotheses": (object(),)}, {"nogoods": ((),)}, {"active_assumptions": {1}}):
            with self.subTest(args=args), self.assertRaises(ValueError):
                graph(**args)
        with self.assertRaises(ValueError):
            graph().paths([], "a")


class BridgeKernelTests(unittest.TestCase):
    def setUp(self):
        self.active = {"assume-bridge", "ab", "clock"}
        self.identity = graph((hypothesis("ab", "a", "b"),), active_assumptions=self.active)
        self.points = (
            TimePoint("event", "EVENT", "world"),
            TimePoint("query", "EVENT", "world"),
            TimePoint("receipt", "AGENT_ACCESS", "world", "alice"),
        )
        self.edges = (
            TemporalConstraint("occurred", "event", "query", strict=True, evidence_roots=("time-evidence",)),
            TemporalConstraint(
                "received",
                "receipt",
                "query",
                strict=True,
                assumptions={"clock"},
                evidence_roots=("receipt-evidence",),
                bridge_id="clock-map",
            ),
        )
        self.temporal = TemporalNetwork(
            self.points, self.edges, active_assumptions=self.active, verified_bridges={"clock-map"}
        )
        self.source = CognitiveScope("source-scope", "report-frame", "analyst", "query")
        self.target = CognitiveScope("target-scope", "character-frame", "alice-view", "query")
        self.analyst = Perspective(
            "analyst", None, (), "query", "evidenced", "uncomputed", ("source-evidence",)
        )
        self.alice = Perspective(
            "alice-view", "alice", (), "query", "message-receipt", "uncomputed", ("source-evidence",)
        )
        self.bridge = Bridge(
            "bridge",
            "source-scope",
            "target-scope",
            ("analyst", "alice-view"),
            (("a", "b"),),
            (),
            {"assume-bridge"},
            {"bridge-evidence"},
        )
        self.live = {"source-evidence", "bridge-evidence", "evidence:ab", "time-evidence", "receipt-evidence"}
        self.records = {"source-evidence": TemporalRecord("report", 1, 9, "event", {"alice": "receipt"}, {})}
        self.premise = Support(frozenset(), frozenset({"source-evidence"}))

    def evaluate(self, **changes):
        kwargs = dict(
            source_scope=self.source,
            target_scope=self.target,
            source_perspective=self.analyst,
            target_perspective=self.alice,
            identity_graph=self.identity,
            temporal_network=self.temporal,
            records_by_root=self.records,
            active_assumptions=self.active,
            live_roots=self.live,
        )
        kwargs.update(changes)
        return evaluate_bridge(self.bridge, self.premise, **kwargs)

    def test_explicit_mappings_and_receipt_propagate_actual_proof_dependencies(self):
        result = self.evaluate()
        self.assertEqual(result.status, "CONDITIONAL_INFORMATION_PROJECTION")
        self.assertEqual(result.supports, (Support(frozenset(self.active), frozenset(self.live)),))
        self.assertNotIn("belief", result.status.lower())
        self.assertFalse(hasattr(self.alice, "access_policy"))

    def test_late_disclosure_does_not_rewrite_earlier_access(self):
        late = replace(self.edges[1], left="query", right="receipt")
        temporal = TemporalNetwork(
            self.points, (self.edges[0], late), active_assumptions=self.active, verified_bridges={"clock-map"}
        )
        result = self.evaluate(temporal_network=temporal)
        self.assertEqual(result.status, "UNRESOLVED")
        self.assertIn("AGENT_ACCESS_OUTSIDE_VIEW", result.obligations)
        self.assertFalse(result.supports)
        self.assertTrue(self.evaluate().supports)
        self.assertFalse(self.evaluate(records_by_root={}).supports)

    def test_identity_retraction_nogood_and_missing_root_invalidate_bridge_only(self):
        self.assertFalse(self.evaluate(identity_graph=graph()).supports)
        for missing in self.live:
            with self.subTest(missing=missing):
                self.assertFalse(self.evaluate(live_roots=self.live - {missing}).supports)
        self.assertFalse(self.evaluate(active_assumptions=self.active - {"clock"}).supports)
        bad = graph(
            (hypothesis("ab", "a", "b"),), active_assumptions=self.active, nogoods=({"ab", "assume-bridge"},)
        )
        self.assertFalse(self.evaluate(identity_graph=bad).supports)

    def test_viewpoint_frame_time_and_nested_scope_cannot_be_implicitly_relabelled(self):
        for changes in (
            {"target_scope": replace(self.target, perspective_id="bob")},
            {"target_perspective": replace(self.alice, perspective_id="bob")},
            {"target_scope": replace(self.target, at_point="event")},
        ):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.evaluate(**changes)
        with self.assertRaises(ValueError):
            replace(self.bridge, entity_mapping=(("a", "b"), ("a", "c")))
        changed = replace(self.target, at_point="event")
        result = self.evaluate(target_scope=changed, target_perspective=replace(self.alice, at_point="event"))
        self.assertIn("MISSING_TIME_MAPPING", result.obligations)
        self.assertFalse(result.supports)

    def test_analyst_view_does_not_implicitly_establish_character_belief(self):
        analyst_target = replace(self.alice, agent_id=None)
        result = self.evaluate(target_perspective=analyst_target, records_by_root={})
        self.assertEqual(result.status, "CONDITIONAL_INFORMATION_PROJECTION")
        self.assertEqual(
            result.supports[0].roots, frozenset({"source-evidence", "bridge-evidence", "evidence:ab"})
        )

    def test_nested_viewpoint_projection_stays_unresolved(self):
        result = self.evaluate(target_perspective=replace(self.alice, nested_path=("bob",)))
        self.assertFalse(result.supports)
        self.assertIn("NESTED_VIEWPOINT_PROJECTION_UNRESOLVED", result.obligations)

    def test_receipt_identity_has_independent_early_and_late_alternatives(self):
        active = self.active | {"alias"}
        identity = IdentityGraph(
            entities("a", "b", "alice", "alias"),
            (hypothesis("ab", "a", "b"), hypothesis("alias", "alice", "alias")),
            active_assumptions=active,
        )
        registry = self.points + (TimePoint("late", "AGENT_ACCESS", "world", "alias"),)
        late = TemporalConstraint(
            "late-receipt",
            "query",
            "late",
            strict=True,
            evidence_roots=("late-evidence",),
            bridge_id="clock-map",
        )
        network = TemporalNetwork(
            registry, self.edges + (late,), active_assumptions=active, verified_bridges={"clock-map"}
        )
        record = replace(
            self.records["source-evidence"], agent_access_end={"alice": "receipt", "alias": "late"}
        )
        result = self.evaluate(
            identity_graph=identity,
            temporal_network=network,
            active_assumptions=active,
            live_roots=self.live | {"evidence:alias", "late-evidence"},
            records_by_root={"source-evidence": record},
        )
        self.assertEqual(result.status, "CONDITIONAL_INFORMATION_PROJECTION")
        self.assertNotIn("alias", result.supports[0].assumptions)
        alias_only = replace(record, agent_access_end={"alias": "late"})
        self.assertFalse(
            self.evaluate(
                identity_graph=identity,
                temporal_network=network,
                active_assumptions=active,
                live_roots=self.live | {"evidence:alias", "late-evidence"},
                records_by_root={"source-evidence": alias_only},
            ).supports
        )
        early = replace(late, left="late", right="query")
        network = TemporalNetwork(
            registry, self.edges + (early,), active_assumptions=active, verified_bridges={"clock-map"}
        )
        result = self.evaluate(
            identity_graph=identity,
            temporal_network=network,
            active_assumptions=active,
            live_roots=self.live | {"evidence:alias", "late-evidence"},
            records_by_root={"source-evidence": alias_only},
        )
        self.assertTrue(result.supports)
        self.assertIn("alias", result.supports[0].assumptions)
        self.assertIn("evidence:alias", result.supports[0].roots)

    def test_identity_total_budget_is_shared_and_cached_queries_do_not_spend_twice(self):
        identity = graph(
            (hypothesis("ab", "a", "b"), hypothesis("bc", "b", "c")),
            active_assumptions={"ab", "bc"},
            max_total_work=1,
        )
        first = identity.paths("a", "c")
        self.assertTrue(first.frontier_unexplored)
        self.assertEqual(identity.total_work, 1)
        self.assertIs(identity.paths("a", "c"), first)
        second = identity.paths("b", "c")
        self.assertTrue(second.frontier_unexplored)
        self.assertEqual(second.work, 0)
        self.assertEqual(identity.total_work, 1)
        self.assertFalse(identity.paths("a", "a").frontier_unexplored)
        with self.assertRaises(ValueError):
            IdentityGraph((replace(entities("a")[0], entity_id=[]),), ())
        with self.assertRaises(ValueError):
            graph((replace(hypothesis("ab", "a", "b"), hypothesis_id=[]),))

    def test_internal_lineage_without_any_material_report_cannot_project_absence(self):
        result = evaluate_bridge(
            self.bridge,
            Support(frozenset(), frozenset({"source-evidence"})),
            source_scope=self.source,
            target_scope=self.target,
            source_perspective=self.analyst,
            target_perspective=self.alice,
            identity_graph=self.identity,
            temporal_network=self.temporal,
            records_by_root=self.records,
            active_assumptions=self.active,
            live_roots=self.live,
            nonmaterial_roots={"source-evidence"},
        )
        self.assertFalse(result.supports)
        self.assertIn("NO_MATERIAL_SOURCE_EVIDENCE", result.obligations)
