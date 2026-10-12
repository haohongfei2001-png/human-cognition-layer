"""Authorized retrieval projections on the ONE existing SQLite event store."""
import json

from hcl.kernel.dependencies import QuerySnapshot, query_index_versions, unpack_dependencies
from hcl.kernel.retrieval import EvidenceNode, RetrievalQuery
from hcl.kernel.scope import failure
from hcl.kernel.types import InferenceResult, SourceDocument, SourceHandle, AccessPolicy, HCLFailure
from hcl.memory.index import build_index, INDEX_SCHEMA, INDEX_VERSION as SEARCH_INDEX_VERSION
from hcl.memory.retrieval import project_retrieval
from hcl.memory.store import denied
from hcl.memory import codec


class RetrievalPreparation:
    """Transaction-local memo and hard preparation work bounds, never authority.

    Entries are immutable projections under one SQLite snapshot, principal and
    write generation. A fresh delivery transaction MUST build a new instance.
    Heights preserve the longest dependency path even on a shared cache hit.
    """
    LIMITS = {"projections": 64, "source_characters": 32 * 1024 * 1024,
              "regions": 262144, "evidence_rows": 4096, "graph_nodes": 32768}

    def __init__(self):
        self.cache, self.stack, self.work = {}, [], {}

    def charge(self, kind, amount):
        total = self.work.get(kind, 0) + amount
        if total > self.LIMITS[kind]:
            raise failure("BUDGET_EXHAUSTED", "RETRIEVAL_PREPARATION_BOUND", "retrieval." + kind,
                          "The transaction's retrieval preparation work bound was reached.", "retrieval")
        self.work[kind] = total

    @staticmethod
    def depth_failure():
        return failure("BUDGET_EXHAUSTED", "RETRIEVAL_DEPENDENCY_DEPTH", "query_dependencies",
                       "The recorded retrieval dependency depth is bounded.", "retrieval")

    def project(self, store, db, session, principal, query):
        key = (session["session_id"], principal.tenant_id, principal.subject_id,
               session["revision"], session["epoch"], session["rule"], db.total_changes,
               codec.canonical(query.wire()))
        depth = len(self.stack)
        if depth >= 8 or any(frame["key"] == key for frame in self.stack):
            raise self.depth_failure()
        cached = self.cache.get(key)
        if cached is not None:
            result, height = cached
            if depth + height > 8:
                raise self.depth_failure()
        else:
            self.charge("projections", 1)
            frame = {"key": key, "height": 1}
            self.stack.append(frame)
            try:
                result = retrieval_projection(store, db, session, principal, query)
            finally:
                self.stack.pop()
            height = frame["height"]
            self.cache[key] = (result, height)
        if self.stack:
            self.stack[-1]["height"] = max(self.stack[-1]["height"], height + 1)
        return result


def argument_nodes(result):
    """Adapt actual recorded M13 proofs/attacks; never reinterpret source prose."""
    if result.kind != "CONDITIONAL_ARGUMENT_ACCEPTANCE":
        raise ValueError("unsupported recorded evidence graph kind")
    nodes = {}
    for model in result.values["models"]:
        prefix = result.result_id + "/" + model["model_id"] + "/"
        arguments = {row["argument_id"]: row for row in model["arguments"]}
        for key, row in arguments.items():
            # Even a priority-blocked attack remains inspectable counterevidence.
            challenges = tuple(prefix + attack["attacker"] for attack in model["attacks"] if attack["target"] == key)
            alternatives = tuple(prefix + other for other, value in arguments.items()
                                 if other != key and value["conclusion"] == row["conclusion"])
            nodes[prefix+key] = EvidenceNode(prefix+key, row["source_segment_ids"],
                                            (tuple(prefix + child for child in row["children"]),),
                                            challenges, alternatives, (),
                                            tuple(sorted(set((*row["assumptions"], *model["frontier"],
                                                              model["acceptance_scope"], "frame:" + model["frame_kind"],
                                                              "conditional-model:" + model["model_id"],
                                                              "namespace-source:" + model["namespace_source_id"])))))
    return nodes


def retrieval_projection(store, db, session, principal, query):
    if store._schema not in (3, 4) or type(query) is not RetrievalQuery:
        raise ValueError("versioned retrieval namespace/query required")
    # Do not inspect source bytes, index counts, graph values, corpus statistics
    # or even existence in an explicit requested scope before authorization.
    rows = [dict(row) for row in db.execute("SELECT * FROM sources WHERE session_id=? ORDER BY source_id", (session["session_id"],))
            if principal.subject_id in json.loads(row["readers"])
            and (query.source_scope is None or row["source_id"] in query.source_scope)]
    if query.source_scope is not None and set(query.source_scope) != {row["source_id"] for row in rows}:
        raise denied()
    if len(rows) > 1024:
        raise failure("BUDGET_EXHAUSTED", "RETRIEVAL_SOURCE_BOUND", "source_scope", "The authorized retrieval scope exceeds its bound.", "retrieval")
    sources, indexes = {}, {}
    total = 0
    remaining_regions = 65536
    for row in rows:
        source_id = row["source_id"]
        content = store._get_object(row["object_hash"])
        source = SourceDocument(SourceHandle(source_id, row["version"]), content["text"],
                                AccessPolicy(session["tenant"], frozenset(json.loads(row["readers"]))), content["formal_problem"])
        total += len(source.text)
        if total > 8 * 1024 * 1024:
            raise failure("BUDGET_EXHAUSTED", "RETRIEVAL_LIBRARY_BOUND", "source_scope", "Narrow the authorized retrieval scope before this bounded index scan.", "retrieval")
        store._retrieval_preparation.charge("source_characters", len(source.text))
        index = None
        cached_hash = content.get("retrieval_index_hash")
        if cached_hash is not None:
            try:
                index = store._get_object(cached_hash)
            except HCLFailure as error:
                if error.diagnostic.code != "STATE_CORRUPT":
                    raise
                # A missing/corrupt disposable index is never a missing original.
                # The authoritative source was already hash-checked above.
        # Source objects are content-addressed host-ingestion products. Their
        # indexes are disposable and independently rebuildable from original text.
        if index is None or index.get("schema") != INDEX_SCHEMA or index.get("version") != SEARCH_INDEX_VERSION:
            index = build_index(source)
        if len(index["regions"]) > remaining_regions:
            index = build_index(source, max_regions=remaining_regions)
        remaining_regions -= len(index["regions"])
        store._retrieval_preparation.charge("regions", len(index["regions"]))
        sources[source_id], indexes[source_id] = source, index
    nodes = {}
    for result_id in query.evidence_result_ids:
        store._retrieval_preparation.charge("evidence_rows", 1)
        row = db.execute("SELECT * FROM inferences WHERE session_id=? AND result_id=?", (session["session_id"], result_id)).fetchone()
        if row is None:
            raise denied()
        dependencies, nested = unpack_dependencies(json.loads(row["read_set"]))
        if not set(dependencies) <= set(sources):
            raise denied()
        # Existing query-bound graphs are validated as existing immutable effects;
        # no automatic "latest graph" creates a self-invalidating dependency loop.
        store._validate_dependencies(db, session, principal, json.loads(row["read_set"]), row["epoch"], session["rule"])
        value = store._get_object(row["object_hash"])
        if type(value) is not InferenceResult or value.result_id != result_id:
            raise failure("FAILED", "RETRIEVAL_GRAPH_CORRUPT", "evidence_result_ids", "A recorded evidence identity is invalid.", "retrieval")
        try:
            additions = argument_nodes(value)
        except (KeyError, ValueError, TypeError):
            raise failure("INVALID_REQUEST", "RETRIEVAL_GRAPH_UNSUPPORTED", "evidence_result_ids", "This recorded result has no supported evidence graph adapter.", "retrieval") from None
        if set(nodes) & set(additions):
            raise ValueError("duplicate recorded graph identity")
        store._retrieval_preparation.charge("graph_nodes", len(additions))
        nodes.update(additions)
        if len(nodes) > 8192:
            raise failure("BUDGET_EXHAUSTED", "RETRIEVAL_GRAPH_BOUND", "evidence_result_ids",
                          "The recorded graph scope exceeds its traversal preparation bound.", "retrieval")
    return project_retrieval(query, sources, indexes, nodes)


class QueryStore:
    """A view of StateStore, never a second authoritative cognitive database."""
    def __init__(self, store):
        if not store.durable:
            raise ValueError("durable unified store required")
        self.store = store

    def search(self, session_id, principal, query):
        with self.store._transaction() as db:
            session = self.store._session(db, session_id, principal)
            dependency, projection = self.store._query_projection(db, session, principal, query)
            selected = {row["source_id"] for row in projection["coverage"]["read_regions"]}
            sources = {key: self.store._source(db, session, principal, key) for key in sorted(selected)}
            snapshot = QuerySnapshot(session_id, principal, session["revision"], session["epoch"], session["rule"],
                                     {key: source.handle.version for key, source in sources.items()},
                                     query_index_versions((dependency,)), sources, (dependency,), {"0": projection})
        # Leave the old WAL read snapshot before the final current-authority gate.
        self.store.validate_snapshot(snapshot)
        return snapshot
