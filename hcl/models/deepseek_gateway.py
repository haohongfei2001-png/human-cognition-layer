"""Explicit host-installed DeepSeek sender into the existing compiler/runner.

Installation and grant issuance are host responsibilities, never inferred from
source text, a decoded receipt, an environment, or an old simulation grant.
"""
from hashlib import sha256
from pathlib import Path
from hcl.kernel.execution import ExecutionBudget, ExecutionIssue
from hcl.kernel.types import HCLFailure, TaskRequest, Issue
from hcl.memory import codec
from hcl.models.deepseek_contracts import (
    PROTOCOL, MODEL, CONTEXT_TOKENS, OUTPUT_TOKENS, MAX_REQUEST_BYTES, MAX_VISIBLE_BYTES,
    DeepSeekBatchAuthorization, DeepSeekCandidateRequest,
)
from hcl.models.deepseek_protocol import request_body, parse_return
from hcl.models.deepseek_transport import DeepSeekHTTPTransport, DeepSeekTransportFailure
from hcl.models.candidate_protocol import candidate_text
from hcl.models.gateway import ProviderCapabilities, ModelReturn
from hcl.runtime.deepseek_ledger import CNYBatchLedger, DeepSeekTaskLedger, authorization_hash
from hcl.runtime.candidate_ledger import blocked
from hcl.runtime.budget import TaskLease, task_key
from hcl.runtime.context import ContextCompiler


class DeepSeekCandidateGateway:
    candidate_purpose = "affect_compile_v2"

    def __init__(self, store, *, authorization, transport):
        if (not store.durable or type(transport) is not DeepSeekHTTPTransport
                or type(authorization) is not DeepSeekBatchAuthorization
                or str(Path(store.path).resolve()) != authorization.state_store_path):
            raise ValueError("durable source-bound DeepSeek host installation required")
        self._store, self._transport, self._grant = store, transport, authorization
        self._batch = CNYBatchLedger(authorization)  # Never creates/reopens old authority.
        self._ledger, self._bindings = DeepSeekTaskLedger(store), {}
        self._capabilities = ProviderCapabilities(MODEL, "deepseek-cny-candidates-1", True,
            CONTEXT_TOKENS, OUTPUT_TOKENS, "PROVIDER_USAGE_NOT_UTF8_TOKEN_ESTIMATE", True, False, False,
            "thinking=disabled;reasoning_effort=none")

    @property
    def capabilities(self):
        return self._capabilities

    def close(self):
        self._batch.close()

    def register_authorization(self, request):
        if (type(request) is not TaskRequest or type(request.issue) is not ExecutionIssue
                or len(request.issue.goals) != 1 or type(request.issue.goals[0]) is not Issue
                or request.issue.goals[0].kind != "affect.evaluate" or request.issue.goals[0].source_id is not None
                or type(request.budget) is not ExecutionBudget or request.budget.max_feedback > 1
                or request.budget.max_visible_output_tokens < OUTPUT_TOKENS):
            raise blocked("DEEPSEEK_SCOPE_REQUIRED")
        fingerprint = sha256(codec.dumps(request)).hexdigest()
        if fingerprint not in self._grant.task_fingerprints:
            raise blocked("CNY_TASK_NOT_AUTHORIZED")
        self._store.snapshot(request.session_id, request.principal, request.source_handles)
        with self._batch._transaction() as db:
            self._batch._validate(db, active=True)
        self._bindings[task_key(request.principal, request.session_id, request.request_id)] = fingerprint

    def revoke_authorization(self):
        self._batch.stop("REVOKED")  # Durable across all workers/processes.
        self._bindings.clear()

    def batch_usage(self):
        return self._batch.audit()

    def call_state(self, principal, session_id, request_id):
        return self._ledger.state(principal, session_id, request_id)

    def usage(self, lease):
        with self._store._transaction() as db:
            self._ledger._lease(db, lease, active=False)
            return self._ledger._usage(db, lease.task_key)

    async def generate(self, context, spec):
        if type(spec.task_lease) is not TaskLease or spec.task_lease.request_id != spec.request_id:
            raise blocked("TASK_LEASE_REQUIRED")
        lease = spec.task_lease
        fingerprint = self._bindings.get(lease.task_key)
        if fingerprint is None:
            raise blocked("DEEPSEEK_HOST_AUTHORIZATION_REQUIRED")
        if context.chunk is None or context.chunk.purpose != self.candidate_purpose or context.chunk.total != 1:
            raise blocked("DEEPSEEK_SINGLE_SYNTHETIC_PACKET_REQUIRED")
        serialized = ContextCompiler(context.semantic_profile).serialize(context.snapshot, context.question, context.chunk)
        body = request_body(serialized)
        if len(body.encode("utf-8")) > min(MAX_REQUEST_BYTES, spec.allowance.max_request_bytes):
            raise blocked("DEEPSEEK_REQUEST_CAPACITY", "BUDGET_EXHAUSTED")
        # Bytes limit storage/transport, not true provider tokens. Monetary hold
        # covers the full documented context, including system/schema framing.
        auth_hash = authorization_hash(self._grant)
        claim_id = sha256(codec.canonical([auth_hash,lease.task_key,spec.call_id]).encode()).hexdigest()
        envelope = DeepSeekCandidateRequest(PROTOCOL,self._grant.batch_id,auth_hash,claim_id,
            fingerprint,context.snapshot.source_versions,serialized,body)
        claimed = owned = False
        try:
            self._batch.reserve(claim_id, fingerprint)
            claimed = True
            self._store._checkpoint("cny_claim_reserved")
            self._ledger.reserve_candidate(lease,context.snapshot,context.question,spec.allowance,spec.call_id,envelope)
            owned = True
            self._store._checkpoint("call_reserved")
            def gate():
                def authorize():
                    if self._bindings.get(lease.task_key) != fingerprint:
                        raise blocked("DEEPSEEK_HOST_AUTHORIZATION_REVOKED")
                    self._ledger.transition(lease,spec.call_id,"RESERVED","SEND_STARTED",snapshot=context.snapshot)
                    self._store._checkpoint("send_started")
                    if self._bindings.get(lease.task_key) != fingerprint:
                        raise blocked("DEEPSEEK_HOST_AUTHORIZATION_REVOKED")
                    self._store.validate_snapshot(context.snapshot)
                self._batch.dispatch(claim_id, authorize)
            raw = await self._transport.send(body, gate)
            self._store._checkpoint("response_received")
            receipt = parse_return(raw,min(spec.allowance.max_output_bytes,MAX_VISIBLE_BYTES))
            del raw
            self._ledger.returned(lease,spec.call_id,receipt)
            self._store._checkpoint("cny_task_return_persisted")
            self._batch.returned(claim_id,receipt)
            self._store._checkpoint("return_persisted")
            if receipt.validation_code:
                raise blocked(receipt.validation_code,"FAILED")
            self._store.validate_snapshot(context.snapshot)
            try:
                candidate = candidate_text(receipt,context.snapshot.source_versions)
            except (ValueError,TypeError,RecursionError,UnicodeError):
                self._ledger.transition(lease,spec.call_id,"RETURNED","RETURNED",
                    validation_code="COMPILE_REJECTED:INVALID_AFFECT_RETURN_ENVELOPE")
                raise HCLFailure("INVALID_REQUEST","affect_compile","INVALID_AFFECT_RETURN_ENVELOPE",
                    "schema/source_input_versions","The candidate must preserve the exact v2 source/version envelope.") from None
            self._ledger.transition(lease,spec.call_id,"RETURNED","RETURNED",validation_code="VALIDATED")
            return ModelReturn(candidate,receipt.finish_reason,len(body.encode()),len(candidate.encode()),
                "HOST_HTTP_RETURN_NOT_AUTOMATIC_SEMANTIC_ACCEPTANCE",self.usage(lease))
        except BaseException as caught:
            # BaseException includes cancellation/process interruption. Never
            # let cancellation make an already committed claim reusable.
            semantic = isinstance(caught,HCLFailure) and caught.diagnostic.stage == "affect_compile"
            error = caught if isinstance(caught,HCLFailure) else blocked(
                caught.code if isinstance(caught,DeepSeekTransportFailure) else "DEEPSEEK_SEND_UNKNOWN","SEND_UNKNOWN")
            if claimed and not semantic:
                self._batch.stop()
            if owned:
                row = self._ledger.call(lease,spec.call_id)
                if row["state"] in ("RESERVED","SEND_STARTED"):
                    self._ledger.transition(lease,spec.call_id,row["state"],
                        "FAILED_BEFORE_SEND" if row["state"] == "RESERVED" else "UNKNOWN",validation_code=error.diagnostic.code)
                elif row["state"] == "RETURNED" and not semantic and isinstance(caught,Exception):
                    self._ledger.transition(lease,spec.call_id,"RETURNED","VALIDATION_REJECTED",validation_code=error.diagnostic.code)
            if not isinstance(caught,Exception):
                raise
            raise HCLFailure(error.status,error.diagnostic.stage,error.diagnostic.code,error.diagnostic.field_path,
                error.diagnostic.message,resource_usage=self.usage(lease)) from None
