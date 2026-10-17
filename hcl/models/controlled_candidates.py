"""Explicit host-installed, disconnected candidate production boundary.

The protocol adapter prepares documented request/response shapes; this release
installs only finite disconnected transports. It cannot install credentials,
perform HTTP, authorize itself, or certify live semantic extraction.
"""
from hashlib import sha256
from hcl.models.candidate_contracts import CandidateAuthorization, MeteredCandidateRequest, MODE, PROTOCOL
from hcl.kernel.execution import ExecutionBudget, ExecutionIssue
from hcl.kernel.types import HCLFailure, TaskRequest, Issue
from hcl.memory import codec
from hcl.models.gateway import ProviderCapabilities, ModelReturn
from hcl.models.candidate_protocol import (DisconnectedChatTransport, request_body, parse_return,
                                           candidate_text)
from hcl.runtime.candidate_ledger import CandidateLedger, blocked
from hcl.runtime.budget import TaskLease, task_key
from hcl.runtime.context import ContextCompiler


def affect_request(request_id, question, source_handles, session_id, principal, *, budget):
    """One finite M03/M06/M08/M05 obligation; no all-domain question router.

    The caller supplies ordinary source text through store.put_source and a
    question. It never has to write mental/attribution candidate JSON.
    """
    return TaskRequest(request_id, question, source_handles, session_id, principal, budget=budget,
                       issue=ExecutionIssue("appraisal", goals=(Issue("appraisal", "affect.evaluate"),)))


class ControlledCandidateGateway:
    candidate_purpose = "affect_compile_v2"

    def __init__(self, store, *, provider, model, transport, context_tokens=1048576, output_tokens=262144):
        if not store.durable or type(transport) is not DisconnectedChatTransport:
            raise ValueError("only built-in disconnected transport on durable state is installed")
        from hcl.kernel.scope import identifier
        identifier(provider); identifier(model)
        if any(type(v) is not int or not 1 <= v <= 4194304 for v in (context_tokens, output_tokens)):
            raise ValueError("finite declared protocol token capacity required")
        self._store, self._transport = store, transport
        self.provider, self.model = provider, model
        self._capabilities = ProviderCapabilities(model, "controlled-chat-candidates-1", False,
                                                 context_tokens, output_tokens,
                                                 "UTF8_BYTES_CONSERVATIVE_UPPER_BOUND", True, False, False)
        self._ledger, self._authorizations = CandidateLedger(store), {}

    @property
    def capabilities(self):
        return self._capabilities

    def register_authorization(self, request, authorization):
        """Trusted embedding-host API, not callable from model/source JSON.

        Same-process hostile Python is outside this trust boundary. Reopening a
        store never re-installs authority; the host must bind it again explicitly.
        Persisted grants/receipts alone cannot dispatch new calls.
        """
        if (type(request) is not TaskRequest or type(authorization) is not CandidateAuthorization
                or type(request.issue) is not ExecutionIssue or len(request.issue.goals) != 1
                or type(request.issue.goals[0]) is not Issue or request.issue.goals[0].kind != "affect.evaluate"
                or request.issue.goals[0].source_id is not None or type(request.budget) is not ExecutionBudget):
            raise blocked("CANDIDATE_SCOPE_REQUIRED")
        if (authorization.provider != self.provider or authorization.model != self.model
                or dict(authorization.source_versions) != {h.source_id: h.version for h in request.source_handles}
                or authorization.max_input_tokens > self.capabilities.context_tokens
                or authorization.max_output_tokens > self.capabilities.output_tokens):
            raise blocked("CANDIDATE_AUTHORIZATION_SCOPE")
        self._store.snapshot(request.session_id, request.principal, request.source_handles)
        key = task_key(request.principal, request.session_id, request.request_id)
        fingerprint = sha256(codec.dumps(request)).hexdigest()
        if authorization.task_fingerprint != fingerprint:
            raise blocked("CANDIDATE_AUTHORIZATION_TASK_MISMATCH")
        prior = self._authorizations.get(key)
        if prior is not None and prior != (fingerprint, authorization):
            raise blocked("CANDIDATE_AUTHORIZATION_CHANGED")
        self._authorizations[key] = (fingerprint, authorization)

    def revoke_authorization(self, request):
        self._authorizations.pop(task_key(request.principal, request.session_id, request.request_id), None)

    def call_state(self, principal, session_id, request_id):
        return self._ledger.state(principal, session_id, request_id)

    async def generate(self, context, spec):
        if type(spec.task_lease) is not TaskLease or spec.task_lease.request_id != spec.request_id:
            raise blocked("TASK_LEASE_REQUIRED")
        lease = spec.task_lease
        binding = self._authorizations.get(lease.task_key)
        if binding is None:
            raise blocked("CANDIDATE_AUTHORIZATION_REQUIRED")
        fingerprint, grant = binding
        if context.chunk is None or context.chunk.purpose != self.candidate_purpose:
            raise blocked("CANDIDATE_PURPOSE_DENIED")
        serialized = ContextCompiler(context.semantic_profile).serialize(context.snapshot, context.question, context.chunk)
        body = request_body(serialized, grant)
        envelope = MeteredCandidateRequest(PROTOCOL, grant, fingerprint, serialized, body)
        owned = False
        dispatch_started = False
        try:
            self._ledger.reserve_candidate(lease, context.snapshot, context.question, spec.allowance, spec.call_id, envelope)
            owned = True
            self._store._checkpoint("call_reserved")
            if self._authorizations.get(lease.task_key) != binding:
                raise blocked("CANDIDATE_AUTHORIZATION_REVOKED")
            self._ledger.transition(lease, spec.call_id, "RESERVED", "SEND_STARTED", snapshot=context.snapshot)
            self._store._checkpoint("send_started")
            # Revalidate after all pre-send seams, immediately before dispatch.
            if self._authorizations.get(lease.task_key) != binding:
                raise blocked("CANDIDATE_AUTHORIZATION_REVOKED")
            self._store.validate_snapshot(context.snapshot)
            # Exact built-in disconnected implementation, not arbitrary callbacks.
            dispatch_started = True
            raw = await self._transport.send(body)
            self._store._checkpoint("response_received")
            receipt = parse_return(raw, grant, min(spec.allowance.max_output_bytes,
                                   spec.allowance.max_visible_output_tokens, self.capabilities.output_tokens))
            self._ledger.returned(lease, spec.call_id, receipt)
            self._store._checkpoint("return_persisted")
            if receipt.validation_code:
                raise blocked(receipt.validation_code, "FAILED")
            self._store.validate_snapshot(context.snapshot)
            try:
                candidate = candidate_text(receipt, context.snapshot.source_versions)
            except (ValueError, TypeError, RecursionError, UnicodeError):
                raise HCLFailure("INVALID_REQUEST", "affect_compile", "INVALID_AFFECT_RETURN_ENVELOPE", "schema/source_input_versions",
                                 "The candidate must preserve the exact v2 source/version envelope.") from None
            self._ledger.transition(lease, spec.call_id, "RETURNED", "RETURNED", validation_code="VALIDATED")
            return ModelReturn(candidate, receipt.finish_reason, len(body.encode()), len(candidate.encode()),
                               "DISCONNECTED_PROTOCOL_SIMULATION_NOT_LIVE", self.usage(lease))
        except Exception as caught:
            error = caught if isinstance(caught, HCLFailure) else blocked("CANDIDATE_SEND_UNKNOWN", "SEND_UNKNOWN")
            if owned:
                row = self._ledger.call(lease, spec.call_id)
                if row["state"] in ("RESERVED", "SEND_STARTED"):
                    # No downstream exception is trusted to claim pre-send.
                    state = "FAILED_BEFORE_SEND" if not dispatch_started else "UNKNOWN"
                    self._ledger.transition(lease, spec.call_id, row["state"], state, validation_code=error.diagnostic.code)
                    if state == "UNKNOWN":
                        error = blocked("CANDIDATE_SEND_UNKNOWN", "SEND_UNKNOWN")
                elif row["state"] == "RETURNED":
                    self._ledger.transition(lease, spec.call_id, "RETURNED", "VALIDATION_REJECTED", validation_code=error.diagnostic.code)
            raise HCLFailure(error.status, error.diagnostic.stage, error.diagnostic.code,
                             error.diagnostic.field_path, error.diagnostic.message,
                             resource_usage=self.usage(lease)) from None

    def usage(self, lease):
        with self._store._transaction() as db:
            self._ledger._lease(db, lease, active=False)
            return self._ledger._usage(db, lease.task_key)
