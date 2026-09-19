"""HCL v0.3 action decision policy.

This layer sits after the frozen cognition state and before action generation.

It does not change HCL v0.3 state semantics. Its purpose is to prevent a
common implementation failure: translating epistemic caution into behavioral
passivity. The policy should use uncertainty to choose better probes,
reversible actions, and alternative routes while still respecting explicit
constraints and agent-specific information access.
"""

from __future__ import annotations

import json
from typing import Any

from hcl.v03.answer_loop import ChatBackend, extract_json


DECISION_POLICY_SYSTEM = """You are the HCL v0.3 Decision Policy.

You receive:
- the acting agent's private goal;
- the interaction context visible to that agent;
- the frozen HCL cognition state;
- currently available action types.

You do NOT change the HCL cognition state. Convert it into a compact action
strategy.

Core rules:
1. Epistemic uncertainty is not an instruction to become passive.
2. Preserve explicit boundaries and commitments. Do not assume a stated hard
   limit is false merely because another agent privately suspects more capacity.
3. If a critical unknown could materially change the next action, prefer a
   specific low-cost information probe with high decision value.
4. If the direct route to the goal is blocked, look for an alternative route to
   the underlying goal instead of merely repeating the blocked request or giving
   up.
5. Prefer reversible probes before irreversible commitments when uncertainty is
   material.
6. Do not sacrifice a known useful opportunity merely to reduce uncertainty.
7. Do not pursue goal score by coercing past explicit non-consent or by knowingly
   violating clear social/legal constraints.
8. Distinguish world truth from the acting agent's information access. Strategy
   may use only what the acting agent knows, observes, or can reasonably infer.
9. Avoid generic politeness as a substitute for goal progress. Be socially
   coherent AND instrumentally useful.
10. Stop, defer, or exit when further action has low expected value. Do not
    endlessly repeat the same request.

Return JSON only:
{
  "goal_progress_state": "OPEN|PARTIAL|BLOCKED|ACHIEVED",
  "hard_constraints": ["..."],
  "soft_constraints": ["..."],
  "critical_information_gap": "...",
  "strategy_type": "DIRECT_PROGRESS|INFORMATION_PROBE|ALTERNATIVE_PATH|COMMIT|DEFER|EXIT",
  "chosen_action_intent": "...",
  "expected_goal_progress": "low|medium|high",
  "information_gain": "low|medium|high",
  "reversibility": "low|medium|high",
  "social_risk": "low|medium|high",
  "decision_note": "..."
}

Use the same natural language as the supplied context for explanatory strings.
Do not write the final dialogue/action itself.
"""


class HCLDecisionPolicy:
    def __init__(
        self,
        backend: ChatBackend,
        *,
        max_tokens: int = 4096,
    ) -> None:
        self.backend = backend
        self.max_tokens = max_tokens

    def build_plan(
        self,
        *,
        private_goal: str,
        visible_context: str,
        state: dict[str, Any],
        available_actions: list[str],
    ) -> dict[str, Any]:
        payload = (
            "【private goal】\n"
            + private_goal
            + "\n\n【visible context】\n"
            + visible_context
            + "\n\n【frozen HCL cognition state】\n"
            + json.dumps(state, ensure_ascii=False, indent=2)
            + "\n\n【available action types】\n"
            + json.dumps(available_actions, ensure_ascii=False)
        )

        for attempt in range(3):
            suffix = ""
            if attempt:
                suffix = (
                    "\n\nPrevious output was not a valid decision-plan JSON. "
                    "Return exactly one complete JSON object and no other text."
                )
            raw = self.backend.complete(
                [
                    {"role": "system", "content": DECISION_POLICY_SYSTEM},
                    {"role": "user", "content": payload + suffix},
                ],
                max_tokens=self.max_tokens,
                temperature=0.0,
            )
            plan = extract_json(raw)
            if plan is not None:
                return self._normalize(plan)

        raise RuntimeError("HCL decision policy returned no valid JSON after 3 attempts")

    @staticmethod
    def _normalize(plan: dict[str, Any]) -> dict[str, Any]:
        progress = str(plan.get("goal_progress_state", "")).upper()
        if progress not in {"OPEN", "PARTIAL", "BLOCKED", "ACHIEVED"}:
            progress = "OPEN"
        plan["goal_progress_state"] = progress

        strategy = str(plan.get("strategy_type", "")).upper()
        if strategy not in {
            "DIRECT_PROGRESS",
            "INFORMATION_PROBE",
            "ALTERNATIVE_PATH",
            "COMMIT",
            "DEFER",
            "EXIT",
        }:
            strategy = "INFORMATION_PROBE"
        plan["strategy_type"] = strategy

        for key in ("hard_constraints", "soft_constraints"):
            if not isinstance(plan.get(key), list):
                plan[key] = []

        for key in (
            "critical_information_gap",
            "chosen_action_intent",
            "decision_note",
        ):
            if not isinstance(plan.get(key), str):
                plan[key] = ""

        for key in (
            "expected_goal_progress",
            "information_gain",
            "reversibility",
            "social_risk",
        ):
            value = str(plan.get(key, "")).lower()
            plan[key] = value if value in {"low", "medium", "high"} else "medium"

        return plan
