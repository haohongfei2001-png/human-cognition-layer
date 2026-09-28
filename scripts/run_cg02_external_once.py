"""One-shot CG-02 provider runner for the existing DeepSeek Actions secret.

Importing this module never reads credentials or calls a provider. The default
GitHub workflow keeps the owner grant at zero; execution requires a later,
explicitly authorized cap plus a unique trigger commit.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys

from scripts.cg02_external_package import PACKAGE, build_package, score_answer


def _write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    temporary.replace(path)


def load_frozen_package():
    frozen = json.loads(PACKAGE.read_text())
    built = build_package()
    if frozen != built:
        raise ValueError("frozen CG-02 package differs from provider-free preflight")
    if frozen.get("provider") != "deepseek":
        raise ValueError("CG-02 provider drift")
    if frozen.get("actions_secret_name") != "DEEPSEEK_API_KEY":
        raise ValueError("CG-02 secret contract drift")
    if frozen.get("model") != "deepseek-v4-pro":
        raise ValueError("CG-02 model drift")
    if frozen.get("maximum_provider_calls") != 20 or len(frozen.get("cases", ())) != 4:
        raise ValueError("CG-02 call/case drift")
    return frozen


class DeepSeekProvider:
    """Explicit adapter; no environment lookup and no retry."""

    def __init__(self, api_key, package):
        if not isinstance(api_key, str) or not api_key:
            raise ValueError("explicit DeepSeek API key required")
        from openai import OpenAI
        self.client = OpenAI(
            api_key=api_key,
            base_url=package["provider_endpoint"],
            max_retries=0,
            timeout=120,
        )
        self.package = package

    def __call__(self, messages):
        request = self.package["provider_request"]
        response = self.client.chat.completions.create(
            model=self.package["model"],
            messages=messages,
            max_tokens=self.package["maximum_output_tokens_per_call"],
            response_format=request["response_format"],
            extra_body={"thinking": request["thinking"]},
        )
        choice = response.choices[0]
        usage = response.usage
        if usage is None or not isinstance(choice.message.content, str):
            raise ValueError("missing provider usage or output")
        basis = self.package["price_basis"]
        cost = (
            usage.prompt_tokens * basis["input_cache_miss_usd_per_million"]
            + usage.completion_tokens * basis["output_usd_per_million"]
        ) / 1_000_000
        usage_raw = usage.model_dump(mode="json")
        hit = usage_raw.get("prompt_cache_hit_tokens")
        miss = usage_raw.get("prompt_cache_miss_tokens")
        # This is a published-rate estimate, separate from the unchanged
        # frozen peak all-cache-miss reservation used to enforce the cap.
        estimated_actual = None
        if (type(hit) is int and type(miss) is int and
                hit + miss == usage.prompt_tokens and type(response.created) is int):
            created = datetime.fromtimestamp(response.created, timezone.utc)
            peak = created.weekday() < 5 and (
                1 <= created.hour < 4 or 6 <= created.hour < 10)
            factor = 1.0 if peak else 0.5
            estimated_actual = (
                hit * 0.044 * factor + miss * basis["input_cache_miss_usd_per_million"] * factor
                + usage.completion_tokens * basis["output_usd_per_million"] * factor
            ) / 1_000_000
        return {
            "model": response.model,
            "raw": choice.message.content,
            "input_tokens": usage.prompt_tokens,
            "output_tokens": usage.completion_tokens,
            "cost_usd": cost,
            "finish_reason": choice.finish_reason,
            "cost_basis": "REPOSITORY_FROZEN_DEEPSEEK_PEAK_ALL_CACHE_MISS",
            "provider_price_estimated_cost_usd": estimated_actual,
            "usage_raw": usage_raw,
            "response_raw": response.model_dump(mode="json"),
        }


class BudgetLedger:
    def __init__(self, package, checkpoint=None):
        self.package = package
        self.checkpoint = checkpoint
        self.calls = 0
        self.cost_usd = 0.0
        self.attempts = []

    def _reserve(self):
        basis = self.package["price_basis"]
        return (
            self.package["maximum_input_tokens_per_call"]
            * basis["input_cache_miss_usd_per_million"]
            + self.package["maximum_output_tokens_per_call"]
            * basis["output_usd_per_million"]
        ) / 1_000_000

    def call(self, provider, messages):
        serialized = json.dumps(messages, ensure_ascii=False).encode()
        if len(serialized) > self.package["maximum_input_tokens_per_call"]:
            raise ValueError("conservative input byte/token bound exceeded")
        if self.calls >= self.package["maximum_provider_calls"]:
            raise ValueError("call cap exceeded")
        reserve = self._reserve()
        if self.cost_usd + reserve > self.package["proposed_hard_cap_usd"]:
            raise ValueError("USD hard cap would be exceeded")

        self.calls += 1
        attempt = {
            "request_raw": {
                "endpoint": self.package["provider_endpoint"] + "/chat/completions",
                "model": self.package["model"],
                "messages": messages,
                "max_tokens": self.package["maximum_output_tokens_per_call"],
                "response_format": self.package["provider_request"]["response_format"],
                "thinking": self.package["provider_request"]["thinking"],
            },
            "pending_reservation_usd": reserve,
            "call_index": self.calls,
        }
        self.attempts.append(attempt)
        if self.checkpoint:
            self.checkpoint(self)

        try:
            result = provider(messages)
            allowed_models = {self.package["model"], self.package["model_version"]}
            if (
                result["model"] not in allowed_models
                or result["input_tokens"] > self.package["maximum_input_tokens_per_call"]
                or result["output_tokens"] > self.package["maximum_output_tokens_per_call"]
                or result["cost_usd"] < 0
                or result["cost_usd"] > reserve
                or not isinstance(result["raw"], str)
            ):
                raise ValueError("provider contract or cap violation")
        except Exception as exc:
            self.cost_usd += reserve
            attempt.pop("pending_reservation_usd", None)
            attempt["failure_reservation_usd"] = reserve
            attempt["failure_type"] = type(exc).__name__
            if self.checkpoint:
                self.checkpoint(self)
            raise

        attempt.pop("pending_reservation_usd", None)
        attempt["result"] = result
        self.cost_usd += result["cost_usd"]
        if self.checkpoint:
            self.checkpoint(self)
        return result


def run_with_provider(provider, package, checkpoint=None):
    rows = []
    ledger = BudgetLedger(package, checkpoint=checkpoint)
    for case in package["cases"]:
        for arm in package["arms"]:
            messages = case["messages"][arm]
            response = ledger.call(provider, messages)
            rows.append(
                {
                    "case_id": case["case_id"],
                    "arm": arm,
                    "raw": response["raw"],
                    "score": score_answer(case, response["raw"]),
                    "usage": {
                        key: response[key]
                        for key in ("model", "input_tokens", "output_tokens", "cost_usd",
                                    "provider_price_estimated_cost_usd", "usage_raw")
                    },
                    "response_raw": response["response_raw"],
                    "final_messages": messages,
                    "preflight": case["preflight"] if arm in ("H", "H-new") else None,
                }
            )
            if checkpoint:
                checkpoint(ledger, rows)
    return {
        "rows": rows,
        "calls": ledger.calls,
        "cost_usd": ledger.cost_usd,
        "attempts": ledger.attempts,
        "scope": "HCL_AUTHORED_DEVELOPMENT_NOT_FRESH_EXTERNAL_EVIDENCE",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()

    package = load_frozen_package()
    if args.validate_only:
        print(
            json.dumps(
                {
                    "provider": package["provider"],
                    "model": package["model"],
                    "cases": len(package["cases"]),
                    "arms": package["arms"],
                    "maximum_provider_calls": package["maximum_provider_calls"],
                    "estimated_worst_case_usd": package["estimated_worst_case_usd"],
                    "hard_cap_usd": package["proposed_hard_cap_usd"],
                    "provider_calls_executed": 0,
                    "treatment_presence": "PASS",
                }
            )
        )
        return 0

    if os.environ.get("HCL_CG02_AUTHORIZED_CAP_USD") != "0.30":
        raise SystemExit("exact CG-02 owner grant is absent")
    key = os.environ.get("DEEPSEEK_API_KEY")
    if not key:
        raise SystemExit("existing DeepSeek Actions secret is absent")

    args.out.mkdir(parents=True, exist_ok=True)
    journal = args.out / "journal.json"
    metadata = {
        "schema": "hcl-cg02-external-run-v1",
        "git_sha": os.environ.get("GITHUB_SHA"),
        "run_id": os.environ.get("GITHUB_RUN_ID"),
        "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
        "authorized_baseline_sha": "86e1db9ecdb908cbe67bc561b878a0d37e4cb819",
        "frozen_package_sha256": hashlib.sha256(PACKAGE.read_bytes()).hexdigest(),
        "provider": package["provider"],
        "model": package["model"],
        "model_version": package["model_version"],
        "usd_hard_cap": package["proposed_hard_cap_usd"],
        "cost_basis": "REPOSITORY_FROZEN_DEEPSEEK_PEAK_ALL_CACHE_MISS",
        "source_policy": package["source_policy"],
    }

    def checkpoint(ledger, rows=None):
        _write_json(
            journal,
            dict(
                metadata,
                state="IN_PROGRESS",
                calls=ledger.calls,
                cost_usd=ledger.cost_usd,
                attempts=ledger.attempts,
                rows=rows or [],
            ),
        )

    provider = DeepSeekProvider(key, package)
    try:
        result = run_with_provider(provider, package, checkpoint=checkpoint)
    except Exception as exc:
        current = json.loads(journal.read_text()) if journal.exists() else metadata
        current.update(state="FAILED", failure_type=type(exc).__name__)
        _write_json(journal, current)
        print(f"CG-02 run stopped: {type(exc).__name__}", file=sys.stderr)
        return 1

    if (
        result["calls"] != 20
        or len(result["rows"]) != 20
        or result["cost_usd"] > package["proposed_hard_cap_usd"]
    ):
        _write_json(journal, dict(metadata, state="INVALID_FINAL_RECEIPT", **result))
        return 1

    final = dict(metadata, state="COMPLETE", **result)
    _write_json(args.out / "results.json", final)
    _write_json(journal, final)
    print(
        json.dumps(
            {
                "calls": result["calls"],
                "rows": len(result["rows"]),
                "conservative_cost_upper_usd": result["cost_usd"],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
