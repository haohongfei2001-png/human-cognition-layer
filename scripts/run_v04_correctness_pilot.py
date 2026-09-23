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
from hcl.v04.model import EventRecord
from hcl.v04.runtime import HCLV04Runtime
from hcl.v04.store import CognitionStore


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


def patch_payload(patch) -> dict:
    propositions = []
    for p in patch.propositions:
        propositions.append(asdict(p))
    assertions = []
    for a in patch.assertions:
        item = asdict(a)
        item["assertion_type"] = a.assertion_type.value
        item["status"] = a.status.value
        item["support_level"] = a.support_level.value if a.support_level else None
        assertions.append(item)
    return {
        "patch_id": patch.patch_id,
        "event_id": patch.event_id,
        "semantic_version": patch.semantic_version,
        "propositions": propositions,
        "assertions": assertions,
    }


def run_check(view: dict, check: dict) -> tuple[bool, str]:
    rows = view["relevant_assertions"]
    kind = check["kind"]

    if kind == "require_type":
        ok = any(x["assertion_type"] == check["assertion_type"] for x in rows)
        return ok, f"require_type {check['assertion_type']}"

    if kind == "forbid_type":
        ok = not any(x["assertion_type"] == check["assertion_type"] for x in rows)
        return ok, f"forbid_type {check['assertion_type']}"

    if kind == "require_type_subject":
        ok = any(
            x["assertion_type"] == check["assertion_type"]
            and x["subject_agent_id"] == check["subject_agent_id"]
            for x in rows
        )
        return ok, (
            f"require_type_subject {check['assertion_type']} "
            f"{check['subject_agent_id']}"
        )

    if kind == "forbid_type_subject":
        ok = not any(
            x["assertion_type"] == check["assertion_type"]
            and x["subject_agent_id"] == check["subject_agent_id"]
            for x in rows
        )
        return ok, (
            f"forbid_type_subject {check['assertion_type']} "
            f"{check['subject_agent_id']}"
        )

    if kind == "require_count_at_least":
        count = sum(
            1 for x in rows if x["assertion_type"] == check["assertion_type"]
        )
        ok = count >= int(check["count"])
        return ok, (
            f"require_count_at_least {check['assertion_type']} "
            f"{check['count']} actual={count}"
        )

    evidence_ids = {x["event_id"] for x in view["evidence"]}
    if kind == "forbid_event_visible":
        ok = check["event_id"] not in evidence_ids
        return ok, f"forbid_event_visible {check['event_id']}"

    if kind == "require_event_visible":
        ok = check["event_id"] in evidence_ids
        return ok, f"require_event_visible {check['event_id']}"

    raise ValueError(f"unknown check kind: {kind}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--fixtures",
        default="eval/v04/correctness_pilot_v01.json",
    )
    parser.add_argument("--model", default="deepseek-flash")
    parser.add_argument("--base-url", default=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"))
    parser.add_argument(
        "--out",
        default="artifacts/hcl-v04-correctness-pilot/result.json",
    )
    args = parser.parse_args()

    api_key = os.environ["DEEPSEEK_API_KEY"]
    backend = OpenAICompatibleBackend(
        api_key=api_key,
        base_url=args.base_url,
        model=args.model,
        seed=42,
        capabilities=DEEPSEEK_FLASH_CAPABILITIES,
    )

    fixtures = json.loads(Path(args.fixtures).read_text(encoding="utf-8"))
    results = []
    hard_failures = []

    for fixture in fixtures:
        runtime = HCLV04Runtime(CognitionStore())
        patches = []
        try:
            for raw_event in fixture["events"]:
                event = event_from_mapping(raw_event)
                runtime.append_event(event)
                patch = runtime.propose_patch(event.event_id, backend)
                runtime.apply_patch(runtime.store.state_version, patch)
                patches.append(patch_payload(patch))

            query_results = []
            for q_index, query in enumerate(fixture.get("queries", [])):
                view = runtime.build_view(
                    query.get("viewer"),
                    query.get("event_time"),
                    query.get("knowledge_cutoff"),
                    query["query"],
                ).as_dict()
                checks = []
                for check in query.get("checks", []):
                    ok, detail = run_check(view, check)
                    checks.append({"ok": ok, "detail": detail, "spec": check})
                    if not ok:
                        hard_failures.append(
                            {
                                "fixture": fixture["id"],
                                "query_index": q_index,
                                "detail": detail,
                            }
                        )
                query_results.append(
                    {
                        "query": query,
                        "view": view,
                        "checks": checks,
                    }
                )

            results.append(
                {
                    "id": fixture["id"],
                    "manual_review": fixture["manual_review"],
                    "events": fixture["events"],
                    "patches": patches,
                    "queries": query_results,
                    "state_version": runtime.store.state_version,
                    "checksum": runtime.store.deterministic_checksum(),
                }
            )
        except Exception as exc:
            hard_failures.append(
                {
                    "fixture": fixture["id"],
                    "query_index": None,
                    "detail": f"{type(exc).__name__}: {exc}",
                }
            )
            results.append(
                {
                    "id": fixture["id"],
                    "manual_review": fixture["manual_review"],
                    "events": fixture["events"],
                    "patches": patches,
                    "queries": [],
                    "state_version": runtime.store.state_version,
                    "checksum": runtime.store.deterministic_checksum(),
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                }
            )
        finally:
            runtime.store.close()

    output = {
        "format": "hcl-v04-correctness-pilot-v01",
        "model": args.model,
        "seed": 42,
        "fixture_count": len(fixtures),
        "hard_check_failures": hard_failures,
        "hard_check_pass": not hard_failures,
        "results": results,
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
                "fixture_count": len(fixtures),
                "hard_check_pass": not hard_failures,
                "hard_check_failure_count": len(hard_failures),
                "artifact": str(out),
            },
            sort_keys=True,
        )
    )
    if hard_failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
