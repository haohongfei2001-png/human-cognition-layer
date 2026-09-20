"""SOTOPIA integration for the frozen HCL v0.3 cognition layer.

This adapter keeps HCL always-on while preserving SOTOPIA's public agent
interface. It rebuilds cognition state from the full visible history each turn;
incremental state updates can be optimized later without changing frozen state
semantics.
"""

from __future__ import annotations

import json
import os
from typing import Any

from hcl.v03.answer_loop import HCLAnswerLoop, extract_json
from hcl.v03.action_checker import HCLActionChecker
from hcl.v03.backends import OpenAICompatibleBackend
from hcl.v03.decision_policy import HCLDecisionPolicy

from sotopia.agents.llm_agent import LLMAgent
from sotopia.messages import AgentAction, Observation


ACTION_SYSTEM = """You are the action generator for a SOTOPIA social agent using HCL v0.3.

You receive:
- the agent's private goal;
- the visible interaction history;
- the current SOTOPIA observation;
- the frozen HCL cognition state;
- the HCL Decision Policy plan;
- the currently available action types.

Choose one valid action that helps the agent pursue its goal while remaining
socially coherent and faithful to the HCL state.

Return JSON only:
{
  "action_type": "none|speak|non-verbal communication|action|leave",
  "argument": "...",
  "to": []
}

Rules:
1. action_type MUST be one of the available actions supplied by the environment.
2. Use an empty argument for none/leave unless content is needed by the action.
3. Do not invent private information the agent has not observed.
4. Do not collapse uncertain motives/beliefs into certainty.
5. Do not create unnecessary doubt when the HCL state is SIMPLE/low.
6. Use the Decision Policy to convert cautious cognition into useful action:
   targeted probing, alternative routes, commitment, or exit as appropriate.
7. Do not treat uncertainty as a reason for passivity when a reversible,
   decision-relevant action is available.
8. Keep the action natural and goal-directed.
9. Do not mention HCL or internal reasoning.
"""


ACTION_REVISION_SYSTEM = """You are revising a SOTOPIA AgentAction after HCL consistency checking.

Return JSON only:
{
  "action_type": "none|speak|non-verbal communication|action|leave",
  "argument": "...",
  "to": []
}

Correct every material checker issue while preserving the useful intent of the
original action. Use only currently available action types. Do not expose HCL
internals.
"""


def _parse_custom_model(model_name: str) -> tuple[str, str, str]:
    """Return (api_model, base_url, api_key)."""
    if model_name.startswith("custom/"):
        if "@" not in model_name:
            raise ValueError(
                "custom model must use custom/<model>@<base_url> syntax"
            )
        model_part, base_url = model_name.split("@", 1)
        api_model = model_part.replace("custom/", "", 1)
        api_key = (
            os.getenv("CUSTOM_API_KEY")
            or os.getenv("DEEPSEEK_API_KEY")
            or os.getenv("OPENAI_API_KEY")
        )
        if not api_key:
            raise RuntimeError(
                "CUSTOM_API_KEY / DEEPSEEK_API_KEY / OPENAI_API_KEY is required"
            )
        return api_model, base_url, api_key

    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("DEEPSEEK_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    if not api_key:
        raise RuntimeError("API key is required for HCLSocialAgent")
    return model_name, base_url, api_key


BASELINE_ACTION_SYSTEM = """You are a SOTOPIA social agent.

You receive:
- your identity;
- your private social goal;
- the visible interaction history;
- the current environment observation;
- the currently available action types.

Choose one valid next action that helps pursue your private goal while keeping
the interaction natural and coherent.

Return JSON only:
{
  "action_type": "none|speak|non-verbal communication|action|leave",
  "argument": "...",
  "to": []
}

Rules:
1. action_type MUST be one of the available actions supplied by the environment.
2. Use an empty argument for none/leave.
3. Stay consistent with the visible history.
4. Do not invent facts or private information not available to the agent.
5. Keep the action natural and goal-directed.
"""


class DirectSocialAgent(LLMAgent):
    """Fair DeepSeek baseline using the same direct transport as HCLSocialAgent.

    SOTOPIA's stock LLMAgent currently requests a response_format unsupported
    by the DeepSeek endpoint and silently falls back to "none". This adapter
    preserves ordinary goal/history-driven social action generation while
    removing that transport incompatibility. It has no HCL state or checker.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        api_model, base_url, api_key = _parse_custom_model(self.model_name)
        self.direct_backend = OpenAICompatibleBackend(
            api_key=api_key,
            base_url=base_url,
            model=api_model,
            seed=42,
        )

    def _history_text_direct(self) -> str:
        return "\n".join(
            message.to_natural_language() for _, message in self.inbox
        )

    async def aact(self, obs: Observation) -> AgentAction:
        history_before = self._history_text_direct()
        self.recv_message("Environment", obs)

        if self._goal is None:
            self._goal = "Act naturally and coherently in the interaction."

        if len(obs.available_actions) == 1 and "none" in obs.available_actions:
            return AgentAction(action_type="none", argument="", to=[])

        payload = (
            f"【agent】\n{self.agent_name}\n\n"
            f"【private goal】\n{self.goal}\n\n"
            "【visible history】\n"
            f"{history_before}\n\n"
            "【current observation】\n"
            f"{obs.to_natural_language()}\n\n"
            "【available actions】\n"
            + json.dumps(obs.available_actions, ensure_ascii=False)
        )

        raw = self.direct_backend.complete(
            [
                {"role": "system", "content": BASELINE_ACTION_SYSTEM},
                {"role": "user", "content": payload},
            ],
            max_tokens=4096,
            temperature=0.0,
        )
        parsed = extract_json(raw)
        if parsed is None:
            return AgentAction(action_type="none", argument="", to=[])

        action_type = str(parsed.get("action_type", "none")).strip()
        if action_type not in obs.available_actions:
            action_type = (
                "none" if "none" in obs.available_actions else obs.available_actions[0]
            )

        argument = str(parsed.get("argument", ""))
        to_value = parsed.get("to", [])
        to = [str(x) for x in to_value] if isinstance(to_value, list) else []

        if action_type in {"none", "leave"}:
            argument = ""

        return AgentAction(
            action_type=action_type,  # type: ignore[arg-type]
            argument=argument,
            to=to,
        )


class HCLSocialAgent(LLMAgent):
    """SOTOPIA LLMAgent-compatible agent with always-on HCL cognition."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        api_model, base_url, api_key = _parse_custom_model(self.model_name)
        backend = OpenAICompatibleBackend(
            api_key=api_key,
            base_url=base_url,
            model=api_model,
            seed=42,
        )
        self.hcl_loop = HCLAnswerLoop(backend)
        self.decision_policy = HCLDecisionPolicy(backend)
        self.action_checker = HCLActionChecker(backend)
        self._hcl_last_state: dict[str, Any] | None = None
        self._hcl_last_decision_plan: dict[str, Any] | None = None
        self._hcl_turn_log: list[dict[str, Any]] = []

    def _history_text(self) -> str:
        return "\n".join(
            message.to_natural_language() for _, message in self.inbox
        )

    def _turn_input(self, obs: Observation, *, history_before: str) -> str:
        return (
            f"你正在扮演 {self.agent_name}。\n"
            f"你的私有目标：{self.goal}\n\n"
            "你目前可见的互动历史：\n"
            f"{history_before}\n\n"
            "当前环境观察：\n"
            f"{obs.to_natural_language()}\n\n"
            f"当前可用动作：{', '.join(obs.available_actions)}\n\n"
            "任务：在下一步行动前，建立对当前社会互动的认知状态。"
        )

    @staticmethod
    def _action_to_text(action: AgentAction) -> str:
        return json.dumps(action.model_dump(), ensure_ascii=False)

    def _generate_action(
        self,
        *,
        turn_input: str,
        state: dict[str, Any],
        decision_plan: dict[str, Any],
        obs: Observation,
        checker: dict[str, Any] | None = None,
        previous: AgentAction | None = None,
    ) -> AgentAction:
        if checker is None:
            system = ACTION_SYSTEM
            payload = (
                "【turn context】\n"
                + turn_input
                + "\n\n【HCL cognition state】\n"
                + json.dumps(state, ensure_ascii=False, indent=2)
                + "\n\n【HCL Decision Policy】\n"
                + json.dumps(decision_plan, ensure_ascii=False, indent=2)
                + "\n\n【available actions】\n"
                + json.dumps(obs.available_actions, ensure_ascii=False)
            )
        else:
            system = ACTION_REVISION_SYSTEM
            payload = (
                "【turn context】\n"
                + turn_input
                + "\n\n【HCL cognition state】\n"
                + json.dumps(state, ensure_ascii=False, indent=2)
                + "\n\n【HCL Decision Policy】\n"
                + json.dumps(decision_plan, ensure_ascii=False, indent=2)
                + "\n\n【available actions】\n"
                + json.dumps(obs.available_actions, ensure_ascii=False)
                + "\n\n【previous action】\n"
                + self._action_to_text(previous or AgentAction(
                    action_type="none", argument="", to=[]
                ))
                + "\n\n【HCL checker】\n"
                + json.dumps(checker, ensure_ascii=False, indent=2)
            )

        raw = self.hcl_loop.backend.complete(
            [
                {"role": "system", "content": system},
                {"role": "user", "content": payload},
            ],
            max_tokens=4096,
            temperature=0.0,
        )
        parsed = extract_json(raw)
        if parsed is None:
            return AgentAction(action_type="none", argument="", to=[])

        action_type = str(parsed.get("action_type", "none")).strip()
        if action_type not in obs.available_actions:
            action_type = "none" if "none" in obs.available_actions else obs.available_actions[0]

        argument = str(parsed.get("argument", ""))
        to_value = parsed.get("to", [])
        to = [str(x) for x in to_value] if isinstance(to_value, list) else []

        if action_type in {"none", "leave"}:
            argument = ""

        return AgentAction(
            action_type=action_type,  # type: ignore[arg-type]
            argument=argument,
            to=to,
        )

    async def aact(self, obs: Observation) -> AgentAction:
        # Capture prior visible history before appending the current observation.
        # This prevents the current observation from being duplicated in the
        # cognition/action prompt.
        history_before = self._history_text()
        self.recv_message("Environment", obs)

        # SOTOPIA normally sets goals before the episode loop. Keep a robust
        # fallback for standalone smoke tests.
        if self._goal is None:
            self._goal = "Act naturally and coherently in the interaction."

        turn_input = self._turn_input(obs, history_before=history_before)
        state = self.hcl_loop.build_state(turn_input)
        self._hcl_last_state = state

        # Canonical always-on rule: even environment-forced no-op turns pass
        # through HCL cognition and are logged. No extra model call is required
        # for decision policy when the environment exposes no actionable choice.
        if len(obs.available_actions) == 1 and "none" in obs.available_actions:
            decision_plan = {
                "goal_progress_state": "OPEN",
                "hard_constraints": ["Environment currently allows only the none action."],
                "soft_constraints": [],
                "critical_information_gap": "",
                "strategy_type": "DEFER",
                "chosen_action_intent": "Observe this turn and take no action because none is the only available action.",
                "expected_goal_progress": "low",
                "information_gain": "medium",
                "reversibility": "high",
                "social_risk": "low",
                "decision_note": "Forced no-op by environment action mask; HCL cognition still updated.",
            }
            self._hcl_last_decision_plan = decision_plan
            final_action = AgentAction(action_type="none", argument="", to=[])
            self._hcl_turn_log.append(
                {
                    "turn_number": obs.turn_number,
                    "forced_noop": True,
                    "state": state,
                    "decision_plan": decision_plan,
                    "draft": final_action.model_dump(),
                    "first_check": {"status": "PASS", "violations": []},
                    "candidate": final_action.model_dump(),
                    "final_check": {"status": "PASS", "violations": []},
                    "final_action": final_action.model_dump(),
                }
            )
            return final_action

        decision_plan = self.decision_policy.build_plan(
            private_goal=self.goal,
            visible_context=turn_input,
            state=state,
            available_actions=list(obs.available_actions),
        )
        self._hcl_last_decision_plan = decision_plan

        draft = self._generate_action(
            turn_input=turn_input,
            state=state,
            decision_plan=decision_plan,
            obs=obs,
        )
        first_check = self.action_checker.check(
            turn_context=turn_input,
            state=state,
            decision_plan=decision_plan,
            available_actions=list(obs.available_actions),
            candidate_action=draft.model_dump(),
        )

        candidate = draft
        if first_check.get("status") == "REVISE":
            candidate = self._generate_action(
                turn_input=turn_input,
                state=state,
                decision_plan=decision_plan,
                obs=obs,
                checker=first_check,
                previous=draft,
            )

        final_check = self.action_checker.check(
            turn_context=turn_input,
            state=state,
            decision_plan=decision_plan,
            available_actions=list(obs.available_actions),
            candidate_action=candidate.model_dump(),
        )
        final_action = candidate
        if final_check.get("status") == "REVISE":
            final_action = self._generate_action(
                turn_input=turn_input,
                state=state,
                decision_plan=decision_plan,
                obs=obs,
                checker=final_check,
                previous=candidate,
            )

        self._hcl_turn_log.append(
            {
                "turn_number": obs.turn_number,
                "forced_noop": False,
                "state": state,
                "decision_plan": decision_plan,
                "draft": draft.model_dump(),
                "first_check": first_check,
                "candidate": candidate.model_dump(),
                "final_check": final_check,
                "final_action": final_action.model_dump(),
            }
        )
        return final_action

    def reset(self) -> None:
        super().reset()
        self._hcl_last_state = None
        self._hcl_last_decision_plan = None
        self._hcl_turn_log = []
