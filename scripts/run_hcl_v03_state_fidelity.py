#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, os
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any
from openai import OpenAI

ROOT = Path(__file__).resolve().parents[1]
DEEPSEEK_BASE_URL = "https://api.deepseek.com"

def extract_json(text: str):
    if not text:
        return None
    text = text.strip()
    candidates = [text]
    l, r = text.find("{"), text.rfind("}")
    if 0 <= l < r:
        candidates.append(text[l:r+1])
    for c in candidates:
        try:
            x = json.loads(c)
            if isinstance(x, dict):
                return x
        except Exception:
            pass
    return None

def flatten_strings(obj: Any):
    out = []
    if isinstance(obj, str):
        out.append(obj)
    elif isinstance(obj, dict):
        for v in obj.values():
            out.extend(flatten_strings(v))
    elif isinstance(obj, list):
        for v in obj:
            out.extend(flatten_strings(v))
    return out

def normalize_state(state):
    """Normalize harmless localized enum variants at the protocol boundary.

    Explanatory strings may follow the user's language, but HCL protocol enums
    are canonical English tokens. Normalization prevents serialization-only
    variation from being mistaken for a cognition failure.
    """
    if not isinstance(state, dict):
        return state
    mode_alias = {
        "简单": "SIMPLE",
        "认识论": "EPISTEMIC",
        "认知": "EPISTEMIC",
        "因果歧义": "CAUSAL_AMBIGUITY",
        "因果模糊": "CAUSAL_AMBIGUITY",
    }
    uncertainty_alias = {
        "低": "low",
        "中": "medium",
        "中等": "medium",
        "高": "high",
    }
    mode = state.get("mode")
    if mode in mode_alias:
        state["mode"] = mode_alias[mode]
    u = state.get("uncertainty")
    if isinstance(u, dict) and u.get("level") in uncertainty_alias:
        u["level"] = uncertainty_alias[u["level"]]
    return state


def schema_errors(state):
    if state is None:
        return ["invalid_json_or_empty"]
    errors = []
    required = ["mode","explicit_facts","agents","hypotheses","missing_bridges","uncertainty","decision_relevant_summary"]
    for key in required:
        if key not in state:
            errors.append("missing:" + key)
    if state.get("mode") not in {"SIMPLE","EPISTEMIC","CAUSAL_AMBIGUITY"}:
        errors.append("invalid:mode")
    if not isinstance(state.get("explicit_facts"), list):
        errors.append("invalid:explicit_facts")
    if not isinstance(state.get("agents"), dict):
        errors.append("invalid:agents")
    if not isinstance(state.get("hypotheses"), list):
        errors.append("invalid:hypotheses")
    if not isinstance(state.get("missing_bridges"), list):
        errors.append("invalid:missing_bridges")
    u = state.get("uncertainty")
    if not isinstance(u, dict):
        errors.append("invalid:uncertainty")
    else:
        if u.get("level") not in {"low","medium","high"}:
            errors.append("invalid:uncertainty.level")
        if not isinstance(u.get("reason"), str):
            errors.append("invalid:uncertainty.reason")
    return errors

def evaluate_fixture(fixture, state):
    exp = fixture["expected"]
    checks = {}
    se = schema_errors(state)
    checks["schema_valid"] = not se
    if state is None:
        return {"passed":False,"checks":checks,"schema_errors":se,"failures":["state unavailable"]}
    checks["mode"] = state.get("mode") == exp["mode"]
    checks["uncertainty"] = state.get("uncertainty",{}).get("level") in exp["uncertainty"]
    hs = state.get("hypotheses",[])
    checks["hypothesis_count"] = exp["min_hypotheses"] <= len(hs) <= exp["max_hypotheses"]
    bridges = state.get("missing_bridges",[])
    checks["missing_bridge"] = (len(bridges) > 0) if exp["require_missing_bridge"] else True
    # Legacy lexical checks are diagnostic-only. They are too brittle to gate
    # cognition fidelity because a valid state may mention a rejected hypothesis
    # or express "insufficient information" with different wording.
    text = "\n".join(flatten_strings(state))
    checks["lexical_required_advisory"] = all(s in text for s in exp.get("required_substrings",[]))
    checks["lexical_forbidden_advisory"] = all(s not in text for s in exp.get("forbidden_substrings",[]))

    # Structured, field-scoped semantic assertions.
    field_contains = exp.get("agent_fields_contains", {})
    field_excludes = exp.get("agent_fields_excludes", {})
    agents = state.get("agents", {}) if isinstance(state.get("agents"), dict) else {}

    contains_ok = True
    for agent, fields in field_contains.items():
        adata = agents.get(agent, {})
        for field, terms in fields.items():
            values = adata.get(field, []) if isinstance(adata, dict) else []
            field_text = "\n".join(str(v) for v in values)
            if not all(term in field_text for term in terms):
                contains_ok = False
    checks["agent_fields_contains"] = contains_ok

    excludes_ok = True
    for agent, fields in field_excludes.items():
        adata = agents.get(agent, {})
        for field, terms in fields.items():
            values = adata.get(field, []) if isinstance(adata, dict) else []
            field_text = "\n".join(str(v) for v in values)
            if any(term in field_text for term in terms):
                excludes_ok = False
    checks["agent_fields_excludes"] = excludes_ok

    min_nested = exp.get("min_beliefs_about_others", {})
    nested_ok = True
    for agent, minimum in min_nested.items():
        adata = agents.get(agent, {})
        values = adata.get("beliefs_about_others", []) if isinstance(adata, dict) else []
        if len(values) < minimum:
            nested_ok = False
    checks["nested_belief_minimum"] = nested_ok

    # Only semantic/structural checks gate pass/fail.
    gating = [
        "schema_valid", "mode", "uncertainty", "hypothesis_count",
        "missing_bridge", "agent_fields_contains",
        "agent_fields_excludes", "nested_belief_minimum"
    ]
    failures = [k for k in gating if not checks.get(k, True)]
    return {"passed":not failures,"checks":checks,"schema_errors":se,"failures":failures}

def call_builder(client, model, system_prompt, fixture, max_tokens):
    user = "情境：\n" + fixture["scene"] + "\n\n问题：\n" + fixture["question"] + "\n\n只生成 HCL 中间状态，不要回答最终问题。"
    last = ""
    for _ in range(4):
        r = client.chat.completions.create(
            model=model,
            messages=[{"role":"system","content":system_prompt},{"role":"user","content":user}],
            temperature=0.0,
            max_tokens=max_tokens,
            seed=42
        )
        last = r.choices[0].message.content or ""
        state = extract_json(last)
        if state is not None:
            return last, normalize_state(state)
    return last, None

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--model", default="deepseek-flash")
    p.add_argument("--fixtures", default="eval/state_fidelity/fixtures_v01.json")
    p.add_argument("--max-tokens", type=int, default=4096)
    p.add_argument("--workers", type=int, default=6)
    args = p.parse_args()

    key = os.getenv("DEEPSEEK_API_KEY")
    if not key:
        raise RuntimeError("DEEPSEEK_API_KEY is required")

    prompt = (ROOT / "hcl/v03/STATE_BUILDER_PROMPT.md").read_text(encoding="utf-8")
    fixtures = json.loads((ROOT / args.fixtures).read_text(encoding="utf-8"))
    client = OpenAI(api_key=key, base_url=DEEPSEEK_BASE_URL)

    def run_one(index_fixture):
        index, fixture = index_fixture
        raw, state = call_builder(client, args.model, prompt, fixture, args.max_tokens)
        ev = evaluate_fixture(fixture, state)
        return index, {
            "id":fixture["id"],"scene":fixture["scene"],"question":fixture["question"],
            "expected":fixture["expected"],"state":state,"evaluation":ev,"raw":raw
        }

    indexed = list(enumerate(fixtures))
    completed = []
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as ex:
        futures = [ex.submit(run_one, item) for item in indexed]
        for done_count, fut in enumerate(as_completed(futures), 1):
            index, result = fut.result()
            completed.append((index, result))
            print(
                f"[{done_count}/{len(fixtures)}] {result['id']}: "
                f"{'PASS' if result['evaluation']['passed'] else 'FAIL'}",
                flush=True,
            )

    results = [result for _, result in sorted(completed, key=lambda x: x[0])]

    passed = sum(r["evaluation"]["passed"] for r in results)
    summary = {
        "model":args.model,
        "fixture_count":len(results),
        "passed":passed,
        "failed":len(results)-passed,
        "pass_rate":passed/len(results),
        "mode_accuracy":sum(r["evaluation"]["checks"].get("mode",False) for r in results)/len(results),
        "uncertainty_accuracy":sum(r["evaluation"]["checks"].get("uncertainty",False) for r in results)/len(results),
        "schema_valid_rate":sum(r["evaluation"]["checks"].get("schema_valid",False) for r in results)/len(results),
        "failed_ids":[r["id"] for r in results if not r["evaluation"]["passed"]]
    }

    out = ROOT / "artifacts/hcl-v03-state-fidelity"
    out.mkdir(parents=True, exist_ok=True)
    (out/"summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    with (out/"results.jsonl").open("w",encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r,ensure_ascii=False)+"\n")

    lines = [
        "# HCL v0.3 State Fidelity Report","",
        f"- Model: {args.model}",
        f"- Fixtures: **{len(results)}**",
        f"- Passed: **{passed}**",
        f"- Failed: **{len(results)-passed}**",
        f"- Pass rate: **{summary['pass_rate']:.1%}**",
        f"- Mode accuracy: **{summary['mode_accuracy']:.1%}**",
        f"- Uncertainty accuracy: **{summary['uncertainty_accuracy']:.1%}**",
        f"- Schema valid rate: **{summary['schema_valid_rate']:.1%}**","",
        "## Case results","",
        "| Case | Result | Mode | Uncertainty | Failures |",
        "|---|---|---|---|---|"
    ]
    for r in results:
        st = r["state"] or {}
        lines.append(
            f"| {r['id']} | {'PASS' if r['evaluation']['passed'] else 'FAIL'} | "
            f"{st.get('mode','?')} | {st.get('uncertainty',{}).get('level','?')} | "
            f"{', '.join(r['evaluation']['failures']) or '-'} |"
        )
    (out/"REPORT.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    print(json.dumps(summary,ensure_ascii=False,indent=2))
    return 0 if passed == len(results) else 3

if __name__ == "__main__":
    raise SystemExit(main())
