"""Source-level retention planning on the same store; no external data service.

Planning is read-only. Physical erasure is a separate, explicitly resumable
operation; a plan or a removed read permission is not an erasure completion.
"""
from hashlib import sha256
import hmac
import json

from hcl.kernel.scope import failure
from hcl.memory import codec
from hcl.memory.lineage import binding, encoded_bindings, retained_bindings, source_token
from hcl.memory.retention_inventory import inventory

PROTOCOL = "hcl-memory-governance-1"
EVENT_KEYS = {"source_tombstones": ("session_id", "source_token"), "erasures": ("erasure_id",),
              "erased_tasks": ("task_key",), "legacy_capsules": ("session_id", "capsule_id"),
              "legacy_roots": ("session_id",)}
TABLES = frozenset({"retention_events", "retention_owners", "retention_refs"}) | frozenset(EVENT_KEYS)


def owner_key(db, owner):
    # Free-form source/result IDs can themselves be private. Namespace-salted
    # opaque keys, not plain hashes of guessable IDs, survive in scoped audit.
    salt = bytes.fromhex(db.execute("SELECT governance_salt FROM revision_control").fetchone()[0])
    return hmac.new(salt, codec.canonical([PROTOCOL, list(owner)]).encode(), sha256).hexdigest()


def install(db):
    """Only explicit namespace creation/cutover installs this mandatory layout."""
    statements = (
        """CREATE TABLE retention_events(seq INTEGER PRIMARY KEY, session_id TEXT NOT NULL,
            owner_key TEXT NOT NULL, annotation TEXT NOT NULL, annotation_hash TEXT NOT NULL)""",
        """CREATE TABLE retention_owners(owner_key TEXT PRIMARY KEY, session_id TEXT NOT NULL,
            owner_kind TEXT NOT NULL, bindings TEXT NOT NULL, quality TEXT NOT NULL, projection_hash TEXT NOT NULL)""",
        """CREATE TABLE retention_refs(seq INTEGER NOT NULL, slot TEXT NOT NULL, session_id TEXT NOT NULL,
            owner_key TEXT NOT NULL, object_hash TEXT NOT NULL, disposable INTEGER NOT NULL,
            state TEXT NOT NULL, PRIMARY KEY(seq,slot))""",
        """CREATE TABLE source_tombstones(session_id TEXT NOT NULL, source_token TEXT NOT NULL,
            erasure_id TEXT NOT NULL, revision INTEGER NOT NULL, PRIMARY KEY(session_id,source_token))""",
        """CREATE TABLE erasures(erasure_id TEXT PRIMARY KEY, session_id TEXT NOT NULL,
            tenant TEXT NOT NULL, owner TEXT NOT NULL, plan_hash TEXT NOT NULL,
            status TEXT NOT NULL, targets TEXT NOT NULL, receipt TEXT NOT NULL)""",
        """CREATE TABLE erased_tasks(task_key TEXT PRIMARY KEY, session_id TEXT NOT NULL,
            tenant TEXT NOT NULL, subject TEXT NOT NULL, usage TEXT NOT NULL)""",
        """CREATE TABLE legacy_capsules(session_id TEXT NOT NULL, capsule_id TEXT NOT NULL,
            kind TEXT NOT NULL, source_id TEXT, versions TEXT NOT NULL, readers TEXT NOT NULL,
            reader_ceiling TEXT NOT NULL,
            bindings TEXT NOT NULL, object_hash TEXT NOT NULL, PRIMARY KEY(session_id,capsule_id))""",
        """CREATE TABLE legacy_roots(session_id TEXT PRIMARY KEY, import_hash TEXT NOT NULL,
            object_hash TEXT NOT NULL)""",
        "CREATE INDEX retention_refs_object ON retention_refs(object_hash)",
        "CREATE INDEX retention_refs_owner ON retention_refs(owner_key)",
    )
    for sql in statements:
        db.execute(sql)


def _annotation(db, event, owner, bindings, quality, slots):
    key = owner_key(db, owner)
    annotation = dict(protocol=PROTOCOL, source_event_identity=event["event_hash"], owner_kind=owner[0], owner_key=key,
                      bindings=sorted(bindings), quality=sorted(quality), slots=slots)
    body = codec.canonical(annotation)
    digest = sha256(codec.canonical([event["event_hash"], body]).encode()).hexdigest()
    db.execute("INSERT INTO retention_events VALUES(?,?,?,?,?)",
               (event["seq"], event["session_id"], key, body, digest))
    existing = read_owner(db, key)
    combined = set(bindings) | (set(map(tuple, json.loads(existing["bindings"]))) if existing else set())
    qualities = set(quality) | (set(json.loads(existing["quality"])) if existing else set())
    row = dict(owner_key=key, session_id=event["session_id"], owner_kind=owner[0],
               bindings=codec.canonical(sorted(combined)), quality=codec.canonical(sorted(qualities)))
    projection_hash = sha256(codec.canonical(row).encode()).hexdigest()
    db.execute("INSERT OR REPLACE INTO retention_owners VALUES(?,?,?,?,?,?)", (*row.values(), projection_hash))
    for slot, row in slots.items():
        db.execute("INSERT INTO retention_refs VALUES(?,?,?,?,?,?,?)",
                   (event["seq"], slot, event["session_id"], key, row["object_hash"], int(row["disposable"]), "LIVE"))


def read_owner(db, key):
    row = db.execute("SELECT * FROM retention_owners WHERE owner_key=?", (key,)).fetchone()
    if row is None:
        return None
    row = dict(row)
    digest = row.pop("projection_hash")
    if sha256(codec.canonical(row).encode()).hexdigest() != digest:
        from hcl.memory.sqlite_store import corrupt
        raise corrupt()
    return row


def backfill(db, salt, read_object, *, object_size=None):
    """Explicit predecessor migration; never silently reconstruct on open."""
    events = [dict(row) for row in db.execute("SELECT * FROM events ORDER BY seq")]
    result = inventory(events, read_object, object_size=object_size)
    refs_by_event = {}
    for row in result["references"]:
        refs_by_event.setdefault(row["seq"], {})[row["slot"]] = row
    for event in events:
        seq, session = event["seq"], event["session_id"]
        owner = result["event_owners"][seq]
        slots = {slot: {"object_hash": ref["object_hash"], "disposable": ref["disposable"]}
                 for slot, ref in refs_by_event.get(seq, {}).items()}
        _annotation(db, event, owner, encoded_bindings(salt, result["event_bindings"][seq]),
                    result["owner_quality"].get(owner, ()), slots)
    return len(events), len(result["references"])


def dependency_bindings(store, db, session, principal, packed):
    """Authenticated scope at write time, including indexed negative evidence."""
    from hcl.kernel.dependencies import unpack_dependencies
    positive, queries = unpack_dependencies(packed)
    result = {binding(session, key, version) for key, version in positive.items()}
    if queries and principal is None:
        raise ValueError("new query-bearing content requires captured principal")
    for dependency in queries:
        query = dependency.query
        from hcl.kernel.concept_registry import ConceptQuery
        if type(query) is ConceptQuery:
            session_row = store._session(db, session, principal)
            _, view = store._query_projection(db, session_row, principal, query)
            result.update(binding(session, key, version) for key, version in view["source_versions"].items())
            continue
        sources = list(db.execute("SELECT source_id,version,readers FROM sources WHERE session_id=?", (session,)))
        allowed = {source["source_id"]: source["version"] for source in sources
                   if principal.subject_id in json.loads(source["readers"])
                   and (query.source_scope is None or source["source_id"] in query.source_scope)}
        if query.history:
            selected = {}
            session_row = store._session(db, session, principal)
            for source in store._source_history(db, session_row, principal):
                if source["source_id"] in allowed and (query.known_at is None or source["recorded_at"] <= query.known_at):
                    selected[source["source_id"]] = max(selected.get(source["source_id"], 0), source["source_version"])
            allowed = selected
        result.update(binding(session, key, version) for key, version in allowed.items())
    return result, bool(queries)



def dependency_origins(db, session, packed):
    """Transitive stored graph provenance can extend beyond a new scan scope."""
    from hcl.kernel.dependencies import unpack_dependencies
    from hcl.memory.sqlite_store import corrupt
    result = set()
    for dependency in unpack_dependencies(packed)[1]:
        for result_id in getattr(dependency.query, "evidence_result_ids", ()):
            origin = read_owner(db, owner_key(db, ("inference", session, result_id)))
            if origin is None:
                raise corrupt()
            result.update(map(tuple, json.loads(origin["bindings"])))
    return result

def capture(store, db, event, kind, row, *, principal=None):
    """Capture actual new-write context before the event transaction publishes."""
    from hcl.kernel.types import Principal, TaskResult
    from hcl.memory.retention_inventory import SLOTS
    session = row["session_id"]
    raw, inherited, quality, slots = set(), set(), {"CAPTURED_WRITE_CONTEXT"}, {}
    if kind in ("tasks", "calls"):
        owner = ("task", session, row["task_key"])
        task = row if kind == "tasks" else db.execute("SELECT * FROM tasks WHERE task_key=?", (row["task_key"],)).fetchone()
        if task is None:
            raise ValueError("retained call has no task owner")
        principal = Principal(task["tenant"], task["subject"])
    elif kind == "inferences":
        owner = ("inference", session, row["result_id"])
    elif kind == "sources":
        owner = ("source", session, row["source_id"], row["version"])
        raw.add(binding(session, row["source_id"], row["version"]))
    elif kind == "legacy_capsules":
        owner = ("capsule", session, row["capsule_id"])
        raw.update(binding(*value) for value in json.loads(row["bindings"]))
        quality.add(row["kind"])
    elif kind == "legacy_roots":
        owner = ("legacy_root", session)
    else:
        owner = ("session", session)
    previous = read_owner(db, owner_key(db, owner))
    if previous:
        inherited.update(map(tuple, json.loads(previous["bindings"])))
        quality.update(json.loads(previous["quality"]))
    for field in ("dependencies", "read_set"):
        if field not in row:
            continue
        captured, queries = dependency_bindings(store, db, session, principal, json.loads(row[field]))
        raw.update(captured)
        inherited.update(dependency_origins(db, session, json.loads(row[field])))
        if queries:
            quality.add("CAPTURED_AUTHORIZED_SCAN_SCOPE")
    for slot in sorted(SLOTS & set(row)):
        if row[slot] is None:
            continue
        value = store._get_object(row[slot])
        origin_refs = set()
        raw.update(retained_bindings(value, session_id=session, origin_refs=origin_refs))
        for origin_session, result_id in origin_refs:
            origin = read_owner(db, owner_key(db, ("inference", origin_session, result_id)))
            if origin is None:
                from hcl.memory.sqlite_store import corrupt
                raise corrupt()
            inherited.update(map(tuple, json.loads(origin["bindings"])))
        slots[slot] = dict(object_hash=row[slot], disposable=False)
        if kind == "sources" and slot == "object_hash" and value.get("retrieval_index_hash"):
            slots["retrieval_index_hash"] = dict(object_hash=value["retrieval_index_hash"], disposable=True)
        if type(value) is TaskResult:
            for claim in value.claim_records:
                for field in claim.used_result_fields:
                    origin = read_owner(db, owner_key(db, ("inference", session, field.result_id)))
                    if origin is None:
                        raise ValueError("retained result origin is missing")
                    inherited.update(map(tuple, json.loads(origin["bindings"])))
    salt = bytes.fromhex(store._revision_control["governance_salt"])
    captured = set(encoded_bindings(salt, raw)) | inherited
    if len(captured) > 16384:
        raise failure("BUDGET_EXHAUSTED", "RETENTION_BINDING_BOUND", "retention",
                      "The retained content binding set exceeds its bound.", "governance")
    from hcl.memory.retention_objects import authorized_bindings
    authorized_bindings(store, db, captured)
    _annotation(db, event, owner, captured, quality, slots)


def verify_inventory(db):
    """Verify annotations and both materialized indexes without loading content."""
    owners, refs = {}, {}
    count, size = db.execute("SELECT count(*),coalesce(sum(length(payload)),0) FROM events").fetchone()
    _, metadata_size = db.execute("SELECT count(*),coalesce(sum(length(annotation)),0) FROM retention_events").fetchone()
    if count > 100000 or size + metadata_size > 128 * 1024 * 1024:
        raise failure("BUDGET_EXHAUSTED", "RETENTION_SCAN_BOUND", "retention",
                      "The retention planning scan exceeds its bound.", "governance")
    events = list(db.execute("SELECT * FROM events ORDER BY seq"))
    annotations = {row["seq"]: dict(row) for row in db.execute("SELECT * FROM retention_events")}
    if {row["seq"] for row in events} != set(annotations):
        raise ValueError("retention event membership mismatch")
    heads = {}
    for event in events:
        expected_hash = sha256(codec.canonical([event["session_id"], event["revision"], event["kind"],
                                  event["payload"], event["previous_hash"]]).encode()).hexdigest()
        if heads.get(event["session_id"], "") != event["previous_hash"] or expected_hash != event["event_hash"]:
            raise ValueError("retention source event chain invalid")
        heads[event["session_id"]] = event["event_hash"]
        row = annotations[event["seq"]]
        annotation = json.loads(row["annotation"])
        digest = sha256(codec.canonical([event["event_hash"], row["annotation"]]).encode()).hexdigest()
        identity = annotation["source_event_identity"]
        if (type(identity) is not str or len(identity) != 64 or any(c not in "0123456789abcdef" for c in identity)):
            raise ValueError("invalid stable event identity")
        if (digest != row["annotation_hash"] or annotation["protocol"] != PROTOCOL
                or row["session_id"] != event["session_id"] or row["owner_key"] != annotation["owner_key"]):
            raise ValueError("retention annotation integrity mismatch")
        key = row["owner_key"]
        previous = owners.setdefault(key, dict(owner_key=key, session_id=event["session_id"],
                            owner_kind=annotation["owner_kind"], bindings=set(), quality=set()))
        previous["bindings"].update(map(tuple, annotation["bindings"]))
        previous["quality"].update(annotation["quality"])
        for slot, value in annotation["slots"].items():
            refs[event["seq"], slot] = dict(seq=event["seq"], slot=slot, session_id=event["session_id"],
                                          owner_key=key, object_hash=value["object_hash"],
                                          disposable=int(value["disposable"]), state="LIVE")
    expected = {key: dict(value, bindings=codec.canonical(sorted(value["bindings"])),
                          quality=codec.canonical(sorted(value["quality"]))) for key, value in owners.items()}
    for row in expected.values():
        row["projection_hash"] = sha256(codec.canonical(row).encode()).hexdigest()
    if expected != {row["owner_key"]: dict(row) for row in db.execute("SELECT * FROM retention_owners")}:
        raise ValueError("retention owner projection mismatch")
    if refs != {(row["seq"], row["slot"]): dict(row) for row in db.execute("SELECT * FROM retention_refs")}:
        raise ValueError("retention reference projection mismatch")
    return expected, refs


def require_governed(store):
    if (store._revision_control or {}).get("governance_protocol") != PROTOCOL:
        raise failure("INVALID_REQUEST", "GOVERNANCE_MIGRATION_REQUIRED", "store",
                      "Source erasure requires an explicitly governed namespace.", "governance")


def plan_source_erasure(store, session_id, principal, source_id, expected_version):
    """Read-only, owner-authorized closure. No content is removed by this API."""
    with store._transaction(maintenance=True) as db:
        return _plan(store, db, session_id, principal, source_id, expected_version)


def _plan(store, db, session_id, principal, source_id, expected_version):
    from hcl.memory.store import denied
    session = store._session(db, session_id, principal, owner=True)
    require_governed(store)
    row = db.execute("SELECT version FROM sources WHERE session_id=? AND source_id=?", (session_id, source_id)).fetchone()
    if row is None:
        legacy = db.execute("SELECT versions FROM legacy_capsules WHERE session_id=? AND source_id=? AND kind='SOURCE'",
                            (session_id, source_id)).fetchone()
        if legacy is None:
            raise denied()
        row = dict(version=max(json.loads(legacy[0])))
    if type(expected_version) is not int or row["version"] != expected_version:
        raise failure("STALE_STATE", "ERASURE_SOURCE_VERSION_CHANGED", "expected_version",
                      "The source version differs from the intended erasure scope.", "governance")
    salt = bytes.fromhex(store._revision_control["governance_salt"])
    token = source_token(salt, session_id, source_id)
    try:
        owners, refs = verify_inventory(db)
        from hcl.memory.retention_objects import pending
        staged = pending(store)
    except (ValueError, TypeError, KeyError):
        from hcl.memory.sqlite_store import corrupt
        raise corrupt() from None
    affected = {key for key, value in owners.items()
                if any(binding[0] == session_id and binding[1] == token for binding in json.loads(value["bindings"]))}
    if any(owners[key]["session_id"] != session_id for key in affected):
        # The current execution contract is session-local. Do not silently drop
        # legacy cross-session copies, or erase another session on one owner's
        # permission. Such an old host-created closure needs an explicit joint
        # maintenance contract before any mutation can proceed.
        raise failure("DEFERRED", "CROSS_SESSION_RETENTION_SCOPE", "retention",
                      "The historical closure requires additional session-scoped maintenance authority.", "governance")
    targets = {value["object_hash"] for value in refs.values() if value["owner_key"] in affected}
    independent = {value["object_hash"] for value in refs.values() if value["owner_key"] not in affected}
    staged_targets = [row for row in staged if any(value[0] == session_id and value[1] == token for value in row["bindings"])]
    staged_names = {row["nonce"] for row in staged_targets}
    targets.update(row["object_hash"] for row in staged_targets)
    independent.update(row["object_hash"] for row in staged if row["nonce"] not in staged_names)
    affected_tasks = {row["task_key"] for row in db.execute("SELECT task_key FROM tasks WHERE session_id=?", (session_id,))
                      if owner_key(db, ("task", session_id, row["task_key"])) in affected}
    calls = [row for row in db.execute("SELECT task_key,attempted FROM calls WHERE session_id=?", (session_id,))
             if row["task_key"] in affected_tasks]
    plan = dict(protocol=PROTOCOL, session_id=session_id, source_token=token, expected_version=expected_version,
                revision=session["revision"], access_epoch=session["epoch"], affected_owners=sorted(affected),
                objects_to_unlink=sorted(targets-independent), shared_objects_retained=len(targets & independent),
                staged_objects=[{key: row[key] for key in ("nonce", "object_hash", "temporary_prefix")}
                                for row in sorted(staged_targets, key=lambda row: row["nonce"])],
                accounting_to_preserve=dict(held_calls=len(calls), unknown_calls=sum(row["attempted"] is None for row in calls),
                                            observed_calls=sum(row["attempted"] or 0 for row in calls)),
                readiness="PLAN_ONLY_NO_ERASURE_PERFORMED")
    plan["plan_hash"] = sha256(codec.canonical(plan).encode()).hexdigest()
    return plan
