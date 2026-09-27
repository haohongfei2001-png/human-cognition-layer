"""Non-fresh v02 output-contract repair; same frozen cognition and public cases."""

import argparse, json, os, sys
from itertools import product
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from hcl.v04.model import EventRecord
from hcl.v10 import Argument, Attack, ArgumentFramework, HCLV10Runtime, SCOPE
from scripts.prepare_v10_pyarg_dev_v01 import (
    CONTRACT,
    MANIFEST,
    sha,
    verified_selection,
)
from scripts.run_v06_fantom_cpd_v01 import CappedBackend
from scripts.run_v06_fantom_cpgd_fresh_v01 import (
    BudgetLedger,
    OneCallDeepSeekBackend,
    _metrics,
)

TOKEN = "HCL_V10_PYARG_DEV_V02_ONCE"
COST_CAP_USD = 0.05
CAPS = {
    "C": {"calls": 4, "input_chars": 10000, "output_chars": 8000},
    "P": {"calls": 4, "input_chars": 12000, "output_chars": 8000},
    "T": {"calls": 4, "input_chars": 30000, "output_chars": 8000},
}
COMMON = (
    "Reason under the explicit complete Dung argumentation graph and the supplied semantics. "
    "IN/OUT/UNDEC are conditional formal labels, not facts about people, moral truth, or actual beliefs. "
    "Preserve cycles and alternatives. Do not infer an attack from ordinary disagreement or omit a listed attack. "
    "Return exactly one JSON object with exactly two TOP-LEVEL keys: labellings and reason. labellings is a nonempty list; each list item has exactly three keys IN, OUT, UNDEC, each an array of node IDs. reason is one TOP-LEVEL nonempty string of at most 500 characters covering all labellings; NEVER put reason inside a labelling. No other keys or markdown. "
    "Grounded requests one least complete labelling; complete requests ALL legal complete labellings. Each node must occur in exactly one label in every labelling."
)
P_SYSTEM = (
    COMMON
    + " Internally list attackers, follow defense and reinstatement until fixed point, and check every complete alternative for legality and completeness."
)
T_SYSTEM = (
    COMMON
    + " Use the supplied generic exact-tool labellings; the HCL source scope binds provenance only. The formal result never determines an actual moral/private belief."
)


def generic_labels(graph, semantics):
    """Independent competent generic solver: exhaustive three-valued local legality.

    No HCL set-defense algorithm or runtime state is used to compute these labels.
    """
    ids = graph["arguments"]
    edges = graph["attacks"]
    complete = []
    if (
        len(ids) > 12
        or len(set(ids)) != len(ids)
        or any(a not in ids or b not in ids for a, b in edges)
    ):
        raise ValueError("bounded valid generic graph required")
    for vector in product(("IN", "OUT", "UNDEC"), repeat=len(ids)):
        labels = dict(zip(ids, vector))
        valid = True
        for a in ids:
            attackers = [labels[x] for x, y in edges if y == a]
            expected = (
                "OUT"
                if "IN" in attackers
                else "IN" if all(x == "OUT" for x in attackers) else "UNDEC"
            )
            if labels[a] != expected:
                valid = False
                break
        if valid:
            complete.append(
                {
                    k: sorted(a for a in ids if labels[a] == k)
                    for k in ("IN", "OUT", "UNDEC")
                }
            )
    complete.sort(key=lambda x: x["IN"])
    if semantics == "complete":
        return complete
    if semantics == "grounded":
        return [
            x for x in complete if all(set(x["IN"]) <= set(y["IN"]) for y in complete)
        ]
    raise ValueError("utility uses grounded/complete semantics only")


def build_state(item):
    g = item["graph"]
    source = (
        CONTRACT
        + "\nPUBLIC CONSTRUCTOR DECLARATIONS:\n"
        + item["source"]
        + "\nDECLARED GRAPH:\n"
        + json.dumps(g, sort_keys=True)
    )
    rt = HCLV10Runtime()
    rt.ingest_event(
        EventRecord(
            event_id=item["case_id"],
            source_id="PyArg-public-author-example",
            raw_text=source,
            valid_time="2026-01-01T00:00:00+00:00",
            recorded_at="2026-01-01T00:00:00+00:00",
            metadata={
                "argumentation_scope": SCOPE,
                "reader_only": True,
                "chronology": "INGESTION_PLACEHOLDER",
            },
        )
    )
    f = ArgumentFramework(
        item["case_id"],
        item["case_id"],
        tuple(Argument(a, json.dumps(a)) for a in g["arguments"]),
        tuple(Attack(a, b, json.dumps([a, b])) for a, b in g["attacks"]),
    )
    rt.ingest_framework(f)
    return rt, source


def inputs(item):
    rt, source = build_state(item)
    state = rt.answer_context(item["case_id"])
    # Source-only state is complete before query/semantics release.
    q = {"semantics": item["semantics"], "task": "return all requested labellings"}
    generic = generic_labels(item["graph"], item["semantics"])
    calc = rt.analyse(item["case_id"], item["semantics"])
    if generic != calc["labellings"]:
        raise RuntimeError("generic solver/runtime disagreement")
    return (
        state,
        q,
        generic,
        calc,
        {
            a: {"source": source, "declared_graph": item["graph"], "query": q}
            | (
                {
                    "source_only_state": state,
                    "generic_tool_labellings": generic,
                    "conditional_computation": calc,
                }
                if a == "T"
                else {}
            )
            for a in CAPS
        },
    )


def parse_answer(raw, ids):
    try:
        x = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError("invalid answer JSON") from exc
    if (
        not isinstance(x, dict)
        or set(x) != {"labellings", "reason"}
        or not isinstance(x["reason"], str)
        or not 1 <= len(x["reason"].strip()) <= 500
        or not isinstance(x["labellings"], list)
        or not 1 <= len(x["labellings"]) <= 2 ** len(ids)
    ):
        raise ValueError("invalid bounded answer")
    rows = []
    for row in x["labellings"]:
        if (
            not isinstance(row, dict)
            or set(row) != {"IN", "OUT", "UNDEC"}
            or any(
                not isinstance(v, list) or any(not isinstance(a, str) for a in v)
                for v in row.values()
            )
        ):
            raise ValueError("invalid labelling fields")
        flat = [a for v in row.values() for a in v]
        if (
            len(flat) != len(ids)
            or len(set(flat)) != len(flat)
            or set(flat) != set(ids)
        ):
            raise ValueError("each source node requires exactly one label")
        rows.append({k: sorted(row[k]) for k in ("IN", "OUT", "UNDEC")})
    if len({json.dumps(r, sort_keys=True) for r in rows}) != len(rows):
        raise ValueError("duplicate labelling")
    return {"labellings": sorted(rows, key=lambda r: r["IN"]), "reason": x["reason"]}


def evaluate_one(item, backends):
    state, q, generic, calc, user = inputs(item)
    arms = {}
    for a in CAPS:
        raw = backends[a].complete_json(
            [
                {
                    "role": "system",
                    "content": (
                        COMMON if a == "C" else P_SYSTEM if a == "P" else T_SYSTEM
                    ),
                },
                {"role": "user", "content": json.dumps(user[a], sort_keys=True)},
            ],
            max_tokens=512,
            temperature=0,
        )
        try:
            answer = parse_answer(raw, item["graph"]["arguments"])
            invalid = None
        except ValueError as exc:
            answer = None
            invalid = str(exc)
        arms[a] = {
            "answer": answer,
            "invalid_reason": invalid,
            "raw_response": raw,
            "response_sha256": sha(raw),
        }
    # No annotated source assertions or scorer decisions enter an answer call.
    for row in arms.values():
        row["agrees_with_declared_graph"] = bool(
            row["answer"] and row["answer"]["labellings"] == generic
        )
    return {
        "case_id": item["case_id"],
        "source_sha256": item["source_sha256"],
        "source_file_sha256": item["source_file_sha256"],
        "family_sha256": item["family_sha256"],
        "source_only_state": state,
        "state_sha256": sha(json.dumps(state, sort_keys=True)),
        "query": q,
        "generic_tool_labellings": generic,
        "conditional_computation": calc,
        "actual_arm_inputs": user,
        "arms": arms,
    }


def validate(items):
    totals = {a: 0 for a in CAPS}
    for item in items:
        _, _, g, c, u = inputs(item)
        assert g == c["labellings"]
        for a in CAPS:
            totals[a] += len(
                COMMON if a == "C" else P_SYSTEM if a == "P" else T_SYSTEM
            ) + len(json.dumps(u[a], sort_keys=True))
    if any(totals[a] > CAPS[a]["input_chars"] for a in CAPS):
        raise RuntimeError("frozen input cap exceeded")
    return totals


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--source-dir", type=Path, required=True)
    p.add_argument(
        "--out",
        type=Path,
        default=ROOT / "artifacts/hcl-v10-pyarg-dev-v02/results.json",
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
    selected = verified_selection(args.source_dir)
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
        or os.getenv("HCL_V10_PYARG_DEV_V02_RUN_ONCE_TOKEN") != TOKEN
    ):
        raise RuntimeError("first-attempt cloud one-shot required")
    if (
        float(os.getenv("HCL_V10_PYARG_DEV_V02_COST_AUTHORIZED_USD") or "0")
        < COST_CAP_USD
    ):
        raise RuntimeError("separate v0.10 authorization required")
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
        "format": "hcl-v10-public-pyarg-example-nonfresh-repair-result-v02",
        "scope": "NON-FRESH output-contract repair on the four v01-consumed public-author examples under identical frozen graphs, not a benchmark, fresh efficacy, natural-language argument mining, moral verdict or specialized architecture gain",
        "selection_sha256": sha(MANIFEST.read_bytes()),
        "status": (
            "SUCCESS"
            if len(completed) == 4 and not failures
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
