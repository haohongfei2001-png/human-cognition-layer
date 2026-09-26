"""C/P/tool-D comparison on supplemented external formal models; no native gold."""

from __future__ import annotations
import argparse, json, os, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from hcl.v09 import HCLV09Runtime
from scripts.prepare_v09_counterbench_dev_v01 import (
    CONTRACT,
    MANIFEST,
    sha,
    verified_selection,
    source_model,
    source_event,
    query_task,
    reference_values,
)
from scripts.run_v06_fantom_cpd_v01 import CappedBackend
from scripts.run_v06_fantom_cpgd_fresh_v01 import (
    BudgetLedger,
    OneCallDeepSeekBackend,
    _metrics,
)

TOKEN = "HCL_V09_COUNTERBENCH_DEV_V01_ONCE"
COST_CAP_USD = 0.10
CAPS = {
    "C": {"calls": 8, "input_chars": 20000, "output_chars": 10000},
    "P": {"calls": 8, "input_chars": 22000, "output_chars": 10000},
    "D": {"calls": 8, "input_chars": 70000, "output_chars": 10000},
}
COMMON = """Reason only under the supplied declared Boolean structural-model contract and full public source. Separate factual observations from interventions and preserve the same exogenous context. Check inconsistent observations and underdetermination before answering. Ordinary causation or absence of evidence never establishes a complete equation unless explicitly stipulated here. Answer JSON with result YES|NO|UNKNOWN, and a brief reason (at most 500 characters). YES means all compatible factual contexts yield target=1 after intervention, NO means all yield target=0, UNKNOWN means inconsistent observations or different possible target outcomes. A hypothetical consequence is not an observed fact or proof about a real person."""
P_SYSTEM = (
    COMMON
    + " Internally check equation directions, joint/alternative parents and negations, abduce factual contexts, replace intervened equations, then predict without overwriting factual evidence."
)
D_SYSTEM = (
    COMMON
    + " Use the supplied exact conditional model calculation; its UNKNOWN is not evidence of target absence."
)


def parse_answer(raw):
    try:
        answer = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError("invalid answer JSON") from exc
    if (
        not isinstance(answer, dict)
        or answer.get("result") not in ("YES", "NO", "UNKNOWN")
        or not isinstance(answer.get("reason"), str)
        or not answer["reason"].strip()
        or len(answer["reason"]) > 500
    ):
        raise ValueError("invalid bounded result/reason")
    return answer


def build_state(item):
    # Only causal source/contract is consumed. Question, metadata and native
    # labels have not been released to this construction path.
    runtime = HCLV09Runtime()
    runtime.ingest_event(source_event(item))
    model, facts, clauses = source_model(item["source"], item["case_id"])
    runtime.ingest_model(model)
    return runtime, model, facts, clauses


def evaluate_one(item, backends):
    runtime, model, facts, clauses = build_state(item)
    state = runtime.answer_context(item["case_id"])
    state_digest = sha(json.dumps(state, sort_keys=True))
    # Query release follows completed and archived source-only state.
    target, observations, interventions = query_task(item["question"], model, facts)
    query = {
        "public_question": item["question"],
        "explicit_factual_assumptions": observations,
        "explicit_interventions": interventions,
        "target": target,
    }
    calculation = runtime.counterfactual(
        item["case_id"], target, observations=observations, interventions=interventions
    )
    source = CONTRACT + "\n" + item["source"]
    arms = {}
    for arm in "CPD":
        user = {"source": source, "query": query}
        if arm == "D":
            user.update(
                {"source_only_state": state, "conditional_calculation": calculation}
            )
        system = COMMON if arm == "C" else P_SYSTEM if arm == "P" else D_SYSTEM
        raw = backends[arm].complete_json(
            [
                {"role": "system", "content": system},
                {"role": "user", "content": json.dumps(user, sort_keys=True)},
            ],
            max_tokens=256,
            temperature=0,
        )
        try:
            answer = parse_answer(raw)
            invalid = None
        except ValueError as exc:
            answer = None
            invalid = str(exc)
        arms[arm] = {
            "answer": answer,
            "raw_response": raw,
            "response_sha256": sha(raw),
            "invalid_reason": invalid,
        }
    # Independent scorer reads only public declared equations, never native
    # answers. Its result is computed after all three answers are saved.
    expected_values = reference_values(
        model, clauses, target, observations, interventions
    )
    if expected_values != calculation["possible_values"]:
        raise RuntimeError("independent equation truth table disagrees with runtime")
    expected = (
        "YES"
        if expected_values == [1]
        else "NO" if expected_values == [0] else "UNKNOWN"
    )
    for row in arms.values():
        row["agrees_with_declared_model"] = bool(
            row["answer"] and row["answer"]["result"] == expected
        )
    return {
        "case_id": item["case_id"],
        "source_sha256": item["source_sha256"],
        "question_sha256": item["question_sha256"],
        "source_only_state": state,
        "state_sha256": state_digest,
        "conditional_calculation": calculation,
        "query": query,
        "adapted_expected_result": expected,
        "arms": arms,
    }


def validate(selected):
    totals = {a: 0 for a in "CPD"}
    for item in selected:
        rt, m, f, c = build_state(item)
        target, observations, interventions = query_task(item["question"], m, f)
        computed = rt.counterfactual(
            item["case_id"],
            target,
            observations=observations,
            interventions=interventions,
        )
        if (
            reference_values(m, c, target, observations, interventions)
            != computed["possible_values"]
        ):
            raise RuntimeError("independent public-model check failed")
        for arm in "CPD":
            user = {
                "source": CONTRACT + "\n" + item["source"],
                "query": {
                    "public_question": item["question"],
                    "explicit_factual_assumptions": observations,
                    "explicit_interventions": interventions,
                    "target": target,
                },
            }
            if arm == "D":
                user.update(
                    {
                        "source_only_state": rt.answer_context(item["case_id"]),
                        "conditional_calculation": computed,
                    }
                )
            totals[arm] += len(
                COMMON if arm == "C" else P_SYSTEM if arm == "P" else D_SYSTEM
            ) + len(json.dumps(user, sort_keys=True))
    if any(totals[a] > CAPS[a]["input_chars"] for a in "CPD"):
        raise RuntimeError("frozen inputs exceed operational cap")
    return totals


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--source", type=Path, required=True)
    p.add_argument(
        "--out",
        type=Path,
        default=ROOT / "artifacts/hcl-v09-counterbench-dev-v01/results.json",
    )
    p.add_argument("--validate-only", action="store_true")
    p.add_argument("--execute", action="store_true")
    args = p.parse_args()
    if args.validate_only == args.execute:
        p.error("choose validate-only or execute")
    bound = (
        sum(c["input_chars"] for c in CAPS.values()) * 0.30
        + sum(c["output_chars"] for c in CAPS.values()) * 1.20
    ) / 1000000
    if bound > COST_CAP_USD:
        raise RuntimeError("planning cost cap unsafe")
    selected = verified_selection(args.source.read_bytes())
    sizes = validate(selected)
    if args.validate_only:
        print(
            json.dumps(
                {
                    "selected": len(selected),
                    "provider_calls": 0,
                    "input_chars": sizes,
                    "cost_cap_usd": COST_CAP_USD,
                    "char_as_token_peak_planning_usd": bound,
                }
            )
        )
        return 0
    if (
        os.getenv("GITHUB_ACTIONS") != "true"
        or os.getenv("GITHUB_RUN_ATTEMPT") != "1"
        or os.getenv("HCL_V09_COUNTERBENCH_DEV_RUN_ONCE_TOKEN") != TOKEN
    ):
        raise RuntimeError("first-attempt cloud one-shot required")
    if (
        float(os.getenv("HCL_V09_COUNTERBENCH_DEV_COST_AUTHORIZED_USD") or "0")
        < COST_CAP_USD
    ):
        raise RuntimeError("separate v0.9 authorization required")
    key = os.getenv("DEEPSEEK_API_KEY")
    if not key:
        raise RuntimeError("existing credential unavailable")
    ledger = BudgetLedger(cap_usd=COST_CAP_USD)
    backends = {
        a: CappedBackend(OneCallDeepSeekBackend(key, ledger), name=a, caps=cap)
        for a, cap in CAPS.items()
    }
    completed = []
    started = []
    failures = []
    for item in selected:
        started.append(item["case_id"])
        try:
            completed.append(evaluate_one(item, backends))
        except Exception as exc:
            failures.append(
                {
                    "case_id": item["case_id"],
                    "error_type": type(exc).__name__,
                    "error": str(exc)[:500],
                }
            )
            break
    metrics = _metrics(backends)
    if len(metrics["TOTAL"]["provider_response_models"]) > 1:
        failures.append({"error_type": "ProviderModelDrift"})
    result = {
        "format": "hcl-v09-supplemented-counterbench-dev-result-v01",
        "scope": "development agreement under supplemented public formal model, not native CounterBench/real-world causation/full-abduction efficacy",
        "selection_sha256": sha(MANIFEST.read_bytes()),
        "status": (
            "SUCCESS"
            if len(completed) == 8 and not failures
            else "PARTIAL_DEVELOPMENT_CONSUMED"
        ),
        "completed_count": len(completed),
        "started_case_ids": started,
        "results": completed,
        "failures": failures,
        "metrics": metrics,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    print(
        json.dumps(
            {
                "status": result["status"],
                "completed_count": len(completed),
                "metrics": metrics["TOTAL"],
            }
        )
    )
    return 0 if result["status"] == "SUCCESS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
