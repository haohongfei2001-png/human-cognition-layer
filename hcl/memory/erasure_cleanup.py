"""Resumable cleanup of explicitly owned, already-redacted local references.

No predecessor, backup, public evidence package or provider copy is touched.
File unlink is never reported complete while a SQLite reader retains old WAL
pages. Tests use only temporary synthetic namespaces.
"""
import json
import os
import re
import sqlite3

from hcl.kernel.scope import failure
from hcl.memory import codec
from hcl.memory.governance import verify_inventory, require_governed
from hcl.memory.retention_objects import pending, sync_directory


def _row(store, db, session_id, principal, erasure_id):
    store._session(db, session_id, principal, owner=True)
    require_governed(store)
    row = db.execute("SELECT * FROM erasures WHERE erasure_id=?", (erasure_id,)).fetchone()
    if row is None or (row["session_id"], row["tenant"], row["owner"]) != (
            session_id, principal.tenant_id, principal.subject_id):
        raise failure("DENIED", "ERASURE_IDENTITY_MISMATCH", "erasure_id",
                      "The erasure is not owned by the authenticated session.", "governance")
    return dict(row)


def receipt(store, session_id, principal, erasure_id):
    with store._transaction(maintenance=True) as db:
        row = _row(store, db, session_id, principal, erasure_id)
        verify_inventory(db)
        return json.loads(row["receipt"])


def _files(store, db, row):
    """Called with the database writer lock, including every filesystem unlink."""
    _, references = verify_inventory(db)
    target = json.loads(row["targets"])
    plan = target["plan"]
    staged = pending(store)
    own = {item["nonce"] for item in plan["staged_objects"]}
    independent = {ref["object_hash"] for ref in references.values()}
    independent.update(item["object_hash"] for item in staged if item["nonce"] not in own)
    known = set(independent)
    for intent in db.execute("SELECT targets FROM erasures"):
        previous_plan = json.loads(intent[0])["plan"]
        known.update(previous_plan["objects_to_unlink"])
        known.update(item["object_hash"] for item in previous_plan["staged_objects"])
    known.update(item["object_hash"] for item in staged)
    tables = {item[0] for item in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if "namespace_control" in tables:
        known.add(db.execute("SELECT package_hash FROM namespace_control").fetchone()[0])
    if store.object_root.is_symlink():
        raise ValueError("invalid managed object directory")
    entries = []
    unknown = 0
    prefixes = {item["temporary_prefix"] for item in staged}
    for path in store.object_root.iterdir():
        if len(entries) >= 100000:
            raise failure("BUDGET_EXHAUSTED", "ERASURE_FILE_SCAN_BOUND", "retention",
                          "The owned object cleanup exceeds its maintenance bound.", "governance")
        if path.is_symlink() or not path.is_file():
            raise ValueError("invalid managed object member")
        if path.name not in known and not path.name[:41] in prefixes:
            unknown += 1
        entries.append(path)
    # Do not guess ownership of a raw host/admin orphan or old untracked file.
    # Known target objects may still be cleaned; the receipt names the gap.
    allowed = set(plan["objects_to_unlink"]) - independent
    prefixes = {item["temporary_prefix"] for item in plan["staged_objects"]}
    for path in entries:
        if path.name in allowed or path.name[:41] in prefixes:
            path.unlink()
            store._checkpoint("erasure_object_unlinked")
    sync_directory(store.object_root)
    store._checkpoint("erasure_objects_directory_synced")
    journal_root = store.path.with_name(store.path.name + ".retention")
    for item in staged:
        if item["nonce"] in own:
            item["path"].unlink()
    if journal_root.exists():
        for path in journal_root.iterdir():
            if re.fullmatch(r"[0-9a-f]{32}\.pending", path.name):
                # Published journals are .json; a pending metadata file always
                # precedes every private payload write and contains no raw text.
                path.unlink()
        sync_directory(journal_root)
    return dict(unknown_owned_objects=unknown,
                newly_shared_objects_retained=len(set(plan["objects_to_unlink"]) & independent))


def resume(store, session_id, principal, erasure_id):
    """Idempotent host maintenance, never automatically dispatched by run()."""
    with store._transaction(True, maintenance=True) as db:
        row = _row(store, db, session_id, principal, erasure_id)
        if row["status"] == "LOCAL_REFERENCE_ERASURE_COMPLETE":
            verify_inventory(db)
            return json.loads(row["receipt"])
        details = _files(store, db, row)
    store._checkpoint("erasure_files_cleaned")
    # VACUUM is outside a transaction by SQLite contract. The tombstone and the
    # current runtime write gate already prevent erased tasks/sources retaining
    # content during this interval. Independent data remains writable.
    scrubbed = False
    try:
        with store._lock:
            store._db.execute("PRAGMA secure_delete=ON")
            store._db.execute("VACUUM")
            store._checkpoint("erasure_database_vacuumed")
            checkpoint = store._db.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()
            scrubbed = checkpoint[0] == 0 and checkpoint[1] == 0 and checkpoint[2] == 0
            if scrubbed:
                with store.path.open("rb") as stream:
                    os.fsync(stream.fileno())
                sync_directory(store.path.parent)
                store._checkpoint("erasure_database_scrubbed")
    except (sqlite3.Error, OSError):
        # The committed logical fence and accounting survive. A later explicit
        # resume retries physical cleanup; no source path/error text is returned.
        scrubbed = False
    with store._transaction(True, maintenance=True) as db:
        row = _row(store, db, session_id, principal, erasure_id)
        result = json.loads(row["receipt"])
        limitations = [item for item in result["limitations"]
                       if item not in ("UNATTRIBUTED_OBJECTS_RETAINED", "DATABASE_SCRUB_PENDING")]
        if details["unknown_owned_objects"]:
            limitations.append("UNATTRIBUTED_OBJECTS_RETAINED")
        if not scrubbed:
            limitations.append("DATABASE_SCRUB_PENDING")
        result.update(details, database_scrubbed=scrubbed, limitations=limitations,
                      status="PARTIAL_ERASURE_RETAINED_COPIES" if limitations else "LOCAL_REFERENCE_ERASURE_COMPLETE")
        encoded = codec.canonical(result)
        if row["status"] != result["status"] or row["receipt"] != encoded:
            row.update(status=result["status"], receipt=encoded)
            revision = store._session(db, session_id, principal, owner=True)["revision"]
            store._record(db, "erasures", row, revision)
    # This last WAL transaction only contains content-free erasure accounting.
    return result
