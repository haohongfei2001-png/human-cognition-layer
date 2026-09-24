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
from .store import V05Store
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
    """Provider boundary + deterministic stance state over a persistent store.

    Raw events are immutable source records. The semantic backend only extracts
    event-local stance signals; current stance is always computed by the
    deterministic projector.
    """

    def __init__(self, store: V05Store | None = None, *, path: str = ":memory:") -> None:
        if store is not None and path != ":memory:":
            raise ValueError("provide either store or path, not both")
        self.store = store or V05Store(path)

    def close(self) -> None:
        self.store.close()

    @property
    def events(self) -> tuple[EventRecord, ...]:
        return self.store.list_events()

    @property
    def stance_events(self) -> tuple[StanceEvent, ...]:
        return self.store.all_stance_events()

    @property
    def semantic_failures(self) -> dict[str, str]:
        return self.store.semantic_failures()

    def _extract_and_commit(
        self,
        event: EventRecord,
        backend: SemanticBackend,
    ) -> V05IngestResult:
        try:
            extraction: ExtractionResult = extract_stance_events(
                event,
                backend,
                known_catalog=catalog_from_events(self.store.all_stance_events()),
            )
        except Exception as exc:
            self.store.record_semantic_failure(event.event_id, str(exc))
            raise

        self.store.commit_semantics(
            event.event_id,
            extraction.stance_events,
            repair_count=extraction.repair_count,
            repair_reason=extraction.repair_reason,
        )
        return V05IngestResult(
            event_id=event.event_id,
            stance_events=extraction.stance_events,
            duplicate=False,
            semantic_repair_count=extraction.repair_count,
            repair_reason=extraction.repair_reason,
        )

    def ingest_event(
        self,
        event: EventRecord,
        backend: SemanticBackend,
    ) -> V05IngestResult:
        duplicate = self.store.append_event(event)
        if duplicate:
            status = self.store.semantic_status(event.event_id)
            if status == "COMMITTED":
                return V05IngestResult(
                    event_id=event.event_id,
                    stance_events=self.store.stance_events_for_source(event.event_id),
                    duplicate=True,
                    semantic_repair_count=0,
                    repair_reason=None,
                )
            if status in {"FAILED", "INVALIDATED"}:
                raise ValueError(
                    f"event_id {event.event_id!r} is preserved but semantic state "
                    f"is {status}; use reprocess_event"
                )
            raise ValueError(
                f"event_id {event.event_id!r} exists without a semantic receipt"
            )

        # Raw evidence was transactionally committed before semantic extraction.
        return self._extract_and_commit(event, backend)

    def reprocess_event(
        self,
        event_id: str,
        backend: SemanticBackend,
    ) -> V05IngestResult:
        event = self.store.get_event(event_id)
        status = self.store.semantic_status(event_id)
        if status == "COMMITTED":
            raise ValueError(
                f"event_id {event_id!r} already has committed stance semantics"
            )
        if status not in {"FAILED", "INVALIDATED"}:
            raise ValueError(
                f"event_id {event_id!r} has no failed/invalidated semantics to reprocess"
            )
        return self._extract_and_commit(event, backend)

    def invalidate_semantics(self, event_id: str, reason: str) -> None:
        self.store.invalidate_semantics(event_id, reason)

    def current_stance(
        self,
        subject_agent_id: str,
        issue_key: str,
        *,
        event_time: str | None = None,
        knowledge_cutoff: str | None = None,
    ) -> CurrentStance:
        return project_current_stance(
            self.store.all_stance_events(),
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
            self.store.all_stance_events(),
            event_time=event_time,
            knowledge_cutoff=knowledge_cutoff,
        )


__all__ = ["HCLV05Runtime", "V05IngestResult"]
