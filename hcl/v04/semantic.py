"""LLM semantic-patch proposal boundary for HCL v0.4."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from typing import Any, Protocol

from .model import (
    AssertionStatus,
    AssertionType,
    BeliefStance,
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
- BELIEF_ESTIMATE: evidence supports an agent stance toward the object-level proposition P.
  Use belief_stance=AFFIRM when the agent is supported as believing P.
  Use belief_stance=DENY when the agent is supported as rejecting/denying P.
  BELIEF_ESTIMATE must point to the object-level proposition P itself; do not
  create a meta-proposition such as "Alice believes P".
- STATED_GOAL_INTENTION: an explicitly stated goal/plan/intention to act; not the only hidden motive.
  A statement such as "I believe P" is a belief report, NOT a goal or intention.
- LATENT_HYPOTHESIS: a candidate hidden interpretation.
- OTHER_UNKNOWN: current candidates may be incomplete.

Do not infer that receiving P means believing P.
Do not infer that a source assertion means P is world truth.
Do not use future information to rewrite historical agent state.
Use SCENE_FACT only when the event metadata explicitly marks the content as an
environment/scene fact or the input contract otherwise explicitly declares it
as world truth.
Do not create BELIEF_ESTIMATE solely because INFORMATION_EXPOSURE occurred.
Create a belief estimate only when the event supplies additional evidence such
as explicit acceptance/rejection, prior belief evidence, or behavior that
supports the estimate.

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
      "support_level": "DIRECT_SUPPORT|INDIRECT_SUPPORT|COUNTEREVIDENCE|INSUFFICIENT|null",
      "belief_stance": "AFFIRM|DENY|null"
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
    now = event.recorded_at
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

        stance_value = raw.get("belief_stance")
        belief_stance = None
        if stance_value is not None:
            try:
                belief_stance = BeliefStance(stance_value)
            except Exception as exc:
                raise SchemaValidationError(
                    f"invalid belief_stance: {stance_value!r}"
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
                belief_stance=belief_stance,
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


SEMANTIC_REPAIR_SYSTEM = """Repair a proposed HCL v0.4 SemanticPatch so that it
matches the declared JSON schema and enum values exactly.

Do not add new facts merely to make the output valid.
Do not change SOURCE_ASSERTION into SCENE_FACT.
Do not change INFORMATION_EXPOSURE into BELIEF_ESTIMATE without independent
acceptance/rejection/behavior evidence.

Allowed support_level values are exactly:
DIRECT_SUPPORT, INDIRECT_SUPPORT, COUNTEREVIDENCE, INSUFFICIENT, or null.

BELIEF_ESTIMATE requires belief_stance AFFIRM or DENY.
Do not encode rejection as a positive belief. If Alice says "I think P is wrong",
use belief_stance=DENY for the object-level proposition P, or represent her
affirmed alternative proposition separately.

Return the corrected JSON object only.
"""


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

    last_error: Exception | None = None
    for attempt in range(2):
        try:
            payload = json.loads(raw)
            return patch_from_mapping(
                event,
                payload,
                semantic_version=semantic_version,
            )
        except (json.JSONDecodeError, SchemaValidationError) as exc:
            last_error = exc
            if attempt == 1:
                break
            raw = backend.complete_json(
                [
                    {"role": "system", "content": SEMANTIC_REPAIR_SYSTEM},
                    {
                        "role": "user",
                        "content": json.dumps(
                            {
                                "event": user_payload,
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

    if isinstance(last_error, json.JSONDecodeError):
        raise SchemaValidationError(
            "semantic backend returned invalid JSON after one repair"
        ) from last_error
    if last_error is not None:
        raise last_error
    raise SchemaValidationError("semantic patch proposal failed")



SEMANTIC_INVARIANT_REPAIR_SYSTEM = """The proposed HCL v0.4 SemanticPatch
passed basic JSON parsing but violated a deterministic cognition invariant.

Repair the semantic proposal once. Preserve supported meaning, but remove or
correct assertions that violate the invariant.

Hard rules:
- INFORMATION_EXPOSURE requires an actual observation/recipient/actor/public
  evidence path for that subject. A sentence saying an agent did NOT receive
  information is not evidence that the agent received it.
- BELIEF_ESTIMATE represents an evidence-supported stance toward object-level P.
  Use belief_stance=AFFIRM or DENY. Do not encode rejection as AFFIRM.
  Do not encode counterevidence as BELIEF_ESTIMATE with COUNTEREVIDENCE.
- SOURCE_ASSERTION is not SCENE_FACT unless the event contract establishes world
  truth.
- Do not invent new facts or new exposure events to satisfy validation.

Return the complete corrected JSON object only, using the original proposal
schema.
"""


def patch_to_mapping(patch: SemanticPatch) -> dict[str, Any]:
    propositions = [asdict(p) for p in patch.propositions]
    assertions = []
    for assertion in patch.assertions:
        item = asdict(assertion)
        item["assertion_type"] = assertion.assertion_type.value
        item["status"] = assertion.status.value
        item["support_level"] = (
            assertion.support_level.value if assertion.support_level else None
        )
        item["belief_stance"] = (
            assertion.belief_stance.value if assertion.belief_stance else None
        )
        assertions.append(item)
    return {
        "propositions": propositions,
        "assertions": assertions,
    }


def repair_patch_for_invariant(
    event: EventRecord,
    patch: SemanticPatch,
    validation_error: str,
    backend: SemanticBackend,
    *,
    semantic_version: str = "v04.1",
    max_tokens: int = 2048,
) -> SemanticPatch:
    raw = backend.complete_json(
        [
            {"role": "system", "content": SEMANTIC_INVARIANT_REPAIR_SYSTEM},
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "event": {
                            "event_id": event.event_id,
                            "valid_time": event.valid_time,
                            "source_id": event.source_id,
                            "actor_id": event.actor_id,
                            "observer_ids": list(event.observer_ids),
                            "recipient_ids": list(event.recipient_ids),
                            "raw_text": event.raw_text,
                            "metadata": event.metadata,
                        },
                        "rejected_patch": patch_to_mapping(patch),
                        "validation_error": validation_error,
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                ),
            },
        ],
        max_tokens=max_tokens,
        temperature=0.0,
    )
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SchemaValidationError(
            "semantic invariant repair returned invalid JSON"
        ) from exc
    return patch_from_mapping(
        event,
        payload,
        semantic_version=semantic_version,
    )
