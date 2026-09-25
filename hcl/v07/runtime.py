"""Minimal evidence-constrained intention, goal and action runtime.

The input is typed evidence anchored to immutable EventRecord objects. Semantic
extraction remains a separate adapter; this layer never converts an observed
action or another person's attribution into a certain private intention.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from hcl.v04.model import EventRecord
from hcl.v06 import HCLV06Runtime, SYSTEM_VIEWER
from hcl.v06.belief import BeliefEvidenceKind


class IntentionSignal(str, Enum):
    EXPLICIT_INTENTION = "EXPLICIT_INTENTION"
    EXPLICIT_GOAL = "EXPLICIT_GOAL"
    OBSERVED_ACTION = "OBSERVED_ACTION"
    INFERRED_MOTIVATION = "INFERRED_MOTIVATION"
    THIRD_PARTY_ATTRIBUTION = "THIRD_PARTY_ATTRIBUTION"
    SUPPORT = "SUPPORT"
    COUNTEREVIDENCE = "COUNTEREVIDENCE"
    EXPLICIT_REVISION = "EXPLICIT_REVISION"
    EXPLICIT_ABANDONMENT = "EXPLICIT_ABANDONMENT"
    EXPLICIT_COMPLETION = "EXPLICIT_COMPLETION"
    CHARACTER_UNCERTAIN = "CHARACTER_UNCERTAIN"


class GoalStatus(str, Enum):
    ACTIVE = "ACTIVE"
    UNRESOLVED = "UNRESOLVED"
    COMPLETED = "COMPLETED"
    ABANDONED = "ABANDONED"
    REVISED = "REVISED"
    CHARACTER_UNCERTAIN = "CHARACTER_UNCERTAIN"
    SYSTEM_INSUFFICIENT = "SYSTEM_INSUFFICIENT"


DIRECT = {BeliefEvidenceKind.SELF_REPORT, BeliefEvidenceKind.NARRATOR_ASSERTION}
DIRECT_SIGNALS = {
    IntentionSignal.EXPLICIT_INTENTION, IntentionSignal.EXPLICIT_GOAL,
    IntentionSignal.EXPLICIT_REVISION, IntentionSignal.EXPLICIT_ABANDONMENT,
    IntentionSignal.EXPLICIT_COMPLETION, IntentionSignal.CHARACTER_UNCERTAIN,
}


@dataclass(frozen=True)
class IntentionEvidenceEvent:
    evidence_id: str
    source_event_id: str
    subject_agent_id: str
    goal_key: str
    signal: IntentionSignal
    provenance: BeliefEvidenceKind
    valid_time: str
    system_record_time: str
    evidence_text: str
    supersedes_goal_key: str | None = None

    def __post_init__(self) -> None:
        for name in ("evidence_id", "source_event_id", "subject_agent_id", "goal_key", "evidence_text"):
            if not str(getattr(self, name)).strip():
                raise ValueError(f"{name} must not be empty")
        datetime.fromisoformat(self.valid_time.replace("Z", "+00:00"))
        datetime.fromisoformat(self.system_record_time.replace("Z", "+00:00"))
        if self.signal in DIRECT_SIGNALS and self.provenance not in DIRECT:
            raise ValueError("private intention/goal transitions require direct evidence")
        if self.signal == IntentionSignal.OBSERVED_ACTION and self.provenance != BeliefEvidenceKind.OBSERVED_ACTION:
            raise ValueError("action evidence requires observed-action provenance")
        if self.signal == IntentionSignal.THIRD_PARTY_ATTRIBUTION and self.provenance != BeliefEvidenceKind.THIRD_PARTY_REPORT:
            raise ValueError("third-party attribution must preserve its source")
        if self.signal == IntentionSignal.INFERRED_MOTIVATION and self.provenance in DIRECT:
            raise ValueError("directly stated motives are not inferred motives")
        if self.signal == IntentionSignal.EXPLICIT_REVISION:
            if not self.supersedes_goal_key or self.supersedes_goal_key == self.goal_key:
                raise ValueError("revision requires a distinct prior goal")
        elif self.supersedes_goal_key is not None:
            raise ValueError("only explicit revision may supersede a goal")

    def as_dict(self) -> dict:
        return {
            "evidence_id": self.evidence_id,
            "source_event_id": self.source_event_id,
            "subject_agent_id": self.subject_agent_id,
            "goal_key": self.goal_key,
            "signal": self.signal.value,
            "provenance": self.provenance.value,
            "valid_time": self.valid_time,
            "system_record_time": self.system_record_time,
            "evidence_text": self.evidence_text,
            "supersedes_goal_key": self.supersedes_goal_key,
        }


@dataclass(frozen=True)
class GoalEstimate:
    subject_agent_id: str
    goal_key: str
    status: GoalStatus
    direct_evidence_ids: tuple[str, ...]
    action_evidence_ids: tuple[str, ...]
    inferred_motivation_ids: tuple[str, ...]
    third_party_attribution_ids: tuple[str, ...]
    support_evidence_ids: tuple[str, ...]
    counterevidence_ids: tuple[str, ...]
    character_uncertainty_ids: tuple[str, ...]
    revised_by_goal_key: str | None

    def as_dict(self) -> dict:
        result = dict(self.__dict__)
        result["status"] = self.status.value
        for key, value in result.items():
            if isinstance(value, tuple):
                result[key] = list(value)
        return result


class HCLV07Runtime:
    """Wrap v0.6 perspective evidence rather than rebuilding access semantics."""

    def __init__(self) -> None:
        self.perspectives = HCLV06Runtime()
        self._evidence: dict[str, IntentionEvidenceEvent] = {}

    def ingest_event(self, event: EventRecord) -> bool:
        return self.perspectives.ingest_prestructured_event(event)

    def ingest_intention_evidence(self, evidence: IntentionEvidenceEvent) -> bool:
        source = {event.event_id: event for event in self.perspectives.events}.get(evidence.source_event_id)
        if source is None:
            raise ValueError("intention evidence must cite an ingested source event")
        if evidence.valid_time != source.valid_time or evidence.system_record_time != source.recorded_at:
            raise ValueError("intention evidence chronology must match its source event")
        if evidence.provenance == BeliefEvidenceKind.SELF_REPORT and source.actor_id != evidence.subject_agent_id:
            raise ValueError("self-report source actor must be the subject")
        if evidence.provenance == BeliefEvidenceKind.THIRD_PARTY_REPORT and (
            not source.actor_id or source.actor_id == evidence.subject_agent_id
        ):
            raise ValueError("third-party report must come from another actor")
        if evidence.provenance == BeliefEvidenceKind.OBSERVED_ACTION and source.actor_id != evidence.subject_agent_id:
            raise ValueError("observed action actor must be the subject")
        if evidence.provenance == BeliefEvidenceKind.NARRATOR_ASSERTION and not source.metadata.get("reader_only"):
            raise ValueError("narrator assertion needs a reader-only source")
        if evidence.signal == IntentionSignal.EXPLICIT_REVISION:
            prior = [
                item for item in self._evidence.values()
                if item.subject_agent_id == evidence.subject_agent_id
                and item.goal_key == evidence.supersedes_goal_key
                and item.signal in {
                    IntentionSignal.EXPLICIT_INTENTION,
                    IntentionSignal.EXPLICIT_GOAL,
                    IntentionSignal.EXPLICIT_REVISION,
                }
                and (item.valid_time, item.system_record_time, item.evidence_id)
                < (evidence.valid_time, evidence.system_record_time, evidence.evidence_id)
            ]
            if not prior:
                raise ValueError("revision must name a prior directly evidenced goal")
        previous = self._evidence.get(evidence.evidence_id)
        if previous is not None:
            if previous != evidence:
                raise ValueError("evidence ID collision with different content")
            return True
        self._evidence[evidence.evidence_id] = evidence
        return False

    def _visible_source_ids(
        self, subject_agent_id: str, observer_agent_id: str | None,
        *, event_time: str | None = None, knowledge_cutoff: str | None = None,
    ) -> set[str]:
        if observer_agent_id == SYSTEM_VIEWER:
            return set(self.perspectives.perspective_view(
                SYSTEM_VIEWER, event_time=event_time, knowledge_cutoff=knowledge_cutoff
            ).event_ids)
        if observer_agent_id is None or observer_agent_id == subject_agent_id:
            return set(self.perspectives.perspective_view(
                subject_agent_id, event_time=event_time, knowledge_cutoff=knowledge_cutoff
            ).event_ids)
        return set(self.perspectives.second_order_view(
            observer_agent_id, subject_agent_id,
            event_time=event_time, knowledge_cutoff=knowledge_cutoff,
        ).event_ids)

    def goal_estimates(
        self, subject_agent_id: str, *, observer_agent_id: str | None = SYSTEM_VIEWER,
        event_time: str | None = None, knowledge_cutoff: str | None = None,
    ) -> tuple[GoalEstimate, ...]:
        visible = self._visible_source_ids(
            subject_agent_id, observer_agent_id,
            event_time=event_time, knowledge_cutoff=knowledge_cutoff,
        )
        evidence = sorted(
            (e for e in self._evidence.values() if e.subject_agent_id == subject_agent_id and e.source_event_id in visible),
            key=lambda e: (e.valid_time, e.system_record_time, e.evidence_id),
        )
        goals = sorted({e.goal_key for e in evidence} | {
            e.supersedes_goal_key for e in evidence if e.supersedes_goal_key
        })
        estimates = []
        for goal in goals:
            status = GoalStatus.SYSTEM_INSUFFICIENT
            revised_by = None
            direct, action, inferred, third_party, support, counter, uncertain = ([] for _ in range(7))
            for item in evidence:
                if item.signal == IntentionSignal.EXPLICIT_REVISION and item.supersedes_goal_key == goal:
                    status = GoalStatus.REVISED
                    revised_by = item.goal_key
                    direct.append(item.evidence_id)
                if item.goal_key != goal:
                    continue
                if item.signal in {IntentionSignal.EXPLICIT_INTENTION, IntentionSignal.EXPLICIT_GOAL, IntentionSignal.EXPLICIT_REVISION}:
                    status = GoalStatus.ACTIVE
                    revised_by = None
                    direct.append(item.evidence_id)
                elif item.signal == IntentionSignal.EXPLICIT_COMPLETION:
                    status = GoalStatus.COMPLETED
                    direct.append(item.evidence_id)
                elif item.signal == IntentionSignal.EXPLICIT_ABANDONMENT:
                    status = GoalStatus.ABANDONED
                    direct.append(item.evidence_id)
                elif item.signal == IntentionSignal.CHARACTER_UNCERTAIN:
                    uncertain.append(item.evidence_id)
                    if status == GoalStatus.SYSTEM_INSUFFICIENT:
                        status = GoalStatus.CHARACTER_UNCERTAIN
                elif item.signal == IntentionSignal.OBSERVED_ACTION:
                    action.append(item.evidence_id)
                elif item.signal == IntentionSignal.INFERRED_MOTIVATION:
                    inferred.append(item.evidence_id)
                elif item.signal == IntentionSignal.THIRD_PARTY_ATTRIBUTION:
                    third_party.append(item.evidence_id)
                elif item.signal == IntentionSignal.SUPPORT:
                    support.append(item.evidence_id)
                elif item.signal == IntentionSignal.COUNTEREVIDENCE:
                    counter.append(item.evidence_id)
                    if status == GoalStatus.ACTIVE:
                        status = GoalStatus.UNRESOLVED
            estimates.append(GoalEstimate(
                subject_agent_id, goal, status, tuple(direct), tuple(action), tuple(inferred),
                tuple(third_party), tuple(support), tuple(counter), tuple(uncertain), revised_by,
            ))
        return tuple(estimates)

    def answer_context(
        self, subject_agent_id: str, *, observer_agent_id: str | None = None,
        event_time: str | None = None, knowledge_cutoff: str | None = None,
    ) -> dict:
        view = self.perspectives.answer_context(
            subject_agent_id, observer_agent_id=observer_agent_id,
            event_time=event_time, knowledge_cutoff=knowledge_cutoff,
        )
        visible = set(view.target_information_view.event_ids)
        evidence = [e.as_dict() for e in self._evidence.values()
                    if e.subject_agent_id == subject_agent_id and e.source_event_id in visible]
        evidence.sort(key=lambda e: (e["valid_time"], e["system_record_time"], e["evidence_id"]))
        return {
            "perspective": view.as_dict(),
            "intention_evidence": evidence,
            "goal_estimates": [e.as_dict() for e in self.goal_estimates(
                subject_agent_id,
                observer_agent_id=observer_agent_id,
                event_time=event_time,
                knowledge_cutoff=knowledge_cutoff,
            )],
            "semantic_rules": {
                "action_does_not_prove_intention": True,
                "inferred_motivation_is_not_unique_truth": True,
                "system_insufficient_is_not_character_lacks_motivation": True,
                "action_change_does_not_imply_goal_revision": True,
                "third_party_attribution_is_not_subject_intention": True,
            },
        }
