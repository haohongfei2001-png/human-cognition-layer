"""Bounded semantic extraction for HCL v0.6 belief evidence."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Protocol

from hcl.v04.model import EventRecord

from .belief import (
    BeliefEvidenceEvent,
    BeliefEvidenceKind,
    BeliefSignal,
)


class V06SemanticExtractionError(ValueError):
    pass


class SemanticBackend(Protocol):
    def complete_json(
        self,
        messages: list[dict[str, str]],
        *,
        max_tokens: int,
        temperature: float = 0.0,
    ) -> str:
        ...


@dataclass(frozen=True)
class ChallengeRelation:
    challenged_proposition_key: str
    alternative_proposition_key: str | None = None


@dataclass(frozen=True)
class V06ExtractionResult:
    belief_evidence: tuple[BeliefEvidenceEvent, ...]
    challenge_relations: tuple[ChallengeRelation, ...]
    repair_count: int = 0
    repair_reason: str | None = None


SEMANTIC_SYSTEM = """You extract event-local evidence for HCL v0.6.

The goal is NOT to guess hidden psychology. Extract only belief evidence that
this event directly provides, while preserving how the evidence was obtained.

Return JSON only:
{
  "belief_evidence": [
    {
      "subject_agent_id": "...",
      "proposition_key": "...",
      "signal": "AFFIRM|DENY|UNCERTAIN",
      "evidence_kind": "SELF_REPORT|NARRATOR_ASSERTION|THIRD_PARTY_REPORT|OBSERVED_ACTION",
      "supersedes_proposition_key": null,
      "evidence_text": "short supporting text"
    }
  ],
  "challenge_relations": [
    {
      "challenged_proposition_key": "...",
      "alternative_proposition_key": null
    }
  ]
}

Evidence kinds:
- SELF_REPORT: the event actor explicitly reports their own belief/denial/
  uncertainty.
- NARRATOR_ASSERTION: narrator/background explicitly states a character's
  belief or uncertainty. Use only when event metadata marks narrator evidence.
- THIRD_PARTY_REPORT: one actor explicitly reports what another person believes.
  This is indirect evidence and must remain indirect.
- OBSERVED_ACTION: the actor's observable action may support or oppose a
  proposition, but does not directly establish private belief.

Challenge relations:
- Use only when the event communicates evidence that directly challenges a
  proposition to the event's explicit recipients/observers.
- Do not choose who was exposed. Deterministic code routes the challenge from
  recipient/observer/public metadata.
- Receiving a challenge is NOT belief revision.

Hard rules:
- Never turn information exposure into belief acceptance.
- Never treat "the system cannot tell what A believes" as "A is uncertain."
- Do not infer a private belief merely because it would explain an action.
- SELF_REPORT subject must be the event actor.
- THIRD_PARTY_REPORT subject must differ from the event actor.
- OBSERVED_ACTION subject must be the event actor.
- NARRATOR_ASSERTION is allowed only for narrator-marked events.
- A supersedes_proposition_key is allowed only when the event explicitly
  supports that the subject revised from the old proposition to the new one.
- Reuse known proposition keys when semantically identical; otherwise create a
  concise proposition key without forcing non-equivalent beliefs together.
- If there is no supported belief evidence or challenge, return empty lists.

Do not output confidence scores, personality traits, motives, emotions, moral
judgments, benchmark labels, answer choices, or current-state summaries.
"""


REPAIR_SYSTEM = """Repair an HCL v0.6 belief-evidence extraction.

Keep only evidence directly supported by the raw event and its provenance.
Do not invent hidden beliefs. Enforce:
- exposure is not belief;
- system uncertainty is not character uncertainty;
- source kind must match event provenance;
- self-report/action subject must match actor;
- narrator assertion requires narrator-marked metadata;
- third-party report remains indirect;
- explicit revision is required for supersedes_proposition_key.

Return the complete corrected JSON object only.
"""


def _clean_key(value, field: str) -> str:
    key = str(value or "").strip()
    if not key:
        raise V06SemanticExtractionError(f"{field} must not be empty")
    if len(key) > 240:
        raise V06SemanticExtractionError(f"{field} is too long")
    if any(ch in key for ch in "\r\n\t"):
        raise V06SemanticExtractionError(f"{field} must be single-line")
    return key


def _clean_text(value) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if len(text) > 600:
        raise V06SemanticExtractionError("evidence_text is too long")
    return text


def _is_narrator_event(event: EventRecord) -> bool:
    return bool(
        event.metadata.get("narrator")
        or event.metadata.get("reader_only")
        or str(event.metadata.get("source_kind", "")).lower() == "narrator"
    )


def _stable_id(source_event_id: str, payload: dict) -> str:
    material = json.dumps(
        {"source_event_id": source_event_id, **payload},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return "belief_" + hashlib.sha256(material.encode("utf-8")).hexdigest()[:20]


def _parse_payload(
    event: EventRecord,
    payload: dict,
) -> tuple[tuple[BeliefEvidenceEvent, ...], tuple[ChallengeRelation, ...]]:
    if not isinstance(payload, dict):
        raise V06SemanticExtractionError("semantic output must be an object")

    raw_evidence = payload.get("belief_evidence", [])
    raw_challenges = payload.get("challenge_relations", [])
    if not isinstance(raw_evidence, list):
        raise V06SemanticExtractionError("belief_evidence must be a list")
    if not isinstance(raw_challenges, list):
        raise V06SemanticExtractionError("challenge_relations must be a list")

    evidence: list[BeliefEvidenceEvent] = []
    identities: set[tuple] = set()

    for index, raw in enumerate(raw_evidence):
        if not isinstance(raw, dict):
            raise V06SemanticExtractionError(
                f"belief_evidence[{index}] must be an object"
            )

        subject = _clean_key(raw.get("subject_agent_id"), "subject_agent_id")
        proposition = _clean_key(raw.get("proposition_key"), "proposition_key")
        try:
            signal = BeliefSignal(str(raw.get("signal")))
        except ValueError as exc:
            raise V06SemanticExtractionError(
                f"invalid belief signal {raw.get('signal')!r}"
            ) from exc
        if signal == BeliefSignal.CHALLENGE:
            raise V06SemanticExtractionError(
                "CHALLENGE belongs in challenge_relations, not belief_evidence"
            )

        try:
            kind = BeliefEvidenceKind(str(raw.get("evidence_kind")))
        except ValueError as exc:
            raise V06SemanticExtractionError(
                f"invalid evidence kind {raw.get('evidence_kind')!r}"
            ) from exc
        if kind == BeliefEvidenceKind.INFORMATION_EXPOSURE:
            raise V06SemanticExtractionError(
                "INFORMATION_EXPOSURE belongs in challenge routing"
            )

        if kind == BeliefEvidenceKind.SELF_REPORT:
            if not event.actor_id or subject != event.actor_id:
                raise V06SemanticExtractionError(
                    "SELF_REPORT subject must equal event actor"
                )
        elif kind == BeliefEvidenceKind.NARRATOR_ASSERTION:
            if not _is_narrator_event(event):
                raise V06SemanticExtractionError(
                    "NARRATOR_ASSERTION requires narrator-marked event metadata"
                )
        elif kind == BeliefEvidenceKind.THIRD_PARTY_REPORT:
            if not event.actor_id or subject == event.actor_id:
                raise V06SemanticExtractionError(
                    "THIRD_PARTY_REPORT requires actor and distinct subject"
                )
        elif kind == BeliefEvidenceKind.OBSERVED_ACTION:
            if not event.actor_id or subject != event.actor_id:
                raise V06SemanticExtractionError(
                    "OBSERVED_ACTION subject must equal event actor"
                )

        supersedes_raw = raw.get("supersedes_proposition_key")
        supersedes = (
            _clean_key(supersedes_raw, "supersedes_proposition_key")
            if supersedes_raw is not None
            else None
        )
        if supersedes is not None and signal != BeliefSignal.AFFIRM:
            raise V06SemanticExtractionError(
                "supersedes_proposition_key requires AFFIRM"
            )
        if supersedes == proposition:
            raise V06SemanticExtractionError("a proposition cannot supersede itself")

        identity = (subject, proposition, signal.value, kind.value, supersedes)
        if identity in identities:
            continue
        identities.add(identity)

        payload_for_id = {
            "subject_agent_id": subject,
            "proposition_key": proposition,
            "signal": signal.value,
            "evidence_kind": kind.value,
            "supersedes_proposition_key": supersedes,
        }
        evidence.append(
            BeliefEvidenceEvent(
                evidence_id=_stable_id(event.event_id, payload_for_id),
                subject_agent_id=subject,
                proposition_key=proposition,
                signal=signal,
                evidence_kind=kind,
                valid_time=event.valid_time,
                system_record_time=event.recorded_at,
                source_event_id=event.event_id,
                source_agent_id=event.actor_id or event.source_id,
                supersedes_proposition_key=supersedes,
                evidence_text=_clean_text(raw.get("evidence_text")),
            )
        )

    challenges: list[ChallengeRelation] = []
    seen_challenges: set[tuple[str, str | None]] = set()
    for index, raw in enumerate(raw_challenges):
        if not isinstance(raw, dict):
            raise V06SemanticExtractionError(
                f"challenge_relations[{index}] must be an object"
            )
        challenged = _clean_key(
            raw.get("challenged_proposition_key"),
            "challenged_proposition_key",
        )
        alternative_raw = raw.get("alternative_proposition_key")
        alternative = (
            _clean_key(alternative_raw, "alternative_proposition_key")
            if alternative_raw is not None
            else None
        )
        if alternative == challenged:
            raise V06SemanticExtractionError(
                "challenge alternative must differ from challenged proposition"
            )
        identity = (challenged, alternative)
        if identity in seen_challenges:
            continue
        seen_challenges.add(identity)
        challenges.append(
            ChallengeRelation(
                challenged_proposition_key=challenged,
                alternative_proposition_key=alternative,
            )
        )

    return tuple(evidence), tuple(challenges)


def extract_belief_evidence(
    event: EventRecord,
    backend: SemanticBackend,
    *,
    known_propositions: tuple[str, ...] = (),
    max_tokens: int = 1536,
) -> V06ExtractionResult:
    user_payload = {
        "event": {
            "event_id": event.event_id,
            "valid_time": event.valid_time,
            "recorded_at": event.recorded_at,
            "source_id": event.source_id,
            "actor_id": event.actor_id,
            "observer_ids": list(event.observer_ids),
            "recipient_ids": list(event.recipient_ids),
            "raw_text": event.raw_text,
            "metadata": event.metadata,
        },
        "known_proposition_keys": list(known_propositions),
    }
    messages = [
        {"role": "system", "content": SEMANTIC_SYSTEM},
        {
            "role": "user",
            "content": json.dumps(user_payload, ensure_ascii=False, sort_keys=True),
        },
    ]
    raw = backend.complete_json(messages, max_tokens=max_tokens, temperature=0.0)

    first_error: Exception | None = None
    for attempt in range(2):
        try:
            payload = json.loads(raw)
            evidence, challenges = _parse_payload(event, payload)
            return V06ExtractionResult(
                belief_evidence=evidence,
                challenge_relations=challenges,
                repair_count=attempt,
                repair_reason=(
                    None
                    if attempt == 0
                    else f"belief extraction repaired after: {first_error}"
                ),
            )
        except (json.JSONDecodeError, V06SemanticExtractionError, ValueError) as exc:
            if first_error is None:
                first_error = exc
            if attempt == 1:
                raise V06SemanticExtractionError(
                    f"v0.6 belief extraction invalid after bounded repair: {exc}"
                ) from exc
            raw = backend.complete_json(
                [
                    {"role": "system", "content": REPAIR_SYSTEM},
                    {
                        "role": "user",
                        "content": json.dumps(
                            {
                                "event": user_payload["event"],
                                "known_proposition_keys": list(known_propositions),
                                "invalid_output": raw,
                                "validation_error": str(exc),
                            },
                            ensure_ascii=False,
                            sort_keys=True,
                        ),
                    },
                ],
                max_tokens=max_tokens,
                temperature=0.0,
            )

    raise V06SemanticExtractionError("v0.6 belief extraction failed")


__all__ = [
    "ChallengeRelation",
    "SemanticBackend",
    "V06ExtractionResult",
    "V06SemanticExtractionError",
    "extract_belief_evidence",
]
