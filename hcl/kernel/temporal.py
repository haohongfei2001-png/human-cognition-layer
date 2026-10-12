"""Exact bounded relative-time constraints, separate from source presentation.

All timepoints and constraints are explicitly proposed input. No calendar or
agent access is inferred from narrative order, storage revision or an ACL.
"""

from dataclasses import dataclass
from fractions import Fraction
from types import MappingProxyType

from hcl.kernel.scope import identifier
from hcl.kernel.types import freeze

AXES = frozenset({"EVENT", "AGENT_ACCESS", "RECORDED_AT", "NARRATIVE_ORDER", "CONCEPT_EFFECTIVE"})


@dataclass(frozen=True)
class TemporalProfile:
    max_points: int = 64
    max_constraints: int = 512
    max_relaxations: int = 300000
    max_proof_edges: int = 256

    def __post_init__(self):
        for name, high in (
            ("max_points", 128),
            ("max_constraints", 4096),
            ("max_relaxations", 2500000),
            ("max_proof_edges", 2048),
        ):
            value = getattr(self, name)
            if type(value) is not int or not 1 <= value <= high:
                raise ValueError("bounded temporal profile required")


@dataclass(frozen=True)
class TimePoint:
    point_id: str
    axis: str
    scope_id: str
    agent_id: str | None = None


@dataclass(frozen=True)
class TemporalConstraint:
    constraint_id: str
    left: str
    right: str
    numerator: int = 0
    denominator: int = 1
    strict: bool = False
    assumptions: frozenset[str] = frozenset()
    evidence_roots: tuple[str, ...] = ()
    bridge_id: str | None = None

    def __post_init__(self):
        object.__setattr__(self, "assumptions", frozenset(self.assumptions))
        object.__setattr__(self, "evidence_roots", tuple(self.evidence_roots))


def _validated_graph(points, constraints, profile, active_assumptions, verified_bridges):
    """Validate all candidates, then return only enabled constraint edges."""
    points, constraints = tuple(points), tuple(constraints)
    if not 1 <= len(points) <= profile.max_points or len(constraints) > profile.max_constraints:
        raise ValueError("temporal graph bound exceeded")
    registry = {}
    for point in points:
        if (
            type(point) is not TimePoint
            or type(point.point_id) is not str
            or point.point_id in registry
            or type(point.axis) is not str
            or point.axis not in AXES
        ):
            raise ValueError("invalid timepoint")
        identifier(point.point_id)
        identifier(point.scope_id)
        if point.axis == "AGENT_ACCESS":
            identifier(point.agent_id)
        elif point.agent_id is not None:
            raise ValueError("only agent-access clocks identify a story agent")
        registry[point.point_id] = point
    active_assumptions, verified_bridges = frozenset(active_assumptions), frozenset(verified_bridges)
    for value in active_assumptions | verified_bridges:
        identifier(value)
    edges, seen = [], set()
    for edge in constraints:
        if (
            type(edge) is not TemporalConstraint
            or edge.constraint_id in seen
            or edge.left not in registry
            or edge.right not in registry
            or type(edge.strict) is not bool
            or type(edge.numerator) is not int
            or abs(edge.numerator) > 10**12
            or type(edge.denominator) is not int
            or not 1 <= edge.denominator <= 10**9
            or (edge.bridge_id is not None and type(edge.bridge_id) is not str)
            or not edge.evidence_roots
            or len(edge.evidence_roots) != len(set(edge.evidence_roots))
        ):
            raise ValueError("invalid temporal constraint")
        identifier(edge.constraint_id)
        seen.add(edge.constraint_id)
        for value in (*edge.evidence_roots, *edge.assumptions):
            identifier(value)
        left, right = registry[edge.left], registry[edge.right]
        if (
            left.axis != right.axis or left.scope_id != right.scope_id or left.agent_id != right.agent_id
        ) and edge.bridge_id not in verified_bridges:
            raise ValueError("explicit validated temporal bridge required")
        if edge.bridge_id is not None and edge.bridge_id not in verified_bridges:
            raise ValueError("unknown temporal bridge")
        if edge.assumptions <= active_assumptions:
            edges.append(edge)
    return registry, tuple(edges)


class TemporalNetwork:
    """Floyd–Warshall over exact rational bounds plus a strictness bit.

    An edge is left - right <= numerator/denominator, or strict <. Strictness
    composes with OR; no arbitrary epsilon or calendar discretization is used.
    Cross-axis/scope edges require a bridge already checked by the scoped core.
    """

    def __init__(
        self,
        points,
        constraints,
        *,
        active_assumptions=frozenset(),
        verified_bridges=frozenset(),
        profile=None
    ):
        self.profile = profile or TemporalProfile()
        if type(self.profile) is not TemporalProfile:
            raise ValueError("typed temporal profile required")
        points, constraints = tuple(points), tuple(constraints)
        registry, edges = _validated_graph(
            points, constraints, self.profile, active_assumptions, verified_bridges
        )
        self.points = MappingProxyType(registry)
        self.constraints = tuple(edges)
        self.inactive_constraint_ids = tuple(edge.constraint_id for edge in constraints if edge not in edges)
        self.distance = {(a, b): ((Fraction(0), 0) if a == b else None) for a in registry for b in registry}
        self.paths = {(a, b): () for a in registry for b in registry}
        self.work = 0
        self.status = "CONSISTENT"
        self.conflict = ()
        for edge in sorted(edges, key=lambda edge: edge.constraint_id):
            key = (edge.right, edge.left)
            cost = (Fraction(edge.numerator, edge.denominator), -int(edge.strict))
            if self.distance[key] is None or cost < self.distance[key]:
                self.distance[key] = cost
                self.paths[key] = (edge.constraint_id,)
                if key[0] == key[1] and cost < (0, 0):
                    self.status = "TEMPORAL_CONFLICT"
                    self.conflict = self.paths[key]
                    return
        for k in sorted(registry):
            for a in sorted(registry):
                for b in sorted(registry):
                    x, y = self.distance[a, k], self.distance[k, b]
                    if x is None or y is None:
                        continue
                    if self.work >= self.profile.max_relaxations:
                        self.status = "FRONTIER_UNEXPLORED"
                        return
                    self.work += 1
                    cost = (x[0] + y[0], min(x[1], y[1]))
                    if self.distance[a, b] is None or cost < self.distance[a, b]:
                        if len(self.paths[a, k]) + len(self.paths[k, b]) > self.profile.max_proof_edges:
                            self.status = "FRONTIER_UNEXPLORED"
                            return
                        self.distance[a, b] = cost
                        self.paths[a, b] = self.paths[a, k] + self.paths[k, b]
                        if a == b and cost < (0, 0):
                            self.status = "TEMPORAL_CONFLICT"
                            self.conflict = self.paths[a, b]
                            return

    def check(self, left, right, *, numerator=0, denominator=1, strict=False):
        if (
            left not in self.points
            or right not in self.points
            or type(numerator) is not int
            or abs(numerator) > 10**12
            or type(denominator) is not int
            or not 1 <= denominator <= 10**9
            or type(strict) is not bool
        ):
            raise ValueError("bounded known relative-time query required")
        if self.status != "CONSISTENT":
            return {"status": self.status, "witness": self.conflict}
        upper = Fraction(numerator, denominator)
        bound = self.distance[right, left]
        if bound is not None and bound <= (upper, -int(strict)):
            return {"status": "ENTAILED", "witness": self.paths[right, left]}
        # Negation of x-y <= c is y-x < -c; strict < negates to <=.
        reverse = self.distance[left, right]
        if reverse is not None and reverse <= (-upper, -int(not strict)):
            return {"status": "REFUTED", "witness": self.paths[left, right]}
        return {"status": "UNRESOLVED", "witness": ()}

    def verify_witness(self, left, right, witness, *, numerator=0, denominator=1, strict=False):
        """Independently sum a returned original-edge path, not closure entries."""
        by_id = {edge.constraint_id: edge for edge in self.constraints}
        current, value, is_strict = right, Fraction(0), False
        for identity in witness:
            edge = by_id.get(identity)
            if edge is None or edge.right != current:
                return False
            value += Fraction(edge.numerator, edge.denominator)
            is_strict = is_strict or edge.strict
            current = edge.left
        return current == left and (value, -int(is_strict)) <= (
            Fraction(numerator, denominator),
            -int(strict),
        )


@dataclass(frozen=True)
class TemporalRecord:
    record_id: str
    version: int
    recorded_at: int
    event_end: str | None
    agent_access_end: object
    payload: object

    def __post_init__(self):
        access = dict(self.agent_access_end)
        if len(access) > 64:
            raise ValueError("bounded explicit agent access records required")
        for agent, point in access.items():
            identifier(agent)
            identifier(point)
        if self.event_end is not None:
            identifier(self.event_end)
        object.__setattr__(self, "agent_access_end", MappingProxyType(access))
        object.__setattr__(self, "payload", freeze(self.payload))


def select_versions(records, *, known_at):
    """Choose correction before event/access filtering; never resurrect old data.

    recorded_at is a separate authenticated ledger clock. It is not inserted
    into the relative event-time graph or treated as a character's access time.
    """
    if type(known_at) is not int or known_at < 0:
        raise ValueError("bounded recorded-at cutoff required")
    records = tuple(records)
    if any(type(row) is not TemporalRecord for row in records):
        raise ValueError("typed temporal records required")
    selected, identities, last_times = {}, set(), {}
    for row in sorted(records, key=lambda row: (row.record_id, row.version)):
        if (
            type(row) is not TemporalRecord
            or type(row.version) is not int
            or row.version < 1
            or type(row.recorded_at) is not int
            or row.recorded_at < 0
            or (row.record_id, row.version) in identities
        ):
            raise ValueError("invalid temporal record")
        identifier(row.record_id)
        identities.add((row.record_id, row.version))
        if row.record_id in last_times and row.recorded_at <= last_times[row.record_id]:
            raise ValueError("correction must have later recorded time")
        last_times[row.record_id] = row.recorded_at
        if row.recorded_at <= known_at:
            selected[row.record_id] = row
    return tuple(selected[key] for key in sorted(selected))


def record_eligibility(row, network, *, at_point, agent_id=None):
    """Conservative historical occurrence/access check, never an ACL decision."""
    if at_point not in network.points or network.points[at_point].axis != "EVENT":
        raise ValueError("explicit event-time query point required")
    if row.event_end is not None and (
        row.event_end not in network.points or network.points[row.event_end].axis != "EVENT"
    ):
        raise ValueError("event time cannot be a record or narrative clock")
    for agent, point in row.agent_access_end.items():
        if (
            point not in network.points
            or network.points[point].axis != "AGENT_ACCESS"
            or network.points[point].agent_id != agent
        ):
            raise ValueError("access time must belong to this explicit story agent")
    obligations = []
    if row.event_end is None:
        obligations.append({"axis": "EVENT", "status": "UNRESOLVED", "witness": ()})
    else:
        obligations.append({"axis": "EVENT", **network.check(row.event_end, at_point)})
    if agent_id is not None:
        access = row.agent_access_end.get(agent_id)
        obligations.append(
            {"axis": "AGENT_ACCESS", **network.check(access, at_point)}
            if access is not None
            else {"axis": "AGENT_ACCESS", "status": "UNRESOLVED", "witness": ()}
        )
    statuses = {row["status"] for row in obligations}
    status = (
        "ELIGIBLE" if statuses == {"ENTAILED"} else "OUTSIDE_VIEW" if "REFUTED" in statuses else "UNRESOLVED"
    )
    return {
        "status": status,
        "obligations": obligations,
        "scope": "PROPOSED_EVENT_AND_ACCESS_TIMES_NOT_BELIEF_OR_SYSTEM_PERMISSION",
    }


class TemporalForest:
    """Independent constraint components share one bounded work allowance.

    An inconsistent clock component cannot erase conclusions about an unrelated
    person/time component. Disconnected points have unknown ordering.
    """

    def __init__(
        self,
        points,
        constraints,
        *,
        active_assumptions=frozenset(),
        verified_bridges=frozenset(),
        nogoods=(),
        profile=None
    ):
        self.profile = profile or TemporalProfile()
        if type(self.profile) is not TemporalProfile:
            raise ValueError("typed temporal profile required")
        points, constraints = tuple(points), tuple(constraints)
        if (
            len(points) > self.profile.max_points
            or len(constraints) > self.profile.max_constraints
            or any(type(point) is not TimePoint for point in points)
            or any(type(edge) is not TemporalConstraint for edge in constraints)
        ):
            raise ValueError("bounded typed temporal forest required")
        registry, enabled = _validated_graph(
            points, constraints, self.profile, active_assumptions, verified_bridges
        )
        adjacency = {key: set() for key in registry}
        for edge in enabled:
            if edge.left not in registry or edge.right not in registry:
                raise ValueError("known temporal endpoints required")
            adjacency[edge.left].add(edge.right)
            adjacency[edge.right].add(edge.left)
        self.points = MappingProxyType(registry)
        self.constraints = constraints
        self.components = {}
        self.work = 0
        self.nogoods = tuple(frozenset(value) for value in nogoods)
        for start in sorted(registry):
            if start in self.components:
                continue
            component = {start}
            queue = [start]
            while queue:
                for neighbor in sorted(adjacency[queue.pop()]):
                    if neighbor not in component:
                        component.add(neighbor)
                        queue.append(neighbor)
            edges = tuple(edge for edge in enabled if edge.left in component)
            remaining = self.profile.max_relaxations - self.work
            network = TemporalNetwork(
                tuple(registry[key] for key in sorted(component)),
                edges,
                active_assumptions=active_assumptions,
                verified_bridges=verified_bridges,
                profile=TemporalProfile(
                    self.profile.max_points,
                    self.profile.max_constraints,
                    max(1, remaining),
                    self.profile.max_proof_edges,
                ),
            )
            if remaining <= 0:
                network.status = "FRONTIER_UNEXPLORED"
                network.work = 0
            self.work += network.work
            # A conflict requiring incompatible proposed hypotheses is unresolved
            # branching, not an unconditional temporal inconsistency.
            if network.status == "TEMPORAL_CONFLICT":
                by_id = {edge.constraint_id: edge for edge in edges}
                used = frozenset().union(*(by_id[key].assumptions for key in network.conflict))
                if any(nogood <= used for nogood in self.nogoods):
                    network.status = "HYPOTHESIS_BRANCHING_UNEXPLORED"
            for key in component:
                self.components[key] = network

    def check(self, left, right, **kwargs):
        if left not in self.components or right not in self.components:
            raise ValueError("known timepoints required")
        network = self.components[left]
        if network is not self.components[right]:
            return {"status": "UNRESOLVED", "witness": ()}
        result = network.check(left, right, **kwargs)
        by_id = {edge.constraint_id: edge for edge in network.constraints}
        used = frozenset().union(*(by_id[key].assumptions for key in result["witness"]))
        if any(nogood <= used for nogood in self.nogoods):
            return {"status": "HYPOTHESIS_BRANCHING_UNEXPLORED", "witness": ()}
        return result

    def verify_witness(self, left, right, witness, **kwargs):
        return (
            left in self.components
            and right in self.components
            and self.components[left] is self.components[right]
            and self.components[left].verify_witness(left, right, witness, **kwargs)
        )
