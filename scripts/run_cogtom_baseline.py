#!/usr/bin/env python3
"""Run the official CogToM benchmark against DeepSeek without modifying its prompts or evaluator.

Phase-0 wrapper responsibilities:
- pin the upstream benchmark revision;
- select a reproducible evaluation subset;
- use CogToM's original prompt/evaluator/pipeline;
- supply an OpenAI-compatible DeepSeek model config;
- write reproducible artifacts for manual error analysis.

The default subset is stratified by (category, subcategory) because CogToM's
JSONL is ordered; using upstream --limit alone would over-sample early paradigms.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import shutil
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / ".cache"
COGTOM_DIR = CACHE / "CogToM"
UPSTREAM_URL = "https://github.com/Beijing-AISI/CogToM.git"
UPSTREAM_COMMIT = "28c6781b6ea7d7ef7d491f61adc18f076f8b993c"
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
SUPPORTED_MODELS = ("deepseek-flash", "deepseek-v4-pro")


def run(cmd: list[str], *, cwd: Path | None = None, env: dict[str, str] | None = None) -> None:
    print("+ " + " ".join(cmd), flush=True)
    subprocess.run(cmd, cwd=cwd, env=env, check=True)


def ensure_cogtom() -> None:
    CACHE.mkdir(parents=True, exist_ok=True)
    if not COGTOM_DIR.exists():
        run(["git", "clone", "--quiet", UPSTREAM_URL, str(COGTOM_DIR)])

    run(["git", "fetch", "--quiet", "origin"], cwd=COGTOM_DIR)
    run(["git", "checkout", "--quiet", "--detach", UPSTREAM_COMMIT], cwd=COGTOM_DIR)

    actual = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=COGTOM_DIR, text=True
    ).strip()
    if actual != UPSTREAM_COMMIT:
        raise RuntimeError(f"CogToM revision mismatch: {actual} != {UPSTREAM_COMMIT}")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def stratified_sample(records: list[dict[str, Any]], size: int, seed: int) -> list[dict[str, Any]]:
    """Round-robin sample across CogToM paradigms with deterministic shuffling."""
    if size <= 0 or size >= len(records):
        return records.copy()

    rng = random.Random(seed)
    buckets: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in records:
        key = (str(row.get("category", "unknown")), str(row.get("subcategory", "unknown")))
        buckets[key].append(row)

    for bucket in buckets.values():
        rng.shuffle(bucket)

    keys = sorted(buckets)
    selected: list[dict[str, Any]] = []
    cursor = {key: 0 for key in keys}

    while len(selected) < size:
        progressed = False
        for key in keys:
            idx = cursor[key]
            bucket = buckets[key]
            if idx >= len(bucket):
                continue
            selected.append(bucket[idx])
            cursor[key] += 1
            progressed = True
            if len(selected) >= size:
                break
        if not progressed:
            break

    # Randomize evaluation order while preserving the selected composition.
    rng.shuffle(selected)
    return selected


def prepare_dataset(
    language: str,
    size: int,
    seed: int,
    sampling: str,
    exclude_size: int = 0,
    exclude_seed: int = 42,
) -> tuple[Path, Path, dict[str, Any]]:
    source = COGTOM_DIR / "data" / f"CogToM-{language}.jsonl"
    records = read_jsonl(source)

    excluded_ids: set[str] = set()
    if exclude_size > 0:
        excluded = stratified_sample(records, size=exclude_size, seed=exclude_seed)
        excluded_ids = {str(r.get("id")) for r in excluded}
        records = [r for r in records if str(r.get("id")) not in excluded_ids]

    if sampling == "head":
        selected = records if size <= 0 else records[:size]
    elif sampling == "stratified":
        selected = stratified_sample(records, size=size, seed=seed)
    else:
        raise ValueError(f"Unsupported sampling strategy: {sampling}")

    sample_name = f"hcl-{language}-{sampling}-{len(selected)}-seed{seed}.jsonl"
    sample_path = COGTOM_DIR / "data" / sample_name
    with sample_path.open("w", encoding="utf-8") as f:
        for row in selected:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    config_path = COGTOM_DIR / "configs" / "datasets" / "hcl-sample.yaml"
    config_path.write_text(
        'dataset_type: "TomDataset"\n'
        f'file_path: "./data/{sample_name}"\n'
        "limit: -1\n",
        encoding="utf-8",
    )

    strata = defaultdict(int)
    categories = defaultdict(int)
    for row in selected:
        categories[str(row.get("category", "unknown"))] += 1
        strata[(str(row.get("category", "unknown")), str(row.get("subcategory", "unknown")))] += 1

    sampling_meta = {
        "strategy": sampling,
        "source_groups": len(records),
        "selected_groups": len(selected),
        "selected_categories": dict(sorted(categories.items())),
        "selected_subcategory_count": len(strata),
        "seed": seed,
        "excluded_groups": len(excluded_ids),
        "exclude_seed": exclude_seed if excluded_ids else None,
    }
    return sample_path, config_path, sampling_meta


def write_llm_config(model: str) -> Path:
    config = COGTOM_DIR / "configs" / "llms" / "hcl-deepseek.yaml"
    config.write_text(
        f'llm_type: "OpenAILLM"\nmodel_name: "{model}"\n',
        encoding="utf-8",
    )
    return config


def write_gen_config(max_tokens: int, seed: int) -> Path:
    """Provider-specific decoding budget; DeepSeek thinking is enabled by default."""
    config = COGTOM_DIR / "configs" / "hcl-deepseek-gen.yaml"
    config.write_text(
        "temperature: 0.0\n"
        f"max_tokens: {max_tokens}\n"
        f"seed: {seed}\n",
        encoding="utf-8",
    )
    return config


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", choices=SUPPORTED_MODELS, default="deepseek-flash")
    parser.add_argument("--language", choices=("zh", "en"), default="zh")
    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Number of CogToM question groups. Each group is evaluated with 5 option-order variants.",
    )
    parser.add_argument(
        "--sampling",
        choices=("stratified", "head"),
        default="stratified",
        help="Subset selection. Stratified is the research default; head exists only for debugging.",
    )
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument(
        "--exclude-size",
        type=int,
        default=0,
        help="Exclude a deterministic stratified sample before selecting this run (for disjoint holdouts).",
    )
    parser.add_argument("--exclude-seed", type=int, default=42)
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=8192,
        help="Completion budget. DeepSeek thinking tokens share this budget; 2048 can truncate hard items.",
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--run-name", default=None)
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    key = os.getenv("DEEPSEEK_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not key:
        print(
            "Missing DEEPSEEK_API_KEY. Add it as an environment variable or GitHub repository secret.",
            file=sys.stderr,
        )
        return 2

    ensure_cogtom()
    (COGTOM_DIR / "results").mkdir(exist_ok=True)
    (COGTOM_DIR / "logs").mkdir(exist_ok=True)

    llm_config = write_llm_config(args.model)
    gen_config = write_gen_config(args.max_tokens, args.seed)
    sample_path, dataset_config, sampling_meta = prepare_dataset(
        language=args.language,
        size=args.limit,
        seed=args.seed,
        sampling=args.sampling,
        exclude_size=args.exclude_size,
        exclude_seed=args.exclude_seed,
    )
    prompt = f"configs/prompts/vanilla-{args.language}.yaml"

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    safe_model = args.model.replace("/", "-")
    run_name = args.run_name or (
        f"{safe_model}_vanilla-{args.language}_{args.sampling}-{sampling_meta['selected_groups']}_{stamp}"
    )

    env = os.environ.copy()
    env["OPENAI_API_KEY"] = key
    env["OPENAI_BASE_URL"] = DEEPSEEK_BASE_URL

    cmd = [
        sys.executable,
        "main.py",
        "--llm-config",
        str(llm_config.relative_to(COGTOM_DIR)),
        "--prompt-config",
        prompt,
        "--gen-config",
        str(gen_config.relative_to(COGTOM_DIR)),
        "--dataset-config",
        str(dataset_config.relative_to(COGTOM_DIR)),
        "--run-name",
        run_name,
        "--limit",
        "-1",
        "--workers",
        str(args.workers),
        "--seed",
        str(args.seed),
    ]
    if args.force:
        cmd.append("--force")

    run(cmd, cwd=COGTOM_DIR, env=env)

    raw = COGTOM_DIR / "results" / f"{run_name}.jsonl"
    if not raw.exists():
        raise FileNotFoundError(f"Expected CogToM result was not created: {raw}")

    artifact_dir = ROOT / "artifacts" / run_name
    artifact_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(raw, artifact_dir / "raw.jsonl")

    metadata = {
        "run_name": run_name,
        "timestamp_utc": stamp,
        "provider": "DeepSeek",
        "model": args.model,
        "base_url": DEEPSEEK_BASE_URL,
        "language": args.language,
        "requested_groups": args.limit,
        "actual_groups": sampling_meta["selected_groups"],
        "variants_per_group": 5,
        "workers": args.workers,
        "max_tokens": args.max_tokens,
        "deepseek_thinking_mode": "default_enabled",
        "seed": args.seed,
        "prompt": f"vanilla-{args.language}",
        "sampling": sampling_meta,
        "cogtom_repository": UPSTREAM_URL,
        "cogtom_commit": UPSTREAM_COMMIT,
    }
    (artifact_dir / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    run(
        [
            sys.executable,
            str(ROOT / "scripts" / "summarize_cogtom.py"),
            "--results",
            str(artifact_dir / "raw.jsonl"),
            "--dataset",
            str(sample_path),
            "--metadata",
            str(artifact_dir / "metadata.json"),
            "--output-dir",
            str(artifact_dir),
        ],
        cwd=ROOT,
    )

    print(f"\nArtifacts: {artifact_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
