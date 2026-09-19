#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, os, sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from openai import OpenAI

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from run_cogtom_baseline import COGTOM_DIR, DEEPSEEK_BASE_URL, UPSTREAM_COMMIT, ensure_cogtom, read_jsonl, stratified_sample

ROUTER_SYSTEM = """You are a conservative routing module for a Human Cognition Layer.
Activate ONLY when the question materially requires nested belief/knowledge tracking,
information-access reasoning, or hidden-cause inference with multiple plausible causes.
Do not activate merely for emotion, persuasion, humor, preference, metaphor, or ordinary commonsense.
When uncertain, return false.
Return JSON only:
{"activate": true, "risk_type": "nested_belief|information_access|hidden_cause|none", "reason": "..."}"""

ANALYSIS_SYSTEM = """You are HCL v0.2's Epistemic Safeguard.
Do not answer the multiple-choice question.
Separate narrator truth from character knowledge; distinguish first- and second-order belief;
require an evidence path for information transfer; preserve multiple hidden causes when needed.
Return concise JSON only:
{"relevant_facts": [], "epistemic_access": [], "nested_beliefs": [], "competing_hypotheses": [], "underdetermined": false, "decision_note": "..."}"""

ANSWER_SYSTEM = """Use the supplied epistemic safeguard only as a correction aid.
Choose the best-supported option without inventing information transfer or hidden causes.
If the test forces one choice, prefer the option requiring the fewest unsupported assumptions.
Output ONLY [[A]], [[B]], [[C]], or [[D]]."""


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


def sequential_holdout(records, size, seed):
    first = stratified_sample(records, 200, 42)
    ids1 = {str(x["id"]) for x in first}
    rem1 = [r for r in records if str(r["id"]) not in ids1]
    second = stratified_sample(rem1, 100, 43)
    ids2 = {str(x["id"]) for x in second}
    rem2 = [r for r in rem1 if str(r["id"]) not in ids2]
    return stratified_sample(rem2, size, seed)


class Calls:
    def __init__(self, model):
        key = os.getenv("DEEPSEEK_API_KEY")
        if not key:
            raise RuntimeError("DEEPSEEK_API_KEY is required")
        self.client = OpenAI(api_key=key, base_url=DEEPSEEK_BASE_URL)
        self.model = model

    def raw(self, messages, max_tokens):
        for _ in range(4):
            r = self.client.chat.completions.create(
                model=self.model, messages=messages, temperature=0.0,
                max_tokens=max_tokens, seed=42
            )
            t = r.choices[0].message.content or ""
            if t.strip():
                return t
        return ""


def pack_metrics(xs):
    contents = [x["content"] for x in xs if x["content"] is not None]
    return {
        "group_accuracy": sum(x["correct"] for x in xs) / len(xs),
        "is_consistent": len(contents) == len(xs) and len(set(contents)) == 1,
    }


def process(calls, prompt_manager, evaluator, dataset, record):
    variants = dataset.gen_variants(record, var_num=5)
    vanilla = []
    for v in variants:
        raw = calls.raw(prompt_manager.build_messages(v), 8192)
        label = evaluator.extract(raw)
        vanilla.append({
            "label": label, "content": v["options"].get(label) if label else None,
            "gold": v["answer"], "correct": label == v["answer"], "raw": raw
        })

    route_raw = calls.raw([
        {"role": "system", "content": ROUTER_SYSTEM},
        {"role": "user", "content": "Scene:\\n" + record["scene"] + "\\n\\nQuestion:\\n" + record["question"]}
    ], 2048)
    route = extract_json(route_raw)
    activated = bool(route and route.get("activate") is True)

    if not activated:
        return make_row(record, vanilla, vanilla, activated, route, None, "router_no_activation")

    analysis_raw = calls.raw([
        {"role": "system", "content": ANALYSIS_SYSTEM},
        {"role": "user", "content": "Scene:\\n" + record["scene"] + "\\n\\nQuestion:\\n" + record["question"]}
    ], 4096)
    analysis = extract_json(analysis_raw)

    if analysis is None:
        return make_row(record, vanilla, vanilla, activated, route, None, "analysis_fail_open")

    state = json.dumps(analysis, ensure_ascii=False)
    hcl = []
    for v, base in zip(variants, vanilla):
        options = "\\n".join(f"{k}. {v['options'][k]}" for k in sorted(v["options"]))
        prompt = "Scene:\\n" + v["scene"] + "\\n\\nQuestion:\\n" + v["question"] + "\\n\\nOptions:\\n" + options + "\\n\\nEpistemic Safeguard:\\n" + state
        raw = calls.raw([{"role": "system", "content": ANSWER_SYSTEM}, {"role": "user", "content": prompt}], 8192)
        label = evaluator.extract(raw)
        if label is None:
            hcl.append(dict(base))
        else:
            hcl.append({
                "label": label, "content": v["options"].get(label),
                "gold": v["answer"], "correct": label == v["answer"], "raw": raw
            })

    return make_row(record, vanilla, hcl, activated, route, analysis, "active")


def make_row(record, vanilla, hcl, activated, route, analysis, path):
    vm, hm = pack_metrics(vanilla), pack_metrics(hcl)
    return {
        "id": record["id"], "category": record.get("category"), "subcategory": record.get("subcategory"),
        "activated": activated, "route": route, "analysis": analysis, "execution_path": path,
        "vanilla": vm, "hcl": hm, "delta": hm["group_accuracy"] - vm["group_accuracy"],
        "vanilla_details": vanilla, "hcl_details": hcl
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--model", default="deepseek-flash")
    p.add_argument("--language", default="zh")
    p.add_argument("--limit", type=int, default=40)
    p.add_argument("--seed", type=int, default=44)
    p.add_argument("--workers", type=int, default=6)
    args = p.parse_args()

    ensure_cogtom()
    sys.path.insert(0, str(COGTOM_DIR))
    from src.dataset import TomDataset
    from src.prompt import PromptManager
    from src.evaluator import Evaluator
    import yaml

    records = read_jsonl(COGTOM_DIR / "data" / f"CogToM-{args.language}.jsonl")
    selected = sequential_holdout(records, args.limit, args.seed)
    temp = ROOT / ".cache" / f"hcl-v02-{args.limit}-seed{args.seed}.jsonl"
    temp.parent.mkdir(parents=True, exist_ok=True)
    with temp.open("w", encoding="utf-8") as f:
        for row in selected:
            f.write(json.dumps(row, ensure_ascii=False) + "\\n")

    dataset = TomDataset(str(temp))
    cfg = yaml.safe_load((COGTOM_DIR / "configs" / "prompts" / f"vanilla-{args.language}.yaml").read_text(encoding="utf-8"))
    pm, ev, calls = PromptManager(**cfg), Evaluator(), Calls(args.model)

    rows = []
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        fs = [ex.submit(process, calls, pm, ev, dataset, r) for r in selected]
        for i, fut in enumerate(as_completed(fs), 1):
            rows.append(fut.result())
            print(f"completed {i}/{len(fs)}", flush=True)

    rows.sort(key=lambda x: str(x["id"]))
    n = len(rows)
    summary = {
        "groups": n,
        "activated_groups": sum(r["activated"] for r in rows),
        "activation_rate": sum(r["activated"] for r in rows) / n,
        "vanilla_mean_group_accuracy": sum(r["vanilla"]["group_accuracy"] for r in rows) / n,
        "hcl_mean_group_accuracy": sum(r["hcl"]["group_accuracy"] for r in rows) / n,
        "vanilla_strict_correct_rate": sum(r["vanilla"]["group_accuracy"] == 1 for r in rows) / n,
        "hcl_strict_correct_rate": sum(r["hcl"]["group_accuracy"] == 1 for r in rows) / n,
        "vanilla_consistency_rate": sum(r["vanilla"]["is_consistent"] for r in rows) / n,
        "hcl_consistency_rate": sum(r["hcl"]["is_consistent"] for r in rows) / n,
        "improved_groups": sum(r["delta"] > 0 for r in rows),
        "harmed_groups": sum(r["delta"] < 0 for r in rows),
        "changed_items": [
            {"id": r["id"], "category": r["category"], "subcategory": r["subcategory"],
             "delta": r["delta"], "route": r["route"]}
            for r in rows if r["delta"] != 0
        ]
    }
    summary["delta_mean_group_accuracy"] = summary["hcl_mean_group_accuracy"] - summary["vanilla_mean_group_accuracy"]

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = ROOT / "artifacts" / f"hcl-v0.2_{args.model}_{args.language}_fresh-{args.limit}_seed{args.seed}_{stamp}"
    out.mkdir(parents=True, exist_ok=True)
    with (out / "raw.jsonl").open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\\n")
    (out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\\n", encoding="utf-8")
    (out / "metadata.json").write_text(json.dumps({
        "method": "HCL v0.2 Selective Epistemic Safeguard",
        "base_model": args.model, "language": args.language,
        "seed": args.seed, "excluded_prior_groups": 300,
        "cogtom_commit": UPSTREAM_COMMIT
    }, ensure_ascii=False, indent=2) + "\\n", encoding="utf-8")

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"Artifacts: {out}")


if __name__ == "__main__":
    main()
