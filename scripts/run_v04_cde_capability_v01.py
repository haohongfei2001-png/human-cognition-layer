from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from hcl.v04.backends import (
    DEEPSEEK_FLASH_CAPABILITIES,
    OpenAICompatibleBackend,
)
from hcl.v04.model import EventRecord
from hcl.v04.runtime import HCLV04Runtime
from hcl.v04.store import CognitionStore


ANSWER_SYSTEM = """You are answering a controlled human-state reasoning query.

Return JSON only:
{"label": "<one exact label from allowed_labels>"}

Track the target person's perspective rather than substituting world truth.
Distinguish:
- a source saying P from P being true;
- receiving P from accepting P;
- system knowledge from the target person's belief;
- later corrections from earlier historical state.

A supported BELIEF_ESTIMATE is the current best estimate of that person's belief
until later evidence supports a belief revision. SOURCE_ASSERTION or
INFORMATION_EXPOSURE alone does not supersede an existing supported belief.
When multiple BELIEF_ESTIMATE records exist for the same issue, prefer the
latest evidence-supported stance while preserving explicit uncertainty where
the evidence genuinely does not decide.
If the evidence does not support one belief label, use UNCERTAIN when it is an
allowed label.
"""


class CountingBackend:
    def __init__(self, backend):
        self.backend = backend
        self.calls = 0
        self.json_calls = 0
        self.text_calls = 0
        self.input_chars = 0
        self.output_chars = 0

    def _record_input(self, messages):
        self.calls += 1
        self.input_chars += sum(len(str(m.get("content", ""))) for m in messages)

    def complete_json(self, messages, *, max_tokens, temperature=0.0):
        self._record_input(messages)
        self.json_calls += 1
        out = self.backend.complete_json(
            messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        self.output_chars += len(out)
        return out

    def complete(self, messages, *, max_tokens, temperature=0.0):
        self._record_input(messages)
        self.text_calls += 1
        out = self.backend.complete(
            messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        self.output_chars += len(out)
        return out

    def metrics(self):
        return {
            "calls": self.calls,
            "json_calls": self.json_calls,
            "text_calls": self.text_calls,
            "input_chars": self.input_chars,
            "output_chars": self.output_chars,
        }


def make_backend(api_key: str, base_url: str, model: str):
    return CountingBackend(
        OpenAICompatibleBackend(
            api_key=api_key,
            base_url=base_url,
            model=model,
            seed=42,
            capabilities=DEEPSEEK_FLASH_CAPABILITIES,
        )
    )


def event_from_mapping(raw: dict) -> EventRecord:
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
        metadata=dict(raw.get("metadata") or {}),
    )


def normalize_label_json(raw: str, allowed_labels: list[str]) -> str:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return "__INVALID_JSON__"
    label = str(payload.get("label", "")).strip().upper()
    if label not in {x.upper() for x in allowed_labels}:
        return f"__INVALID_LABEL__:{label}"
    return label


def answer_from_context(backend, query: dict, context: dict) -> str:
    raw = backend.complete_json(
        [
            {"role": "system", "content": ANSWER_SYSTEM},
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "allowed_labels": query["allowed_labels"],
                        "question": query["question"],
                        "query_context": context,
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                ),
            },
        ],
        max_tokens=256,
        temperature=0.0,
    )
    return normalize_label_json(raw, query["allowed_labels"])


def answer_from_memory(backend, query: dict, events: list[dict]) -> str:
    raw = backend.complete_json(
        [
            {"role": "system", "content": ANSWER_SYSTEM},
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "allowed_labels": query["allowed_labels"],
                        "question": query["question"],
                        "event_history": events,
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                ),
            },
        ],
        max_tokens=256,
        temperature=0.0,
    )
    return normalize_label_json(raw, query["allowed_labels"])


def state_signature(context: dict) -> list:
    rows = []
    for a in context["relevant_assertions"]:
        rows.append(
            (
                a.get("assertion_type"),
                a.get("subject_agent_id"),
                a.get("belief_stance"),
                a.get("proposition_text"),
                tuple(a.get("evidence_event_ids") or []),
                a.get("valid_time"),
            )
        )
    return sorted(rows, key=repr)


def run_dynamic(scenario: dict, backend) -> list[dict]:
    runtime = HCLV04Runtime(CognitionStore())
    results = []
    repair_count = 0
    ingested = 0
    try:
        for query_index, query in enumerate(scenario["queries"]):
            target = int(query["after_event"])
            while ingested < target:
                raw_event = scenario["events"][ingested]
                ingest = runtime.ingest_event(
                    event_from_mapping(raw_event),
                    backend,
                )
                repair_count += ingest.semantic_repair_count
                ingested += 1

            context = runtime.build_view(
                "__system__",
                None,
                None,
                query["question"],
            ).as_dict()
            prediction = answer_from_context(backend, query, context)
            results.append(
                {
                    "query_index": query_index,
                    "after_event": target,
                    "gold": query["gold"],
                    "prediction": prediction,
                    "correct": prediction == query["gold"],
                    "state_signature": state_signature(context),
                    "state_version": context["state_version"],
                }
            )
    finally:
        runtime.store.close()
    for row in results:
        row["scenario_semantic_repairs"] = repair_count
    return results


def run_reconstruction(scenario: dict, backend) -> list[dict]:
    results = []
    repair_count = 0
    for query_index, query in enumerate(scenario["queries"]):
        runtime = HCLV04Runtime(CognitionStore())
        try:
            target = int(query["after_event"])
            for raw_event in scenario["events"][:target]:
                ingest = runtime.ingest_event(
                    event_from_mapping(raw_event),
                    backend,
                )
                repair_count += ingest.semantic_repair_count
            context = runtime.build_view(
                "__system__",
                None,
                None,
                query["question"],
            ).as_dict()
            prediction = answer_from_context(backend, query, context)
            results.append(
                {
                    "query_index": query_index,
                    "after_event": target,
                    "gold": query["gold"],
                    "prediction": prediction,
                    "correct": prediction == query["gold"],
                    "state_signature": state_signature(context),
                    "state_version": context["state_version"],
                }
            )
        finally:
            runtime.store.close()
    for row in results:
        row["scenario_semantic_repairs"] = repair_count
    return results


def run_memory(scenario: dict, backend) -> list[dict]:
    results = []
    for query_index, query in enumerate(scenario["queries"]):
        target = int(query["after_event"])
        history = scenario["events"][:target]
        prediction = answer_from_memory(backend, query, history)
        results.append(
            {
                "query_index": query_index,
                "after_event": target,
                "gold": query["gold"],
                "prediction": prediction,
                "correct": prediction == query["gold"],
            }
        )
    return results


def summarize(rows: list[dict], backend: CountingBackend) -> dict:
    total = len(rows)
    correct = sum(1 for row in rows if row["correct"])
    failures = [
        {
            "scenario": row["scenario"],
            "query_index": row["query_index"],
            "gold": row["gold"],
            "prediction": row["prediction"],
        }
        for row in rows
        if not row["correct"]
    ]
    return {
        "total": total,
        "correct": correct,
        "accuracy": correct / total if total else 0.0,
        "failures": failures,
        "backend": backend.metrics(),
        "semantic_repairs": sum(
            row.get("scenario_semantic_repairs", 0) for row in rows
        ),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--fixtures",
        default="eval/v04/cde_capability_v01.json",
    )
    parser.add_argument("--model", default="deepseek-flash")
    parser.add_argument(
        "--base-url",
        default=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
    )
    parser.add_argument(
        "--out",
        default="artifacts/hcl-v04-cde/result.json",
    )
    args = parser.parse_args()

    api_key = os.environ["DEEPSEEK_API_KEY"]
    fixtures = json.loads(Path(args.fixtures).read_text(encoding="utf-8"))

    backends = {
        "C": make_backend(api_key, args.base_url, args.model),
        "D": make_backend(api_key, args.base_url, args.model),
        "E": make_backend(api_key, args.base_url, args.model),
    }
    arm_rows = {"C": [], "D": [], "E": []}
    pair_rows = []

    for scenario in fixtures:
        c_rows = run_reconstruction(scenario, backends["C"])
        d_rows = run_dynamic(scenario, backends["D"])
        e_rows = run_memory(scenario, backends["E"])

        for arm, rows in (("C", c_rows), ("D", d_rows), ("E", e_rows)):
            for row in rows:
                arm_rows[arm].append({"scenario": scenario["id"], **row})

        for c_row, d_row in zip(c_rows, d_rows):
            pair_rows.append(
                {
                    "scenario": scenario["id"],
                    "query_index": c_row["query_index"],
                    "c_d_state_equal": (
                        c_row["state_signature"] == d_row["state_signature"]
                    ),
                    "c_prediction": c_row["prediction"],
                    "d_prediction": d_row["prediction"],
                    "gold": c_row["gold"],
                }
            )

    output = {
        "format": "hcl-v04-cde-capability-v01",
        "model": args.model,
        "seed": 42,
        "scenario_count": len(fixtures),
        "query_count": sum(len(x["queries"]) for x in fixtures),
        "arms": {
            arm: summarize(arm_rows[arm], backends[arm])
            for arm in ("C", "D", "E")
        },
        "c_d_state_equal": {
            "equal": sum(1 for x in pair_rows if x["c_d_state_equal"]),
            "total": len(pair_rows),
        },
        "pairs": pair_rows,
        "rows": arm_rows,
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
                "C": output["arms"]["C"]["accuracy"],
                "D": output["arms"]["D"]["accuracy"],
                "E": output["arms"]["E"]["accuracy"],
                "c_d_state_equal": output["c_d_state_equal"],
                "artifact": str(out),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
