"""LLM semantic-patch proposal boundary for HCL v0.4."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Protocol

from .model import (
    AssertionStatus,
    AssertionType,
    CognitiveAssertion,
    EventRecord,
    Proposition,
    SemanticPatch,
    SupportLevel,
    utc_now_iso,
)
from .schema import SchemaValidationError, validate_patch_structure


class SemanticBackend(Protocol):
    def complete_json(
        self,
        messages: list[dict[str, str]],
        *,
        max_tokens: int,
        temperature: float = 0.0,
    ) -> str:
        ...


SEMANTIC_SYSTEM = """You are the semantic proposal stage of HCL v0.4.

You do not write committed cognition state. You propose a patch that deterministic
code will validate.

Keep these record types distinct:
- SCENE_FACT: explicit task/environment fact, not automatically known by agents.
- SOURCE_ASSERTION: a source said proposition P; does not establish P as true.
- INFORMATION_EXPOSURE: an agent observed/received content; does not establish belief.
- BELIEF_ESTIMATE: evidence supports that an agent believes P; remains revisable.
- STATED_GOAL_INTENTION: an explicitly stated goal/plan; not the only hidden motive.
- LATENT_HYPOTHESIS: a candidate hidden interpretation.
- OTHER_UNKNOWN: current candidates may be incomplete.

Do not infer that receiving P means believing P.
Do not infer that a source assertion means P is world truth.
Do not use future information to rewrite historical agent state.

Return JSON only with:
{
  "propositions": [
    {
      "proposition_id": "...",
      "canonical_text": "...",
      "source_event_ids": ["..."]
    }
  ],
  "assertions": [
    {
      "assertion_id": "...",
      "assertion_type": "...",
      "subject_agent_id": null,
      "proposition_id": null,
      "hypothesis_text": null,
      "valid_time": "...",
      "evidence_event_ids": ["..."],
      "depends_on_assertion_ids": [],
      "status": "ACTIVE|UNRESOLVED",
      "support_level": null
    }
  ]
}
"""


def _stable_id(prefix: str, payload: str) -> str:
    return f"{prefix}_{hashlib.sha256(payload.encode('utf-8')).hexdigest()[:16]}"


def patch_from_mapping(
    event: EventRecord,
    payload: dict[str, Any],
    *,
    semantic_version: str,
) -> SemanticPatch:
    if not isinstance(payload, dict):
        raise SchemaValidationError("semantic backend must return a JSON object")

    propositions: list[Proposition] = []
    for raw in payload.get("propositions", []):
        if not isinstance(raw, dict):
            raise SchemaValidationError("proposition entries must be objects")
        canonical_text = str(raw.get("canonical_text", "")).strip()
        proposition_id = str(raw.get("proposition_id", "")).strip()
        if not proposition_id:
            proposition_id = _stable_id("p", f"{event.event_id}:{canonical_text}")
        source_event_ids = tuple(raw.get("source_event_ids") or [event.event_id])
        propositions.append(
            Proposition(
                proposition_id=proposition_id,
                canonical_text=canonical_text,
                polarity=str(raw.get("polarity", "POSITIVE")),
                relation_metadata=dict(raw.get("relation_metadata") or {}),
                valid_time_start=raw.get("valid_time_start"),
                valid_time_end=raw.get("valid_time_end"),
                source_event_ids=source_event_ids,
            )
        )

    assertions: list[CognitiveAssertion] = []
    now = utc_now_iso()
    for raw in payload.get("assertions", []):
        if not isinstance(raw, dict):
            raise SchemaValidationError("assertion entries must be objects")
        type_value = raw.get("assertion_type")
        try:
            assertion_type = AssertionType(type_value)
        except Exception as exc:
            raise SchemaValidationError(
                f"invalid assertion_type: {type_value!r}"
            ) from exc

        status_value = raw.get("status", "ACTIVE")
        try:
            status = AssertionStatus(status_value)
        except Exception as exc:
            raise SchemaValidationError(f"invalid status: {status_value!r}") from exc

        support_value = raw.get("support_level")
        support = None
        if support_value is not None:
            try:
                support = SupportLevel(support_value)
            except Exception as exc:
                raise SchemaValidationError(
                    f"invalid support_level: {support_value!r}"
                ) from exc

        seed = json.dumps(raw, sort_keys=True, ensure_ascii=False)
        assertion_id = str(raw.get("assertion_id", "")).strip()
        if not assertion_id:
            assertion_id = _stable_id("a", f"{event.event_id}:{seed}")

        assertions.append(
            CognitiveAssertion(
                assertion_id=assertion_id,
                assertion_type=assertion_type,
                subject_agent_id=raw.get("subject_agent_id"),
                proposition_id=raw.get("proposition_id"),
                hypothesis_text=raw.get("hypothesis_text"),
                valid_time=str(raw.get("valid_time") or event.valid_time),
                system_record_time=str(raw.get("system_record_time") or now),
                evidence_event_ids=tuple(
                    raw.get("evidence_event_ids") or [event.event_id]
                ),
                depends_on_assertion_ids=tuple(
                    raw.get("depends_on_assertion_ids") or []
                ),
                status=status,
                support_level=support,
                semantic_version=semantic_version,
            )
        )

    patch_id = _stable_id(
        "patch",
        json.dumps(payload, sort_keys=True, ensure_ascii=False)
        + f":{event.event_id}:{semantic_version}",
    )
    patch = SemanticPatch(
        patch_id=patch_id,
        event_id=event.event_id,
        semantic_version=semantic_version,
        propositions=tuple(propositions),
        assertions=tuple(assertions),
    )
    validate_patch_structure(patch)
    return patch


def propose_patch(
    event: EventRecord,
    backend: SemanticBackend,
    *,
    semantic_version: str = "v04.1",
    max_tokens: int = 2048,
) -> SemanticPatch:
    user_payload = {
        "event_id": event.event_id,
        "valid_time": event.valid_time,
        "source_id": event.source_id,
        "actor_id": event.actor_id,
        "observer_ids": list(event.observer_ids),
        "recipient_ids": list(event.recipient_ids),
        "raw_text": event.raw_text,
        "metadata": event.metadata,
    }
    raw = backend.complete_json(
        [
            {"role": "system", "content": SEMANTIC_SYSTEM},
            {
                "role": "user",
                "content": json.dumps(user_payload, ensure_ascii=False, sort_keys=True),
            },
        ],
        max_tokens=max_tokens,
        temperature=0.0,
    )
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SchemaValidationError("semantic backend returned invalid JSON") from exc
    return patch_from_mapping(
        event,
        payload,
        semantic_version=semantic_version,
    )
