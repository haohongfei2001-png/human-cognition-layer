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

    def __init__(self, path):
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
        version = self._db.execute("PRAGMA user_version").fetchone()[0]
        if version not in (0, SCHEMA, 2):
            self._db.close()
            raise ValueError("unsupported store schema; migration or rollback is required")
        self._schema = version or SCHEMA
        self._namespace_generation = None
        self._version_bundle = None
        if version == 2:
            from hcl.memory.migrations.control import read_control, version_bundle
            try:
                control = read_control(self._db)
                self._namespace_generation = control["generation"]
                self._version_bundle = version_bundle()
                if json.loads(control["versions"]) != self._version_bundle:
                    raise ValueError("controlled namespace version mismatch")
            except BaseException:
                self._db.close()
                raise
            # A published controlled namespace must already have its schema.
            # Never repair a partial import or downgrade it to schema 1.
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
        self._db.execute(f"PRAGMA user_version={SCHEMA}")

    def close(self):
        with self._lock:
            self._db.close()

    def _checkpoint(self, stage):
        """No-op seam for tests to simulate abrupt interruption, never callbacks from input."""

    @contextmanager
    def _transaction(self, write=False):
        with self._lock:
            try:
                self._db.execute("BEGIN IMMEDIATE" if write else "BEGIN")
                if self._db.execute("PRAGMA user_version").fetchone()[0] != self._schema:
                    raise corrupt()
                if self._namespace_generation is not None:
                    from hcl.memory.migrations.control import validate_execution
                    validate_execution(self._db, self._namespace_generation, self._version_bundle)
                yield self._db
                self._checkpoint("before_commit")
                self._db.commit()
            except BaseException as error:
                if self._db.in_transaction:
                    self._db.rollback()
                if isinstance(error, (sqlite3.Error, OSError)):
                    raise failure("FAILED", "STORAGE_FAILURE", "store", "The state transaction could not complete.", "storage") from None
                raise

    def _put_object(self, value):
        body = codec.dumps(value)
        digest = sha256(body).hexdigest()
        target = self.object_root/digest
        if target.exists():
            self._get_object(digest)
            return digest
        descriptor, temporary = tempfile.mkstemp(prefix="pending-", dir=self.object_root)
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

    def _record(self, db, table, record, revision):
        if table not in TABLE_KEYS:
            raise ValueError("unknown projection")
        session_id = record["session_id"]
        prior = db.execute("SELECT event_hash FROM events WHERE session_id=? ORDER BY seq DESC LIMIT 1", (session_id,)).fetchone()
        previous = prior[0] if prior else ""
        payload = codec.canonical(record)
        digest = sha256(codec.canonical([session_id, revision, table, payload, previous]).encode()).hexdigest()
        db.execute("INSERT INTO events(session_id,revision,kind,payload,previous_hash,event_hash) VALUES(?,?,?,?,?,?)",
                   (session_id, revision, table, payload, previous, digest))
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
            digest = self._put_object({"text": text, "formal_problem": formal_problem})
            version = previous["version"] + 1 if previous else 1
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
            return Snapshot(session_id, principal, session["revision"], session["epoch"], session["rule"],
                            {key: source.handle.version for key, source in views.items()}, {}, views)

    def current_handles(self, session_id, principal, source_ids):
        """Authorized current identities for the bounded compatibility adapter."""
        with self._transaction() as db:
            session = self._session(db, session_id, principal)
            return tuple(self._source(db, session, principal, identifier(key)).handle for key in source_ids)

    def _validate_dependencies(self, db, session, principal, read_set, epoch, rule):
        version_map(read_set)
        if type(epoch) is not int or epoch != session["epoch"]:
            raise failure("DENIED", "ACCESS_EPOCH_CHANGED", "access_epoch", "Access changed; the prior snapshot cannot be used.", "access")
        if rule != session["rule"]:
            raise failure("STALE_STATE", "RULE_VERSION_CHANGED", "rule_version", "The rule version changed.")
        for source_id, version in read_set.items():
            source = self._source(db, session, principal, source_id)
            if source.handle.version != version:
                raise failure("STALE_STATE", "READ_SET_CHANGED", "read_set", "An input read by the operation changed.")

    def _validate_snapshot(self, db, snapshot, read_set=None):
        session = self._session(db, snapshot.session_id, snapshot.principal)
        dependencies = snapshot.source_versions if read_set is None else version_map(read_set)
        if (type(snapshot.revision) is not int or snapshot.revision < 0 or snapshot.revision > session["revision"]
                or snapshot.index_versions or set(snapshot.immutable_views) != set(snapshot.source_versions)
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
        check_commit_contract(expected_revision, read_set, access_epoch, delta)
        with self._transaction(True) as db:
            session = self._session(db, delta.session_id, delta.principal)
            self._validate_dependencies(db, session, delta.principal, read_set, access_epoch, delta.rule_version)
            if expected_revision > session["revision"]:
                raise failure("STALE_STATE", "FUTURE_REVISION", "base_revision", "A future base revision cannot commit.")
            for result in delta.new_inferences:
                if type(result) is not InferenceResult or result.rule_version != delta.rule_version:
                    raise failure("FAILED", "INVALID_INFERENCE", "new_inferences", "Inference type and rules must match the delta.")
                identifier(result.result_id)
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
                        object_hash=self._put_object(result), read_set=codec.canonical(dict(read_set)), epoch=access_epoch,
                        base_revision=expected_revision, commit_revision=session["revision"]), session["revision"])
                self._record(db, "sessions", session, session["revision"])
            return CommitResult(session["revision"], tuple(ids))

    def inferences(self, session_id, principal):
        with self._transaction() as db:
            session = self._session(db, session_id, principal)
            result = []
            for row in db.execute("SELECT * FROM inferences WHERE session_id=? ORDER BY result_id", (session_id,)):
                self._validate_dependencies(db, session, principal, json.loads(row["read_set"]), row["epoch"], RULE_VERSION)
                result.append(self._get_object(row["object_hash"]))
            return tuple(result)

    def rebuild_projections(self):
        """Trusted host maintenance with exclusive write lock; no external calls."""
        with self._transaction(True) as db:
            records = {table: {} for table in TABLE_KEYS}
            previous = {}
            for event in db.execute("SELECT * FROM events ORDER BY seq"):
                table, session_id = event["kind"], event["session_id"]
                digest = sha256(codec.canonical([session_id, event["revision"], table, event["payload"], event["previous_hash"]]).encode()).hexdigest()
                if table not in TABLE_KEYS or event["previous_hash"] != previous.get(session_id, "") or digest != event["event_hash"]:
                    raise corrupt()
                previous[session_id] = digest
                record = json.loads(event["payload"])
                if record["session_id"] != session_id:
                    raise corrupt()
                for name in OBJECT_FIELDS & set(record):
                    if record[name] is not None:
                        self._get_object(record[name])
                records[table][tuple(record[key] for key in TABLE_KEYS[table])] = record
            for table in TABLE_KEYS:
                db.execute(f"DELETE FROM {table}")
                for record in records[table].values():
                    self._upsert(db, table, record)
            return {table: len(rows) for table, rows in records.items()}
