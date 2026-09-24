"""Issue-centered current stance core for HCL v0.5."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from itertools import groupby
from typing import Iterable


def _parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


class StanceSignal(str, Enum):
    AFFIRM = "AFFIRM"
    DENY = "DENY"
    REVISION_EXPOSURE = "REVISION_EXPOSURE"
    UNRESOLVED = "UNRESOLVED"


class StanceStatus(str, Enum):
    AFFIRMED = "AFFIRMED"
    UNRESOLVED = "UNRESOLVED"
    NO_AFFIRMED_VALUE = "NO_AFFIRMED_VALUE"
    CONFLICT = "CONFLICT"


@dataclass(frozen=True)
class StanceEvent:
    event_id: str
    subject_agent_id: str
    issue_key: str
    signal: StanceSignal
    valid_time: str
    system_record_time: str
    value_key: str | None = None
    prior_value_key: str | None = None
    evidence_event_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.event_id.strip():
            raise ValueError("event_id must not be empty")
        if not self.subject_agent_id.strip():
            raise ValueError("subject_agent_id must not be empty")
        if not self.issue_key.strip():
            raise ValueError("issue_key must not be empty")
        _parse_time(self.valid_time)
        _parse_time(self.system_record_time)

        if self.signal in {
            StanceSignal.AFFIRM,
            StanceSignal.DENY,
            StanceSignal.UNRESOLVED,
        } and not self.value_key:
            raise ValueError(f"{self.signal.value} requires value_key")

        if self.signal == StanceSignal.REVISION_EXPOSURE:
            if not self.value_key or not self.prior_value_key:
                raise ValueError(
                    "REVISION_EXPOSURE requires value_key and prior_value_key"
                )
            if self.value_key == self.prior_value_key:
                raise ValueError("revision values must differ")


@dataclass(frozen=True)
class CurrentStance:
    subject_agent_id: str
    issue_key: str
    status: StanceStatus
    affirmed_value_key: str | None
    rejected_value_keys: tuple[str, ...]
    pending_revision_value_key: str | None
    suspended_value_key: str | None
    last_valid_time: str | None
    last_system_record_time: str | None
    support_event_ids: tuple[str, ...]
    transition_event_ids: tuple[str, ...]

    def as_dict(self) -> dict:
        return {
            "subject_agent_id": self.subject_agent_id,
            "issue_key": self.issue_key,
            "status": self.status.value,
            "affirmed_value_key": self.affirmed_value_key,
            "rejected_value_keys": list(self.rejected_value_keys),
            "pending_revision_value_key": self.pending_revision_value_key,
            "suspended_value_key": self.suspended_value_key,
            "last_valid_time": self.last_valid_time,
            "last_system_record_time": self.last_system_record_time,
            "support_event_ids": list(self.support_event_ids),
            "transition_event_ids": list(self.transition_event_ids),
        }


@dataclass
class _MutableState:
    accepted: str | None = None
    rejected: set[str] = None
    pending: str | None = None
    suspended: str | None = None
    conflict: bool = False
    last_valid_time: str | None = None
    last_system_record_time: str | None = None
    support_event_ids: set[str] = None
    transition_event_ids: list[str] = None

    def __post_init__(self) -> None:
        if self.rejected is None:
            self.rejected = set()
        if self.support_event_ids is None:
            self.support_event_ids = set()
        if self.transition_event_ids is None:
            self.transition_event_ids = []


def _time_key(event: StanceEvent) -> tuple[datetime, datetime]:
    return _parse_time(event.valid_time), _parse_time(event.system_record_time)


def _event_sort_key(event: StanceEvent) -> tuple[datetime, datetime, str]:
    return (*_time_key(event), event.event_id)


def _apply_batch(state: _MutableState, batch: list[StanceEvent]) -> None:
    state.last_valid_time = batch[0].valid_time
    state.last_system_record_time = batch[0].system_record_time
    for event in batch:
        state.transition_event_ids.append(event.event_id)
        state.support_event_ids.update(event.evidence_event_ids or (event.event_id,))

    affirms = {e.value_key for e in batch if e.signal == StanceSignal.AFFIRM}
    denies = {e.value_key for e in batch if e.signal == StanceSignal.DENY}
    unresolved_values = [
        e.value_key for e in batch if e.signal == StanceSignal.UNRESOLVED
    ]
    revisions = [
        e for e in batch if e.signal == StanceSignal.REVISION_EXPOSURE
    ]

    # Explicit stance at a timestamp outranks receipt-only uncertainty at the
    # same timestamp. Multiple different affirmative values fail closed.
    if len(affirms) > 1:
        state.accepted = None
        state.pending = None
        state.suspended = None
        state.conflict = True
        state.rejected.update(v for v in denies if v)
        return

    affirmed = next(iter(affirms), None)
    if affirmed is not None and affirmed in denies:
        state.accepted = None
        state.pending = None
        state.suspended = None
        state.conflict = True
        state.rejected.add(affirmed)
        return

    if affirmed is not None:
        state.accepted = affirmed
        state.pending = None
        state.suspended = None
        state.conflict = False
        state.rejected.discard(affirmed)

    state.rejected.update(v for v in denies if v)

    # A rejection of the pending candidate restores the stance that was
    # suspended by receipt of that revision, unless this same batch contains a
    # new affirmative stance.
    if affirmed is None and state.pending and state.pending in denies:
        state.accepted = state.suspended
        state.pending = None
        state.suspended = None
        state.conflict = False

    # Denying the currently affirmed value without affirming an alternative
    # leaves no positive current value.
    if affirmed is None and state.accepted in denies:
        state.accepted = None

    has_explicit_stance = bool(affirms or denies)
    if not has_explicit_stance:
        for revision in revisions:
            new_value = revision.value_key
            old_value = revision.prior_value_key

            # Confirmation of a revision the agent already accepts is
            # informationally redundant and must not reopen uncertainty.
            if state.accepted == new_value:
                continue

            # If the agent currently accepts the revision's old value (or some
            # other value on this issue), receipt suspends that commitment
            # until an explicit stance resolves the revision.
            if state.pending != new_value:
                state.suspended = state.accepted
            state.accepted = None
            state.pending = new_value
            state.conflict = False

        if unresolved_values:
            new_value = unresolved_values[-1]
            if state.pending != new_value:
                state.suspended = state.accepted
            state.accepted = None
            state.pending = new_value
            state.conflict = False


def project_current_stance(
    events: Iterable[StanceEvent],
    *,
    subject_agent_id: str,
    issue_key: str,
    event_time: str | None = None,
    knowledge_cutoff: str | None = None,
) -> CurrentStance:
    relevant = []
    for event in events:
        if event.subject_agent_id != subject_agent_id or event.issue_key != issue_key:
            continue
        if event_time is not None and _parse_time(event.valid_time) > _parse_time(event_time):
            continue
        if (
            knowledge_cutoff is not None
            and _parse_time(event.system_record_time) > _parse_time(knowledge_cutoff)
        ):
            continue
        relevant.append(event)

    relevant.sort(key=_event_sort_key)
    state = _MutableState()
    for _, group in groupby(relevant, key=_time_key):
        _apply_batch(state, list(group))

    if state.conflict:
        status = StanceStatus.CONFLICT
    elif state.pending is not None:
        status = StanceStatus.UNRESOLVED
    elif state.accepted is not None:
        status = StanceStatus.AFFIRMED
    else:
        status = StanceStatus.NO_AFFIRMED_VALUE

    return CurrentStance(
        subject_agent_id=subject_agent_id,
        issue_key=issue_key,
        status=status,
        affirmed_value_key=state.accepted,
        rejected_value_keys=tuple(sorted(state.rejected)),
        pending_revision_value_key=state.pending,
        suspended_value_key=state.suspended,
        last_valid_time=state.last_valid_time,
        last_system_record_time=state.last_system_record_time,
        support_event_ids=tuple(sorted(state.support_event_ids)),
        transition_event_ids=tuple(state.transition_event_ids),
    )


def project_all_current_stances(
    events: Iterable[StanceEvent],
    *,
    event_time: str | None = None,
    knowledge_cutoff: str | None = None,
) -> tuple[CurrentStance, ...]:
    materialized = tuple(events)
    keys = sorted(
        {(event.subject_agent_id, event.issue_key) for event in materialized}
    )
    return tuple(
        project_current_stance(
            materialized,
            subject_agent_id=subject,
            issue_key=issue,
            event_time=event_time,
            knowledge_cutoff=knowledge_cutoff,
        )
        for subject, issue in keys
    )


__all__ = [
    "CurrentStance",
    "StanceEvent",
    "StanceSignal",
    "StanceStatus",
    "project_all_current_stances",
    "project_current_stance",
]
