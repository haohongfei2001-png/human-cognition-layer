# HCL v0.5 EQ-02 — LongMemEval Knowledge-Update Qualification Closure

Verdict: **COMPLETE / QUALIFICATION PASS / SEALED 32-ROW SELECTION / NO PROVIDER RUN**

## Exact qualification evidence

- PR: #46
- exact qualification head: `62d69ae7cf573923161be135bb54a71280e71750`
- workflow: `HCL v0.5 EQ-02 LongMemEval Qualification`
- run: `36094801638` — SUCCESS
- artifact: `10846604293`
- artifact ZIP digest:
  `sha256:d3f9e6545856a9fb0700f412dc7fc9a6f8609460507a0013aae89e93cffe1101`
- redacted manifest SHA-256:
  `80df22912d1a6a82bdd3b820896d58c945072e8be8d407165b09797faef89c7d`

Pinned upstream:
- code:
  `xiaowu0162/LongMemEval@9e0b455f4ef0e2ab8f2e582289761153549043fc`
- dataset revision:
  `98d7416c24c778c2fee6e6f3006e7a073259d48f`
- cleaned-S SHA-256:
  `d6f21ea9d60a0d56f34a05b609c79c88a451d2ae03597821ea3d5a9678c3a442`

No LLM/provider call was made.

## Dataset audit

Observed cleaned-S:
- total rows: **500**
- knowledge-update: **78**
- multi-session: 133
- temporal-reasoning: 133
- single-session-user: 70
- single-session-assistant: 56
- single-session-preference: 30

The expected 78 knowledge-update rows are present.

All 78 knowledge-update rows have non-monotonic **file/list order** relative to
their explicit timestamps. The adapter therefore stably orders sessions by:
1. benchmark `haystack_dates`;
2. original source position only as a tie-break/provenance field.

This chronology operation is independent of question, answer and evidence
labels.

Three blank history turns were observed across all 78 knowledge-update rows.
They are skipped deterministically rather than turned into fabricated events.

## State-construction firewall

Only the following benchmark material may cross into HCL state ingestion:
- session ID;
- session timestamp;
- turn role;
- turn content.

The qualification implementation structurally strips and rejects:
- `answer`;
- `answer_session_ids`;
- `question`;
- `has_answer`;
- `autoeval_label`;
- `gold`;
- `correct_answer`.

The question is withheld until after state construction.

This is structural isolation. Natural-language answer content is allowed to
appear inside raw history when it is genuinely part of the evidence; only
out-of-band annotations are forbidden.

## Event adaptation

The provider-free adapter maps:
- user turn -> actor `longmemeval_user`, recipient assistant;
- assistant turn -> actor `longmemeval_assistant`, recipient user;
- benchmark session timestamp -> event valid time;
- stable within-session microsecond offsets -> tie-breaking only;
- raw turn content -> raw event text.

No benchmark-specific stance/revision semantic rule is added.

This preserves the existing v0.5 semantic boundary: the model still decides
from the raw event whether an explicit self stance or explicit revision relation
is directly supported.

## Sealed selection

Selection manifest:
- `eval/longmemeval/knowledge_update_selection_v01.json`

Rule frozen before any provider use:
- filter `question_type == knowledge-update`;
- rank by SHA-256(`HCL-LONGMEMEVAL-KU-EQ02-20260925|question_id`);
- choose first **32**.

The committed manifest stores only:
- question ID;
- history SHA-256;
- upstream/dataset provenance.

It stores no question, answer or history text.

## Qualification decision

EQ-02 **passes** as an adapter/evidence-boundary qualification.

This does NOT yet establish that v0.5 is useful on LongMemEval. It establishes
only that:
- the external data can be converted deterministically;
- chronology is externally supplied;
- the current v0.5 semantic extractor can be invoked without adding
  benchmark-specific semantic rules;
- sealed rows can remain blind to question/gold during state construction.

## Next gate

Do not immediately run the sealed 32 rows.

First create a provider-backed **execution-compatibility diagnostic** on a
small, deterministically frozen subset of the **46 non-selected
knowledge-update rows**.

Purpose:
- verify canonical v0.5 extraction can process realistic LongMemEval histories;
- measure semantic-error/repair rate and state growth;
- verify runtime/cost feasibility;
- do not score task answers;
- do not use question or gold in state construction or diagnostic judgment;
- do not modify v0.5 semantics from the diagnostic.

If the existing mechanism cannot ingest this external stream reliably, stop
before consuming sealed efficacy rows.

If it can, freeze the paid C/D/G efficacy protocol on the sealed 32 rows.

**Gate: HCL_V05_EQ02_QUALIFICATION_PASS_EXTERNAL_INGEST_COMPATIBILITY_NEXT**
