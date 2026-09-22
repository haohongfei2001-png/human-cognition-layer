#!/usr/bin/env python3
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

from openai import OpenAI

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from hcl.v03.answer_loop import STATE_SYSTEM, extract_json
from scripts.run_state_generation_reliability_audit_v01 import render_case

BASE_URL = "https://api.deepseek.com"
MODEL = "deepseek-flash"
SEED = 42
TEMPERATURE = 0.0
STATE_MAX_TOKENS = 8192
BACKEND_EMPTY_RETRIES = 4
HCL_STATE_RETRIES = 3
FIXTURES = ROOT / "eval/answer_loop/state_generation_reliability_v01.json"

STATE_ONLY_SUFFIX = "\n\n只生成 HCL 中间状态，不要回答最终问题。"
RETRY_SUFFIX = (
    "\n\n前一次输出不是可解析的 JSON。"
    "这次必须只输出一个完整 JSON 对象，不要使用 Markdown、代码块或额外文字。"
)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def json_top_level_type(value: Any) -> str:
    if isinstance(value, dict):
        return "object"
    if isinstance(value, list):
        return "array"
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, str):
        return "string"
    if isinstance(value, (int, float)):
        return "number"
    return type(value).__name__


def usage_field(usage: Any, name: str) -> int | None:
    if usage is None:
        return None
    value = getattr(usage, name, None)
    return int(value) if isinstance(value, int) else None


def classify_call(meta: dict[str, Any]) -> str:
    if meta.get("provider_exception_type"):
        return "provider_exception"

    finish = meta.get("finish_reason")
    if meta["empty_after_strip"]:
        if finish == "length":
            return "empty_length"
        if finish == "stop":
            return "empty_stop"
        return "empty_other_finish"

    if meta["full_json_syntax_valid"]:
        if meta["json_top_level_type"] == "object":
            return "valid_json_object"
        return "valid_json_nonobject"

    if meta["hcl_object_parseable"]:
        return "embedded_object_recoverable"

    if finish == "length":
        return "nonparseable_length"
    if finish == "stop":
        return "nonparseable_stop"
    return "nonparseable_other_finish"


def observe_response(response: Any, *, hcl_attempt: int, provider_call: int, duration_ms: int) -> dict[str, Any]:
    choice = response.choices[0]
    content = choice.message.content
    text = content or ""
    raw = text.encode("utf-8")
    stripped_text = text.strip()
    stripped = stripped_text.encode("utf-8")

    syntax_valid = False
    top_type = None
    if stripped_text:
        try:
            parsed = json.loads(stripped_text)
            syntax_valid = True
            top_type = json_top_level_type(parsed)
        except Exception:
            pass

    meta = {
        "hcl_attempt": hcl_attempt,
        "provider_call": provider_call,
        "duration_ms": duration_ms,
        "finish_reason": getattr(choice, "finish_reason", None),
        "content_is_none": content is None,
        "response_bytes": len(raw),
        "stripped_response_bytes": len(stripped),
        "response_sha256": sha256_bytes(raw),
        "empty_after_strip": len(stripped) == 0,
        "full_json_syntax_valid": syntax_valid,
        "json_top_level_type": top_type,
        "hcl_object_parseable": extract_json(text) is not None,
        "starts_with_object_brace": stripped_text.startswith("{"),
        "ends_with_object_brace": stripped_text.endswith("}"),
        "contains_code_fence": (chr(96) * 3) in text or "~~~" in text,
        "prompt_tokens": usage_field(getattr(response, "usage", None), "prompt_tokens"),
        "completion_tokens": usage_field(getattr(response, "usage", None), "completion_tokens"),
        "total_tokens": usage_field(getattr(response, "usage", None), "total_tokens"),
    }
    meta["category"] = classify_call(meta)
    return meta


def run_provider_attempt(
    client: OpenAI,
    messages: list[dict[str, str]],
    *,
    hcl_attempt: int,
) -> tuple[str, list[dict[str, Any]]]:
    observations: list[dict[str, Any]] = []
    last = ""
    for provider_call in range(1, BACKEND_EMPTY_RETRIES + 1):
        started = time.monotonic()
        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=messages,
                temperature=TEMPERATURE,
                max_tokens=STATE_MAX_TOKENS,
                seed=SEED,
                response_format={"type": "json_object"},
            )
        except Exception as exc:
            duration_ms = int((time.monotonic() - started) * 1000)
            meta = {
                "hcl_attempt": hcl_attempt,
                "provider_call": provider_call,
                "duration_ms": duration_ms,
                "provider_exception_type": type(exc).__name__,
            }
            meta["category"] = classify_call(meta)
            observations.append(meta)
            raise

        duration_ms = int((time.monotonic() - started) * 1000)
        meta = observe_response(
            response,
            hcl_attempt=hcl_attempt,
            provider_call=provider_call,
            duration_ms=duration_ms,
        )
        observations.append(meta)
        last = response.choices[0].message.content or ""
        if last.strip():
            return last, observations
    return last, observations


def run_case(case: dict[str, Any], api_key: str) -> dict[str, Any]:
    user_input = render_case(case)
    client = OpenAI(api_key=api_key, base_url=BASE_URL)
    base_user = user_input + STATE_ONLY_SUFFIX
    all_calls: list[dict[str, Any]] = []
    success = False
    failure_class = None
    provider_exception_type = None
    hcl_attempts_used = 0

    for attempt in range(1, HCL_STATE_RETRIES + 1):
        hcl_attempts_used = attempt
        suffix = RETRY_SUFFIX if attempt > 1 else ""
        messages = [
            {"role": "system", "content": STATE_SYSTEM},
            {"role": "user", "content": base_user + suffix},
        ]
        try:
            text, calls = run_provider_attempt(
                client,
                messages,
                hcl_attempt=attempt,
            )
            all_calls.extend(calls)
        except Exception as exc:
            failure_class = "provider_exception"
            provider_exception_type = type(exc).__name__
            break

        if extract_json(text) is not None:
            success = True
            break

    if not success and failure_class is None:
        failure_class = "state_json_exhaustion"

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
        "input_sha256": sha256_bytes(encoded_input),
        "success": success,
        "failure_class": failure_class,
        "provider_exception_type": provider_exception_type,
        "hcl_attempts_used": hcl_attempts_used,
        "provider_call_count": len(all_calls),
        "provider_calls": all_calls,
    }


def assert_content_free(payload: Any) -> None:
    raw = json.dumps(payload, ensure_ascii=False).lower()
    forbidden = (
        '"input":',
        '"prompt":',
        '"messages":',
        '"response":',
        '"response_text":',
        '"state":',
        '"parsed_json":',
        '"api_key":',
        '"exception_text":',
    )
    for key in forbidden:
        if key in raw:
            raise RuntimeError(f"content-free artifact boundary violated: {key}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--shard-index", type=int, required=True)
    parser.add_argument("--shard-count", type=int, default=6)
    parser.add_argument(
        "--out",
        type=Path,
        default=ROOT / "artifacts/hcl-structured-output-diagnostic-v01",
    )
    args = parser.parse_args()

    if args.shard_count != 6 or not 0 <= args.shard_index < 6:
        raise RuntimeError("diagnostic requires exactly 6 shards")

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
        raise RuntimeError("unexpected diagnostic shard shape")

    results: list[dict[str, Any]] = []
    for case in selected:
        result = run_case(case, api_key)
        results.append(result)
        categories = Counter(x["category"] for x in result["provider_calls"])
        print(
            f"{case['id']}: success={result['success']} "
            f"hcl_attempts={result['hcl_attempts_used']} "
            f"provider_calls={result['provider_call_count']} "
            f"failure_class={result['failure_class']} "
            f"categories={dict(categories)}",
            flush=True,
        )

    payload = {
        "shard_index": args.shard_index,
        "shard_count": args.shard_count,
        "requested": 4,
        "completed": len(results),
        "results": results,
    }
    assert_content_free(payload)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / f"shard_{args.shard_index}.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
