"""Fresh routed semantic extraction v0.2 pilot for HCL v0.5."""

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
from hcl.v05.semantic import extract_routed_stance_events
from hcl.v05.stance import StanceSignal


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

    def metrics(self):
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


def self_dict(event) -> dict[str, str]:
    return {
        "issue_key": event.issue_key,
        "signal": event.signal.value,
        "value_key": event.value_key,
    }


def revision_dict(relation) -> dict[str, str]:
    return {
        "issue_key": relation.issue_key,
        "new_value_key": relation.new_value_key,
        "prior_value_key": relation.prior_value_key,
    }


def routed_dict(event) -> dict[str, str | None]:
    return {
        "subject_agent_id": event.subject_agent_id,
        "issue_key": event.issue_key,
        "signal": event.signal.value,
        "value_key": event.value_key,
        "prior_value_key": event.prior_value_key,
    }


def self_key(row: dict[str, Any]) -> tuple[str, str, str]:
    return (
        str(row["issue_key"]),
        str(row["signal"]),
        str(row["value_key"]),
    )


def revision_key(row: dict[str, Any]) -> tuple[str, str, str]:
    return (
        str(row["issue_key"]),
        str(row["new_value_key"]),
        str(row["prior_value_key"]),
    )


def validate_fixture(fixture: dict[str, Any], gold: dict[str, Any]) -> None:
    assert fixture["format"] == "hcl-v05-routed-semantic-extraction-v02-fixture"
    assert gold["format"] == "hcl-v05-routed-semantic-extraction-v02-gold"
    streams = fixture["streams"]
    assert len(streams) == 3
    assert all(len(stream["events"]) == 12 for stream in streams)

    event_map = {}
    catalog_by_event = {}
    for stream in streams:
        catalog = stream["catalog_seed"]
        assert isinstance(catalog, dict) and len(catalog) == 1
        for values in catalog.values():
            assert len(values) == 3
            assert len(values) == len(set(values))
        for event in stream["events"]:
            eid = event["event_id"]
            assert eid not in event_map
            event_map[eid] = event
            catalog_by_event[eid] = catalog

    assert len(event_map) == 36
    assert set(event_map) == set(gold["rows"])

    fixture_text = json.dumps(fixture, sort_keys=True)
    for forbidden in ('"risk_class"', '"self_stances"', '"revision_relations"'):
        assert forbidden not in fixture_text

    self_total = revision_total = 0
    for event_id, truth in gold["rows"].items():
        event = event_map[event_id]
        catalog = catalog_by_event[event_id]
        assert truth["risk_class"]

        seen_self = set()
        for row in truth["self_stances"]:
            key = self_key(row)
            assert key not in seen_self
            seen_self.add(key)
            self_total += 1
            issue, signal, value = key
            assert issue in catalog
            assert value in catalog[issue]
            assert signal in {"AFFIRM", "DENY", "UNRESOLVED"}
            assert event.get("actor_id")

        seen_revision = set()
        for row in truth["revision_relations"]:
            key = revision_key(row)
            assert key not in seen_revision
            seen_revision.add(key)
            revision_total += 1
            issue, new_value, prior_value = key
            assert issue in catalog
            assert new_value in catalog[issue]
            assert prior_value in catalog[issue]
            assert new_value != prior_value

    assert self_total == 19
    assert revision_total == 14


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


def extract_rows(fixture: dict[str, Any], backend: MeteredBackend):
    rows = []
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
            predicted_self = []
            predicted_revisions = []
            routed = []
            try:
                result = extract_routed_stance_events(
                    event_from_mapping(raw_event),
                    backend,
                    known_catalog=catalog,
                )
                predicted_self = sorted(
                    [
                        self_dict(event)
                        for event in result.stance_events
                        if event.signal != StanceSignal.REVISION_EXPOSURE
                    ],
                    key=lambda x: repr(self_key(x)),
                )
                predicted_revisions = sorted(
                    [revision_dict(item) for item in result.revision_relations],
                    key=lambda x: repr(revision_key(x)),
                )
                routed = sorted(
                    [routed_dict(event) for event in result.stance_events],
                    key=repr,
                )
                repair_count = result.repair_count
                repair_reason = result.repair_reason
            except Exception as exc:
                extraction_error = f"{type(exc).__name__}: {exc}"

            rows.append(
                {
                    "stream": stream["id"],
                    "event_id": raw_event["event_id"],
                    "predicted_self_stances": predicted_self,
                    "predicted_revision_relations": predicted_revisions,
                    "routed_stance_events": routed,
                    "repair_count": repair_count,
                    "repair_reason": repair_reason,
                    "extraction_error": extraction_error,
                    "elapsed_seconds": round(time.perf_counter() - started, 6),
                }
            )
    return rows


def score_rows(rows: list[dict[str, Any]], gold: dict[str, Any]):
    scored = []
    risk_failures = Counter()
    self_tp = self_fp = self_fn = 0
    rev_tp = rev_fp = rev_fn = 0

    for row in rows:
        truth = gold["rows"][row["event_id"]]
        gold_self = {self_key(x) for x in truth["self_stances"]}
        pred_self = {self_key(x) for x in row["predicted_self_stances"]}
        gold_rev = {revision_key(x) for x in truth["revision_relations"]}
        pred_rev = {revision_key(x) for x in row["predicted_revision_relations"]}

        missing_self = sorted(gold_self - pred_self, key=repr)
        extra_self = sorted(pred_self - gold_self, key=repr)
        missing_rev = sorted(gold_rev - pred_rev, key=repr)
        extra_rev = sorted(pred_rev - gold_rev, key=repr)

        self_tp += len(gold_self & pred_self)
        self_fp += len(extra_self)
        self_fn += len(missing_self)
        rev_tp += len(gold_rev & pred_rev)
        rev_fp += len(extra_rev)
        rev_fn += len(missing_rev)

        exact = (
            not missing_self
            and not extra_self
            and not missing_rev
            and not extra_rev
            and row["extraction_error"] is None
        )
        if not exact:
            risk_failures[truth["risk_class"]] += 1

        scored.append(
            {
                **row,
                "expected_self_stances": sorted(
                    truth["self_stances"], key=lambda x: repr(self_key(x))
                ),
                "expected_revision_relations": sorted(
                    truth["revision_relations"],
                    key=lambda x: repr(revision_key(x)),
                ),
                "risk_class": truth["risk_class"],
                "exact": exact,
                "missing_self": [list(x) for x in missing_self],
                "extra_self": [list(x) for x in extra_self],
                "missing_revision": [list(x) for x in missing_rev],
                "extra_revision": [list(x) for x in extra_rev],
            }
        )

    def ratio(tp, fp_or_fn, kind):
        denom = tp + fp_or_fn
        if not denom:
            return 1.0
        return tp / denom

    return {
        "exact_events": sum(1 for row in scored if row["exact"]),
        "total_events": len(scored),
        "self_tp": self_tp,
        "self_fp": self_fp,
        "self_fn": self_fn,
        "self_precision": ratio(self_tp, self_fp, "precision"),
        "self_recall": ratio(self_tp, self_fn, "recall"),
        "revision_tp": rev_tp,
        "revision_fp": rev_fp,
        "revision_fn": rev_fn,
        "revision_precision": ratio(rev_tp, rev_fp, "precision"),
        "revision_recall": ratio(rev_tp, rev_fn, "recall"),
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
        default="eval/v05/routed_semantic_extraction_v02_fixture.json",
    )
    parser.add_argument(
        "--gold",
        default="eval/v05/routed_semantic_extraction_v02_gold.json",
    )
    parser.add_argument("--model", default="deepseek-flash")
    parser.add_argument(
        "--base-url",
        default=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
    )
    parser.add_argument(
        "--out",
        default="artifacts/hcl-v05-routed-semantic-extraction-v02/result.json",
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
                    "events": sum(len(s["events"]) for s in fixture["streams"]),
                    "self_gold": sum(
                        len(row["self_stances"]) for row in gold["rows"].values()
                    ),
                    "revision_gold": sum(
                        len(row["revision_relations"])
                        for row in gold["rows"].values()
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
        "format": "hcl-v05-routed-semantic-extraction-v02",
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
                "self_tp": output["self_tp"],
                "self_fp": output["self_fp"],
                "self_fn": output["self_fn"],
                "revision_tp": output["revision_tp"],
                "revision_fp": output["revision_fp"],
                "revision_fn": output["revision_fn"],
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
