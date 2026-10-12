"""Explicit side-copy upgrade of S1 ledgers; old writers are terminally fenced.

The durable ordering deliberately permits downtime: verified unpublished copy,
old terminal fence, then atomic target-directory publication. It never permits
both old and new stores to be active. Recovery cannot create a second target,
release a reservation, infer an abandoned owner, or resend an unknown call.
"""

from contextlib import contextmanager
from hashlib import sha256
import json
import os
from pathlib import Path
import shutil
import sqlite3
from uuid import uuid4

from hcl.kernel.scope import failure, principal_identity
from hcl.kernel.types import RULE_VERSION, freeze
from hcl.memory import codec
from hcl.memory.sqlite_store import TABLE_KEYS, OBJECT_FIELDS, SQLiteStateStore, corrupt
from hcl.memory.store import denied
from .control import ACTIVE as LEGACY_ACTIVE, read_control, version_bundle
from . import revision_control as control

# Exact shipped S1.3 / S2.1 runtime bundles, not blanket acceptance of old code.
PREDECESSOR_CODE_HASHES = frozenset(
    {
        "99a1320fea14505ec3132527259cb8b2b4c0560a87d9cbb6f5fb0724731388c8",
        "6300fbe06ebcc6580a8c1e64c8c183e16bd43b46a746e2bee1973ef45e78af8f",
    }
)


def _sync_directory(path):
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _persist(path, value):
    pending = path.with_name(path.name + ".pending-" + uuid4().hex)
    try:
        with pending.open("xb") as stream:
            stream.write(codec.canonical(value).encode())
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(pending, path)
        _sync_directory(path.parent)
    finally:
        pending.unlink(missing_ok=True)


def _connect(path, *, write=False):
    db = sqlite3.connect(
        path.as_uri() + ("?mode=rw" if write else "?mode=ro"), uri=True, isolation_level=None, timeout=10
    )
    db.row_factory = sqlite3.Row
    if write:
        db.execute("PRAGMA synchronous=FULL")
    return db


def _authorize(db, principal):
    principal_identity(principal)
    rows = list(db.execute("SELECT * FROM sessions"))
    if not rows or any(
        row["tenant"] != principal.tenant_id or row["owner"] != principal.subject_id for row in rows
    ):
        raise denied()
    if any(row["rule"] != RULE_VERSION for row in rows):
        raise ValueError("unsupported predecessor rule version")


def _history(db, object_root, *, load_content=True):
    """Validate every old event/object and exact projection, without repairing it."""
    from hcl.memory.erasure import event_keys, object_references, REDACTED
    keys = event_keys(db)
    if set(keys) != set(TABLE_KEYS):
        from hcl.memory.governance import verify_inventory
        verify_inventory(db)
    previous, records, objects, events = {}, {key: {} for key in keys}, set(), []
    columns = {table: {row[1] for row in db.execute(f"PRAGMA table_info({table})")} for table in keys}
    for event in db.execute("SELECT * FROM events ORDER BY seq"):
        if len(events) >= 100000:
            raise ValueError("explicit migration event bound exceeded")
        row = dict(event)
        table = row["kind"]
        session = row["session_id"]
        digest = sha256(
            codec.canonical([session, row["revision"], table, row["payload"], row["previous_hash"]]).encode()
        ).hexdigest()
        if (
            (table not in keys and table != REDACTED)
            or previous.get(session, "") != row["previous_hash"]
            or row["event_hash"] != digest
        ):
            raise corrupt()
        previous[session] = digest
        record = json.loads(row["payload"])
        if table == REDACTED:
            if record["session_id"] != session:
                raise corrupt()
            events.append(row)
            continue
        if set(record) != columns[table] or record["session_id"] != session:
            raise corrupt()
        records[table][tuple(record[key] for key in keys[table])] = record
        objects.update(object_references(table, record))
        events.append(row)
    for table, expected in records.items():
        actual = {
            tuple(row[key] for key in keys[table]): dict(row)
            for row in db.execute(f"SELECT * FROM {table}")
        }
        if actual != expected:
            raise corrupt()
    tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    namespace = read_control(db) if "namespace_control" in tables else None
    legacy_package = namespace["package_hash"] if namespace else None
    capsule_root = None
    if legacy_package:
        if "legacy_roots" in tables:
            roots = list(db.execute("SELECT * FROM legacy_roots"))
            if roots and (len(roots) != 1 or roots[0]["object_hash"] != legacy_package
                          or roots[0]["session_id"] != namespace["session_id"]):
                raise corrupt()
            capsule_root = roots[0] if roots else None
        objects.add(legacy_package)
    erased = "source_tombstones" in tables and db.execute("SELECT 1 FROM source_tombstones LIMIT 1").fetchone() is not None
    size = 0
    for digest in sorted(objects):
        if (
            type(digest) is not str
            or len(digest) != 64
            or any(char not in "0123456789abcdef" for char in digest)
        ):
            raise corrupt()
        if not load_content:
            continue  # Published-target retry needs original metadata, not old raw bytes.
        path = object_root / digest
        if path.is_symlink() or not path.is_file() or path.stat().st_size > 4 * 1024 * 1024:
            raise corrupt()
        size += path.stat().st_size
        if size > 128 * 1024 * 1024:
            raise ValueError("explicit migration content bound exceeded")
        if erased and digest == legacy_package and capsule_root is None:
            # This unresolved mixed capsule is explicitly retained/blocked, not
            # delivered or re-decoded after erasure. A later scoped conversion
            # must separately validate its exact original bytes.
            continue
        body = path.read_bytes()
        if sha256(body).hexdigest() != digest:
            raise corrupt()
        value = codec.loads(body)
        if capsule_root is not None and digest == legacy_package:
            from .capsules import validate_root
            validate_root(value, namespace["namespace_id"], capsule_root["import_hash"])
    payload = {
        "events": events,
        "projections": {key: sorted(values.values(), key=codec.canonical) for key, values in records.items()},
    }
    return sha256(codec.canonical(payload).encode()).hexdigest(), tuple(sorted(objects)), events


S22_CODE_HASH = "ff8d68236a625b575c4d39f4eabf7aeba7da034ae5277338d6a518b4723fecea"
S23_CODE_HASH = "badb3f7745a21193f199c4224847ccc931e4079e1d545c17825762b651d2404f"
S3_FINITE_CODE_HASH = "5087d2f8bb75441bd176fa715f50fcb46709d877e23322d7ecf0765b9fc39ee8"
S4_ARGUMENT_CODE_HASH = "f4a534f8b0beed70fde28a90372023efe7161b43eea6955ea1e87046303bc374"
M04_DISCOVERY_CODE_HASH = "1d8dd8c70f98fe8b370939f016615550b09fc7aa1dbcaf7d27820b479f89ebbd"
M04_QUALIFIED_CODE_HASH = "d733606ff73ab7f923b082fb0c56ab195db235ded81667739588d6f48664cfde"
M07_INTERACTION_CODE_HASH = "0143be82cb3f96b801abd79b86e2cd35f811645f8bce9497c3dd49863735b45a"
M08_AFFECT_CODE_HASH = "596b7e52d66e320ab66cdf4a9ef87c3fee96af2e65559440e1df7bdf4d4590d8"
M09_RELATIONSHIP_CODE_HASH = "c11fe822eee9df604ec02887638f8b7af323489317097a9b4ecf9375bcbcd510"
# Development predecessor: replace the test commit with its verified identical
# published main identity before this governance candidate can be published.
M10_RETRIEVAL_CODE_HASH = "0cff907d511fc684251b4bcce902e5800b372885ed4b27bd8989f99c22fc436f"
REVISION_PREDECESSORS = frozenset((S22_CODE_HASH, S23_CODE_HASH, S3_FINITE_CODE_HASH, S4_ARGUMENT_CODE_HASH, M04_DISCOVERY_CODE_HASH, M04_QUALIFIED_CODE_HASH, M07_INTERACTION_CODE_HASH, M08_AFFECT_CODE_HASH, M09_RELATIONSHIP_CODE_HASH, M10_RETRIEVAL_CODE_HASH))


def _target_schema(schema):
    return {1: 3, 2: 4, 3: 3, 4: 4}[schema]


def _validate_predecessor(db, schema, source_path):
    if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='cutover_control'").fetchone():
        raise ValueError("active predecessor has unexpected terminal cutover metadata")
    if schema == 1:
        return
    if schema in (3, 4):
        revision = control.read_legacy(db)
        bundle = json.loads(revision["versions"])
        expected = {"schema": schema, "rules": RULE_VERSION, "indexes": {"revision": 1}, "code_sha256": bundle.get("code_sha256")}
        if bundle.get("code_sha256") == M10_RETRIEVAL_CODE_HASH:
            expected["indexes"] = {"revision": 1, "retrieval": "hcl-evidence-retrieval-1"}
        if (revision["mode"] != control.ACTIVE or bundle != expected
                or bundle.get("code_sha256") not in REVISION_PREDECESSORS
                or revision["target_path"] != str(source_path)):
            raise ValueError("unsupported, relocated or inactive revision predecessor")
        if schema == 4:
            namespace = read_control(db)
            if namespace["mode"] != LEGACY_ACTIVE or json.loads(namespace["versions"]) != bundle:
                raise ValueError("controlled predecessor bundles disagree")
        return
    row = read_control(db)
    bundle = json.loads(row["versions"])
    expected = {"schema": 2, "rules": RULE_VERSION, "indexes": {}}
    if (
        row["mode"] != LEGACY_ACTIVE
        or any(bundle.get(key) != value for key, value in expected.items())
        or set(bundle) != {"schema", "rules", "indexes", "code_sha256"}
        or bundle["code_sha256"] not in PREDECESSOR_CODE_HASHES | REVISION_PREDECESSORS | {version_bundle()["code_sha256"]}
    ):
        raise ValueError("unsupported or inactive controlled predecessor")


class RevisionCutover:
    def __init__(self, source, directory):
        source, directory = Path(source), Path(directory)
        if source.is_symlink() or directory.is_symlink():
            raise ValueError("explicit nonsymlink cutover paths required")
        self.source = source.resolve()
        self.directory = directory.resolve()
        if self.source == self.directory or self.directory in self.source.parents:
            raise ValueError("separate cutover destination required")
        self.path = self.directory / "state.sqlite"
        self.intent = self.directory.with_name("." + self.directory.name + ".cutover.json")
        self.stage = self.directory.with_name("." + self.directory.name + ".unpublished")

    @staticmethod
    def _checkpoint(stage):
        """Only a trusted test fault seam, never supplied by source/model input."""

    @classmethod
    def upgrade(cls, source, directory, principal):
        target = cls(source, directory)
        target._upgrade(principal)
        return target

    def _upgrade(self, principal):
        db = None
        try:
            self.directory.parent.mkdir(parents=True, exist_ok=True)
            db = _connect(self.source, write=True)
            db.execute("BEGIN IMMEDIATE")
            _authorize(db, principal)
            schema = db.execute("PRAGMA user_version").fetchone()[0]
            if schema not in (1, 2, 3, 4, control.TERMINAL_SOURCE):
                raise ValueError("explicit supported predecessor required")
            if self.intent.exists():
                if self.intent.is_symlink():
                    raise ValueError("invalid cutover intent path")
                intent = json.loads(self.intent.read_text())
                if intent.get("source") != str(self.source) or intent.get("target") != str(self.directory):
                    raise ValueError("cutover intent identity mismatch")
            elif schema == control.TERMINAL_SOURCE or self.directory.exists() or self.stage.exists():
                raise ValueError("cutover recovery requires its original intent")
            else:
                intent = {
                    "format": "hcl-ledger-cutover-1",
                    "upgrade_id": uuid4().hex,
                    "source": str(self.source),
                    "target": str(self.directory),
                    "origin_schema": schema,
                    "target_schema": _target_schema(schema),
                    "versions": version_bundle(schema=_target_schema(schema)),
                    "checkpoint": None,
                    "phase": "PREPARING",
                }
                _persist(self.intent, intent)
            if (
                intent.get("format") != "hcl-ledger-cutover-1"
                or intent.get("origin_schema") not in (1, 2, 3, 4)
                or intent.get("target_schema") != _target_schema(intent["origin_schema"])
                or intent.get("versions") != version_bundle(schema=intent["target_schema"])
            ):
                raise ValueError("cutover intent version mismatch")
            object_root = self.source.with_name(self.source.name + ".objects")
            if object_root.is_symlink():
                raise ValueError("invalid predecessor object root")
            checkpoint, objects, source_events = _history(
                db, object_root, load_content=not (schema == control.TERMINAL_SOURCE and self.directory.exists()))
            if schema in (1, 2, 3, 4):
                if schema != intent["origin_schema"] or self.directory.exists():
                    raise ValueError("cutover source/target identity conflict")
                _validate_predecessor(db, schema, self.source)
                # Only our exact, still-unpublished copy can be rebuilt. The old
                # store remains the sole writer until this entire copy verifies.
                if self.stage.exists():
                    if self.stage.is_symlink() or not (self.stage / "intent.json").is_file():
                        raise ValueError("unowned cutover stage")
                    marker = json.loads((self.stage / "intent.json").read_text())
                    if marker.get("upgrade_id") != intent["upgrade_id"]:
                        raise ValueError("foreign cutover stage")
                    shutil.rmtree(self.stage)
                # A failed marker write cannot strand an unowned final stage.
                # Publish the owned staging directory only after its marker is
                # durable. The unique preparation directory is ours to clean.
                preparation = self.stage.with_name(self.stage.name + ".preparing-" + uuid4().hex)
                preparation.mkdir()
                try:
                    _persist(preparation / "intent.json", intent)
                    os.rename(preparation, self.stage)
                    _sync_directory(self.stage.parent)
                finally:
                    if preparation.exists():
                        shutil.rmtree(preparation)
                copied = self.stage / "state.sqlite"
                view = _connect(self.source)
                copy = sqlite3.connect(copied, isolation_level=None)
                try:
                    view.backup(copy)  # separate read connection under old writer lock
                    copy.execute(f"PRAGMA user_version={control.UNPUBLISHED}")
                finally:
                    view.close()
                    copy.close()
                destination_objects = self.stage / "state.sqlite.objects"
                destination_objects.mkdir()
                for digest in objects:
                    with (destination_objects / digest).open("wb") as stream:
                        stream.write((object_root / digest).read_bytes())
                        stream.flush()
                        os.fsync(stream.fileno())
                _sync_directory(destination_objects)
                verification = _connect(copied)
                try:
                    if _history(verification, destination_objects)[0] != checkpoint:
                        raise corrupt()
                finally:
                    verification.close()
                intent.update(checkpoint=checkpoint, phase="PREPARED")
                _persist(self.intent, intent)
                _persist(self.stage / "intent.json", intent)
                self._checkpoint("prepared")
                binding = {key: value for key, value in intent.items() if key != "phase"}
                db.execute(
                    "CREATE TABLE cutover_control(singleton INTEGER PRIMARY KEY CHECK(singleton=1), binding TEXT NOT NULL)"
                )
                db.execute("INSERT INTO cutover_control VALUES(1,?)", (codec.canonical(binding),))
                if schema in (3, 4):
                    # Old read-only helpers validated their own control but did
                    # not inspect user_version. Terminally invalidate that old
                    # reader contract too, so a chained ancestor export cannot
                    # bypass the latest target's erasure/authorization fence.
                    db.execute("UPDATE revision_control SET mode='TERMINAL_SOURCE' WHERE singleton=1")
                db.execute(f"PRAGMA user_version={control.TERMINAL_SOURCE}")
                db.commit()  # Every already-open old connection now fails its fence.
                # Retake the terminal source's lock for the entire recovery /
                # activation / publication tail. A competing recovery may run
                # first in this gap, but cannot run concurrently after this lock.
                db.execute("BEGIN IMMEDIATE")
            else:
                rows = db.execute("SELECT binding FROM cutover_control WHERE singleton=1").fetchall()
                binding = {key: value for key, value in intent.items() if key != "phase"}
                if len(rows) != 1 or json.loads(rows[0][0]) != binding or checkpoint != intent["checkpoint"]:
                    raise ValueError("terminal source belongs to another exact cutover")
                if intent["origin_schema"] in (3, 4):
                    old_control = db.execute("SELECT mode FROM revision_control").fetchall()
                    if len(old_control) != 1 or old_control[0][0] != "TERMINAL_SOURCE":
                        raise ValueError("terminal predecessor reader fence is missing")
                # Keep BEGIN IMMEDIATE until publication and receipt persistence.
            self._checkpoint("source_fenced")
            if not self.directory.exists():
                staged = self.stage / "state.sqlite"
                if self.stage.is_symlink() or not staged.is_file():
                    raise ValueError("verified unpublished target required for recovery")
                copy = _connect(staged, write=True)
                try:
                    copy.execute("BEGIN IMMEDIATE")
                    stage_schema = copy.execute("PRAGMA user_version").fetchone()[0]
                    if stage_schema == control.UNPUBLISHED:
                        if _history(copy, self.stage / "state.sqlite.objects")[0] != intent["checkpoint"]:
                            raise corrupt()
                        if intent["origin_schema"] in (3, 4):
                            # Only this fully verified unpublished copy may replace
                            # its predecessor control. Original source metadata is
                            # retained under the terminal fence for audit.
                            _validate_predecessor(copy, intent["origin_schema"], self.source)
                            copy.execute("DROP TABLE revision_control")
                        control.install(
                            copy,
                            schema=intent["target_schema"],
                            upgrade_id=intent["upgrade_id"],
                            origin_schema=intent["origin_schema"],
                            checkpoint=intent["checkpoint"],
                            source_path=str(self.source),
                            target_path=str(self.path),
                        )
                        from hcl.memory.governance import backfill
                        salt = bytes.fromhex(control.read(copy)["governance_salt"])
                        object_root = self.stage / "state.sqlite.objects"
                        def read_original(digest):
                            body = (object_root / digest).read_bytes()
                            if sha256(body).hexdigest() != digest:
                                raise corrupt()
                            return codec.loads(body)
                        backfill(copy, salt, read_original,
                                 object_size=lambda digest: (object_root / digest).stat().st_size)
                        if intent["target_schema"] == 4:
                            copy.execute(
                                "UPDATE namespace_control SET versions=? WHERE singleton=1",
                                (codec.canonical(intent["versions"]),),
                            )
                        copy.execute(f"PRAGMA user_version={intent['target_schema']}")
                    elif stage_schema != intent["target_schema"]:
                        raise ValueError("unknown unpublished schema")
                    else:
                        from hcl.memory.erasure import authorized_prefix
                        _, _, staged_events = _history(copy, self.stage / "state.sqlite.objects")
                        if not authorized_prefix(copy, source_events, staged_events):
                            raise corrupt()
                    self._validate_target_identity(copy, intent)
                    copy.commit()
                finally:
                    if copy.in_transaction:
                        copy.rollback()
                    copy.close()
                self._checkpoint("target_activated_unpublished")
                # A directory publication moves DB and objects together. If a
                # competing recovery already published, validate it below.
                try:
                    os.rename(self.stage, self.directory)
                except OSError:
                    if not self.directory.exists():
                        raise
                _sync_directory(self.directory.parent)
            self._checkpoint("published")
            self._verify_published(intent, source_events)
            intent["phase"] = "PUBLISHED"
            _persist(self.intent, intent)
        except (sqlite3.Error, OSError):
            raise failure(
                "FAILED",
                "STORAGE_FAILURE",
                "migration",
                "The cutover could not complete safely.",
                "migration",
            ) from None
        finally:
            if db is not None:
                if db.in_transaction:
                    db.rollback()
                db.close()

    def _validate_target_identity(self, db, intent):
        row = control.read(db)
        if (
            db.execute("PRAGMA user_version").fetchone()[0] != intent["target_schema"]
            or row["upgrade_id"] != intent["upgrade_id"]
            or row["source_path"] != str(self.source)
            or row["target_path"] != str(self.path)
            or row["checkpoint"] != intent["checkpoint"]
            or row["origin_schema"] != intent["origin_schema"]
            or json.loads(row["versions"]) != intent["versions"]
        ):
            raise ValueError("published target does not match its exact cutover")

    def _verify_published(self, intent, source_events):
        db = _connect(self.path)
        try:
            db.execute("BEGIN")
            self._validate_target_identity(db, intent)
            _, _, events = _history(db, self.path.with_name(self.path.name + ".objects"))
            from hcl.memory.erasure import authorized_prefix
            if not authorized_prefix(db, source_events, events):
                raise corrupt()
            db.commit()
        finally:
            db.close()

    def open_store(self):
        return SQLiteStateStore(self.path)

    @contextmanager
    def _target(self, principal, *, write=False):
        db = _connect(self.path, write=write)
        try:
            db.execute("BEGIN IMMEDIATE" if write else "BEGIN")
            _authorize(db, principal)
            if (db.execute("PRAGMA user_version").fetchone()[0] not in (3, 4)
                    or db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='cutover_control'").fetchone()):
                raise failure("DENIED", "REVISION_NAMESPACE_FENCED", "namespace",
                              "The namespace has been superseded by its terminal cutover.", "migration")
            row = control.read(db)
            if row["source_path"] != str(self.source) or row["target_path"] != str(self.path):
                raise corrupt()
            yield db, row
            db.commit()
        finally:
            if db.in_transaction:
                db.rollback()
            db.close()

    def rollback(self, principal):
        with self._target(principal, write=True) as (db, row):
            if row["mode"] != control.ACTIVE:
                raise ValueError("rollback is terminal and cannot reactivate execution")
            db.execute("UPDATE revision_control SET mode=? WHERE singleton=1", (control.READ_ONLY,))
        return freeze(
            {"mode": control.READ_ONLY, "old_writer": "TERMINALLY_FENCED", "new_ledger": "RETAINED_NO_RESEND"}
        )

    def _read_authorization(self, db, principal):
        # Historical predecessor exports cannot resurrect locally erased bytes.
        # A selective capsule export is required before this whole-ledger view
        # can reopen after any source erasure.
        if db.execute("SELECT 1 FROM source_tombstones LIMIT 1").fetchone():
            raise failure("DENIED", "ERASED_HISTORICAL_EXPORT", "legacy_view",
                          "The historical whole-ledger view contains erased material.", "governance")
        # Old read-only material must not resurrect access revoked on the target.
        if any(
            principal.subject_id not in json.loads(row["members"])
            for row in db.execute("SELECT members FROM sessions")
        ):
            raise denied()
        if any(
            principal.subject_id not in json.loads(row["readers"])
            for row in db.execute("SELECT readers FROM sources")
        ):
            raise denied()
        tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if "namespace_control" in tables:
            row = read_control(db)
            root = db.execute("SELECT * FROM legacy_roots WHERE session_id=?", (row["session_id"],)).fetchone()
            if root:
                if root["object_hash"] != row["package_hash"]:
                    raise corrupt()
                if any(principal.subject_id not in json.loads(value[key]) for value in db.execute(
                        "SELECT readers,reader_ceiling FROM legacy_capsules WHERE kind='SOURCE'")
                        for key in ("readers", "reader_ceiling")):
                    raise denied()
                body = (self.path.with_name(self.path.name + ".objects") / root["object_hash"]).read_bytes()
                if sha256(body).hexdigest() != root["object_hash"]:
                    raise corrupt()
                from .capsules import validate_root
                validate_root(codec.loads(body), row["namespace_id"], root["import_hash"])
                return
            digest = row["package_hash"]
            body = (self.path.with_name(self.path.name + ".objects") / digest).read_bytes()
            if sha256(body).hexdigest() != digest:
                raise corrupt()
            package = codec.loads(body)
            if any(principal.subject_id not in members for members in package["host_readers"].values()):
                raise denied()

    def legacy_view(self, principal):
        with self._target(principal) as (target, _):
            self._read_authorization(target, principal)
            db = _connect(self.source)
            try:
                db.execute("BEGIN")
                if db.execute("PRAGMA user_version").fetchone()[0] != control.TERMINAL_SOURCE:
                    raise corrupt()
                _authorize(db, principal)
                object_root = self.source.with_name(self.source.name + ".objects")
                _, objects, _ = _history(db, object_root)
                result = freeze(
                    {
                        "projections": {
                            table: [dict(row) for row in db.execute(f"SELECT * FROM {table}")]
                            for table in TABLE_KEYS
                        },
                        "objects": {
                            digest: codec.encode(codec.loads((object_root / digest).read_bytes()))
                            for digest in objects
                        },
                        "scope": "HISTORICAL_ORIGINAL_NOT_CURRENT_INFERENCE",
                    }
                )
                db.commit()
            finally:
                db.close()
        # Leave the content-reading WAL snapshot before final permission check.
        with self._target(principal) as (db, _):
            self._read_authorization(db, principal)
        return result

    def audit(self, principal):
        with self._target(principal) as (db, row):
            return freeze(
                {
                    "mode": row["mode"],
                    "upgrade_id": row["upgrade_id"],
                    "calls": [
                        dict(call)
                        for call in db.execute(
                            "SELECT state,attempted,validation_code FROM calls ORDER BY task_key,call_id"
                        )
                    ],
                    "event_count": db.execute("SELECT count(*) FROM events").fetchone()[0],
                }
            )
