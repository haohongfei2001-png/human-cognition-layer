"""Frozen event-local semantic extraction pilot for HCL v0.5."""

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

from hcl.v04.model import EventRecord
from hcl.v05.semantic import SemanticExtractionError, extract_stance_events


class MeteredBackend:
    def __init__(self, backend: Any):
        self.backend = backend
        self.calls = 0
        self.input_chars = 0
        self.output_chars = 0
        self.provider_wall_seconds = 0.0

    def complete_json(self, messages, *, max_tokens, temperature=0.0):
        self.calls += 1
        self.input_chars += sum(len(str(m.get("content", ""))) for m in messages)
        started = time.perf_counter()
        try:
            out = self.backend.complete_json(
                messages, max_tokens=max_tokens, temperature=temperature
            )
        finally:
            self.provider_wall_seconds += time.perf_counter() - started
        self.output_chars += len(out)
        return out

    def metrics(self) -> dict[str, int | float]:
        return {
            "calls": self.calls,
            "input_chars": self.input_chars,
            "output_chars": self.output_chars,
            "provider_wall_seconds": round(self.provider_wall_seconds, 6),
        }


def make_backend(api_key: str, base_url: str, model: str) -> MeteredBackend:
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
        metadata=dict(raw.get("metadata") or {}),
    )


def signal_dict(event) -> dict[str, Any]:
    return {
        "subject_agent_id": event.subject_agent_id,
        "issue_key": event.issue_key,
        "signal": event.signal.value,
        "value_key": event.value_key,
        "prior_value_key": event.prior_value_key,
    }


def signal_key(raw: dict[str, Any]) -> tuple[str, str, str, str, str | None]:
    return (
        str(raw["subject_agent_id"]),
        str(raw["issue_key"]),
        str(raw["signal"]),
        str(raw["value_key"]),
        (
            None
            if raw.get("prior_value_key") is None
            else str(raw.get("prior_value_key"))
        ),
    )


def _event_accessible(raw: dict[str, Any], subject: str) -> bool:
    return bool(
        (raw.get("metadata") or {}).get("public")
        or raw.get("actor_id") == subject
        or subject in (raw.get("observer_ids") or [])
        or subject in (raw.get("recipient_ids") or [])
    )


def validate_fixture(fixture: dict[str, Any], gold: dict[str, Any]) -> None:
    assert fixture["format"] == "hcl-v05-semantic-extraction-v01-fixture"
    assert gold["format"] == "hcl-v05-semantic-extraction-v01-gold"
    streams = fixture["streams"]
    assert len(streams) == 3
    assert all(len(stream["events"]) == 12 for stream in streams)

    event_map: dict[str, dict[str, Any]] = {}
    event_to_catalog: dict[str, dict[str, list[str]]] = {}
    for stream in streams:
        catalog = stream["catalog_seed"]
        assert isinstance(catalog, dict) and len(catalog) == 1
        for values in catalog.values():
            assert len(values) == 3
            assert len(values) == len(set(values))
        for event in stream["events"]:
            eid = event["event_id"]
            assert eid not in event_map
            assert event["raw_text"].strip()
            event_map[eid] = event
            event_to_catalog[eid] = catalog

    assert len(event_map) == 36
    assert set(event_map) == set(gold["rows"])

    fixture_text = json.dumps(fixture, sort_keys=True)
    assert '"risk_class"' not in fixture_text
    assert '"signals"' not in fixture_text

    total_signals = 0
    for event_id, truth in gold["rows"].items():
        event = event_map[event_id]
        catalog = event_to_catalog[event_id]
        assert truth["risk_class"]
        seen = set()
        for signal in truth["signals"]:
            key = signal_key(signal)
            assert key not in seen
            seen.add(key)
            total_signals += 1
            subject, issue, signal_type, value, prior = key
            assert issue in catalog
            assert value in catalog[issue]
            if prior is not None:
                assert prior in catalog[issue]
            if signal_type in {"AFFIRM", "DENY", "UNRESOLVED"}:
                assert subject == event.get("actor_id")
                assert prior is None
            elif signal_type == "REVISION_EXPOSURE":
                assert prior is not None and prior != value
                assert _event_accessible(event, subject)
            else:
                raise AssertionError(f"unknown signal type {signal_type}")

    assert total_signals == 36

    forbidden = {
        "briefing room",
        "budget cap",
        "shipping dock",
        "lin",
        "maya",
        "nora",
    }
    lowered = fixture_text.lower()
    assert not any(item in lowered for item in forbidden)


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


def extract_rows(
    fixture: dict[str, Any],
    backend: MeteredBackend,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for stream in fixture["streams"]:
        catalog = {
            str(issue): [str(value) for value in values]
            for issue, values in stream["catalog_seed"].items()
        }
        for raw_event in stream["events"]:
            started = time.perf_counter()
            extraction_error = None
            repair_count = 0
            repair_reason = None
            predicted: list[dict[str, Any]] = []
            try:
                result = extract_stance_events(
                    event_from_mapping(raw_event),
                    backend,
                    known_catalog=catalog,
                )
                predicted = [signal_dict(event) for event in result.stance_events]
                repair_count = result.repair_count
                repair_reason = result.repair_reason
            except SemanticExtractionError as exc:
                extraction_error = str(exc)
            rows.append(
                {
                    "stream": stream["id"],
                    "event_id": raw_event["event_id"],
                    "prediction": sorted(predicted, key=lambda x: repr(signal_key(x))),
                    "repair_count": repair_count,
                    "repair_reason": repair_reason,
                    "extraction_error": extraction_error,
                    "elapsed_seconds": round(time.perf_counter() - started, 6),
                }
            )
    return rows


def score_rows(rows: list[dict[str, Any]], gold: dict[str, Any]) -> dict[str, Any]:
    scored: list[dict[str, Any]] = []
    risk_failures = Counter()
    tp = fp = fn = 0
    for row in rows:
        truth = gold["rows"][row["event_id"]]
        expected = sorted(truth["signals"], key=lambda x: repr(signal_key(x)))
        pred_set = {signal_key(item) for item in row["prediction"]}
        gold_set = {signal_key(item) for item in expected}
        missing = sorted(gold_set - pred_set, key=repr)
        extra = sorted(pred_set - gold_set, key=repr)
        exact = not missing and not extra and row["extraction_error"] is None
        tp += len(pred_set & gold_set)
        fp += len(extra)
        fn += len(missing)
        if not exact:
            risk_failures[truth["risk_class"]] += 1
        scored.append(
            {
                **row,
                "expected": expected,
                "risk_class": truth["risk_class"],
                "exact": exact,
                "missing": [list(item) for item in missing],
                "extra": [list(item) for item in extra],
            }
        )

    precision = tp / (tp + fp) if tp + fp else 1.0
    recall = tp / (tp + fn) if tp + fn else 1.0
    return {
        "exact_events": sum(1 for row in scored if row["exact"]),
        "total_events": len(scored),
        "signal_tp": tp,
        "signal_fp": fp,
        "signal_fn": fn,
        "signal_precision": precision,
        "signal_recall": recall,
        "events_with_repair": sum(1 for row in scored if row["repair_count"]),
        "events_with_extraction_error": sum(
            1 for row in scored if row["extraction_error"] is not None
        ),
        "failure_risk_classes": dict(sorted(risk_failures.items())),
        "rows": scored,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--fixtures",
        default="eval/v05/semantic_extraction_v01_fixture.json",
    )
    parser.add_argument(
        "--gold",
        default="eval/v05/semantic_extraction_v01_gold.json",
    )
    parser.add_argument("--model", default="deepseek-flash")
    parser.add_argument(
        "--base-url",
        default=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
    )
    parser.add_argument(
        "--out",
        default="artifacts/hcl-v05-semantic-extraction-v01/result.json",
    )
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()

    fixture, gold, fixture_sha, gold_sha = load_and_validate(
        args.fixtures, args.gold
    )
    if args.validate_only:
        print(
            json.dumps(
                {
                    "streams": len(fixture["streams"]),
                    "events": sum(len(x["events"]) for x in fixture["streams"]),
                    "gold_signals": sum(
                        len(row["signals"]) for row in gold["rows"].values()
                    ),
                    "fixture_sha256": fixture_sha,
                    "gold_sha256": gold_sha,
                },
                sort_keys=True,
            )
        )
        return

    backend = make_backend(
        os.environ["DEEPSEEK_API_KEY"],
        args.base_url,
        args.model,
    )
    rows = extract_rows(fixture, backend)
    scored = score_rows(rows, gold)
    output = {
        "format": "hcl-v05-semantic-extraction-v01",
        "model": args.model,
        "seed": 42,
        "fixture_sha256": fixture_sha,
        "gold_sha256": gold_sha,
        "backend": backend.metrics(),
        **scored,
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
                "exact_events": output["exact_events"],
                "total_events": output["total_events"],
                "signal_tp": output["signal_tp"],
                "signal_fp": output["signal_fp"],
                "signal_fn": output["signal_fn"],
                "events_with_repair": output["events_with_repair"],
                "events_with_extraction_error": output[
                    "events_with_extraction_error"
                ],
                "backend": output["backend"],
                "artifact": str(out),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
