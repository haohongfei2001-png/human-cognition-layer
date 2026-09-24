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


__all__ = [
    "ExtractionResult",
    "SemanticBackend",
    "SemanticExtractionError",
    "catalog_from_events",
    "extract_stance_events",
]
