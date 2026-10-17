"""Versioned metering inside the existing atomic, hash-checked call/event log."""
from hashlib import sha256
from hcl.models.candidate_contracts import MODE, MeteredCandidateRequest, MeteredCandidateReturn
from hcl.kernel.types import HCLFailure
from hcl.kernel.scope import identifier
from hcl.memory import codec
from .budget import TaskBudgetLedger
from .execution_ledger import validate_execution_reservation


def blocked(code, status="DENIED"):
    return HCLFailure(status, "model", code, "candidate_authorization",
                      "The candidate call is outside its bound authorization or accounting contract.")


def split_calls(store, calls):
    ordinary, metered = [], []
    for row in calls:
        request = store._get_object(row["request_hash"])
        if type(request) is MeteredCandidateRequest:
            response = store._get_object(row["response_hash"]) if row["response_hash"] else None
            if response is not None and type(response) is not MeteredCandidateReturn:
                raise blocked("CANDIDATE_LEDGER_CORRUPT", "FAILED")
            metered.append((row, request, response))
        else:
            ordinary.append(row)
    return ordinary, metered


def cost_hold(row, request, response):
    if row["state"] == "FAILED_BEFORE_SEND":
        return 0
    return (response.settled_nanos if response is not None and response.settled_nanos is not None
            else request.authorization.reservation_nanos)


def usd(nanos):
    whole, fraction = divmod(nanos, 10**9)
    return str(whole) + "." + str(fraction).zfill(9)


def metered_usage(calls):
    if not calls:
        return {}
    known = sum(row["attempted"] or 0 for row, _, _ in calls)
    unknown = any(row["attempted"] is None for row, _, _ in calls)
    observed = sum(r.settled_nanos for _, _, r in calls if r is not None and r.settled_nanos is not None)
    held = sum(cost_hold(row, request, response) for row, request, response in calls)
    unsettled = any(row["state"] != "FAILED_BEFORE_SEND" and (r is None or r.settled_nanos is None)
                    for row, _, r in calls)
    return dict(accounting_mode=MODE, provider_calls=0, provider_spend_usd="0",
                metered_transport_calls=None if unknown else known,
                observed_metered_transport_calls=known, held_metered_transport_calls=len(calls),
                metered_send_unknown=unknown, simulated_cost_unknown=unsettled,
                simulated_provider_spend_usd=None if unsettled else usd(observed),
                observed_simulated_provider_spend_usd=usd(observed),
                held_simulated_cost_nanos=held, observed_simulated_cost_nanos=observed,
                observed_protocol_input_tokens=sum(r.input_tokens or 0 for _, _, r in calls if r),
                observed_protocol_output_tokens=sum(r.output_tokens or 0 for _, _, r in calls if r),
                replay_new_metered_transport_calls=0)


class CandidateLedger(TaskBudgetLedger):
    def reserve_candidate(self, lease, snapshot, question, allowance, call_id, envelope):
        identifier(call_id)
        with self.store._transaction(True) as db:
            session, task = self._lease(db, lease)
            self.store._validate_snapshot(db, snapshot)
            request = self.store._get_object(task["request_hash"])
            grant = envelope.authorization
            if (envelope.task_fingerprint != task["fingerprint"]
                    or grant.task_fingerprint != task["fingerprint"]
                    or snapshot.session_id != lease.session_id or snapshot.principal != lease.principal
                    or question != request.question or dict(snapshot.source_versions) != dict(grant.source_versions)):
                raise blocked("CANDIDATE_TASK_BINDING_MISMATCH")
            validate_execution_reservation(self, db, task, request, snapshot, call_id, envelope.context, allowance)
            if db.execute("SELECT 1 FROM calls WHERE task_key=? AND call_id=?", (lease.task_key, call_id)).fetchone():
                raise blocked("CALL_ALREADY_RESERVED", "FAILED")
            rows = list(db.execute("SELECT * FROM calls WHERE task_key=?", (lease.task_key,)))
            ordinary, metered = split_calls(self.store, rows)
            if ordinary or any(r.authorization != grant or r.task_fingerprint != task["fingerprint"] for _, r, _ in metered):
                raise blocked("CANDIDATE_AUTHORIZATION_CHANGED")
            if any(row["attempted"] is None or (response is not None and response.settled_nanos is None)
                   for row, _, response in metered):
                raise blocked("CANDIDATE_UNKNOWN_NO_RESEND", "SEND_UNKNOWN")
            if any(response is not None and response.validation_code for _, _, response in metered):
                raise blocked("CANDIDATE_PROTOCOL_FAILURE_NO_RETRY", "FAILED")
            if len(metered) >= grant.max_calls:
                raise blocked("CANDIDATE_CALL_BUDGET", "BUDGET_EXHAUSTED")
            held = sum(cost_hold(*values) for values in metered)
            if held + grant.reservation_nanos > grant.max_cost_nanos:
                raise blocked("CANDIDATE_COST_BUDGET", "BUDGET_EXHAUSTED")
            size = len(envelope.body.encode("utf-8"))
            if size > allowance.max_request_bytes or sum(r["request_bytes"] for r in rows) + size > allowance.max_total_request_bytes:
                raise blocked("CANDIDATE_REQUEST_CAPACITY", "BUDGET_EXHAUSTED")
            if size > grant.max_input_tokens:
                raise blocked("CANDIDATE_INPUT_TOKEN_CAPACITY", "BUDGET_EXHAUSTED")
            row = dict(task_key=lease.task_key, call_id=call_id, session_id=lease.session_id, state="RESERVED",
                       owner_id=lease.owner_id, request_hash=self.store._put_content(envelope,
                           session_id=lease.session_id, context=snapshot, owner=("task", lease.session_id, lease.task_key)),
                       response_hash=None, request_bytes=size, output_bytes=None, attempted=0, validation_code=None)
            self.store._record(db, "calls", row, session["revision"])
            return row

    def returned(self, lease, call_id, receipt):
        # This transaction records billing and visible response before semantic
        # validation or late ACL checks. Neither can retroactively erase usage.
        with self.store._transaction(True) as db:
            session, _ = self._lease(db, lease)
            row = dict(db.execute("SELECT * FROM calls WHERE task_key=? AND call_id=?",
                                  (lease.task_key, call_id)).fetchone())
            if row["state"] != "SEND_STARTED" or type(receipt) is not MeteredCandidateReturn:
                raise blocked("CANDIDATE_RETURN_STATE", "FAILED")
            row.update(state="RETURNED", attempted=1, response_hash=self.store._put_content(receipt,
                       session_id=lease.session_id, owner=("task", lease.session_id, lease.task_key)),
                       output_bytes=len(receipt.visible_text.encode("utf-8")) if receipt.visible_text is not None else None,
                       validation_code=receipt.validation_code)
            self.store._record(db, "calls", row, session["revision"])
            return row
