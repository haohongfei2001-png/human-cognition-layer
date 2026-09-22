#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from hcl.v03.answer_loop import HCLAnswerLoop, extract_json
from hcl.v03.backends import OpenAICompatibleBackend
from scripts.run_state_generation_reliability_audit_v01 import render_case

BASE_URL = "https://api.deepseek.com"
MODEL = "deepseek-flash"
SEED = 42
STATE_MAX_TOKENS = 8192
FIXTURES = ROOT / "eval/answer_loop/state_generation_reliability_v01.json"
KNOWN_STATE_EXHAUSTION = "HCL state builder returned no valid JSON after 3 attempts"


class ObservingRepairBackend:
    def __init__(self, inner: Any) -> None:
        self.inner = inner
        self.attempts: list[dict[str, Any]] = []

    def _record_success(self, text: str, *, structured: bool) -> str:
        encoded = text.encode("utf-8")
        self.attempts.append({
            "attempt": len(self.attempts) + 1,
            "structured_mode": structured,
            "response_bytes": len(encoded),
            "response_sha256": hashlib.sha256(encoded).hexdigest(),
            "empty": not bool(text.strip()),
            "json_object_parseable": extract_json(text) is not None,
        })
        return text

    def _record_exception(self, exc: Exception, *, structured: bool) -> None:
        self.attempts.append({
            "attempt": len(self.attempts) + 1,
            "structured_mode": structured,
            "backend_exception_type": type(exc).__name__,
        })

    def complete_json(
        self,
        messages: list[dict[str, str]],
        *,
        max_tokens: int,
        temperature: float = 0.0,
    ) -> str:
        try:
            text = self.inner.complete_json(
                messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )
        except Exception as exc:
            self._record_exception(exc, structured=True)
            raise
        return self._record_success(text, structured=True)

    def complete(
        self,
        messages: list[dict[str, str]],
        *,
        max_tokens: int,
        temperature: float = 0.0,
    ) -> str:
        try:
            text = self.inner.complete(
                messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )
        except Exception as exc:
            self._record_exception(exc, structured=False)
            raise
        return self._record_success(text, structured=False)


def run_case(case: dict[str, Any], api_key: str) -> dict[str, Any]:
    user_input = render_case(case)
    backend = ObservingRepairBackend(
        OpenAICompatibleBackend(
            api_key=api_key,
            base_url=BASE_URL,
            model=MODEL,
            seed=SEED,
        )
    )
    loop = HCLAnswerLoop(backend, state_max_tokens=STATE_MAX_TOKENS)

    failure_class = None
    backend_exception_type = None
    success = False
    try:
        loop.build_state(user_input)
        success = True
    except Exception as exc:
        if isinstance(exc, RuntimeError) and str(exc) == KNOWN_STATE_EXHAUSTION:
            failure_class = "state_json_exhaustion"
        else:
            failure_class = "backend_or_other_exception"
            backend_exception_type = type(exc).__name__

    encoded_input = user_input.encode("utf-8")
    return {
        "id": case["id"],
        "length_band": case["length_band"],
        "complexity": case["complexity"],
        "event_count": case["event_count"],
        "agent_count": case["agent_count"],
        "nested_claims": case["nested_claims"],
        "variant": case["variant"],
        "input_bytes": len(encoded_input),
        "input_sha256": hashlib.sha256(encoded_input).hexdigest(),
        "attempt_count": len(backend.attempts),
        "success": success,
        "failure_class": failure_class,
        "backend_exception_type": backend_exception_type,
        "attempts": backend.attempts,
    }


def assert_content_free(rows: list[dict[str, Any]]) -> None:
    raw = json.dumps(rows, ensure_ascii=False).lower()
    for key in (
        '"input":',
        '"prompt":',
        '"messages":',
        '"response":',
        '"response_text":',
        '"state":',
        '"normalized_state":',
        '"api_key":',
        '"exception_text":',
    ):
        if key in raw:
            raise RuntimeError(f"content-free artifact boundary violated: {key}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--shard-index", type=int, required=True)
    parser.add_argument("--shard-count", type=int, default=6)
    parser.add_argument(
        "--out",
        type=Path,
        default=ROOT / "artifacts/hcl-state-json-repair-v02",
    )
    args = parser.parse_args()

    if args.shard_count != 6 or not 0 <= args.shard_index < args.shard_count:
        raise RuntimeError("repair validation requires exactly 6 shards")

    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise RuntimeError("DEEPSEEK_API_KEY is required")

    suite = json.loads(FIXTURES.read_text(encoding="utf-8"))
    cases = suite["cases"]
    if len(cases) != 24:
        raise RuntimeError("expected 24 frozen reliability cases")

    start = args.shard_index * 4
    selected = cases[start : start + 4]
    if len(selected) != 4:
        raise RuntimeError("unexpected repair-v0.2 validation shard shape")
    if len({(x["length_band"], x["complexity"]) for x in selected}) != 1:
        raise RuntimeError("each shard must contain exactly one frozen stratum")

    results: list[dict[str, Any]] = []
    for case in selected:
        result = run_case(case, api_key)
        results.append(result)
        print(
            f"{case['id']}: success={result['success']} "
            f"attempts={result['attempt_count']} "
            f"failure_class={result['failure_class']}",
            flush=True,
        )

    assert_content_free(results)
    args.out.mkdir(parents=True, exist_ok=True)
    payload = {
        "shard_index": args.shard_index,
        "shard_count": args.shard_count,
        "requested": 4,
        "completed": len(results),
        "results": results,
    }
    (args.out / f"shard_{args.shard_index}.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
