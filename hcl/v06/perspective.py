"""Evidence-bounded first- and second-order perspective views for HCL v0.6."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable

from hcl.v04.model import EventRecord

SYSTEM_VIEWER = "__hcl_system_reader__"


def _parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _within_cutoff(
    event: EventRecord,
    *,
    event_time: str | None,
    knowledge_cutoff: str | None,
) -> bool:
    if event_time is not None and _parse_time(event.valid_time) > _parse_time(event_time):
        return False
    if knowledge_cutoff is not None and _parse_time(event.recorded_at) > _parse_time(
        knowledge_cutoff
    ):
        return False
    return True


def event_accessible_to(event: EventRecord, viewer_agent_id: str) -> bool:
    """Return whether the viewer directly has this raw event as evidence.

    SYSTEM_VIEWER is the external reader/system and can inspect all stored raw
    evidence. Characters do not inherit narrator/reader-only information unless
    the event also carries an explicit access path to them.
    """

    if viewer_agent_id == SYSTEM_VIEWER:
        return True

    if bool(event.metadata.get("reader_only")):
        return False

    if bool(event.metadata.get("public")):
        return True

    return bool(
        event.actor_id == viewer_agent_id
        or viewer_agent_id in event.observer_ids
        or viewer_agent_id in event.recipient_ids
    )


def viewer_can_establish_target_access(
    event: EventRecord,
    *,
    viewer_agent_id: str,
    target_agent_id: str,
) -> bool:
    """Whether viewer has evidence that target had access to this event.

    This deliberately requires two things:
    1. the viewer can inspect the event/access metadata; and
    2. the target has an explicit access path (or the event is public).

    It does not infer hidden communication, shared background knowledge, or
    mental-state transfer.
    """

    if viewer_agent_id == SYSTEM_VIEWER:
        viewer_has_event = True
    else:
        viewer_has_event = event_accessible_to(event, viewer_agent_id)

    if not viewer_has_event:
        return False

    if bool(event.metadata.get("reader_only")):
        return False

    if bool(event.metadata.get("public")):
        return True

    return bool(
        event.actor_id == target_agent_id
        or target_agent_id in event.observer_ids
        or target_agent_id in event.recipient_ids
    )


@dataclass(frozen=True)
class PerspectiveView:
    viewer_agent_id: str
    target_agent_id: str
    order: int
    event_ids: tuple[str, ...]
    events: tuple[EventRecord, ...]
    event_time: str | None
    knowledge_cutoff: str | None

    def as_dict(self) -> dict:
        return {
            "viewer_agent_id": self.viewer_agent_id,
            "target_agent_id": self.target_agent_id,
            "order": self.order,
            "event_ids": list(self.event_ids),
            "event_time": self.event_time,
            "knowledge_cutoff": self.knowledge_cutoff,
            "events": [
                {
                    "event_id": e.event_id,
                    "valid_time": e.valid_time,
                    "recorded_at": e.recorded_at,
                    "source_id": e.source_id,
                    "actor_id": e.actor_id,
                    "observer_ids": list(e.observer_ids),
                    "recipient_ids": list(e.recipient_ids),
                    "raw_text": e.raw_text,
                    "metadata": dict(e.metadata),
                }
                for e in self.events
            ],
        }


def first_order_perspective(
    events: Iterable[EventRecord],
    *,
    target_agent_id: str,
    event_time: str | None = None,
    knowledge_cutoff: str | None = None,
) -> PerspectiveView:
    """Evidence directly available to the target character."""

    materialized = [
        event
        for event in events
        if _within_cutoff(
            event, event_time=event_time, knowledge_cutoff=knowledge_cutoff
        )
        and event_accessible_to(event, target_agent_id)
    ]
    materialized.sort(
        key=lambda e: (_parse_time(e.valid_time), _parse_time(e.recorded_at), e.event_id)
    )
    return PerspectiveView(
        viewer_agent_id=target_agent_id,
        target_agent_id=target_agent_id,
        order=1,
        event_ids=tuple(e.event_id for e in materialized),
        events=tuple(materialized),
        event_time=event_time,
        knowledge_cutoff=knowledge_cutoff,
    )


def bounded_second_order_perspective(
    events: Iterable[EventRecord],
    *,
    viewer_agent_id: str,
    target_agent_id: str,
    event_time: str | None = None,
    knowledge_cutoff: str | None = None,
) -> PerspectiveView:
    """Evidence the viewer can establish was available to the target.

    This is a bounded second-order view: "according to A's evidence, what did B
    have access to?" It is intentionally not recursive beyond this level.
    """

    materialized = [
        event
        for event in events
        if _within_cutoff(
            event, event_time=event_time, knowledge_cutoff=knowledge_cutoff
        )
        and viewer_can_establish_target_access(
            event,
            viewer_agent_id=viewer_agent_id,
            target_agent_id=target_agent_id,
        )
    ]
    materialized.sort(
        key=lambda e: (_parse_time(e.valid_time), _parse_time(e.recorded_at), e.event_id)
    )
    return PerspectiveView(
        viewer_agent_id=viewer_agent_id,
        target_agent_id=target_agent_id,
        order=2,
        event_ids=tuple(e.event_id for e in materialized),
        events=tuple(materialized),
        event_time=event_time,
        knowledge_cutoff=knowledge_cutoff,
    )


__all__ = [
    "SYSTEM_VIEWER",
    "PerspectiveView",
    "bounded_second_order_perspective",
    "event_accessible_to",
    "first_order_perspective",
    "viewer_can_establish_target_access",
]
