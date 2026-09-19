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
    SOTOPIA_COMMIT,
    MODEL,
    run_episode,
)

from sotopia.database import EnvAgentComboStorage
from sotopia.database.persistent_profile import EnvironmentList

DIMENSIONS = [
    "believability",
    "relationship",
    "knowledge",
    "secret",
    "social_rules",
    "financial_and_material_benefits",
    "goal",
]


def pick_hard_settings(*, start: int, count: int) -> list[dict[str, Any]]:
    hard = EnvironmentList.get(HARD_LIST_ID)
    if not isinstance(hard.agent_index, list):
        raise RuntimeError("SOTOPIA hard agent_index is not a list")

    combos = EnvAgentComboStorage.find().all()
    by_env: dict[str, list[list[str]]] = defaultdict(list)
    for combo in combos:
        by_env[combo.env_id].append(list(combo.agent_ids))

    # Stable ordering inside each environment.
    for env_id in by_env:
        by_env[env_id].sort(key=lambda ids: tuple(ids))

    settings: list[dict[str, Any]] = []
    for env_id, index in zip(hard.environments, hard.agent_index):
        candidates = by_env.get(env_id, [])
        if not candidates:
            continue
        settings.append(
            {
                "environment": env_id,
                "tested_index": int(index),
                "agent_ids": candidates[0],
            }
        )

    chosen = settings[start : start + count]
    if len(chosen) != count:
        raise RuntimeError(
            f"Requested {count} hard settings from offset {start}, "
            f"but only {len(chosen)} were available"
        )
    return chosen


def tested_reward(episode: dict[str, Any]) -> dict[str, Any]:
    idx = int(episode["tested_index"])
    rewards = episode["rewards"]
    if idx >= len(rewards) or rewards[idx] is None:
        raise RuntimeError(
            f"Missing tested-role reward for {episode['environment']} index={idx}"
        )
    reward = rewards[idx]
    if not isinstance(reward, dict) or "dimensions" not in reward:
        raise RuntimeError("Malformed tested-role reward")
    return reward


def aggregate(results: list[dict[str, Any]]) -> dict[str, Any]:
    if not results:
        return {
            "completed_settings": 0,
            "overall": {},
            "dimensions": {},
        }

    control_overall: list[float] = []
    treatment_overall: list[float] = []
    overall_delta: list[float] = []

    by_dim: dict[str, dict[str, list[float]]] = {
        d: {"control": [], "treatment": [], "delta": []} for d in DIMENSIONS
    }

    improved = tied = worsened = 0

    for result in results:
        c = result["tested_control"]
        t = result["tested_treatment"]

        co = float(c["overall"])
        to = float(t["overall"])
        delta = to - co
        control_overall.append(co)
        treatment_overall.append(to)
        overall_delta.append(delta)

        if delta > 1e-9:
            improved += 1
        elif delta < -1e-9:
            worsened += 1
        else:
            tied += 1

        for d in DIMENSIONS:
            cv = float(c["dimensions"][d])
            tv = float(t["dimensions"][d])
            by_dim[d]["control"].append(cv)
            by_dim[d]["treatment"].append(tv)
            by_dim[d]["delta"].append(tv - cv)

    def mean(xs: list[float]) -> float:
        return sum(xs) / len(xs)

    return {
        "completed_settings": len(results),
        "overall": {
            "control_mean": mean(control_overall),
            "treatment_mean": mean(treatment_overall),
            "paired_delta_mean": mean(overall_delta),
            "improved_settings": improved,
            "tied_settings": tied,
            "worsened_settings": worsened,
        },
        "dimensions": {
            d: {
                "control_mean": mean(by_dim[d]["control"]),
                "treatment_mean": mean(by_dim[d]["treatment"]),
                "paired_delta_mean": mean(by_dim[d]["delta"]),
            }
            for d in DIMENSIONS
        },
    }


async def run_with_retry(**kwargs: Any) -> dict[str, Any]:
    last: Exception | None = None
    for attempt in range(2):
        try:
            return await run_episode(**kwargs)
        except Exception as exc:
            last = exc
            if attempt == 0:
                await asyncio.sleep(5)
    assert last is not None
    raise last


async def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--start", type=int, default=0)
    p.add_argument("--count", type=int, default=10)
    args = p.parse_args()

    settings = pick_hard_settings(start=args.start, count=args.count)

    out = ROOT / "artifacts/sotopia-hard-slice-ab"
    out.mkdir(parents=True, exist_ok=True)

    manifest = {
        "upstream": {
            "repository": "sotopia-lab/sotopia",
            "commit": SOTOPIA_COMMIT,
            "hard_list_id": HARD_LIST_ID,
        },
        "model": MODEL,
        "slice": {
            "start": args.start,
            "count": args.count,
            "settings": settings,
        },
        "design": {
            "control": "DirectSocialAgent / Direct DeepSeek",
            "treatment": "HCLSocialAgent / same Direct DeepSeek",
            "partner": "DirectSocialAgent / same Direct DeepSeek",
            "only_tested_role_difference": "always-on HCL cognition layer",
        },
    }
    (out / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    results: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []

    for offset, setting in enumerate(settings):
        ordinal = args.start + offset
        env_id = setting["environment"]
        tested_index = int(setting["tested_index"])
        agent_ids = list(setting["agent_ids"])

        print(
            f"[{offset+1}/{len(settings)}] setting={ordinal} env={env_id} "
            f"tested_index={tested_index}",
            flush=True,
        )

        try:
            control = await run_with_retry(
                env_id=env_id,
                agent_ids=agent_ids,
                tested_index=tested_index,
                use_hcl=False,
                tag=f"hcl_slice_{ordinal:03d}_control",
            )
            treatment = await run_with_retry(
                env_id=env_id,
                agent_ids=agent_ids,
                tested_index=tested_index,
                use_hcl=True,
                tag=f"hcl_slice_{ordinal:03d}_treatment",
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
                f"  control={cr['overall']:.4f} "
                f"treatment={tr['overall']:.4f} "
                f"delta={item['paired_overall_delta']:+.4f} "
                f"hcl_states={treatment['hcl_turn_count']}",
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
            print(f"  FAILED: {failure}", flush=True)

        progress = {
            "requested_settings": len(settings),
            "completed_settings": len(results),
            "failed_settings": failures,
            "aggregate": aggregate(results),
        }
        (out / "progress.json").write_text(
            json.dumps(progress, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    summary = {
        "requested_settings": len(settings),
        "completed_settings": len(results),
        "failed_settings": failures,
        "aggregate": aggregate(results),
        "claim_boundary": (
            "This is a fixed 10-setting paired slice, not the full SOTOPIA-Hard "
            "benchmark and not a final efficacy claim. Repeated runs are required "
            "before uncertainty estimates or robustness claims."
        ),
    }
    (out / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)

    return 0 if not failures and len(results) == len(settings) else 3


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
