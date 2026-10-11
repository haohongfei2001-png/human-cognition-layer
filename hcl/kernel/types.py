"""Versioned, immutable contracts for the first unified execution slice.

No provider SDKs, evaluation data, language heuristics or authority live here.
FormalProblem is an explicitly supplied formal interpretation, not an automatic
translation of SourceDocument.text. Open semantic compilation belongs to S2.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Mapping, Protocol

SCHEMA_VERSION = "hcl-unified-1"
RULE_VERSION = "s1.1-explicit-finite-interpretation-1"
FORMAL_SCOPE = "FORMAL_INTERPRETATION_NOT_WORLD_OR_PRIVATE_MENTAL_TRUTH"


def freeze(value: Any) -> Any:
    """Defensively copy JSON-shaped values, including their nested containers."""
    if isinstance(value, Mapping):
        if any(not isinstance(key, str) for key in value):
            raise ValueError("mapping keys must be strings")
        return MappingProxyType({key: freeze(item) for key, item in value.items()})
    if isinstance(value, (tuple, list)):
        return tuple(freeze(item) for item in value)
    if value is None or type(value) in (str, bool, int, float):
        return value
    raise ValueError("only JSON-shaped values are permitted")


def thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [thaw(item) for item in value]
    return value


@dataclass(frozen=True)
class Principal:
    tenant_id: str
    subject_id: str


@dataclass(frozen=True)
class AccessPolicy:
    tenant_id: str
    readers: frozenset[str]

    def __post_init__(self) -> None:
        object.__setattr__(self, "readers", frozenset(self.readers))

    def permits(self, principal: Principal) -> bool:
        return self.tenant_id == principal.tenant_id and principal.subject_id in self.readers


@dataclass(frozen=True)
class SourceHandle:
    source_id: str
    version: int


@dataclass(frozen=True)
class FormalProblem:
    """Versioned explicit formal IR; strings use the bounded legacy grammar."""
    premises: tuple[str, ...]
    conclusion: str
    interpretation: Mapping[str, Any]
    representation: str = "legacy-formal-v1"

    def __post_init__(self) -> None:
        object.__setattr__(self, "premises", tuple(self.premises))
        object.__setattr__(self, "interpretation", freeze(self.interpretation))


@dataclass(frozen=True)
class SourceDocument:
    handle: SourceHandle
    text: str
    access_policy: AccessPolicy
    formal_problem: FormalProblem | None = None


@dataclass(frozen=True)
class BudgetSlice:
    max_formula_chars: int = 16000
    max_premises: int = 32
    max_local_evaluations: int = 33
    max_mock_calls: int = 0
    max_request_bytes: int = 65536
    max_output_bytes: int = 16384


@dataclass(frozen=True)
class Issue:
    issue_id: str
    kind: str = "source.report"
    source_id: str | None = None


@dataclass(frozen=True)
class TaskRequest:
    request_id: str
    question: str
    source_handles: tuple[SourceHandle, ...]
    session_id: str
    principal: Principal
    epistemic_profile: str = "balanced"
    budget: BudgetSlice = field(default_factory=BudgetSlice)
    output_contract: str = "natural-language-with-claims-v1"
    issue: Issue = field(default_factory=lambda: Issue("answer"))

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_handles", tuple(self.source_handles))


@dataclass(frozen=True)
class Diagnostic:
    stage: str
    code: str
    field_path: str
    message: str


class HCLFailure(Exception):
    """Only allowlisted, non-source diagnostic text crosses the delivery boundary."""
    def __init__(self, status: str, stage: str, code: str, field_path: str, message: str,
                 *, resource_usage: Mapping[str, Any] | None = None):
        super().__init__(code)
        self.status = status
        self.diagnostic = Diagnostic(stage, code, field_path, message)
        self.resource_usage = freeze(resource_usage or {})


@dataclass(frozen=True)
class InferenceResult:
    result_id: str
    kind: str
    values: Mapping[str, Any]
    assumption_environments: tuple[str, ...]
    premise_ids: tuple[str, ...]
    counterevidence_ids: tuple[str, ...]
    rule_version: str
    coverage: str
    diagnostics: tuple[Diagnostic, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "values", freeze(self.values))


@dataclass(frozen=True)
class Snapshot:
    session_id: str
    principal: Principal
    revision: int
    access_epoch: int
    rule_version: str
    source_versions: Mapping[str, int]
    index_versions: Mapping[str, int]
    immutable_views: Mapping[str, SourceDocument]

    def __post_init__(self) -> None:
        for name in ("source_versions", "index_versions", "immutable_views"):
            object.__setattr__(self, name, MappingProxyType(dict(getattr(self, name))))


@dataclass(frozen=True)
class Delta:
    session_id: str
    principal: Principal
    base_revision: int
    access_epoch: int
    rule_version: str
    read_set: Mapping[str, int]
    new_inferences: tuple[InferenceResult, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "read_set", freeze(self.read_set))
        object.__setattr__(self, "new_inferences", tuple(self.new_inferences))


@dataclass(frozen=True)
class OpResult:
    operation_id: str
    version: str
    read_set: Mapping[str, int]
    effects: tuple[str, ...]
    result_refs: tuple[str, ...]
    issues: tuple[str, ...]
    resource_usage: Mapping[str, Any]
    diagnostics: tuple[Diagnostic, ...]
    candidate_delta: Delta

    def __post_init__(self) -> None:
        object.__setattr__(self, "read_set", freeze(self.read_set))
        object.__setattr__(self, "resource_usage", freeze(self.resource_usage))


class CognitiveOperator(Protocol):
    def run(self, snapshot: Snapshot, issue: Issue, allowance: BudgetSlice) -> OpResult: ...


@dataclass(frozen=True)
class ResultField:
    result_id: str
    field: str
    value: Any

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", freeze(self.value))


@dataclass(frozen=True)
class AnswerClaim:
    text: str
    claim_id: str
    used_result_fields: tuple[ResultField, ...]
    support_envs: tuple[str, ...]
    counterevidence: tuple[str, ...]
    epistemic_status: str
    materiality: str = "decisive"


@dataclass(frozen=True)
class AnswerContract:
    answer: str
    claims: tuple[AnswerClaim, ...]
    mechanical_validation: str
    semantic_validation: str


@dataclass(frozen=True)
class CommitResult:
    revision: int
    result_ids: tuple[str, ...]


@dataclass(frozen=True)
class TaskResult:
    answer: str
    claim_records: tuple[AnswerClaim, ...]
    status: str
    unresolved_issues: tuple[str, ...]
    execution_receipt: Mapping[str, Any]
    usage: Mapping[str, Any]
    state_revision: int | None
    diagnostics: tuple[Diagnostic, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "execution_receipt", freeze(self.execution_receipt))
        object.__setattr__(self, "usage", freeze(self.usage))


@dataclass(frozen=True)
class DeliveryEvent:
    kind: str
    status: str
    result: TaskResult | None = None
