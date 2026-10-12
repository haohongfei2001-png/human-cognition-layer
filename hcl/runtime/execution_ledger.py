"""Durable execution checkpoints on the existing hash-checked task/event log.

Task identity and old wire bytes do not change. Only explicit host abandonment
can transfer an interrupted graph, and an unknown send forbids graph resumption.
"""

from dataclasses import replace
from hashlib import sha256
import json

from hcl.kernel.execution import ExecutionCheckpoint, ExecutionIssue, PROTOCOL, ResumeToken
from hcl.kernel.types import HCLFailure, TaskResult
from hcl.kernel.dependencies import pack_dependencies, unpack_dependencies
from hcl.memory import codec
from .budget import TaskBudgetLedger, TaskLease, task_key


def stopped(code, status="FAILED", stage="recovery"):
    return HCLFailure(
        status, stage, code, "execution", "The execution cannot continue under its current bound state."
    )


class ExecutionLedger:
    def __init__(self, store):
        self.store, self.tasks = store, TaskBudgetLedger(store)

    def _checkpoint(self, task):
        if not task["result_hash"]:
            return None
        value = self.store._get_object(task["result_hash"])
        if type(value) is not ExecutionCheckpoint or value.owner_id != task["owner_id"]:
            raise stopped("EXECUTION_CHECKPOINT_CORRUPT")
        return value

    def open(self, request, snapshot, initial):
        key = task_key(request.principal, request.session_id, request.request_id)
        fingerprint = sha256(codec.dumps(request)).hexdigest()
        with self.store._transaction(True) as db:
            session = self.store._session(db, request.session_id, request.principal)
            row = db.execute("SELECT * FROM tasks WHERE task_key=?", (key,)).fetchone()
            if row:
                if row["fingerprint"] != fingerprint:
                    raise stopped("REQUEST_FINGERPRINT_MISMATCH", "INVALID_REQUEST", "admission")
                self.tasks._replay_dependencies(db, request, session, row)
                if row["state"] in ("COMPLETED", "FAILED"):
                    return None, None, self.tasks._existing(db, request, session, row, fingerprint)
                checkpoint = self._checkpoint(row)
                if (
                    row["state"] != "ACTIVE"
                    or row["owner_id"] != self.store.owner_id
                    or checkpoint is None
                    or checkpoint.mode != "RESUMABLE"
                ):
                    raise HCLFailure(
                        "FAILED",
                        "admission",
                        "TASK_IN_PROGRESS",
                        "request_id",
                        "The existing graph requires an explicit authenticated recovery handoff.",
                        resource_usage=self.tasks._usage(db, key),
                    )
                checkpoint = replace(checkpoint, mode="RUNNING")
                task = dict(row)
                task["result_hash"] = self.store._put_object(checkpoint)
                self.store._record(db, "tasks", task, session["revision"])
                return (
                    TaskLease(
                        key, request.session_id, request.principal, request.request_id, self.store.owner_id
                    ),
                    checkpoint,
                    None,
                )
        lease, replay = self.tasks.bind(request, snapshot)
        if replay is not None:
            return None, None, replay
        self.save(lease, initial)
        return lease, initial, None

    def save(self, lease, checkpoint):
        with self.store._transaction(True) as db:
            session, task = self.tasks._lease(db, lease)
            if type(checkpoint) is not ExecutionCheckpoint or checkpoint.owner_id != lease.owner_id:
                raise stopped("EXECUTION_CHECKPOINT_OWNER")
            if len(codec.dumps(checkpoint)) > 4 * 1024 * 1024:
                raise stopped("AUDIT_CHECKPOINT_CAPACITY", "BUDGET_EXHAUSTED", "storage")
            task["result_hash"] = self.store._put_object(checkpoint)
            self.store._record(db, "tasks", task, session["revision"])
        self.store._checkpoint("execution_checkpoint_saved")

    def usage(self, lease):
        with self.store._transaction() as db:
            self.tasks._lease(db, lease, active=False)
            usage = self.tasks._usage(db, lease.task_key)
            calls = list(db.execute("SELECT output_bytes FROM calls WHERE task_key=?", (lease.task_key,)))
            usage["observed_output_bytes"] = sum(call[0] or 0 for call in calls)
            usage["output_usage_unknown"] = any(call[0] is None for call in calls)
            return usage

    def recover(self, request, expected_owner_id):
        """Host operation, never called by run(), a timer or source/model text."""
        key = task_key(request.principal, request.session_id, request.request_id)
        fingerprint = sha256(codec.dumps(request)).hexdigest()
        with self.store._transaction(True) as db:
            session = self.store._session(db, request.session_id, request.principal)
            row = db.execute("SELECT * FROM tasks WHERE task_key=?", (key,)).fetchone()
            if (
                type(request.issue) is not ExecutionIssue
                or row is None
                or row["fingerprint"] != fingerprint
                or row["owner_id"] != expected_owner_id
                or row["state"] != "ACTIVE"
            ):
                raise stopped("EXECUTION_RECOVERY_DENIED", "DENIED")
            self.tasks._replay_dependencies(db, request, session, row)
            checkpoint = self._checkpoint(row)
            if checkpoint is None:
                raise stopped("EXECUTION_CHECKPOINT_MISSING")
            unknown = False
            for original in list(db.execute("SELECT * FROM calls WHERE task_key=?", (key,))):
                call = dict(original)
                if call["state"] in ("SEND_STARTED", "UNKNOWN") or call["attempted"] is None:
                    unknown = True
                if call["state"] in ("RESERVED", "SEND_STARTED"):
                    call.update(
                        state="FAILED_BEFORE_SEND" if call["state"] == "RESERVED" else "UNKNOWN",
                        attempted=0 if call["state"] == "RESERVED" else None,
                        validation_code="OWNER_ABANDONED_NO_RESEND",
                    )
                    self.store._record(db, "calls", call, session["revision"])
            task = dict(row)
            if unknown:
                task["state"] = "INTERRUPTED"
                self.store._record(db, "tasks", task, session["revision"])
                # Commit the UNKNOWN transition, then report the block below.
                token = None
            else:
                task["owner_id"] = self.store.owner_id
                checkpoint = replace(checkpoint, owner_id=self.store.owner_id, mode="RESUMABLE")
                task["result_hash"] = self.store._put_object(checkpoint)
                self.store._record(db, "tasks", task, session["revision"])
                token = ResumeToken(key, fingerprint, self.store.owner_id)
        if token is None:
            raise stopped("UNKNOWN_SEND_NO_RESUME", "SEND_UNKNOWN")
        return token

    def audit(self, request):
        """Complete owner audit, gated on current access to every session source.

        This deliberately stricter export includes failed branches and original
        model returns, unlike final delivery's minimal actual dependencies.
        """
        key = task_key(request.principal, request.session_id, request.request_id)
        fingerprint = sha256(codec.dumps(request)).hexdigest()

        def authorize(db):
            self.store._session(db, request.session_id, request.principal, owner=True)
            row = db.execute("SELECT * FROM tasks WHERE task_key=?", (key,)).fetchone()
            if row is None or row["fingerprint"] != fingerprint:
                raise stopped("EXECUTION_AUDIT_DENIED", "DENIED", "access")
            for source in db.execute(
                "SELECT source_id FROM sources WHERE session_id=?", (request.session_id,)
            ):
                self.store._source(
                    db,
                    self.store._session(db, request.session_id, request.principal),
                    request.principal,
                    source[0],
                )
            return row

        with self.store._transaction() as db:
            authorize(db)
            checkpoints = []
            for event in db.execute(
                "SELECT payload FROM events WHERE session_id=? AND kind='tasks' ORDER BY seq",
                (request.session_id,),
            ):
                row = json.loads(event[0])
                if row["task_key"] != key or not row["result_hash"]:
                    continue
                value = self.store._get_object(row["result_hash"])
                if type(value) is ExecutionCheckpoint:
                    checkpoints.append(value)
            calls = []
            for row in db.execute("SELECT * FROM calls WHERE task_key=? ORDER BY call_id", (key,)):
                calls.append(
                    dict(
                        call_id=row["call_id"],
                        state=row["state"],
                        validation_code=row["validation_code"],
                        request=self.store._get_object(row["request_hash"]),
                        response=(
                            self.store._get_object(row["response_hash"]) if row["response_hash"] else None
                        ),
                    )
                )
        with self.store._transaction() as db:
            authorize(db)  # Leave the content-reading WAL snapshot before export.
        return dict(protocol=PROTOCOL, checkpoints=tuple(checkpoints), calls=tuple(calls))

    def finalize(self, lease, checkpoint, result, bindings):
        """Validate every used branch in one fresh transaction, then persist."""
        with self.store._transaction(True) as db:
            session, task = self.tasks._lease(db, lease)
            positive, queries = {}, []
            for snapshot, read_set in bindings:
                self.store._validate_snapshot(db, snapshot, read_set)
                p, q = unpack_dependencies(self.store.snapshot_dependencies(snapshot, read_set))
                if any(key in positive and positive[key] != version for key, version in p.items()):
                    raise stopped("EXECUTION_VERSION_CONFLICT", "STALE_STATE", "commit")
                positive.update(p)
                for item in q:
                    if item not in queries:
                        queries.append(item)
            if len(queries) > 64:
                raise stopped("TASK_QUERY_DEPENDENCY_BOUND", "BUDGET_EXHAUSTED", "commit")
            task.update(
                state="COMPLETED" if result.status in ("COMPLETED", "PARTIAL") else "FAILED",
                result_hash=self.store._put_object(result),
                dependencies=codec.canonical(pack_dependencies(positive, queries)),
            )
            self.store._record(db, "tasks", task, session["revision"])
        self.store._checkpoint("task_finished")


def validate_execution_reservation(ledger, db, task, request, snapshot, call_id, serialized, allowance):
    """Only a previously persisted exact graph binding can change call context."""
    if not task["result_hash"]:
        raise stopped("EXECUTION_CALL_BINDING_REQUIRED", "DENIED", "model")
    checkpoint = ledger.store._get_object(task["result_hash"])
    if (
        type(checkpoint) is not ExecutionCheckpoint
        or checkpoint.mode != "RUNNING"
        or allowance != request.budget
    ):
        raise stopped("EXECUTION_CALL_BINDING_REQUIRED", "DENIED", "model")
    matches = [node for node in checkpoint.nodes.values() if node.get("call_id") == call_id]
    if len(matches) != 1:
        raise stopped("EXECUTION_CALL_BINDING_REQUIRED", "DENIED", "model")
    node = matches[0]
    from hcl.kernel.execution import SnapshotRef

    reference = node.get("call_snapshot")
    if type(reference) is not SnapshotRef:
        raise stopped("EXECUTION_CALL_BINDING_REQUIRED", "DENIED", "model")
    bound_snapshot = checkpoint.snapshots["values"].get(reference.digest)
    if bound_snapshot is None or sha256(codec.dumps(bound_snapshot)).hexdigest() != reference.digest:
        raise stopped("EXECUTION_CALL_CONTEXT_CHANGED", "DENIED", "model")
    if (
        bound_snapshot != snapshot
        or node.get("wire_hash") != sha256(serialized.encode()).hexdigest()
        or node["state"] != "RUNNING"
    ):
        raise stopped("EXECUTION_CALL_CONTEXT_CHANGED", "DENIED", "model")
    calls = list(db.execute("SELECT * FROM calls WHERE task_key=?", (task["task_key"],)))
    if any(call["attempted"] is None for call in calls):
        raise stopped("UNKNOWN_SEND_NO_RESEND", "SEND_UNKNOWN", "model")
    if (
        sum(call["request_bytes"] for call in calls) + len(serialized.encode())
        > allowance.max_total_request_bytes
    ):
        raise stopped("TOTAL_REQUEST_BYTES_EXCEEDED", "BUDGET_EXHAUSTED", "model")
    # Reserve a full per-call visible output slice before dispatch. Unknown size
    # remains a hold, not a presumed zero, and cannot overdraw task capacity.
    output_held = sum(
        call["output_bytes"] if call["output_bytes"] is not None else allowance.max_output_bytes
        for call in calls
    )
    if output_held + 2 * allowance.max_output_bytes > allowance.max_total_output_bytes:
        raise stopped("TOTAL_OUTPUT_BYTES_EXCEEDED", "BUDGET_EXHAUSTED", "model")
