"""Explicit host-controlled recovery; no timer or reconnect can resend work."""
from hcl.runtime.budget import TaskBudgetLedger


class RecoveryManager:
    def __init__(self, store):
        self.ledger = TaskBudgetLedger(store)

    def pending(self, principal, session_id):
        return self.ledger.pending(principal, session_id)

    def recover_abandoned(self, principal, session_id, request_id, *, expected_owner_id):
        return self.ledger.recover_abandoned(principal, session_id, request_id, expected_owner_id)
