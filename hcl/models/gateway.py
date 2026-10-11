"""A no-network model gateway for S1.1 contract and fault tests only.

There is deliberately no provider transport or credential loader. Reservations
are process-local and cannot authorize live work or establish crash recovery.
S1.2 supplies durable reservation/recovery before any live port is considered.
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


class ModelPort(Protocol):
    def describe(self) -> ProviderCapabilities: ...


class OfflineModelPort:
    """A supplied test response; no language comprehension is implied."""
    def __init__(self, response: str = "Offline fixture response.", *, fault: str | None = None):
        if fault not in (None, "before_send", "send_unknown", "invalid_return"):
            raise ValueError("unknown fixture fault")
        self.response = response
        self.fault = fault
        self.attempts = 0

    def describe(self) -> ProviderCapabilities:
        return ProviderCapabilities("offline-fixture-v1", "simulation", network=False)

    async def generate(self, serialized_context: str) -> str:
        if self.fault == "before_send":
            raise HCLFailure("FAILED", "model", "FAILED_BEFORE_SEND", "transport",
                             "The offline port failed before simulated sending.")
        self.attempts += 1
        if self.fault == "send_unknown":
            raise HCLFailure("SEND_UNKNOWN", "model", "SEND_UNKNOWN", "transport",
                             "The simulated send outcome is unknown; it will not be retried.")
        if self.fault == "invalid_return":
            return None
        return self.response


@dataclass(frozen=True)
class AuthorizedContext:
    snapshot: Snapshot
    question: str


@dataclass(frozen=True)
class CallSpec:
    request_id: str
    allowance: BudgetSlice


class ModelGateway:
    def __init__(self, store: StateStore, port: OfflineModelPort | None = None):
        self._store = store
        self._port = port if port is not None else OfflineModelPort()
        # Do not turn a capability claim or an arbitrary callback into authority.
        if type(self._port) is not OfflineModelPort:
            raise ValueError("S1.1 supports only the built-in offline fixture port")
        self._calls: dict[tuple[Principal, str, str], str] = {}

    @property
    def capabilities(self) -> ProviderCapabilities:
        return self._port.describe()

    def call_state(self, principal: Principal, session_id: str, request_id: str) -> str | None:
        return self._calls.get((principal, session_id, request_id))

    async def generate(self, authorized_context: AuthorizedContext, call_spec: CallSpec) -> ModelReturn:
        snapshot = authorized_context.snapshot
        self._store.validate_snapshot(snapshot)
        allowance = call_spec.allowance
        key = (snapshot.principal, snapshot.session_id, call_spec.request_id)
        if key in self._calls:
            raise HCLFailure("FAILED", "model", "CALL_ALREADY_RESERVED", "request_id",
                             "This call is already reserved; automatic resending is forbidden.")
        if allowance.max_mock_calls < 1:
            raise HCLFailure("BUDGET_EXHAUSTED", "model", "MOCK_CALL_BUDGET", "budget.max_mock_calls",
                             "No offline model call was allowed for this task.")
        # Source contents are tagged as untrusted data, never as system policy.
        serialized = json.dumps({"schema": "hcl-offline-context-1", "question": authorized_context.question,
                                 "untrusted_sources": [
                                     {"source_id": source.handle.source_id, "text": source.text}
                                     for source in snapshot.immutable_views.values()]}, ensure_ascii=False)
        request_bytes = len(serialized.encode("utf-8"))
        if request_bytes > allowance.max_request_bytes:
            raise HCLFailure("BUDGET_EXHAUSTED", "model", "REQUEST_BYTES_EXCEEDED",
                             "budget.max_request_bytes", "The complete request exceeds the byte allowance.")
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
