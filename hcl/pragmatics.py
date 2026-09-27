"""Minimal pragmatic interpretation method, without inferred belief persistence.

This is a thin reasoning procedure over exact public source anchors, not an
algorithm that determines a person's true intentions or emotions.
"""

import json

THIN_METHOD = (
    "Internally separate the reply's literal content from its context-supported communicative implication. "
    "Compare plausible readings against the actual question and situation, retaining conditions, hedges and uncertainty. "
    "Check whether the preferred reading depends on an unstated fact; reject such certainty. "
    "An inferred communicative reading is not a known private intention, emotion or belief."
)


def source_view(row):
    """Exact dialogue anchors only; never annotations or rewritten hypotheses."""
    fields = {k: row[k] for k in ("context", "question-X", "answer-Y")}
    if any(
        not isinstance(v, str) or not v.strip() or len(v) > 2000
        for v in fields.values()
    ):
        raise ValueError("bounded nonempty source anchors required")
    return {
        "situation": fields["context"],
        "turns": [
            {"speaker": "X", "utterance": fields["question-X"]},
            {"speaker": "Y", "utterance": fields["answer-Y"]},
        ],
        "scope": "PUBLIC_DIALOGUE_READING_NOT_PRIVATE_MENTAL_TRUTH",
    }


def request_messages(view, task, common, thin=False):
    return [
        {"role": "system", "content": common + (" " + THIN_METHOD if thin else "")},
        {
            "role": "user",
            "content": json.dumps({"source": view, "task": task}, sort_keys=True),
        },
    ]
