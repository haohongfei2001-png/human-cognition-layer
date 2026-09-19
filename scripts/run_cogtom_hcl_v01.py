#!/usr/bin/env python3
"""Evaluate HCL v0.1 as a portable external cognition layer on CogToM.

No model weights are modified.

For each CogToM group:
1. HCL analysis pass (scene + question, no answer key and no options);
2. the same base model receives the HCL state plus each official option permutation;
3. scoring uses CogToM's official Evaluator.

The HCL analysis is computed once per group and reused across all five option
permutations, keeping the module portable and relatively cheap.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
import threading
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from openai import OpenAI

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from run_cogtom_baseline import (  # noqa: E402
    COGTOM_DIR,
    DEEPSEEK_BASE_URL,
    UPSTREAM_COMMIT,
    UPSTREAM_URL,
    ensure_cogtom,
    read_jsonl,
    stratified_sample,
)

HCL_SYSTEM = """You are the Human Cognition Layer v0.1.
Your job is not to answer the multiple-choice question. Build a compact epistemic state.

Strict rules:
1. Separate narrator/world truth from what each character actually observed.
2. Track first-order beliefs separately from second-order beliefs.
3. Never assume information transfer without an explicit or strongly supported evidence path.
4. When an observed outcome has multiple possible hidden causes, keep multiple hypotheses alive.
5. Distinguish plausible from established.
6. Mark missing evidence bridges and underdetermination.

Return JSON only with this schema:
{
  "explicit_facts": ["..."],
  "agents": {
    "name": {
      "observed": ["..."],
      "knows_or_strongly_supported": ["..."],
      "believes_or_may_believe": ["..."],
      "beliefs_about_others": ["..."]
    }
  },
  "candidate_interpretations": [
    {
      "hypothesis": "...",
      "support": ["..."],
      "counterevidence_or_missing_bridge": ["..."],
      "confidence": 0.0
    }
  ],
  "underdetermined": true,
  "missing_bridges": ["..."]
}
Do not invent facts that are not in the scene.
"""

ANSWER_SYSTEM = """You are answering a CogToM multiple-choice item.
Use the supplied HCL epistemic state as an external reasoning aid.
Choose the best-supported option from the story. Do not invent hidden information transfer.
If the situation is underdetermined but the test forces one option, select the option requiring
the fewest unsupported assumptions.
Output ONLY [[A]], [[B]], [[C]], or [[D]].
"""


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--model", default="deepseek-flash")
    p.add_argument("--language", choices=("zh", "en"), default="zh")
    p.add_argument("--limit", type=int, default=100)
    p.add_argument("--seed", type=int, default=43)
    p.add_argument("--exclude-size", type=int, default=200)
    p.add_argument("--exclude-seed", type=int, default=42)
    p.add_argument("--workers", type=int, default=8)
    p.add_argument("--analysis-max-tokens", type=int, default=4096)
    p.add_argument("--answer-max-tokens", type=int, default=8192)
    return p.parse_args()


def build_holdout(language: str, size: int, seed: int, exclude_size: int, exclude_seed: int) -> list[dict[str, Any]]:
    source = COGTOM_DIR / "data" / f"CogToM-{language}.jsonl"
    records = read_jsonl(source)
    excluded = stratified_sample(records, size=exclude_size, seed=exclude_seed)
    excluded_ids = {str(r.get("id")) for r in excluded}
    remaining = [r for r in records if str(r.get("id")) not in excluded_ids]
    return stratified_sample(remaining, size=size, seed=seed)


def format_options(options: dict[str, str]) -> str:
    return "\n".join(f"{k}. {options[k]}" for k in sorted(options))


def extract_label(text: str) -> str | None:
    import re
    patterns = [
        r"\[\[([A-D])\]\]",
        r"(?:答案|Answer|Choice|Option)\s*[:：\-\s]*([A-D])\b",
        r"\b([A-D])[\.\)]?\s*$",
    ]
    for pattern in patterns:
        m = re.findall(pattern, text or "", flags=re.IGNORECASE | re.DOTALL)
        if m:
            return m[-1].upper()
    return None


class Runner:
    def __init__(self, model: str, analysis_max_tokens: int, answer_max_tokens: int):
        key = os.getenv("DEEPSEEK_API_KEY")
        if not key:
            raise RuntimeError("DEEPSEEK_API_KEY is required")
        self.client = OpenAI(api_key=key, base_url=DEEPSEEK_BASE_URL)
        self.model = model
        self.analysis_max_tokens = analysis_max_tokens
        self.answer_max_tokens = answer_max_tokens
        self.lock = threading.Lock()

    def call(self, messages: list[dict[str, str]], max_tokens: int) -> str:
        last = ""
        for _ in range(4):
            r = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.0,
                max_tokens=max_tokens,
                seed=42,
            )
            last = r.choices[0].message.content or ""
            if last.strip():
                return last
        return last

    def analyze(self, record: dict[str, Any]) -> str:
        language_hint = "Use Chinese for string values." if any("\u4e00" <= ch <= "\u9fff" for ch in record["scene"]) else ""
        prompt = f"""情境 / Scene:
{record['scene']}

问题 / Question:
{record['question']}

{language_hint}
Build the epistemic state. Do NOT choose an option and do NOT infer from any hidden answer key."""
        return self.call(
            [
                {"role": "system", "content": HCL_SYSTEM},
                {"role": "user", "content": prompt},
            ],
            self.analysis_max_tokens,
        )

    def answer(self, record: dict[str, Any], hcl_state: str) -> tuple[str | None, str]:
        prompt = f"""【情境】
{record['scene']}

【问题】
{record['question']}

【选项】
{format_options(record['options'])}

【HCL v0.1 外部认知状态】
{hcl_state}

根据情境和 HCL 状态选择最有依据的选项。只输出 [[选项字母]]。"""
        raw = self.call(
            [
                {"role": "system", "content": ANSWER_SYSTEM},
                {"role": "user", "content": prompt},
            ],
            self.answer_max_tokens,
        )
        return extract_label(raw), raw


def process_group(runner: Runner, dataset, record: dict[str, Any]) -> dict[str, Any]:
    state = runner.analyze(record)
    variants = dataset.gen_variants(record, var_num=5)
    details = []
    contents = []
    correct = 0

    for variant in variants:
        label, raw = runner.answer(variant, state)
        gold = variant["answer"]
        ok = label == gold
        if ok:
            correct += 1
        content = variant["options"].get(label) if label else None
        if content is not None:
            contents.append(content)
        details.append(
            {
                "meta_info": variant.get("meta_info", {}),
                "permuted_answer": gold,
                "extracted_label": label,
                "extracted_content": content,
                "is_correct": ok,
                "raw_output": raw,
            }
        )

    consistent = len(contents) == len(variants) and len(set(contents)) == 1
    return {
        "id": record["id"],
        "category": record.get("category", "unknown"),
        "subcategory": record.get("subcategory"),
        "group_accuracy": correct / len(variants),
        "is_consistent": consistent,
        "variant_count": len(variants),
        "hcl_state": state,
        "details": details,
    }


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    cat = defaultdict(list)
    sub = defaultdict(list)
    for r in rows:
        a = float(r["group_accuracy"])
        cat[str(r.get("category"))].append(a)
        sub[str(r.get("subcategory"))].append(a)
    return {
        "groups": len(rows),
        "mean_group_accuracy": sum(float(r["group_accuracy"]) for r in rows) / len(rows),
        "strict_all_variants_correct_rate": sum(float(r["group_accuracy"]) == 1.0 for r in rows) / len(rows),
        "semantic_consistency_rate": sum(bool(r["is_consistent"]) for r in rows) / len(rows),
        "groups_with_any_error": sum(float(r["group_accuracy"]) < 1.0 for r in rows),
        "category_accuracy": {k: sum(v) / len(v) for k, v in sorted(cat.items())},
        "subcategory_accuracy": {k: sum(v) / len(v) for k, v in sorted(sub.items())},
    }


def main() -> int:
    args = parse_args()
    ensure_cogtom()
    sys.path.insert(0, str(COGTOM_DIR))
    from src.dataset import TomDataset  # type: ignore

    holdout = build_holdout(
        args.language, args.limit, args.seed, args.exclude_size, args.exclude_seed
    )

    # Use TomDataset only for the official option-variant generation logic.
    temp = ROOT / ".cache" / f"hcl-holdout-{args.language}-{args.limit}-seed{args.seed}.jsonl"
    temp.parent.mkdir(parents=True, exist_ok=True)
    with temp.open("w", encoding="utf-8") as f:
        for row in holdout:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    dataset = TomDataset(str(temp))

    runner = Runner(args.model, args.analysis_max_tokens, args.answer_max_tokens)
    rows: list[dict[str, Any]] = []

    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futures = {ex.submit(process_group, runner, dataset, r): r["id"] for r in holdout}
        for i, future in enumerate(as_completed(futures), 1):
            rows.append(future.result())
            print(f"completed {i}/{len(futures)}", flush=True)

    # Sort for stable artifacts.
    rows.sort(key=lambda r: str(r["id"]))
    summary = summarize(rows)

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = ROOT / "artifacts" / f"hcl-v0.1_{args.model}_{args.language}_holdout-{args.limit}_seed{args.seed}_{stamp}"
    out.mkdir(parents=True, exist_ok=True)

    with (out / "raw.jsonl").open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    meta = {
        "method": "HCL v0.1 Epistemic Uncertainty Layer",
        "base_model": args.model,
        "language": args.language,
        "groups": args.limit,
        "variants_per_group": 5,
        "seed": args.seed,
        "excluded_design_groups": args.exclude_size,
        "exclude_seed": args.exclude_seed,
        "analysis_max_tokens": args.analysis_max_tokens,
        "answer_max_tokens": args.answer_max_tokens,
        "cogtom_commit": UPSTREAM_COMMIT,
        "cogtom_repository": UPSTREAM_URL,
    }
    (out / "metadata.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    errors = [r for r in rows if float(r["group_accuracy"]) < 1.0]
    with (out / "errors.jsonl").open("w", encoding="utf-8") as f:
        for r in errors:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(json.dumps({"metadata": meta, **summary}, ensure_ascii=False, indent=2))
    print(f"Artifacts: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
