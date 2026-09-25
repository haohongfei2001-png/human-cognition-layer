#!/usr/bin/env python3
"""Score frozen C/D/G answers with the pinned official LongMemEval judge prompt."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.preflight_v05_longmemeval_cdg_v01 import preflight_dataset, validate_manifest
from scripts.qualify_longmemeval_knowledge_update_v01 import EXPECTED_DATASET_SHA256

OFFICIAL_JUDGE_BLOB = "4732f3772b04a2b9069121ade304e6320494abc2"
JUDGE_MODEL = "gpt-4o-2024-08-06"


class JudgeError(ValueError):
    pass


def official_prompt_function(path: Path):
    source = path.read_bytes()
    git_blob = hashlib.sha1(f"blob {len(source)}\0".encode() + source).hexdigest()
    if git_blob != OFFICIAL_JUDGE_BLOB:
        raise JudgeError("official judge source blob drift")
    parsed = ast.parse(source.decode("utf-8"))
    functions = [x for x in parsed.body if isinstance(x, ast.FunctionDef) and x.name == "get_anscheck_prompt"]
    if len(functions) != 1:
        raise JudgeError("official judge prompt function missing or duplicated")
    namespace: dict = {}
    module = ast.Module(body=functions, type_ignores=[])
    exec(compile(module, str(path), "exec"), namespace)
    return namespace["get_anscheck_prompt"]


def validate_answers(raw: dict, selected: list[dict]) -> None:
    if raw.get("format") != "hcl-v05-longmemeval-cdg-answers-v01":
        raise JudgeError("wrong raw answer format")
    if raw.get("status") != "answers_complete_unscored":
        raise JudgeError("answers are not complete and frozen")
    if raw.get("dataset_sha256") != EXPECTED_DATASET_SHA256:
        raise JudgeError("raw answer dataset digest drift")
    ids = [x["question_id"] for x in selected]
    rows = raw.get("rows")
    if not isinstance(rows, list) or len(rows) != len(ids):
        raise JudgeError("raw answer row count mismatch")
    if [x.get("question_id") for x in rows] != ids:
        raise JudgeError("raw answer order or identity drift")
    if raw.get("attempted_ids") != ids:
        raise JudgeError("attempted IDs mismatch")
    for row, selected_row in zip(rows, selected):
        if row.get("history_sha256") != selected_row["history_sha256"]:
            raise JudgeError("raw answer history hash mismatch")
        answers = row.get("answers")
        if not isinstance(answers, dict) or set(answers) != {"C", "D", "G"}:
            raise JudgeError("C/D/G answers incomplete")
        if any(not isinstance(x, str) for x in answers.values()):
            raise JudgeError("answer must be text")
        if not isinstance(row.get("packet_sha256"), str) or len(row["packet_sha256"]) != 64:
            raise JudgeError("answer packet hash missing")


def score_one(question: str, answer: str, qid: str, hypotheses: dict[str, str],
              prompt_function, client,
              on_progress: Callable[[str, dict], None] | None = None) -> dict:
    result = {}
    for arm in ("C", "D", "G"):
        prompt = prompt_function("knowledge-update", question, answer,
                                 hypotheses[arm], abstention="_abs" in qid)
        completion = client.chat.completions.create(
            model=JUDGE_MODEL, messages=[{"role": "user", "content": prompt}],
            n=1, temperature=0, max_tokens=10)
        raw_response = (completion.choices[0].message.content or "").strip()
        result[arm] = {"judge_prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
                       "judge_prompt": prompt, "raw_response": raw_response,
                       "label": "yes" in raw_response.lower(),
                       "ambiguous": raw_response.lower() not in {"yes", "no"}}
        if on_progress is not None:
            on_progress(arm, result[arm])
    return result


def _write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--official-judge-source", type=Path, required=True)
    parser.add_argument("--dataset", type=Path)
    parser.add_argument("--raw-answers", type=Path)
    parser.add_argument("--out", type=Path, default=Path("artifacts/longmemeval-cdg-v01/judge-results.json"))
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--score", action="store_true")
    args = parser.parse_args()
    if args.validate_only == args.score:
        parser.error("choose exactly one of --validate-only or --score")
    prompt_function = official_prompt_function(args.official_judge_source)
    if not prompt_function("knowledge-update", "Q", "A", "R").endswith("Answer yes or no only."):
        raise JudgeError("official knowledge-update prompt shape changed")
    _, selected = validate_manifest()
    if args.validate_only:
        print(json.dumps({"official_judge_blob": OFFICIAL_JUDGE_BLOB,
                          "model": JUDGE_MODEL, "provider_calls": 0}, sort_keys=True))
        return
    if os.getenv("GITHUB_ACTIONS") != "true" or os.getenv("GITHUB_RUN_ATTEMPT") != "1":
        raise JudgeError("judge execution requires first-attempt GitHub Actions")
    if not args.dataset or not args.raw_answers:
        parser.error("--score requires --dataset and --raw-answers")
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        raise JudgeError("official judge credential missing")
    preflight_dataset(args.dataset, selected)
    raw_bytes = args.raw_answers.read_bytes()
    raw = json.loads(raw_bytes)
    validate_answers(raw, selected)
    data = json.loads(args.dataset.read_text(encoding="utf-8"))
    lookup = {x["question_id"]: x for x in data}
    from openai import OpenAI
    client = OpenAI(api_key=key)
    result = {"format": "hcl-v05-longmemeval-cdg-judge-v01",
              "status": "in_progress", "model": JUDGE_MODEL,
              "official_judge_blob": OFFICIAL_JUDGE_BLOB,
              "raw_answers_sha256": hashlib.sha256(raw_bytes).hexdigest(),
              "rows": [], "attempted_ids": []}
    _write_json(args.out, result)
    try:
        for entry in raw["rows"]:
            qid = entry["question_id"]
            result["attempted_ids"].append(qid)
            _write_json(args.out, result)
            ref = lookup[qid]
            def checkpoint(arm: str, judgment: dict) -> None:
                partial = result.setdefault("partial_row", {"question_id": qid,
                                                            "judgments": {}})
                partial["judgments"][arm] = judgment
                _write_json(args.out, result)
            scores = score_one(ref["question"], ref["answer"], qid,
                               entry["answers"], prompt_function, client,
                               on_progress=checkpoint)
            result["rows"].append({"question_id": qid, "judgments": scores})
            result.pop("partial_row", None)
            _write_json(args.out, result)
        result["status"] = "complete"
    except Exception as exc:
        result["status"] = "failed_partial"
        result["failure"] = {"type": type(exc).__name__, "message": str(exc)}
        raise
    finally:
        _write_json(args.out, result)


if __name__ == "__main__":
    main()
