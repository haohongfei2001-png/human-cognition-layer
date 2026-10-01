"""Layer 1 scoring: regex-based answer extraction and string matching."""

from __future__ import annotations

import re
from dataclasses import dataclass

from .models import Scenario

_PUNCT_RE = re.compile(r"[^\w\s]")
_WS_RE = re.compile(r"\s+")

# Patterns that often introduce the actual answer in verbose responses.
_LEADIN_PATTERNS = [
    r"the answer is\s+(.+?)(?:\.|$)",
    r"answer:\s*(.+?)(?:\.|$|\n)",
    r"will look (?:in|on|at|for|towards?)\s+(.+?)(?:\.|$|,)",
    r"will go (?:to|towards?)\s+(.+?)(?:\.|$|,)",
    r"would (?:look|go) (?:in|on|at|to|towards?)\s+(.+?)(?:\.|$|,)",
    r"most likely (?:feeling|feels?)\s+(.+?)(?:\.|$|,)",
    r"the most likely (?:emotion|feeling|response) is\s+(.+?)(?:\.|$)",
]

_NEGATION_TOKENS = {"not", "n't", "no", "never", "neither", "nor"}


@dataclass
class ScoreOutcome:
    correct: bool | None  # None means ambiguous, defer to Layer 2
    extracted_answer: str | None
    ambiguous: bool


def _normalize(text: str) -> str:
    text = text.lower().strip()
    text = _PUNCT_RE.sub(" ", text)
    text = _WS_RE.sub(" ", text)
    return text.strip()


def extract_answer(response: str) -> str | None:
    """Best-effort extraction of the salient answer phrase from a model response."""
    if not response:
        return None
    lowered = response.strip().lower()
    for pattern in _LEADIN_PATTERNS:
        match = re.search(pattern, lowered, flags=re.IGNORECASE)
        if match:
            return match.group(1).strip(" .,'\"")
    # Fall back to the first sentence — short responses often answer directly.
    first = re.split(r"[.!?\n]", response.strip(), maxsplit=1)[0]
    if first and len(first) <= 200:
        return first.strip()
    return None


def _find_phrase(haystack_norm: str, needle_norm: str) -> int:
    """Return the index of needle as a whole-word phrase in haystack, or -1.

    Word boundaries prevent substring false positives ("no" in "know",
    "basket" in "basketball").
    """
    match = re.search(rf"\b{re.escape(needle_norm)}\b", haystack_norm)
    return match.start() if match else -1


def _has_negation_around(haystack_norm: str, needle_norm: str) -> bool:
    """Return True if the candidate phrase appears in a negated clause."""
    idx = _find_phrase(haystack_norm, needle_norm)
    if idx < 0:
        return False
    preceding = haystack_norm[max(0, idx - 40) : idx]
    tokens = preceding.split()
    return any(tok in _NEGATION_TOKENS for tok in tokens[-6:])


def _candidate_phrases(scenario: Scenario) -> list[str]:
    phrases = [scenario.expected_answer, *scenario.answer_aliases]
    return [_normalize(p) for p in phrases if p]


def score_response(scenario: Scenario, response: str) -> ScoreOutcome:
    """Layer 1 scoring. Returns correct/incorrect/ambiguous."""
    if not response or not response.strip():
        return ScoreOutcome(correct=False, extracted_answer=None, ambiguous=False)

    extracted = extract_answer(response)
    response_norm = _normalize(response)
    extracted_norm = _normalize(extracted) if extracted else ""

    candidates = _candidate_phrases(scenario)
    matched = False
    matched_in_extracted = False

    for cand in candidates:
        if not cand:
            continue
        if (
            extracted_norm
            and _find_phrase(extracted_norm, cand) >= 0
            and not _has_negation_around(extracted_norm, cand)
        ):
            matched = True
            matched_in_extracted = True
            break
        if _find_phrase(response_norm, cand) >= 0 and not _has_negation_around(response_norm, cand):
            matched = True
            break

    if matched:
        # Sanity check for yes/no scenarios where the wrong polarity may also appear.
        if scenario.expected_answer.lower() in {"yes", "no"}:
            opposite = "no" if scenario.expected_answer.lower() == "yes" else "yes"
            opp_norm = _normalize(opposite)
            if _find_phrase(response_norm, opp_norm) >= 0 and not matched_in_extracted:
                # Both yes and no appear somewhere — flag for Layer 2.
                return ScoreOutcome(correct=None, extracted_answer=extracted, ambiguous=True)
        return ScoreOutcome(correct=True, extracted_answer=extracted, ambiguous=False)

    # No match — but if the response is verbose, it might still be right semantically.
    if len(response_norm.split()) > 25:
        return ScoreOutcome(correct=None, extracted_answer=extracted, ambiguous=True)

    return ScoreOutcome(correct=False, extracted_answer=extracted, ambiguous=False)
