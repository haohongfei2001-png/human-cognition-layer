"""Schema and invariant validation for HCL v0.4 records."""

from __future__ import annotations

from datetime import datetime

from .model import (
    AssertionType,
    CognitiveAssertion,
    EventRecord,
    Proposition,
    SemanticPatch,
)


class SchemaValidationError(ValueError):
    pass


def _require_text(value: str | None, field: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise SchemaValidationError(f"{field} must be a non-empty string")


def _parse_time(value: str, field: str) -> datetime:
    _require_text(value, field)
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise SchemaValidationError(f"{field} must be ISO-8601") from exc


def validate_event(event: EventRecord) -> None:
    _require_text(event.event_id, "event_id")
    _require_text(event.raw_text, "raw_text")
    _require_text(event.source_id, "source_id")
    _require_text(event.semantic_version, "semantic_version")
    _parse_time(event.valid_time, "valid_time")
    _parse_time(event.recorded_at, "recorded_at")


def validate_proposition(proposition: Proposition) -> None:
    _require_text(proposition.proposition_id, "proposition_id")
    _require_text(proposition.canonical_text, "canonical_text")
    if proposition.valid_time_start:
        _parse_time(proposition.valid_time_start, "valid_time_start")
    if proposition.valid_time_end:
        _parse_time(proposition.valid_time_end, "valid_time_end")


def validate_assertion(assertion: CognitiveAssertion) -> None:
    _require_text(assertion.assertion_id, "assertion_id")
    _parse_time(assertion.valid_time, "valid_time")
    _parse_time(assertion.system_record_time, "system_record_time")
    _require_text(assertion.semantic_version, "semantic_version")

    if assertion.assertion_type in {
        AssertionType.INFORMATION_EXPOSURE,
        AssertionType.BELIEF_ESTIMATE,
        AssertionType.STATED_GOAL_INTENTION,
    } and not assertion.subject_agent_id:
        raise SchemaValidationError(
            f"{assertion.assertion_type.value} requires subject_agent_id"
        )

    if assertion.assertion_type == AssertionType.LATENT_HYPOTHESIS:
        if not assertion.subject_agent_id or not assertion.hypothesis_text:
            raise SchemaValidationError(
                "LATENT_HYPOTHESIS requires subject_agent_id and hypothesis_text"
            )

    if assertion.assertion_type == AssertionType.OTHER_UNKNOWN:
        if not assertion.hypothesis_text:
            raise SchemaValidationError("OTHER_UNKNOWN requires hypothesis_text")

    if assertion.assertion_type != AssertionType.OTHER_UNKNOWN:
        if not assertion.proposition_id and not assertion.hypothesis_text:
            raise SchemaValidationError(
                f"{assertion.assertion_type.value} requires proposition_id or hypothesis_text"
            )


def validate_patch_structure(patch: SemanticPatch) -> None:
    _require_text(patch.patch_id, "patch_id")
    _require_text(patch.event_id, "event_id")
    _require_text(patch.semantic_version, "semantic_version")

    proposition_ids: set[str] = set()
    for proposition in patch.propositions:
        validate_proposition(proposition)
        if proposition.proposition_id in proposition_ids:
            raise SchemaValidationError(
                f"duplicate proposition_id in patch: {proposition.proposition_id}"
            )
        proposition_ids.add(proposition.proposition_id)

    assertion_ids: set[str] = set()
    for assertion in patch.assertions:
        validate_assertion(assertion)
        if assertion.assertion_id in assertion_ids:
            raise SchemaValidationError(
                f"duplicate assertion_id in patch: {assertion.assertion_id}"
            )
        assertion_ids.add(assertion.assertion_id)
