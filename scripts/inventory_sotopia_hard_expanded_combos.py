#!/usr/bin/env python3
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from sotopia.database import EnvAgentComboStorage
from sotopia.database.persistent_profile import EnvironmentList

HARD_LIST_ID = "01HAK34YPB1H1RWXQDASDKHSNS"

def main() -> int:
    hard = EnvironmentList.get(HARD_LIST_ID)
    if not isinstance(hard.agent_index, list):
        raise RuntimeError("Hard agent_index is not a list")

    combos = EnvAgentComboStorage.find().all()
    by_env: dict[str, list[list[str]]] = defaultdict(list)
    for combo in combos:
        by_env[combo.env_id].append(list(combo.agent_ids))
    for env_id in by_env:
        by_env[env_id].sort(key=lambda ids: tuple(ids))

    expanded = []
    per_env = []
    consumed_first_combo_keys = set()

    for env_ord, (env_id, tested_index) in enumerate(
        zip(hard.environments, hard.agent_index)
    ):
        candidates = by_env.get(env_id, [])
        if not candidates:
            raise RuntimeError(f"No EnvAgentComboStorage for hard env {env_id}")

        per_env.append(
            {
                "environment_ordinal": env_ord,
                "environment": env_id,
                "tested_index": int(tested_index),
                "combo_count": len(candidates),
            }
        )

        for combo_ord, agent_ids in enumerate(candidates):
            key = f"{env_id}|{int(tested_index)}|{'|'.join(agent_ids)}"
            row = {
                "expanded_ordinal": len(expanded),
                "environment_ordinal": env_ord,
                "combo_ordinal": combo_ord,
                "environment": env_id,
                "tested_index": int(tested_index),
                "agent_ids": agent_ids,
                "key": key,
                "previous_first_combo_consumed": combo_ord == 0,
            }
            expanded.append(row)
            if combo_ord == 0:
                consumed_first_combo_keys.add(key)

    fresh = [x for x in expanded if x["key"] not in consumed_first_combo_keys]

    out = Path("artifacts/sotopia-hard-expanded-inventory")
    out.mkdir(parents=True, exist_ok=True)
    result = {
        "hard_list_id": HARD_LIST_ID,
        "hard_environment_count": len(hard.environments),
        "expanded_combo_count": len(expanded),
        "previous_first_combo_consumed_count": len(consumed_first_combo_keys),
        "unused_expanded_combo_count": len(fresh),
        "per_environment": per_env,
        "expanded_settings": expanded,
        "first_10_unused_expanded": fresh[:10],
    }
    (out / "inventory.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(
        json.dumps(
            {
                "hard_environment_count": result["hard_environment_count"],
                "expanded_combo_count": result["expanded_combo_count"],
                "previous_first_combo_consumed_count": result[
                    "previous_first_combo_consumed_count"
                ],
                "unused_expanded_combo_count": result["unused_expanded_combo_count"],
                "combo_counts": [x["combo_count"] for x in per_env],
                "first_10_unused_expanded_ordinals": [
                    x["expanded_ordinal"] for x in fresh[:10]
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
