"""Bounded semantic event extraction for the HCL v0.5 stance core."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Protocol

from hcl.v04.model import EventRecord

from .stance import StanceEvent, StanceSignal


class SemanticExtractionError(ValueError):
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
class ExtractionResult:
    stance_events: tuple[StanceEvent, ...]
    repair_count: int = 0
    repair_reason: str | None = None
    revision_relations: tuple["RevisionRelation", ...] = ()


SEMANTIC_SYSTEM = """You extract event-local stance signals for HCL v0.5.

You DO NOT decide a person's final/current belief. Deterministic code does that
later. Extract only what this one event directly supports.

Return JSON only:
{
  "stance_events": [
    {
      "subject_agent_id": "...",
      "issue_key": "...",
      "signal": "AFFIRM|DENY|REVISION_EXPOSURE|UNRESOLVED",
      "value_key": "...",
      "prior_value_key": null
    }
  ]
}

Definitions:
- AFFIRM: the subject explicitly accepts/believes value_key for issue_key.
- DENY: the subject explicitly rejects/denies value_key for issue_key.
- REVISION_EXPOSURE: the subject actually receives/observes an explicit
  correction/replacement from prior_value_key to value_key. Receipt is not
  acceptance.
- UNRESOLVED: the subject explicitly says they have not accepted/rejected or
  have not decided about value_key.

Hard constraints:
- AFFIRM, DENY and UNRESOLVED are self-stance reports: normally the subject must
  be the event actor. Do not infer another person's stance from a source claim.
- REVISION_EXPOSURE requires an actual information path to that subject in this
  event. A correction sent to Bob only is not exposure for Alice.
- Do not create stance signals from world/system facts that the target did not
  receive.
- Do not infer acceptance from receipt.
- Do not infer a revision from a mere repeated statement of the same value.
- issue_key identifies the semantic issue (for example one room assignment),
  while value_key identifies one alternative value. Reuse known keys exactly
  when they match. For a new issue/value, choose a concise stable key.
- A revision must use the new object-level value as value_key and the replaced
  object-level value as prior_value_key. Do not use a meta-sentence such as
  "Blue replaces Red" as the value key.
- If this event contains no directly supported stance signal, return an empty
  stance_events list.

Do not output gold labels, predictions, confidence scores, or current-state
summaries.
"""

REPAIR_SYSTEM = """Repair the proposed HCL v0.5 stance-event extraction.

Preserve only signals directly supported by the supplied raw event. Obey:
- self stance (AFFIRM/DENY/UNRESOLVED) requires the subject to be the event actor;
- REVISION_EXPOSURE requires an actual event access path to the subject;
- receipt is not acceptance;
- revision values must differ;
- all keys/enum values must match the declared schema.

Remove unsupported signals rather than inventing replacements.
Return the complete JSON object only.
"""


def _stable_event_id(source_event_id: str, payload: dict) -> str:
    material = json.dumps(
        {"source_event_id": source_event_id, **payload},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    digest = hashlib.sha256(material.encode("utf-8")).hexdigest()[:16]
    return f"stance_{digest}"


def _clean_key(value, field: str) -> str:
    key = str(value or "").strip()
    if not key:
        raise SemanticExtractionError(f"{field} must not be empty")
    if len(key) > 160:
        raise SemanticExtractionError(f"{field} is too long")
    if any(ch in key for ch in "\r\n\t"):
        raise SemanticExtractionError(f"{field} must be a single-line key")
    return key


def _event_accessible(event: EventRecord, subject: str) -> bool:
    return bool(
        event.metadata.get("public")
        or event.actor_id == subject
        or subject in event.observer_ids
        or subject in event.recipient_ids
    )


def _parse_payload(
    event: EventRecord,
    payload: dict,
) -> tuple[StanceEvent, ...]:
    if not isinstance(payload, dict):
        raise SemanticExtractionError("semantic output must be an object")
    rows = payload.get("stance_events", [])
    if not isinstance(rows, list):
        raise SemanticExtractionError("stance_events must be a list")

    result: list[StanceEvent] = []
    identities: set[tuple[str, str, str, str | None, str | None]] = set()
    for index, raw in enumerate(rows):
        if not isinstance(raw, dict):
            raise SemanticExtractionError(f"stance_events[{index}] must be an object")
        subject = _clean_key(raw.get("subject_agent_id"), "subject_agent_id")
        issue_key = _clean_key(raw.get("issue_key"), "issue_key")
        try:
            signal = StanceSignal(str(raw.get("signal")))
        except ValueError as exc:
            raise SemanticExtractionError(
                f"invalid signal={raw.get('signal')!r}"
            ) from exc

        value_key = _clean_key(raw.get("value_key"), "value_key")
        prior_raw = raw.get("prior_value_key")
        prior = (
            _clean_key(prior_raw, "prior_value_key")
            if prior_raw is not None
            else None
        )

        if signal in {
            StanceSignal.AFFIRM,
            StanceSignal.DENY,
            StanceSignal.UNRESOLVED,
        }:
            if event.actor_id != subject:
                raise SemanticExtractionError(
                    f"{signal.value} requires subject to be event actor"
                )
            if prior is not None:
                raise SemanticExtractionError(
                    f"{signal.value} must not set prior_value_key"
                )

        if signal == StanceSignal.REVISION_EXPOSURE:
            if prior is None:
                raise SemanticExtractionError(
                    "REVISION_EXPOSURE requires prior_value_key"
                )
            if prior == value_key:
                raise SemanticExtractionError("revision values must differ")
            if not _event_accessible(event, subject):
                raise SemanticExtractionError(
                    "REVISION_EXPOSURE has no information path to subject"
                )
        elif prior is not None:
            raise SemanticExtractionError(
                "prior_value_key is valid only for REVISION_EXPOSURE"
            )

        identity = (
            subject,
            issue_key,
            signal.value,
            value_key,
            prior,
        )
        if identity in identities:
            continue
        identities.add(identity)

        id_payload = {
            "subject_agent_id": subject,
            "issue_key": issue_key,
            "signal": signal.value,
            "value_key": value_key,
            "prior_value_key": prior,
        }
        result.append(
            StanceEvent(
                event_id=_stable_event_id(event.event_id, id_payload),
                subject_agent_id=subject,
                issue_key=issue_key,
                signal=signal,
                value_key=value_key,
                prior_value_key=prior,
                valid_time=event.valid_time,
                system_record_time=event.recorded_at,
                evidence_event_ids=(event.event_id,),
            )
        )
    return tuple(result)


def catalog_from_events(events: tuple[StanceEvent, ...]) -> dict[str, list[str]]:
    catalog: dict[str, set[str]] = {}
    for event in events:
        values = catalog.setdefault(event.issue_key, set())
        if event.value_key:
            values.add(event.value_key)
        if event.prior_value_key:
            values.add(event.prior_value_key)
    return {
        issue: sorted(values)
        for issue, values in sorted(catalog.items())
    }


def extract_stance_events(
    event: EventRecord,
    backend: SemanticBackend,
    *,
    known_catalog: dict[str, list[str]] | None = None,
    max_tokens: int = 1536,
) -> ExtractionResult:
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
        "known_issue_value_catalog": known_catalog or {},
    }
    messages = [
        {"role": "system", "content": SEMANTIC_SYSTEM},
        {
            "role": "user",
            "content": json.dumps(user_payload, ensure_ascii=False, sort_keys=True),
        },
    ]
    raw = backend.complete_json(
        messages,
        max_tokens=max_tokens,
        temperature=0.0,
    )

    first_error: Exception | None = None
    for attempt in range(2):
        try:
            payload = json.loads(raw)
            stance_events = _parse_payload(event, payload)
            return ExtractionResult(
                stance_events=stance_events,
                repair_count=attempt,
                repair_reason=(
                    None
                    if attempt == 0
                    else f"semantic extraction required one repair after: {first_error}"
                ),
            )
        except (json.JSONDecodeError, SemanticExtractionError) as exc:
            if first_error is None:
                first_error = exc
            if attempt == 1:
                raise SemanticExtractionError(
                    f"stance extraction invalid after bounded repair: {exc}"
                ) from exc
            raw = backend.complete_json(
                [
                    {"role": "system", "content": REPAIR_SYSTEM},
                    {
                        "role": "user",
                        "content": json.dumps(
                            {
                                "event": user_payload["event"],
                                "known_issue_value_catalog": known_catalog or {},
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

    raise SemanticExtractionError("stance extraction failed")


@dataclass(frozen=True)
class RevisionRelation:
    issue_key: str
    new_value_key: str
    prior_value_key: str


ROUTED_SEMANTIC_SYSTEM = """You extract two kinds of event-local semantics for HCL v0.5.

You do NOT decide anyone's final/current belief and you do NOT decide who was
exposed to a revision. Deterministic code handles information-flow routing from
the event recipient/observer metadata.

Return JSON only:
{
  "self_stances": [
    {
      "issue_key": "...",
      "signal": "AFFIRM|DENY|UNRESOLVED",
      "value_key": "..."
    }
  ],
  "revision_relations": [
    {
      "issue_key": "...",
      "new_value_key": "...",
      "prior_value_key": "..."
    }
  ]
}

SELF STANCE rules:
- self_stances describe ONLY an explicit mental stance reported by the event
  actor about the actor themself.
- A source merely telling, informing, announcing, asserting, or reporting that
  proposition P is true is NOT evidence of the source's own belief and must not
  create a self_stance.
- "A tells B: X is current" -> no self stance for A.
- "A says: I believe/accept X" -> AFFIRM X.
- "A says: I reject/deny X" -> DENY X.
- "A says: I have not decided whether to accept X" -> UNRESOLVED X.
- A third-party claim about another person's stance is not a self stance.
- A self-report that mentions a previously received correction does not itself
  recreate revision exposure.

REVISION RELATION rules:
- revision_relations identify only an explicit semantic replacement/correction
  relation in this event: new_value replaces/corrects prior_value.
- Do not include a subject/person in a revision relation.
- Do not infer a revision from a repeated statement of the same value.
- A relay may contain a revision relation if it explicitly says new replaces or
  supersedes old.
- A world/system update may contain a revision relation even if not everyone
  observed it. Deterministic routing decides who was exposed.

IDENTITY rules:
- issue_key identifies the semantic issue.
- value keys identify object-level alternatives, never meta-sentences.
- Reuse known issue/value keys exactly when they match.
- For a new issue/value, choose a concise stable key.

If neither kind is directly supported, return empty lists.
Do not output subject_agent_id, gold labels, predictions, confidence, or a
current-state summary.
"""


ROUTED_REPAIR_SYSTEM = """Repair the HCL v0.5 routed semantic extraction.

Return exactly:
{
  "self_stances": [
    {"issue_key": "...", "signal": "AFFIRM|DENY|UNRESOLVED", "value_key": "..."}
  ],
  "revision_relations": [
    {"issue_key": "...", "new_value_key": "...", "prior_value_key": "..."}
  ]
}

Hard rules:
- self_stances are only explicit self-reports by the event actor;
- source assertion is not source belief;
- third-party stance claim is not self stance;
- revision relations contain no person/subject;
- revision new and prior values must differ;
- mentioning an earlier correction in a self-report does not recreate exposure;
- remove unsupported entries rather than inventing replacements.

Return the complete corrected JSON object only.
"""


def _explicit_exposure_targets(event: EventRecord) -> tuple[str, ...]:
    targets = []
    seen = set()
    for subject in (*event.recipient_ids, *event.observer_ids):
        subject = str(subject).strip()
        if not subject or subject in seen:
            continue
        seen.add(subject)
        targets.append(subject)
    return tuple(targets)


def _parse_routed_payload(
    event: EventRecord,
    payload: dict,
) -> tuple[tuple[StanceEvent, ...], tuple[RevisionRelation, ...]]:
    if not isinstance(payload, dict):
        raise SemanticExtractionError("semantic output must be an object")
    allowed_top = {"self_stances", "revision_relations"}
    extra_top = set(payload) - allowed_top
    if extra_top:
        raise SemanticExtractionError(
            f"unexpected routed extraction fields: {sorted(extra_top)}"
        )

    raw_self = payload.get("self_stances", [])
    raw_revisions = payload.get("revision_relations", [])
    if not isinstance(raw_self, list):
        raise SemanticExtractionError("self_stances must be a list")
    if not isinstance(raw_revisions, list):
        raise SemanticExtractionError("revision_relations must be a list")

    result: list[StanceEvent] = []
    identities: set[tuple[str, str, str, str, str | None]] = set()

    if raw_self and not event.actor_id:
        raise SemanticExtractionError(
            "self_stances require an event actor"
        )

    for index, raw in enumerate(raw_self):
        if not isinstance(raw, dict):
            raise SemanticExtractionError(
                f"self_stances[{index}] must be an object"
            )
        allowed = {"issue_key", "signal", "value_key"}
        extra = set(raw) - allowed
        if extra:
            raise SemanticExtractionError(
                f"self_stances[{index}] has unexpected fields: {sorted(extra)}"
            )
        issue_key = _clean_key(raw.get("issue_key"), "issue_key")
        value_key = _clean_key(raw.get("value_key"), "value_key")
        try:
            signal = StanceSignal(str(raw.get("signal")))
        except ValueError as exc:
            raise SemanticExtractionError(
                f"invalid self stance signal={raw.get('signal')!r}"
            ) from exc
        if signal not in {
            StanceSignal.AFFIRM,
            StanceSignal.DENY,
            StanceSignal.UNRESOLVED,
        }:
            raise SemanticExtractionError(
                "self_stances may contain only AFFIRM, DENY, or UNRESOLVED"
            )
        subject = str(event.actor_id)
        identity = (subject, issue_key, signal.value, value_key, None)
        if identity in identities:
            continue
        identities.add(identity)
        id_payload = {
            "subject_agent_id": subject,
            "issue_key": issue_key,
            "signal": signal.value,
            "value_key": value_key,
            "prior_value_key": None,
        }
        result.append(
            StanceEvent(
                event_id=_stable_event_id(event.event_id, id_payload),
                subject_agent_id=subject,
                issue_key=issue_key,
                signal=signal,
                value_key=value_key,
                prior_value_key=None,
                valid_time=event.valid_time,
                system_record_time=event.recorded_at,
                evidence_event_ids=(event.event_id,),
            )
        )

    revisions: list[RevisionRelation] = []
    revision_keys: set[tuple[str, str, str]] = set()
    targets = _explicit_exposure_targets(event)
    for index, raw in enumerate(raw_revisions):
        if not isinstance(raw, dict):
            raise SemanticExtractionError(
                f"revision_relations[{index}] must be an object"
            )
        allowed = {"issue_key", "new_value_key", "prior_value_key"}
        extra = set(raw) - allowed
        if extra:
            raise SemanticExtractionError(
                f"revision_relations[{index}] has unexpected fields: {sorted(extra)}"
            )
        issue_key = _clean_key(raw.get("issue_key"), "issue_key")
        new_value = _clean_key(raw.get("new_value_key"), "new_value_key")
        prior_value = _clean_key(raw.get("prior_value_key"), "prior_value_key")
        if new_value == prior_value:
            raise SemanticExtractionError("revision values must differ")
        revision_key = (issue_key, new_value, prior_value)
        if revision_key in revision_keys:
            continue
        revision_keys.add(revision_key)
        revisions.append(
            RevisionRelation(
                issue_key=issue_key,
                new_value_key=new_value,
                prior_value_key=prior_value,
            )
        )
        for subject in targets:
            identity = (
                subject,
                issue_key,
                StanceSignal.REVISION_EXPOSURE.value,
                new_value,
                prior_value,
            )
            if identity in identities:
                continue
            identities.add(identity)
            id_payload = {
                "subject_agent_id": subject,
                "issue_key": issue_key,
                "signal": StanceSignal.REVISION_EXPOSURE.value,
                "value_key": new_value,
                "prior_value_key": prior_value,
            }
            result.append(
                StanceEvent(
                    event_id=_stable_event_id(event.event_id, id_payload),
                    subject_agent_id=subject,
                    issue_key=issue_key,
                    signal=StanceSignal.REVISION_EXPOSURE,
                    value_key=new_value,
                    prior_value_key=prior_value,
                    valid_time=event.valid_time,
                    system_record_time=event.recorded_at,
                    evidence_event_ids=(event.event_id,),
                )
            )

    return tuple(result), tuple(revisions)


def extract_routed_stance_events(
    event: EventRecord,
    backend: SemanticBackend,
    *,
    known_catalog: dict[str, list[str]] | None = None,
    max_tokens: int = 1536,
) -> ExtractionResult:
    """Extract self stance + revision relation, route exposure deterministically."""
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
        "known_issue_value_catalog": known_catalog or {},
    }
    raw = backend.complete_json(
        [
            {"role": "system", "content": ROUTED_SEMANTIC_SYSTEM},
            {
                "role": "user",
                "content": json.dumps(
                    user_payload, ensure_ascii=False, sort_keys=True
                ),
            },
        ],
        max_tokens=max_tokens,
        temperature=0.0,
    )

    first_error: Exception | None = None
    for attempt in range(2):
        try:
            payload = json.loads(raw)
            stance_events, revision_relations = _parse_routed_payload(event, payload)
            return ExtractionResult(
                stance_events=stance_events,
                repair_count=attempt,
                repair_reason=(
                    None
                    if attempt == 0
                    else f"routed semantic extraction required one repair after: {first_error}"
                ),
                revision_relations=revision_relations,
            )
        except (json.JSONDecodeError, SemanticExtractionError) as exc:
            if first_error is None:
                first_error = exc
            if attempt == 1:
                raise SemanticExtractionError(
                    f"routed stance extraction invalid after bounded repair: {exc}"
                ) from exc
            raw = backend.complete_json(
                [
                    {"role": "system", "content": ROUTED_REPAIR_SYSTEM},
                    {
                        "role": "user",
                        "content": json.dumps(
                            {
                                "event": user_payload["event"],
                                "known_issue_value_catalog": known_catalog or {},
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
    raise SemanticExtractionError("routed stance extraction failed")


__all__ = [
    "ExtractionResult",
    "SemanticBackend",
    "SemanticExtractionError",
    "RevisionRelation",
    "catalog_from_events",
    "extract_routed_stance_events",
    "extract_stance_events",
]
