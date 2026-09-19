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
from hcl.v03.backends import OpenAICompatibleBackend

from sotopia.agents.llm_agent import LLMAgent
from sotopia.messages import AgentAction, Observation


ACTION_SYSTEM = """You are the action generator for a SOTOPIA social agent using HCL v0.3.

You receive:
- the agent's private goal;
- the visible interaction history;
- the current SOTOPIA observation;
- the frozen HCL cognition state;
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
6. Keep the action natural and goal-directed.
7. Do not mention HCL or internal reasoning.
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
        self._hcl_last_state: dict[str, Any] | None = None
        self._hcl_turn_log: list[dict[str, Any]] = []

    def _history_text(self) -> str:
        return "\n".join(
            message.to_natural_language() for _, message in self.inbox
        )

    def _turn_input(self, obs: Observation) -> str:
        return (
            f"你正在扮演 {self.agent_name}。\n"
            f"你的私有目标：{self.goal}\n\n"
            "你目前可见的互动历史：\n"
            f"{self._history_text()}\n\n"
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
        self.recv_message("Environment", obs)

        # SOTOPIA normally sets goals before the episode loop. Keep a robust
        # fallback for standalone smoke tests.
        if self._goal is None:
            self._goal = "Act naturally and coherently in the interaction."

        if len(obs.available_actions) == 1 and "none" in obs.available_actions:
            return AgentAction(action_type="none", argument="", to=[])

        turn_input = self._turn_input(obs)
        state = self.hcl_loop.build_state(turn_input)
        self._hcl_last_state = state

        draft = self._generate_action(
            turn_input=turn_input,
            state=state,
            obs=obs,
        )
        first_check = self.hcl_loop.check(
            turn_input,
            state,
            self._action_to_text(draft),
        )

        candidate = draft
        if first_check.get("status") == "REVISE":
            candidate = self._generate_action(
                turn_input=turn_input,
                state=state,
                obs=obs,
                checker=first_check,
                previous=draft,
            )

        final_check = self.hcl_loop.check(
            turn_input,
            state,
            self._action_to_text(candidate),
        )
        final_action = candidate
        if final_check.get("status") == "REVISE":
            final_action = self._generate_action(
                turn_input=turn_input,
                state=state,
                obs=obs,
                checker=final_check,
                previous=candidate,
            )

        self._hcl_turn_log.append(
            {
                "turn_number": obs.turn_number,
                "state": state,
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
        self._hcl_turn_log = []
