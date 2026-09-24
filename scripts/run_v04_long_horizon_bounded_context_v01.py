"""Bounded long-horizon HCL v0.4 capability comparison (D/E primary, C diagnostic)."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from hcl.v04.model import EventRecord
from hcl.v04.runtime import HCLV04Runtime
from hcl.v04.store import CognitionStore


MEMORY_SYSTEM = """Maintain a compact ordinary persistent memory for future
human-state reasoning over a long event stream.

This is an ordinary free-form memory, not a typed cognition schema. Preserve
only information likely to matter later. Be especially careful about:
- who actually received or observed information;
- a source saying something versus an established environment fact;
- whether a person explicitly accepted, rejected, or remained undecided;
- corrections/replacements and the earlier version they changed;
- dated changes needed to answer historical questions.

Do not invent acceptance, belief, or access. Do not copy every event. Rewrite
and compress the memory as needed. Return only the updated free-form memory
text, with no JSON wrapper or commentary.
"""

MEMORY_REPAIR_SYSTEM = """Compress the supplied ordinary memory without adding
facts. Preserve the important timeline, perspective boundaries, corrections,
and explicit acceptance/rejection/uncertainty. Return only the compressed memory
text within the requested character limit.
"""

ANSWER_SYSTEM = """Answer a controlled human-state reasoning query from the
supplied context.

Return JSON only:
{"label": "<one exact label from allowed_labels>"}

Use only supplied evidence. Track the target person's perspective rather than
substituting system/world truth. Receiving a proposition does not by itself
establish acceptance or belief. A correction known to somebody else does not
rewrite the target person's state. If the evidence does not support one current
stance, use UNCERTAIN when it is allowed. For historical questions, answer for
the requested historical time rather than the present.
"""

HARNESS_ONLY_METADATA_FIELDS = {"track", "sequence"}

STOPWORDS = {
    "the", "a", "an", "is", "are", "was", "were", "to", "of", "and", "or",
    "in", "on", "at", "as", "does", "do", "did", "which", "what", "currently",
    "current", "believe", "believes", "based", "only", "perspective", "after",
    "before", "now", "has", "have", "had", "been", "be", "it", "this", "that",
    "with", "from", "for", "supported", "evidence", "end", "stream",
}


class MeteredBackend:
    def __init__(self, backend: Any):
        self.backend = backend
        self.calls = 0
        self.json_calls = 0
        self.text_calls = 0
        self.input_chars = 0
        self.output_chars = 0
        self.provider_wall_seconds = 0.0

    def _record_input(self, messages: list[dict[str, str]]) -> None:
        self.calls += 1
        self.input_chars += sum(len(str(m.get("content", ""))) for m in messages)

    def complete_json(self, messages, *, max_tokens, temperature=0.0):
        self._record_input(messages)
        self.json_calls += 1
        started = time.perf_counter()
        try:
            out = self.backend.complete_json(
                messages, max_tokens=max_tokens, temperature=temperature
            )
        finally:
            self.provider_wall_seconds += time.perf_counter() - started
        self.output_chars += len(out)
        return out

    def complete(self, messages, *, max_tokens, temperature=0.0):
        self._record_input(messages)
        self.text_calls += 1
        started = time.perf_counter()
        try:
            out = self.backend.complete(
                messages, max_tokens=max_tokens, temperature=temperature
            )
        finally:
            self.provider_wall_seconds += time.perf_counter() - started
        self.output_chars += len(out)
        return out

    def metrics(self) -> dict[str, int]:
        return {
            "calls": self.calls,
            "json_calls": self.json_calls,
            "text_calls": self.text_calls,
            "input_chars": self.input_chars,
            "output_chars": self.output_chars,
            "provider_wall_seconds": round(self.provider_wall_seconds, 6),
        }


def make_real_backend(api_key: str, base_url: str, model: str) -> MeteredBackend:
    from hcl.v04.backends import (
        DEEPSEEK_FLASH_CAPABILITIES,
        OpenAICompatibleBackend,
    )

    return MeteredBackend(
        OpenAICompatibleBackend(
            api_key=api_key,
            base_url=base_url,
            model=model,
            seed=42,
            capabilities=DEEPSEEK_FLASH_CAPABILITIES,
        )
    )


def model_visible_metadata(raw: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in dict(raw.get("metadata") or {}).items()
        if key not in HARNESS_ONLY_METADATA_FIELDS
    }


def event_from_mapping(raw: dict[str, Any]) -> EventRecord:
    return EventRecord(
        event_id=raw["event_id"],
        valid_time=raw["valid_time"],
        recorded_at=raw["recorded_at"],
        raw_text=raw["raw_text"],
        source_id=raw["source_id"],
        actor_id=raw.get("actor_id"),
        observer_ids=tuple(raw.get("observer_ids") or []),
        recipient_ids=tuple(raw.get("recipient_ids") or []),
        semantic_version=raw.get("semantic_version", "v04.1"),
        supersedes=raw.get("supersedes"),
        metadata=model_visible_metadata(raw),
    )


def event_prompt_payload(raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "event_id": raw["event_id"],
        "valid_time": raw["valid_time"],
        "recorded_at": raw["recorded_at"],
        "source_id": raw["source_id"],
        "actor_id": raw.get("actor_id"),
        "observer_ids": raw.get("observer_ids") or [],
        "recipient_ids": raw.get("recipient_ids") or [],
        "raw_text": raw["raw_text"],
        "metadata": model_visible_metadata(raw),
    }


def _tokens(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9]+", text.lower())
        if len(token) > 1 and token not in STOPWORDS
    }


def validate_fixture(fixture: dict[str, Any], gold: dict[str, Any]) -> None:
    assert fixture["format"] == "hcl-v04-long-horizon-bounded-context-v01-fixture"
    assert gold["format"] == "hcl-v04-long-horizon-bounded-context-v01-gold"
    assert fixture["query_context_char_budget"] > 0
    assert 0 < fixture["ordinary_memory_char_budget"] <= fixture["query_context_char_budget"]
    streams = fixture["streams"]
    assert len(streams) == 3

    query_ids: list[str] = []
    event_ids: set[str] = set()
    for stream in streams:
        assert len(stream["events"]) == 80
        assert len(stream["queries"]) == 6
        for event in stream["events"]:
            eid = event["event_id"]
            assert eid not in event_ids
            event_ids.add(eid)
            assert event["raw_text"].strip()
            assert event["valid_time"] and event["recorded_at"]
        primary_count = sum(
            1
            for event in stream["events"]
            if (event.get("metadata") or {}).get("track") == "primary"
        )
        assert primary_count >= 8
        full_history_chars = len(
            json.dumps(
                [event_prompt_payload(event) for event in stream["events"]],
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        assert full_history_chars > fixture["query_context_char_budget"]

        for query in stream["queries"]:
            assert "gold" not in query
            assert "risk_class" not in query
            assert 1 <= int(query["after_event"]) <= 80
            assert query["target_agent_id"] == stream["target_agent_id"]
            assert len(query["allowed_labels"]) >= 2
            query_ids.append(query["query_id"])

    assert len(query_ids) == len(set(query_ids)) == 18
    assert set(query_ids) == set(gold["labels"])
    for query_id, row in gold["labels"].items():
        assert row["gold"]
        assert row["risk_class"]
        stream = next(
            s for s in streams if any(q["query_id"] == query_id for q in s["queries"])
        )
        query = next(q for q in stream["queries"] if q["query_id"] == query_id)
        assert row["gold"] in query["allowed_labels"]

    serialized_fixture = json.dumps(fixture, sort_keys=True)
    assert '"gold"' not in serialized_fixture
    assert '"risk_class"' not in serialized_fixture
    assert "PROPOSITION_REVISION" not in MEMORY_SYSTEM
    assert "BELIEF_ESTIMATE" not in MEMORY_SYSTEM
    assert "INFORMATION_EXPOSURE" not in MEMORY_SYSTEM


def parse_label(raw: str, allowed_labels: list[str]) -> str:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return "__INVALID_JSON__"
    label = str(payload.get("label", "")).strip().upper()
    allowed = {str(x).upper() for x in allowed_labels}
    if label not in allowed:
        return f"__INVALID_LABEL__:{label}"
    return label


def update_ordinary_memory(
    backend: MeteredBackend,
    memory: str,
    event: dict[str, Any],
    *,
    memory_char_budget: int,
) -> tuple[str, int]:
    payload = {
        "memory_char_limit": memory_char_budget,
        "previous_memory": memory,
        "new_event": event_prompt_payload(event),
    }
    messages = [
        {"role": "system", "content": MEMORY_SYSTEM},
        {"role": "user", "content": json.dumps(payload, ensure_ascii=False, sort_keys=True)},
    ]
    out = backend.complete(messages, max_tokens=2048, temperature=0.0).strip()
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
            f"ordinary memory exceeds frozen character budget: {len(out)} > "
            f"{memory_char_budget}"
        )
    return out, repairs


def _event_retrieval_score(
    event: dict[str, Any], query: dict[str, Any]
) -> tuple[int, str, str]:
    query_tokens = _tokens(
        query["question"] + " " + " ".join(query.get("allowed_labels") or [])
    )
    event_tokens = _tokens(event["raw_text"])
    target = query["target_agent_id"].lower()
    target_access = (
        str(event.get("actor_id") or "").lower() == target
        or target in {str(x).lower() for x in event.get("recipient_ids") or []}
        or target in {str(x).lower() for x in event.get("observer_ids") or []}
        or target in event["raw_text"].lower()
    )
    overlap = len(query_tokens & event_tokens)
    score = overlap * 20 + int(target_access) * 12
    return score, str(event.get("recorded_at") or ""), str(event["event_id"])


def ordinary_query_context(
    memory: str,
    events: list[dict[str, Any]],
    query: dict[str, Any],
    *,
    query_char_budget: int,
) -> tuple[dict[str, Any], int]:
    ranked = sorted(
        events[: int(query["after_event"])],
        key=lambda e: _event_retrieval_score(e, query),
        reverse=True,
    )
    selected: list[dict[str, Any]] = []
    base = {"ordinary_memory": memory, "supporting_events": selected}
    if len(json.dumps(base, ensure_ascii=False, sort_keys=True)) > query_char_budget:
        raise ValueError("ordinary memory alone exceeds query-time context budget")

    for event in ranked:
        candidate = selected + [event_prompt_payload(event)]
        payload = {"ordinary_memory": memory, "supporting_events": candidate}
        size = len(json.dumps(payload, ensure_ascii=False, sort_keys=True))
        if size <= query_char_budget:
            selected = candidate

    payload = {"ordinary_memory": memory, "supporting_events": selected}
    size = len(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    assert size <= query_char_budget
    return payload, size


def _assertion_text(assertion: dict[str, Any]) -> str:
    return " ".join(
        str(assertion.get(key) or "")
        for key in (
            "assertion_type",
            "subject_agent_id",
            "proposition_text",
            "hypothesis_text",
            "belief_stance",
            "support_level",
            "projection_status",
        )
    )


def _assertion_score(assertion: dict[str, Any], query: dict[str, Any]) -> tuple[int, str]:
    qtokens = _tokens(
        query["question"] + " " + " ".join(query.get("allowed_labels") or [])
    )
    atokens = _tokens(_assertion_text(assertion))
    target = query["target_agent_id"].lower()
    subject_match = str(assertion.get("subject_agent_id") or "").lower() == target
    overlap = len(qtokens & atokens)
    stance = int(assertion.get("assertion_type") == "BELIEF_ESTIMATE")
    revision = int(assertion.get("assertion_type") == "PROPOSITION_REVISION")
    score = overlap * 20 + int(subject_match) * 14 + stance * 5 + revision * 4
    return score, str(assertion.get("system_record_time") or "")


def compact_hcl_context(
    context: dict[str, Any],
    query: dict[str, Any],
    *,
    query_char_budget: int,
) -> tuple[dict[str, Any], int]:
    all_assertions = list(context.get("relevant_assertions") or [])
    ranked = sorted(
        all_assertions,
        key=lambda a: _assertion_score(a, query),
        reverse=True,
    )

    chosen = ranked[:18]
    props = {
        p
        for row in chosen
        for p in (row.get("proposition_id"), row.get("related_proposition_id"))
        if p
    }
    linked = [
        row
        for row in all_assertions
        if row not in chosen
        and (
            row.get("proposition_id") in props
            or row.get("related_proposition_id") in props
        )
    ]
    for row in linked:
        if row not in chosen:
            chosen.append(row)

    chosen = sorted(chosen, key=lambda a: _assertion_score(a, query), reverse=True)
    evidence_ids = {
        eid
        for row in chosen
        for eid in (row.get("evidence_event_ids") or [])
    }
    evidence = [
        row
        for row in (context.get("evidence") or [])
        if row.get("event_id") in evidence_ids
    ]
    conflicts = [
        row
        for row in (context.get("unresolved_conflicts") or [])
        if str(row.get("subject_agent_id") or "").lower()
        in {"", query["target_agent_id"].lower()}
    ]
    unsupported = [
        row
        for row in (context.get("unsupported_conclusions") or [])
        if query["target_agent_id"].lower() in str(row).lower()
    ]

    def payload() -> dict[str, Any]:
        return {
            "state_version": context.get("state_version"),
            "relevant_assertions": chosen,
            "evidence": evidence,
            "unresolved_conflicts": conflicts,
            "unsupported_conclusions": unsupported,
        }

    while len(json.dumps(payload(), ensure_ascii=False, sort_keys=True)) > query_char_budget:
        if evidence:
            evidence.pop()
        elif len(chosen) > 4:
            chosen.pop()
        elif unsupported:
            unsupported.pop()
        elif conflicts:
            conflicts.pop()
        else:
            raise ValueError("HCL query projection cannot fit frozen context budget")

    result = payload()
    size = len(json.dumps(result, ensure_ascii=False, sort_keys=True))
    assert size <= query_char_budget
    return result, size


def persistent_hcl_state_chars(store: CognitionStore) -> int:
    """Size the derived persistent cognition state, excluding raw event history."""
    assertions = [
        dict(row)
        for row in store.conn.execute(
            """
            SELECT * FROM assertions
            WHERE status IN ('ACTIVE', 'UNRESOLVED')
            ORDER BY assertion_id
            """
        ).fetchall()
    ]
    propositions = [
        dict(row)
        for row in store.conn.execute(
            "SELECT * FROM propositions ORDER BY proposition_id"
        ).fetchall()
    ]
    return len(
        json.dumps(
            {"assertions": assertions, "propositions": propositions},
            ensure_ascii=False,
            sort_keys=True,
        )
    )


def answer_label(
    backend: MeteredBackend,
    query: dict[str, Any],
    *,
    arm: str,
    dynamic_context: dict[str, Any],
) -> str:
    task = {
        "arm_context_kind": {
            "C": "complete_raw_history",
            "D": "bounded_structured_persistent_context",
            "E": "bounded_ordinary_persistent_memory",
        }[arm],
        "target_agent_id": query["target_agent_id"],
        "allowed_labels": query["allowed_labels"],
        "question": query["question"],
        "context": dynamic_context,
    }
    raw = backend.complete_json(
        [
            {"role": "system", "content": ANSWER_SYSTEM},
            {"role": "user", "content": json.dumps(task, ensure_ascii=False, sort_keys=True)},
        ],
        max_tokens=192,
        temperature=0.0,
    )
    return parse_label(raw, query["allowed_labels"])


def run_d_stream(
    stream: dict[str, Any],
    backend: MeteredBackend,
    *,
    query_char_budget: int,
) -> list[dict[str, Any]]:
    runtime = HCLV04Runtime(CognitionStore())
    rows: list[dict[str, Any]] = []
    ingested = 0
    semantic_repairs = 0
    try:
        for query in stream["queries"]:
            target = int(query["after_event"])
            while ingested < target:
                result = runtime.ingest_event(
                    event_from_mapping(stream["events"][ingested]),
                    backend,
                )
                semantic_repairs += result.semantic_repair_count
                ingested += 1

            query_started = time.perf_counter()
            raw_context = runtime.build_view(
                "__system__",
                query.get("event_time"),
                None,
                query["question"],
            ).as_dict()
            state_chars = persistent_hcl_state_chars(runtime.store)
            bounded, context_chars = compact_hcl_context(
                raw_context, query, query_char_budget=query_char_budget
            )
            prediction = answer_label(
                backend, query, arm="D", dynamic_context=bounded
            )
            query_elapsed = time.perf_counter() - query_started
            rows.append(
                {
                    "query_id": query["query_id"],
                    "prediction": prediction,
                    "query_context_chars": context_chars,
                "query_elapsed_seconds": round(query_elapsed, 6),
                    "state_version": raw_context.get("state_version"),
                    "state_chars": state_chars,
                    "query_elapsed_seconds": round(query_elapsed, 6),
                    "semantic_repairs_so_far": semantic_repairs,
                }
            )
    finally:
        runtime.store.close()
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
    processed = 0
    memory_repairs = 0
    queries_by_after: dict[int, list[dict[str, Any]]] = {}
    for query in stream["queries"]:
        queries_by_after.setdefault(int(query["after_event"]), []).append(query)

    for index, event in enumerate(stream["events"], start=1):
        memory, repaired = update_ordinary_memory(
            backend,
            memory,
            event,
            memory_char_budget=memory_char_budget,
        )
        memory_repairs += repaired
        processed = index
        for query in queries_by_after.get(index, []):
            query_started = time.perf_counter()
            bounded, context_chars = ordinary_query_context(
                memory,
                stream["events"],
                query,
                query_char_budget=query_char_budget,
            )
            prediction = answer_label(
                backend, query, arm="E", dynamic_context=bounded
            )
            query_elapsed = time.perf_counter() - query_started
            rows.append(
                {
                    "query_id": query["query_id"],
                    "prediction": prediction,
                    "query_context_chars": context_chars,
                    "memory_chars": len(memory),
                    "query_elapsed_seconds": round(query_elapsed, 6),
                    "memory_repairs_so_far": memory_repairs,
                    "events_processed": processed,
                }
            )
    return rows


def run_c_stream(
    stream: dict[str, Any],
    backend: MeteredBackend,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for query in stream["queries"]:
        query_started = time.perf_counter()
        events = [
            event_prompt_payload(event)
            for event in stream["events"][: int(query["after_event"])]
        ]
        dynamic = {
            "event_time": query.get("event_time"),
            "event_history": events,
        }
        context_chars = len(json.dumps(dynamic, ensure_ascii=False, sort_keys=True))
        prediction = answer_label(
            backend, query, arm="C", dynamic_context=dynamic
        )
        query_elapsed = time.perf_counter() - query_started
        rows.append(
            {
                "query_id": query["query_id"],
                "prediction": prediction,
                "query_context_chars": context_chars,
            }
        )
    return rows


def score_rows(
    rows: list[dict[str, Any]],
    gold: dict[str, Any],
) -> dict[str, Any]:
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
        "correct": sum(row["correct"] for row in scored),
        "total": len(scored),
        "accuracy": (
            sum(row["correct"] for row in scored) / len(scored)
            if scored
            else 0.0
        ),
        "failure_risk_classes": dict(sorted(failures.items())),
        "rows": scored,
    }


def load_and_validate(
    fixture_path: str,
    gold_path: str,
) -> tuple[dict[str, Any], dict[str, Any], str, str]:
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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--fixtures",
        default="eval/v04/long_horizon_bounded_context_v01_fixture.json",
    )
    parser.add_argument(
        "--gold",
        default="eval/v04/long_horizon_bounded_context_v01_gold.json",
    )
    parser.add_argument("--model", default="deepseek-flash")
    parser.add_argument(
        "--base-url",
        default=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
    )
    parser.add_argument(
        "--out",
        default="artifacts/hcl-v04-long-horizon-v01/result.json",
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
        c_stream_rows = run_c_stream(stream, backends["C"])
        arm_wall_seconds["C"] += time.perf_counter() - started
        for row in c_stream_rows:
            raw_rows["C"].append({"stream": stream["id"], **row})
        started = time.perf_counter()
        d_stream_rows = run_d_stream(
            stream,
            backends["D"],
            query_char_budget=query_budget,
        )
        arm_wall_seconds["D"] += time.perf_counter() - started
        for row in d_stream_rows:
            raw_rows["D"].append({"stream": stream["id"], **row})

        started = time.perf_counter()
        e_stream_rows = run_e_stream(
            stream,
            backends["E"],
            query_char_budget=query_budget,
            memory_char_budget=memory_budget,
        )
        arm_wall_seconds["E"] += time.perf_counter() - started
        for row in e_stream_rows:
            raw_rows["E"].append({"stream": stream["id"], **row})

    scored = {
        arm: score_rows(raw_rows[arm], gold)
        for arm in ("C", "D", "E")
    }
    output = {
        "format": "hcl-v04-long-horizon-bounded-context-v01",
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
