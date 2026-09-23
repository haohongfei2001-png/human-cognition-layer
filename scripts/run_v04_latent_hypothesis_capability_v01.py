from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from hcl.v04.backends import (
    DEEPSEEK_FLASH_CAPABILITIES,
    OpenAICompatibleBackend,
)
from hcl.v04.hypotheses import (
    HypothesisStatus,
    HypothesisTarget,
    HypothesisTracker,
)
from hcl.v04.model import EventRecord
from hcl.v04.store import CognitionStore


PREDICT_SYSTEM = """You predict the next observable behavior in a controlled
human-state reasoning scenario.

Return JSON only:
{"label": "<one exact label from allowed_labels>"}

Use the evidence and candidate interpretations provided.
Do not treat a hypothesis as fact merely because it is currently stronger.
Preserve uncertainty when alternatives remain materially plausible.
"""


class CountingBackend:
    def __init__(self, backend):
        self.backend = backend
        self.calls = 0
        self.input_chars = 0
        self.output_chars = 0

    def complete_json(self, messages, *, max_tokens, temperature=0.0):
        self.calls += 1
        self.input_chars += sum(len(str(x.get("content", ""))) for x in messages)
        out = self.backend.complete_json(
            messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        self.output_chars += len(out)
        return out

    def metrics(self):
        return {
            "calls": self.calls,
            "input_chars": self.input_chars,
            "output_chars": self.output_chars,
        }


def make_backend(api_key, base_url, model):
    return CountingBackend(
        OpenAICompatibleBackend(
            api_key=api_key,
            base_url=base_url,
            model=model,
            seed=42,
            capabilities=DEEPSEEK_FLASH_CAPABILITIES,
        )
    )


def event_from_mapping(raw):
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
        metadata=dict(raw.get("metadata") or {}),
    )


def target_from_mapping(raw):
    return HypothesisTarget(
        target_id=raw["target_id"],
        subject_agent_id=raw["subject_agent_id"],
        target_kind=raw["target_kind"],
        question=raw["question"],
        candidate_definitions=tuple(
            (str(x[0]).upper(), str(x[1]))
            for x in raw["candidates"]
        ),
    )


def event_payload(event):
    return {
        "event_id": event.event_id,
        "valid_time": event.valid_time,
        "recorded_at": event.recorded_at,
        "source_id": event.source_id,
        "actor_id": event.actor_id,
        "observer_ids": list(event.observer_ids),
        "recipient_ids": list(event.recipient_ids),
        "raw_text": event.raw_text,
        "metadata": event.metadata,
    }


def state_payload(state):
    return {
        "target_id": state.target_id,
        "version": state.version,
        "semantic_version": state.semantic_version,
        "candidates": [
            {
                "label": c.label,
                "description": c.description,
                "status": c.status.value,
                "support_event_ids": list(c.support_event_ids),
                "counterevidence_event_ids": list(c.counterevidence_event_ids),
                "unresolved_event_ids": list(c.unresolved_event_ids),
                "rationale": c.rationale,
            }
            for c in state.candidates
        ],
    }


def referenced_evidence(store, state):
    ids = []
    seen = set()
    for c in state.candidates:
        for eid in (
            list(c.support_event_ids)
            + list(c.counterevidence_event_ids)
            + list(c.unresolved_event_ids)
        ):
            if eid not in seen:
                seen.add(eid)
                ids.append(eid)
    return [event_payload(store.get_event(eid)) for eid in ids]


def parse_label(raw, allowed):
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return "__INVALID_JSON__"
    label = str(payload.get("label", "")).strip().upper()
    allowed_set = {x.upper() for x in allowed}
    if label not in allowed_set:
        return f"__INVALID_LABEL__:{label}"
    return label


def predict_from_hypotheses(backend, query, target, state, evidence):
    raw = backend.complete_json(
        [
            {"role": "system", "content": PREDICT_SYSTEM},
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "allowed_labels": query["allowed_labels"],
                        "question": query["question"],
                        "target": {
                            "subject_agent_id": target.subject_agent_id,
                            "target_kind": target.target_kind,
                            "latent_question": target.question,
                            "candidate_definitions": list(
                                target.candidate_definitions
                            ),
                        },
                        "hypothesis_state": state_payload(state),
                        "referenced_evidence": evidence,
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                ),
            },
        ],
        max_tokens=256,
        temperature=0.0,
    )
    return parse_label(raw, query["allowed_labels"])


def predict_from_history(backend, query, target, events):
    raw = backend.complete_json(
        [
            {"role": "system", "content": PREDICT_SYSTEM},
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "allowed_labels": query["allowed_labels"],
                        "question": query["question"],
                        "target": {
                            "subject_agent_id": target.subject_agent_id,
                            "target_kind": target.target_kind,
                            "latent_question": target.question,
                            "candidate_definitions": list(
                                target.candidate_definitions
                            ),
                        },
                        "event_history": [event_payload(x) for x in events],
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                ),
            },
        ],
        max_tokens=256,
        temperature=0.0,
    )
    return parse_label(raw, query["allowed_labels"])


def hidden_rank(state, hidden):
    rank = {
        HypothesisStatus.SUPPORTED: 3,
        HypothesisStatus.PLAUSIBLE: 2,
        HypothesisStatus.WEAKENED: 1,
        HypothesisStatus.CONTRADICTED: 0,
    }
    by_label = {c.label: c for c in state.candidates}
    hidden_status = by_label[hidden].status
    max_rank = max(rank[c.status] for c in state.candidates)
    return {
        "hidden_status": hidden_status.value,
        "hidden_top_or_tied": rank[hidden_status] == max_rank,
        "other_unknown_status": by_label["OTHER_UNKNOWN"].status.value,
    }


def signature(state):
    return sorted(
        [
            (
                c.label,
                c.status.value,
                tuple(c.support_event_ids),
                tuple(c.counterevidence_event_ids),
                tuple(c.unresolved_event_ids),
            )
            for c in state.candidates
        ],
        key=repr,
    )


def run_c(scenario, backend):
    rows = []
    target = target_from_mapping(scenario["target"])
    for qi, query in enumerate(scenario["queries"]):
        store = CognitionStore()
        tracker = HypothesisTracker(store)
        try:
            tracker.create_target(target)
            events = [
                event_from_mapping(x)
                for x in scenario["events"][: int(query["after_event"])]
            ]
            for ev in events:
                store.append_event(ev)
            tracker.update(
                target.target_id,
                [x.event_id for x in events],
                backend,
            )
            state = tracker.current(target.target_id)
            pred = predict_from_hypotheses(
                backend,
                query,
                target,
                state,
                referenced_evidence(store, state),
            )
            rows.append(
                {
                    "query_index": qi,
                    "prediction": pred,
                    "gold": query["gold_behavior"],
                    "correct": pred == query["gold_behavior"],
                    "state_signature": signature(state),
                    "latent_diagnostic": hidden_rank(
                        state, scenario["hidden_target"]
                    ),
                }
            )
        finally:
            store.close()
    return rows


def run_d(scenario, backend):
    rows = []
    target = target_from_mapping(scenario["target"])
    store = CognitionStore()
    tracker = HypothesisTracker(store)
    tracker.create_target(target)
    ingested = 0
    repair_count = 0
    try:
        for qi, query in enumerate(scenario["queries"]):
            target_count = int(query["after_event"])
            while ingested < target_count:
                ev = event_from_mapping(scenario["events"][ingested])
                store.append_event(ev)
                receipt = tracker.update(
                    target.target_id,
                    [ev.event_id],
                    backend,
                )
                repair_count += int(receipt.repaired)
                ingested += 1
            state = tracker.current(target.target_id)
            pred = predict_from_hypotheses(
                backend,
                query,
                target,
                state,
                referenced_evidence(store, state),
            )
            rows.append(
                {
                    "query_index": qi,
                    "prediction": pred,
                    "gold": query["gold_behavior"],
                    "correct": pred == query["gold_behavior"],
                    "state_signature": signature(state),
                    "latent_diagnostic": hidden_rank(
                        state, scenario["hidden_target"]
                    ),
                    "scenario_repairs": repair_count,
                }
            )
    finally:
        store.close()
    return rows


def run_e(scenario, backend):
    rows = []
    target = target_from_mapping(scenario["target"])
    for qi, query in enumerate(scenario["queries"]):
        events = [
            event_from_mapping(x)
            for x in scenario["events"][: int(query["after_event"])]
        ]
        pred = predict_from_history(backend, query, target, events)
        rows.append(
            {
                "query_index": qi,
                "prediction": pred,
                "gold": query["gold_behavior"],
                "correct": pred == query["gold_behavior"],
            }
        )
    return rows


def summarize(rows, backend):
    total = len(rows)
    correct = sum(1 for x in rows if x["correct"])
    latent_rows = [x for x in rows if "latent_diagnostic" in x]
    return {
        "total": total,
        "correct": correct,
        "accuracy": correct / total if total else 0.0,
        "failures": [
            {
                "scenario": x["scenario"],
                "query_index": x["query_index"],
                "prediction": x["prediction"],
                "gold": x["gold"],
            }
            for x in rows
            if not x["correct"]
        ],
        "hidden_top_or_tied": (
            sum(
                1
                for x in latent_rows
                if x["latent_diagnostic"]["hidden_top_or_tied"]
            )
            if latent_rows
            else None
        ),
        "latent_total": len(latent_rows),
        "backend": backend.metrics(),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--fixtures",
        default="eval/v04/latent_hypothesis_capability_v01.json",
    )
    parser.add_argument("--model", default="deepseek-flash")
    parser.add_argument(
        "--base-url",
        default=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
    )
    parser.add_argument(
        "--out",
        default="artifacts/hcl-v04-latent-v01/result.json",
    )
    args = parser.parse_args()

    api_key = os.environ["DEEPSEEK_API_KEY"]
    fixtures = json.loads(Path(args.fixtures).read_text(encoding="utf-8"))
    backends = {
        arm: make_backend(api_key, args.base_url, args.model)
        for arm in ("C", "D", "E")
    }
    rows = {"C": [], "D": [], "E": []}
    pairs = []

    for scenario in fixtures:
        c = run_c(scenario, backends["C"])
        d = run_d(scenario, backends["D"])
        e = run_e(scenario, backends["E"])
        for arm, arm_rows in (("C", c), ("D", d), ("E", e)):
            for row in arm_rows:
                rows[arm].append({"scenario": scenario["id"], **row})
        for c_row, d_row in zip(c, d):
            pairs.append(
                {
                    "scenario": scenario["id"],
                    "query_index": c_row["query_index"],
                    "state_equal": (
                        c_row["state_signature"] == d_row["state_signature"]
                    ),
                    "c_prediction": c_row["prediction"],
                    "d_prediction": d_row["prediction"],
                    "gold": c_row["gold"],
                }
            )

    output = {
        "format": "hcl-v04-latent-hypothesis-capability-v01",
        "model": args.model,
        "seed": 42,
        "scenario_count": len(fixtures),
        "query_count": sum(len(x["queries"]) for x in fixtures),
        "arms": {
            arm: summarize(rows[arm], backends[arm])
            for arm in ("C", "D", "E")
        },
        "c_d_state_equal": {
            "equal": sum(1 for x in pairs if x["state_equal"]),
            "total": len(pairs),
        },
        "pairs": pairs,
        "rows": rows,
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
                "C_hidden_top": output["arms"]["C"]["hidden_top_or_tied"],
                "D_hidden_top": output["arms"]["D"]["hidden_top_or_tied"],
                "c_d_state_equal": output["c_d_state_equal"],
                "artifact": str(out),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
