"""Hypothesis-guided probe and action selection for HCL v0.4."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Protocol

from .hypotheses import HypothesisState, HypothesisTarget
from .schema import SchemaValidationError


@dataclass(frozen=True)
class ProbeOption:
    probe_id: str
    description: str


@dataclass(frozen=True)
class ActionOption:
    action_id: str
    description: str


@dataclass(frozen=True)
class ProbeDecision:
    probe_id: str
    rationale: str
    targeted_hypotheses: tuple[str, ...] = ()
    repaired: bool = False


@dataclass(frozen=True)
class ActionDecision:
    action_id: str
    rationale: str
    repaired: bool = False


class PolicyBackend(Protocol):
    def complete_json(
        self,
        messages: list[dict[str, str]],
        *,
        max_tokens: int,
        temperature: float = 0.0,
    ) -> str:
        ...


PROBE_SYSTEM = """Choose one allowed information-gathering probe.

You are given competing hypotheses about a human agent.

Rules:
- hypotheses are uncertain, not facts;
- prefer a probe that separates currently plausible hypotheses;
- avoid redundant questions when existing evidence already answers them;
- prefer low-cost/reversible information gathering when discrimination is similar;
- choose only from allowed_probes;
- do not request inaccessible evidence outside the allowed options.

Return JSON only:
{
  "probe_id": "<allowed probe id>",
  "rationale": "short evidence-grounded reason",
  "targeted_hypotheses": ["candidate labels this probe helps distinguish"]
}
"""


ACTION_SYSTEM = """Choose one allowed action using the updated evidence and
hypothesis state.

Rules:
- choose only from allowed_actions;
- do not treat a leading hypothesis as certain when alternatives remain;
- prefer an action that is appropriate under the supported evidence;
- do not claim uncertainty is resolved if it is not.

Return JSON only:
{
  "action_id": "<allowed action id>",
  "rationale": "short evidence-grounded reason"
}
"""


REPAIR_SYSTEM = """Repair the policy output to match the required JSON schema.

Use only the supplied allowed option IDs.
Do not add new probes/actions.
A non-empty rationale is required.
Return corrected JSON only.
"""


class HypothesisGuidedPolicy:
    @staticmethod
    def _state_payload(state: HypothesisState) -> dict:
        return {
            "target_id": state.target_id,
            "version": state.version,
            "candidates": [
                {
                    "label": c.label,
                    "description": c.description,
                    "status": c.status.value,
                    "support_event_ids": list(c.support_event_ids),
                    "counterevidence_event_ids": list(
                        c.counterevidence_event_ids
                    ),
                    "unresolved_event_ids": list(c.unresolved_event_ids),
                    "rationale": c.rationale,
                }
                for c in state.candidates
            ],
        }

    @staticmethod
    def _target_payload(target: HypothesisTarget) -> dict:
        return {
            "target_id": target.target_id,
            "subject_agent_id": target.subject_agent_id,
            "target_kind": target.target_kind,
            "question": target.question,
            "candidate_definitions": list(target.candidate_definitions),
        }

    @staticmethod
    def _repair(
        backend: PolicyBackend,
        *,
        invalid_output: str,
        error: str,
        contract: dict,
    ) -> str:
        return backend.complete_json(
            [
                {"role": "system", "content": REPAIR_SYSTEM},
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "invalid_output": invalid_output,
                            "validation_error": error,
                            "contract": contract,
                        },
                        ensure_ascii=False,
                        sort_keys=True,
                    ),
                },
            ],
            max_tokens=768,
            temperature=0.0,
        )

    def choose_probe(
        self,
        target: HypothesisTarget,
        hypothesis_state: HypothesisState,
        evidence: list[dict],
        probes: tuple[ProbeOption, ...] | list[ProbeOption],
        backend: PolicyBackend,
    ) -> ProbeDecision:
        options = tuple(probes)
        allowed = {x.probe_id for x in options}
        candidate_labels = {c.label for c in hypothesis_state.candidates}
        contract = {
            "allowed_probe_ids": sorted(allowed),
            "candidate_labels": sorted(candidate_labels),
        }
        raw = backend.complete_json(
            [
                {"role": "system", "content": PROBE_SYSTEM},
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "target": self._target_payload(target),
                            "hypothesis_state": self._state_payload(
                                hypothesis_state
                            ),
                            "evidence": evidence,
                            "allowed_probes": [
                                {
                                    "probe_id": x.probe_id,
                                    "description": x.description,
                                }
                                for x in options
                            ],
                        },
                        ensure_ascii=False,
                        sort_keys=True,
                    ),
                },
            ],
            max_tokens=768,
            temperature=0.0,
        )

        for attempt in range(2):
            try:
                payload = json.loads(raw)
                probe_id = str(payload.get("probe_id", "")).strip()
                rationale = str(payload.get("rationale", "")).strip()
                targeted = tuple(
                    str(x).strip().upper()
                    for x in (payload.get("targeted_hypotheses") or [])
                    if str(x).strip()
                )
                if probe_id not in allowed:
                    raise SchemaValidationError(
                        f"invalid probe_id: {probe_id!r}"
                    )
                if not rationale:
                    raise SchemaValidationError("probe rationale required")
                invalid_targets = set(targeted) - candidate_labels
                if invalid_targets:
                    raise SchemaValidationError(
                        "unknown targeted hypotheses: "
                        f"{sorted(invalid_targets)}"
                    )
                return ProbeDecision(
                    probe_id=probe_id,
                    rationale=rationale,
                    targeted_hypotheses=targeted,
                    repaired=attempt == 1,
                )
            except (json.JSONDecodeError, SchemaValidationError) as exc:
                if attempt == 1:
                    raise
                raw = self._repair(
                    backend,
                    invalid_output=raw,
                    error=str(exc),
                    contract=contract,
                )
        raise AssertionError("unreachable")

    def choose_action(
        self,
        target: HypothesisTarget,
        hypothesis_state: HypothesisState,
        evidence: list[dict],
        actions: tuple[ActionOption, ...] | list[ActionOption],
        backend: PolicyBackend,
    ) -> ActionDecision:
        options = tuple(actions)
        allowed = {x.action_id for x in options}
        contract = {"allowed_action_ids": sorted(allowed)}
        raw = backend.complete_json(
            [
                {"role": "system", "content": ACTION_SYSTEM},
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "target": self._target_payload(target),
                            "hypothesis_state": self._state_payload(
                                hypothesis_state
                            ),
                            "evidence": evidence,
                            "allowed_actions": [
                                {
                                    "action_id": x.action_id,
                                    "description": x.description,
                                }
                                for x in options
                            ],
                        },
                        ensure_ascii=False,
                        sort_keys=True,
                    ),
                },
            ],
            max_tokens=768,
            temperature=0.0,
        )

        for attempt in range(2):
            try:
                payload = json.loads(raw)
                action_id = str(payload.get("action_id", "")).strip()
                rationale = str(payload.get("rationale", "")).strip()
                if action_id not in allowed:
                    raise SchemaValidationError(
                        f"invalid action_id: {action_id!r}"
                    )
                if not rationale:
                    raise SchemaValidationError("action rationale required")
                return ActionDecision(
                    action_id=action_id,
                    rationale=rationale,
                    repaired=attempt == 1,
                )
            except (json.JSONDecodeError, SchemaValidationError) as exc:
                if attempt == 1:
                    raise
                raw = self._repair(
                    backend,
                    invalid_output=raw,
                    error=str(exc),
                    contract=contract,
                )
        raise AssertionError("unreachable")
