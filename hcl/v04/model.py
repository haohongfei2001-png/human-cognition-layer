"""Typed records for the HCL v0.4 minimal cognition slice."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class AssertionType(str, Enum):
    SCENE_FACT = "SCENE_FACT"
    SOURCE_ASSERTION = "SOURCE_ASSERTION"
    INFORMATION_EXPOSURE = "INFORMATION_EXPOSURE"
    BELIEF_ESTIMATE = "BELIEF_ESTIMATE"
    STATED_GOAL_INTENTION = "STATED_GOAL_INTENTION"
    LATENT_HYPOTHESIS = "LATENT_HYPOTHESIS"
    OTHER_UNKNOWN = "OTHER_UNKNOWN"


class AssertionStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INVALID = "INVALID"
    SUPERSEDED = "SUPERSEDED"
    UNRESOLVED = "UNRESOLVED"


class SupportLevel(str, Enum):
    DIRECT_SUPPORT = "DIRECT_SUPPORT"
    INDIRECT_SUPPORT = "INDIRECT_SUPPORT"
    COUNTEREVIDENCE = "COUNTEREVIDENCE"
    INSUFFICIENT = "INSUFFICIENT"


class BeliefStance(str, Enum):
    AFFIRM = "AFFIRM"
    DENY = "DENY"


@dataclass(frozen=True)
class EventRecord:
    event_id: str
    valid_time: str
    raw_text: str
    source_id: str
    recorded_at: str = field(default_factory=utc_now_iso)
    actor_id: str | None = None
    observer_ids: tuple[str, ...] = ()
    recipient_ids: tuple[str, ...] = ()
    semantic_version: str = "v04.1"
    supersedes: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Proposition:
    proposition_id: str
    canonical_text: str
    polarity: str = "POSITIVE"
    relation_metadata: dict[str, Any] = field(default_factory=dict)
    valid_time_start: str | None = None
    valid_time_end: str | None = None
    source_event_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class CognitiveAssertion:
    assertion_id: str
    assertion_type: AssertionType
    valid_time: str
    system_record_time: str
    evidence_event_ids: tuple[str, ...]
    subject_agent_id: str | None = None
    proposition_id: str | None = None
    hypothesis_text: str | None = None
    depends_on_assertion_ids: tuple[str, ...] = ()
    status: AssertionStatus = AssertionStatus.ACTIVE
    support_level: SupportLevel | None = None
    belief_stance: BeliefStance | None = None
    semantic_version: str = "v04.1"


@dataclass(frozen=True)
class SemanticPatch:
    patch_id: str
    event_id: str
    semantic_version: str
    propositions: tuple[Proposition, ...] = ()
    assertions: tuple[CognitiveAssertion, ...] = ()


@dataclass(frozen=True)
class EventReceipt:
    event_id: str
    event_index: int
    recorded_at: str
    duplicate: bool = False


@dataclass(frozen=True)
class StateReceipt:
    patch_id: str
    state_version: int
    checksum: str
    duplicate: bool = False


@dataclass(frozen=True)
class InvalidationReceipt:
    state_version: int
    invalidated_assertion_ids: tuple[str, ...]
    invalidated_patch_ids: tuple[str, ...]
    reason: str
    checksum: str


@dataclass(frozen=True)
class RebuildReceipt:
    state_version: int
    rebuilt_assertion_count: int
    active_patch_count: int
    checksum: str
    checkpoint: int | None = None


@dataclass(frozen=True)
class IngestResult:
    event_receipt: EventReceipt
    state_receipt: StateReceipt
    committed_patch: SemanticPatch
    rejected_patch: SemanticPatch | None = None
    semantic_repair_count: int = 0
    repair_reason: str | None = None


@dataclass(frozen=True)
class QueryContext:
    viewer: str | None
    event_time: str | None
    knowledge_cutoff: str | None
    query: str
    relevant_assertions: tuple[dict[str, Any], ...]
    evidence: tuple[dict[str, Any], ...]
    unresolved_conflicts: tuple[dict[str, Any], ...]
    latent_hypotheses: tuple[dict[str, Any], ...]
    unsupported_conclusions: tuple[str, ...]
    state_version: int
    semantic_version: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CheckerResult:
    status: str
    violations: tuple[str, ...]
    reason: str = ""

    @property
    def passed(self) -> bool:
        return self.status == "PASS" and not self.violations


@dataclass(frozen=True)
class ResponseResult:
    answer: str
    check: CheckerResult
    verified: bool
    state_version: int
    answer_version: int
