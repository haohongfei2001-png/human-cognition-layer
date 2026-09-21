#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from hcl.integrations.sotopia_agent import DirectSocialAgent, HCLSocialAgent

from sotopia.agents import Agents
from sotopia.agents.llm_agent import LLMAgent
from sotopia.database import (
    AgentProfile,
    EnvAgentComboStorage,
    EnvironmentProfile,
    SotopiaDimensions,
)
from sotopia.database.persistent_profile import EnvironmentList
from sotopia.envs.evaluators import (
    EvaluationForAgents,
    RuleBasedTerminatedEvaluator,
)
from sotopia.generation_utils.generate import agenerate
from sotopia.generation_utils.output_parsers import PydanticOutputParser
from sotopia.envs.parallel import ParallelSotopiaEnv
from sotopia.messages import AgentAction, SimpleMessage

MODEL = "custom/deepseek-flash@https://api.deepseek.com"
HARD_LIST_ID = "01HAK34YPB1H1RWXQDASDKHSNS"
SOTOPIA_COMMIT = "a0aaafb440e570e5e61b7c44a44e5e417c545383"


def pick_first_hard_setting() -> tuple[str, str, list[str]]:
    hard = EnvironmentList.get(HARD_LIST_ID)
    hard_envs = hard.environments
    agent_index = hard.agent_index
    if not isinstance(agent_index, list):
        raise RuntimeError("SOTOPIA hard agent_index is not a list")

    combos = EnvAgentComboStorage.find().all()
    for env_id, index in zip(hard_envs, agent_index):
        for combo in combos:
            if combo.env_id == env_id:
                return env_id, str(index), list(combo.agent_ids)

    raise RuntimeError("No hard environment / agent combo found in installed dataset")


def build_env(env_id: str) -> ParallelSotopiaEnv:
    profile = EnvironmentProfile.get(env_id)
    return ParallelSotopiaEnv(
        env_profile=profile,
        action_order="round-robin",
        model_name=MODEL,
        evaluators=[
            RuleBasedTerminatedEvaluator(max_turn_number=20, max_stale_turn=2),
        ],
        terminal_evaluators=[],
    )


def make_agents(
    *,
    agent_ids: list[str],
    tested_index: int,
    use_hcl: bool,
    seed: int = 42,
) -> list[LLMAgent]:
    profiles = [AgentProfile.get(agent_id) for agent_id in agent_ids]
    agents: list[LLMAgent] = []
    for i, profile in enumerate(profiles):
        # Fair A/B: every agent uses the same direct DeepSeek transport.
        # The only treatment difference is HCL on the tested role.
        cls = HCLSocialAgent if use_hcl and i == tested_index else DirectSocialAgent
        agent = cls(agent_profile=profile, model_name=MODEL)
        if isinstance(agent, HCLSocialAgent):
            agent.hcl_loop.backend.seed = seed
            agent.decision_policy.backend.seed = seed

            decision_backend = agent.decision_policy.backend
            if os.getenv("HCL_PROVIDER_ATTEMPT_DIAGNOSTICS") == "1":
                from scripts.hcl_decision_diagnostics import (
                    ProviderAttemptDiagnosticBackend,
                )
                decision_backend = ProviderAttemptDiagnosticBackend(decision_backend)

            if os.getenv("HCL_DECISION_DIAGNOSTICS") == "1":
                from scripts.hcl_decision_diagnostics import DecisionDiagnosticBackend
                decision_backend = DecisionDiagnosticBackend(decision_backend)

            agent.decision_policy.backend = decision_backend
        else:
            agent.direct_backend.seed = seed
        agents.append(agent)
    return agents


async def evaluate_transcript(messages: list[tuple[str, Any]]) -> list[dict[str, Any] | None]:
    """Run SOTOPIA's official dimension rubric with robust score extraction.

    The pinned upstream EpisodeLLMEvaluator successfully generates and parses
    EvaluationForAgents, but then indexes nested Pydantic model_dump values as
    tuples (value[1]/value[0]). Under Pydantic v2 those values are dictionaries,
    causing a KeyError(1) that is swallowed and returned as an empty score list.

    This helper preserves the official prompt, EvaluationForAgents schema and
    SotopiaDimensions, changing only the broken extraction step.
    """
    messages_filtered = [
        (speaker, message)
        for speaker, message in messages
        if "did nothing" not in message.to_natural_language()
    ]
    history = "\n".join(
        (
            f"{speaker} {message.to_natural_language()}"
            if speaker != "Environment"
            else message.to_natural_language()
        )
        for speaker, message in messages_filtered
    )

    participating_agents = {
        speaker for speaker, _ in messages if speaker != "Environment"
    }
    num_agents = len(participating_agents)
    if num_agents == 0:
        return []

    agent_instruction = (
        "There are exactly "
        + str(num_agents)
        + " agents. Under the 'evaluations' field, use exactly these keys: "
        + "["
        + ", ".join(f'"agent_{i+1}"' for i in range(num_agents))
        + "] (no other keys).\n"
    )

    response_cls = EvaluationForAgents[SotopiaDimensions]
    response = await agenerate(
        model_name=MODEL,
        # Reformat with the same provider/model, never the upstream OpenAI default.
        bad_output_process_model=MODEL.split("@", 1)[0].replace("custom/", "openai/", 1),
        template="""{history}
            Based on previous interactions, evaluate how well participants achieve their goals.
            {agent_instruction}
            Please follow the format:
            {format_instructions}
        """,
        input_values={
            "history": history,
            "agent_instruction": agent_instruction,
        },
        output_parser=PydanticOutputParser(
            pydantic_object=response_cls,
        ),
        temperature=0.0,
        structured_output=False,
    )

    scored: list[dict[str, Any] | None] = []
    for evaluation in list(response.evaluations.values())[:num_agents]:
        raw = evaluation.model_dump()
        dimensions: dict[str, float | int] = {}
        reasoning: dict[str, str] = {}

        for dimension, value in raw.items():
            score: Any = None
            reason = ""
            if isinstance(value, dict):
                score = value.get("score")
                reason = str(value.get("reasoning", ""))
            elif isinstance(value, (list, tuple)) and len(value) >= 2:
                reason = str(value[0])
                score = value[1]

            if isinstance(score, (int, float)):
                dimensions[dimension] = score
                reasoning[dimension] = reason

        if dimensions:
            scored.append(
                {
                    "overall": sum(dimensions.values()) / len(dimensions),
                    "dimensions": dimensions,
                    "reasoning": reasoning,
                }
            )
        else:
            scored.append(None)

    return scored



async def run_episode(
    *,
    env_id: str,
    agent_ids: list[str],
    tested_index: int,
    use_hcl: bool,
    tag: str,
    seed: int = 42,
) -> dict[str, Any]:
    """Run one official SOTOPIA episode without constructing EpisodeLog.

    Upstream's pinned Redis EpisodeLog model currently fails under the hosted
    runner with an ExpressionProxy default for pk. That persistence bug is
    orthogonal to environment dynamics/evaluation, so this runner uses the
    same env/agent loop and terminal evaluators but stores results directly as
    JSON artifacts.
    """
    env = build_env(env_id)
    agent_list = make_agents(
        agent_ids=agent_ids,
        tested_index=tested_index,
        use_hcl=use_hcl,
        seed=seed,
    )
    agents = Agents({agent.agent_name: agent for agent in agent_list})

    observations = env.reset(agents=agents, omniscient=False)
    agents.reset()

    for index, agent_name in enumerate(env.agents):
        agents[agent_name].goal = env.profile.agent_goals[index]

    transcript: list[list[dict[str, str]]] = []
    done = False
    final_info: dict[str, Any] = {}

    while not done:
        turn_record: list[dict[str, str]] = []

        actions = await asyncio.gather(
            *[
                agents[agent_name].aact(observations[agent_name])
                for agent_name in env.agents
            ]
        )

        action_map: dict[str, AgentAction] = {}
        for idx, agent_name in enumerate(env.agents):
            action = actions[idx]
            try:
                AgentAction.model_validate(
                    action.model_dump(),
                    context={"agent_names": env.agents, "sender": agent_name},
                )
            except ValueError as exc:
                agents[agent_name].recv_message(
                    "Environment",
                    SimpleMessage(
                        message=(
                            f"Invalid action: {exc}. "
                            "Regenerate according to the error."
                        )
                    ),
                )
                action = await agents[agent_name].aact(observations[agent_name])
                AgentAction.model_validate(
                    action.model_dump(),
                    context={"agent_names": env.agents, "sender": agent_name},
                )

            action_map[agent_name] = action
            turn_record.append(
                {
                    "sender": agent_name,
                    "receiver": "Environment",
                    "message": action.to_natural_language(),
                }
            )

        observations, _, terminated, _, info = await env.astep(action_map)
        final_info = info

        for agent_name in env.agents:
            turn_record.append(
                {
                    "sender": "Environment",
                    "receiver": agent_name,
                    "message": observations[agent_name].to_natural_language(),
                }
            )

        transcript.append(turn_record)
        done = all(terminated.values())

    tested_agent = agent_list[tested_index]
    hcl_log = (
        getattr(tested_agent, "_hcl_turn_log", [])
        if use_hcl
        else []
    )

    # Score with SOTOPIA's official rubric/schema, while bypassing only the
    # pinned evaluator's broken Pydantic-v2 tuple indexing during extraction.
    scored = await evaluate_transcript(env.inbox)
    reasoning = ""

    return {
        "tag": tag,
        "environment": env_id,
        "tested_index": tested_index,
        "agent_ids": agent_ids,
        "agent_names": [agent.agent_name for agent in agent_list],
        "models": [MODEL, MODEL, MODEL],
        "rewards": scored,
        "reasoning": reasoning,
        "messages": transcript,
        "generation_seed": seed,
        "hcl_turn_count": len(hcl_log),
        "hcl_turn_log": hcl_log,
    }


async def main() -> int:
    if not os.getenv("CUSTOM_API_KEY"):
        raise RuntimeError("CUSTOM_API_KEY is required")

    env_id, index, agent_ids = pick_first_hard_setting()
    tested_index = int(index)

    control_tag = "hcl_sotopia_one_control"
    hcl_tag = "hcl_sotopia_one_treatment"

    control = await run_episode(
        env_id=env_id,
        agent_ids=agent_ids,
        tested_index=tested_index,
        use_hcl=False,
        tag=control_tag,
    )
    treatment = await run_episode(
        env_id=env_id,
        agent_ids=agent_ids,
        tested_index=tested_index,
        use_hcl=True,
        tag=hcl_tag,
    )

    assert treatment["hcl_turn_count"] > 0
    assert control["environment"] == treatment["environment"]
    assert control["agent_ids"] == treatment["agent_ids"]
    assert control["tested_index"] == treatment["tested_index"]

    result = {
        "upstream": {
            "repository": "sotopia-lab/sotopia",
            "commit": SOTOPIA_COMMIT,
            "hard_list_id": HARD_LIST_ID,
        },
        "model_configuration": {
            "test_base_model": MODEL,
            "partner_model": MODEL,
            "evaluator_model": MODEL,
        },
        "setting": {
            "environment": env_id,
            "tested_index": tested_index,
            "agent_ids": agent_ids,
        },
        "control": control,
        "treatment": treatment,
        "integrity_checks": {
            "same_environment": True,
            "same_agents": True,
            "same_tested_role": True,
            "hcl_turn_state_present": True,
        },
        "note": (
            "This is a one-setting engineering A/B smoke, not a performance claim. "
            "Both arms and the partner use the same direct DeepSeek transport; the "
            "treatment's only tested-role difference is the always-on HCL cognition "
            "layer. SOTOPIA generation is stochastic; performance inference requires "
            "a fixed multi-setting / repeated evaluation slice."
        ),
    }

    out = ROOT / "artifacts/sotopia-hard-one-ab"
    out.mkdir(parents=True, exist_ok=True)
    (out / "result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8",
    )

    summary = {
        "environment": env_id,
        "tested_index": tested_index,
        "control_rewards": control["rewards"],
        "treatment_rewards": treatment["rewards"],
        "control_message_turns": len(control["messages"]),
        "treatment_message_turns": len(treatment["messages"]),
        "hcl_turn_count": treatment["hcl_turn_count"],
    }
    (out / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
