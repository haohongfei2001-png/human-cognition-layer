"""Evidence-based belief state and revision semantics for HCL v0.6."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from itertools import groupby
from typing import Iterable


def _parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


class BeliefEvidenceKind(str, Enum):
    SELF_REPORT = "SELF_REPORT"
    NARRATOR_ASSERTION = "NARRATOR_ASSERTION"
    THIRD_PARTY_REPORT = "THIRD_PARTY_REPORT"
    OBSERVED_ACTION = "OBSERVED_ACTION"
    INFORMATION_EXPOSURE = "INFORMATION_EXPOSURE"


class BeliefSignal(str, Enum):
    AFFIRM = "AFFIRM"
    DENY = "DENY"
    UNCERTAIN = "UNCERTAIN"
    CHALLENGE = "CHALLENGE"


class BeliefStatus(str, Enum):
    AFFIRMED = "AFFIRMED"
    DENIED = "DENIED"
    CHARACTER_UNCERTAIN = "CHARACTER_UNCERTAIN"
    SYSTEM_INSUFFICIENT = "SYSTEM_INSUFFICIENT"
    SUPERSEDED = "SUPERSEDED"
    CONFLICT = "CONFLICT"


DIRECT_KINDS = {
    BeliefEvidenceKind.SELF_REPORT,
    BeliefEvidenceKind.NARRATOR_ASSERTION,
}


@dataclass(frozen=True)
class BeliefEvidenceEvent:
    evidence_id: str
    subject_agent_id: str
    proposition_key: str
    signal: BeliefSignal
    evidence_kind: BeliefEvidenceKind
    valid_time: str
    system_record_time: str
    source_event_id: str
    source_agent_id: str | None = None
    supersedes_proposition_key: str | None = None
    evidence_text: str | None = None

    def __post_init__(self) -> None:
        for name, value in (
            ("evidence_id", self.evidence_id),
            ("subject_agent_id", self.subject_agent_id),
            ("proposition_key", self.proposition_key),
            ("source_event_id", self.source_event_id),
        ):
            if not str(value).strip():
                raise ValueError(f"{name} must not be empty")

        _parse_time(self.valid_time)
        _parse_time(self.system_record_time)

        if self.signal == BeliefSignal.CHALLENGE:
            if self.evidence_kind != BeliefEvidenceKind.INFORMATION_EXPOSURE:
                raise ValueError("CHALLENGE requires INFORMATION_EXPOSURE evidence")
            if self.supersedes_proposition_key is not None:
                raise ValueError("CHALLENGE must not supersede a proposition")
        elif self.evidence_kind == BeliefEvidenceKind.INFORMATION_EXPOSURE:
            raise ValueError(
                "INFORMATION_EXPOSURE is reserved for CHALLENGE; exposure is not belief"
            )

        if self.supersedes_proposition_key is not None:
            if self.signal != BeliefSignal.AFFIRM:
                raise ValueError("only AFFIRM may explicitly supersede a prior belief")
            if self.evidence_kind not in DIRECT_KINDS:
                raise ValueError("belief revision requires direct belief evidence")
            if self.supersedes_proposition_key == self.proposition_key:
                raise ValueError("a proposition cannot supersede itself")

    @property
    def direct(self) -> bool:
        return self.evidence_kind in DIRECT_KINDS


@dataclass(frozen=True)
class CurrentBeliefEstimate:
    subject_agent_id: str
    proposition_key: str
    status: BeliefStatus
    basis_evidence_ids: tuple[str, ...]
    unresolved_challenge_evidence_ids: tuple[str, ...]
    indirect_support_evidence_ids: tuple[str, ...]
    indirect_counter_evidence_ids: tuple[str, ...]
    superseded_by_proposition_key: str | None
    last_valid_time: str | None
    last_system_record_time: str | None

    def as_dict(self) -> dict:
        return {
            "subject_agent_id": self.subject_agent_id,
            "proposition_key": self.proposition_key,
            "status": self.status.value,
            "basis_evidence_ids": list(self.basis_evidence_ids),
            "unresolved_challenge_evidence_ids": list(
                self.unresolved_challenge_evidence_ids
            ),
            "indirect_support_evidence_ids": list(
                self.indirect_support_evidence_ids
            ),
            "indirect_counter_evidence_ids": list(
                self.indirect_counter_evidence_ids
            ),
            "superseded_by_proposition_key": self.superseded_by_proposition_key,
            "last_valid_time": self.last_valid_time,
            "last_system_record_time": self.last_system_record_time,
        }


@dataclass
class _BeliefState:
    status: BeliefStatus = BeliefStatus.SYSTEM_INSUFFICIENT
    basis: list[str] = None
    challenges: list[str] = None
    indirect_support: list[str] = None
    indirect_counter: list[str] = None
    superseded_by: str | None = None
    last_valid_time: str | None = None
    last_system_record_time: str | None = None

    def __post_init__(self) -> None:
        if self.basis is None:
            self.basis = []
        if self.challenges is None:
            self.challenges = []
        if self.indirect_support is None:
            self.indirect_support = []
        if self.indirect_counter is None:
            self.indirect_counter = []


def _sort_key(event: BeliefEvidenceEvent) -> tuple[datetime, datetime, str]:
    return (
        _parse_time(event.valid_time),
        _parse_time(event.system_record_time),
        event.evidence_id,
    )


def _time_key(event: BeliefEvidenceEvent) -> tuple[datetime, datetime]:
    return _parse_time(event.valid_time), _parse_time(event.system_record_time)


def _status_for_signal(signal: BeliefSignal) -> BeliefStatus:
    if signal == BeliefSignal.AFFIRM:
        return BeliefStatus.AFFIRMED
    if signal == BeliefSignal.DENY:
        return BeliefStatus.DENIED
    if signal == BeliefSignal.UNCERTAIN:
        return BeliefStatus.CHARACTER_UNCERTAIN
    raise ValueError(f"no direct status for {signal.value}")


def _apply_batch(
    state: _BeliefState,
    batch: list[BeliefEvidenceEvent],
    *,
    proposition_key: str,
) -> None:
    state.last_valid_time = batch[0].valid_time
    state.last_system_record_time = batch[0].system_record_time

    for event in batch:
        if event.signal == BeliefSignal.CHALLENGE and event.proposition_key == proposition_key:
            state.challenges.append(event.evidence_id)
            continue

        if not event.direct:
            if event.proposition_key != proposition_key:
                continue
            if event.signal == BeliefSignal.AFFIRM:
                state.indirect_support.append(event.evidence_id)
            elif event.signal == BeliefSignal.DENY:
                state.indirect_counter.append(event.evidence_id)
            continue

    superseding = [
        event
        for event in batch
        if event.direct
        and event.signal == BeliefSignal.AFFIRM
        and event.supersedes_proposition_key == proposition_key
    ]
    direct_here = [
        event
        for event in batch
        if event.direct
        and event.proposition_key == proposition_key
        and event.signal != BeliefSignal.CHALLENGE
    ]

    if direct_here:
        distinct = {event.signal for event in direct_here}
        if len(distinct) > 1:
            state.status = BeliefStatus.CONFLICT
            state.basis = [event.evidence_id for event in direct_here]
            state.superseded_by = None
            state.challenges = []
            return

        signal = direct_here[-1].signal
        state.status = _status_for_signal(signal)
        state.basis = [event.evidence_id for event in direct_here]
        state.superseded_by = None
        state.challenges = []
        return

    if superseding:
        targets = {event.proposition_key for event in superseding}
        if len(targets) > 1:
            state.status = BeliefStatus.CONFLICT
            state.basis = [event.evidence_id for event in superseding]
            state.superseded_by = None
            state.challenges = []
            return
        event = superseding[-1]
        state.status = BeliefStatus.SUPERSEDED
        state.basis = [event.evidence_id]
        state.superseded_by = event.proposition_key
        state.challenges = []


def project_belief_estimate(
    events: Iterable[BeliefEvidenceEvent],
    *,
    subject_agent_id: str,
    proposition_key: str,
    visible_source_event_ids: set[str] | frozenset[str] | None = None,
    event_time: str | None = None,
    knowledge_cutoff: str | None = None,
) -> CurrentBeliefEstimate:
    """Project a belief without converting exposure or weak evidence into belief.

    Direct self-report / narrator assertion can establish a current estimate.
    Third-party reports and observed actions remain indirect evidence. Challenge
    exposure is recorded but never changes the current belief by itself.
    """

    relevant: list[BeliefEvidenceEvent] = []
    for event in events:
        if event.subject_agent_id != subject_agent_id:
            continue
        if (
            event.proposition_key != proposition_key
            and event.supersedes_proposition_key != proposition_key
        ):
            continue
        if (
            visible_source_event_ids is not None
            and event.source_event_id not in visible_source_event_ids
        ):
            continue
        if event_time is not None and _parse_time(event.valid_time) > _parse_time(
            event_time
        ):
            continue
        if (
            knowledge_cutoff is not None
            and _parse_time(event.system_record_time) > _parse_time(knowledge_cutoff)
        ):
            continue
        relevant.append(event)

    relevant.sort(key=_sort_key)
    state = _BeliefState()
    for _, group in groupby(relevant, key=_time_key):
        _apply_batch(state, list(group), proposition_key=proposition_key)

    return CurrentBeliefEstimate(
        subject_agent_id=subject_agent_id,
        proposition_key=proposition_key,
        status=state.status,
        basis_evidence_ids=tuple(state.basis),
        unresolved_challenge_evidence_ids=tuple(state.challenges),
        indirect_support_evidence_ids=tuple(state.indirect_support),
        indirect_counter_evidence_ids=tuple(state.indirect_counter),
        superseded_by_proposition_key=state.superseded_by,
        last_valid_time=state.last_valid_time,
        last_system_record_time=state.last_system_record_time,
    )


def project_subject_beliefs(
    events: Iterable[BeliefEvidenceEvent],
    *,
    subject_agent_id: str,
    visible_source_event_ids: set[str] | frozenset[str] | None = None,
    event_time: str | None = None,
    knowledge_cutoff: str | None = None,
) -> tuple[CurrentBeliefEstimate, ...]:
    materialized = tuple(events)
    propositions = sorted(
        {
            proposition
            for event in materialized
            if event.subject_agent_id == subject_agent_id
            for proposition in (
                event.proposition_key,
                event.supersedes_proposition_key,
            )
            if proposition
        }
    )
    return tuple(
        project_belief_estimate(
            materialized,
            subject_agent_id=subject_agent_id,
            proposition_key=proposition,
            visible_source_event_ids=visible_source_event_ids,
            event_time=event_time,
            knowledge_cutoff=knowledge_cutoff,
        )
        for proposition in propositions
    )


__all__ = [
    "BeliefEvidenceEvent",
    "BeliefEvidenceKind",
    "BeliefSignal",
    "BeliefStatus",
    "CurrentBeliefEstimate",
    "DIRECT_KINDS",
    "project_belief_estimate",
    "project_subject_beliefs",
]
