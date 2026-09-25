#!/usr/bin/env python3
"""Staged one-shot LongMemEval C/D/G answers; scoring is a separate process.

Provider execution is deliberately unavailable outside GitHub Actions and an
exact one-shot nonce. No workflow currently supplies that nonce.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from hcl.v05.runtime import HCLV05Runtime
from scripts.longmemeval_cdg_v01 import (
    GenericMemory,
    IngestionReceipt,
    ProtocolError,
    answer_packet,
    arm_messages,
    canonical_json,
)
from scripts.preflight_v05_longmemeval_cdg_v01 import (
    preflight_dataset,
    validate_manifest,
)
from scripts.qualify_longmemeval_knowledge_update_v01 import (
    EXPECTED_DATASET_SHA256,
    events_from_state_view,
    history_digest,
    state_input_view,
)
from scripts.run_v04_long_horizon_bounded_context_v01 import (
    event_from_mapping,
    make_real_backend,
)

RUN_ONCE_TOKEN = "HCL_V05_LONGMEMEVAL_CDG_V01_RUN_ONCE_20260925_A1"
MODEL = "deepseek-flash"
BASE_URL = "https://api.deepseek.com"
COMMON_PACKET_CHAR_LIMIT = 30000
STATE_CHAR_LIMIT = 16000


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def _state_from_d(events: list[dict[str, Any]], backend: Any) -> tuple[list[dict], dict]:
    runtime = HCLV05Runtime()
    repairs = 0
    committed = 0
    try:
        for mapping in events:
            result = runtime.ingest_event(event_from_mapping(mapping), backend)
            repairs += int(result.semantic_repair_count)
            committed += len(result.stance_events)
            if runtime.semantic_failures:
                raise ProtocolError("D semantic failure; row consumed, stop run")
        state = [x.as_dict() for x in runtime.all_current_stances()]
        if len(canonical_json(state)) > STATE_CHAR_LIMIT:
            raise ProtocolError("D current state exceeds frozen answer budget")
        return state, {"events": len(events), "semantic_failures": 0,
                       "semantic_repairs": repairs,
                       "stance_events": committed, "state_chars": len(canonical_json(state))}
    finally:
        runtime.close()


def _state_from_g(events: list[dict[str, Any]], backend: Any) -> tuple[dict, dict]:
    memory = GenericMemory(backend, state_char_limit=STATE_CHAR_LIMIT)
    for event in events:
        memory.ingest(event)
    return memory.state, {"events": memory.processed_events,
                          "compacted_updates": memory.compacted_updates,
                          "repair_calls": memory.repair_calls,
                          "state_chars": len(canonical_json(memory.state))}


def run_one(row: dict, expected_history_sha: str, backends: dict[str, Any],
            on_progress: Callable[[dict], None] | None = None) -> dict:
    view = state_input_view(row)
    if history_digest(view) != expected_history_sha:
        raise ProtocolError("selected history drift before provider execution")
    qid = str(row["question_id"])
    events = events_from_state_view(view, id_prefix=hashlib.sha256(qid.encode()).hexdigest()[:16])
    d_state, d_ingest = _state_from_d(events, backends["D"])
    g_state, g_ingest = _state_from_g(events, backends["G"])
    receipt = IngestionReceipt(expected_history_sha, d_ingest["events"],
                               g_ingest["events"], len(events))
    packet = answer_packet(row, receipt)
    common = arm_messages(packet)
    if len(common[1]["content"]) > COMMON_PACKET_CHAR_LIMIT:
        raise ProtocolError("common oracle packet exceeds frozen answer budget")
    messages = {"C": common, "D": arm_messages(packet, d_state),
                "G": arm_messages(packet, g_state)}
    if any(value[:2] != common for value in messages.values()):
        raise ProtocolError("unequal answer-time evidence")
    if any(len(value[-1]["content"]) > STATE_CHAR_LIMIT + 80 for value in
           [messages["D"], messages["G"]]):
        raise ProtocolError("derived-state answer budget exceeded")
    answers = {}
    for arm in ("C", "D", "G"):
        answers[arm] = backends[arm].complete(messages[arm], max_tokens=256, temperature=0.0)
        if on_progress is not None:
            on_progress({"question_id": qid, "packet_sha256": packet["packet_sha256"],
                         "answers": dict(answers)})
    return {"question_id": qid, "history_sha256": expected_history_sha,
            "packet_sha256": packet["packet_sha256"],
            "common_messages_sha256": hashlib.sha256(canonical_json(common).encode()).hexdigest(),
            "answers": answers, "d_ingest": d_ingest, "g_ingest": g_ingest,
            "d_state": d_state, "g_state": g_state}


def execute(dataset: Path, out: Path, selected: list[dict]) -> None:
    if os.getenv("GITHUB_ACTIONS") != "true" or os.getenv("GITHUB_RUN_ATTEMPT") != "1":
        raise ProtocolError("provider execution requires first-attempt GitHub Actions")
    if os.getenv("HCL_LONGMEMEVAL_CDG_V01_RUN_ONCE_TOKEN") != RUN_ONCE_TOKEN:
        raise ProtocolError("one-shot trigger missing")
    key = os.environ.get("DEEPSEEK_API_KEY")
    if not key:
        raise ProtocolError("DeepSeek credential missing")
    # This preflight reads history-only state views and hashes before paid calls.
    preflight_dataset(dataset, selected)
    data = json.loads(dataset.read_text(encoding="utf-8"))
    lookup = {x["question_id"]: x for x in data}
    backends = {arm: make_real_backend(key, BASE_URL, MODEL, provider_profile="deepseek_flash")
                for arm in ("C", "D", "G")}
    result = {"format": "hcl-v05-longmemeval-cdg-answers-v01",
              "status": "in_progress", "run_head": os.environ.get("GITHUB_SHA"),
              "dataset_sha256": EXPECTED_DATASET_SHA256,
              "selected_count": len(selected), "rows": [], "attempted_ids": [], "backend": {}}
    _write_json(out, result)
    try:
        for item in selected:
            qid = item["question_id"]
            result["attempted_ids"].append(qid)
            _write_json(out, result)
            def checkpoint(partial: dict) -> None:
                result["partial_row"] = partial
                _write_json(out, result)
            row_result = run_one(lookup[qid], item["history_sha256"], backends,
                                 on_progress=checkpoint)
            result["rows"].append(row_result)
            result.pop("partial_row", None)
            result["backend"] = {arm: backend.metrics() for arm, backend in backends.items()}
            _write_json(out, result)
        result["status"] = "answers_complete_unscored"
    except Exception as exc:
        result["status"] = "failed_partial_consumed"
        result["failure"] = {"type": type(exc).__name__, "message": str(exc)}
        raise
    finally:
        result["backend"] = {arm: backend.metrics() for arm, backend in backends.items()}
        _write_json(out, result)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path)
    parser.add_argument("--out", type=Path, default=Path("artifacts/longmemeval-cdg-v01/raw-answers.json"))
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    if args.validate_only == args.execute:
        parser.error("choose exactly one of --validate-only or --execute")
    _, selected = validate_manifest()
    if args.validate_only:
        if args.dataset:
            result = preflight_dataset(args.dataset, selected)
            print(json.dumps({k: v for k, v in result.items() if k != "rows"}, sort_keys=True))
        else:
            print(json.dumps({"selected_count": len(selected), "provider_calls": 0}, sort_keys=True))
        return
    if args.dataset is None:
        parser.error("--execute requires --dataset")
    execute(args.dataset, args.out, selected)


if __name__ == "__main__":
    main()
