"""Event-local affect extraction; no task or human appraisal labels are inputs."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from hcl.v04.model import EventRecord
from hcl.v06.belief import BeliefEvidenceKind as Provenance
from .runtime import (
    AffectEvidenceEvent,
    AffectKind,
    EvidenceStrength,
    AppraisalDimension,
    _order,
)


class V08ExtractionError(ValueError):
    pass


@dataclass(frozen=True)
class V08ExtractionResult:
    evidence: tuple[AffectEvidenceEvent, ...]
    repair_count: int = 0
    repair_reason: str | None = None


SYSTEM = """Extract only source-grounded affect and appraisal evidence from this one source event.
Return JSON {"affect_evidence": [{"subject_agent_id":"name or source actor","episode_key":"short stable situation key","kind":"EMOTION|APPRAISAL|EXPRESSION|CHARACTER_UNCERTAIN","strength":"DIRECT|INFERRED|ATTRIBUTED","value":"brief claim, without a unique-private-mind assertion","provenance":"SELF_REPORT|NARRATOR_ASSERTION|THIRD_PARTY_REPORT|OBSERVED_ACTION","evidence_text":"exact source substring","dimension":null,"goal_key":null,"supersedes_evidence_id":null}]}.
Return [] when no supported evidence exists. Maximum eight rows.
Emotion self-reports and directly narrated feelings can be DIRECT reports. Behavior or outcomes do not prove a feeling; use EXPRESSION for behavior, or INFERRED EMOTION for a plausible hypothesis. Multiple emotions and alternative interpretations can coexist. Another actor's judgment must be THIRD_PARTY_REPORT/ATTRIBUTED, not private truth. Explicit character uncertainty is distinct from the system not knowing.
APPRAISAL dimension is GOAL_RELEVANCE, GOAL_CONGRUENCE, CONTROL, CERTAINTY, or ACCOUNTABILITY. Record source-supported appraisals; do not force a deterministic appraisal-to-emotion mapping. A linked goal_key must be in known_goal_keys. Do not invent prior goals.
SELF_REPORT must refer to the source actor's own report. OBSERVED_ACTION must refer to the source actor's behavior and cannot support DIRECT mental evidence. NARRATOR_ASSERTION requires reader_only. EXPRESSION must be INFERRED with OBSERVED_ACTION or NARRATOR_ASSERTION. Only explicit DIRECT EMOTION or APPRAISAL revision may supersede an earlier direct evidence ID of the same subject, episode, kind and dimension. Changed action/expression alone does not revise emotion.
Never use task, question, gold, human ratings, persona labels, benchmark fields or hidden generator state."""
REPAIR = "Repair the full affect_evidence JSON. Remove unsupported or invalid rows. Use exact source excerpts, preserve direct/inferred/attributed distinctions and mixed emotions. Do not fabricate a revision or goal link. Return only the JSON object."


def _parse(event, raw, prior_evidence, known_goal_keys):
    try:
        payload = json.loads(raw)
        rows = payload["affect_evidence"]
        if not isinstance(rows, list) or len(rows) > 8:
            raise ValueError("affect_evidence must be a list of at most eight rows")
        result = []
        seen = set()
        priors = {x.evidence_id: x for x in prior_evidence}
        for row in rows:
            if not isinstance(row, dict):
                raise ValueError("affect row must be an object")
            fields = {
                k: row.get(k)
                for k in (
                    "subject_agent_id",
                    "episode_key",
                    "value",
                    "evidence_text",
                    "goal_key",
                    "supersedes_evidence_id",
                )
            }
            kind = AffectKind(row.get("kind"))
            strength = EvidenceStrength(row.get("strength"))
            provenance = Provenance(row.get("provenance"))
            dimension = (
                AppraisalDimension(row["dimension"])
                if row.get("dimension") is not None
                else None
            )
            material = json.dumps(
                [
                    event.event_id,
                    fields,
                    kind.value,
                    strength.value,
                    provenance.value,
                    dimension.value if dimension else None,
                ],
                sort_keys=True,
                ensure_ascii=False,
            )
            evidence_id = "affect_" + hashlib.sha256(material.encode()).hexdigest()[:20]
            item = AffectEvidenceEvent(
                evidence_id=evidence_id,
                source_event_id=event.event_id,
                kind=kind,
                strength=strength,
                provenance=provenance,
                dimension=dimension,
                valid_time=event.valid_time,
                system_record_time=event.recorded_at,
                **fields,
            )
            if item.evidence_text.strip() not in event.raw_text:
                raise ValueError("affect quote is not an exact source excerpt")
            if (
                provenance in {Provenance.SELF_REPORT, Provenance.OBSERVED_ACTION}
                and event.actor_id != item.subject_agent_id
            ):
                raise ValueError("affect subject differs from source actor")
            if provenance == Provenance.THIRD_PARTY_REPORT and (
                not event.actor_id or event.actor_id == item.subject_agent_id
            ):
                raise ValueError("third-party report requires another actor")
            if provenance == Provenance.NARRATOR_ASSERTION and not event.metadata.get(
                "reader_only"
            ):
                raise ValueError("narrator assertion lacks reader-only source")
            if item.goal_key is not None and item.goal_key not in known_goal_keys:
                raise ValueError("affect goal link is not previously evidenced")
            if item.supersedes_evidence_id is not None:
                old = priors.get(item.supersedes_evidence_id)
                if (
                    old is None
                    or old.strength != EvidenceStrength.DIRECT
                    or (old.subject_agent_id, old.episode_key, old.kind, old.dimension)
                    != (
                        item.subject_agent_id,
                        item.episode_key,
                        item.kind,
                        item.dimension,
                    )
                    or _order(old)[:2] >= _order(item)[:2]
                ):
                    raise ValueError(
                        "affect revision lacks matching earlier direct evidence"
                    )
            if evidence_id in seen:
                raise ValueError("duplicate affect evidence")
            seen.add(evidence_id)
            result.append(item)
        return tuple(result)
    except (ValueError, KeyError, TypeError, AttributeError) as exc:
        raise V08ExtractionError(str(exc)) from exc


def extract_affect_evidence(
    event: EventRecord,
    backend,
    *,
    prior_evidence=(),
    known_goal_keys=(),
    max_tokens=1536,
):
    source = {
        "event_id": event.event_id,
        "actor_id": event.actor_id,
        "reader_only": bool(event.metadata.get("reader_only")),
        "raw_text": event.raw_text,
        "known_goal_keys": list(known_goal_keys),
        "prior_direct_evidence": [
            x.as_dict() for x in prior_evidence if x.strength == EvidenceStrength.DIRECT
        ],
    }
    messages = [
        {"role": "system", "content": SYSTEM},
        {
            "role": "user",
            "content": json.dumps(source, sort_keys=True, ensure_ascii=False),
        },
    ]
    raw = backend.complete_json(messages, max_tokens=max_tokens, temperature=0.0)
    try:
        return V08ExtractionResult(_parse(event, raw, prior_evidence, known_goal_keys))
    except V08ExtractionError as exc:
        repair = backend.complete_json(
            messages
            + [
                {"role": "assistant", "content": raw},
                {"role": "user", "content": REPAIR},
            ],
            max_tokens=max_tokens,
            temperature=0.0,
        )
        return V08ExtractionResult(
            _parse(event, repair, prior_evidence, known_goal_keys), 1, str(exc)
        )
