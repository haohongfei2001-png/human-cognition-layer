"""Namespace version/fence contract, with no user-content or model authority."""
from hashlib import sha256
from pathlib import Path
import json

from hcl.kernel.scope import failure
from hcl.kernel.types import RULE_VERSION
from hcl.memory import codec

NAMESPACE_SCHEMA = 2
ACTIVE = "ACTIVE_NEW"
READ_ONLY = "LEGACY_READ_ONLY"


def version_bundle(*, schema=NAMESPACE_SCHEMA):
    root = Path(__file__).resolve().parents[2]
    # Explicit runtime source only, never evaluation data, private packages or git history.
    files = {str(path.relative_to(root)): sha256(path.read_bytes()).hexdigest()
             for path in sorted(root.rglob("*.py"))}
    bundle = {"code_sha256": sha256(codec.canonical(files).encode()).hexdigest(),
            "schema": schema, "rules": RULE_VERSION, "indexes": ({"revision":1, "retrieval":"hcl-evidence-retrieval-1"} if schema in (3, 4) else {})}
    if schema in (3, 4):
        bundle["governance"] = "hcl-memory-governance-1"
    return bundle


def blocked():
    return failure("DENIED", "NAMESPACE_READ_ONLY", "namespace", "This namespace is not active for execution.", "migration")


def read_control(db):
    rows = db.execute("SELECT * FROM namespace_control").fetchall()
    if len(rows) != 1:
        raise failure("FAILED", "NAMESPACE_CONTROL_CORRUPT", "namespace", "Namespace control failed validation.", "migration")
    row = dict(rows[0])
    expected = {"singleton", "namespace_id", "tenant", "owner", "session_id", "package_hash",
                "mode", "active_target", "generation", "versions"}
    if (set(row) != expected or row["singleton"] != 1 or row["mode"] not in (ACTIVE, READ_ONLY)
            or type(row["generation"]) is not int or row["generation"] < 1
            or row["active_target"] != ("unified" if row["mode"] == ACTIVE else "legacy_snapshot")):
        raise failure("FAILED", "NAMESPACE_CONTROL_CORRUPT", "namespace", "Namespace control failed validation.", "migration")
    return row


def validate_execution(db, generation, bundle):
    row = read_control(db)
    if row["mode"] != ACTIVE or row["generation"] != generation:
        raise blocked()
    try:
        versions = json.loads(row["versions"])
    except (ValueError, TypeError):
        versions = None
    if versions != bundle:
        raise failure("DENIED", "NAMESPACE_VERSION_CHANGED", "namespace", "The controlled version bundle differs.", "migration")
