#!/usr/bin/env python3
"""Synthetic access probe before any sealed LongMemEval provider call."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from hcl.v04.provider_profiles import capabilities_for_profile
from scripts.run_v04_long_horizon_bounded_context_v01 import make_real_backend

JUDGE_MODEL = "gpt-4o-2024-08-06"


class AccessError(ValueError):
    pass


def validate_shapes() -> dict:
    deepseek = capabilities_for_profile("deepseek_flash")
    qwen = capabilities_for_profile("qwen_openai")
    if not deepseek.json_object_mode or not qwen.json_object_mode:
        raise AccessError("JSON capability missing")
    if qwen.seed or qwen.json_extra_body:
        raise AccessError("Qwen profile inherited DeepSeek-only request fields")
    return {"deepseek_profile": "deepseek_flash", "qwen_profile": "qwen_openai",
            "judge_model": JUDGE_MODEL, "provider_calls": 0}


def probe() -> dict:
    if os.getenv("GITHUB_ACTIONS") != "true" or os.getenv("GITHUB_RUN_ATTEMPT") != "1":
        raise AccessError("access probe requires first-attempt GitHub Actions")
    required = ("DEEPSEEK_API_KEY", "QWEN_API_KEY", "QWEN_BASE_URL",
                "QWEN_MODEL", "OPENAI_API_KEY")
    if missing := [x for x in required if not os.getenv(x)]:
        raise AccessError(f"provider access configuration missing: {missing}")
    result = validate_shapes()
    synthetic = [{"role": "system", "content": "Return JSON only."},
                 {"role": "user", "content": 'Return {"ok": true}.'}]
    for name, key, base, model, profile in (
        ("deepseek", os.environ["DEEPSEEK_API_KEY"], "https://api.deepseek.com",
         "deepseek-flash", "deepseek_flash"),
        ("qwen", os.environ["QWEN_API_KEY"], os.environ["QWEN_BASE_URL"],
         os.environ["QWEN_MODEL"], "qwen_openai"),
    ):
        backend = make_real_backend(key, base, model, provider_profile=profile)
        answer = backend.complete_json(synthetic, max_tokens=128, temperature=0.0)
        try:
            parsed = json.loads(answer)
        except json.JSONDecodeError as exc:
            raise AccessError(f"{name} JSON-mode probe failed") from exc
        if parsed.get("ok") is not True:
            raise AccessError(f"{name} JSON-mode probe did not return expected shape")
        result[name] = {"model": model, "profile": profile,
                        "calls": backend.metrics()["calls"]}
    from openai import OpenAI
    judge = OpenAI(api_key=os.environ["OPENAI_API_KEY"], max_retries=0)
    response = judge.chat.completions.create(
        model=JUDGE_MODEL,
        messages=[{"role": "user", "content": "Answer yes or no only: is 1 equal to 1?"}],
        n=1, temperature=0, max_tokens=10)
    if "yes" not in (response.choices[0].message.content or "").lower():
        raise AccessError("official judge model probe failed")
    result["judge"] = {"model": JUDGE_MODEL, "calls": 1}
    result["provider_calls"] = 3
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--probe", action="store_true")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    if args.validate_only == args.probe:
        parser.error("choose exactly one of --validate-only or --probe")
    result = validate_shapes() if args.validate_only else probe()
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
