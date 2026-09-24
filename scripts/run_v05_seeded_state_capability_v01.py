"""Fresh seeded end-to-end stance tracking comparison for HCL v0.5."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from hcl.v05.runtime import HCLV05Runtime
from hcl.v05.stance import StanceStatus
from scripts.run_v04_long_horizon_bounded_context_v01 import (
    MeteredBackend,
    _event_retrieval_score,
    event_from_mapping,
    event_prompt_payload,
    make_real_backend,
    parse_label,
)


MEMORY_SYSTEM = """Maintain a compact ordinary free-form memory for future
human-state reasoning over a long event stream.

You receive a frozen issue/value ontology. Use it as naming help, but do not use
a typed HCL cognition schema. Maintain whatever ordinary notes best support later
questions.

Be especially careful about:
- who actually received or observed information;
- source/world claims versus a person's own stance;
- explicit acceptance, rejection, or undecided state;
- correction/replacement events and whether the target actually received them;
- repeated confirmations that do not necessarily change stance;
- dated changes needed for historical questions.

Do not invent access or acceptance. Rewrite/compress freely. Return only the
updated memory text.
"""

MEMORY_REPAIR_SYSTEM = """Compress the supplied ordinary memory without adding
facts. Preserve perspective boundaries, explicit stance, corrections, important
dates, and the supplied ontology keys. Return only memory text within the
requested character limit.
"""

ANSWER_SYSTEM = """Answer a controlled human-state query from the supplied
context.

Return JSON only:
{"label":"<one exact label from allowed_labels>"}

Use the frozen issue/value ontology and only the supplied evidence. Answer the
target person's stance, not system/world truth. Receiving a correction does not
by itself establish acceptance. A correction known only to another person does
not change the target's stance. If no single value is currently supported, use
UNCERTAIN when allowed. For historical questions, answer at event_time rather
than the present.
"""


def validate_fixture(fixture: dict[str, Any], gold: dict[str, Any]) -> None:
    assert fixture["format"] == "hcl-v05-seeded-state-capability-v01-fixture"
    assert gold["format"] == "hcl-v05-seeded-state-capability-v01-gold"
    assert fixture["query_context_char_budget"] == 8000
    assert fixture["ordinary_memory_char_budget"] == 6000
    assert len(fixture["streams"]) == 3

    event_ids: set[str] = set()
    query_ids: list[str] = []
    for stream in fixture["streams"]:
        assert len(stream["events"]) == 72
        assert len(stream["queries"]) == 8
        ontology = stream["ontology_seed"]
        assert stream["target_issue_key"] in ontology
        assert len(ontology) == 3
        for issue, values in ontology.items():
            assert issue.strip()
            assert len(values) == 3
            assert len(values) == len(set(values))
            assert all(str(value).strip() for value in values)

        full_chars = len(
            json.dumps(
                [event_prompt_payload(event) for event in stream["events"]],
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        assert full_chars > fixture["query_context_char_budget"]

        for event in stream["events"]:
            eid = event["event_id"]
            assert eid not in event_ids
            event_ids.add(eid)
            assert event["raw_text"].strip()
            assert event["valid_time"]
            assert event["recorded_at"]

        previous_after = 0
        for query in stream["queries"]:
            assert "gold" not in query
            assert "risk_class" not in query
            assert query["target_agent_id"] == stream["target_agent_id"]
            assert query["target_issue_key"] == stream["target_issue_key"]
            assert int(query["after_event"]) >= previous_after
            previous_after = int(query["after_event"])
            assert 1 <= int(query["after_event"]) <= 72
            allowed = query["allowed_labels"]
            assert allowed[-1] == "UNCERTAIN"
            assert allowed[:-1] == ontology[stream["target_issue_key"]]
            query_ids.append(query["query_id"])

    assert len(query_ids) == len(set(query_ids)) == 24
    assert set(query_ids) == set(gold["labels"])
    for query_id, truth in gold["labels"].items():
        assert truth["gold"]
        assert truth["risk_class"]
        stream = next(
            stream
            for stream in fixture["streams"]
            if any(q["query_id"] == query_id for q in stream["queries"])
        )
        query = next(q for q in stream["queries"] if q["query_id"] == query_id)
        assert truth["gold"] in query["allowed_labels"]

    serialized = json.dumps(fixture, ensure_ascii=False, sort_keys=True)
    assert '"gold"' not in serialized
    assert '"risk_class"' not in serialized

    # Do not accidentally reuse concrete consumed v0.4 targets/domains.
    lowered = serialized.lower()
    for phrase in ("briefing room", "budget cap", "shipping dock"):
        assert phrase not in lowered
    for agent in ("lin", "maya", "nora"):
        import re
        assert re.search(rf"\b{agent}\b", lowered) is None


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


def update_memory(
    backend: MeteredBackend,
    memory: str,
    event: dict[str, Any],
    ontology_seed: dict[str, list[str]],
    *,
    memory_char_budget: int,
) -> tuple[str, int]:
    payload = {
        "memory_char_limit": memory_char_budget,
        "frozen_issue_value_ontology": ontology_seed,
        "previous_memory": memory,
        "new_event": event_prompt_payload(event),
    }
    out = backend.complete(
        [
            {"role": "system", "content": MEMORY_SYSTEM},
            {
                "role": "user",
                "content": json.dumps(payload, ensure_ascii=False, sort_keys=True),
            },
        ],
        max_tokens=2048,
        temperature=0.0,
    ).strip()
    repairs = 0
    if len(out) > memory_char_budget:
        repairs = 1
        out = backend.complete(
            [
                {"role": "system", "content": MEMORY_REPAIR_SYSTEM},
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "memory_char_limit": memory_char_budget,
                            "frozen_issue_value_ontology": ontology_seed,
                            "memory_to_compress": out,
                        },
                        ensure_ascii=False,
                        sort_keys=True,
                    ),
                },
            ],
            max_tokens=2048,
            temperature=0.0,
        ).strip()
    if len(out) > memory_char_budget:
        raise ValueError(
            f"ordinary memory exceeds frozen limit: {len(out)} > {memory_char_budget}"
        )
    return out, repairs


def ordinary_query_context(
    memory: str,
    events: list[dict[str, Any]],
    query: dict[str, Any],
    ontology_seed: dict[str, list[str]],
    *,
    query_char_budget: int,
) -> tuple[dict[str, Any], int]:
    ranked = sorted(
        events[: int(query["after_event"])],
        key=lambda e: _event_retrieval_score(e, query),
        reverse=True,
    )
    selected: list[dict[str, Any]] = []

    def payload():
        return {
            "frozen_issue_value_ontology": ontology_seed,
            "ordinary_memory": memory,
            "supporting_events": selected,
            "event_time": query.get("event_time"),
        }

    if len(json.dumps(payload(), ensure_ascii=False, sort_keys=True)) > query_char_budget:
        raise ValueError("ordinary memory + ontology exceed query-time budget")

    for event in ranked:
        candidate = selected + [event_prompt_payload(event)]
        test = {
            "frozen_issue_value_ontology": ontology_seed,
            "ordinary_memory": memory,
            "supporting_events": candidate,
            "event_time": query.get("event_time"),
        }
        if len(json.dumps(test, ensure_ascii=False, sort_keys=True)) <= query_char_budget:
            selected = candidate

    result = payload()
    size = len(json.dumps(result, ensure_ascii=False, sort_keys=True))
    assert size <= query_char_budget
    return result, size


def answer_label(
    backend: MeteredBackend,
    query: dict[str, Any],
    ontology_seed: dict[str, list[str]],
    dynamic_context: dict[str, Any],
    *,
    context_kind: str,
) -> str:
    task = {
        "context_kind": context_kind,
        "frozen_issue_value_ontology": ontology_seed,
        "target_agent_id": query["target_agent_id"],
        "target_issue_key": query["target_issue_key"],
        "event_time": query.get("event_time"),
        "allowed_labels": query["allowed_labels"],
        "question": query["question"],
        "context": dynamic_context,
    }
    raw = backend.complete_json(
        [
            {"role": "system", "content": ANSWER_SYSTEM},
            {
                "role": "user",
                "content": json.dumps(task, ensure_ascii=False, sort_keys=True),
            },
        ],
        max_tokens=192,
        temperature=0.0,
    )
    return parse_label(raw, query["allowed_labels"])


def stance_prediction(state, allowed_labels: list[str]) -> str:
    if (
        state.status == StanceStatus.AFFIRMED
        and state.affirmed_value_key in allowed_labels
    ):
        return str(state.affirmed_value_key)
    return "UNCERTAIN"


def state_snapshot(runtime: HCLV05Runtime) -> dict[str, Any]:
    return {
        "current_stances": [
            stance.as_dict()
            for stance in runtime.all_current_stances()
        ],
        "stance_event_count": len(runtime.stance_events),
        "semantic_failures": runtime.semantic_failures,
    }


def run_d_stream(
    stream: dict[str, Any],
    backend: MeteredBackend,
) -> list[dict[str, Any]]:
    runtime = HCLV05Runtime(semantic_catalog_seed=stream["ontology_seed"])
    rows: list[dict[str, Any]] = []
    ingested = 0
    semantic_repairs = 0
    semantic_errors: list[dict[str, str]] = []
    try:
        for query in stream["queries"]:
            target = int(query["after_event"])
            while ingested < target:
                raw_event = stream["events"][ingested]
                try:
                    result = runtime.ingest_event(
                        event_from_mapping(raw_event),
                        backend,
                    )
                    semantic_repairs += result.semantic_repair_count
                except Exception as exc:
                    semantic_errors.append(
                        {
                            "event_id": raw_event["event_id"],
                            "error": f"{type(exc).__name__}: {exc}",
                        }
                    )
                ingested += 1

            started = time.perf_counter()
            state = runtime.current_stance(
                query["target_agent_id"],
                query["target_issue_key"],
                event_time=query.get("event_time"),
            )
            prediction = stance_prediction(state, query["allowed_labels"])
            snapshot = state_snapshot(runtime)
            state_chars = len(
                json.dumps(snapshot, ensure_ascii=False, sort_keys=True)
            )
            rows.append(
                {
                    "query_id": query["query_id"],
                    "prediction": prediction,
                    "query_context_chars": len(
                        json.dumps(state.as_dict(), ensure_ascii=False, sort_keys=True)
                    ),
                    "target_current_stance": state.as_dict(),
                    "persistent_state": snapshot,
                    "state_chars": state_chars,
                    "query_elapsed_seconds": round(
                        time.perf_counter() - started, 6
                    ),
                    "semantic_repairs_so_far": semantic_repairs,
                    "semantic_errors_so_far": list(semantic_errors),
                }
            )
    finally:
        runtime.close()
    return rows


def run_e_stream(
    stream: dict[str, Any],
    backend: MeteredBackend,
    *,
    query_char_budget: int,
    memory_char_budget: int,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    memory = ""
    memory_repairs = 0
    queries_by_after: dict[int, list[dict[str, Any]]] = {}
    for query in stream["queries"]:
        queries_by_after.setdefault(int(query["after_event"]), []).append(query)

    for index, event in enumerate(stream["events"], start=1):
        memory, repaired = update_memory(
            backend,
            memory,
            event,
            stream["ontology_seed"],
            memory_char_budget=memory_char_budget,
        )
        memory_repairs += repaired
        for query in queries_by_after.get(index, []):
            started = time.perf_counter()
            context, context_chars = ordinary_query_context(
                memory,
                stream["events"],
                query,
                stream["ontology_seed"],
                query_char_budget=query_char_budget,
            )
            prediction = answer_label(
                backend,
                query,
                stream["ontology_seed"],
                context,
                context_kind="bounded_ordinary_persistent_memory",
            )
            rows.append(
                {
                    "query_id": query["query_id"],
                    "prediction": prediction,
                    "query_context_chars": context_chars,
                    "memory_chars": len(memory),
                    "query_context": context,
                    "query_elapsed_seconds": round(
                        time.perf_counter() - started, 6
                    ),
                    "memory_repairs_so_far": memory_repairs,
                }
            )
    return rows


def run_c_stream(
    stream: dict[str, Any],
    backend: MeteredBackend,
) -> list[dict[str, Any]]:
    rows = []
    for query in stream["queries"]:
        started = time.perf_counter()
        history = [
            event_prompt_payload(event)
            for event in stream["events"][: int(query["after_event"])]
        ]
        context = {
            "frozen_issue_value_ontology": stream["ontology_seed"],
            "event_time": query.get("event_time"),
            "event_history": history,
        }
        prediction = answer_label(
            backend,
            query,
            stream["ontology_seed"],
            context,
            context_kind="complete_raw_history_diagnostic",
        )
        rows.append(
            {
                "query_id": query["query_id"],
                "prediction": prediction,
                "query_context_chars": len(
                    json.dumps(context, ensure_ascii=False, sort_keys=True)
                ),
                "query_context": context,
                "query_elapsed_seconds": round(
                    time.perf_counter() - started, 6
                ),
            }
        )
    return rows


def score_rows(rows: list[dict[str, Any]], gold: dict[str, Any]) -> dict[str, Any]:
    scored = []
    failures = Counter()
    for row in rows:
        truth = gold["labels"][row["query_id"]]
        correct = row["prediction"] == truth["gold"]
        enriched = {
            **row,
            "gold": truth["gold"],
            "risk_class": truth["risk_class"],
            "correct": correct,
        }
        scored.append(enriched)
        if not correct:
            failures[truth["risk_class"]] += 1
    return {
        "correct": sum(int(row["correct"]) for row in scored),
        "total": len(scored),
        "accuracy": (
            sum(int(row["correct"]) for row in scored) / len(scored)
            if scored
            else 0.0
        ),
        "failure_risk_classes": dict(sorted(failures.items())),
        "rows": scored,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--fixtures",
        default="eval/v05/seeded_state_capability_v01_fixture.json",
    )
    parser.add_argument(
        "--gold",
        default="eval/v05/seeded_state_capability_v01_gold.json",
    )
    parser.add_argument("--model", default="deepseek-flash")
    parser.add_argument(
        "--base-url",
        default=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
    )
    parser.add_argument(
        "--out",
        default="artifacts/hcl-v05-seeded-state-capability-v01/result.json",
    )
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()

    fixture, gold, fixture_sha, gold_sha = load_and_validate(
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
    arm_wall_seconds = {"C": 0.0, "D": 0.0, "E": 0.0}

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
            memory_char_budget=memory_budget,
        )
        arm_wall_seconds["E"] += time.perf_counter() - started
        raw_rows["E"].extend({"stream": stream["id"], **row} for row in rows)

    scored = {
        arm: score_rows(raw_rows[arm], gold)
        for arm in ("C", "D", "E")
    }
    output = {
        "format": "hcl-v05-seeded-state-capability-v01",
        "model": args.model,
        "seed": 42,
        "fixture_sha256": fixture_sha,
        "gold_sha256": gold_sha,
        "query_context_char_budget": query_budget,
        "ordinary_memory_char_budget": memory_budget,
        "primary_comparison": ["D", "E"],
        "diagnostic_oracle": "C",
        "d_answer_mode": "deterministic_current_stance_projection",
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
                    arm: backends[arm].metrics()
                    for arm in ("C", "D", "E")
                },
                "artifact": str(out),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
