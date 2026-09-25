"""Minimal perspective + belief runtime for HCL v0.6."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Iterable

from hcl.v04.model import EventRecord

from .belief import (
    BeliefEvidenceEvent,
    BeliefEvidenceKind,
    BeliefSignal,
    CurrentBeliefEstimate,
    project_belief_estimate,
    project_subject_beliefs,
)
from .perspective import (
    SYSTEM_VIEWER,
    PerspectiveView,
    bounded_second_order_perspective,
    first_order_perspective,
)
from .semantic import (
    SemanticBackend,
    V06ExtractionResult,
    V06SemanticExtractionError,
    extract_belief_evidence,
)


@dataclass(frozen=True)
class V06IngestResult:
    event_id: str
    belief_evidence: tuple[BeliefEvidenceEvent, ...]
    duplicate: bool
    semantic_repair_count: int
    repair_reason: str | None


@dataclass(frozen=True)
class PerspectiveAnswerContext:
    target_agent_id: str
    observer_agent_id: str | None
    perspective_order: int
    target_information_view: PerspectiveView
    belief_estimates: tuple[CurrentBeliefEstimate, ...]

    def as_dict(self) -> dict:
        return {
            "target_agent_id": self.target_agent_id,
            "observer_agent_id": self.observer_agent_id,
            "perspective_order": self.perspective_order,
            "target_information_view": self.target_information_view.as_dict(),
            "belief_estimates": [x.as_dict() for x in self.belief_estimates],
            "semantic_rules": {
                "information_exposure_is_not_belief_revision": True,
                "system_uncertainty_is_not_character_uncertainty": True,
                "narrator_knowledge_is_not_character_knowledge": True,
                "indirect_evidence_does_not_establish_private_belief": True,
                "partial_or_related_evidence_is_not_precise_knowledge": True,
            },
        }


class HCLV06Runtime:
    """Benchmark-independent minimal human-perspective cognition runtime.

    v0.6 deliberately keeps raw evidence and derived belief evidence separate.
    It does not replace v0.5 persistence. This first capability slice is focused
    on correctness of information boundaries and belief revision semantics.
    """

    def __init__(self) -> None:
        self._events: list[EventRecord] = []
        self._events_by_id: dict[str, EventRecord] = {}
        self._semantic: dict[str, V06ExtractionResult] = {}
        self._semantic_failures: dict[str, str] = {}
        self._prestructured_event_ids: set[str] = set()

    @property
    def events(self) -> tuple[EventRecord, ...]:
        return tuple(self._events)

    @property
    def semantic_failures(self) -> dict[str, str]:
        return dict(self._semantic_failures)

    @property
    def known_agents(self) -> tuple[str, ...]:
        agents: set[str] = set()
        for event in self._events:
            if event.actor_id:
                agents.add(event.actor_id)
            agents.update(event.observer_ids)
            agents.update(event.recipient_ids)
        return tuple(sorted(agents))

    @property
    def known_propositions(self) -> tuple[str, ...]:
        values: set[str] = set()
        for result in self._semantic.values():
            for evidence in result.belief_evidence:
                values.add(evidence.proposition_key)
                if evidence.supersedes_proposition_key:
                    values.add(evidence.supersedes_proposition_key)
            for relation in result.challenge_relations:
                values.add(relation.challenged_proposition_key)
                if relation.alternative_proposition_key:
                    values.add(relation.alternative_proposition_key)
        return tuple(sorted(values))

    def _append_raw_event(self, event: EventRecord) -> bool:
        existing = self._events_by_id.get(event.event_id)
        if existing is not None:
            if existing != event:
                raise ValueError(
                    f"event_id {event.event_id!r} already exists with different content"
                )
            return True
        self._events.append(event)
        self._events_by_id[event.event_id] = event
        return False

    def ingest_prestructured_event(self, event: EventRecord) -> bool:
        """Commit trusted/validated access metadata without belief extraction.

        This is used when an upstream adapter has already converted a transcript
        into immutable EventRecord evidence. It adds real perspective state
        without forcing one model call per utterance. The same event may later
        be semantically enriched through ingest_event.
        """

        duplicate = self._append_raw_event(event)
        if duplicate:
            if event.event_id in self._semantic:
                return True
            if event.event_id in self._semantic_failures:
                raise ValueError(
                    f"event_id {event.event_id!r} has failed semantics; "
                    "reprocess before treating it as clean prestructured evidence"
                )
            self._prestructured_event_ids.add(event.event_id)
            return True
        self._prestructured_event_ids.add(event.event_id)
        return False

    def _extract(
        self,
        event: EventRecord,
        backend: SemanticBackend,
    ) -> V06IngestResult:
        try:
            result = extract_belief_evidence(
                event,
                backend,
                known_propositions=self.known_propositions,
            )
        except Exception as exc:
            self._semantic_failures[event.event_id] = str(exc)
            raise
        self._semantic[event.event_id] = result
        self._semantic_failures.pop(event.event_id, None)
        self._prestructured_event_ids.discard(event.event_id)
        return V06IngestResult(
            event_id=event.event_id,
            belief_evidence=result.belief_evidence,
            duplicate=False,
            semantic_repair_count=result.repair_count,
            repair_reason=result.repair_reason,
        )

    def ingest_event(
        self,
        event: EventRecord,
        backend: SemanticBackend,
    ) -> V06IngestResult:
        duplicate = self._append_raw_event(event)
        if duplicate:
            if event.event_id in self._semantic:
                result = self._semantic[event.event_id]
                return V06IngestResult(
                    event_id=event.event_id,
                    belief_evidence=result.belief_evidence,
                    duplicate=True,
                    semantic_repair_count=0,
                    repair_reason=None,
                )
            if event.event_id in self._semantic_failures:
                raise ValueError(
                    f"event_id {event.event_id!r} is preserved but v0.6 semantics "
                    "failed; use reprocess_event"
                )
            if event.event_id in self._prestructured_event_ids:
                return self._extract(event, backend)
            raise ValueError(
                f"event_id {event.event_id!r} exists without v0.6 semantics"
            )
        return self._extract(event, backend)

    def reprocess_event(
        self,
        event_id: str,
        backend: SemanticBackend,
    ) -> V06IngestResult:
        if event_id not in self._events_by_id:
            raise KeyError(event_id)
        if event_id in self._semantic:
            raise ValueError(f"event_id {event_id!r} already has committed v0.6 semantics")
        if event_id not in self._semantic_failures:
            raise ValueError(f"event_id {event_id!r} has no failed semantics to reprocess")
        return self._extract(self._events_by_id[event_id], backend)

    @staticmethod
    def _challenge_id(
        source_event_id: str,
        subject_agent_id: str,
        proposition_key: str,
    ) -> str:
        raw = f"{source_event_id}|{subject_agent_id}|{proposition_key}|CHALLENGE"
        return "belief_" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:20]

    def _challenge_targets(self, event: EventRecord) -> tuple[str, ...]:
        explicit = set(event.observer_ids) | set(event.recipient_ids)
        override = event.metadata.get("challenge_target_ids")
        if isinstance(override, (list, tuple)):
            explicit &= {str(x) for x in override}

        if bool(event.metadata.get("public")):
            explicit.update(self.known_agents)

        # Speaking a challenge does not by itself mean the speaker's own belief
        # was challenged. Include actor only when explicitly listed.
        if (
            event.actor_id
            and event.actor_id not in event.observer_ids
            and event.actor_id not in event.recipient_ids
        ):
            explicit.discard(event.actor_id)

        return tuple(sorted(x for x in explicit if x))

    @property
    def belief_evidence(self) -> tuple[BeliefEvidenceEvent, ...]:
        evidence: list[BeliefEvidenceEvent] = []
        for event in self._events:
            result = self._semantic.get(event.event_id)
            if result is None:
                continue
            evidence.extend(result.belief_evidence)
            for relation in result.challenge_relations:
                for subject in self._challenge_targets(event):
                    evidence.append(
                        BeliefEvidenceEvent(
                            evidence_id=self._challenge_id(
                                event.event_id,
                                subject,
                                relation.challenged_proposition_key,
                            ),
                            subject_agent_id=subject,
                            proposition_key=relation.challenged_proposition_key,
                            signal=BeliefSignal.CHALLENGE,
                            evidence_kind=BeliefEvidenceKind.INFORMATION_EXPOSURE,
                            valid_time=event.valid_time,
                            system_record_time=event.recorded_at,
                            source_event_id=event.event_id,
                            source_agent_id=event.actor_id or event.source_id,
                            evidence_text=(
                                None
                                if relation.alternative_proposition_key is None
                                else "alternative:"
                                + relation.alternative_proposition_key
                            ),
                        )
                    )
        return tuple(evidence)

    def perspective_view(
        self,
        target_agent_id: str,
        *,
        event_time: str | None = None,
        knowledge_cutoff: str | None = None,
    ) -> PerspectiveView:
        return first_order_perspective(
            self._events,
            target_agent_id=target_agent_id,
            event_time=event_time,
            knowledge_cutoff=knowledge_cutoff,
        )

    def second_order_view(
        self,
        viewer_agent_id: str,
        target_agent_id: str,
        *,
        event_time: str | None = None,
        knowledge_cutoff: str | None = None,
    ) -> PerspectiveView:
        return bounded_second_order_perspective(
            self._events,
            viewer_agent_id=viewer_agent_id,
            target_agent_id=target_agent_id,
            event_time=event_time,
            knowledge_cutoff=knowledge_cutoff,
        )

    def belief_estimate(
        self,
        subject_agent_id: str,
        proposition_key: str,
        *,
        viewer_agent_id: str = SYSTEM_VIEWER,
        event_time: str | None = None,
        knowledge_cutoff: str | None = None,
    ) -> CurrentBeliefEstimate:
        if viewer_agent_id == SYSTEM_VIEWER:
            visible = {event.event_id for event in self._events}
        else:
            visible = set(
                self.perspective_view(
                    viewer_agent_id,
                    event_time=event_time,
                    knowledge_cutoff=knowledge_cutoff,
                ).event_ids
            )
        return project_belief_estimate(
            self.belief_evidence,
            subject_agent_id=subject_agent_id,
            proposition_key=proposition_key,
            visible_source_event_ids=visible,
            event_time=event_time,
            knowledge_cutoff=knowledge_cutoff,
        )

    def subject_beliefs(
        self,
        subject_agent_id: str,
        *,
        viewer_agent_id: str = SYSTEM_VIEWER,
        event_time: str | None = None,
        knowledge_cutoff: str | None = None,
    ) -> tuple[CurrentBeliefEstimate, ...]:
        if viewer_agent_id == SYSTEM_VIEWER:
            visible = {event.event_id for event in self._events}
        else:
            visible = set(
                self.perspective_view(
                    viewer_agent_id,
                    event_time=event_time,
                    knowledge_cutoff=knowledge_cutoff,
                ).event_ids
            )
        return project_subject_beliefs(
            self.belief_evidence,
            subject_agent_id=subject_agent_id,
            visible_source_event_ids=visible,
            event_time=event_time,
            knowledge_cutoff=knowledge_cutoff,
        )

    def answer_context(
        self,
        target_agent_id: str,
        *,
        observer_agent_id: str | None = None,
        event_time: str | None = None,
        knowledge_cutoff: str | None = None,
    ) -> PerspectiveAnswerContext:
        """Build an evidence-bounded context for first/second-order answering."""

        if observer_agent_id is None or observer_agent_id == target_agent_id:
            information_view = self.perspective_view(
                target_agent_id,
                event_time=event_time,
                knowledge_cutoff=knowledge_cutoff,
            )
            # Raw narrator/reader-only facts must not enter the character's
            # information view. Direct narrator evidence *about the character's
            # belief*, however, is evidence available to the external HCL
            # system when modeling that character. Keep these channels separate.
            observer_for_beliefs = SYSTEM_VIEWER
            order = 1
        else:
            information_view = self.second_order_view(
                observer_agent_id,
                target_agent_id,
                event_time=event_time,
                knowledge_cutoff=knowledge_cutoff,
            )
            observer_for_beliefs = observer_agent_id
            order = 2

        beliefs = self.subject_beliefs(
            target_agent_id,
            viewer_agent_id=observer_for_beliefs,
            event_time=event_time,
            knowledge_cutoff=knowledge_cutoff,
        )
        return PerspectiveAnswerContext(
            target_agent_id=target_agent_id,
            observer_agent_id=observer_agent_id,
            perspective_order=order,
            target_information_view=information_view,
            belief_estimates=beliefs,
        )

    def global_perspective_context(
        self,
        *,
        event_time: str | None = None,
        knowledge_cutoff: str | None = None,
    ) -> dict:
        """Question-independent perspective state for a whole interaction.

        The context is constructed before a downstream question is released.
        It exposes each character's own bounded evidence separately and a
        pairwise access matrix containing only event IDs for bounded second-order
        reasoning. It does not collapse all private evidence into one world view.
        """

        agents = self.known_agents
        first_order = {
            agent: self.perspective_view(
                agent,
                event_time=event_time,
                knowledge_cutoff=knowledge_cutoff,
            ).as_dict()
            for agent in agents
        }
        second_order = {
            viewer: {
                target: list(
                    self.second_order_view(
                        viewer,
                        target,
                        event_time=event_time,
                        knowledge_cutoff=knowledge_cutoff,
                    ).event_ids
                )
                for target in agents
                if target != viewer
            }
            for viewer in agents
        }
        system_beliefs = {
            agent: [
                estimate.as_dict()
                for estimate in self.subject_beliefs(
                    agent,
                    viewer_agent_id=SYSTEM_VIEWER,
                    event_time=event_time,
                    knowledge_cutoff=knowledge_cutoff,
                )
            ]
            for agent in agents
        }
        return {
            "agents": list(agents),
            "first_order_views": first_order,
            "second_order_access_event_ids": second_order,
            "system_belief_estimates": system_beliefs,
            "semantic_rules": {
                "views_are_not_interchangeable": True,
                "information_exposure_is_not_belief_acceptance": True,
                "system_uncertainty_is_not_character_uncertainty": True,
                "reader_narrator_information_does_not_leak_to_characters": True,
                "partial_or_related_evidence_is_not_precise_knowledge": True,
            },
        }

    def answer_messages(
        self,
        question: str,
        *,
        target_agent_id: str,
        observer_agent_id: str | None = None,
        event_time: str | None = None,
        knowledge_cutoff: str | None = None,
    ) -> list[dict[str, str]]:
        """Messages for a base model to answer from the bounded perspective."""

        if not question.strip():
            raise ValueError("question must not be empty")
        context = self.answer_context(
            target_agent_id,
            observer_agent_id=observer_agent_id,
            event_time=event_time,
            knowledge_cutoff=knowledge_cutoff,
        )
        system = (
            "Answer using only the supplied HCL perspective context. "
            "Do not use narrator/world facts outside target_information_view. "
            "Information exposure does not imply belief acceptance. "
            "SYSTEM_INSUFFICIENT means the evidence is insufficient to know the "
            "character's belief; it does not mean the character is uncertain. "
            "Indirect reports/actions are evidence, not private-belief truth. "
            "A related topic or partial summary is not the same as knowing a "
            "precise compound fact: require support for every material detail "
            "before treating precise information as known. "
            "If the bounded evidence cannot answer the question, say that the "
            "available evidence is insufficient."
        )
        user = json.dumps(
            {
                "question": question,
                "hcl_perspective_context": context.as_dict(),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
        return [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]


__all__ = [
    "HCLV06Runtime",
    "PerspectiveAnswerContext",
    "V06IngestResult",
    "V06SemanticExtractionError",
]
