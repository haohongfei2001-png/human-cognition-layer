"""Durable, content-free staging lineage for supported object writes.

The journal precedes every governed payload write. A crash before its SQLite
reference commits must not leave an unattributable private CAS or pending file.
"""
from hashlib import sha256
import hmac
import json
import os
from pathlib import Path
import re
import sqlite3
from uuid import uuid4

from hcl.kernel.scope import failure
from hcl.memory import codec
from hcl.memory.lineage import encoded_bindings, retained_bindings

PROTOCOL = "hcl-retained-object-stage-1"


def sync_directory(path):
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def root(store):
    directory = store.path.with_name(store.path.name + ".retention")
    if directory.is_symlink():
        from hcl.memory.sqlite_store import corrupt
        raise corrupt()
    if not directory.exists():
        directory.mkdir()
        sync_directory(directory.parent)
    return directory


def authorized_bindings(store, db, bindings):
    for session, token, _ in bindings:
        if db.execute("SELECT 1 FROM source_tombstones WHERE session_id=? AND source_token=?", (session, token)).fetchone():
            raise failure("DENIED", "CONTENT_ERASED", "retention",
                          "The referenced material was erased and cannot be retained again.", "governance")


def put(store, value, *, session_id, context=None, bindings=(), owner=None, dependencies=None, principal=None):
    from hcl.memory.governance import owner_key, read_owner, dependency_bindings, dependency_origins
    if not store._db.in_transaction:
        raise ValueError("governed object write requires its store transaction")
    salt = bytes.fromhex(store._revision_control["governance_salt"])
    origins = set()
    raw = set(bindings) | set(retained_bindings(value, session_id=session_id, origin_refs=origins))
    if context is not None:
        raw.update(retained_bindings(context, session_id=session_id, origin_refs=origins))
    if dependencies is not None:
        raw.update(dependency_bindings(store, store._db, session_id, principal, dependencies)[0])
    if any(row[0] != session_id for row in raw | origins):
        raise failure("INVALID_REQUEST", "RETENTION_SESSION_MISMATCH", "retention",
                      "A retained task artifact must belong to its authenticated execution session.", "governance")
    encoded = set(encoded_bindings(salt, raw))
    if dependencies is not None:
        encoded.update(dependency_origins(store._db, session_id, dependencies))
    for origin_session, result_id in origins:
        prior = read_owner(store._db, owner_key(store._db, ("inference", origin_session, result_id)))
        if prior is None:
            from hcl.memory.sqlite_store import corrupt
            raise corrupt()
        encoded.update(map(tuple, json.loads(prior["bindings"])))
    if owner is not None:
        prior = read_owner(store._db, owner_key(store._db, owner))
        if prior:
            encoded.update(map(tuple, json.loads(prior["bindings"])))
    if len(encoded) > 16384:
        raise failure("BUDGET_EXHAUSTED", "RETENTION_BINDING_BOUND", "retention",
                      "The retained content binding set exceeds its bound.", "governance")
    authorized_bindings(store, store._db, encoded)
    directory = root(store)
    nonce = uuid4().hex
    digest = sha256(codec.dumps(value)).hexdigest()
    body = dict(protocol=PROTOCOL, nonce=nonce, object_hash=digest,
                temporary_prefix="pending-" + nonce + "-", bindings=sorted(encoded))
    body["integrity"] = hmac.new(salt, codec.canonical(body).encode(), sha256).hexdigest()
    serialized = codec.canonical(body).encode()
    if len(serialized) > 4 * 1024 * 1024:
        raise failure("BUDGET_EXHAUSTED", "RETENTION_JOURNAL_BOUND", "retention",
                      "The retained object journal exceeds its maintenance bound.", "governance")
    path = directory / (nonce + ".json")
    # A torn metadata write must not masquerade as an invalid published journal
    # and permanently block unrelated source maintenance. No payload write is
    # allowed until the complete journal has atomically published and fsynced.
    temporary = directory / (nonce + ".pending")
    with temporary.open("xb") as stream:
        stream.write(serialized)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)
    sync_directory(directory)
    store._retention_journals.append((path, digest))
    store._checkpoint("retention_journal_persisted")
    previous = getattr(store, "_retention_current_journal", None)
    store._retention_current_journal = nonce
    try:
        actual = store._put_object(value)
        if actual != digest:
            raise ValueError("governed object identity changed")
        return actual
    finally:
        store._retention_current_journal = previous


def cleanup_committed(store):
    """Remove only metadata whose payload already has a durable live reference.

    Cleanup failure keeps an attributable journal for later maintenance, without
    turning a committed task into an apparent rollback or deleting its payload.
    """
    changed = False
    for path, digest in store._retention_journals:
        try:
            if store._db.execute("SELECT 1 FROM retention_refs WHERE object_hash=? AND state='LIVE' LIMIT 1", (digest,)).fetchone():
                path.unlink(missing_ok=True)
                changed = True
        except (OSError, sqlite3.Error):
            continue
    if changed:
        try:
            sync_directory(root(store))
        except OSError:
            pass


def pending(store):
    """Validate retained staging metadata; never inspect staged payload bytes."""
    salt = bytes.fromhex(store._revision_control["governance_salt"])
    directory = store.path.with_name(store.path.name + ".retention")
    if directory.is_symlink():
        raise ValueError("invalid retained object journal directory")
    if not directory.exists():
        return ()
    entries = []
    for count, path in enumerate(directory.iterdir()):
        if count >= 100000:
            raise failure("BUDGET_EXHAUSTED", "RETENTION_JOURNAL_BOUND", "retention",
                          "The retained object journal exceeds its maintenance bound.", "governance")
        if path.is_symlink() or not path.is_file() or path.stat().st_size > 4 * 1024 * 1024:
            raise ValueError("invalid retained object journal")
        if re.fullmatch(r"[0-9a-f]{32}\.pending", path.name):
            continue  # Incomplete content-free metadata; no payload can precede publication.
        if not re.fullmatch(r"[0-9a-f]{32}\.json", path.name):
            raise ValueError("invalid retained object journal")
        row = json.loads(path.read_text())
        digest = row.pop("integrity")
        if (row["protocol"] != PROTOCOL or row["nonce"] + ".json" != path.name
                or row["temporary_prefix"] != "pending-" + row["nonce"] + "-"
                or not re.fullmatch(r"[0-9a-f]{64}", row["object_hash"])
                or not hmac.compare_digest(digest, hmac.new(salt, codec.canonical(row).encode(), sha256).hexdigest())):
            raise ValueError("retained object journal integrity mismatch")
        entries.append(dict(row, path=path))
    return tuple(entries)
