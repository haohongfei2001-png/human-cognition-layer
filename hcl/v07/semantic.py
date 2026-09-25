"""Question-blind event-local extraction for v0.7 intention evidence."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Protocol

from hcl.v04.model import EventRecord
from hcl.v06.belief import BeliefEvidenceKind

from .runtime import IntentionEvidenceEvent, IntentionSignal


class V07ExtractionError(ValueError):
    pass


class SemanticBackend(Protocol):
    def complete_json(self, messages: list[dict[str, str]], *, max_tokens: int, temperature: float = 0.0) -> str:
        ...


@dataclass(frozen=True)
class V07ExtractionResult:
    evidence: tuple[IntentionEvidenceEvent, ...]
    repair_count: int = 0
    repair_reason: str | None = None


SYSTEM = """Extract only intention, goal, action and motivation evidence directly supported by this one source event.
Return JSON only: {"intention_evidence": [{"subject_agent_id": "...", "goal_key": "...", "signal": "EXPLICIT_INTENTION|EXPLICIT_GOAL|OBSERVED_ACTION|INFERRED_MOTIVATION|THIRD_PARTY_ATTRIBUTION|SUPPORT|COUNTEREVIDENCE|EXPLICIT_REVISION|EXPLICIT_ABANDONMENT|EXPLICIT_COMPLETION|CHARACTER_UNCERTAIN", "provenance": "SELF_REPORT|NARRATOR_ASSERTION|THIRD_PARTY_REPORT|OBSERVED_ACTION", "evidence_text": "exact substring of event.raw_text", "supersedes_goal_key": null}]}.
Use [] when no signal is supported. Reuse a known goal key only when its meaning matches.
SELF_REPORT must be the actor explicitly describing their own intention or goal. NARRATOR_ASSERTION requires reader-only narrator evidence; it may also source an OBSERVED_ACTION when the narrator describes a character's behavior. THIRD_PARTY_REPORT is another actor's attribution, never the subject's true motive. OBSERVED_ACTION records behavior; it cannot prove intention. INFERRED_MOTIVATION is a possible explanation, never a unique fact. An action change is not goal revision. A revision, completion or abandonment needs explicit direct evidence. Character uncertainty must be explicitly expressed; system lack of evidence is not character uncertainty.
The exact evidence_text must appear in the source event. Do not use question, answer, options, gold, benchmark metadata, or hidden generator state."""

REPAIR = """Repair the event-local intention evidence JSON. Remove any unsupported row. Every evidence_text must be an exact substring of event.raw_text. Preserve source provenance, action/intention separation, and explicit revision requirements. Return only the complete JSON object."""


def _parse(event: EventRecord, raw: str, known_goals: tuple[str, ...]) -> tuple[IntentionEvidenceEvent, ...]:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise V07ExtractionError("invalid JSON") from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("intention_evidence"), list):
        raise V07ExtractionError("intention_evidence must be a list")
    result: list[IntentionEvidenceEvent] = []
    seen: set[str] = set()
    for index, row in enumerate(payload["intention_evidence"]):
        if not isinstance(row, dict):
            raise V07ExtractionError(f"row {index} must be an object")
        subject = str(row.get("subject_agent_id") or "").strip()
        goal = str(row.get("goal_key") or "").strip()
        quote = str(row.get("evidence_text") or "").strip()
        if not subject or not goal or not quote or len(goal) > 240 or len(quote) > 600:
            raise V07ExtractionError(f"invalid row {index} identity or excerpt")
        if quote not in event.raw_text:
            raise V07ExtractionError("evidence excerpt is not in source event")
        try:
            signal = IntentionSignal(str(row.get("signal")))
            provenance = BeliefEvidenceKind(str(row.get("provenance")))
        except ValueError as exc:
            raise V07ExtractionError(f"invalid signal or provenance in row {index}") from exc
        prior = row.get("supersedes_goal_key")
        if prior is not None:
            prior = str(prior).strip()
        if signal == IntentionSignal.EXPLICIT_REVISION and prior not in known_goals:
            raise V07ExtractionError("revision names a goal not previously evidenced")
        if provenance == BeliefEvidenceKind.SELF_REPORT and event.actor_id != subject:
            raise V07ExtractionError("self report subject differs from actor")
        if provenance == BeliefEvidenceKind.THIRD_PARTY_REPORT and (
            not event.actor_id or event.actor_id == subject
        ):
            raise V07ExtractionError("third-party attribution lacks another actor")
        if provenance == BeliefEvidenceKind.OBSERVED_ACTION and event.actor_id != subject:
            raise V07ExtractionError("observed action subject differs from actor")
        if provenance == BeliefEvidenceKind.NARRATOR_ASSERTION and not event.metadata.get("reader_only"):
            raise V07ExtractionError("narrator assertion lacks reader-only evidence")
        material = json.dumps([event.event_id, subject, goal, signal.value, provenance.value, quote, prior], ensure_ascii=False, separators=(",", ":"))
        evidence_id = "intent_" + hashlib.sha256(material.encode("utf-8")).hexdigest()[:20]
        if evidence_id in seen:
            raise V07ExtractionError("duplicate intention evidence")
        seen.add(evidence_id)
        try:
            result.append(IntentionEvidenceEvent(
                evidence_id=evidence_id, source_event_id=event.event_id,
                subject_agent_id=subject, goal_key=goal, signal=signal,
                provenance=provenance, valid_time=event.valid_time,
                system_record_time=event.recorded_at, evidence_text=quote,
                supersedes_goal_key=prior,
            ))
        except ValueError as exc:
            raise V07ExtractionError(str(exc)) from exc
    return tuple(result)


def extract_intention_evidence(
    event: EventRecord, backend: SemanticBackend, *, known_goals: tuple[str, ...] = (), max_tokens: int = 2048,
) -> V07ExtractionResult:
    source = {
        "event_id": event.event_id, "actor_id": event.actor_id,
        "observer_ids": list(event.observer_ids), "recipient_ids": list(event.recipient_ids),
        "valid_time": event.valid_time, "reader_only": bool(event.metadata.get("reader_only")),
        "raw_text": event.raw_text, "known_goal_keys": list(known_goals),
    }
    messages = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": json.dumps(source, ensure_ascii=False, sort_keys=True)},
    ]
    first = backend.complete_json(messages, max_tokens=max_tokens, temperature=0.0)
    try:
        return V07ExtractionResult(_parse(event, first, known_goals))
    except V07ExtractionError as exc:
        repair_messages = messages + [
            {"role": "assistant", "content": first},
            {"role": "user", "content": REPAIR},
        ]
        repaired = backend.complete_json(repair_messages, max_tokens=max_tokens, temperature=0.0)
        return V07ExtractionResult(_parse(event, repaired, known_goals), repair_count=1, repair_reason=str(exc))
