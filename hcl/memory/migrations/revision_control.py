"""Terminal cutover fences for the query-dependency storage protocol."""

from hcl.kernel.scope import failure
from hcl.memory import codec
from .control import version_bundle

ACTIVE = "ACTIVE"
READ_ONLY = "READ_ONLY"
TERMINAL_SOURCE = 91
UNPUBLISHED = 92


def install(db, *, schema, upgrade_id, origin_schema, checkpoint, source_path, target_path):
    if schema not in (3, 4):
        raise ValueError("revision schema required")
    db.execute(
        """CREATE TABLE revision_control(singleton INTEGER PRIMARY KEY CHECK(singleton=1),
        upgrade_id TEXT NOT NULL, origin_schema INTEGER NOT NULL, checkpoint TEXT NOT NULL,
        source_path TEXT NOT NULL, target_path TEXT NOT NULL, mode TEXT NOT NULL, versions TEXT NOT NULL)"""
    )
    db.execute(
        "INSERT INTO revision_control VALUES(1,?,?,?,?,?,?,?)",
        (
            upgrade_id,
            origin_schema,
            checkpoint,
            source_path,
            target_path,
            ACTIVE,
            codec.canonical(version_bundle(schema=schema)),
        ),
    )


def read(db):
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
    if len(rows) != 1 or set(dict(rows[0])) != expected:
        raise ValueError("revision control missing or corrupt")
    row = dict(rows[0])
    if (
        row["singleton"] != 1
        or row["mode"] not in (ACTIVE, READ_ONLY)
        or row["origin_schema"] not in (0, 1, 2, 3, 4)
    ):
        raise ValueError("invalid revision control")
    return row


def validate(db, expected):
    row = read(db)
    if row != expected or row["mode"] != ACTIVE:
        raise failure(
            "DENIED",
            "REVISION_NAMESPACE_FENCED",
            "store",
            "This revision namespace is not active.",
            "migration",
        )
