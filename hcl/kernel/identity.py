"""Retractable source-local identity hypotheses, never destructive name merging."""

from collections import deque
from dataclasses import dataclass
from types import MappingProxyType

from hcl.kernel.scope import identifier
from hcl.kernel.truth import Support


@dataclass(frozen=True)
class SourceLocalEntity:
    entity_id: str
    source_id: str
    source_version: int
    label: str
    segment_ids: tuple[str, ...]

    def __post_init__(self):
        object.__setattr__(self, "segment_ids", tuple(self.segment_ids))


@dataclass(frozen=True)
class IdentityHypothesis:
    hypothesis_id: str
    left: str
    right: str
    evidence_roots: frozenset[str]
    assumptions: frozenset[str] = frozenset()
    active: bool = True

    def __post_init__(self):
        object.__setattr__(self, "evidence_roots", frozenset(self.evidence_roots))
        object.__setattr__(self, "assumptions", frozenset(self.assumptions))


@dataclass(frozen=True)
class IdentityPaths:
    supports: tuple[Support, ...]
    frontier_unexplored: bool
    work: int


class IdentityGraph:
    def __init__(
        self,
        entities,
        hypotheses,
        *,
        active_assumptions=frozenset(),
        nogoods=(),
        max_paths=64,
        max_work=10000,
        max_total_work=100000
    ):
        entities, hypotheses = tuple(entities), tuple(hypotheses)
        if (
            not 0 <= len(entities) <= 1024
            or len(hypotheses) > 4096
            or type(max_paths) is not int
            or not 1 <= max_paths <= 256
            or type(max_work) is not int
            or not 1 <= max_work <= 1000000
            or type(max_total_work) is not int
            or not 1 <= max_total_work <= 1000000
        ):
            raise ValueError("bounded identity graph required")
        self.entities = {}
        for entity in entities:
            if (
                type(entity) is not SourceLocalEntity
                or type(entity.entity_id) is not str
                or entity.entity_id in self.entities
                or type(entity.source_version) is not int
                or entity.source_version < 1
                or not entity.segment_ids
            ):
                raise ValueError("source-local entity identity and anchors required")
            for value in (entity.entity_id, entity.source_id, entity.label, *entity.segment_ids):
                identifier(value)
            self.entities[entity.entity_id] = entity
        self.active_assumptions = frozenset(active_assumptions)
        self.nogoods = tuple(frozenset(value) for value in nogoods)
        if (
            len(self.active_assumptions) > 8192
            or len(self.nogoods) > 4096
            or any(not value or len(value) > 8192 for value in self.nogoods)
        ):
            raise ValueError("bounded nonempty nogoods and assumptions required")
        for value in self.active_assumptions | frozenset().union(*self.nogoods):
            identifier(value)
        if any(type(value) is not IdentityHypothesis for value in hypotheses):
            raise ValueError("typed identity hypotheses required")
        self.max_paths, self.max_work = max_paths, max_work
        self.max_total_work, self.total_work, self._cache = max_total_work, 0, {}
        self.adjacency = {key: [] for key in self.entities}
        seen = set()
        for hypothesis in hypotheses:
            for value in (hypothesis.hypothesis_id, hypothesis.left, hypothesis.right):
                identifier(value)
        for hypothesis in sorted(hypotheses, key=lambda value: value.hypothesis_id):
            if (
                type(hypothesis) is not IdentityHypothesis
                or hypothesis.hypothesis_id in seen
                or hypothesis.left not in self.entities
                or hypothesis.right not in self.entities
                or hypothesis.left == hypothesis.right
                or not hypothesis.evidence_roots
                or type(hypothesis.active) is not bool
            ):
                raise ValueError("explicit evidenced identity hypothesis required")
            seen.add(hypothesis.hypothesis_id)
            for value in (hypothesis.hypothesis_id, *hypothesis.evidence_roots, *hypothesis.assumptions):
                identifier(value)
            assumptions = hypothesis.assumptions | {hypothesis.hypothesis_id}
            if hypothesis.active and assumptions <= self.active_assumptions:
                support = Support(assumptions, hypothesis.evidence_roots)
                self.adjacency[hypothesis.left].append((hypothesis.right, support))
                self.adjacency[hypothesis.right].append((hypothesis.left, support))
        self.entities = MappingProxyType(self.entities)
        self.adjacency = MappingProxyType({key: tuple(value) for key, value in self.adjacency.items()})

    def paths(self, left, right):
        identifier(left)
        identifier(right)
        key = (left, right)
        if key not in self._cache:
            result = self._paths(left, right, min(self.max_work, self.max_total_work - self.total_work))
            self.total_work += result.work
            self._cache[key] = result
        return self._cache[key]

    def _paths(self, left, right, work_limit):
        identifier(left)
        identifier(right)
        if left not in self.entities or right not in self.entities:
            raise ValueError("known source-local identities required")
        if left == right:
            return IdentityPaths((Support(frozenset(), frozenset()),), False, 0)
        labels = {key: [] for key in self.entities}
        empty = Support(frozenset(), frozenset())
        labels[left].append(empty)
        queue, work, frontier = deque([(left, empty)]), 0, False
        while queue:
            node, prior = queue.popleft()
            for neighbor, edge in self.adjacency[node]:
                if work >= work_limit:
                    return IdentityPaths(
                        tuple(sorted(labels[right], key=lambda support: support.key())), True, work
                    )
                work += 1
                value = Support(prior.assumptions | edge.assumptions, prior.roots | edge.roots)
                if any(nogood <= value.assumptions for nogood in self.nogoods):
                    continue
                current = labels[neighbor]
                if any(old.assumptions <= value.assumptions and old.roots <= value.roots for old in current):
                    continue
                remaining = [
                    old
                    for old in current
                    if not (value.assumptions <= old.assumptions and value.roots <= old.roots)
                ]
                if len(remaining) >= self.max_paths:
                    frontier = True
                    continue
                labels[neighbor] = remaining + [value]
                queue.append((neighbor, value))
        return IdentityPaths(tuple(sorted(labels[right], key=lambda support: support.key())), frontier, work)
