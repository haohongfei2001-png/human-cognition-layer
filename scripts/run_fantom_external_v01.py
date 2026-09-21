#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in os.sys.path:
    os.sys.path.insert(0, str(ROOT))

from hcl.v03.answer_loop import HCLAnswerLoop
from hcl.v03.backends import OpenAICompatibleBackend
from scripts.inventory_fantom_external_v01 import (
    SALT,
    accessibility,
    download_verified,
    load_dataframe,
    make_key,
    sha,
    tom_order,
)

SELECTION_FILE = ROOT / "eval/fantom/selection_v01.json"

MODEL = "deepseek-flash"
BASE_URL = "https://api.deepseek.com"
SEED = 42
TEMPERATURE = 0.0
DIRECT_MAX_TOKENS = 4096

CONTROL_SYSTEM = (
    "Answer the user's benchmark request directly. Follow its requested output "
    "format exactly and do not add an explanation."
)


def response_meta(text: str) -> dict[str, Any]:
    encoded = text.encode("utf-8")
    return {
        "response_bytes": len(encoded),
        "response_sha256": hashlib.sha256(encoded).hexdigest(),
    }


def token_f1(reference: str, prediction: str) -> float:
    gold = reference.lower().split()
    pred = prediction.lower().split()
    if not gold and not pred:
        return 1.0
    if not gold or not pred:
        return 0.0
    common = Counter(gold) & Counter(pred)
    same = sum(common.values())
    if same == 0:
        return 0.0
    precision = same / len(pred)
    recall = same / len(gold)
    return 2 * precision * recall / (precision + recall)


def parse_mc(text: str) -> str | None:
    bracketed = re.findall(r"\[\s*([ABab])\s*\]", text)
    unique = {x.upper() for x in bracketed}
    if len(unique) == 1:
        return next(iter(unique))
    if len(unique) > 1:
        return None

    match = re.match(
        r"^\s*(?:answer\s*:\s*)?\(?\s*([ABab])\s*\)?(?:\s|[\.,:;]|$)",
        text,
        flags=re.IGNORECASE,
    )
    return match.group(1).upper() if match else None


def parse_binary(text: str) -> str | None:
    match = re.match(
        r"^\s*(?:answer\s*:\s*)?(yes|no|true|false)\b",
        text,
        flags=re.IGNORECASE,
    )
    if not match:
        return None
    value = match.group(1).lower()
    return "yes" if value in {"yes", "true"} else "no"


def load_selection() -> dict[str, Any]:
    return json.loads(SELECTION_FILE.read_text(encoding="utf-8"))


def build_question_map(df: Any) -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}

    for _, row in df.iterrows():
        set_id = str(row["set_id"])
        context = str(row["short_context"]).strip()

        fact = row.get("factQA")
        if isinstance(fact, dict) and fact.get("question") is not None:
            q = str(fact["question"])
            key = make_key(
                set_id=set_id,
                family="fact",
                question=q,
                ordinal_in_family=0,
            )
            records[key] = {
                "question_id": key,
                "set_id": set_id,
                "family": "fact",
                "context": context,
                "question": q,
                "correct_answer": str(fact.get("correct_answer", "")),
            }

        beliefs = row.get("beliefQAs")
        if isinstance(beliefs, list):
            for idx, qa in enumerate(beliefs):
                if not isinstance(qa, dict) or qa.get("question") is None:
                    continue
                q = str(qa["question"])
                key = make_key(
                    set_id=set_id,
                    family="belief_mc",
                    question=q,
                    ordinal_in_family=idx,
                )
                records[key] = {
                    "question_id": key,
                    "set_id": set_id,
                    "family": "belief_mc",
                    "context": context,
                    "question": q,
                    "correct_answer": str(qa.get("correct_answer", "")),
                    "wrong_answer": str(qa.get("wrong_answer", "")),
                    "accessibility": accessibility(qa),
                    "tom_order": tom_order(qa),
                }

        answerability = row.get("answerabilityQAs_binary")
        if isinstance(answerability, list):
            fact_question = (
                str(fact.get("question", "")) if isinstance(fact, dict) else ""
            )
            for idx, qa in enumerate(answerability):
                if not isinstance(qa, dict) or qa.get("question") is None:
                    continue
                q = str(qa["question"])
                key = make_key(
                    set_id=set_id,
                    family="answerability_binary",
                    question=q,
                    ordinal_in_family=idx,
                )
                records[key] = {
                    "question_id": key,
                    "set_id": set_id,
                    "family": "answerability_binary",
                    "context": context,
                    "question": q,
                    "target": fact_question,
                    "correct_answer": str(qa.get("correct_answer", "")).lower(),
                    "accessibility": accessibility(qa),
                }

        info_access = row.get("infoAccessibilityQAs_binary")
        if isinstance(info_access, list):
            fact_question = (
                str(fact.get("question", "")) if isinstance(fact, dict) else ""
            )
            fact_answer = (
                str(fact.get("correct_answer", "")) if isinstance(fact, dict) else ""
            )
            for idx, qa in enumerate(info_access):
                if not isinstance(qa, dict) or qa.get("question") is None:
                    continue
                q = str(qa["question"])
                key = make_key(
                    set_id=set_id,
                    family="info_accessibility_binary",
                    question=q,
                    ordinal_in_family=idx,
                )
                records[key] = {
                    "question_id": key,
                    "set_id": set_id,
                    "family": "info_accessibility_binary",
                    "context": context,
                    "question": q,
                    "information_question": fact_question,
                    "information_answer": fact_answer,
                    "correct_answer": str(qa.get("correct_answer", "")).lower(),
                    "accessibility": accessibility(qa),
                }

    return records


def belief_orientation(question_id: str) -> str:
    return "A" if int(sha(SALT + "|choice|" + question_id), 16) % 2 == 0 else "B"


def build_prompt(record: dict[str, Any], manifest: dict[str, Any]) -> str:
    context = record["context"]
    question = record["question"]
    family = record["family"]

    if family == "belief_mc":
        expected_orientation = belief_orientation(record["question_id"])
        if expected_orientation != manifest["correct_option"]:
            raise RuntimeError(
                f"Belief option orientation drift for {record['question_id']}"
            )
        if manifest["correct_option"] == "A":
            option_a = record["correct_answer"]
            option_b = record["wrong_answer"]
        else:
            option_a = record["wrong_answer"]
            option_b = record["correct_answer"]

        task = (
            f"Conversation:\n{context}\n\n"
            f"Question:\n{question}\n\n"
            f"Options:\n[A] {option_a}\n[B] {option_b}\n\n"
            "Return exactly [A] or [B]."
        )
    elif family == "answerability_binary":
        task = (
            f"Conversation:\n{context}\n\n"
            f"Target: {record['target']}\n"
            f"Question: {question}\n\n"
            "Return exactly yes or no."
        )
    elif family == "info_accessibility_binary":
        task = (
            f"Conversation:\n{context}\n\n"
            f"Information: {record['information_question']} "
            f"{record['information_answer']}\n"
            f"Question: {question}\n\n"
            "Return exactly yes or no."
        )
    elif family == "fact":
        task = (
            f"Conversation:\n{context}\n\n"
            f"Question: {question}\n\n"
            "Return only a short answer phrase."
        )
    else:
        raise RuntimeError(f"Unsupported FANToM family: {family}")

    return (
        "This is a theory-of-mind test. Answer only from the supplied "
        "conversation and follow the requested output format exactly.\n\n"
        + task
    )


def score_response(
    *,
    record: dict[str, Any],
    manifest: dict[str, Any],
    response: str,
) -> dict[str, Any]:
    family = record["family"]

    if family == "belief_mc":
        pred = parse_mc(response)
        return {
            "normalized_prediction": pred,
            "correct": pred == manifest["correct_option"],
        }

    if family in {"answerability_binary", "info_accessibility_binary"}:
        pred = parse_binary(response)
        gold = "no" if record["correct_answer"] == "no:long" else record["correct_answer"]
        if gold not in {"yes", "no"}:
            raise RuntimeError(
                f"Unexpected binary FANToM answer for {record['question_id']}: {gold}"
            )
        return {
            "normalized_prediction": pred,
            "correct": pred == gold,
        }

    if family == "fact":
        f1 = token_f1(record["correct_answer"], response)
        return {
            "normalized_prediction": None,
            "token_f1": f1,
        }

    raise RuntimeError(f"Unsupported family: {family}")


def run_control(backend: OpenAICompatibleBackend, prompt: str) -> str:
    return backend.complete(
        [
            {"role": "system", "content": CONTROL_SYSTEM},
            {"role": "user", "content": prompt},
        ],
        max_tokens=DIRECT_MAX_TOKENS,
        temperature=TEMPERATURE,
    ).strip()


def evaluate_one(
    *,
    manifest: dict[str, Any],
    record: dict[str, Any],
    control_backend: OpenAICompatibleBackend,
    hcl_loop: HCLAnswerLoop,
) -> dict[str, Any]:
    prompt = build_prompt(record, manifest)

    control_response = run_control(control_backend, prompt)
    control_score = score_response(
        record=record,
        manifest=manifest,
        response=control_response,
    )

    hcl_run = hcl_loop.run(prompt)
    treatment_response = hcl_run.final_answer.strip()
    treatment_score = score_response(
        record=record,
        manifest=manifest,
        response=treatment_response,
    )

    result: dict[str, Any] = {
        "question_id": manifest["question_id"],
        "set_id": manifest["set_id"],
        "conversation_id": manifest["conversation_id"],
        "stratum": manifest["stratum"],
        "family": manifest["family"],
        "control": {
            **control_score,
            **response_meta(control_response),
        },
        "treatment": {
            **treatment_score,
            **response_meta(treatment_response),
            "hcl_mode": hcl_run.state.get("mode"),
            "hcl_uncertainty": (
                hcl_run.state.get("uncertainty", {}).get("level")
                if isinstance(hcl_run.state.get("uncertainty"), dict)
                else None
            ),
            "first_check_status": hcl_run.first_check.get("status"),
            "final_check_status": hcl_run.final_check.get("status"),
            "revision_performed": hcl_run.revision_performed,
            "second_revision_performed": hcl_run.second_revision_performed,
        },
    }

    if manifest["family"] != "fact":
        c = bool(result["control"]["correct"])
        t = bool(result["treatment"]["correct"])
        result["paired_outcome"] = (
            "improved" if (not c and t)
            else "worsened" if (c and not t)
            else "both_correct" if (c and t)
            else "both_wrong"
        )
    else:
        result["paired_f1_delta"] = (
            float(result["treatment"]["token_f1"])
            - float(result["control"]["token_f1"])
        )

    return result


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--shard-index", type=int, required=True)
    p.add_argument("--shard-count", type=int, default=4)
    p.add_argument(
        "--out",
        type=Path,
        default=ROOT / "artifacts/fantom-external-v01",
    )
    args = p.parse_args()

    if not os.getenv("DEEPSEEK_API_KEY"):
        raise RuntimeError("DEEPSEEK_API_KEY is required")
    if args.shard_index < 0 or args.shard_index >= args.shard_count:
        raise RuntimeError("Invalid shard index")

    selection = load_selection()
    selected = list(selection["selected"])
    shard = selected[args.shard_index :: args.shard_count]

    if args.shard_count != 4 or len(selected) != 32 or len(shard) != 8:
        raise RuntimeError(
            f"Unexpected FANToM sharding: total={len(selected)} shard={len(shard)}"
        )

    archive = download_verified()
    df = load_dataframe(archive)
    question_map = build_question_map(df)

    control_backend = OpenAICompatibleBackend(
        api_key=os.environ["DEEPSEEK_API_KEY"],
        base_url=BASE_URL,
        model=MODEL,
        seed=SEED,
    )
    treatment_backend = OpenAICompatibleBackend(
        api_key=os.environ["DEEPSEEK_API_KEY"],
        base_url=BASE_URL,
        model=MODEL,
        seed=SEED,
    )
    hcl_loop = HCLAnswerLoop(treatment_backend)

    results: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []

    for manifest in shard:
        qid = manifest["question_id"]
        try:
            record = question_map[qid]
            if record["set_id"] != manifest["set_id"]:
                raise RuntimeError(f"FANToM set_id drift for {qid}")
            if record["family"] != manifest["family"]:
                raise RuntimeError(f"FANToM family drift for {qid}")

            result = evaluate_one(
                manifest=manifest,
                record=record,
                control_backend=control_backend,
                hcl_loop=hcl_loop,
            )
            results.append(result)
            print(
                json.dumps(
                    {
                        "question_id": qid,
                        "stratum": manifest["stratum"],
                        "paired_outcome": result.get("paired_outcome"),
                        "paired_f1_delta": result.get("paired_f1_delta"),
                    },
                    ensure_ascii=False,
                ),
                flush=True,
            )
        except Exception as exc:
            failures.append(
                {
                    "question_id": qid,
                    "set_id": manifest["set_id"],
                    "stratum": manifest["stratum"],
                    "error_type": type(exc).__name__,
                }
            )
            print(
                json.dumps(
                    {
                        "question_id": qid,
                        "stratum": manifest["stratum"],
                        "error_type": type(exc).__name__,
                    },
                    ensure_ascii=False,
                ),
                flush=True,
            )

    args.out.mkdir(parents=True, exist_ok=True)
    output = {
        "source_commit": selection["source"]["commit"],
        "dataset_sha256": selection["source"]["dataset_sha256"],
        "model": MODEL,
        "seed": SEED,
        "temperature": TEMPERATURE,
        "shard_index": args.shard_index,
        "shard_count": args.shard_count,
        "requested": len(shard),
        "completed": len(results),
        "failures": failures,
        "results": results,
        "claim_boundary": (
            "Predeclared FANToM v0.1 paired external pilot; no conversation, "
            "question, gold answer, prompt, or full HCL state text stored."
        ),
    }
    (args.out / f"shard_{args.shard_index}.json").write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    return 0 if not failures and len(results) == len(shard) else 3


if __name__ == "__main__":
    raise SystemExit(main())
