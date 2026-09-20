#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.run_sotopia_hard_one_ab import (
    HARD_LIST_ID,
    MODEL,
    SOTOPIA_COMMIT,
    run_episode,
)
from scripts.run_sotopia_hard_slice_ab import DIMENSIONS, aggregate, run_with_retry, tested_reward

from sotopia.database import EnvAgentComboStorage
from sotopia.database.persistent_profile import EnvironmentList


def pick_setting(*, environment_ordinal: int, combo_ordinal: int) -> dict[str, Any]:
    hard = EnvironmentList.get(HARD_LIST_ID)
    if not isinstance(hard.agent_index, list):
        raise RuntimeError("SOTOPIA hard agent_index is not a list")
    if environment_ordinal < 0 or environment_ordinal >= len(hard.environments):
        raise RuntimeError(
            f"environment_ordinal={environment_ordinal} out of range "
            f"0..{len(hard.environments)-1}"
        )

    combos = EnvAgentComboStorage.find().all()
    by_env: dict[str, list[list[str]]] = defaultdict(list)
    for combo in combos:
        by_env[combo.env_id].append(list(combo.agent_ids))
    for env_id in by_env:
        by_env[env_id].sort(key=lambda ids: tuple(ids))

    env_id = hard.environments[environment_ordinal]
    candidates = by_env.get(env_id, [])
    if combo_ordinal < 0 or combo_ordinal >= len(candidates):
        raise RuntimeError(
            f"combo_ordinal={combo_ordinal} unavailable for env {env_id}; "
            f"count={len(candidates)}"
        )

    expanded_ordinal = 0
    for i in range(environment_ordinal):
        expanded_ordinal += len(by_env.get(hard.environments[i], []))
    expanded_ordinal += combo_ordinal

    return {
        "expanded_ordinal": expanded_ordinal,
        "environment_ordinal": environment_ordinal,
        "combo_ordinal": combo_ordinal,
        "environment": env_id,
        "tested_index": int(hard.agent_index[environment_ordinal]),
        "agent_ids": candidates[combo_ordinal],
    }


async def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--environment-ordinal", type=int, required=True)
    p.add_argument("--combo-ordinal", type=int, default=1)
    p.add_argument("--seed", type=int, default=42)
    args = p.parse_args()

    setting = pick_setting(
        environment_ordinal=args.environment_ordinal,
        combo_ordinal=args.combo_ordinal,
    )
    ordinal = int(setting["expanded_ordinal"])
    env_id = str(setting["environment"])
    tested_index = int(setting["tested_index"])
    agent_ids = list(setting["agent_ids"])

    out = ROOT / "artifacts/sotopia-hard-expanded-one-ab"
    out.mkdir(parents=True, exist_ok=True)

    manifest = {
        "upstream": {
            "repository": "sotopia-lab/sotopia",
            "commit": SOTOPIA_COMMIT,
            "hard_list_id": HARD_LIST_ID,
        },
        "model": MODEL,
        "generation_seed": args.seed,
        "setting": setting,
        "design": {
            "control": "DirectSocialAgent / Direct DeepSeek",
            "treatment": "HCLSocialAgent / same Direct DeepSeek",
            "partner": "DirectSocialAgent / same Direct DeepSeek",
            "freshness": (
                "Fresh env-agent combo; environment template may have appeared "
                "in earlier diagnostics."
            ),
        },
    }
    (out / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    failures: list[dict[str, Any]] = []
    results: list[dict[str, Any]] = []

    try:
        control = await run_with_retry(
            env_id=env_id,
            agent_ids=agent_ids,
            tested_index=tested_index,
            use_hcl=False,
            tag=f"hcl_expanded_seed{args.seed}_{ordinal:03d}_control",
            seed=args.seed,
        )
        treatment = await run_with_retry(
            env_id=env_id,
            agent_ids=agent_ids,
            tested_index=tested_index,
            use_hcl=True,
            tag=f"hcl_expanded_seed{args.seed}_{ordinal:03d}_treatment",
            seed=args.seed,
        )

        cr = tested_reward(control)
        tr = tested_reward(treatment)
        item = {
            "ordinal": ordinal,
            "setting": setting,
            "tested_control": cr,
            "tested_treatment": tr,
            "paired_overall_delta": float(tr["overall"]) - float(cr["overall"]),
            "paired_dimension_delta": {
                d: float(tr["dimensions"][d]) - float(cr["dimensions"][d])
                for d in DIMENSIONS
            },
            "control": control,
            "treatment": treatment,
        }
        results.append(item)
        (out / f"setting_{ordinal:03d}.json").write_text(
            json.dumps(item, ensure_ascii=False, indent=2, default=str) + "\n",
            encoding="utf-8",
        )
        print(
            f"expanded={ordinal} env_ord={args.environment_ordinal} "
            f"combo_ord={args.combo_ordinal} control={cr['overall']:.4f} "
            f"treatment={tr['overall']:.4f} "
            f"delta={item['paired_overall_delta']:+.4f}",
            flush=True,
        )
    except Exception as exc:
        failure = {
            "ordinal": ordinal,
            "setting": setting,
            "error_type": type(exc).__name__,
            "error": str(exc),
        }
        failures.append(failure)
        print(json.dumps(failure, ensure_ascii=False), flush=True)

    progress = {
        "generation_seed": args.seed,
        "requested_settings": 1,
        "completed_settings": len(results),
        "failed_settings": failures,
        "aggregate": aggregate(results),
    }
    (out / "progress.json").write_text(
        json.dumps(progress, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (out / "summary.json").write_text(
        json.dumps(
            {
                **progress,
                "claim_boundary": (
                    "Fresh env-agent-combo robustness evidence within previously "
                    "seen SOTOPIA-Hard environment templates; not fresh-environment "
                    "generalization and not official leaderboard-comparable."
                ),
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return 0 if not failures and len(results) == 1 else 3


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
