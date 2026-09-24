"""Final internal strong-baseline replication for HCL v0.5."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.run_v04_long_horizon_bounded_context_v01 import (
    MeteredBackend,
    event_prompt_payload,
    make_real_backend,
)
from scripts.run_v05_seeded_state_capability_v01 import (
    run_c_stream,
    run_d_stream,
    run_e_stream,
    score_rows,
)


GENERIC_STATE_SYSTEM = """Maintain a compact generic structured state for future
human-state questions over a long event stream.

You receive a frozen issue/value ontology, the previous JSON state, and one new
raw event. Update the JSON state using ordinary reasoning. This is a generic
structured memory, not a specialized cognition module.

Return JSON only with exactly this top-level shape:
{
  "agents": {
    "<agent>": {
      "<issue>": {
        "current_label": "<one ontology value|UNCERTAIN>",
        "rejected_values": ["<ontology value>", "..."],
        "history": [
          {
            "valid_time": "<copy an event valid_time>",
            "label": "<one ontology value|UNCERTAIN>",
            "note": "<short reason/provenance>"
          }
        ]
      }
    }
  }
}

Guidance:
- Track a person's stance, not system/world truth.
- A source asserting or announcing X does not by itself prove the source or
  recipient accepts X.
- Information delivered only to somebody else does not update an uninformed
  person's stance.
- Receiving a correction can matter, but receipt alone does not prove
  acceptance. Explicit acceptance/rejection/undecided evidence should control
  the person's stored stance.
- Keep different agents and issues separate.
- When current_label changes, preserve a short dated history entry so later
  historical questions can be answered.
- Keep enough older dated history to reconstruct meaningful prior stances.
- rejected_values should contain explicit rejected alternatives that still
  matter; it may be compacted.
- Do not invent agents, access, acceptance, rejection, or dates.
- Reuse ontology keys exactly.
- Omit agent/issue cells with no meaningful mental-state evidence.
- Stay within state_char_limit. Compress notes/history if needed.

Do not use or imitate any HCL-specific schema, routing mechanism, or transition
algorithm. Return the complete updated JSON state only.
"""

GENERIC_REPAIR_SYSTEM = """Repair/compress a generic structured state.

Return JSON only with top-level {"agents": {...}} and the declared per-cell
fields current_label, rejected_values, history.

Requirements:
- preserve supported current stances and enough dated history for historical
  questions;
- labels/issues must come from the supplied ontology;
- do not add facts;
- remove malformed or unsupported entries;
- shorten notes and prune redundant history before dropping meaningful stance
  transitions;
- fit within state_char_limit.

Return the complete repaired state only.
"""


class GenericStateError(ValueError):
    pass


def _parse_time(value: str) -> datetime:
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def _state_chars(state: dict[str, Any]) -> int:
    return len(json.dumps(state, ensure_ascii=False, sort_keys=True))


def validate_generic_state(
    state: dict[str, Any],
    ontology: dict[str, list[str]],
    *,
    state_char_limit: int,
) -> None:
    if not isinstance(state, dict) or set(state) != {"agents"}:
        raise GenericStateError("generic state must contain only top-level agents")
    agents = state["agents"]
    if not isinstance(agents, dict):
        raise GenericStateError("agents must be an object")

    for agent, issues in agents.items():
        if not str(agent).strip() or not isinstance(issues, dict):
            raise GenericStateError("agent keys must map to objects")
        for issue, cell in issues.items():
            if issue not in ontology:
                raise GenericStateError(f"unknown issue: {issue}")
            if not isinstance(cell, dict):
                raise GenericStateError("issue cell must be an object")
            allowed_fields = {"current_label", "rejected_values", "history"}
            if set(cell) - allowed_fields:
                raise GenericStateError(
                    f"unexpected issue cell fields: {sorted(set(cell)-allowed_fields)}"
                )
            if set(cell) != allowed_fields:
                raise GenericStateError(
                    "issue cell requires current_label, rejected_values, history"
                )
            allowed_labels = set(ontology[issue]) | {"UNCERTAIN"}
            label = str(cell["current_label"])
            if label not in allowed_labels:
                raise GenericStateError(
                    f"invalid current_label {label!r} for issue {issue}"
                )
            rejected = cell["rejected_values"]
            if not isinstance(rejected, list):
                raise GenericStateError("rejected_values must be a list")
            if len(rejected) != len(set(map(str, rejected))):
                raise GenericStateError("rejected_values must be unique")
            for value in rejected:
                if str(value) not in ontology[issue]:
                    raise GenericStateError(
                        f"invalid rejected value {value!r} for issue {issue}"
                    )
            history = cell["history"]
            if not isinstance(history, list):
                raise GenericStateError("history must be a list")
            previous: datetime | None = None
            for entry in history:
                if not isinstance(entry, dict):
                    raise GenericStateError("history entries must be objects")
                if set(entry) != {"valid_time", "label", "note"}:
                    raise GenericStateError(
                        "history entries require valid_time, label, note"
                    )
                current = _parse_time(entry["valid_time"])
                if previous is not None and current < previous:
                    raise GenericStateError("history must be chronological")
                previous = current
                if str(entry["label"]) not in allowed_labels:
                    raise GenericStateError("history label outside ontology")
                if not isinstance(entry["note"], str):
                    raise GenericStateError("history note must be a string")
                if len(entry["note"]) > 240:
                    raise GenericStateError("history note too long")

    if _state_chars(state) > state_char_limit:
        raise GenericStateError(
            f"generic state exceeds limit: {_state_chars(state)} > {state_char_limit}"
        )


def update_generic_state(
    backend: MeteredBackend,
    state: dict[str, Any],
    event: dict[str, Any],
    ontology: dict[str, list[str]],
    *,
    state_char_limit: int,
) -> tuple[dict[str, Any], int]:
    payload = {
        "state_char_limit": state_char_limit,
        "frozen_issue_value_ontology": ontology,
        "previous_state": state,
        "new_event": event_prompt_payload(event),
    }
    raw = backend.complete_json(
        [
            {"role": "system", "content": GENERIC_STATE_SYSTEM},
            {
                "role": "user",
                "content": json.dumps(payload, ensure_ascii=False, sort_keys=True),
            },
        ],
        max_tokens=3072,
        temperature=0.0,
    )

    first_error: Exception | None = None
    for attempt in range(2):
        try:
            parsed = json.loads(raw)
            validate_generic_state(
                parsed,
                ontology,
                state_char_limit=state_char_limit,
            )
            return parsed, attempt
        except (json.JSONDecodeError, GenericStateError) as exc:
            if first_error is None:
                first_error = exc
            if attempt == 1:
                raise GenericStateError(
                    f"generic state invalid after bounded repair: {exc}"
                ) from exc
            raw = backend.complete_json(
                [
                    {"role": "system", "content": GENERIC_REPAIR_SYSTEM},
                    {
                        "role": "user",
                        "content": json.dumps(
                            {
                                "state_char_limit": state_char_limit,
                                "frozen_issue_value_ontology": ontology,
                                "previous_valid_state": state,
                                "invalid_candidate_state": raw,
                                "validation_error": str(exc),
                            },
                            ensure_ascii=False,
                            sort_keys=True,
                        ),
                    },
                ],
                max_tokens=3072,
                temperature=0.0,
            )
    raise GenericStateError(f"generic state update failed: {first_error}")


def generic_state_prediction(
    state: dict[str, Any],
    query: dict[str, Any],
) -> str:
    cell = (
        state.get("agents", {})
        .get(query["target_agent_id"], {})
        .get(query["target_issue_key"])
    )
    if not isinstance(cell, dict):
        return "UNCERTAIN"

    allowed = set(query["allowed_labels"])
    event_time = query.get("event_time")
    if event_time:
        cutoff = _parse_time(event_time)
        candidates = []
        for entry in cell.get("history", []):
            try:
                valid = _parse_time(entry["valid_time"])
            except Exception:
                continue
            if valid <= cutoff:
                candidates.append((valid, str(entry["label"])))
        if not candidates:
            return "UNCERTAIN"
        label = max(candidates, key=lambda item: item[0])[1]
        return label if label in allowed else "UNCERTAIN"

    label = str(cell.get("current_label", "UNCERTAIN"))
    return label if label in allowed else "UNCERTAIN"


def run_g_stream(
    stream: dict[str, Any],
    backend: MeteredBackend,
    *,
    state_char_budget: int,
) -> list[dict[str, Any]]:
    state: dict[str, Any] = {"agents": {}}
    rows: list[dict[str, Any]] = []
    repairs = 0
    errors: list[dict[str, str]] = []
    queries_by_after: dict[int, list[dict[str, Any]]] = {}
    for query in stream["queries"]:
        queries_by_after.setdefault(int(query["after_event"]), []).append(query)

    for index, event in enumerate(stream["events"], start=1):
        previous = state
        try:
            state, repaired = update_generic_state(
                backend,
                state,
                event,
                stream["ontology_seed"],
                state_char_limit=state_char_budget,
            )
            repairs += repaired
        except Exception as exc:
            state = previous
            errors.append(
                {
                    "event_id": event["event_id"],
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )

        for query in queries_by_after.get(index, []):
            started = time.perf_counter()
            prediction = generic_state_prediction(state, query)
            target_cell = (
                state.get("agents", {})
                .get(query["target_agent_id"], {})
                .get(query["target_issue_key"])
            )
            rows.append(
                {
                    "query_id": query["query_id"],
                    "prediction": prediction,
                    "query_context_chars": len(
                        json.dumps(
                            target_cell if target_cell is not None else {},
                            ensure_ascii=False,
                            sort_keys=True,
                        )
                    ),
                    "generic_state": json.loads(json.dumps(state)),
                    "target_state_cell": target_cell,
                    "state_chars": _state_chars(state),
                    "query_elapsed_seconds": round(
                        time.perf_counter() - started, 6
                    ),
                    "state_repairs_so_far": repairs,
                    "state_errors_so_far": list(errors),
                }
            )
    return rows


def validate_fixture(fixture: dict[str, Any], gold: dict[str, Any]) -> None:
    assert fixture["format"] == "hcl-v05-strong-baseline-replication-v01-fixture"
    assert gold["format"] == "hcl-v05-strong-baseline-replication-v01-gold"
    assert fixture["query_context_char_budget"] == 8000
    assert fixture["persistent_state_char_budget"] == 6000
    assert len(fixture["streams"]) == 4

    event_ids: set[str] = set()
    query_ids: list[str] = []

    for stream in fixture["streams"]:
        assert len(stream["events"]) == 96
        assert len(stream["queries"]) == 12
        assert len(stream["ontology_seed"]) == 4
        assert len(stream["target_agents"]) == 2
        assert len(set(stream["target_agents"])) == 2
        assert len(stream["queried_issues"]) == 2
        assert len(set(stream["queried_issues"])) == 2
        assert set(stream["queried_issues"]).issubset(stream["ontology_seed"])

        for issue, values in stream["ontology_seed"].items():
            assert issue.strip()
            assert len(values) == 3
            assert len(values) == len(set(values))
            assert all(str(v).strip() for v in values)

        known_agents: set[str] = set()
        for event in stream["events"]:
            eid = event["event_id"]
            assert eid not in event_ids
            event_ids.add(eid)
            assert event["raw_text"].strip()
            assert event["valid_time"] and event["recorded_at"]
            if event.get("actor_id"):
                known_agents.add(str(event["actor_id"]))
            known_agents.update(map(str, event.get("recipient_ids") or []))
            known_agents.update(map(str, event.get("observer_ids") or []))
        assert len(known_agents) >= 5

        full_chars = len(
            json.dumps(
                [event_prompt_payload(event) for event in stream["events"]],
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        assert full_chars > fixture["query_context_char_budget"]

        previous_after = 0
        seen_targets: set[str] = set()
        seen_issues: set[str] = set()
        for query in stream["queries"]:
            assert "gold" not in query
            assert "risk_class" not in query
            after = int(query["after_event"])
            assert previous_after <= after <= 96
            previous_after = after
            assert query["target_agent_id"] in stream["target_agents"]
            assert query["target_issue_key"] in stream["queried_issues"]
            seen_targets.add(query["target_agent_id"])
            seen_issues.add(query["target_issue_key"])
            values = stream["ontology_seed"][query["target_issue_key"]]
            assert query["allowed_labels"] == values + ["UNCERTAIN"]
            query_ids.append(query["query_id"])
        assert seen_targets == set(stream["target_agents"])
        assert seen_issues == set(stream["queried_issues"])

    assert len(query_ids) == len(set(query_ids)) == 48
    assert set(query_ids) == set(gold["labels"])
    for query_id, truth in gold["labels"].items():
        assert truth["gold"]
        assert truth["risk_class"]
        stream = next(
            s for s in fixture["streams"]
            if any(q["query_id"] == query_id for q in s["queries"])
        )
        query = next(q for q in stream["queries"] if q["query_id"] == query_id)
        assert truth["gold"] in query["allowed_labels"]

    serialized = json.dumps(fixture, ensure_ascii=False, sort_keys=True)
    assert '"gold"' not in serialized
    assert '"risk_class"' not in serialized

    for forbidden in (
        "briefing room",
        "budget cap",
        "shipping dock",
        "release channel",
        "backup cadence",
        "invoice currency",
    ):
        assert forbidden not in serialized.lower()


def load_and_validate(fixture_path: str, gold_path: str):
    fixture_bytes = Path(fixture_path).read_bytes()
    gold_bytes = Path(gold_path).read_bytes()
    fixture = json.loads(fixture_bytes)
    gold = json.loads(gold_bytes)
    validate_fixture(fixture, gold)
    return (
        fixture,
        gold,
        hashlib.sha256(fixture_bytes).hexdigest(),
        hashlib.sha256(gold_bytes).hexdigest(),
    )


def _stream_scores(rows: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    out: dict[str, dict[str, int]] = {}
    for row in rows:
        block = out.setdefault(row["stream"], {"correct": 0, "total": 0})
        block["total"] += 1
        block["correct"] += int(row["correct"])
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--fixtures",
        default="eval/v05/strong_baseline_replication_v01_fixture.json",
    )
    parser.add_argument(
        "--gold",
        default="eval/v05/strong_baseline_replication_v01_gold.json",
    )
    parser.add_argument("--model", default="deepseek-flash")
    parser.add_argument(
        "--base-url",
        default=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
    )
    parser.add_argument(
        "--out",
        default="artifacts/hcl-v05-strong-baseline-replication-v01/result.json",
    )
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()

    fixture, gold, fixture_sha, gold_sha = load_and_validate(
        args.fixtures, args.gold
    )
    query_budget = int(fixture["query_context_char_budget"])
    state_budget = int(fixture["persistent_state_char_budget"])

    if args.validate_only:
        print(
            json.dumps(
                {
                    "streams": len(fixture["streams"]),
                    "events": sum(len(s["events"]) for s in fixture["streams"]),
                    "queries": sum(len(s["queries"]) for s in fixture["streams"]),
                    "query_context_char_budget": query_budget,
                    "persistent_state_char_budget": state_budget,
                    "fixture_sha256": fixture_sha,
                    "gold_sha256": gold_sha,
                },
                sort_keys=True,
            )
        )
        return

    api_key = os.environ["DEEPSEEK_API_KEY"]
    backends = {
        arm: make_real_backend(api_key, args.base_url, args.model)
        for arm in ("C", "D", "E", "G")
    }
    raw_rows = {"C": [], "D": [], "E": [], "G": []}
    arm_wall_seconds = {arm: 0.0 for arm in raw_rows}

    for stream in fixture["streams"]:
        started = time.perf_counter()
        rows = run_c_stream(stream, backends["C"])
        arm_wall_seconds["C"] += time.perf_counter() - started
        raw_rows["C"].extend({"stream": stream["id"], **row} for row in rows)

        started = time.perf_counter()
        rows = run_d_stream(stream, backends["D"])
        arm_wall_seconds["D"] += time.perf_counter() - started
        raw_rows["D"].extend({"stream": stream["id"], **row} for row in rows)

        started = time.perf_counter()
        rows = run_e_stream(
            stream,
            backends["E"],
            query_char_budget=query_budget,
            memory_char_budget=state_budget,
        )
        arm_wall_seconds["E"] += time.perf_counter() - started
        raw_rows["E"].extend({"stream": stream["id"], **row} for row in rows)

        started = time.perf_counter()
        rows = run_g_stream(
            stream,
            backends["G"],
            state_char_budget=state_budget,
        )
        arm_wall_seconds["G"] += time.perf_counter() - started
        raw_rows["G"].extend({"stream": stream["id"], **row} for row in rows)

    scored = {
        arm: score_rows(raw_rows[arm], gold)
        for arm in ("C", "D", "E", "G")
    }

    d_only = [
        row["query_id"]
        for row in scored["D"]["rows"]
        if row["correct"]
        and not next(
            x["correct"]
            for x in scored["G"]["rows"]
            if x["query_id"] == row["query_id"]
        )
    ]
    g_only = [
        row["query_id"]
        for row in scored["G"]["rows"]
        if row["correct"]
        and not next(
            x["correct"]
            for x in scored["D"]["rows"]
            if x["query_id"] == row["query_id"]
        )
    ]

    output = {
        "format": "hcl-v05-strong-baseline-replication-v01",
        "model": args.model,
        "seed": 42,
        "fixture_sha256": fixture_sha,
        "gold_sha256": gold_sha,
        "query_context_char_budget": query_budget,
        "persistent_state_char_budget": state_budget,
        "primary_comparison": ["D", "G"],
        "secondary_baseline": "E",
        "diagnostic_oracle": "C",
        "d_answer_mode": "deterministic_current_stance_projection",
        "g_answer_mode": "deterministic_generic_state_readout",
        "paired": {
            "d_only": d_only,
            "g_only": g_only,
            "net_d_minus_g": scored["D"]["correct"] - scored["G"]["correct"],
        },
        "arms": {
            arm: {
                **scored[arm],
                "stream_scores": _stream_scores(scored[arm]["rows"]),
                "backend": backends[arm].metrics(),
                "wall_clock_seconds": round(arm_wall_seconds[arm], 6),
                "max_query_context_chars": max(
                    row["query_context_chars"] for row in raw_rows[arm]
                ),
                "max_persistent_state_chars": (
                    max(
                        row.get(
                            "state_chars",
                            row.get("memory_chars", 0),
                        )
                        for row in raw_rows[arm]
                    )
                    if arm in {"D", "E", "G"}
                    else None
                ),
            }
            for arm in ("C", "D", "E", "G")
        },
    }

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "fixture_sha256": fixture_sha,
                "gold_sha256": gold_sha,
                "C": scored["C"]["accuracy"],
                "D": scored["D"]["accuracy"],
                "E": scored["E"]["accuracy"],
                "G": scored["G"]["accuracy"],
                "D_minus_G": output["paired"]["net_d_minus_g"],
                "backend": {
                    arm: backends[arm].metrics()
                    for arm in ("C", "D", "E", "G")
                },
                "artifact": str(out),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
