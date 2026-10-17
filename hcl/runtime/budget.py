"""One persistent task budget shared by all offline branches and connections."""
from dataclasses import dataclass, replace
from hashlib import sha256
import json

from hcl.kernel.scope import failure, identifier
from hcl.kernel.types import HCLFailure, TaskResult
from hcl.memory import codec


@dataclass(frozen=True)
class TaskLease:
    task_key: str
    session_id: str
    principal: object
    request_id: str
    owner_id: str


def task_key(principal, session_id, request_id):
    return sha256(codec.canonical([principal.tenant_id, principal.subject_id, session_id, request_id]).encode()).hexdigest()


class TaskBudgetLedger:
    def __init__(self, store):
        if not store.durable:
            raise ValueError("persistent task ledger requires durable state")
        self.store = store

    def _lease(self, db, lease, *, active=True):
        session = self.store._session(db, lease.session_id, lease.principal)
        row = db.execute("SELECT * FROM tasks WHERE task_key=?", (lease.task_key,)).fetchone()
        if (row is None or row["session_id"] != lease.session_id or row["tenant"] != lease.principal.tenant_id
                or row["subject"] != lease.principal.subject_id
                or task_key(lease.principal, lease.session_id, lease.request_id) != lease.task_key
                or row["owner_id"] != lease.owner_id):
            raise failure("DENIED", "TASK_LEASE_DENIED", "task", "The task lease is not authorized.", "access")
        from hcl.memory.erasure import erased_task
        erased_task(self.store, db, row)
        if row["request_id"] != lease.request_id:
            raise failure("DENIED", "TASK_LEASE_DENIED", "task", "The task lease is not authorized.", "access")
        if active and row["state"] != "ACTIVE":
            raise failure("FAILED", "TASK_NOT_ACTIVE", "task", "This task cannot dispatch additional work.", "admission")
        return session, dict(row)

    def _usage(self, db, key):
        calls = list(db.execute("SELECT * FROM calls WHERE task_key=?", (key,)))
        from .candidate_ledger import split_calls, metered_usage
        all_calls = calls
        from .deepseek_ledger import split_deepseek_calls, native_usage
        calls, native = split_deepseek_calls(self.store, calls)
        calls, metered = split_calls(self.store, calls)
        unknown = any(call["attempted"] is None for call in calls)
        known = sum(call["attempted"] or 0 for call in calls)
        usage = {
            "mock_calls": None if unknown else known,
            "observed_mock_calls": known,
            "held_mock_calls": len(calls),
            "mock_usage_unknown": unknown,
            "estimated_request_bytes": sum(call["request_bytes"] for call in all_calls),
            "replay_new_mock_calls": 0,
        }
        if len(calls) == 1:
            usage["mock_call_state"] = calls[0]["state"]
        usage.update(metered_usage(metered))
        usage.update(native_usage(native))
        return usage

    def _replay_dependencies(self, db, request, session, row):
        from hcl.memory.erasure import erased_task
        erased_task(self.store, db, row)
        try:
            self.store._validate_dependencies(
                db, session, request.principal, json.loads(row["dependencies"]), row["epoch"], row["rule"]
            )
        except HCLFailure as error:
            raise HCLFailure(
                error.status,
                error.diagnostic.stage,
                error.diagnostic.code,
                error.diagnostic.field_path,
                error.diagnostic.message,
                resource_usage=self._usage(db, row["task_key"]),
            ) from None

    def _existing(self, db, request, session, row, fingerprint):
        if row["fingerprint"] != fingerprint:
            raise failure("INVALID_REQUEST", "REQUEST_FINGERPRINT_MISMATCH", "request_id", "The request identity is already bound to different input or limits.", "admission")
        self._replay_dependencies(db,request,session,row)
        if row["state"] in ("COMPLETED", "FAILED") and row["result_hash"]:
            result = self.store._get_object(row["result_hash"])
            if type(result) is not TaskResult:
                raise failure("FAILED", "STATE_CORRUPT", "task", "The stored task result is invalid.", "storage")
            return replace(result, execution_receipt=dict(result.execution_receipt, replayed=True),
                           usage=dict(result.usage, replay_new_mock_calls=0))
        code = "TASK_IN_PROGRESS" if row["state"] == "ACTIVE" else "TASK_INTERRUPTED_NO_RESEND"
        usage=self._usage(db,row['task_key'])
        raise HCLFailure("FAILED", "admission", code, "request_id", "The prior task cannot silently execute again.",
                         resource_usage=usage)

    def resume(self, request):
        """Only committed actual dependencies matter; never repeat computation."""
        key = task_key(request.principal, request.session_id, request.request_id)
        fingerprint = sha256(codec.dumps(request)).hexdigest()
        with self.store._transaction() as db:
            session = self.store._session(db, request.session_id, request.principal)
            row = db.execute("SELECT * FROM tasks WHERE task_key=?", (key,)).fetchone()
            return self._existing(db, request, session, row, fingerprint) if row else None

    def validate_cached_delivery(self, request):
        """Fresh transaction after loading the result leaves its old WAL snapshot."""
        key = task_key(request.principal, request.session_id, request.request_id)
        fingerprint = sha256(codec.dumps(request)).hexdigest()
        with self.store._transaction() as db:
            session = self.store._session(db, request.session_id, request.principal)
            row = db.execute("SELECT * FROM tasks WHERE task_key=?", (key,)).fetchone()
            if row is not None and row["fingerprint"] == fingerprint:
                from hcl.memory.erasure import erased_task
                erased_task(self.store, db, row)
            if row is None or row["fingerprint"] != fingerprint or row["state"] not in ("COMPLETED", "FAILED"):
                raise failure("DENIED", "CACHED_DELIVERY_CHANGED", "task", "The cached delivery binding is no longer current.", "access")
            self._replay_dependencies(db,request,session,row)

    def bind(self, request, snapshot):
        key = task_key(request.principal, request.session_id, request.request_id)
        fingerprint = sha256(codec.dumps(request)).hexdigest()
        with self.store._transaction(True) as db:
            session = self.store._validate_snapshot(db, snapshot)
            row = db.execute("SELECT * FROM tasks WHERE task_key=?", (key,)).fetchone()
            if row:
                return None, self._existing(db, request, session, row, fingerprint)
            lease = TaskLease(key, request.session_id, request.principal, request.request_id, self.store.owner_id)
            record = dict(task_key=key, session_id=request.session_id, tenant=request.principal.tenant_id,
                subject=request.principal.subject_id, request_id=request.request_id, fingerprint=fingerprint,
                request_hash=self.store._put_content(request, session_id=request.session_id, context=snapshot), budget=codec.dumps(request.budget).decode(),
                state="ACTIVE", owner_id=lease.owner_id, result_hash=None,
                dependencies=codec.canonical(self.store.snapshot_dependencies(snapshot)), epoch=snapshot.access_epoch, rule=snapshot.rule_version)
            self.store._record(db, "tasks", record, session["revision"])
            return lease, None

    def finish(self, lease, snapshot, read_set, result):
        with self.store._transaction(True) as db:
            session, row = self._lease(db, lease)
            if result.status in ("COMPLETED", "PARTIAL"):
                self.store._validate_snapshot(db, snapshot, read_set)
            row.update(state="COMPLETED" if result.status in ("COMPLETED", "PARTIAL") else "FAILED",
                       result_hash=self.store._put_content(result, session_id=lease.session_id, context=snapshot,
                            owner=("task", lease.session_id, lease.task_key)), dependencies=codec.canonical(self.store.snapshot_dependencies(snapshot, read_set)))
            self.store._record(db, "tasks", row, session["revision"])

    def reserve(self, lease, snapshot, question, allowance, call_id, serialized):
        identifier(call_id)
        request_bytes = len(serialized.encode("utf-8"))
        with self.store._transaction(True) as db:
            session, task = self._lease(db, lease)
            self.store._validate_snapshot(db, snapshot)
            request = self.store._get_object(task["request_hash"])
            from hcl.kernel.execution import ExecutionIssue
            if type(request.issue) is ExecutionIssue:
                if snapshot.session_id != lease.session_id or snapshot.principal != lease.principal or question != request.question:
                    raise failure("DENIED", "TASK_CONTEXT_MISMATCH", "call_spec", "Call identity differs from the bound task.", "access")
                from hcl.runtime.execution_ledger import validate_execution_reservation
                validate_execution_reservation(self, db, task, request, snapshot, call_id, serialized, allowance)
            elif (snapshot.session_id != lease.session_id or snapshot.principal != lease.principal
                    or question != request.question or allowance != request.budget
                    or self.store.snapshot_dependencies(snapshot) != json.loads(task["dependencies"])):
                raise failure("DENIED", "TASK_CONTEXT_MISMATCH", "call_spec", "Call context or allowance differs from the bound task.", "access")
            if db.execute("SELECT 1 FROM calls WHERE task_key=? AND call_id=?", (lease.task_key, call_id)).fetchone():
                raise failure("FAILED", "CALL_ALREADY_RESERVED", "call_id", "This call cannot be reserved or sent again.", "model")
            used = db.execute("SELECT count(*) FROM calls WHERE task_key=?", (lease.task_key,)).fetchone()[0]
            if used >= request.budget.max_mock_calls:
                raise failure("BUDGET_EXHAUSTED", "MOCK_CALL_BUDGET", "budget.max_mock_calls", "The shared task call budget is exhausted.", "model")
            if request_bytes > request.budget.max_request_bytes:
                raise failure("BUDGET_EXHAUSTED", "REQUEST_BYTES_EXCEEDED", "budget.max_request_bytes", "The complete request exceeds its byte limit.", "model")
            row = dict(task_key=lease.task_key, call_id=call_id, session_id=lease.session_id, state="RESERVED",
                owner_id=lease.owner_id, request_hash=self.store._put_content(serialized, session_id=lease.session_id, context=snapshot,
                    owner=("task", lease.session_id, lease.task_key)), response_hash=None,
                request_bytes=request_bytes, output_bytes=None, attempted=0, validation_code=None)
            self.store._record(db, "calls", row, session["revision"])
            return row

    def transition(self, lease, call_id, expected, state, *, snapshot=None, response=None, validation_code=None):
        allowed = {
            "RESERVED": {"SEND_STARTED", "FAILED_BEFORE_SEND"},
            "SEND_STARTED": {"RETURNED", "FAILED_BEFORE_SEND", "UNKNOWN"},
            "RETURNED": {"RETURNED", "VALIDATION_REJECTED"},
        }
        with self.store._transaction(True) as db:
            session, _ = self._lease(db, lease)
            original = db.execute("SELECT * FROM calls WHERE task_key=? AND call_id=?", (lease.task_key, call_id)).fetchone()
            if original is None or original["state"] != expected or state not in allowed.get(expected, set()):
                raise failure("FAILED", "CALL_STATE_CONFLICT", "call_id", "The call state cannot transition or repeat.", "model")
            if snapshot is not None:
                self.store._validate_snapshot(db, snapshot)
            row = dict(original)
            row.update(state=state, validation_code=validation_code)
            if state == "SEND_STARTED" or state == "UNKNOWN":
                row["attempted"] = None  # Possible send is never counted as known zero.
            elif state == "FAILED_BEFORE_SEND":
                row["attempted"] = 0
            elif state == "RETURNED" and expected == "SEND_STARTED":
                row["response_hash"] = self.store._put_content(response, session_id=lease.session_id,
                    owner=("task", lease.session_id, lease.task_key))
                row["attempted"] = 1
                if type(response) is str:
                    try:
                        row["output_bytes"] = len(response.encode("utf-8"))
                    except UnicodeEncodeError:
                        row["output_bytes"] = None
            self.store._record(db, "calls", row, session["revision"])
            return row

    def call(self, lease, call_id):
        with self.store._transaction() as db:
            self._lease(db, lease, active=False)
            row = db.execute("SELECT * FROM calls WHERE task_key=? AND call_id=?", (lease.task_key, call_id)).fetchone()
            return dict(row) if row else None

    def state(self, principal, session_id, request_id, call_id="response"):
        with self.store._transaction() as db:
            self.store._session(db, session_id, principal)
            key = task_key(principal, session_id, request_id)
            row = db.execute("SELECT state FROM calls WHERE task_key=? AND call_id=?", (key, call_id)).fetchone()
            return row[0] if row else None

    def pending(self, principal, session_id):
        with self.store._transaction() as db:
            self.store._session(db, session_id, principal)
            return tuple(dict(row) for row in db.execute(
                "SELECT request_id,owner_id,state FROM tasks WHERE session_id=? AND tenant=? AND subject=? AND state='ACTIVE'",
                (session_id, principal.tenant_id, principal.subject_id)))

    def recover_abandoned(self, principal, session_id, request_id, expected_owner_id):
        """Host explicitly confirms abandonment; opening a connection never recovers."""
        with self.store._transaction(True) as db:
            session = self.store._session(db, session_id, principal)
            key = task_key(principal, session_id, request_id)
            original = db.execute("SELECT * FROM tasks WHERE task_key=?", (key,)).fetchone()
            if original is None or original["owner_id"] != expected_owner_id:
                raise failure("DENIED", "TASK_RECOVERY_DENIED", "task", "The recovery identity is not authorized.", "access")
            if original["state"] != "ACTIVE":
                return 0
            changed = 0
            for call in list(db.execute("SELECT * FROM calls WHERE task_key=?", (key,))):
                row = dict(call)
                if row["state"] not in ("RESERVED", "SEND_STARTED"):
                    continue
                row["state"] = "FAILED_BEFORE_SEND" if row["state"] == "RESERVED" else "UNKNOWN"
                row["attempted"] = 0 if row["state"] == "FAILED_BEFORE_SEND" else None
                row["validation_code"] = "OWNER_ABANDONED_NO_RESEND"
                self.store._record(db, "calls", row, session["revision"])
                changed += 1
            task = dict(original)
            task["state"] = "INTERRUPTED"
            self.store._record(db, "tasks", task, session["revision"])
            return changed


def call_usage(row):
    """Estimated/reserved/observed/unknown are distinct, including offline faults."""
    return {"mock_calls": row["attempted"], "held_mock_calls": 1,
            "estimated_request_bytes": row["request_bytes"], "observed_output_bytes": row["output_bytes"],
            "mock_usage_unknown": row["attempted"] is None, "provider_calls": 0, "provider_spend_usd": "0"}
