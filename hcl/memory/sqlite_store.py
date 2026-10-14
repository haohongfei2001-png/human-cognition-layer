"""SQLite WAL events and disposable projections, with atomic content objects.

Only the embedding host creates sessions or ingests sources. Objects are written
and fsynced before the referencing SQLite transaction commits. A crash may leave
an unreferenced object, never a published dangling reference. Events contain
object hashes, not duplicate source text. They are integrity records, not a
cryptographic defense against an administrator rewriting the entire database.
"""
from contextlib import contextmanager
from dataclasses import replace
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import sqlite3
import tempfile
from threading import RLock
from uuid import uuid4

from hcl.kernel.scope import check_commit_contract, failure, identifier, principal_identity, version_map
from hcl.kernel.types import (
    AccessPolicy, CommitResult, FormalProblem, HCLFailure, InferenceResult,
    RULE_VERSION, Snapshot, SourceDocument, SourceHandle,
)
from hcl.memory import codec
from hcl.memory.store import denied

SCHEMA = 1
TABLE_KEYS = {
    "sessions": ("session_id",), "sources": ("session_id", "source_id"),
    "inferences": ("session_id", "result_id"), "tasks": ("task_key",),
    "calls": ("task_key", "call_id"),
}
OBJECT_FIELDS = {"object_hash", "request_hash", "result_hash", "response_hash"}


def corrupt():
    return failure("FAILED", "STATE_CORRUPT", "store", "Stored state failed integrity validation.", "storage")


class SQLiteStateStore:
    durable = True

    def __init__(self, path, *, revision=False):
        self.path = Path(path).resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.object_root = self.path.with_name(self.path.name + ".objects")
        self.object_root.mkdir(exist_ok=True)
        self._lock = RLock()
        self.owner_id = uuid4().hex  # Execution owner, not user authorization.
        self._db = sqlite3.connect(self.path, isolation_level=None, check_same_thread=False, timeout=10)
        self._db.row_factory = sqlite3.Row
        self._db.execute("PRAGMA journal_mode=WAL")
        self._db.execute("PRAGMA synchronous=FULL")
        self._db.execute("PRAGMA secure_delete=ON")
        version = self._db.execute("PRAGMA user_version").fetchone()[0]
        if version not in (0, SCHEMA, 2, 3, 4) or (revision and version in (1, 2)):
            self._db.close()
            raise ValueError("unsupported store schema; migration or rollback is required")
        self._schema = version or (3 if revision else SCHEMA)
        self._namespace_generation = None
        self._version_bundle = None
        self._revision_control = None
        if version in (3, 4):
            from hcl.memory.migrations.revision_control import read
            from hcl.memory.migrations.control import version_bundle

            try:
                self._revision_control = read(self._db)
                if self._revision_control["target_path"] != str(self.path):
                    raise ValueError("revision namespace is not at its published path")
                if json.loads(self._revision_control["versions"]) != version_bundle(schema=version):
                    raise ValueError("revision namespace version mismatch")
                self._validate_layout()
            except BaseException:
                self._db.close()
                raise
        if version in (2, 4):
            from hcl.memory.migrations.control import read_control, version_bundle
            try:
                control = read_control(self._db)
                self._namespace_generation = control["generation"]
                self._version_bundle = version_bundle(schema=version)
                if json.loads(control["versions"]) != self._version_bundle:
                    raise ValueError("controlled namespace version mismatch")
            except BaseException:
                self._db.close()
                raise
            # A published controlled namespace must already have its schema.
            # Never repair a partial import or downgrade it to schema 1.
            return
        if version == 3:
            return
        self._db.executescript("""
        CREATE TABLE IF NOT EXISTS sessions(session_id TEXT PRIMARY KEY, tenant TEXT NOT NULL,
          owner TEXT NOT NULL, members TEXT NOT NULL, revision INTEGER NOT NULL, epoch INTEGER NOT NULL, rule TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS sources(session_id TEXT NOT NULL, source_id TEXT NOT NULL,
          version INTEGER NOT NULL, object_hash TEXT NOT NULL, readers TEXT NOT NULL, PRIMARY KEY(session_id, source_id));
        CREATE TABLE IF NOT EXISTS inferences(session_id TEXT NOT NULL, result_id TEXT NOT NULL,
          object_hash TEXT NOT NULL, read_set TEXT NOT NULL, epoch INTEGER NOT NULL,
          base_revision INTEGER NOT NULL, commit_revision INTEGER NOT NULL, PRIMARY KEY(session_id, result_id));
        CREATE TABLE IF NOT EXISTS tasks(task_key TEXT PRIMARY KEY, session_id TEXT NOT NULL, tenant TEXT NOT NULL,
          subject TEXT NOT NULL, request_id TEXT NOT NULL, fingerprint TEXT NOT NULL, request_hash TEXT NOT NULL,
          budget TEXT NOT NULL, state TEXT NOT NULL, owner_id TEXT NOT NULL, result_hash TEXT,
          dependencies TEXT NOT NULL, epoch INTEGER NOT NULL, rule TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS calls(task_key TEXT NOT NULL, call_id TEXT NOT NULL, session_id TEXT NOT NULL,
          state TEXT NOT NULL, owner_id TEXT NOT NULL, request_hash TEXT NOT NULL, response_hash TEXT,
          request_bytes INTEGER NOT NULL, output_bytes INTEGER, attempted INTEGER,
          validation_code TEXT, PRIMARY KEY(task_key, call_id));
        CREATE TABLE IF NOT EXISTS events(seq INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT NOT NULL,
          revision INTEGER NOT NULL, kind TEXT NOT NULL, payload TEXT NOT NULL,
          previous_hash TEXT NOT NULL, event_hash TEXT NOT NULL);
        """)
        if self._schema == 3:
            from hcl.memory.migrations.revision_control import install, read

            install(
                self._db,
                schema=3,
                upgrade_id=uuid4().hex,
                origin_schema=0,
                checkpoint="",
                source_path=str(self.path),
                target_path=str(self.path),
            )
            self._revision_control = read(self._db)
        self._db.execute(f"PRAGMA user_version={self._schema}")

    def _validate_layout(self):
        required = set(TABLE_KEYS) | {"events", "revision_control"}
        from hcl.memory.governance import TABLES as GOVERNANCE_TABLES
        required |= GOVERNANCE_TABLES
        tables = {row[0] for row in self._db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if not required <= tables:
            raise corrupt()
        for table in TABLE_KEYS:
            if not set(TABLE_KEYS[table]) <= {
                row[1] for row in self._db.execute(f"PRAGMA table_info({table})")
            }:
                raise corrupt()

    def close(self):
        with self._lock:
            self._db.close()

    def _checkpoint(self, stage):
        """No-op seam for tests to simulate abrupt interruption, never callbacks from input."""

    @contextmanager
    def _transaction(self, write=False, *, maintenance=False):
        with self._lock:
            try:
                self._db.execute("BEGIN IMMEDIATE" if write else "BEGIN")
                self._retrieval_preparation = None
                self._retention_journals = []
                if self._db.execute("PRAGMA user_version").fetchone()[0] != self._schema:
                    raise corrupt()
                if self._revision_control is not None:
                    from hcl.memory.migrations.revision_control import validate
                    validate(self._db, self._revision_control, maintenance=maintenance)
                if self._namespace_generation is not None:
                    from hcl.memory.migrations.control import validate_execution
                    validate_execution(self._db, self._namespace_generation, self._version_bundle)
                yield self._db
                self._checkpoint("before_commit")
                self._db.commit()
                if self._revision_control is not None:
                    from hcl.memory.retention_objects import cleanup_committed
                    cleanup_committed(self)
            except BaseException as error:
                if self._db.in_transaction:
                    self._db.rollback()
                if isinstance(error, (sqlite3.Error, OSError)):
                    raise failure("FAILED", "STORAGE_FAILURE", "store", "The state transaction could not complete.", "storage") from None
                raise
            finally:
                # In particular, never carry an old WAL authorization decision
                # into the separate late-delivery transaction.
                self._retrieval_preparation = None
                self._retention_journals = []

    def _put_object(self, value):
        body = codec.dumps(value)
        digest = sha256(body).hexdigest()
        target = self.object_root/digest
        if target.exists():
            self._get_object(digest)
            return digest
        journal = getattr(self, "_retention_current_journal", None)
        descriptor, temporary = tempfile.mkstemp(prefix="pending-" + (journal + "-" if journal else ""), dir=self.object_root)
        try:
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(body)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, target)
            directory_fd = os.open(self.object_root, os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
        self._checkpoint("object_persisted")
        return digest

    def _put_content(self, value, *, session_id, context=None, bindings=(), owner=None, dependencies=None, principal=None):
        if self._revision_control is None:
            return self._put_object(value)
        from hcl.memory.retention_objects import put
        return put(self, value, session_id=session_id, context=context, bindings=bindings, owner=owner,
                   dependencies=dependencies, principal=principal)

    def _get_object(self, digest):
        if type(digest) is not str or not re.fullmatch("[0-9a-f]{64}", digest):
            raise corrupt()
        target = self.object_root/digest
        try:
            if target.is_symlink():
                raise corrupt()
            body = target.read_bytes()
            if sha256(body).hexdigest() != digest:
                raise corrupt()
            return codec.loads(body)
        except (OSError, ValueError, TypeError, KeyError, RecursionError):
            raise corrupt() from None

    def _record(self, db, table, record, revision, *, principal=None):
        from hcl.memory.governance import EVENT_KEYS
        if table not in TABLE_KEYS and not (self._revision_control is not None and table in EVENT_KEYS):
            raise ValueError("unknown projection")
        session_id = record["session_id"]
        prior = db.execute("SELECT event_hash FROM events WHERE session_id=? ORDER BY seq DESC LIMIT 1", (session_id,)).fetchone()
        previous = prior[0] if prior else ""
        payload = codec.canonical(record)
        digest = sha256(codec.canonical([session_id, revision, table, payload, previous]).encode()).hexdigest()
        event = db.execute("INSERT INTO events(session_id,revision,kind,payload,previous_hash,event_hash) VALUES(?,?,?,?,?,?)",
                   (session_id, revision, table, payload, previous, digest))
        if self._revision_control is not None:
            from hcl.memory.governance import capture
            capture(self, db, dict(seq=event.lastrowid, session_id=session_id, event_hash=digest),
                    table, record, principal=principal)
        self._checkpoint("event_appended")
        self._upsert(db, table, record)
        self._checkpoint("projection_updated")

    def _upsert(self, db, table, record):
        columns = tuple(row[1] for row in db.execute(f"PRAGMA table_info({table})"))
        if set(columns) != set(record):
            raise corrupt()
        db.execute(f"INSERT OR REPLACE INTO {table} ({','.join(columns)}) VALUES ({','.join('?' for _ in columns)})",
                   tuple(record[column] for column in columns))

    def _session(self, db, session_id, principal, *, owner=False):
        principal_identity(principal)
        row = db.execute("SELECT * FROM sessions WHERE session_id=?", (session_id,)).fetchone()
        if (row is None or row["tenant"] != principal.tenant_id or principal.subject_id not in json.loads(row["members"])
                or (owner and row["owner"] != principal.subject_id)):
            raise denied()
        if row["rule"] != RULE_VERSION:
            raise failure("STALE_STATE", "RULE_VERSION_CHANGED", "rule_version", "The stored rule version is not current.")
        return dict(row)

    def create_session(self, session_id, owner, members=frozenset()):
        identifier(session_id)
        principal_identity(owner)
        members = frozenset(identifier(member) for member in members) | {owner.subject_id}
        with self._transaction(True) as db:
            if db.execute("SELECT 1 FROM sessions WHERE session_id=?", (session_id,)).fetchone():
                raise ValueError("new session ID required")
            self._record(db, "sessions", dict(session_id=session_id, tenant=owner.tenant_id, owner=owner.subject_id,
                         members=codec.canonical(sorted(members)), revision=0, epoch=0, rule=RULE_VERSION), 0)

    def put_source(self, session_id, principal, source_id, text, *, formal_problem=None, readers=None):
        identifier(source_id)
        if type(text) is not str or (formal_problem is not None and type(formal_problem) is not FormalProblem):
            raise ValueError("typed source text and formal input required")
        try:
            text.encode("utf-8")
        except UnicodeEncodeError:
            raise failure("INVALID_REQUEST", "INVALID_SOURCE_ENCODING", "text", "Source text must be valid Unicode.", "ingestion") from None
        with self._transaction(True) as db:
            session = self._session(db, session_id, principal, owner=True)
            previous = db.execute("SELECT * FROM sources WHERE session_id=? AND source_id=?", (session_id, source_id)).fetchone()
            readers = sorted(identifier(member) for member in (readers if readers is not None else json.loads(session["members"])))
            readers = codec.canonical(sorted(set(readers)))
            version = previous["version"] + 1 if previous else 1
            content = {"text": text, "formal_problem": formal_problem}
            if self._schema in (3, 4):
                from hcl.memory.index import build_index
                source = SourceDocument(SourceHandle(source_id, version), text,
                                        AccessPolicy(principal.tenant_id, frozenset(json.loads(readers))), formal_problem)
                # Disposable cached projection. Keep the authoritative source
                # object small; a dropped cache is rebuilt from exact originals.
                content["retrieval_index_hash"] = self._put_content(build_index(source), session_id=session_id,
                                                                     bindings=((session_id, source_id, version),))
            digest = self._put_content(content, session_id=session_id, bindings=((session_id, source_id, version),))
            session["revision"] += 1
            if previous and previous["readers"] != readers:
                session["epoch"] += 1
            self._record(db, "sources", dict(session_id=session_id, source_id=source_id, version=version,
                         object_hash=digest, readers=readers), session["revision"])
            self._record(db, "sessions", session, session["revision"])
            return SourceHandle(source_id, version)

    def set_readers(self, session_id, principal, source_id, readers):
        with self._transaction(True) as db:
            session = self._session(db, session_id, principal, owner=True)
            source = db.execute("SELECT * FROM sources WHERE session_id=? AND source_id=?", (session_id, source_id)).fetchone()
            if source is None:
                raise denied()
            source = dict(source)
            source["readers"] = codec.canonical(sorted(set(identifier(member) for member in readers)))
            session["epoch"] += 1
            session["revision"] += 1
            self._record(db, "sources", source, session["revision"])
            self._record(db, "sessions", session, session["revision"])

    def _source(self, db, session, principal, source_id):
        row = db.execute("SELECT * FROM sources WHERE session_id=? AND source_id=?", (session["session_id"], source_id)).fetchone()
        if row is None or principal.subject_id not in json.loads(row["readers"]):
            raise denied()
        content = self._get_object(row["object_hash"])
        return SourceDocument(SourceHandle(source_id, row["version"]), content["text"],
                              AccessPolicy(session["tenant"], frozenset(json.loads(row["readers"]))), content["formal_problem"])

    def snapshot(self, session_id, principal, source_handles):
        with self._transaction() as db:
            session = self._session(db, session_id, principal)
            views = {}
            for handle in source_handles:
                if type(handle) is not SourceHandle:
                    raise ValueError("typed source handle required")
                version_map({handle.source_id: handle.version})
                source = self._source(db, session, principal, handle.source_id)
                if source.handle != handle:
                    raise failure("STALE_STATE", "STALE_SOURCE", "source_handles.version", "A source version changed.", "snapshot")
                if handle.source_id in views:
                    raise failure("INVALID_REQUEST", "DUPLICATE_SOURCE", "source_handles", "A source was requested twice.", "admission")
                views[handle.source_id] = source
            result = Snapshot(session_id, principal, session["revision"], session["epoch"], session["rule"],
                              {key: source.handle.version for key, source in views.items()}, {}, views)
        # A public snapshot contains original bytes. Leave its old WAL view
        # before the delivery gate, just as QueryStore.search already does.
        self.validate_snapshot(result)
        return result

    def _query_projection(self, db, session, principal, query):
        from hcl.kernel.dependencies import INDEX_KIND, query_projection
        from hcl.kernel.retrieval import RetrievalQuery
        from hcl.kernel.concept_registry import ConceptQuery
        if type(query) is ConceptQuery:
            from hcl.memory.concept_registry import project
            return project(self, db, session, principal, query)
        if type(query) is RetrievalQuery:
            from hcl.memory.query_store import RetrievalPreparation
            if not db.in_transaction:
                raise ValueError("retrieval requires an authorized transaction")
            if self._retrieval_preparation is None:
                self._retrieval_preparation = RetrievalPreparation()
            return self._retrieval_preparation.project(self, db, session, principal, query)

        if self._schema not in (3, 4):
            raise failure(
                "INVALID_REQUEST",
                "REVISION_MIGRATION_REQUIRED",
                "store",
                "Revision execution requires the explicit upgraded store.",
            )
        visible = {
            row["source_id"]: row["version"]
            for row in db.execute("SELECT * FROM sources WHERE session_id=?", (session["session_id"],))
            if principal.subject_id in json.loads(row["readers"])
        }
        source_history = self._source_history(db, session, principal) if query.history else ()
        selected_versions = dict(visible)
        if query.history:
            selected_versions = {}
            for item in source_history:
                if query.known_at is None or item["recorded_at"] <= query.known_at:
                    selected_versions[item["source_id"]] = max(
                        item["source_version"], selected_versions.get(item["source_id"], 0)
                    )
        indexed, index_history = {}, []
        rows = (
            ()
            if query.source_only
            else db.execute(
                "SELECT * FROM inferences WHERE session_id=? ORDER BY commit_revision DESC,result_id DESC",
                (session["session_id"],),
            )
        )
        for count, row in enumerate(rows):
            if count >= 10000:
                raise failure(
                    "BUDGET_EXHAUSTED",
                    "INDEX_SCAN_BOUND",
                    "index",
                    "The candidate index scan bound was reached.",
                )
            # Source-bearing objects are read only after the exact positive map
            # proves current principal authorization, before inspecting kind.
            try:
                from hcl.kernel.dependencies import unpack_dependencies

                positive, queries = unpack_dependencies(json.loads(row["read_set"]))
            except (ValueError, TypeError):
                raise corrupt() from None
            if not all(selected_versions.get(key) == value for key, value in positive.items()):
                continue
            historical_binding = None
            if queries:
                if positive or len(queries) != 1 or not queries[0].query.source_only:
                    continue
                query_scope = queries[0].query.source_scope
                if query_scope is None or not query_scope or not set(query_scope) <= set(visible):
                    continue
                # This branch reads source-event metadata only, never recursively
                # scans index rows to validate a historical source-only selector.
                historical = [
                    item
                    for item in self._source_history(db, session, principal)
                    if item["source_id"] in query_scope and item["recorded_at"] <= queries[0].query.known_at
                ]
                if not historical:
                    raise corrupt()
                historical_binding = {}
                for item in historical:
                    key = item["source_id"]
                    if (
                        key not in historical_binding
                        or item["source_version"] > historical_binding[key]["source_version"]
                    ):
                        historical_binding[key] = item
                if any(
                    selected_versions.get(key) != value["source_version"]
                    for key, value in historical_binding.items()
                ):
                    continue
                from hcl.kernel.dependencies import query_projection

                token, _ = query_projection(queries[0].query, visible, {}, source_history=historical)
                if token != queries[0]:
                    raise corrupt()
            result = self._get_object(row["object_hash"])
            if type(result) is not InferenceResult or result.kind != INDEX_KIND:
                continue
            from hcl.kernel.dependencies import validate_source_index

            values = validate_source_index(result.values)
            source_id = values["source_id"]
            if historical_binding is None:
                if positive.get(source_id) != values["source_version"]:
                    raise corrupt()
            elif (
                source_id not in historical_binding
                or values["source_version"] != historical_binding[source_id]["source_version"]
            ):
                raise corrupt()
            index_history.append((values, row["commit_revision"]))
            if source_id not in indexed and values["source_version"] == visible[source_id]:
                indexed[source_id] = values
        try:
            source_history = self._source_history(db, session, principal) if query.history else ()
            return query_projection(
                query, visible, indexed, index_history=index_history, source_history=source_history
            )
        except (ValueError, TypeError):
            raise corrupt() from None

    def _source_history(self, db, session, principal):
        visible = {
            row["source_id"]: dict(row)
            for row in db.execute("SELECT * FROM sources WHERE session_id=?", (session["session_id"],))
            if principal.subject_id in json.loads(row["readers"])
        }
        previous, first, latest = "", {}, {}
        for number, event in enumerate(
            db.execute("SELECT * FROM events WHERE session_id=? ORDER BY seq", (session["session_id"],))
        ):
            if number >= 100000:
                raise failure(
                    "BUDGET_EXHAUSTED",
                    "SOURCE_HISTORY_BOUND",
                    "history",
                    "The source history scan bound was reached.",
                )
            digest = sha256(
                codec.canonical(
                    [
                        session["session_id"],
                        event["revision"],
                        event["kind"],
                        event["payload"],
                        event["previous_hash"],
                    ]
                ).encode()
            ).hexdigest()
            if digest != event["event_hash"] or previous != event["previous_hash"]:
                raise corrupt()
            previous = digest
            if event["kind"] != "sources":
                continue
            row = json.loads(event["payload"])
            source_id = row["source_id"]
            if source_id not in visible:
                continue
            key = (source_id, row["version"])
            if key in first:
                if row["object_hash"] != first[key]["object_hash"]:
                    raise corrupt()
            else:
                if source_id in latest and row["version"] != latest[source_id]["version"] + 1:
                    raise corrupt()
                first[key] = {
                    "source_id": source_id,
                    "source_version": row["version"],
                    "recorded_at": event["revision"],
                    "object_hash": row["object_hash"],
                    "event_hash": self._historical_event_identity(db, event),
                }
            latest[source_id] = row
        if latest != visible:
            raise corrupt()
        return tuple(first.values())

    def _historical_event_identity(self, db, event):
        if self._revision_control is None:
            return event["event_hash"]
        row = db.execute("SELECT annotation,annotation_hash FROM retention_events WHERE seq=?", (event["seq"],)).fetchone()
        if row is None or sha256(codec.canonical([event["event_hash"], row["annotation"]]).encode()).hexdigest() != row["annotation_hash"]:
            raise corrupt()
        identity = json.loads(row["annotation"])["source_event_identity"]
        if type(identity) is not str or not re.fullmatch("[0-9a-f]{64}", identity):
            raise corrupt()
        return identity

    def _historical_source(self, db, session, principal, binding):
        source = self._source(db, session, principal, binding["source_id"])  # always CURRENT ACL
        if binding not in self._source_history(db, session, principal):
            raise corrupt()
        content = self._get_object(binding["object_hash"])
        return SourceDocument(
            SourceHandle(binding["source_id"], binding["source_version"]),
            content["text"],
            source.access_policy,
            content["formal_problem"],
        )

    def historical_snapshot(self, session_id, principal, source_handles, *, known_at):
        from hcl.kernel.dependencies import IndexQuery, INDEX_VERSION, QuerySnapshot

        if type(known_at) is not int or known_at < 0:
            raise ValueError("explicit recorded cutoff required")
        handles = tuple(source_handles)
        query = IndexQuery({}, tuple(handle.source_id for handle in handles), True, known_at, True)
        with self._transaction() as db:
            session = self._session(db, session_id, principal)
            if known_at > session["revision"]:
                raise failure(
                    "INVALID_REQUEST",
                    "FUTURE_RECORDED_CUTOFF",
                    "issue.known_at",
                    "A future ledger cutoff cannot select historical evidence.",
                    "admission",
                )
            dependency, view = self._query_projection(db, session, principal, query)
            selected = {row["source_id"]: row for row in view["source_history"]}
            views = {}
            for handle in handles:
                self._source(db, session, principal, handle.source_id)
                if (
                    handle.source_id not in selected
                    or selected[handle.source_id]["source_version"] != handle.version
                ):
                    raise failure(
                        "STALE_STATE",
                        "HISTORICAL_SELECTION_CHANGED",
                        "source_handles",
                        "The exact source is not selected at this cutoff.",
                    )
                views[handle.source_id] = self._historical_source(
                    db, session, principal, selected[handle.source_id]
                )
            result = QuerySnapshot(
                session_id,
                principal,
                session["revision"],
                session["epoch"],
                session["rule"],
                {key: source.handle.version for key, source in views.items()},
                {"revision": INDEX_VERSION},
                views,
                (dependency,),
                {"0": view},
                selected,
            )
        self.validate_snapshot(result)
        return result

    def search_snapshot(self, session_id, principal, query):
        from hcl.memory.query_store import QueryStore
        return QueryStore(self).search(session_id, principal, query)

    def query_snapshot(self, session_id, principal, source_handles, queries):
        from hcl.kernel.dependencies import INDEX_VERSION, QuerySnapshot, query_index_versions

        queries = tuple(queries)
        if not 1 <= len(queries) <= 64:
            raise ValueError("bounded nonempty query set required")
        # Build both positive content and absence/query coverage in one WAL view.
        with self._transaction() as db:
            session = self._session(db, session_id, principal)
            views = {}
            for handle in source_handles:
                if type(handle) is not SourceHandle:
                    raise ValueError("typed source handles required")
                if handle.source_id in views:
                    raise failure(
                        "INVALID_REQUEST",
                        "DUPLICATE_SOURCE",
                        "source_handles",
                        "A source was requested more than once.",
                        "admission",
                    )
                source = self._source(db, session, principal, handle.source_id)
                if source.handle != handle:
                    raise failure(
                        "STALE_STATE", "STALE_SOURCE", "source_handles", "A source version changed."
                    )
                views[handle.source_id] = source
            dependencies, query_views = [], {}
            for number, query in enumerate(queries):
                dependency, projection = self._query_projection(db, session, principal, query)
                dependencies.append(dependency)
                query_views[str(number)] = projection
            result = QuerySnapshot(
                session_id,
                principal,
                session["revision"],
                session["epoch"],
                session["rule"],
                {key: source.handle.version for key, source in views.items()},
                query_index_versions(dependencies),
                views,
                tuple(dependencies),
                query_views,
            )
        self.validate_snapshot(result)
        return result

    def revision_snapshot(self, session_id, principal, source_handles, *, known_at=None):
        from hcl.kernel.dependencies import IndexQuery, QuerySnapshot

        query = IndexQuery({"kind": "program"}, history=True, known_at=known_at)
        if known_at is None:
            return self.query_snapshot(session_id, principal, source_handles, (query,))
        historical = self.historical_snapshot(session_id, principal, source_handles, known_at=known_at)
        current = self.query_snapshot(session_id, principal, (), (query,))
        snapshot = QuerySnapshot(
            session_id,
            principal,
            current.revision,
            current.access_epoch,
            current.rule_version,
            historical.source_versions,
            current.index_versions,
            historical.immutable_views,
            current.query_dependencies + historical.query_dependencies,
            {"0": current.query_views["0"], "1": historical.query_views["0"]},
            historical.historical_sources,
        )
        self.validate_snapshot(snapshot)
        return snapshot

    def _revision_previous(self, snapshot, query, known_at):
        from hcl.operators.revision import RESULT_KIND, VERSION

        with self._transaction() as db:
            session = self._validate_snapshot(db, snapshot)
            for number, row in enumerate(
                db.execute(
                    "SELECT * FROM inferences WHERE session_id=? ORDER BY commit_revision DESC,result_id DESC",
                    (snapshot.session_id,),
                )
            ):
                if number >= 10000:
                    raise failure(
                        "BUDGET_EXHAUSTED",
                        "REVISION_HISTORY_BOUND",
                        "history",
                        "The revision result scan bound was reached.",
                    )
                result = self._get_object(row["object_hash"])
                if type(result) is not InferenceResult or result.kind != RESULT_KIND:
                    continue
                values = result.values
                if (
                    values.get("operator_version") != VERSION
                    or values.get("query") != query
                    or values.get("known_at") != known_at
                    or values.get("principal")
                    != {"tenant": snapshot.principal.tenant_id, "subject": snapshot.principal.subject_id}
                ):
                    continue
                try:
                    for binding in values["source_bindings"]:
                        self._source(db, session, snapshot.principal, binding["source_id"])
                except HCLFailure as error:
                    if error.status == "DENIED":
                        continue
                    raise
                # Internal recomputation only: stale content is never a delivery
                # candidate and cannot bypass a fresh final dependency check.
                return result
        return None

    def current_handles(self, session_id, principal, source_ids):
        """Authorized current identities for the bounded compatibility adapter."""
        with self._transaction() as db:
            session = self._session(db, session_id, principal)
            return tuple(self._source(db, session, principal, identifier(key)).handle for key in source_ids)

    def _validate_dependencies(self, db, session, principal, read_set, epoch, rule):
        from hcl.kernel.dependencies import unpack_dependencies
        try:
            read_set, queries = unpack_dependencies(read_set)
        except (ValueError, TypeError):
            raise corrupt() from None
        if queries and self._schema not in (3, 4):
            raise corrupt()
        if type(epoch) is not int or epoch != session["epoch"]:
            raise failure("DENIED", "ACCESS_EPOCH_CHANGED", "access_epoch", "Access changed; the prior snapshot cannot be used.", "access")
        if rule != session["rule"]:
            raise failure("STALE_STATE", "RULE_VERSION_CHANGED", "rule_version", "The rule version changed.")
        for source_id, version in read_set.items():
            source = self._source(db, session, principal, source_id)
            if source.handle.version != version:
                raise failure("STALE_STATE", "READ_SET_CHANGED", "read_set", "An input read by the operation changed.")

        for query in queries:
            current, _ = self._query_projection(db, session, principal, query.query)
            if current != query:
                raise failure(
                    "STALE_STATE",
                    "QUERY_DEPENDENCY_CHANGED",
                    "query_dependencies",
                    "An indexed query or its coverage changed.",
                )

    def snapshot_dependencies(self, snapshot, read_set=None):
        from hcl.kernel.dependencies import QuerySnapshot, pack_dependencies

        positive = snapshot.source_versions if read_set is None else read_set
        if type(snapshot) is QuerySnapshot:
            positive = {
                key: value for key, value in positive.items() if key not in snapshot.historical_sources
            }
        return pack_dependencies(
            positive, snapshot.query_dependencies if type(snapshot) is QuerySnapshot else ()
        )

    def _validate_snapshot(self, db, snapshot, read_set=None):
        from hcl.kernel.dependencies import QuerySnapshot, INDEX_VERSION, query_index_versions
        session = self._session(db, snapshot.session_id, snapshot.principal)
        # Revocation is an access failure before any query comparison, including
        # queries whose result disappears precisely because ACL filtering changed.
        self._validate_dependencies(
            db, session, snapshot.principal, {}, snapshot.access_epoch, snapshot.rule_version
        )
        indexed = type(snapshot) is QuerySnapshot
        if indexed:
            if self._schema not in (3, 4) or dict(snapshot.index_versions) != query_index_versions(snapshot.query_dependencies):
                raise corrupt()
            expected_views = {}
            for number, dependency in enumerate(snapshot.query_dependencies):
                current, view = self._query_projection(db, session, snapshot.principal, dependency.query)
                if current != dependency:
                    raise failure(
                        "STALE_STATE",
                        "QUERY_DEPENDENCY_CHANGED",
                        "query_dependencies",
                        "An indexed query or its coverage changed.",
                    )
                expected_views[str(number)] = view
            if snapshot.query_views != expected_views:
                raise corrupt()
            historical = {
                row["source_id"]: row
                for number, dependency in enumerate(snapshot.query_dependencies)
                if dependency.query.source_only
                for row in expected_views[str(number)]["source_history"]
            }
            if snapshot.historical_sources != historical:
                raise corrupt()
            if not set(historical) <= set(snapshot.source_versions):
                raise corrupt()
            for key, binding in historical.items():
                if snapshot.source_versions[key] != binding["source_version"] or snapshot.immutable_views[
                    key
                ] != self._historical_source(db, session, snapshot.principal, binding):
                    raise corrupt()
        dependencies = snapshot.source_versions if read_set is None else version_map(read_set)
        if indexed:
            dependencies = {key:value for key,value in dependencies.items() if key not in snapshot.historical_sources}
        if (type(snapshot.revision) is not int or snapshot.revision < 0 or snapshot.revision > session["revision"]
                or (snapshot.index_versions and not indexed) or set(snapshot.immutable_views) != set(snapshot.source_versions)
                or not set(dependencies) <= set(snapshot.source_versions)):
            raise failure("DENIED", "SNAPSHOT_CONTENT_MISMATCH", "snapshot", "The snapshot contract is invalid.", "access")
        self._validate_dependencies(db, session, snapshot.principal, dependencies, snapshot.access_epoch, snapshot.rule_version)
        for source_id, version in dependencies.items():
            if (version != snapshot.source_versions[source_id]
                    or snapshot.immutable_views[source_id] != self._source(db, session, snapshot.principal, source_id)):
                raise failure("DENIED", "SNAPSHOT_CONTENT_MISMATCH", "immutable_views", "Snapshot content does not match its authorized source.", "access")
        return session

    def validate_snapshot(self, snapshot, read_set=None):
        with self._transaction() as db:
            self._validate_snapshot(db, snapshot, read_set)

    def commit(self, expected_revision, read_set, access_epoch, delta):
        from hcl.kernel.dependencies import QueryDelta, INDEX_KIND, validate_source_index, pack_dependencies
        check_commit_contract(expected_revision, read_set, access_epoch, delta)
        dependencies = pack_dependencies(read_set, delta.query_dependencies if type(delta) is QueryDelta else ())
        with self._transaction(True) as db:
            session = self._session(db, delta.session_id, delta.principal)
            self._validate_dependencies(db, session, delta.principal, dependencies, access_epoch, delta.rule_version)
            if expected_revision > session["revision"]:
                raise failure("STALE_STATE", "FUTURE_REVISION", "base_revision", "A future base revision cannot commit.")
            # Validate the entire adoption write-set before per-row CAS checks.
            # Every row below sees the pre-commit database, so two replacements
            # of one stream in a batch must never both pass the same old head.
            adoption_streams = [result.values.get("stream_token") for result in delta.new_inferences
                                if type(result) is InferenceResult and result.kind == "CONCEPT_ADOPTION"]
            if any(type(stream) is not str or not stream for stream in adoption_streams):
                raise failure("INVALID_REQUEST", "CONCEPT_ADOPTION_IDENTITY", "new_inferences",
                              "An adoption stream must have its exact opaque identity.")
            if len(adoption_streams) != len(set(adoption_streams)):
                raise failure("INVALID_REQUEST", "CONCEPT_ADOPTION_BATCH_FORK", "new_inferences",
                              "A batch can append at most one adoption per explicit stream.")
            for result in delta.new_inferences:
                if type(result) is not InferenceResult or result.rule_version != delta.rule_version:
                    raise failure("FAILED", "INVALID_INFERENCE", "new_inferences", "Inference type and rules must match the delta.")
                identifier(result.result_id)
                if result.kind in ("CONCEPT_ADOPTION", "CONCEPT_SUBSCRIPTION"):
                    from hcl.memory.concept_registry import validate_commit
                    validate_commit(self, db, session, delta, result)
                if result.kind == INDEX_KIND:
                    if self._schema not in (3, 4):
                        raise failure(
                            "INVALID_REQUEST",
                            "REVISION_MIGRATION_REQUIRED",
                            "store",
                            "Revision execution requires the explicit upgraded store.",
                        )
                    try:
                        index = validate_source_index(result.values)
                    except (ValueError, TypeError):
                        raise corrupt() from None
                    if read_set.get(index["source_id"]) != index["source_version"]:
                        # Only the explicit historical source selector can bind
                        # a non-current source index; ordinary positives stay exact.
                        if type(delta) is not QueryDelta or read_set:
                            raise corrupt()
                        historical = []
                        for dependency in delta.query_dependencies:
                            if not dependency.query.source_only:
                                raise corrupt()
                            _, projection = self._query_projection(
                                db, session, delta.principal, dependency.query
                            )
                            historical.extend(projection["source_history"])
                        if not any(
                            (item["source_id"], item["source_version"])
                            == (index["source_id"], index["source_version"])
                            for item in historical
                        ):
                            raise corrupt()
            ids = [result.result_id for result in delta.new_inferences]
            if (len(ids) != len(set(ids)) or any(db.execute("SELECT 1 FROM inferences WHERE session_id=? AND result_id=?",
                (delta.session_id, key)).fetchone() for key in ids)):
                raise failure("FAILED", "RESULT_ID_COLLISION", "new_inferences", "An inference identity is already present.")
            # Only disjoint append-inference writes are supported. Unchanged exact
            # positive dependencies prove a rebase; no query/absence claim is made.
            if ids:
                session["revision"] += 1
                for result in delta.new_inferences:
                    self._record(db, "inferences", dict(session_id=delta.session_id, result_id=result.result_id,
                        object_hash=self._put_content(result, session_id=delta.session_id, context=delta,
                            dependencies=dependencies, principal=delta.principal), read_set=codec.canonical(dependencies), epoch=access_epoch,
                        base_revision=expected_revision, commit_revision=session["revision"]), session["revision"], principal=delta.principal)
                self._record(db, "sessions", session, session["revision"])
            return CommitResult(session["revision"], tuple(ids))

    def _validate_inference_delivery(self, session_id, principal, expected):
        """Fresh current authority and exact row identity for loaded results."""
        with self._transaction() as db:
            session = self._session(db, session_id, principal)
            for original in expected:
                row = db.execute("SELECT * FROM inferences WHERE session_id=? AND result_id=?",
                                 (session_id, original["result_id"])).fetchone()
                if row is None or dict(row) != dict(original):
                    raise failure("DENIED", "INFERENCE_DELIVERY_CHANGED", "inferences",
                                  "The loaded inference is no longer an authorized current reference.", "access")
                self._validate_dependencies(db, session, principal, json.loads(row["read_set"]),
                                            row["epoch"], session["rule"])
                from hcl.memory.concept_registry import authorize_delivery
                authorize_delivery(self, session_id, principal, row)

    def inferences(self, session_id, principal):
        with self._transaction() as db:
            session = self._session(db, session_id, principal)
            result, expected = [], []
            for row in db.execute("SELECT * FROM inferences WHERE session_id=? ORDER BY result_id", (session_id,)):
                self._validate_dependencies(db, session, principal, json.loads(row["read_set"]), row["epoch"], RULE_VERSION)
                result.append(self._get_object(row["object_hash"]))
                expected.append(dict(row))
        self._validate_inference_delivery(session_id, principal, expected)
        return tuple(result)

    def plan_source_erasure(self, session_id, principal, source_id, *, expected_version):
        from hcl.memory.governance import plan_source_erasure
        return plan_source_erasure(self, session_id, principal, source_id, expected_version)

    def prepare_legacy_capsules(self, session_id, principal):
        from hcl.memory.legacy_capsule_store import prepare
        return prepare(self, session_id, principal)

    def legacy_source_view(self, session_id, principal, source_ids):
        from hcl.memory.legacy_capsule_store import source_view
        return source_view(self, session_id, principal, source_ids)

    def set_legacy_readers(self, session_id, principal, source_id, readers):
        from hcl.memory.legacy_capsule_store import set_readers
        return set_readers(self, session_id, principal, source_id, readers)

    def begin_source_erasure(self, session_id, principal, source_id, *, expected_version, plan_hash, erasure_id):
        from hcl.memory.erasure import begin_source_erasure
        return begin_source_erasure(self, session_id, principal, source_id, expected_version, plan_hash, erasure_id)

    def resume_source_erasure(self, session_id, principal, erasure_id):
        from hcl.memory.erasure_cleanup import resume
        return resume(self, session_id, principal, erasure_id)

    def source_erasure_receipt(self, session_id, principal, erasure_id):
        from hcl.memory.erasure_cleanup import receipt
        return receipt(self, session_id, principal, erasure_id)

    def rebuild_projections(self):
        """Trusted host maintenance with exclusive write lock; no external calls."""
        with self._transaction(True) as db:
            from hcl.memory.erasure import event_keys, object_references, REDACTED
            keys = event_keys(db)
            if self._revision_control is not None:
                from hcl.memory.governance import verify_inventory
                verify_inventory(db)
            records = {table: {} for table in keys}
            previous = {}
            for event in db.execute("SELECT * FROM events ORDER BY seq"):
                table, session_id = event["kind"], event["session_id"]
                digest = sha256(codec.canonical([session_id, event["revision"], table, event["payload"], event["previous_hash"]]).encode()).hexdigest()
                if (table not in keys and table != REDACTED) or event["previous_hash"] != previous.get(session_id, "") or digest != event["event_hash"]:
                    raise corrupt()
                previous[session_id] = digest
                record = json.loads(event["payload"])
                if record["session_id"] != session_id:
                    raise corrupt()
                if table == REDACTED:
                    continue
                for digest in object_references(table, record):
                    self._get_object(digest)
                records[table][tuple(record[key] for key in keys[table])] = record
            for table in keys:
                db.execute(f"DELETE FROM {table}")
                for record in records[table].values():
                    self._upsert(db, table, record)
            return {table: len(rows) for table, rows in records.items() if table in TABLE_KEYS}
