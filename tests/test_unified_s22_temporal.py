"""Real relative constraint closure and independent finite oracle contrasts."""

from dataclasses import replace
from fractions import Fraction
import itertools
import unittest

from hcl.kernel.temporal import (
    TemporalConstraint,
    TemporalNetwork,
    TemporalProfile,
    TemporalRecord,
    TimePoint,
    record_eligibility,
    select_versions,
)


def edge(identity, left, right, upper=0, **kwargs):
    return TemporalConstraint(identity, left, right, upper, evidence_roots=("source:" + identity,), **kwargs)


def points(*names):
    return tuple(TimePoint(name, "EVENT", "source-frame") for name in names)


class TemporalKernelTests(unittest.TestCase):
    def test_relative_intervals_strict_paths_and_independent_proof_sum(self):
        network = TemporalNetwork(
            points("depart", "arrive", "receive", "unrelated"),
            (
                edge("min-travel", "depart", "arrive", -2),
                edge("max-travel", "arrive", "depart", 4),
                edge("receive-later", "arrive", "receive", strict=True),
            ),
        )
        result = network.check("depart", "receive", strict=True)
        self.assertEqual(result["status"], "ENTAILED")
        self.assertTrue(network.verify_witness("depart", "receive", result["witness"], strict=True))
        self.assertFalse(network.verify_witness("receive", "depart", result["witness"], strict=True))
        self.assertEqual(network.check("receive", "depart")["status"], "REFUTED")
        self.assertEqual(network.check("unrelated", "depart")["status"], "UNRESOLVED")

    def test_rational_strictness_has_no_epsilon_rounding(self):
        network = TemporalNetwork(
            points("a", "b", "c"), (edge("ab", "a", "b", 1, denominator=3, strict=True), edge("bc", "b", "c"))
        )
        result = network.check("a", "c", numerator=1, denominator=3, strict=True)
        self.assertEqual(result["status"], "ENTAILED")
        self.assertTrue(
            network.verify_witness("a", "c", result["witness"], numerator=1, denominator=3, strict=True)
        )
        self.assertEqual(network.check("c", "a", numerator=-1, denominator=3)["status"], "REFUTED")
        self.assertEqual(network.check("a", "c", numerator=1, denominator=4)["status"], "UNRESOLVED")

    def test_conflicts_and_unknown_order_do_not_become_global_conclusions(self):
        network = TemporalNetwork(points("a", "b"), (edge("ab", "a", "b", strict=True), edge("ba", "b", "a")))
        self.assertEqual(network.status, "TEMPORAL_CONFLICT")
        self.assertEqual(network.check("a", "b")["status"], "TEMPORAL_CONFLICT")
        first = {row.constraint_id: row for row in network.constraints}[network.conflict[0]]
        self.assertTrue(network.verify_witness(first.right, first.right, network.conflict, strict=True))
        unrelated = TemporalNetwork(points("a", "b"), ())
        self.assertEqual(unrelated.check("a", "b")["status"], "UNRESOLVED")
        self.assertEqual(unrelated.check("b", "a")["status"], "UNRESOLVED")

    def test_axes_and_perspective_scopes_need_explicit_validated_bridge(self):
        registry = (
            TimePoint("event", "EVENT", "world"),
            TimePoint("order", "NARRATIVE_ORDER", "world"),
            TimePoint("access", "AGENT_ACCESS", "world", "张三"),
            TimePoint("record", "RECORDED_AT", "analyst"),
        )
        for other in ("order", "access", "record"):
            with self.subTest(other=other), self.assertRaises(ValueError):
                TemporalNetwork(registry, (edge("implicit", other, "event"),))
        explicit = replace(edge("mapped", "access", "event"), bridge_id="clock-map")
        with self.assertRaises(ValueError):
            TemporalNetwork(registry, (explicit,))
        network = TemporalNetwork(registry, (explicit,), verified_bridges={"clock-map"})
        self.assertEqual(network.check("access", "event")["status"], "ENTAILED")
        self.assertEqual(network.check("order", "event")["status"], "UNRESOLVED")
        self.assertEqual(network.check("record", "event")["status"], "UNRESOLVED")

    def test_withdrawn_temporal_assumption_removes_only_its_constraint(self):
        relation = edge("ab", "a", "b", strict=True, assumptions={"clock-hypothesis"})
        active = TemporalNetwork(points("a", "b"), (relation,), active_assumptions={"clock-hypothesis"})
        inactive = TemporalNetwork(points("a", "b"), (relation,))
        self.assertEqual(active.check("a", "b", strict=True)["status"], "ENTAILED")
        self.assertEqual(inactive.check("a", "b", strict=True)["status"], "UNRESOLVED")
        self.assertEqual(inactive.inactive_constraint_ids, ("ab",))

    def test_record_correction_selected_before_historical_time_filter(self):
        registry = points("early", "query", "late") + (
            TimePoint("access-old", "AGENT_ACCESS", "source-frame", "张三"),
            TimePoint("access-new", "AGENT_ACCESS", "source-frame", "张三"),
        )
        network = TemporalNetwork(
            registry,
            (
                edge("early-query", "early", "query", strict=True),
                edge("query-late", "query", "late", strict=True),
                replace(edge("old-access", "access-old", "query", strict=True), bridge_id="times"),
                replace(edge("new-access", "query", "access-new", strict=True), bridge_id="times"),
            ),
            verified_bridges={"times"},
        )
        first = TemporalRecord(
            "report", 1, 2, "early", {"张三": "access-old"}, {"text": "original candidate"}
        )
        correction = TemporalRecord(
            "report", 2, 7, "late", {"张三": "access-new"}, {"text": "corrected candidate"}
        )
        old = select_versions((first, correction), known_at=3)
        current = select_versions((first, correction), known_at=8)
        self.assertEqual(old, (first,))
        self.assertEqual(current, (correction,))
        self.assertEqual(
            record_eligibility(old[0], network, at_point="query", agent_id="张三")["status"], "ELIGIBLE"
        )
        self.assertEqual(
            record_eligibility(current[0], network, at_point="query", agent_id="张三")["status"],
            "OUTSIDE_VIEW",
        )
        self.assertEqual(old, select_versions((first, correction), known_at=3))

    def test_late_disclosure_cannot_backfill_agent_access_or_belief(self):
        registry = (
            TimePoint("event", "EVENT", "world"),
            TimePoint("query", "EVENT", "world"),
            TimePoint("access-late", "AGENT_ACCESS", "world", "alice"),
            TimePoint("access-early", "AGENT_ACCESS", "world", "alice"),
        )
        constraints = (
            edge("event-before", "event", "query", strict=True),
            replace(edge("late-access", "query", "access-late", strict=True), bridge_id="times"),
            replace(edge("early-access", "access-early", "query", strict=True), bridge_id="times"),
        )
        network = TemporalNetwork(registry, constraints, verified_bridges={"times"})
        disclosure = TemporalRecord(
            "disclosure", 1, 9, "event", {"alice": "access-late"}, {"report": "received later"}
        )
        self.assertFalse(select_versions((disclosure,), known_at=8))
        self.assertEqual(
            record_eligibility(disclosure, network, at_point="query", agent_id="alice")["status"],
            "OUTSIDE_VIEW",
        )
        self.assertEqual(record_eligibility(disclosure, network, at_point="query")["status"], "ELIGIBLE")
        self.assertEqual(
            record_eligibility(disclosure, network, at_point="query", agent_id="bob")["status"], "UNRESOLVED"
        )
        earlier_receipt_evidence = replace(
            disclosure, version=2, recorded_at=10, agent_access_end={"alice": "access-early"}
        )
        now = select_versions((disclosure, earlier_receipt_evidence), known_at=10)[0]
        self.assertEqual(
            record_eligibility(now, network, at_point="query", agent_id="alice")["status"], "ELIGIBLE"
        )
        self.assertEqual(select_versions((disclosure, earlier_receipt_evidence), known_at=9), (disclosure,))
        self.assertIn(
            "NOT_BELIEF_OR_SYSTEM_PERMISSION", record_eligibility(now, network, at_point="query")["scope"]
        )

    def test_record_and_other_agent_clocks_cannot_be_relabelled_access(self):
        registry = (
            TimePoint("event", "EVENT", "world"),
            TimePoint("query", "EVENT", "world"),
            TimePoint("record", "RECORDED_AT", "analyst"),
            TimePoint("bob-access", "AGENT_ACCESS", "world", "bob"),
        )
        network = TemporalNetwork(registry, (edge("event-before", "event", "query"),))
        for point in ("event", "record", "bob-access"):
            row = TemporalRecord("r", 1, 1, "event", {"alice": point}, {})
            with self.subTest(point=point), self.assertRaises(ValueError):
                record_eligibility(row, network, at_point="query", agent_id="alice")
        with self.assertRaises(ValueError):
            record_eligibility(TemporalRecord("r", 1, 1, "record", {}, {}), network, at_point="query")

    def test_work_bound_never_reports_consistency_as_proved(self):
        network = TemporalNetwork(
            points("a", "b"), (edge("ab", "a", "b"),), profile=TemporalProfile(max_relaxations=1)
        )
        self.assertEqual(network.status, "FRONTIER_UNEXPLORED")
        self.assertEqual(network.work, 1)
        self.assertEqual(network.check("a", "b")["status"], "FRONTIER_UNEXPLORED")

    def test_125_connected_systems_agree_with_independent_assignment_oracle(self):
        for ab, bc, ca in itertools.product(range(-2, 3), repeat=3):
            constraints = (edge("ab", "a", "b", ab), edge("bc", "b", "c", bc), edge("ca", "c", "a", ca))
            network = TemporalNetwork(points("a", "b", "c"), constraints)
            feasible = [
                (b, c)
                for b, c in itertools.product(range(-6, 7), repeat=2)
                if -b <= ab and b - c <= bc and c <= ca
            ]
            self.assertEqual(network.status == "TEMPORAL_CONFLICT", not feasible)
            if feasible:
                values = {-b <= 0 for b, c in feasible}
                expected = (
                    "ENTAILED" if values == {True} else "REFUTED" if values == {False} else "UNRESOLVED"
                )
                self.assertEqual(network.check("a", "b")["status"], expected)
                if expected == "ENTAILED":
                    self.assertTrue(network.verify_witness("a", "b", network.check("a", "b")["witness"]))

    def test_invalid_points_bounds_and_record_order_are_rejected(self):
        invalid = [
            (points("a", "a"), ()),
            (points("a", "b"), (edge("bad", "a", "b", denominator=0),)),
            (points("a", "b"), (replace(edge("bad", "a", "b"), evidence_roots=()),)),
        ]
        for registry, constraints in invalid:
            with self.subTest(registry=registry), self.assertRaises(ValueError):
                TemporalNetwork(registry, constraints)
        first = TemporalRecord("r", 1, 3, None, {}, {})
        with self.assertRaises(ValueError):
            select_versions((first, replace(first, version=2, recorded_at=2)), known_at=4)
        with self.assertRaises(ValueError):
            select_versions((object(),), known_at=4)


class TemporalForestTests(unittest.TestCase):
    def test_conflict_is_local_and_inactive_bridge_cannot_join_components(self):
        from hcl.kernel.temporal import TemporalForest

        constraints = (
            edge("bad-ab", "a", "b", strict=True),
            edge("bad-ba", "b", "a"),
            edge("good-cd", "c", "d", strict=True),
            edge("inactive-bc", "b", "c", assumptions={"withdrawn"}),
        )
        forest = TemporalForest(points("a", "b", "c", "d"), constraints)
        self.assertEqual(forest.check("a", "b")["status"], "TEMPORAL_CONFLICT")
        result = forest.check("c", "d", strict=True)
        self.assertEqual(result["status"], "ENTAILED")
        self.assertTrue(forest.verify_witness("c", "d", result["witness"], strict=True))
        self.assertEqual(forest.check("a", "c")["status"], "UNRESOLVED")

    def test_incompatible_hypothesis_path_and_cycle_are_unexplored(self):
        from hcl.kernel.temporal import TemporalForest

        constraints = (edge("ab", "a", "b", assumptions={"h1"}), edge("bc", "b", "c", assumptions={"h2"}))
        forest = TemporalForest(
            points("a", "b", "c"), constraints, active_assumptions={"h1", "h2"}, nogoods=({"h1", "h2"},)
        )
        self.assertEqual(forest.check("a", "c")["status"], "HYPOTHESIS_BRANCHING_UNEXPLORED")
        self.assertEqual(forest.check("a", "b")["status"], "ENTAILED")
        cyclic = constraints + (edge("ca", "c", "a", strict=True),)
        forest = TemporalForest(
            points("a", "b", "c"), cyclic, active_assumptions={"h1", "h2"}, nogoods=({"h1", "h2"},)
        )
        self.assertEqual(forest.check("a", "c")["status"], "HYPOTHESIS_BRANCHING_UNEXPLORED")

    def test_global_work_is_bounded_and_inactive_constraints_still_validated(self):
        from hcl.kernel.temporal import TemporalForest

        forest = TemporalForest(points("a", "b", "c"), (), profile=TemporalProfile(max_relaxations=1))
        self.assertEqual(forest.work, 1)
        self.assertEqual(forest.check("a", "a")["status"], "ENTAILED")
        self.assertEqual(forest.check("c", "c")["status"], "FRONTIER_UNEXPLORED")
        with self.assertRaises(ValueError):
            TemporalForest(
                points("a", "b"), (edge("bad", "a", "b", denominator=0, assumptions={"inactive"}),)
            )
        with self.assertRaises(ValueError):
            TemporalRecord("r", 1, 1, None, {str(n): "point" for n in range(65)}, {})
