#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from hcl.integrations.sotopia_agent import DirectSocialAgent, HCLSocialAgent
from sotopia.messages import AgentAction, Observation


MODEL = "custom/deepseek-flash@https://api.deepseek.com"


async def main() -> int:
    if not os.getenv("CUSTOM_API_KEY"):
        raise RuntimeError("CUSTOM_API_KEY is required")

    observation = Observation(
        last_turn=(
            'Bob said: "I do not want to lend you the car because I am worried '
            'you may return it late again."'
        ),
        turn_number=1,
        available_actions=["none", "speak", "non-verbal communication", "action", "leave"],
    )

    base = DirectSocialAgent(agent_name="Alice", model_name=MODEL)
    base.goal = (
        "Convince Bob to lend you the car while preserving trust and addressing "
        "his concern about returning it late."
    )
    base_action: AgentAction = await base.aact(observation)

    hcl = HCLSocialAgent(agent_name="Alice", model_name=MODEL)
    hcl.goal = (
        "Convince Bob to lend you the car while preserving trust and addressing "
        "his concern about returning it late."
    )
    hcl_action: AgentAction = await hcl.aact(observation)

    assert base_action.action_type in observation.available_actions
    assert hcl_action.action_type in observation.available_actions
    assert isinstance(hcl_action.argument, str)
    assert hcl.action_checker is not None
    assert hcl._hcl_last_state is not None
    assert hcl._hcl_last_decision_plan is not None
    assert hcl._hcl_turn_log
    assert hcl._hcl_turn_log[-1]["forced_noop"] is False
    assert "decision_plan" in hcl._hcl_turn_log[-1]

    state = hcl._hcl_last_state
    assert state.get("mode") in {"SIMPLE", "EPISTEMIC", "CAUSAL_AMBIGUITY"}
    assert state.get("uncertainty", {}).get("level") in {"low", "medium", "high"}


    # Canonical always-on invariant: an environment-forced no-op must still
    # build/log HCL cognition instead of bypassing the module.
    forced_noop_observation = Observation(
        last_turn='Bob said: "I need a moment to think."',
        turn_number=2,
        available_actions=["none"],
    )
    before_noop_logs = len(hcl._hcl_turn_log)
    noop_action: AgentAction = await hcl.aact(forced_noop_observation)
    assert noop_action.action_type == "none"
    assert len(hcl._hcl_turn_log) == before_noop_logs + 1
    assert hcl._hcl_turn_log[-1]["forced_noop"] is True
    assert hcl._hcl_turn_log[-1]["state"]["mode"] in {
        "SIMPLE",
        "EPISTEMIC",
        "CAUSAL_AMBIGUITY",
    }
    assert hcl._hcl_turn_log[-1]["decision_plan"]["strategy_type"] == "DEFER"

    result = {
        "upstream": {
            "repository": "sotopia-lab/sotopia",
            "commit": "a0aaafb440e570e5e61b7c44a44e5e417c545383",
        },
        "model": MODEL,
        "base_action": base_action.model_dump(),
        "hcl_action": hcl_action.model_dump(),
        "hcl_state": state,
        "hcl_decision_plan": hcl._hcl_last_decision_plan,
        "hcl_turn_log": hcl._hcl_turn_log,
        "forced_noop_action": noop_action.model_dump(),
        "checks": {
            "base_action_valid": True,
            "hcl_action_valid": True,
            "hcl_state_present": True,
            "hcl_decision_plan_present": True,
            "hcl_turn_log_present": True,
            "forced_noop_passed_hcl": True,
        },
    }

    out = ROOT / "artifacts/sotopia-hcl-smoke"
    out.mkdir(parents=True, exist_ok=True)
    (out / "result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
