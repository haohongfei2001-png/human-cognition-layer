#!/usr/bin/env python3
"""Run the official CogToM benchmark against DeepSeek without modifying CogToM.

This wrapper intentionally keeps Phase 0 minimal:
- pins the upstream benchmark revision;
- uses CogToM's original prompts/evaluator;
- only supplies an OpenAI-compatible DeepSeek model config;
- writes reproducible artifacts for later manual error analysis.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / ".cache"
COGTOM_DIR = CACHE / "CogToM"
UPSTREAM_URL = "https://github.com/Beijing-AISI/CogToM.git"
UPSTREAM_COMMIT = "28c6781b6ea7d7ef7d491f61adc18f076f8b993c"
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
SUPPORTED_MODELS = ("deepseek-flash", "deepseek-v4-pro")


def run(cmd: list[str], *, cwd: Path | None = None, env: dict[str, str] | None = None) -> None:
    printable = " ".join(cmd)
    print(f"+ {printable}", flush=True)
    subprocess.run(cmd, cwd=cwd, env=env, check=True)


def ensure_cogtom() -> None:
    CACHE.mkdir(parents=True, exist_ok=True)
    if not COGTOM_DIR.exists():
        run(["git", "clone", "--quiet", UPSTREAM_URL, str(COGTOM_DIR)])

    # Always pin the benchmark to the recorded revision.
    run(["git", "fetch", "--quiet", "origin"], cwd=COGTOM_DIR)
    run(["git", "checkout", "--quiet", "--detach", UPSTREAM_COMMIT], cwd=COGTOM_DIR)

    actual = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=COGTOM_DIR, text=True
    ).strip()
    if actual != UPSTREAM_COMMIT:
        raise RuntimeError(f"CogToM revision mismatch: {actual} != {UPSTREAM_COMMIT}")


def write_llm_config(model: str) -> Path:
    config = COGTOM_DIR / "configs" / "llms" / "hcl-deepseek.yaml"
    config.write_text(
        f'llm_type: "OpenAILLM"\nmodel_name: "{model}"\n',
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
    parser.add_argument("--workers", type=int, default=4)
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

    # CogToM requires these directories to exist.
    (COGTOM_DIR / "results").mkdir(exist_ok=True)
    (COGTOM_DIR / "logs").mkdir(exist_ok=True)

    config_path = write_llm_config(args.model)
    prompt = f"configs/prompts/vanilla-{args.language}.yaml"
    dataset = f"configs/datasets/cogtom-{args.language}.yaml"

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    safe_model = args.model.replace("/", "-")
    run_name = args.run_name or f"{safe_model}_vanilla-{args.language}_{args.limit}_{stamp}"

    env = os.environ.copy()
    env["OPENAI_API_KEY"] = key
    env["OPENAI_BASE_URL"] = DEEPSEEK_BASE_URL

    cmd = [
        sys.executable,
        "main.py",
        "--llm-config",
        str(config_path.relative_to(COGTOM_DIR)),
        "--prompt-config",
        prompt,
        "--dataset-config",
        dataset,
        "--run-name",
        run_name,
        "--limit",
        str(args.limit),
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
        "limit_groups": args.limit,
        "variants_per_group": 5,
        "workers": args.workers,
        "seed": args.seed,
        "prompt": f"vanilla-{args.language}",
        "cogtom_repository": UPSTREAM_URL,
        "cogtom_commit": UPSTREAM_COMMIT,
    }
    (artifact_dir / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    dataset_path = COGTOM_DIR / "data" / f"CogToM-{args.language}.jsonl"
    run(
        [
            sys.executable,
            str(ROOT / "scripts" / "summarize_cogtom.py"),
            "--results",
            str(artifact_dir / "raw.jsonl"),
            "--dataset",
            str(dataset_path),
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
