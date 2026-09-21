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
- recent HCL decision/action history, when available;
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
   up. Taxonomy: use ALTERNATIVE_PATH when a hard constraint blocks the primary
   mechanism and meaningful progress now depends on a different mechanism
   (for example matching, substitution, recruitment, or another authorized
   route), even if the action also accepts already-available partial progress.
   Reserve DIRECT_PROGRESS for progress through the same still-viable primary
   mechanism.
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
11. Distinguish a current negotiating position from a hard constraint. Opening
    asks/offers, tentative plans, preferences, "around X", "maybe X", and current
    targets are soft by default. Treat a position as hard only when there is
    evidence such as explicit final/firm/floor/ceiling/cap/will-not language,
    explicit non-consent, or an external legal/policy/safety/resource limit.
12. Information probes are interventions, not passive observations. Before
    asking an open-ended budget/preference question, consider whether it may
    invite a low self-anchor, harden a tentative position, consume option value,
    or reveal an unnecessary private constraint.
13. A concrete bounded proposal can both advance the goal and reveal
    flexibility. When the acting agent has a concrete target, no hard constraint
    rules it out, rejection is reversible, and the proposal is socially/legal/
    safety compatible, prefer DIRECT_PROGRESS over generic preference elicitation
    when it has comparable information value and better expected goal progress.
14. Transition from probing to progress once enough decision-relevant
    information exists. Do not keep collecting generic motivation/comfort/
    preference information when a safe materially useful proposal can be made.
15. Do not EXIT merely because an opening ask/offer misses the private target.
    If no incompatible hard floor/cap is known, normally make at least one
    bounded counterproposal first. EXIT becomes appropriate after an explicit
    incompatible hard boundary, repeated bounded proposals establishing
    infeasibility, or negligible marginal value.
16. Verification has a finite budget. Treat materially equivalent attempts to
    resolve the same information gap as one probe family. Use recent decision/
    action history to count prior attempts; do not reset the budget merely by
    rephrasing the same question or repeating the same external action.
17. Before choosing INFORMATION_PROBE, decide whether the proposed probe can
    produce a NEW OBSERVABLE result inside the current interaction interface and
    relevant time horizon. If the result is off-interface, unavailable, or has
    already failed to appear after equivalent attempts, its marginal information
    value is low even if the underlying fact remains important.
18. If two or more materially equivalent verification attempts have produced no
    new decision-relevant evidence, normally mark that probe family EXHAUSTED.
    A further probe is justified only if a genuinely new channel/evidence source
    is available and can plausibly resolve the gap.
19. Account explicitly for option decay. When waiting or repeated probing can
    destroy a useful opportunity, compare the cost of waiting with the risk of
    acting. Prefer a bounded constraint-respecting reversible fallback when one
    exists.
20. When verification is EXHAUSTED or UNRESOLVABLE_IN_INTERFACE, do not fabricate
    a resolution and do not silently treat the uncertain proposition as true.
    Set fallback_required=true and choose the best safe fallback:
    conditional/reversible commitment, alternative path, defer, or exit.
21. Hard legal, ownership, consent, and safety constraints remain binding. Probe
    exhaustion is never permission to cross a hard boundary.

Return JSON only:
{
  "goal_progress_state": "OPEN|PARTIAL|BLOCKED|ACHIEVED",
  "hard_constraints": ["..."],
  "soft_constraints": ["..."],
  "critical_information_gap": "...",
  "verification_status": "NOT_NEEDED|RESOLVABLE|UNRESOLVABLE_IN_INTERFACE|EXHAUSTED",
  "equivalent_probe_count": 0,
  "option_decay": "low|medium|high",
  "fallback_required": false,
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
        max_tokens: int = 8192,
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
        decision_history: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        payload = (
            "【private goal】\n"
            + private_goal
            + "\n\n【visible context】\n"
            + visible_context
            + "\n\n【frozen HCL cognition state】\n"
            + json.dumps(state, ensure_ascii=False, indent=2)
            + "\n\n【recent HCL decision/action history】\n"
            + json.dumps(decision_history or [], ensure_ascii=False, indent=2)
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

        verification = str(plan.get("verification_status", "")).upper()
        if verification not in {
            "NOT_NEEDED",
            "RESOLVABLE",
            "UNRESOLVABLE_IN_INTERFACE",
            "EXHAUSTED",
        }:
            verification = "NOT_NEEDED"
        plan["verification_status"] = verification

        try:
            probe_count = int(plan.get("equivalent_probe_count", 0))
        except (TypeError, ValueError):
            probe_count = 0
        plan["equivalent_probe_count"] = max(0, probe_count)

        fallback = plan.get("fallback_required", False)
        if isinstance(fallback, bool):
            normalized_fallback = fallback
        else:
            normalized_fallback = str(fallback).strip().lower() in {
                "true",
                "1",
                "yes",
            }
        if verification in {"EXHAUSTED", "UNRESOLVABLE_IN_INTERFACE"}:
            normalized_fallback = True
        plan["fallback_required"] = normalized_fallback

        for key in (
            "expected_goal_progress",
            "information_gain",
            "reversibility",
            "social_risk",
            "option_decay",
        ):
            value = str(plan.get(key, "")).lower()
            plan[key] = value if value in {"low", "medium", "high"} else "medium"

        return plan
