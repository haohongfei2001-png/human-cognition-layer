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

from hcl.integrations.sotopia_agent import HCLSocialAgent

from sotopia.agents.llm_agent import LLMAgent
from sotopia.database import (
    AgentProfile,
    EnvAgentComboStorage,
    EnvironmentProfile,
    EpisodeLog,
    SotopiaDimensions,
)
from sotopia.database.persistent_profile import EnvironmentList
from sotopia.envs.evaluators import (
    EpisodeLLMEvaluator,
    EvaluationForAgents,
    RuleBasedTerminatedEvaluator,
)
from sotopia.envs.parallel import ParallelSotopiaEnv
from sotopia.server import arun_one_episode

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
        terminal_evaluators=[
            EpisodeLLMEvaluator(
                MODEL,
                EvaluationForAgents[SotopiaDimensions],
            ),
        ],
    )


def make_agents(
    *,
    agent_ids: list[str],
    tested_index: int,
    use_hcl: bool,
) -> list[LLMAgent]:
    profiles = [AgentProfile.get(agent_id) for agent_id in agent_ids]
    agents: list[LLMAgent] = []
    for i, profile in enumerate(profiles):
        cls = HCLSocialAgent if use_hcl and i == tested_index else LLMAgent
        agents.append(cls(agent_profile=profile, model_name=MODEL))
    return agents


async def run_episode(
    *,
    env_id: str,
    agent_ids: list[str],
    tested_index: int,
    use_hcl: bool,
    tag: str,
) -> dict[str, Any]:
    env = build_env(env_id)
    agents = make_agents(
        agent_ids=agent_ids,
        tested_index=tested_index,
        use_hcl=use_hcl,
    )

    await arun_one_episode(
        env=env,
        agent_list=agents,
        omniscient=False,
        script_like=False,
        json_in_script=False,
        tag=tag,
        push_to_db=True,
        streaming=False,
    )

    episodes = EpisodeLog.find(EpisodeLog.tag == tag).all()
    if not episodes:
        raise RuntimeError(f"EpisodeLog not found for tag {tag}")
    episode = episodes[-1]

    tested_agent = agents[tested_index]
    hcl_log = (
        getattr(tested_agent, "_hcl_turn_log", [])
        if use_hcl
        else []
    )

    return {
        "tag": tag,
        "environment": env_id,
        "tested_index": tested_index,
        "agent_ids": agent_ids,
        "agent_names": [agent.agent_name for agent in agents],
        "models": episode.models,
        "rewards": episode.rewards,
        "reasoning": episode.reasoning,
        "messages": episode.messages,
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
            "SOTOPIA generation is stochastic; performance inference requires a fixed "
            "multi-setting / repeated evaluation slice."
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
