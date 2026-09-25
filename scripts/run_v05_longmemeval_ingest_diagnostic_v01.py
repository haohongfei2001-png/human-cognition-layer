#!/usr/bin/env python3
"""Provider-backed, non-scored LongMemEval ingest compatibility diagnostic."""

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
from scripts.qualify_longmemeval_knowledge_update_v01 import (
    EXPECTED_DATASET_SHA256,
    assert_state_firewall,
    events_from_state_view,
    history_digest,
    sha256_file,
    state_input_view,
)
from scripts.run_v04_long_horizon_bounded_context_v01 import (
    event_from_mapping,
    make_real_backend,
)

SELECTION = REPO_ROOT / "eval/longmemeval/knowledge_update_ingest_diagnostic_v01.json"
MODEL = "deepseek-flash"
BASE_URL = "https://api.deepseek.com"


class DiagnosticError(ValueError):
    pass


def load_rows(dataset: Path) -> dict[str, dict[str, Any]]:
    if sha256_file(dataset) != EXPECTED_DATASET_SHA256:
        raise DiagnosticError("pinned LongMemEval dataset SHA mismatch")
    data = json.loads(dataset.read_text(encoding="utf-8"))
    out = {}
    for row in data:
        qid = str(row.get("question_id", "")).strip()
        if qid:
            out[qid] = row
    return out


def diagnose_one(
    *,
    qid: str,
    row: dict[str, Any],
    expected_history_sha: str,
    backend: Any,
) -> dict[str, Any]:
    if row.get("question_type") != "knowledge-update":
        raise DiagnosticError(f"{qid}: not knowledge-update")
    view = state_input_view(row)
    assert_state_firewall(row, view)
    observed_history_sha = history_digest(view)
    if observed_history_sha != expected_history_sha:
        raise DiagnosticError(
            f"{qid}: history SHA drift {observed_history_sha} != {expected_history_sha}"
        )

    events = events_from_state_view(view, id_prefix=hashlib.sha256(qid.encode()).hexdigest()[:16])
    runtime = HCLV05Runtime()
    failures = Counter()
    repairs = 0
    committed_stance_events = 0
    signals = Counter()
    started = time.perf_counter()

    for mapping in events:
        event = event_from_mapping(mapping)
        try:
            result = runtime.ingest_event(event, backend)
        except Exception as exc:
            failures[type(exc).__name__] += 1
            continue
        repairs += int(result.semantic_repair_count)
        committed_stance_events += len(result.stance_events)
        signals.update(x.signal.value for x in result.stance_events)

    elapsed = time.perf_counter() - started
    current = runtime.all_current_stances()
    statuses = Counter(x.status.value for x in current)
    catalog = runtime.semantic_catalog()
    state_chars = len(
        json.dumps(
            [x.as_dict() for x in current],
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    semantic_failures = len(runtime.semantic_failures)
    runtime.close()

    return {
        "question_id": qid,
        "history_sha256": observed_history_sha,
        "session_count": len(view["history"]),
        "event_count": len(events),
        "successful_event_ingests": len(events) - semantic_failures,
        "semantic_failure_count": semantic_failures,
        "semantic_failure_types": dict(sorted(failures.items())),
        "semantic_repair_count": repairs,
        "stance_events_committed": committed_stance_events,
        "stance_signal_counts": dict(sorted(signals.items())),
        "current_stance_count": len(current),
        "current_stance_status_counts": dict(sorted(statuses.items())),
        "semantic_catalog_issue_count": len(catalog),
        "semantic_catalog_value_count": sum(len(v) for v in catalog.values()),
        "current_state_chars": state_chars,
        "arm_wall_seconds": round(elapsed, 6),
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--dataset", type=Path, required=True)
    p.add_argument(
        "--selection",
        type=Path,
        default=SELECTION,
    )
    p.add_argument(
        "--out",
        type=Path,
        default=Path("artifacts/longmemeval-ingest-diagnostic-v01/result.json"),
    )
    p.add_argument("--validate-only", action="store_true")
    args = p.parse_args()

    selection = json.loads(args.selection.read_text(encoding="utf-8"))
    if selection["format"] != "hcl-v05-longmemeval-ingest-diagnostic-selection-v01":
        raise DiagnosticError("unexpected diagnostic selection format")
    if len(selection["selected"]) != 2:
        raise DiagnosticError("diagnostic selection must contain exactly two rows")

    sealed = json.loads(
        (REPO_ROOT / "eval/longmemeval/knowledge_update_selection_v01.json").read_text(
            encoding="utf-8"
        )
    )
    sealed_ids = {x["question_id"] for x in sealed["selected"]}
    diag_ids = {x["question_id"] for x in selection["selected"]}
    if sealed_ids & diag_ids:
        raise DiagnosticError("diagnostic rows overlap sealed efficacy rows")

    if args.validate_only:
        print(
            json.dumps(
                {
                    "selected_count": len(selection["selected"]),
                    "diagnostic_ids": sorted(diag_ids),
                    "sealed_overlap": 0,
                    "dataset_sha256": selection["dataset_sha256"],
                },
                sort_keys=True,
            )
        )
        return

    rows = load_rows(args.dataset)
    key = os.environ["DEEPSEEK_API_KEY"]
    backend = make_real_backend(
        key,
        BASE_URL,
        MODEL,
        provider_profile="deepseek_flash",
    )

    results = []
    for selected in selection["selected"]:
        qid = selected["question_id"]
        if qid not in rows:
            raise DiagnosticError(f"selected row missing: {qid}")
        results.append(
            diagnose_one(
                qid=qid,
                row=rows[qid],
                expected_history_sha=selected["history_sha256"],
                backend=backend,
            )
        )

    total_events = sum(x["event_count"] for x in results)
    total_failures = sum(x["semantic_failure_count"] for x in results)
    total_repairs = sum(x["semantic_repair_count"] for x in results)
    total_stances = sum(x["stance_events_committed"] for x in results)

    output = {
        "format": "hcl-v05-longmemeval-ingest-diagnostic-v01",
        "claim_boundary": (
            "External ingest compatibility diagnostic only: no task question, "
            "answer, answer_session_ids, has_answer label, task prediction or "
            "task score was used."
        ),
        "provider": {
            "model": MODEL,
            "base_url": BASE_URL,
            "profile": "deepseek_flash",
            "seed": 42,
            "temperature": 0.0,
        },
        "dataset_sha256": EXPECTED_DATASET_SHA256,
        "selected_count": len(results),
        "total_events": total_events,
        "total_semantic_failures": total_failures,
        "semantic_failure_rate": (
            total_failures / total_events if total_events else 0.0
        ),
        "total_semantic_repairs": total_repairs,
        "semantic_repair_rate": (
            total_repairs / total_events if total_events else 0.0
        ),
        "total_stance_events_committed": total_stances,
        "rows": results,
        "backend": backend.metrics(),
        "pre_registered_compatibility_gate": {
            "all_rows_completed": len(results) == 2,
            "semantic_failure_rate_lte_1pct": (
                (total_failures / total_events) <= 0.01 if total_events else False
            ),
            "semantic_repair_rate_lte_5pct": (
                (total_repairs / total_events) <= 0.05 if total_events else False
            ),
            "nonzero_stance_events": total_stances > 0,
        },
    }
    gate = output["pre_registered_compatibility_gate"]
    output["compatibility_pass"] = all(gate.values())

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "compatibility_pass": output["compatibility_pass"],
                "selected_count": output["selected_count"],
                "total_events": total_events,
                "semantic_failures": total_failures,
                "semantic_repairs": total_repairs,
                "stance_events": total_stances,
                "backend": output["backend"],
                "artifact": str(args.out),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
