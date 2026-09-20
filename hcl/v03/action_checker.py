"""Action-specific HCL checker for interactive decisions.

This checker is intentionally separate from the generic answer checker. An
interactive agent may rationally act while uncertainty remains. The checker
verifies factual/epistemic consistency, hard constraints, and Decision Policy
alignment without equating action under uncertainty with a claim of certainty.
"""

from __future__ import annotations

import json
from typing import Any

from hcl.v03.answer_loop import ChatBackend, extract_json


ACTION_CHECK_SYSTEM = """You are the HCL v0.3 Action Checker.

You receive:
1. the visible turn context;
2. the frozen HCL cognition state;
3. the HCL Decision Policy plan;
4. the currently available action types;
5. a candidate AgentAction.

Your job is to check the action, not to reconsider the whole strategy from
scratch.

Critical distinction:
- choosing an action while uncertainty remains is NOT the same as asserting
  that the uncertainty has been resolved;
- a reversible or conditional action can be correct under uncertainty;
- do not reject such an action merely because a missing bridge remains.

Also distinguish:
- world facts and explicit hard constraints;
- explicit consent / legal / safety boundaries;
- prior provisional plans or tentative self-statements.
A later strategy may legitimately revise a provisional intention when the
situation changes. That is not automatically a factual contradiction.

Check these violation families:
- INVALID_ACTION_TYPE: action_type is unavailable.
- HARD_CONSTRAINT: action violates an explicit hard constraint, consent
  boundary, or clear legal/safety constraint represented in the state/plan.
- INFORMATION_ACCESS: action relies on private information the actor does not
  have.
- EPISTEMIC_ASSERTION: action language states an unresolved proposition as
  known/verified fact.
- UNSUPPORTED_INVENTION: action introduces a material unsupported fact.
- PLAN_MISMATCH: action materially abandons or reverses the Decision Policy
  intent without a reason grounded in the visible context.
- IRREVERSIBILITY_MISMATCH: plan depends on reversibility/contingency but the
  action removes that protection.
- LOOPING: plan says a probe route is exhausted or low-value, but the action
  simply repeats the same probe.

Rules:
1. A deliberate commitment under uncertainty may PASS if the Decision Policy
   explicitly selected it and hard constraints are preserved.
2. Do not treat an earlier tentative statement by the agent as an immutable
   fact unless it was an explicit commitment that remains binding.
3. Do not infer that taking an action means the agent believes every uncertain
   proposition is resolved.
4. Judge the candidate against the supplied Decision Policy, while still
   independently enforcing hard factual and constraint consistency.
5. PASS requires zero material violations.

Return JSON only:
{
  "status": "PASS|REVISE",
  "violations": [
    {
      "type": "INVALID_ACTION_TYPE|HARD_CONSTRAINT|INFORMATION_ACCESS|EPISTEMIC_ASSERTION|UNSUPPORTED_INVENTION|PLAN_MISMATCH|IRREVERSIBILITY_MISMATCH|LOOPING",
      "explanation": "..."
    }
  ],
  "revision_instruction": "..."
}
"""


class HCLActionChecker:
    def __init__(
        self,
        backend: ChatBackend,
        *,
        max_tokens: int = 4096,
    ) -> None:
        self.backend = backend
        self.max_tokens = max_tokens

    def check(
        self,
        *,
        turn_context: str,
        state: dict[str, Any],
        decision_plan: dict[str, Any],
        available_actions: list[str],
        candidate_action: dict[str, Any],
    ) -> dict[str, Any]:
        payload = (
            "【turn context】\n"
            + turn_context
            + "\n\n【frozen HCL cognition state】\n"
            + json.dumps(state, ensure_ascii=False, indent=2)
            + "\n\n【HCL Decision Policy】\n"
            + json.dumps(decision_plan, ensure_ascii=False, indent=2)
            + "\n\n【available actions】\n"
            + json.dumps(available_actions, ensure_ascii=False)
            + "\n\n【candidate AgentAction】\n"
            + json.dumps(candidate_action, ensure_ascii=False, indent=2)
        )

        for attempt in range(3):
            suffix = ""
            if attempt:
                suffix = (
                    "\n\nPrevious checker output was not valid JSON. "
                    "Return exactly one complete JSON object and no other text."
                )
            raw = self.backend.complete(
                [
                    {"role": "system", "content": ACTION_CHECK_SYSTEM},
                    {"role": "user", "content": payload + suffix},
                ],
                max_tokens=self.max_tokens,
                temperature=0.0,
            )
            result = extract_json(raw)
            if result is not None:
                return self._normalize(result)

        return {
            "status": "REVISE",
            "violations": [
                {
                    "type": "UNSUPPORTED_INVENTION",
                    "explanation": (
                        "Action checker returned no valid structured verdict "
                        "after bounded retries."
                    ),
                }
            ],
            "revision_instruction": (
                "Regenerate the action directly from the frozen cognition state "
                "and Decision Policy, preserving hard constraints and explicit "
                "contingencies."
            ),
        }

    @staticmethod
    def _normalize(result: dict[str, Any]) -> dict[str, Any]:
        status = str(result.get("status", "")).upper()
        result["status"] = status if status in {"PASS", "REVISE"} else "REVISE"
        if not isinstance(result.get("violations"), list):
            result["violations"] = []
        if not isinstance(result.get("revision_instruction"), str):
            result["revision_instruction"] = ""
        return result
