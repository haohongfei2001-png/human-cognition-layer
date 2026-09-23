"""Frozen, internal open-world C/D/E comparison; no runtime promotion."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.run_v04_hypothesis_guided_action_v01 import (
    run_direct,
    run_structured,
    summary,
)
from scripts.run_v04_latent_hypothesis_capability_v01 import make_backend

FIXTURES = REPO_ROOT / "eval/v04/open_world_hypothesis_v01.json"
FROZEN_SHA256 = "ad8d8e96ab6e3d251bda416a10e9f6eac028d87d5376b1c8eea0441ea3bcbe41"


def validate_fixtures(raw: bytes) -> list[dict]:
    digest = hashlib.sha256(raw).hexdigest()
    if digest != FROZEN_SHA256:
        raise ValueError(f"frozen fixture digest mismatch: {digest}")
    fixtures = json.loads(raw)
    if not isinstance(fixtures, list) or not 6 <= len(fixtures) <= 8:
        raise ValueError("frozen comparison needs six to eight scenarios")
    scenario_ids: set[str] = set()
    hidden_other = 0
    hidden_named = 0
    for scenario in fixtures:
        sid = scenario["id"]
        if not isinstance(sid, str) or sid in scenario_ids:
            raise ValueError(f"invalid or duplicate scenario ID: {sid}")
        scenario_ids.add(sid)
        target = scenario["target"]
        candidates = target["candidates"]
        labels = [row[0] for row in candidates]
        if not 2 <= len(labels) <= 3 or len(set(labels)) != len(labels) or "OTHER_UNKNOWN" in labels:
            raise ValueError(f"{sid}: expected two or three distinct named candidates")
        possible = set(labels) | {"OTHER_UNKNOWN"}
        hidden = scenario["hidden_target"]
        if hidden not in possible:
            raise ValueError(f"{sid}: hidden state outside the frozen simulation")
        hidden_other += hidden == "OTHER_UNKNOWN"
        hidden_named += hidden != "OTHER_UNKNOWN"
        probes = [row[0] for row in scenario["probes"]]
        actions = [row[0] for row in scenario["actions"]]
        if len(probes) != 3 or len(set(probes)) != 3 or len(actions) != 3 or len(set(actions)) != 3:
            raise ValueError(f"{sid}: exactly three distinct probes and actions required")
        if not set(scenario["high_information_probes"]) <= set(probes):
            raise ValueError(f"{sid}: undeclared high-information probe")
        if set(scenario["probe_responses"]) != possible or set(scenario["correct_actions"]) != possible:
            raise ValueError(f"{sid}: every possible state needs frozen responses and action")
        for response_map in scenario["probe_responses"].values():
            if set(response_map) != set(probes) or not all(isinstance(x, str) and x.strip() for x in response_map.values()):
                raise ValueError(f"{sid}: missing or empty probe response")
        if not set(scenario["correct_actions"].values()) <= set(actions):
            raise ValueError(f"{sid}: undeclared correct action")
        events = scenario["initial_events"]
        ids = [event["event_id"] for event in events]
        if not events or len(ids) != len(set(ids)):
            raise ValueError(f"{sid}: initial raw events must have unique IDs")
        valid_times = []
        for event in events:
            if not event["raw_text"].strip() or not event["source_id"] or not event["actor_id"]:
                raise ValueError(f"{sid}: event lacks raw evidence or provenance")
            if not isinstance(event["observer_ids"], list) or not event["observer_ids"]:
                raise ValueError(f"{sid}: event lacks an observer perspective")
            valid_time = datetime.fromisoformat(event["valid_time"])
            recorded_at = datetime.fromisoformat(event["recorded_at"])
            if valid_time.tzinfo is None or recorded_at.tzinfo is None or recorded_at < valid_time:
                raise ValueError(f"{sid}: invalid bitemporal chronology")
            valid_times.append(valid_time)
        if valid_times != sorted(valid_times):
            raise ValueError(f"{sid}: initial events out of valid-time order")
    if hidden_other < 2 or hidden_named < 2:
        raise ValueError("open-world fixture lacks named or OTHER_UNKNOWN coverage")
    return fixtures


class AuditBackend:
    """Keep only synthetic model outputs needed for a later semantic audit."""

    def __init__(self, backend, call_budget: list[int]):
        self.backend = backend
        self.call_budget = call_budget
        self.calls: list[dict] = []
        self.scenario = ""

    def complete_json(self, messages, *, max_tokens, temperature=0.0):
        if self.call_budget[0] >= 160:
            raise RuntimeError("frozen provider-call ceiling reached")
        self.call_budget[0] += 1
        result = self.backend.complete_json(messages, max_tokens=max_tokens, temperature=temperature)
        self.calls.append({"scenario": self.scenario, "step": len(self.calls) + 1, "raw_output": result})
        return result

    def metrics(self):
        return self.backend.metrics()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--model", default="deepseek-flash")
    parser.add_argument("--base-url", default=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"))
    parser.add_argument("--out", default="artifacts/hcl-v04-open-world-v01/result.json")
    args = parser.parse_args()
    raw = FIXTURES.read_bytes()
    fixtures = validate_fixtures(raw)
    if args.validate_only:
        print(json.dumps({"scenarios": len(fixtures), "fixture_sha256": FROZEN_SHA256}))
        return

    api_key = os.environ["DEEPSEEK_API_KEY"]
    call_budget = [0]
    backends = {arm: AuditBackend(make_backend(api_key, args.base_url, args.model), call_budget) for arm in ("C", "D", "E")}
    rows: dict[str, list[dict]] = {arm: [] for arm in backends}
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    status = "IN_PROGRESS"
    try:
        for scenario in fixtures:
            for arm, backend in backends.items():
                backend.scenario = scenario["id"]
                row = run_direct(scenario, backend) if arm == "E" else run_structured(scenario, backend, persistent=arm == "D")
                rows[arm].append(row)
        status = "MEASURED_PENDING_SEMANTIC_AUDIT"
    except Exception as exc:
        status = f"FAILED:{type(exc).__name__}:{exc}"
        raise
    finally:
        result = {
            "format": "hcl-v04-open-world-hypothesis-v01",
            "status": status,
            "model": args.model,
            "fixture_sha256": FROZEN_SHA256,
            "scenario_count": len(fixtures),
            "provider_calls_attempted": call_budget[0],
            "arms": {arm: summary(rows[arm], backend) for arm, backend in backends.items()},
            "rows": rows,
            "synthetic_model_outputs_for_semantic_audit": {arm: backend.calls for arm, backend in backends.items()},
            "semantic_audit": "PENDING_MANUAL_REVIEW",
            "promotion": "NONE",
        }
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"arms": result["arms"], "artifact": str(out)}, sort_keys=True))


if __name__ == "__main__":
    main()
