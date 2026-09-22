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

BASE_URL = "https://api.deepseek.com"
MODEL = "deepseek-flash"
SEED = 42
STATE_MAX_TOKENS = 8192
FIXTURES = ROOT / "eval/answer_loop/state_generation_reliability_v01.json"
KNOWN_STATE_EXHAUSTION = "HCL state builder returned no valid JSON after 3 attempts"


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def render_case(case: dict[str, Any]) -> str:
    agents = [f"Agent-{chr(ord('A') + i)}" for i in range(case["agent_count"])]
    variant = int(case["variant"])
    events: list[str] = []
    for i in range(int(case["event_count"])):
        actor = agents[(i + variant) % len(agents)]
        other = agents[(i + variant + 1) % len(agents)]
        room = 1 + ((i * 3 + variant) % 7)
        locker = 1 + ((i * 5 + variant) % 19)
        if i % 5 == 0:
            events.append(
                f"Event {i+1}: {actor} is present in laboratory room {room} and "
                f"sees marker M{i+1} placed in locker L{locker}."
            )
        elif i % 5 == 1:
            events.append(
                f"Event {i+1}: {actor} leaves laboratory room {room} before a "
                f"notice about marker M{i} is posted; no message is sent to {actor}."
            )
        elif i % 5 == 2:
            events.append(
                f"Event {i+1}: {actor} directly tells {other} that locker L{locker} "
                f"is reserved, and {other} explicitly hears the statement."
            )
        elif i % 5 == 3:
            events.append(
                f"Event {i+1}: while {actor} is absent, {other} sees marker M{i+1} "
                f"moved to locker L{locker}; {actor} receives no update."
            )
        else:
            events.append(
                f"Event {i+1}: {actor} and {other} are together in room {room} when "
                f"a supervisor publicly announces that tag T{i+1} is active."
            )

    for j in range(int(case["nested_claims"])):
        a = agents[(j + variant) % len(agents)]
        b = agents[(j + variant + 1) % len(agents)]
        c = agents[(j + variant + 2) % len(agents)]
        events.append(
            f"Recursive note {j+1}: {a} sees {b} leave before a locker change, and "
            f"{a} knows that {c} saw {b} leave; no later communication to {b} is "
            f"described."
        )

    target = agents[variant % len(agents)]
    observer = agents[(variant + 1) % len(agents)]
    question = (
        f"Question: Based only on this synthetic record, represent the "
        f"decision-relevant cognition state needed to reason about what {observer} "
        f"can know or believe about {target}'s information after the final event. "
        f"Do not assume unmentioned communication."
    )
    return "\n".join([
        "Synthetic reliability fixture. The following events are artificial.",
        *events,
        question,
    ])


class ObservingBackend:
    def __init__(self, inner: Any) -> None:
        self.inner = inner
        self.attempts: list[dict[str, Any]] = []

    def complete(
        self,
        messages: list[dict[str, str]],
        *,
        max_tokens: int,
        temperature: float = 0.0,
    ) -> str:
        ordinal = len(self.attempts) + 1
        try:
            text = self.inner.complete(
                messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )
        except Exception as exc:
            self.attempts.append({
                "attempt": ordinal,
                "backend_exception_type": type(exc).__name__,
            })
            raise

        encoded = text.encode("utf-8")
        self.attempts.append({
            "attempt": ordinal,
            "response_bytes": len(encoded),
            "response_sha256": hashlib.sha256(encoded).hexdigest(),
            "empty": not bool(text.strip()),
            "json_object_parseable": extract_json(text) is not None,
        })
        return text


def run_case(case: dict[str, Any], api_key: str) -> dict[str, Any]:
    user_input = render_case(case)
    backend = ObservingBackend(
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


def summarize(results: list[dict[str, Any]]) -> dict[str, Any]:
    json_failures = [x for x in results if x["failure_class"] == "state_json_exhaustion"]
    other_failures = [x for x in results if x["failure_class"] == "backend_or_other_exception"]
    if len(json_failures) >= 2 and len(other_failures) >= 2:
        interpretation = "MIXED_RUNTIME_RELIABILITY_DEFECT"
    elif len(json_failures) >= 2:
        interpretation = "STATE_JSON_RELIABILITY_DEFECT_ESTABLISHED"
    elif len(other_failures) >= 2:
        interpretation = "BACKEND_OR_OTHER_RELIABILITY_DEFECT_ESTABLISHED"
    else:
        interpretation = "NO_REPEATABLE_DEFECT_ESTABLISHED"

    by_stratum: dict[str, dict[str, int]] = {}
    for item in results:
        key = f"{item['length_band']}/{item['complexity']}"
        slot = by_stratum.setdefault(
            key,
            {"n": 0, "success": 0, "state_json_exhaustion": 0, "backend_or_other_exception": 0},
        )
        slot["n"] += 1
        if item["success"]:
            slot["success"] += 1
        elif item["failure_class"]:
            slot[item["failure_class"]] += 1

    return {
        "suite": "HCL state-generation reliability audit v0.1",
        "model": MODEL,
        "seed": SEED,
        "state_max_tokens": STATE_MAX_TOKENS,
        "fixture_count": len(results),
        "success_count": sum(bool(x["success"]) for x in results),
        "failure_count": sum(not bool(x["success"]) for x in results),
        "state_json_exhaustion_count": len(json_failures),
        "backend_or_other_exception_count": len(other_failures),
        "state_json_exhaustion_ids": [x["id"] for x in json_failures],
        "backend_or_other_exception_ids": [x["id"] for x in other_failures],
        "by_stratum": by_stratum,
        "predeclared_interpretation": interpretation,
        "claim_boundary": (
            "Independent synthetic audit of frozen HCL state-generation reliability; "
            "no external benchmark content and no efficacy claim."
        ),
    }


def assert_content_free_artifacts(summary: dict[str, Any], results: list[dict[str, Any]]) -> None:
    raw = json.dumps({"summary": summary, "results": results}, ensure_ascii=False).lower()
    forbidden_keys = [
        '"input":', '"prompt":', '"messages":', '"response":', '"response_text":',
        '"state":', '"normalized_state":', '"api_key":', '"exception_text":',
    ]
    for key in forbidden_keys:
        if key in raw:
            raise RuntimeError(f"content-free artifact boundary violated: {key}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--out",
        type=Path,
        default=ROOT / "artifacts/hcl-state-generation-reliability-v01",
    )
    args = parser.parse_args()

    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise RuntimeError("DEEPSEEK_API_KEY is required")

    suite = json.loads(FIXTURES.read_text(encoding="utf-8"))
    cases = suite["cases"]
    results: list[dict[str, Any]] = []
    for case in cases:
        result = run_case(case, api_key)
        results.append(result)
        print(
            f"{case['id']}: success={result['success']} "
            f"attempts={result['attempt_count']} "
            f"failure_class={result['failure_class']}",
            flush=True,
        )

    summary = summarize(results)
    assert_content_free_artifacts(summary, results)

    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    with (args.out / "results.jsonl").open("w", encoding="utf-8") as handle:
        for result in results:
            handle.write(json.dumps(result, ensure_ascii=False) + "\n")

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
