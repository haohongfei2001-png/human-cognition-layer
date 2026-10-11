"""Isolated, idempotent imports with an atomic pointer to a read-only old view.

Rollback is terminal in S1.3. It does not resume an old generator, delete the new
ledger, or reactivate a held call. A later reactivation protocol is not implied.
"""
from contextlib import contextmanager
from hashlib import sha256
import json
import os
from pathlib import Path
import sqlite3
import tempfile

from hcl.kernel.scope import failure, identifier, principal_identity
from hcl.kernel.types import Principal, RULE_VERSION, SourceHandle, freeze
from hcl.memory import codec
from hcl.memory.sqlite_store import SQLiteStateStore, corrupt
from hcl.memory.store import denied
from .compile import compile_snapshot
from .control import ACTIVE, READ_ONLY, read_control, version_bundle


class MigrationNamespace:
    def __init__(self, directory):
        self.directory = Path(directory).resolve()
        self.path = self.directory / "state.sqlite"

    @staticmethod
    def _checkpoint(stage):
        """Host fault-injection seam. Never populated from imported input."""

    @classmethod
    def import_snapshot(cls, directory, snapshot, *, namespace_id, owner, readers=None):
        principal_identity(owner)
        identifier(namespace_id)
        package = compile_snapshot(snapshot, namespace_id)
        imported_ids = {row["source_id"] for row in package["original"]["sources"]}
        if readers is None:
            readers = {key: (owner.subject_id,) for key in imported_ids}
        if set(readers) != imported_ids:
            raise ValueError("explicit reader mapping must cover every imported source identity")
        readers = {key: sorted(set(identifier(member) for member in members)) for key, members in readers.items()}
        # This is authenticated host ACL, never legacy permitted_observers.
        package["host_readers"] = readers
        package["owner"] = {"tenant": owner.tenant_id, "subject": owner.subject_id}
        body = codec.dumps(package)
        package_hash = sha256(body).hexdigest()
        target = cls(directory)
        if target.directory.exists():
            target._match(owner, namespace_id, package_hash)
            return target
        target.directory.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix=".hcl-import-", dir=target.directory.parent) as temporary:
            stage = Path(temporary) / "namespace"
            stage.mkdir()
            store = SQLiteStateStore(stage / "state.sqlite")
            try:
                members = sorted({owner.subject_id} | {member for values in readers.values() for member in values})
                session_id = "migration:" + sha256(namespace_id.encode()).hexdigest()
                with store._transaction(True) as db:
                    session = dict(session_id=session_id, tenant=owner.tenant_id, owner=owner.subject_id,
                                   members=codec.canonical(members), revision=1, epoch=0, rule=RULE_VERSION)
                    store._record(db, "sessions", session, 1)
                    for source in package["current_sources"]:
                        mapped = package["source_mapping"][source["old_key"]]
                        store._record(db, "sources", dict(session_id=session_id, source_id=mapped["source_id"],
                            version=mapped["version"], readers=codec.canonical(readers[source["source_id"]]),
                            object_hash=store._put_object({"text": source["text"], "formal_problem": source["formal_problem"]})), 1)
                    stored_hash = store._put_object(package)
                    if stored_hash != package_hash:
                        raise corrupt()
                    db.execute("""CREATE TABLE namespace_control(singleton INTEGER PRIMARY KEY CHECK(singleton=1),
                        namespace_id TEXT NOT NULL, tenant TEXT NOT NULL, owner TEXT NOT NULL, session_id TEXT NOT NULL,
                        package_hash TEXT NOT NULL, mode TEXT NOT NULL, active_target TEXT NOT NULL,
                        generation INTEGER NOT NULL, versions TEXT NOT NULL)""")
                    db.execute("INSERT INTO namespace_control VALUES(1,?,?,?,?,?,?,?,?,?)",
                        (namespace_id, owner.tenant_id, owner.subject_id, session_id, package_hash,
                         ACTIVE, "unified", 1, codec.canonical(version_bundle())))
                    db.execute("PRAGMA user_version=2")
                    cls._checkpoint("import_before_commit")
                cls._checkpoint("import_committed_unpublished")
            finally:
                store.close()
            # Publish database, objects and pointer together in the same filesystem.
            # A concurrent importer never overwrites an already published namespace.
            try:
                os.rename(stage, target.directory)
            except OSError:
                if not target.directory.exists():
                    raise
                target._match(owner, namespace_id, package_hash)
                return target
            descriptor = os.open(target.directory.parent, os.O_RDONLY)
            try:
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
        return target

    @contextmanager
    def _control(self, principal, *, write=False):
        principal_identity(principal)
        db = None
        try:
            # No create, initialization, repair, WAL mode change or schema downgrade.
            db = sqlite3.connect(self.path.as_uri() + ("?mode=rw" if write else "?mode=ro"), uri=True,
                                 isolation_level=None, timeout=10)
            db.row_factory = sqlite3.Row
            db.execute("BEGIN IMMEDIATE" if write else "BEGIN")
            if db.execute("PRAGMA user_version").fetchone()[0] != 2:
                raise corrupt()
            row = read_control(db)
            if row["tenant"] != principal.tenant_id or row["owner"] != principal.subject_id:
                raise denied()
            yield db, row
            db.commit()
        except (sqlite3.Error, OSError):
            if db is not None:
                db.rollback()
            raise failure("FAILED", "STORAGE_FAILURE", "namespace", "The namespace transaction could not complete.", "migration") from None
        finally:
            if db is not None:
                if db.in_transaction:
                    db.rollback()
                db.close()

    def _package(self, row):
        digest = row["package_hash"]
        if type(digest) is not str or len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
            raise corrupt()
        path = self.directory / "state.sqlite.objects" / digest
        if path.is_symlink():
            raise corrupt()
        body = path.read_bytes()
        if sha256(body).hexdigest() != digest:
            raise corrupt()
        try:
            package = codec.loads(body)
            if package["schema"] != "hcl-legacy-migration-1" or package["namespace"] != row["namespace_id"]:
                raise corrupt()
            return package
        except (ValueError, TypeError, KeyError):
            raise corrupt() from None

    def _match(self, owner, namespace_id, package_hash):
        with self._control(owner) as (_, row):
            self._package(row)
            if row["namespace_id"] != namespace_id or row["package_hash"] != package_hash:
                raise ValueError("namespace already binds a different immutable import")

    def open_store(self):
        # Ownership for tasks still comes from the authenticated HCL principal.
        return SQLiteStateStore(self.path)

    def receipt(self, principal):
        with self._control(principal) as (db, row):
            package = self._package(row)
            self._authorize_content(db, row, principal)
            result = freeze(dict(namespace=row["namespace_id"], session_id=row["session_id"],
                mode=row["mode"], generation=row["generation"], active_target=row["active_target"],
                package_hash=row["package_hash"], versions=json.loads(row["versions"]),
                source_mapping=package["source_mapping"], record_mapping=package["record_mapping"],
                records=package["records"], truth="NOT_ESTABLISHED"))
        self._fresh_content_authorization(principal)
        return result

    def legacy_view(self, principal):
        """Read-only original typed snapshot, including partial/quarantined fields.

        Encoded FormalProblem retains its explicit host-input type. Returned data
        is a detached immutable JSON view, never a handle into writable storage.
        """
        with self._control(principal) as (db, row):
            self._authorize_content(db, row, principal)
            result = freeze(codec.encode(self._package(row)["original"]))
        self._fresh_content_authorization(principal)
        return result

    def _fresh_content_authorization(self, principal):
        # Like engine cached delivery, leave the content-loading WAL snapshot
        # before the last permission check. No claim of eliminating all TOCTOU.
        with self._control(principal) as (db, row):
            self._authorize_content(db, row, principal)

    def _authorize_content(self, db, row, principal):
        # Namespace ownership permits administration, not a bypass of a later
        # source-read revocation. Mixed/partial packages are never over-exposed.
        # Quarantined, historical and withdrawn sources may have no active row:
        # their immutable import ACL remains mandatory. Conflicting versions of
        # one source share the explicit host policy; no reader union is inferred.
        package = self._package(row)
        if any(principal.subject_id not in readers for readers in package["host_readers"].values()):
            raise denied()
        session = db.execute("SELECT members FROM sessions WHERE session_id=?", (row["session_id"],)).fetchone()
        if session is None or principal.subject_id not in json.loads(session["members"]):
            raise denied()
        if any(principal.subject_id not in json.loads(source["readers"]) for source in
               db.execute("SELECT readers FROM sources WHERE session_id=?", (row["session_id"],))):
            raise denied()

    def rollback(self, principal, *, expected_generation):
        if type(expected_generation) is not int or expected_generation < 1:
            raise ValueError("exact expected namespace generation required")
        with self._control(principal, write=True) as (db, row):
            self._package(row)
            if row["mode"] != ACTIVE or row["generation"] != expected_generation:
                raise failure("DENIED", "NAMESPACE_GENERATION_CHANGED", "namespace", "The namespace generation is not current.", "migration")
            db.execute("UPDATE namespace_control SET mode=?,active_target=?,generation=generation+1 WHERE singleton=1",
                       (READ_ONLY, "legacy_snapshot"))
            self._checkpoint("rollback_before_commit")
        return freeze(dict(mode=READ_ONLY, generation=expected_generation + 1, active_target="legacy_snapshot"))

    def audit(self, principal):
        """Host-only accounting for isolated new logs, also available after rollback."""
        with self._control(principal) as (db, row):
            self._package(row)
            return freeze(dict(mode=row["mode"], generation=row["generation"],
                counts={table: db.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
                        for table in ("events", "sources", "inferences", "tasks", "calls")},
                calls=[dict(call) for call in db.execute("SELECT state,attempted,validation_code FROM calls ORDER BY task_key,call_id")]))
