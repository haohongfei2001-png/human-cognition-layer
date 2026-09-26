"""Evidence-constrained affect and appraisal, reusing goal/perspective history."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from enum import Enum

from hcl.v04.model import EventRecord
from hcl.v06 import SYSTEM_VIEWER
from hcl.v06.belief import BeliefEvidenceKind as Provenance
from hcl.v07 import HCLV07Runtime


class AffectKind(str, Enum):
    EMOTION = "EMOTION"
    APPRAISAL = "APPRAISAL"
    EXPRESSION = "EXPRESSION"
    CHARACTER_UNCERTAIN = "CHARACTER_UNCERTAIN"


class EvidenceStrength(str, Enum):
    DIRECT = "DIRECT"
    INFERRED = "INFERRED"
    ATTRIBUTED = "ATTRIBUTED"


class AppraisalDimension(str, Enum):
    GOAL_RELEVANCE = "GOAL_RELEVANCE"
    GOAL_CONGRUENCE = "GOAL_CONGRUENCE"
    CONTROL = "CONTROL"
    CERTAINTY = "CERTAINTY"
    ACCOUNTABILITY = "ACCOUNTABILITY"


DIRECT_PROVENANCE = {Provenance.SELF_REPORT, Provenance.NARRATOR_ASSERTION}


def _time(value: str) -> datetime:
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.utcoffset() is None:
        raise ValueError("affect chronology requires a timezone")
    return result


@dataclass(frozen=True)
class AffectEvidenceEvent:
    evidence_id: str
    source_event_id: str
    subject_agent_id: str
    episode_key: str
    kind: AffectKind
    strength: EvidenceStrength
    value: str
    provenance: Provenance
    valid_time: str
    system_record_time: str
    evidence_text: str
    dimension: AppraisalDimension | None = None
    goal_key: str | None = None
    supersedes_evidence_id: str | None = None

    def __post_init__(self):
        for field in (
            "evidence_id",
            "source_event_id",
            "subject_agent_id",
            "episode_key",
            "value",
            "evidence_text",
        ):
            value = getattr(self, field)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field} must be a nonempty string")
        if (
            len(self.value) > 500
            or len(self.evidence_text) > 1000
            or len(self.episode_key) > 240
        ):
            raise ValueError("affect evidence field cap exceeded")
        if (
            not isinstance(self.kind, AffectKind)
            or not isinstance(self.strength, EvidenceStrength)
            or not isinstance(self.provenance, Provenance)
        ):
            raise ValueError("typed affect kind, strength and provenance required")
        _time(self.valid_time)
        _time(self.system_record_time)
        if self.kind == AffectKind.APPRAISAL:
            if not isinstance(self.dimension, AppraisalDimension):
                raise ValueError("appraisal requires a bounded dimension")
        elif self.dimension is not None or self.goal_key is not None:
            raise ValueError("only appraisal may carry dimension or goal link")
        if (
            self.strength == EvidenceStrength.DIRECT
            and self.provenance not in DIRECT_PROVENANCE
        ):
            raise ValueError(
                "direct mental report requires self-report or narrator evidence"
            )
        if (self.provenance == Provenance.THIRD_PARTY_REPORT) != (
            self.strength == EvidenceStrength.ATTRIBUTED
        ):
            raise ValueError("third-party attribution must remain attributed")
        if self.kind == AffectKind.EXPRESSION and (
            self.strength != EvidenceStrength.INFERRED
            or self.provenance
            not in {Provenance.OBSERVED_ACTION, Provenance.NARRATOR_ASSERTION}
        ):
            raise ValueError(
                "expression is observed behavior, not a direct mental report"
            )
        if (
            self.kind == AffectKind.CHARACTER_UNCERTAIN
            and self.strength != EvidenceStrength.DIRECT
        ):
            raise ValueError("character uncertainty requires an explicit report")
        if self.supersedes_evidence_id is not None and (
            self.strength != EvidenceStrength.DIRECT
            or self.kind not in {AffectKind.EMOTION, AffectKind.APPRAISAL}
        ):
            raise ValueError(
                "only explicit direct mental evidence can revise a prior report"
            )
        for optional in (self.goal_key, self.supersedes_evidence_id):
            if optional is not None and (
                not isinstance(optional, str) or not optional.strip()
            ):
                raise ValueError("empty affect relation")

    def as_dict(self):
        data = dict(self.__dict__)
        for key in ("kind", "strength", "provenance", "dimension"):
            if data[key] is not None:
                data[key] = data[key].value
        return data


def _order(item: AffectEvidenceEvent):
    return (_time(item.valid_time), _time(item.system_record_time), item.evidence_id)


class HCLV08Runtime:
    """No rule maps actions, outcomes or appraisals to a unique private emotion."""

    def __init__(self, intentions: HCLV07Runtime | None = None):
        self.intentions = intentions if intentions is not None else HCLV07Runtime()
        self._evidence: dict[str, AffectEvidenceEvent] = {}
        self._semantic_results = {}

    def ingest_event(self, event: EventRecord):
        return self.intentions.ingest_event(event)

    def ingest_affect_evidence(self, evidence: AffectEvidenceEvent):
        source = next(
            (
                x
                for x in self.intentions.perspectives.events
                if x.event_id == evidence.source_event_id
            ),
            None,
        )
        if source is None:
            raise ValueError("affect evidence requires an ingested source")
        if (evidence.valid_time, evidence.system_record_time) != (
            source.valid_time,
            source.recorded_at,
        ):
            raise ValueError("affect chronology must match source")
        if evidence.evidence_text.strip() not in source.raw_text:
            raise ValueError("affect evidence needs an exact source excerpt")
        if (
            evidence.provenance in {Provenance.SELF_REPORT, Provenance.OBSERVED_ACTION}
            and source.actor_id != evidence.subject_agent_id
        ):
            raise ValueError(
                "self-report/observation subject differs from source actor"
            )
        if evidence.provenance == Provenance.THIRD_PARTY_REPORT and (
            not source.actor_id or source.actor_id == evidence.subject_agent_id
        ):
            raise ValueError("attribution requires another source actor")
        if (
            evidence.provenance == Provenance.NARRATOR_ASSERTION
            and not source.metadata.get("reader_only")
        ):
            raise ValueError("narrator evidence requires a reader-only source")
        prior = self._evidence.get(evidence.supersedes_evidence_id)
        if evidence.supersedes_evidence_id is not None:
            if (
                prior is None
                or prior.strength != EvidenceStrength.DIRECT
                or (
                    prior.subject_agent_id,
                    prior.episode_key,
                    prior.kind,
                    prior.dimension,
                )
                != (
                    evidence.subject_agent_id,
                    evidence.episode_key,
                    evidence.kind,
                    evidence.dimension,
                )
                or _order(prior)[:2] >= _order(evidence)[:2]
            ):
                raise ValueError(
                    "revision needs earlier direct evidence in the same subject/episode/kind/dimension"
                )
        if evidence.goal_key is not None:
            goals = self.intentions.goal_estimates(
                evidence.subject_agent_id,
                observer_agent_id=SYSTEM_VIEWER,
                event_time=evidence.valid_time,
                knowledge_cutoff=evidence.system_record_time,
            )
            if not any(
                x.goal_key == evidence.goal_key and x.direct_evidence_ids for x in goals
            ):
                raise ValueError(
                    "appraisal goal link needs an already evidenced direct goal"
                )
        previous = self._evidence.get(evidence.evidence_id)
        if previous is not None:
            if previous != evidence:
                raise ValueError("affect evidence ID collision")
            return True
        self._evidence[evidence.evidence_id] = evidence
        return False

    def ingest_semantic_event(self, event: EventRecord, backend, *, max_tokens=1536):
        from .semantic import extract_affect_evidence

        existing = next(
            (
                x
                for x in self.intentions.perspectives.events
                if x.event_id == event.event_id
            ),
            None,
        )
        if existing is not None and existing != event:
            raise ValueError("source event ID collision")
        if event.event_id in self._semantic_results:
            return self._semantic_results[event.event_id]
        # Preserve the original source even if both extraction attempts fail.
        self.ingest_event(event)
        source_viewer = (
            SYSTEM_VIEWER if event.metadata.get("reader_only") else event.actor_id
        )
        visible_prior_sources = (
            self.intentions._visible_source_ids(
                event.actor_id,
                source_viewer,
                event_time=event.valid_time,
                knowledge_cutoff=event.recorded_at,
            )
            if source_viewer
            else set()
        )
        known = tuple(
            x
            for x in self._evidence.values()
            if x.source_event_id in visible_prior_sources
        )
        prior_ids = {x.evidence_id for x in known}
        goal_keys_by_subject = {
            subject: {
                x.goal_key
                for x in self.intentions.goal_estimates(
                    subject,
                    observer_agent_id=source_viewer,
                    event_time=event.valid_time,
                    knowledge_cutoff=event.recorded_at,
                )
                if x.direct_evidence_ids
            }
            for subject in {x.subject_agent_id for x in known}
        }
        known = tuple(
            replace(
                x,
                goal_key=(
                    x.goal_key
                    if x.goal_key in goal_keys_by_subject[x.subject_agent_id]
                    else None
                ),
                supersedes_evidence_id=(
                    x.supersedes_evidence_id
                    if x.supersedes_evidence_id in prior_ids
                    else None
                ),
            )
            for x in known
        )
        goals = (
            self.intentions.goal_estimates(
                event.actor_id,
                observer_agent_id=source_viewer,
                event_time=event.valid_time,
                knowledge_cutoff=event.recorded_at,
            )
            if event.actor_id
            else ()
        )
        result = extract_affect_evidence(
            event,
            backend,
            prior_evidence=known,
            known_goal_keys=tuple(x.goal_key for x in goals if x.direct_evidence_ids),
            max_tokens=max_tokens,
        )
        before = dict(self._evidence)
        try:
            for item in result.evidence:
                self.ingest_affect_evidence(item)
        except Exception:
            self._evidence = before
            raise
        self._semantic_results[event.event_id] = result
        return result

    def answer_context(
        self,
        subject_agent_id: str,
        *,
        observer_agent_id=SYSTEM_VIEWER,
        event_time=None,
        knowledge_cutoff=None,
    ):
        visible = self.intentions._visible_source_ids(
            subject_agent_id,
            observer_agent_id,
            event_time=event_time,
            knowledge_cutoff=knowledge_cutoff,
        )
        evidence = sorted(
            (
                x
                for x in self._evidence.values()
                if x.subject_agent_id == subject_agent_id
                and x.source_event_id in visible
            ),
            key=_order,
        )
        superseded = {
            x.supersedes_evidence_id for x in evidence if x.supersedes_evidence_id
        }
        current = [x for x in evidence if x.evidence_id not in superseded]
        goals = self.intentions.goal_estimates(
            subject_agent_id,
            observer_agent_id=observer_agent_id,
            event_time=event_time,
            knowledge_cutoff=knowledge_cutoff,
        )
        visible_goals = {x.goal_key for x in goals if x.direct_evidence_ids}
        visible_evidence_ids = {x.evidence_id for x in evidence}

        def serialize(item):
            row = item.as_dict()
            # A relation pointer must not reveal a goal hidden from this view.
            if row["goal_key"] not in visible_goals:
                row["goal_key"] = None
            if row["supersedes_evidence_id"] not in visible_evidence_ids:
                row["supersedes_evidence_id"] = None
            return row

        reported = [
            x
            for x in current
            if x.kind == AffectKind.EMOTION and x.strength == EvidenceStrength.DIRECT
        ]
        hypotheses = [
            x
            for x in current
            if x.kind == AffectKind.EMOTION and x.strength == EvidenceStrength.INFERRED
        ]
        uncertain = [x for x in current if x.kind == AffectKind.CHARACTER_UNCERTAIN]
        status = (
            "SUPPORTED_REPORT"
            if reported
            else (
                "CHARACTER_UNCERTAIN"
                if uncertain
                else "HYPOTHESIS_ONLY" if hypotheses else "SYSTEM_INSUFFICIENT"
            )
        )
        return {
            "schema": "hcl-v08-evidence-constrained-affect-v01",
            "subject_agent_id": subject_agent_id,
            "observer_agent_id": observer_agent_id,
            "emotion_status": status,
            "current_evidence": [serialize(x) for x in current],
            "historical_evidence": [
                serialize(x) for x in evidence if x.evidence_id in superseded
            ],
            "visible_goal_context": [x.as_dict() for x in goals],
            "policy": "Reports, expressions, attributed judgments and plausible hypotheses remain distinct. Mixed emotions can coexist. Appraisal/outcome never uniquely determines emotion. Missing system evidence is not absence of feeling.",
        }
