"""Owner-authorized, content-free erasure intents and ledger redaction.

An intent commits before any physical cleanup. Missing payloads are legitimate
only after their exact event references have been redacted; ordinary corruption
continues to fail closed. This module never operates on a predecessor directory.
"""
from hashlib import sha256
import hmac
import json
import re

from hcl.kernel.scope import failure
from hcl.kernel.types import HCLFailure, TaskResult
from hcl.memory import codec
from hcl.memory.governance import PROTOCOL, EVENT_KEYS, _plan, owner_key, verify_inventory, require_governed

REDACTED = "retention.redacted"


def semantic_hash(event):
    """Independent of the hash-chain links which necessarily follow redaction."""
    return sha256(codec.canonical([event["seq"], event["session_id"], event["revision"],
                                  event["kind"], event["payload"]]).encode()).hexdigest()


def event_keys(db):
    from hcl.memory.sqlite_store import TABLE_KEYS
    tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    return dict(TABLE_KEYS, **EVENT_KEYS) if "retention_events" in tables else dict(TABLE_KEYS)


def object_references(kind, row):
    from hcl.memory.sqlite_store import OBJECT_FIELDS
    if (kind == REDACTED or row.get("state") == "CONTENT_ERASED"
            or kind == "calls" and row.get("validation_code") == "CONTENT_ERASED") :
        return ()
    return tuple(row[name] for name in OBJECT_FIELDS & set(row) if row[name] is not None)


def _usage(store, db, task):
    """Retain only allowlisted mechanical accounting, never a model string."""
    from hcl.kernel.execution import ExecutionCheckpoint
    from hcl.runtime.budget import TaskBudgetLedger
    usage = {}
    if task["result_hash"]:
        value = store._get_object(task["result_hash"])
        if type(value) is TaskResult:
            numeric = {"provider_calls", "mock_calls", "observed_mock_calls", "held_mock_calls",
                       "mock_usage_unknown", "estimated_request_bytes", "observed_output_bytes",
                       "output_usage_unknown", "replay_new_mock_calls", "local_evaluations",
                       "observed_local_evaluations", "held_local_evaluations", "execution_steps", "repair_calls"}
            usage.update((key, number) for key, number in value.usage.items()
                         if key in numeric and (number is None or type(number) is bool
                                                or type(number) is int and number >= 0))
            if value.usage.get("tokenizer") == "UTF8_BYTES_CONSERVATIVE_UPPER_BOUND":
                usage["tokenizer"] = "UTF8_BYTES_CONSERVATIVE_UPPER_BOUND"
        elif type(value) is ExecutionCheckpoint:
            counters = value.counters
            usage.update(local_evaluations=None if counters["local_unknown"] else counters["local_observed"],
                         observed_local_evaluations=counters["local_observed"],
                         held_local_evaluations=counters["local_reserved"], execution_steps=counters["steps"],
                         repair_calls=counters["feedback"])
    calls = list(db.execute("SELECT output_bytes FROM calls WHERE task_key=?", (task["task_key"],)))
    usage.update(TaskBudgetLedger(store)._usage(db, task["task_key"]),
                 observed_output_bytes=sum(row[0] or 0 for row in calls),
                 output_usage_unknown=any(row[0] is None for row in calls))
    usage.setdefault("provider_calls", 0)
    usage.setdefault("provider_spend_usd", "0")
    return usage


def erased_task(store, db, row):
    """Called only after the caller's task identity has been authenticated."""
    if row["state"] != "CONTENT_ERASED":
        return
    account = db.execute("SELECT * FROM erased_tasks WHERE task_key=?", (row["task_key"],)).fetchone()
    if account is None or any(account[key] != row[key] for key in ("session_id", "tenant", "subject")):
        from hcl.memory.sqlite_store import corrupt
        raise corrupt()
    raise HCLFailure("DENIED", "governance", "CONTENT_ERASED", "task",
                     "The task contains erased material and cannot be replayed or resumed.",
                     resource_usage=json.loads(account["usage"]))


def _opaque(salt, value):
    return "erased:" + hmac.new(salt, codec.canonical(value).encode(), sha256).hexdigest()


def _sanitize(kind, row, salt):
    row = dict(row)
    if kind == "tasks":
        row.update(request_id=_opaque(salt, ["request", row["task_key"]]), request_hash="",
                   result_hash=None, dependencies="{}", state="CONTENT_ERASED")
    elif kind == "calls":
        row.update(call_id=_opaque(salt, ["call", row["task_key"], row["call_id"]]),
                   request_hash="", response_hash=None, validation_code="CONTENT_ERASED")
        # Transport state and the UNKNOWN hold remain exact. The empty request
        # hash, rather than a fake replacement payload, marks unavailable bytes.
    return row


def _rebuild_annotations(db, annotations):
    """Rebind validated annotations to the authorized replacement event chain."""
    db.execute("DELETE FROM retention_events")
    db.execute("DELETE FROM retention_owners")
    db.execute("DELETE FROM retention_refs")
    owners = {}
    for event in db.execute("SELECT * FROM events ORDER BY seq"):
        annotation = annotations[event["seq"]]
        body = codec.canonical(annotation)
        digest = sha256(codec.canonical([event["event_hash"], body]).encode()).hexdigest()
        key = annotation["owner_key"]
        db.execute("INSERT INTO retention_events VALUES(?,?,?,?,?)",
                   (event["seq"], event["session_id"], key, body, digest))
        owner = owners.setdefault(key, dict(owner_key=key, session_id=event["session_id"],
                                 owner_kind=annotation["owner_kind"], bindings=set(), quality=set()))
        owner["bindings"].update(map(tuple, annotation["bindings"]))
        owner["quality"].update(annotation["quality"])
        for slot, ref in annotation["slots"].items():
            db.execute("INSERT INTO retention_refs VALUES(?,?,?,?,?,?,?)",
                       (event["seq"], slot, event["session_id"], key, ref["object_hash"], int(ref["disposable"]), "LIVE"))
    for row in owners.values():
        row.update(bindings=codec.canonical(sorted(row["bindings"])), quality=codec.canonical(sorted(row["quality"])))
        digest = sha256(codec.canonical(row).encode()).hexdigest()
        db.execute("INSERT INTO retention_owners VALUES(?,?,?,?,?,?)", (*row.values(), digest))


def _redact(store, db, affected, erasure_id):
    salt = bytes.fromhex(store._revision_control["governance_salt"])
    annotations = {row["seq"]: json.loads(row["annotation"]) for row in db.execute("SELECT * FROM retention_events")}
    changes, heads = [], {}
    for original in list(db.execute("SELECT * FROM events ORDER BY seq")):
        event = dict(original)
        annotation = annotations[event["seq"]]
        if annotation["owner_key"] in affected:
            before = semantic_hash(event)
            kind, row = event["kind"], json.loads(event["payload"])
            if kind in ("tasks", "calls"):
                event["payload"] = codec.canonical(_sanitize(kind, row, salt))
            elif kind in ("sources", "inferences", "legacy_capsules"):
                event.update(kind=REDACTED, payload=codec.canonical(dict(session_id=event["session_id"],
                              owner_key=annotation["owner_key"], erasure_id=erasure_id)))
            else:
                raise ValueError("unrecognized source-bearing retention owner")
            annotation.update(bindings=[], slots={}, quality=["SOURCE_ERASED"])
            changes.append(dict(seq=event["seq"], before=before, after=semantic_hash(event)))
        previous = heads.get(event["session_id"], "")
        digest = sha256(codec.canonical([event["session_id"], event["revision"], event["kind"],
                                        event["payload"], previous]).encode()).hexdigest()
        heads[event["session_id"]] = digest
        db.execute("UPDATE events SET kind=?,payload=?,previous_hash=?,event_hash=? WHERE seq=?",
                   (event["kind"], event["payload"], previous, digest, event["seq"]))
    _rebuild_annotations(db, annotations)
    # All historical versions of an affected owner disappear, not merely the
    # last materialized row. Rebuild can therefore never resurrect them.
    for table in ("sources", "inferences", "tasks", "calls", "legacy_capsules"):
        db.execute(f"DELETE FROM {table}")
        for event in db.execute("SELECT payload FROM events WHERE kind=? ORDER BY seq", (table,)):
            store._upsert(db, table, json.loads(event[0]))
    return changes


def begin_source_erasure(store, session_id, principal, source_id, expected_version, plan_hash, erasure_id):
    """Commit the logical fence atomically; this is not physical completion."""
    if type(erasure_id) is not str or not re.fullmatch("[0-9a-f]{32}", erasure_id):
        raise ValueError("opaque 128-bit hexadecimal erasure identity required")
    with store._transaction(True, maintenance=True) as db:
        session = store._session(db, session_id, principal, owner=True)
        require_governed(store)
        old = db.execute("SELECT * FROM erasures WHERE erasure_id=?", (erasure_id,)).fetchone()
        if old is not None:
            if (old["session_id"], old["tenant"], old["owner"], old["plan_hash"]) != (
                    session_id, principal.tenant_id, principal.subject_id, plan_hash):
                raise failure("DENIED", "ERASURE_IDENTITY_MISMATCH", "erasure_id",
                              "The erasure identity is already bound to another scope.", "governance")
            from hcl.memory.lineage import source_token
            bound = json.loads(old["targets"])["plan"]
            token = source_token(bytes.fromhex(store._revision_control["governance_salt"]), session_id, source_id)
            if bound["source_token"] != token or bound["expected_version"] != expected_version:
                raise failure("DENIED", "ERASURE_IDENTITY_MISMATCH", "source_id",
                              "The erasure identity belongs to a different source scope.", "governance")
            verify_inventory(db)
            return json.loads(old["receipt"])
        plan = _plan(store, db, session_id, principal, source_id, expected_version)
        if plan_hash != plan["plan_hash"]:
            raise failure("STALE_STATE", "ERASURE_PLAN_CHANGED", "plan_hash",
                          "The retained reference closure changed after planning.", "governance")
        affected = set(plan["affected_owners"])
        accounting = []
        for task in db.execute("SELECT * FROM tasks WHERE session_id=?", (session_id,)):
            if owner_key(db, ("task", session_id, task["task_key"])) in affected:
                accounting.append(dict(task_key=task["task_key"], session_id=session_id, tenant=task["tenant"],
                                       subject=task["subject"], usage=codec.canonical(_usage(store, db, task))))
        changes = _redact(store, db, affected, erasure_id)
        session["revision"] += 1
        store._record(db, "source_tombstones", dict(session_id=session_id, source_token=plan["source_token"],
                      erasure_id=erasure_id, revision=session["revision"]), session["revision"])
        for account in accounting:
            store._record(db, "erased_tasks", account, session["revision"])
        targets = dict(plan=plan, event_changes=changes)
        tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        limitations = []
        if "namespace_control" in tables:
            if not db.execute("SELECT 1 FROM legacy_roots WHERE session_id=?", (session_id,)).fetchone():
                limitations.append("LEGACY_CAPSULE_REQUIRES_SCOPED_REDACTION")
            elif db.execute("SELECT 1 FROM legacy_capsules WHERE session_id=? AND kind='UNKNOWN_PROVENANCE' LIMIT 1",
                            (session_id,)).fetchone():
                limitations.append("UNKNOWN_LEGACY_PROVENANCE_RETAINED")
        if store._revision_control["source_path"] != str(store.path):
            limitations.append("PREDECESSOR_COPY_RETAINED")
        receipt = dict(protocol=PROTOCOL, erasure_id=erasure_id, status="LOGICALLY_ERASED_PHYSICAL_PENDING",
                       source_token=plan["source_token"], erased_owners=len(affected),
                       shared_objects_retained=plan["shared_objects_retained"],
                       accounting_preserved=plan["accounting_to_preserve"], limitations=limitations,
                       physical_scope="CURRENT_MANAGED_NAMESPACE_ONLY")
        store._record(db, "erasures", dict(erasure_id=erasure_id, session_id=session_id,
                      tenant=principal.tenant_id, owner=principal.subject_id, plan_hash=plan_hash,
                      status=receipt["status"], targets=codec.canonical(targets), receipt=codec.canonical(receipt)),
                      session["revision"])
        store._record(db, "sessions", session, session["revision"])
        verify_inventory(db)
        store._checkpoint("erasure_logical_fence_persisted")
    store._checkpoint("erasure_logical_fence_committed")
    return receipt


def authorized_prefix(db, original_events, current_events):
    """A cutover replay accepts only explicitly recorded content redactions."""
    changes = {}
    for row in db.execute("SELECT targets FROM erasures ORDER BY json_extract(targets,'$.plan.revision'),erasure_id"):
        for change in json.loads(row[0])["event_changes"]:
            changes.setdefault(change["seq"], []).append(change)
    if len(current_events) < len(original_events):
        return False
    for original, current in zip(original_events, current_events):
        digest = semantic_hash(original)
        target = semantic_hash(current)
        started = False
        for change in changes.get(original["seq"], ()):
            if not started:
                if digest != change["before"]:
                    continue  # Before this source checkpoint, not a new permission.
                started = True
            if digest != change["before"]:
                return False  # Once begun, every later change must be contiguous.
            digest = change["after"]
        if digest != target:
            return False
    return True
