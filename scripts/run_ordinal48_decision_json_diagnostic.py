#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import contextlib
import io
import json
import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.run_sotopia_hard_expanded_one_ab import pick_setting
from scripts.run_sotopia_hard_one_ab import MODEL, SOTOPIA_COMMIT, run_episode

ENVIRONMENT_ORDINAL = 9
COMBO_ORDINAL = 3
EXPECTED_EXPANDED_ORDINAL = 48
SEED = 42
MAX_EPISODE_ATTEMPTS = 2
DIAGNOSTIC_PREFIX = "HCL_DECISION_DIAGNOSTIC "


def parse_diagnostic_events(stderr_text: str, *, attempt: int) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for line in stderr_text.splitlines():
        if not line.startswith(DIAGNOSTIC_PREFIX):
            continue
        try:
            event = json.loads(line[len(DIAGNOSTIC_PREFIX) :])
        except json.JSONDecodeError:
            continue
        if isinstance(event, dict):
            safe = {
                key: event[key]
                for key in (
                    "call",
                    "max_tokens",
                    "temperature",
                    "outcome",
                    "response_bytes",
                    "response_sha256",
                )
                if key in event
            }
            safe["episode_attempt"] = attempt
            events.append(safe)
    return events


def classify_attempt(
    *,
    success: bool,
    error_type: str | None,
    exact_invalid_json: bool,
    events: list[dict[str, Any]],
) -> str:
    outcomes = [str(event.get("outcome", "")) for event in events]

    if success:
        return "episode_success_not_reproduced"

    if exact_invalid_json:
        tail = outcomes[-3:]
        if len(tail) == 3 and all(x == "empty" for x in tail):
            return "empty_output_family"
        if len(tail) == 3 and all(x == "no_parseable_object" for x in tail):
            return "nonempty_unparseable_output_family"
        if len(tail) == 3 and all(
            x in {"empty", "no_parseable_object", "observation_unavailable"}
            for x in tail
        ):
            return "mixed_invalid_output_family"
        return "invalid_json_family_not_fully_observed"

    if "transport_exception" in outcomes:
        return "transport_or_provider_failure"

    if error_type:
        return "other_episode_failure"

    return "diagnostic_inconclusive"


async def main() -> int:
    if os.getenv("HCL_DECISION_DIAGNOSTICS") != "1":
        raise RuntimeError("HCL_DECISION_DIAGNOSTICS=1 is required")
    if not os.getenv("CUSTOM_API_KEY"):
        raise RuntimeError("CUSTOM_API_KEY is required")

    setting = pick_setting(
        environment_ordinal=ENVIRONMENT_ORDINAL,
        combo_ordinal=COMBO_ORDINAL,
    )
    if int(setting["expanded_ordinal"]) != EXPECTED_EXPANDED_ORDINAL:
        raise RuntimeError(
            "Diagnostic setting drift: expected expanded ordinal "
            f"{EXPECTED_EXPANDED_ORDINAL}, got {setting['expanded_ordinal']}"
        )

    out = ROOT / "artifacts/ordinal48-decision-json-diagnostic"
    out.mkdir(parents=True, exist_ok=True)

    attempts: list[dict[str, Any]] = []
    final_episode_outcome = "not_run"

    for attempt in range(1, MAX_EPISODE_ATTEMPTS + 1):
        captured = io.StringIO()
        success = False
        error_type: str | None = None
        exact_invalid_json = False
        hcl_turn_count: int | None = None

        try:
            with contextlib.redirect_stderr(captured):
                episode = await run_episode(
                    env_id=str(setting["environment"]),
                    agent_ids=list(setting["agent_ids"]),
                    tested_index=int(setting["tested_index"]),
                    use_hcl=True,
                    tag=f"ordinal48_json_diag_seed{SEED}_attempt{attempt}",
                    seed=SEED,
                )
            success = True
            hcl_turn_count = int(episode.get("hcl_turn_count", 0))
            final_episode_outcome = "success"
        except Exception as exc:
            error_type = type(exc).__name__
            exact_invalid_json = (
                isinstance(exc, RuntimeError)
                and str(exc)
                == "HCL decision policy returned no valid JSON after 3 attempts"
            )
            final_episode_outcome = "failure"

        events = parse_diagnostic_events(captured.getvalue(), attempt=attempt)
        classification = classify_attempt(
            success=success,
            error_type=error_type,
            exact_invalid_json=exact_invalid_json,
            events=events,
        )

        attempts.append(
            {
                "episode_attempt": attempt,
                "episode_outcome": "success" if success else "failure",
                "error_type": error_type,
                "exact_invalid_json_runtime_error": exact_invalid_json,
                "hcl_turn_count": hcl_turn_count,
                "classification": classification,
                "decision_events": events,
            }
        )

        if success:
            break

        if attempt < MAX_EPISODE_ATTEMPTS:
            await asyncio.sleep(5)

    event_count = sum(len(item["decision_events"]) for item in attempts)
    summary = {
        "purpose": "consumed ordinal48 Decision JSON diagnostic replay only",
        "claim_boundary": (
            "Not fresh evidence; not a holdout completion; no efficacy result. "
            "No control arm or reward result is promoted by this diagnostic."
        ),
        "upstream": {
            "repository": "sotopia-lab/sotopia",
            "commit": SOTOPIA_COMMIT,
        },
        "model": MODEL,
        "generation_seed": SEED,
        "setting": {
            "environment_ordinal": ENVIRONMENT_ORDINAL,
            "combo_ordinal": COMBO_ORDINAL,
            "expanded_ordinal": EXPECTED_EXPANDED_ORDINAL,
        },
        "max_episode_attempts": MAX_EPISODE_ATTEMPTS,
        "attempts_executed": len(attempts),
        "diagnostic_event_count": event_count,
        "final_episode_outcome": final_episode_outcome,
        "attempts": attempts,
    }

    (out / "result.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    public_summary = {
        "attempts_executed": len(attempts),
        "diagnostic_event_count": event_count,
        "final_episode_outcome": final_episode_outcome,
        "attempt_classifications": [
            {
                "episode_attempt": item["episode_attempt"],
                "episode_outcome": item["episode_outcome"],
                "error_type": item["error_type"],
                "exact_invalid_json_runtime_error": item[
                    "exact_invalid_json_runtime_error"
                ],
                "classification": item["classification"],
                "decision_event_outcomes": [
                    event.get("outcome") for event in item["decision_events"]
                ],
            }
            for item in attempts
        ],
    }
    print(json.dumps(public_summary, ensure_ascii=False, indent=2))

    # Workflow success means diagnostic evidence was collected, not that the
    # historical episode passed. Require at least one observed Decision Policy
    # transport call so a green job cannot be mistaken for an empty diagnostic.
    return 0 if event_count > 0 else 3


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
