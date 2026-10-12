"""Explicit, bounded retrieval questions and recorded-graph evidence contracts."""
from collections.abc import Mapping
from dataclasses import dataclass
import re

from .scope import identifier
from .types import Issue, freeze, thaw

RETRIEVAL_VERSION = "hcl-evidence-retrieval-1"
ROUTES = ("support", "challenge", "alternative")


@dataclass(frozen=True)
class RetrievalQuery:
    queries: object
    source_scope: tuple[str, ...] | None = None
    seed_nodes: tuple[str, ...] = ()
    evidence_result_ids: tuple[str, ...] = ()
    max_hits_per_route: int = 8
    max_nodes: int = 256
    max_characters: int = 65536
    version: str = RETRIEVAL_VERSION

    def __post_init__(self):
        if self.version != RETRIEVAL_VERSION or not isinstance(self.queries, Mapping) or set(self.queries) != set(ROUTES):
            raise ValueError("three explicit retrieval routes required")
        for query in self.queries.values():
            identifier(query)
            if len(query) > 8192:
                raise ValueError("bounded retrieval query text required")
        for key, maximum in (("max_hits_per_route", 128), ("max_nodes", 4096), ("max_characters", 1048576)):
            value = getattr(self, key)
            if type(value) is not int or not 0 <= value <= maximum:
                raise ValueError("bounded retrieval allowance required")
        object.__setattr__(self, "queries", freeze(self.queries))
        for key, limit in (("source_scope", 1024), ("seed_nodes", 128), ("evidence_result_ids", 128)):
            values = getattr(self, key)
            if values is None and key == "source_scope":
                continue
            if type(values) not in (tuple, list) or len(values) > limit or len(set(values)) != len(values):
                raise ValueError("bounded unique retrieval identifiers required")
            for value in values:
                identifier(value)
            object.__setattr__(self, key, tuple(sorted(values)))

    # The shared dependency validator also supports the older history selector.
    # Retrieval 1 has no implied historical snapshot or current-world absence.
    history = False
    source_only = False
    known_at = None

    def wire(self):
        return dict(queries=thaw(self.queries), source_scope=None if self.source_scope is None else list(self.source_scope),
                    seed_nodes=list(self.seed_nodes), evidence_result_ids=list(self.evidence_result_ids), max_hits_per_route=self.max_hits_per_route,
                    max_nodes=self.max_nodes, max_characters=self.max_characters, version=self.version)


@dataclass(frozen=True)
class RetrievalDependency:
    query: RetrievalQuery
    digest: str
    index_version: str = RETRIEVAL_VERSION

    def __post_init__(self):
        if (type(self.query) is not RetrievalQuery or type(self.digest) is not str
                or re.fullmatch("[0-9a-f]{64}", self.digest) is None
                or self.index_version != RETRIEVAL_VERSION):
            raise ValueError("versioned retrieval dependency required")

    def wire(self):
        return dict(retrieval_query=self.query.wire(), digest=self.digest, index_version=self.index_version)


@dataclass(frozen=True)
class RetrievalIssue(Issue):
    kind: str = "memory.retrieve"
    query: RetrievalQuery | None = None


@dataclass(frozen=True)
class EvidenceNode:
    node_id: str
    source_segments: tuple[str, ...]
    support_groups: tuple[tuple[str, ...], ...] = ()
    challenges: tuple[str, ...] = ()
    alternatives: tuple[str, ...] = ()
    revision_reasons: tuple[str, ...] = ()
    qualifications: tuple[str, ...] = ()

    def __post_init__(self):
        identifier(self.node_id)
        for key in ("source_segments", "challenges", "alternatives", "revision_reasons", "qualifications"):
            values = tuple(getattr(self, key))
            if len(values) > 4096:
                raise ValueError("bounded recorded node required")
            for item in values:
                identifier(item)
            object.__setattr__(self, key, tuple(sorted(set(values))))
        groups = tuple(tuple(sorted(set(group))) for group in self.support_groups)
        if len(groups) > 256 or any(len(group) > 4096 for group in groups):
            raise ValueError("bounded support alternatives required")
        for group in groups:
            for item in group:
                identifier(item)
        object.__setattr__(self, "support_groups", tuple(sorted(set(groups))))
