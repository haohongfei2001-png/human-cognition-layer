"""A no-network model gateway with memory-fixture or durable task accounting.

There is deliberately no provider transport or credential loader. Reservations
on the SQLite backend commit before the simulated transport and share one task
budget across connections. Neither backend authorizes live work.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Protocol

from hcl.kernel.types import BudgetSlice, HCLFailure, Principal, Snapshot
from hcl.memory.store import StateStore


@dataclass(frozen=True)
class ProviderCapabilities:
    model_id: str
    model_family: str
    network: bool
    context_tokens: int | None = None
    output_tokens: int | None = None
    tokenizer: str | None = None
    structured_output: bool | None = None
    cancellation: bool | None = None
    idempotency: bool | None = None
    reasoning_parameters: str | None = None


@dataclass(frozen=True)
class ModelReturn:
    visible_text: str
    finish_reason: str
    request_bytes: int
    output_bytes: int
    evidence_level: str = "OFFLINE_FIXTURE_NOT_SEMANTIC_VALIDATION"
    resource_usage: dict | None = None


class ModelPort(Protocol):
    def describe(self) -> ProviderCapabilities: ...


class OfflineModelPort:
    """A supplied test response; no language comprehension is implied."""
    def __init__(self, response: str = "Offline fixture response.", *, fault: str | None = None,
                 responses: tuple[str, ...] | None = None, context_tokens: int | None = None, output_tokens: int | None = None):
        if fault not in (None, "before_send", "send_unknown", "invalid_return"):
            raise ValueError("unknown fixture fault")
        if responses is not None and (type(responses) not in (tuple, list) or not responses):
            raise ValueError("a nonempty finite offline response sequence is required")
        for cap in (context_tokens, output_tokens):
            if cap is not None and (type(cap) is not int or cap < 1):
                raise ValueError("positive declared fixture token capacity required")
        self.responses = None if responses is None else tuple(responses)
        self.context_tokens, self.output_tokens = context_tokens, output_tokens
        self.contexts = []
        self.response = response
        self.fault = fault
        self.attempts = 0

    def describe(self) -> ProviderCapabilities:
        return ProviderCapabilities("offline-fixture-v1", "simulation", network=False,
                                    context_tokens=self.context_tokens, output_tokens=self.output_tokens,
                                    tokenizer="UTF8_BYTES_CONSERVATIVE_UPPER_BOUND")

    async def generate(self, serialized_context: str) -> str:
        if self.fault == "before_send":
            raise HCLFailure("FAILED", "model", "FAILED_BEFORE_SEND", "transport",
                             "The offline port failed before simulated sending.")
        self.contexts.append(serialized_context)
        self.attempts += 1
        if self.fault == "send_unknown":
            raise HCLFailure("SEND_UNKNOWN", "model", "SEND_UNKNOWN", "transport",
                             "The simulated send outcome is unknown; it will not be retried.")
        if self.fault == "invalid_return":
            return None
        if self.responses is not None:
            if self.attempts > len(self.responses):
                raise HCLFailure("FAILED", "model", "OFFLINE_FIXTURE_EXHAUSTED", "response",
                                 "No further explicitly supplied fixture response exists.")
            return self.responses[self.attempts - 1]
        return self.response


@dataclass(frozen=True)
class AuthorizedContext:
    snapshot: Snapshot
    question: str
    purpose: str = "answer"
    semantic_profile: object = None
    chunk: object = None


@dataclass(frozen=True)
class CallSpec:
    request_id: str
    allowance: BudgetSlice
    task_lease: object | None = None
    call_id: str = "response"


class ModelGateway:
    def __init__(self, store: StateStore, port: OfflineModelPort | None = None):
        self._store = store
        self._port = port if port is not None else OfflineModelPort()
        # Do not turn a capability claim or an arbitrary callback into authority.
        if type(self._port) is not OfflineModelPort:
            raise ValueError("Only the built-in offline fixture port is currently supported")
        self._calls: dict[tuple[Principal, str, str, str], str] = {}
        self._context_compiler = None
        from hcl.runtime.budget import TaskBudgetLedger
        self._ledger = TaskBudgetLedger(store) if store.durable else None

    @property
    def capabilities(self) -> ProviderCapabilities:
        return self._port.describe()

    def call_state(self, principal: Principal, session_id: str, request_id: str) -> str | None:
        if self._ledger is not None:
            return self._ledger.state(principal, session_id, request_id)
        return self._calls.get((principal, session_id, request_id, "response"))

    async def generate(self, authorized_context: AuthorizedContext, call_spec: CallSpec) -> ModelReturn:
        snapshot = authorized_context.snapshot
        self._store.validate_snapshot(snapshot)
        allowance = call_spec.allowance
        key = (snapshot.principal, snapshot.session_id, call_spec.request_id, call_spec.call_id)
        if self._ledger is None and key in self._calls:
            raise HCLFailure("FAILED", "model", "CALL_ALREADY_RESERVED", "request_id",
                             "This call is already reserved; automatic resending is forbidden.")
        if allowance.max_mock_calls < 1:
            raise HCLFailure("BUDGET_EXHAUSTED", "model", "MOCK_CALL_BUDGET", "budget.max_mock_calls",
                             "No offline model call was allowed for this task.")
        # Source contents are tagged as untrusted data, never as system policy.
        if authorized_context.chunk is not None:
            from hcl.kernel.execution import ExecutionBudget
            from hcl.runtime.context import ContextCompiler, tokens_upper_bound
            if type(allowance) is not ExecutionBudget:
                raise HCLFailure("INVALID_REQUEST", "context", "EXECUTION_BUDGET_REQUIRED", "budget",
                                 "Bounded contexts require explicit task execution limits.")
            compiler = self._context_compiler
            if compiler is None or compiler.semantic_profile != authorized_context.semantic_profile:
                compiler = self._context_compiler = ContextCompiler(authorized_context.semantic_profile)
            serialized = compiler.serialize(snapshot, authorized_context.question, authorized_context.chunk)
            if tokens_upper_bound(serialized) > compiler.limit(allowance, self.capabilities):
                raise HCLFailure("BUDGET_EXHAUSTED", "context", "CONTEXT_TOKENS_EXCEEDED", "context",
                                 "The complete serialized packet exceeds its conservative token or byte bound.")
            if self._ledger is None:
                raise HCLFailure("INVALID_REQUEST", "context", "DURABLE_EXECUTION_REQUIRED", "store",
                                 "Budgeted execution requires the persistent task ledger.")
            return await self._generate_durable(authorized_context, call_spec, serialized)
        context = {"schema": "hcl-offline-context-1", "question": authorized_context.question,
                   "untrusted_sources": [
                       {"source_id": source.handle.source_id, "text": source.text}
                       for source in snapshot.immutable_views.values()]}
        if authorized_context.purpose == "semantic_compile":
            from hcl.semantics.segments import semantic_context
            from hcl.semantics.frames import SemanticProfile
            if authorized_context.semantic_profile is not None and type(authorized_context.semantic_profile) is not SemanticProfile:
                raise HCLFailure("INVALID_REQUEST", "model", "INVALID_SEMANTIC_PROFILE", "semantic_profile",
                                 "The semantic execution profile is not typed.")
            # Build only from the already authenticated snapshot. A caller cannot
            # attach arbitrary extra context or foreign source text to this mode.
            context["semantic_task"] = semantic_context(snapshot, authorized_context.question, authorized_context.semantic_profile)
        elif authorized_context.purpose == "revision_compile":
            from hcl.kernel.dependencies import QuerySnapshot
            from hcl.semantics.revision import revision_context
            if type(snapshot) is not QuerySnapshot:
                raise HCLFailure("INVALID_REQUEST", "model", "REVISION_SNAPSHOT_REQUIRED", "snapshot",
                                 "Revision candidates require an authorized indexed snapshot.")
            context["revision_task"] = revision_context(snapshot, authorized_context.question)
        elif authorized_context.purpose != "answer":
            raise HCLFailure("INVALID_REQUEST", "model", "UNSUPPORTED_MODEL_PURPOSE", "purpose",
                             "The requested model purpose is not supported.")
        serialized = json.dumps(context, ensure_ascii=False)
        request_bytes = len(serialized.encode("utf-8"))
        if request_bytes > allowance.max_request_bytes:
            raise HCLFailure("BUDGET_EXHAUSTED", "model", "REQUEST_BYTES_EXCEEDED",
                             "budget.max_request_bytes", "The complete request exceeds the byte allowance.")
        if self._ledger is not None:
            return await self._generate_durable(authorized_context, call_spec, serialized)
        self._calls[key] = "RESERVED_IN_MEMORY_ONLY"
        try:
            response = await self._port.generate(serialized)
        except HCLFailure as error:
            self._calls[key] = error.status
            raise
        except Exception:
            self._calls[key] = "SEND_UNKNOWN"
            raise HCLFailure("SEND_UNKNOWN", "model", "SEND_UNKNOWN", "transport",
                             "The simulated call failed without a confirmed send outcome.") from None
        self._calls[key] = "RETURNED"
        if not isinstance(response, str) or not response.strip():
            self._calls[key] = "INVALID_RETURN"
            raise HCLFailure("FAILED", "model", "INVALID_MODEL_RETURN", "visible_text",
                             "The model return must contain visible text.")
        try:
            output_bytes = len(response.encode("utf-8"))
        except UnicodeEncodeError:
            self._calls[key] = "INVALID_RETURN"
            raise HCLFailure("FAILED", "model", "INVALID_MODEL_ENCODING", "visible_text",
                             "The model return is not valid Unicode text.") from None
        if output_bytes > allowance.max_output_bytes:
            self._calls[key] = "OUTPUT_REJECTED"
            raise HCLFailure("BUDGET_EXHAUSTED", "model", "OUTPUT_BYTES_EXCEEDED",
                             "budget.max_output_bytes", "The model return exceeds the output allowance.")
        self._store.validate_snapshot(snapshot)
        return ModelReturn(response, "stop", request_bytes, output_bytes)

    async def _generate_durable(self, context, spec, serialized):
        from hcl.runtime.budget import TaskLease, call_usage
        if type(spec.task_lease) is not TaskLease or spec.task_lease.request_id != spec.request_id:
            raise HCLFailure("DENIED", "model", "TASK_LEASE_REQUIRED", "call_spec.task_lease",
                             "A persistent task lease is required before reserving a call.")
        lease, call_id = spec.task_lease, spec.call_id
        owned = False
        try:
            self._ledger.reserve(lease, context.snapshot, context.question, spec.allowance, call_id, serialized)
            owned = True  # Returned only after the exclusive reservation committed.
            self._store._checkpoint("call_reserved")
            self._ledger.transition(lease, call_id, "RESERVED", "SEND_STARTED", snapshot=context.snapshot)
            self._store._checkpoint("send_started")
            response = await self._port.generate(serialized)
            self._store._checkpoint("response_received")
            self._ledger.transition(lease, call_id, "SEND_STARTED", "RETURNED", response=response)
            self._store._checkpoint("return_persisted")
            if type(response) is not str or not response.strip():
                raise HCLFailure("FAILED", "model", "INVALID_MODEL_RETURN", "visible_text", "The model return must contain visible text.")
            try:
                output_bytes = len(response.encode("utf-8"))
            except UnicodeEncodeError:
                raise HCLFailure("FAILED", "model", "INVALID_MODEL_ENCODING", "visible_text", "The model return is not valid Unicode text.") from None
            if output_bytes > spec.allowance.max_output_bytes:
                raise HCLFailure("BUDGET_EXHAUSTED", "model", "OUTPUT_BYTES_EXCEEDED", "budget.max_output_bytes", "The model return exceeds its output allowance.")
            if context.chunk is not None:
                caps = [spec.allowance.max_visible_output_tokens]
                if self.capabilities.output_tokens is not None:
                    caps.append(self.capabilities.output_tokens)
                if output_bytes > min(caps):
                    raise HCLFailure("BUDGET_EXHAUSTED", "model", "OUTPUT_TOKENS_EXCEEDED", "output",
                                     "Visible output exceeds its conservative token bound.")
            self._store.validate_snapshot(context.snapshot)
            row = self._ledger.transition(lease, call_id, "RETURNED", "RETURNED", validation_code="VALIDATED")
            return ModelReturn(response, "stop", len(serialized.encode("utf-8")), output_bytes,
                               resource_usage=call_usage(row))
        except Exception as caught:
            error = caught if isinstance(caught, HCLFailure) else HCLFailure(
                "SEND_UNKNOWN", "model", "SEND_UNKNOWN", "transport",
                "The simulated call could not establish a durable outcome; it will not be resent.")
            if not owned:
                raise error from None
            try:
                row = self._ledger.call(lease, call_id)
                state = row["state"]
                if state in ("RESERVED", "SEND_STARTED"):
                    next_state = "FAILED_BEFORE_SEND" if state == "RESERVED" or error.diagnostic.code == "FAILED_BEFORE_SEND" else "UNKNOWN"
                    row = self._ledger.transition(lease, call_id, state, next_state,
                                                  validation_code=error.diagnostic.code)
                elif state == "RETURNED":
                    row = self._ledger.transition(lease, call_id, state, "VALIDATION_REJECTED",
                                                  validation_code=error.diagnostic.code)
                usage = dict(call_usage(row), mock_call_state=row["state"])
            except HCLFailure:
                # Persistent SEND_STARTED is recovered explicitly after the owner
                # is abandoned. An unavailable ledger cannot certify zero usage.
                usage = {"mock_calls": None, "held_mock_calls": 1, "mock_usage_unknown": True,
                         "mock_call_state": "DURABLE_OUTCOME_UNAVAILABLE"}
            raise HCLFailure(error.status, error.diagnostic.stage, error.diagnostic.code,
                             error.diagnostic.field_path, error.diagnostic.message,
                             resource_usage=usage) from None
