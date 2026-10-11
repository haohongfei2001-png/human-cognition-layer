"""Bounded old method names backed solely by the formal HCL engine.

Unsupported narrative preparation and callbacks are explicit failures. This is
not the S5 wholesale replacement of old domain APIs or their return types.
"""
from uuid import uuid4

from hcl.api import HCL
from hcl.kernel.types import BudgetSlice, Issue, TaskRequest


class CognitionWorkspace:
    def __init__(self, store, *, principal, session_id, gateway=None):
        if not store.durable:
            raise ValueError("compatibility workspace requires the durable unified store")
        self.store, self.principal, self.session_id = store, principal, session_id
        self.hcl = HCL(store, principal=principal, gateway=gateway)

    def put_source(self, source_id, text, *, formal_problem=None, readers=None, permitted_observers=()):
        if permitted_observers:
            raise ValueError("story observer metadata requires the typed legacy import, not a system ACL")
        return self.store.put_source(self.session_id, self.principal, source_id, text,
                                     formal_problem=formal_problem, readers=readers)

    def prepare(self, query, *, source_ids, request_id=None, issue_kind="source.report", budget=None, through_order=None):
        if through_order is not None:
            raise ValueError("partial narrative preparation is outside the S1 compatibility slice")
        if type(source_ids) is not tuple or not source_ids or len(source_ids) != len(set(source_ids)):
            raise ValueError("explicit distinct source identities required")
        handles = self.store.current_handles(self.session_id, self.principal, source_ids)
        return TaskRequest(request_id or uuid4().hex, query, handles, self.session_id, self.principal,
                           budget=budget or BudgetSlice(),
                           issue=Issue("compat", issue_kind, source_ids[0] if issue_kind == "logic.check_interpretation" else None))

    def answer(self, query, answer_backend=None, **kwargs):
        if answer_backend is not None:
            raise ValueError("legacy provider callbacks are disabled; configure the unified ModelGateway")
        return self.hcl.run_sync(self.prepare(query, **kwargs))

    async def run(self, request):
        return await self.hcl.run(request)

    def stream(self, request):
        return self.hcl.stream(request)
