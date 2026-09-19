"""HCL v0.3 always-on answer loop.

Canonical pipeline:
input -> frozen HCL cognition state -> base-model draft
-> HCL consistency/calibration check -> optional revision
-> final HCL verification -> final answer.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from typing import Any, Protocol


class ChatBackend(Protocol):
    def complete(
        self,
        messages: list[dict[str, str]],
        *,
        max_tokens: int,
        temperature: float = 0.0,
    ) -> str:
        ...


def extract_json(text: str) -> dict[str, Any] | None:
    if not text:
        return None
    text = text.strip()
    candidates = [text]
    if "~~~" in text:
        for part in text.split("~~~"):
            part = part.strip()
            if part.startswith("json"):
                part = part[4:].strip()
            if part.startswith("{") and part.endswith("}"):
                candidates.append(part)
    left, right = text.find("{"), text.rfind("}")
    if 0 <= left < right:
        candidates.append(text[left : right + 1])
    for candidate in candidates:
        try:
            value = json.loads(candidate)
            if isinstance(value, dict):
                return value
        except Exception:
            pass
    return None


STATE_SYSTEM = """You are the Human Cognition Layer (HCL) v0.3 state builder.

Your output is an intermediate cognition state, not the final answer.

Every input passes through HCL. Choose exactly one mode:
- SIMPLE: decision-relevant state is directly established; do not invent extra branches.
- EPISTEMIC: information access, false belief, nested belief, or world/belief divergence matters.
- CAUSAL_AMBIGUITY: multiple materially different hidden causes remain relevant.

Frozen rules:
1. world truth != agent knowledge;
2. first-order belief != second-order belief;
3. information transfer requires an evidence path;
4. world-truth / agent-belief divergence is epistemic;
5. preserve genuine competing causes;
6. do not manufacture exotic alternatives merely because they are logically possible;
7. use the minimal sufficient model;
8. calibrate uncertainty to the actual question granularity;
9. low = explicit/direct/overwhelming at required granularity;
10. medium = one interpretation materially favored, credible alternatives remain;
11. high = materially different interpretations remain comparably plausible, or a critical bridge is missing;
12. protocol enums remain English.

Return JSON only:
{
  "mode": "SIMPLE|EPISTEMIC|CAUSAL_AMBIGUITY",
  "explicit_facts": ["..."],
  "agents": {
    "agent": {
      "observed": ["..."],
      "knows": ["..."],
      "believes": ["..."],
      "beliefs_about_others": ["..."]
    }
  },
  "hypotheses": [
    {
      "hypothesis": "...",
      "support": ["..."],
      "counterevidence_or_missing": ["..."]
    }
  ],
  "missing_bridges": ["..."],
  "uncertainty": {
    "level": "low|medium|high",
    "reason": "..."
  },
  "decision_relevant_summary": "..."
}

Use the same natural language as the input for explanatory strings.
Do not answer the user's final question.
"""


DRAFT_SYSTEM = """You are the response generator inside an always-on Human Cognition Layer system.

Answer the user's actual question using the supplied HCL state as structured cognitive context.

Rules:
- respect explicit facts and agent-specific information access;
- do not give a character narrator-only knowledge;
- preserve genuine uncertainty when the state says evidence is insufficient;
- do not add speculative alternatives when the state is SIMPLE/low unless the user asks;
- answer at the granularity of the user's question;
- be concise unless the user asks for detail.

Do not mention HCL, JSON, benchmark mechanics, or internal checking.
Return only the user-facing draft answer.
"""


CHECK_SYSTEM = """You are the HCL v0.3 consistency and calibration checker.

You receive:
1. the user's input;
2. the frozen HCL cognition state;
3. a candidate answer.

Check exactly these violation families:
- FACT_CONTRADICTION: contradicts explicit facts.
- INFORMATION_ACCESS: gives an agent information they did not observe/receive/infer with support.
- BELIEF_LEVEL: confuses world truth, first-order belief, or second-order belief.
- PREMATURE_COLLAPSE: presents one hidden cause/mental state as certain when genuine alternatives remain.
- OVER_UNCERTAINTY: invents doubt or alternatives despite direct/overwhelming evidence at the asked granularity.
- GRANULARITY: answers a different finer/coarser question than the user asked.
- UNSUPPORTED_INVENTION: introduces material claims absent from facts/hypotheses.

Return JSON only:
{
  "status": "PASS|REVISE",
  "violations": [
    {
      "type": "FACT_CONTRADICTION|INFORMATION_ACCESS|BELIEF_LEVEL|PREMATURE_COLLAPSE|OVER_UNCERTAINTY|GRANULARITY|UNSUPPORTED_INVENTION",
      "explanation": "..."
    }
  ],
  "calibration": {
    "appropriate": true,
    "reason": "..."
  },
  "revision_instruction": "..."
}

PASS requires zero material violations.
Do not reject merely for harmless wording/style differences.
"""


REVISION_SYSTEM = """You are the final response generator inside an always-on HCL system.

Revise the draft to satisfy the supplied HCL cognition state and HCL checker.

Requirements:
- correct every material checker violation;
- preserve valid parts of the draft;
- do not expose HCL internals;
- do not mention that a revision occurred;
- answer the user's actual question directly;
- calibrate certainty to the evidence;
- do not invent extra uncertainty.

Return only the final user-facing answer.
"""


@dataclass
class HCLRun:
    user_input: str
    state: dict[str, Any]
    draft: str
    first_check: dict[str, Any]
    revision_performed: bool
    candidate_final: str
    final_check: dict[str, Any]
    second_revision_performed: bool
    final_answer: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class HCLAnswerLoop:
    def __init__(
        self,
        backend: ChatBackend,
        *,
        state_max_tokens: int = 8192,
        answer_max_tokens: int = 4096,
        check_max_tokens: int = 4096,
    ) -> None:
        self.backend = backend
        self.state_max_tokens = state_max_tokens
        self.answer_max_tokens = answer_max_tokens
        self.check_max_tokens = check_max_tokens

    def build_state(self, user_input: str) -> dict[str, Any]:
        base_user = user_input + "\n\n只生成 HCL 中间状态，不要回答最终问题。"
        last_raw = ""
        for attempt in range(3):
            suffix = ""
            if attempt > 0:
                suffix = (
                    "\n\n前一次输出不是可解析的 JSON。"
                    "这次必须只输出一个完整 JSON 对象，不要使用 Markdown、代码块或额外文字。"
                )
            last_raw = self.backend.complete(
                [
                    {"role": "system", "content": STATE_SYSTEM},
                    {
                        "role": "user",
                        "content": base_user + suffix,
                    },
                ],
                max_tokens=self.state_max_tokens,
                temperature=0.0,
            )
            state = extract_json(last_raw)
            if state is not None:
                return self._normalize_state(state)

        raise RuntimeError(
            "HCL state builder returned no valid JSON after 3 attempts"
        )

    def generate_draft(self, user_input: str, state: dict[str, Any]) -> str:
        return self.backend.complete(
            [
                {"role": "system", "content": DRAFT_SYSTEM},
                {
                    "role": "user",
                    "content": self._answer_payload(user_input, state),
                },
            ],
            max_tokens=self.answer_max_tokens,
            temperature=0.0,
        ).strip()

    def check(
        self,
        user_input: str,
        state: dict[str, Any],
        answer: str,
    ) -> dict[str, Any]:
        raw = self.backend.complete(
            [
                {"role": "system", "content": CHECK_SYSTEM},
                {
                    "role": "user",
                    "content": (
                        "【用户输入】\n"
                        + user_input
                        + "\n\n【HCL cognition state】\n"
                        + json.dumps(state, ensure_ascii=False, indent=2)
                        + "\n\n【候选回答】\n"
                        + answer
                    ),
                },
            ],
            max_tokens=self.check_max_tokens,
            temperature=0.0,
        )
        result = extract_json(raw)
        if result is None:
            return {
                "status": "REVISE",
                "violations": [
                    {
                        "type": "UNSUPPORTED_INVENTION",
                        "explanation": "Checker returned no valid structured verdict.",
                    }
                ],
                "calibration": {
                    "appropriate": False,
                    "reason": "Checker output invalid; conservative regeneration required.",
                },
                "revision_instruction": (
                    "Regenerate directly from the HCL state using only supported facts, "
                    "beliefs, hypotheses, and calibrated uncertainty."
                ),
            }
        return self._normalize_check(result)

    def revise(
        self,
        user_input: str,
        state: dict[str, Any],
        draft: str,
        check: dict[str, Any],
    ) -> str:
        return self.backend.complete(
            [
                {"role": "system", "content": REVISION_SYSTEM},
                {
                    "role": "user",
                    "content": (
                        "【用户输入】\n"
                        + user_input
                        + "\n\n【HCL cognition state】\n"
                        + json.dumps(state, ensure_ascii=False, indent=2)
                        + "\n\n【原始回答】\n"
                        + draft
                        + "\n\n【HCL checker】\n"
                        + json.dumps(check, ensure_ascii=False, indent=2)
                    ),
                },
            ],
            max_tokens=self.answer_max_tokens,
            temperature=0.0,
        ).strip()

    def run(self, user_input: str) -> HCLRun:
        state = self.build_state(user_input)
        draft = self.generate_draft(user_input, state)
        first_check = self.check(user_input, state, draft)

        revision_performed = first_check.get("status") == "REVISE"
        if revision_performed:
            candidate_final = self.revise(user_input, state, draft, first_check)
        else:
            candidate_final = draft

        final_check = self.check(user_input, state, candidate_final)
        second_revision_performed = final_check.get("status") == "REVISE"

        if second_revision_performed:
            final_answer = self.revise(
                user_input,
                state,
                candidate_final,
                final_check,
            )
        else:
            final_answer = candidate_final

        return HCLRun(
            user_input=user_input,
            state=state,
            draft=draft,
            first_check=first_check,
            revision_performed=revision_performed,
            candidate_final=candidate_final,
            final_check=final_check,
            second_revision_performed=second_revision_performed,
            final_answer=final_answer,
        )

    @staticmethod
    def _answer_payload(user_input: str, state: dict[str, Any]) -> str:
        return (
            "【用户输入】\n"
            + user_input
            + "\n\n【HCL cognition state】\n"
            + json.dumps(state, ensure_ascii=False, indent=2)
            + "\n\n请生成用户可见回答。"
        )

    @staticmethod
    def _normalize_state(state: dict[str, Any]) -> dict[str, Any]:
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
        if state.get("mode") in mode_alias:
            state["mode"] = mode_alias[state["mode"]]
        uncertainty = state.get("uncertainty")
        if isinstance(uncertainty, dict) and uncertainty.get("level") in uncertainty_alias:
            uncertainty["level"] = uncertainty_alias[uncertainty["level"]]
        return state

    @staticmethod
    def _normalize_check(check: dict[str, Any]) -> dict[str, Any]:
        status = str(check.get("status", "")).upper()
        check["status"] = status if status in {"PASS", "REVISE"} else "REVISE"
        if not isinstance(check.get("violations"), list):
            check["violations"] = []
        if not isinstance(check.get("calibration"), dict):
            check["calibration"] = {
                "appropriate": False,
                "reason": "Missing calibration verdict.",
            }
        if not isinstance(check.get("revision_instruction"), str):
            check["revision_instruction"] = ""
        return check
