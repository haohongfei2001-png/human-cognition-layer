"""Versioned positive and query dependencies; absence is indexed coverage only."""

from collections.abc import Mapping
from dataclasses import dataclass
from hashlib import sha256
import re

from hcl.kernel.scope import identifier, version_map
from hcl.kernel.types import Delta, Snapshot, Issue, freeze, thaw

INDEX_VERSION = 1
INDEX_KIND = "revision.source_index"
INDEX_SCHEMA = "hcl-source-revision-index-1"
DEPENDENCY_SCHEMA = "hcl-query-dependencies-1"
QUERY_FIELDS = frozenset(
    {"kind", "agent_id", "message_id", "interval_id", "scope_id", "claim_id", "entity_id"}
)


@dataclass(frozen=True)
class RevisionIssue(Issue):
    kind: str = "revision.evaluate"
    known_at: int | None = None


@dataclass(frozen=True)
class IndexQuery:
    filters: object
    source_scope: tuple[str, ...] | None = None
    history: bool = False
    known_at: int | None = None
    source_only: bool = False

    def __post_init__(self):
        if (self.known_at is not None and (type(self.known_at) is not int or self.known_at < 0)) or type(
            self.source_only
        ) is not bool:
            raise ValueError("typed recorded cutoff/source selector required")
        if (self.known_at is not None or self.source_only) and not self.history:
            raise ValueError("recorded cutoff requires explicit historical selection")
        if self.source_only and self.known_at is None:
            raise ValueError("source-only selector requires a fixed recorded cutoff")
        if self.source_only and self.filters:
            raise ValueError("source-only selector cannot also claim record retrieval")
        if type(self.history) is not bool:
            raise ValueError("typed history query required")
        if not isinstance(self.filters, Mapping) or not set(self.filters) <= QUERY_FIELDS:
            raise ValueError("allowlisted exact index query required")
        for value in self.filters.values():
            identifier(value)
        object.__setattr__(self, "filters", freeze(self.filters))
        if self.source_scope is not None:
            values = tuple(self.source_scope)
            if len(values) > 1024 or len(values) != len(set(values)):
                raise ValueError("bounded unique source query scope required")
            for value in values:
                identifier(value)
            object.__setattr__(self, "source_scope", tuple(sorted(values)))

    def wire(self):
        return {
            "filters": thaw(self.filters),
            "source_scope": None if self.source_scope is None else list(self.source_scope),
            "history": self.history,
            "known_at": self.known_at,
            "source_only": self.source_only,
        }


@dataclass(frozen=True)
class QueryDependency:
    query: IndexQuery
    digest: str
    index_version: int = INDEX_VERSION

    def __post_init__(self):
        if (
            type(self.query) is not IndexQuery
            or type(self.digest) is not str
            or re.fullmatch("[0-9a-f]{64}", self.digest) is None
            or self.index_version != INDEX_VERSION
            or type(self.index_version) is not int
        ):
            raise ValueError("versioned exact query dependency required")

    def wire(self):
        return {"query": self.query.wire(), "digest": self.digest, "index_version": self.index_version}


@dataclass(frozen=True)
class QuerySnapshot(Snapshot):
    query_dependencies: tuple[QueryDependency, ...] = ()
    query_views: object = None
    historical_sources: object = None

    def __post_init__(self):
        super().__post_init__()
        object.__setattr__(self, "query_dependencies", tuple(self.query_dependencies))
        object.__setattr__(self, "query_views", freeze(self.query_views or {}))
        object.__setattr__(self, "historical_sources", freeze(self.historical_sources or {}))


@dataclass(frozen=True)
class QueryDelta(Delta):
    query_dependencies: tuple[QueryDependency, ...] = ()

    def __post_init__(self):
        super().__post_init__()
        object.__setattr__(self, "query_dependencies", tuple(self.query_dependencies))


def pack_dependencies(positive, queries=()):
    positive = version_map(positive)
    queries = tuple(queries)
    if not queries:
        return positive  # Preserve old task/request/object bytes and exact maps.
    if len(queries) > 64 or any(type(item) is not QueryDependency for item in queries):
        raise ValueError("bounded typed query dependencies required")
    return {"schema": DEPENDENCY_SCHEMA, "positive": positive, "queries": [item.wire() for item in queries]}


def unpack_dependencies(value):
    if not isinstance(value, Mapping):
        raise ValueError("dependency object required")
    # Even a source literally named "schema" keeps its ordinary positive map.
    if all(type(item) is int for item in value.values()):
        return version_map(value), ()
    if set(value) != {"schema", "positive", "queries"} or value["schema"] != DEPENDENCY_SCHEMA:
        raise ValueError("unsupported dependency envelope")
    if type(value["queries"]) not in (list, tuple) or not 1 <= len(value["queries"]) <= 64:
        raise ValueError("bounded query dependencies required")
    queries = []
    for item in value["queries"]:
        if not isinstance(item, Mapping) or set(item) != {"query", "digest", "index_version"}:
            raise ValueError("unknown query dependency fields")
        wire = item["query"]
        if not isinstance(wire, Mapping) or set(wire) != {
            "filters",
            "source_scope",
            "history",
            "known_at",
            "source_only",
        }:
            raise ValueError("unknown exact query fields")
        queries.append(
            QueryDependency(
                IndexQuery(
                    wire["filters"],
                    wire["source_scope"],
                    wire["history"],
                    wire["known_at"],
                    wire["source_only"],
                ),
                item["digest"],
                item["index_version"],
            )
        )
    return version_map(value["positive"]), tuple(queries)


def source_index_values(source_id, source_version, records, *, complete, program):
    """A mechanically compiled candidate index, never a world-completeness claim."""
    identifier(source_id)
    if type(source_version) is not int or source_version < 1 or type(complete) is not bool:
        raise ValueError("exact source index version and coverage required")
    records = tuple(records)
    if len(records) > 1024:
        raise ValueError("source index record limit")
    seen = set()
    for record in records:
        if (
            not isinstance(record, Mapping)
            or "record_id" not in record
            or "kind" not in record
            or not set(record) <= QUERY_FIELDS | {"record_id", "payload"}
        ):
            raise ValueError("invalid candidate index record")
        for key, value in record.items():
            if key != "payload":
                identifier(value)
        if record["record_id"] in seen:
            raise ValueError("duplicate candidate index record")
        seen.add(record["record_id"])
    value = {
        "schema": INDEX_SCHEMA,
        "source_id": source_id,
        "source_version": source_version,
        "index_version": INDEX_VERSION,
        "records": records,
        "complete": complete,
        "program": program,
    }
    frozen = freeze(value)
    from hcl.memory.codec import canonical

    if len(canonical(thaw(frozen)).encode()) > 1048576:
        raise ValueError("bounded candidate index required")
    return frozen


def validate_source_index(values):
    if not isinstance(values, Mapping) or set(values) != {
        "schema",
        "source_id",
        "source_version",
        "index_version",
        "records",
        "complete",
        "program",
    }:
        raise ValueError("invalid source index fields")
    if (
        values["schema"] != INDEX_SCHEMA
        or type(values["index_version"]) is not int
        or values["index_version"] != INDEX_VERSION
    ):
        raise ValueError("unsupported source index version")
    return source_index_values(
        values["source_id"],
        values["source_version"],
        values["records"],
        complete=values["complete"],
        program=values["program"],
    )


def query_projection(query, visible_sources, indexed_sources, *, index_history=(), source_history=()):
    """ACL filtering MUST precede this pure function, including pending counts.

    Unknown/uncompiled/partially parsed visible sources remain pending. A new
    relevant source invalidates absence even before semantic compilation. An
    exactly compiled unrelated source does not change the final query token.
    """
    if type(query) is not IndexQuery or len(visible_sources) > 1024:
        raise ValueError("bounded typed query projection required")
    visible_sources = version_map(visible_sources)
    selected_history = {}
    recorded = {}
    if query.history:
        for row in source_history:
            source_id = row["source_id"]
            if source_id not in visible_sources or (
                query.source_scope is not None and source_id not in query.source_scope
            ):
                continue
            if query.known_at is not None and row["recorded_at"] > query.known_at:
                continue
            previous = selected_history.get(source_id)
            if previous is None or row["source_version"] > previous["source_version"]:
                selected_history[source_id] = row
        visible_sources = {key: row["source_version"] for key, row in selected_history.items()}
        indexed_sources = {}
        for values, indexed_at in index_history:
            key = values["source_id"]
            if visible_sources.get(key) == values["source_version"] and indexed_at > recorded.get(key, -1):
                indexed_sources[key] = values
                recorded[key] = indexed_at
    pending, matches = [], []
    for source_id, version in sorted(visible_sources.items()):
        if query.source_scope is not None and source_id not in query.source_scope:
            continue
        if query.source_only:
            continue
        values = indexed_sources.get(source_id)
        if values is None or values["source_version"] != version:
            pending.append([source_id, version, "UNCOMPILED"])
            continue
        values = validate_source_index(values)
        if not values["complete"]:
            pending.append([source_id, version, "PARTIAL_CANDIDATE_COVERAGE"])
        for record in values["records"]:
            if all(record.get(key) == value for key, value in query.filters.items()):
                match = {"source_id": source_id, "source_version": version, "record": thaw(record)}
                if query.history:
                    match["recorded_at"] = selected_history[source_id]["recorded_at"]
                    match["indexed_at"] = recorded[source_id]
                matches.append(match)
    from hcl.memory.codec import canonical

    matches.sort(key=canonical)
    projection = {
        "query": query.wire(),
        "index_version": INDEX_VERSION,
        "matches": matches,
        "pending": pending,
        "absence_eligible": not query.source_only and not matches and not pending,
        "coverage": "DECLARED_CANDIDATE_INDEX_ONLY_NOT_WORLD_ABSENCE",
    }
    if query.history:
        projection["source_history"] = sorted([dict(row) for row in selected_history.values()], key=canonical)
    digest = sha256(canonical(projection).encode()).hexdigest()
    return QueryDependency(query, digest), freeze(projection)
