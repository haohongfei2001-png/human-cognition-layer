"""Minimal event-to-current-stance runtime for HCL v0.5."""

from __future__ import annotations

from dataclasses import dataclass

from hcl.v04.model import EventRecord

from .semantic import (
    ExtractionResult,
    SemanticBackend,
    catalog_from_events,
    extract_stance_events,
)
from .stance import (
    CurrentStance,
    StanceEvent,
    project_all_current_stances,
    project_current_stance,
)


@dataclass(frozen=True)
class V05IngestResult:
    event_id: str
    stance_events: tuple[StanceEvent, ...]
    duplicate: bool
    semantic_repair_count: int
    repair_reason: str | None


class HCLV05Runtime:
    """Provider boundary + deterministic stance state.

    Raw events are immutable source records. The semantic backend only extracts
    event-local stance signals; current stance is always computed by the
    deterministic projector.
    """

    def __init__(self) -> None:
        self._events: dict[str, EventRecord] = {}
        self._stance_events: list[StanceEvent] = []
        self._stance_by_source_event: dict[str, tuple[StanceEvent, ...]] = {}

    @property
    def events(self) -> tuple[EventRecord, ...]:
        return tuple(self._events.values())

    @property
    def stance_events(self) -> tuple[StanceEvent, ...]:
        return tuple(self._stance_events)

    def ingest_event(
        self,
        event: EventRecord,
        backend: SemanticBackend,
    ) -> V05IngestResult:
        existing = self._events.get(event.event_id)
        if existing is not None:
            if existing != event:
                raise ValueError(
                    f"event_id {event.event_id!r} already exists with different content"
                )
            return V05IngestResult(
                event_id=event.event_id,
                stance_events=self._stance_by_source_event[event.event_id],
                duplicate=True,
                semantic_repair_count=0,
                repair_reason=None,
            )

        extraction: ExtractionResult = extract_stance_events(
            event,
            backend,
            known_catalog=catalog_from_events(tuple(self._stance_events)),
        )
        self._events[event.event_id] = event
        self._stance_events.extend(extraction.stance_events)
        self._stance_by_source_event[event.event_id] = extraction.stance_events
        return V05IngestResult(
            event_id=event.event_id,
            stance_events=extraction.stance_events,
            duplicate=False,
            semantic_repair_count=extraction.repair_count,
            repair_reason=extraction.repair_reason,
        )

    def current_stance(
        self,
        subject_agent_id: str,
        issue_key: str,
        *,
        event_time: str | None = None,
        knowledge_cutoff: str | None = None,
    ) -> CurrentStance:
        return project_current_stance(
            self._stance_events,
            subject_agent_id=subject_agent_id,
            issue_key=issue_key,
            event_time=event_time,
            knowledge_cutoff=knowledge_cutoff,
        )

    def all_current_stances(
        self,
        *,
        event_time: str | None = None,
        knowledge_cutoff: str | None = None,
    ) -> tuple[CurrentStance, ...]:
        return project_all_current_stances(
            self._stance_events,
            event_time=event_time,
            knowledge_cutoff=knowledge_cutoff,
        )


__all__ = ["HCLV05Runtime", "V05IngestResult"]
