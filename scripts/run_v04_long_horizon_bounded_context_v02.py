"""Independent long-horizon v0.2 fixture on the frozen D/E comparison harness."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any

from scripts.run_v04_long_horizon_bounded_context_v01 import (
    MEMORY_SYSTEM,
    event_prompt_payload,
    make_real_backend,
    run_c_stream,
    run_d_stream,
    run_e_stream,
    score_rows,
)


def validate_fixture_v02(fixture: dict[str, Any], gold: dict[str, Any]) -> None:
    assert fixture["format"] == "hcl-v04-long-horizon-bounded-context-v02-fixture"
    assert gold["format"] == "hcl-v04-long-horizon-bounded-context-v02-gold"
    assert fixture["query_context_char_budget"] == 8000
    assert fixture["ordinary_memory_char_budget"] == 6000
    assert len(fixture["streams"]) == 3

    event_ids: set[str] = set()
    query_ids: list[str] = []
    for stream in fixture["streams"]:
        assert len(stream["events"]) == 80
        assert len(stream["queries"]) == 6
        assert stream["target_agent_id"]

        primary_count = 0
        for event in stream["events"]:
            event_id = event["event_id"]
            assert event_id not in event_ids
            event_ids.add(event_id)
            assert event["raw_text"].strip()
            assert event["valid_time"] and event["recorded_at"]
            if (event.get("metadata") or {}).get("track") == "primary":
                primary_count += 1
        assert primary_count >= 8

        full_history_chars = len(
            json.dumps(
                [event_prompt_payload(event) for event in stream["events"]],
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        assert full_history_chars > fixture["query_context_char_budget"]

        previous_after = 0
        for query in stream["queries"]:
            assert "gold" not in query
            assert "risk_class" not in query
            after_event = int(query["after_event"])
            assert 1 <= after_event <= 80
            assert after_event >= previous_after
            previous_after = after_event
            assert query["target_agent_id"] == stream["target_agent_id"]
            assert len(query["allowed_labels"]) >= 2
            query_ids.append(query["query_id"])

    assert len(query_ids) == len(set(query_ids)) == 18
    assert set(query_ids) == set(gold["labels"])
    for query_id, truth in gold["labels"].items():
        assert truth["gold"]
        assert truth["risk_class"]
        stream = next(
            s
            for s in fixture["streams"]
            if any(q["query_id"] == query_id for q in s["queries"])
        )
        query = next(q for q in stream["queries"] if q["query_id"] == query_id)
        assert truth["gold"] in query["allowed_labels"]

    serialized_fixture = json.dumps(fixture, ensure_ascii=False, sort_keys=True)
    assert '"gold"' not in serialized_fixture
    assert '"risk_class"' not in serialized_fixture
    assert "PROPOSITION_REVISION" not in MEMORY_SYSTEM
    assert "BELIEF_ESTIMATE" not in MEMORY_SYSTEM
    assert "INFORMATION_EXPOSURE" not in MEMORY_SYSTEM


def load_and_validate_v02(
    fixture_path: str,
    gold_path: str,
) -> tuple[dict[str, Any], dict[str, Any], str, str]:
    fixture_bytes = Path(fixture_path).read_bytes()
    gold_bytes = Path(gold_path).read_bytes()
    fixture = json.loads(fixture_bytes)
    gold = json.loads(gold_bytes)
    validate_fixture_v02(fixture, gold)
    return (
        fixture,
        gold,
        hashlib.sha256(fixture_bytes).hexdigest(),
        hashlib.sha256(gold_bytes).hexdigest(),
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--fixtures",
        default="eval/v04/long_horizon_bounded_context_v02_fixture.json",
    )
    parser.add_argument(
        "--gold",
        default="eval/v04/long_horizon_bounded_context_v02_gold.json",
    )
    parser.add_argument("--model", default="deepseek-flash")
    parser.add_argument(
        "--base-url",
        default=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
    )
    parser.add_argument(
        "--out",
        default="artifacts/hcl-v04-long-horizon-v02/result.json",
    )
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()

    fixture, gold, fixture_sha, gold_sha = load_and_validate_v02(
        args.fixtures, args.gold
    )
    query_budget = int(fixture["query_context_char_budget"])
    memory_budget = int(fixture["ordinary_memory_char_budget"])

    if args.validate_only:
        print(
            json.dumps(
                {
                    "streams": len(fixture["streams"]),
                    "events": sum(len(s["events"]) for s in fixture["streams"]),
                    "queries": sum(len(s["queries"]) for s in fixture["streams"]),
                    "query_context_char_budget": query_budget,
                    "ordinary_memory_char_budget": memory_budget,
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
        for arm in ("C", "D", "E")
    }
    raw_rows = {"C": [], "D": [], "E": []}

    import time
    arm_wall_seconds = {"C": 0.0, "D": 0.0, "E": 0.0}

    for stream in fixture["streams"]:
        started = time.perf_counter()
        c_rows = run_c_stream(stream, backends["C"])
        arm_wall_seconds["C"] += time.perf_counter() - started
        raw_rows["C"].extend({"stream": stream["id"], **row} for row in c_rows)

        started = time.perf_counter()
        d_rows = run_d_stream(
            stream,
            backends["D"],
            query_char_budget=query_budget,
        )
        arm_wall_seconds["D"] += time.perf_counter() - started
        raw_rows["D"].extend({"stream": stream["id"], **row} for row in d_rows)

        started = time.perf_counter()
        e_rows = run_e_stream(
            stream,
            backends["E"],
            query_char_budget=query_budget,
            memory_char_budget=memory_budget,
        )
        arm_wall_seconds["E"] += time.perf_counter() - started
        raw_rows["E"].extend({"stream": stream["id"], **row} for row in e_rows)

    scored = {arm: score_rows(raw_rows[arm], gold) for arm in ("C", "D", "E")}
    output = {
        "format": "hcl-v04-long-horizon-bounded-context-v02",
        "model": args.model,
        "seed": 42,
        "fixture_sha256": fixture_sha,
        "gold_sha256": gold_sha,
        "query_context_char_budget": query_budget,
        "ordinary_memory_char_budget": memory_budget,
        "primary_comparison": ["D", "E"],
        "diagnostic_oracle": "C",
        "arms": {
            arm: {
                **scored[arm],
                "backend": backends[arm].metrics(),
                "wall_clock_seconds": round(arm_wall_seconds[arm], 6),
                "max_query_context_chars": max(
                    row["query_context_chars"] for row in raw_rows[arm]
                ),
                "max_persistent_state_chars": (
                    max(
                        row.get("state_chars", row.get("memory_chars", 0))
                        for row in raw_rows[arm]
                    )
                    if arm in {"D", "E"}
                    else None
                ),
            }
            for arm in ("C", "D", "E")
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
                "backend": {
                    arm: backends[arm].metrics() for arm in ("C", "D", "E")
                },
                "artifact": str(out),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
