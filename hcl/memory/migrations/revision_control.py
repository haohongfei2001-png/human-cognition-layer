"""Terminal cutover fences for the query-dependency storage protocol."""

from hcl.kernel.scope import failure
from hcl.memory import codec
import secrets
from hashlib import sha256
from .control import version_bundle

ACTIVE = "ACTIVE"
READ_ONLY = "READ_ONLY"
TERMINAL_SOURCE = 91
UNPUBLISHED = 92


def install(db, *, schema, upgrade_id, origin_schema, checkpoint, source_path, target_path):
    if schema not in (3, 4):
        raise ValueError("revision schema required")
    salt = secrets.token_hex(32)
    binding = sha256(codec.canonical(["hcl-memory-governance-1", salt, upgrade_id, source_path, target_path]).encode()).hexdigest()
    db.execute(
        """CREATE TABLE revision_control(singleton INTEGER PRIMARY KEY CHECK(singleton=1),
        upgrade_id TEXT NOT NULL, origin_schema INTEGER NOT NULL, checkpoint TEXT NOT NULL,
        source_path TEXT NOT NULL, target_path TEXT NOT NULL, mode TEXT NOT NULL, versions TEXT NOT NULL,
        governance_protocol TEXT NOT NULL, governance_salt TEXT NOT NULL, governance_binding TEXT NOT NULL)"""
    )
    db.execute(
        "INSERT INTO revision_control VALUES(1,?,?,?,?,?,?,?,?,?,?)",
        (
            upgrade_id,
            origin_schema,
            checkpoint,
            source_path,
            target_path,
            ACTIVE,
            codec.canonical(version_bundle(schema=schema)),
            "hcl-memory-governance-1",
            salt,
            binding,
        ),
    )
    from hcl.memory.governance import install as install_governance
    install_governance(db)


def _read(db, governed):
    rows = db.execute("SELECT * FROM revision_control").fetchall()
    expected = {
        "singleton",
        "upgrade_id",
        "origin_schema",
        "checkpoint",
        "source_path",
        "target_path",
        "mode",
        "versions",
    }
    if governed:
        expected |= {"governance_protocol", "governance_salt", "governance_binding"}
    if len(rows) != 1 or set(dict(rows[0])) != expected:
        raise ValueError("revision control missing or corrupt")
    row = dict(rows[0])
    if (
        row["singleton"] != 1
        or row["mode"] not in (ACTIVE, READ_ONLY)
        or row["origin_schema"] not in (0, 1, 2, 3, 4)
    ):
        raise ValueError("invalid revision control")
    if governed and (row["governance_protocol"] != "hcl-memory-governance-1"
                     or type(row["governance_salt"]) is not str or len(row["governance_salt"]) != 64
                     or any(c not in "0123456789abcdef" for c in row["governance_salt"])):
        raise ValueError("invalid governance control")
    if governed and row["governance_binding"] != sha256(codec.canonical([
            row["governance_protocol"], row["governance_salt"], row["upgrade_id"],
            row["source_path"], row["target_path"]]).encode()).hexdigest():
        raise ValueError("governance namespace binding mismatch")
    return row


def read(db):
    return _read(db, True)


def read_legacy(db):
    """Strict predecessor reader, used only by explicit cutover validation."""
    return _read(db, False)


def validate(db, expected, *, maintenance=False):
    row = read(db)
    same = row == expected
    if maintenance:
        same = {key: value for key, value in row.items() if key != "mode"} == {
            key: value for key, value in expected.items() if key != "mode"}
    if not same or (row["mode"] != ACTIVE and not (maintenance and row["mode"] == READ_ONLY)):
        raise failure(
            "DENIED",
            "REVISION_NAMESPACE_FENCED",
            "store",
            "This revision namespace is not active.",
            "migration",
        )


def continue_governance(
    db, *, schema, upgrade_id, origin_schema, checkpoint, source_path, target_path
):
    """Rebind a verified unpublished successor without regenerating ownership.

    No inventory backfill or table installation: erased history cannot be read
    again, and every HMAC owner/tombstone/capsule identity uses the original salt.
    """
    from hcl.memory.governance import verify_inventory

    old = read(db)
    if old["mode"] != ACTIVE or schema not in (3, 4):
        raise ValueError("active governed predecessor required")
    verify_inventory(db)
    binding = sha256(
        codec.canonical(
            [
                old["governance_protocol"],
                old["governance_salt"],
                upgrade_id,
                source_path,
                target_path,
            ]
        ).encode()
    ).hexdigest()
    db.execute(
        """UPDATE revision_control SET upgrade_id=?,origin_schema=?,checkpoint=?,source_path=?,target_path=?,
                  mode=?,versions=?,governance_binding=? WHERE singleton=1""",
        (
            upgrade_id,
            origin_schema,
            checkpoint,
            source_path,
            target_path,
            ACTIVE,
            codec.canonical(version_bundle(schema=schema)),
            binding,
        ),
    )
    current = read(db)
    if current["governance_salt"] != old["governance_salt"]:
        raise ValueError("governance ownership changed")
    verify_inventory(db)
