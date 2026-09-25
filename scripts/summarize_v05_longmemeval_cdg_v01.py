#!/usr/bin/env python3
"""Provider-free paired summary of frozen LongMemEval C/D/G judge labels."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.preflight_v05_longmemeval_cdg_v01 import validate_manifest
from scripts.score_v05_longmemeval_cdg_v01 import validate_answers

BOOTSTRAP_SEED = 20260925
BOOTSTRAP_DRAWS = 10000


class SummaryError(ValueError):
    pass


def exact_mcnemar_p(d_only: int, g_only: int) -> float:
    discordant = d_only + g_only
    if discordant == 0:
        return 1.0
    tail = sum(math.comb(discordant, i) for i in range(min(d_only, g_only) + 1))
    return min(1.0, 2.0 * tail / (2 ** discordant))


def paired_bootstrap_interval(differences: list[int]) -> tuple[float, float]:
    if not differences:
        raise SummaryError("no paired outcomes")
    rng = random.Random(BOOTSTRAP_SEED)
    n = len(differences)
    means = sorted(sum(differences[rng.randrange(n)] for _ in range(n)) / n
                   for _ in range(BOOTSTRAP_DRAWS))
    return means[249], means[9749]


def summarize(raw: dict, judged: dict, selected: list[dict]) -> dict:
    validate_answers(raw, selected)
    if judged.get("format") != "hcl-v05-longmemeval-cdg-judge-v01" or judged.get("status") != "complete":
        raise SummaryError("judge results incomplete")
    ids = [x["question_id"] for x in selected]
    if [x.get("question_id") for x in judged.get("rows", [])] != ids:
        raise SummaryError("judge row order or identity drift")
    if judged.get("attempted_ids") != ids:
        raise SummaryError("judge attempted IDs mismatch")
    paired = []
    for qid, row in zip(ids, judged["rows"]):
        judgments = row.get("judgments")
        if not isinstance(judgments, dict) or set(judgments) != {"C", "D", "G"}:
            raise SummaryError("missing paired judgment")
        labels = {}
        for arm in ("C", "D", "G"):
            item = judgments[arm]
            if not isinstance(item.get("label"), bool):
                raise SummaryError("judge label must be Boolean")
            labels[arm] = item["label"]
        paired.append({"question_id": qid, "abstention": qid.endswith("_abs"),
                       "labels": labels,
                       "judge_ambiguous": {arm: bool(judgments[arm].get("ambiguous"))
                                           for arm in ("C", "D", "G")}})
    scores = {arm: sum(row["labels"][arm] for row in paired) for arm in ("C", "D", "G")}
    d_only = sum(row["labels"]["D"] and not row["labels"]["G"] for row in paired)
    g_only = sum(row["labels"]["G"] and not row["labels"]["D"] for row in paired)
    d_c_only = sum(row["labels"]["D"] and not row["labels"]["C"] for row in paired)
    c_d_only = sum(row["labels"]["C"] and not row["labels"]["D"] for row in paired)
    ci = paired_bootstrap_interval([int(row["labels"]["D"]) - int(row["labels"]["G"])
                                    for row in paired])
    backend = raw.get("backend", {})
    chars = {}
    wall = {}
    for arm in ("C", "D", "G"):
        meter = backend.get(arm, {})
        chars[arm] = int(meter.get("input_chars", 0)) + int(meter.get("output_chars", 0))
        wall[arm] = float(meter.get("provider_wall_seconds", 0.0))
    if chars["G"] <= 0 or wall["G"] <= 0:
        raise SummaryError("missing G cost denominator")
    severe_d = any(row.get("d_ingest", {}).get("semantic_failures", 0) for row in raw["rows"])
    g_loss = any(row.get("g_ingest", {}).get("events") != row.get("d_ingest", {}).get("events")
                 for row in raw["rows"])
    p = exact_mcnemar_p(d_only, g_only)
    capability = scores["D"] - scores["G"] >= 5 and p <= 0.05 and not severe_d and not g_loss
    practical = (scores["D"] >= scores["G"] - 1 and not severe_d and
                 chars["D"] <= 0.6 * chars["G"] and wall["D"] <= 0.6 * wall["G"])
    return {"format": "hcl-v05-longmemeval-cdg-summary-v01",
            "selected_count": len(ids), "scores": scores,
            "d_only_g": d_only, "g_only_d": g_only,
            "d_only_c": d_c_only, "c_only_d": c_d_only,
            "exact_mcnemar_d_g_two_sided_p": p,
            "paired_bootstrap_d_g_95pct": list(ci),
            "bootstrap_seed": BOOTSTRAP_SEED, "bootstrap_draws": BOOTSTRAP_DRAWS,
            "provider_chars": chars, "provider_wall_seconds": wall,
            "d_to_g_char_ratio": chars["D"] / chars["G"],
            "d_to_g_wall_ratio": wall["D"] / wall["G"],
            "capability_signal_gate": capability,
            "answer_quality_improvement_claim_allowed": capability and scores["D"] > scores["C"],
            "practical_utility_gate": practical,
            "claim_boundary": "Oracle-evidence-assisted knowledge-update only; judge variance and discordant raw answers require review.",
            "paired": paired}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-answers", type=Path, required=True)
    parser.add_argument("--judge-results", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    _, selected = validate_manifest()
    raw_bytes = args.raw_answers.read_bytes()
    judged = json.loads(args.judge_results.read_text(encoding="utf-8"))
    if judged.get("raw_answers_sha256") != hashlib.sha256(raw_bytes).hexdigest():
        raise SummaryError("judge inputs differ from frozen raw answers")
    summary = summarize(json.loads(raw_bytes), judged, selected)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k != "paired"}, sort_keys=True))


if __name__ == "__main__":
    main()
