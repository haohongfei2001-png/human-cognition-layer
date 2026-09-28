# CG-01 minimal external development package

Status: **PROVIDER-FREE PACKAGE FROZEN; USD 0.75 OWNER GRANT RECEIVED;
ONE-TIME EXECUTION PENDING**.
This is a four-case falsification probe, not a fresh benchmark, efficacy proof,
leaderboard attempt or permission to spend. It follows CG01-A/B/C and their
provider-free correctness checks.

## Source and exposure

Source: Project Gutenberg [*Short Stories Old and New*, eBook 10483](https://www.gutenberg.org/ebooks/10483),
edited by C. Alphonso Smith, originally published 1916. The catalog marks the
eBook **public domain in the USA**. Frozen UTF-8 source URL:
`https://www.gutenberg.org/cache/epub/10483/pg10483.txt`; full-file SHA256:
`14eef73227e014591aff4bf6bc217e6d030fa6daaf429742c0f6501172f5bb8e`.
The committed [package](../reports/HCL_CG01_EXTERNAL_PACKAGE.json) contains
the exact source spans, excerpt hashes, questions and source-only adjudication
criteria. The preflight verifies each excerpt against the pinned source bytes.

The two story families are *The Necklace* and *The Gift of the Magi*, two cases
each. All four have been read during source audit and are marked
`SOURCE_AUDIT_EXPOSED_NOT_PROVIDER_CONSUMED`. They must never be described as
unexposed/fresh. No native benchmark labels or hidden author intentions are used.
One case has an explicit narrator denial of a required prior-awareness
condition; two have directly stated purposes and available resources or
transactions; one challenges a tempting prior-knowledge attribution without a
source-grounded first-learning timestamp. Source-only judgments concern whether each candidate
explanation's requirements are supported, contradicted or unresolved. They do
not claim a single true motive.

## Fair arms and output

All arms receive the identical excerpt, candidate and question, use the same
model and the same JSON final-answer contract. Their treatment differs only as
frozen below:

| Arm | Treatment |
|---|---|
| C | Strong direct source-grounded answer. |
| P | Simple knowledge/explicit-goal/opportunity checklist. |
| G | Competent generic structured multi-hypothesis, actor/order/access method. |
| H | Actual v1 router, semantic preparation when needed, CG-01 condition checker and final cognition context. |
| H-new | Identical H source, preparation and candidate context, with only the condition states and checker result removed. |

For each case, H and H-new **share one semantic preparation output**. The
preparation prompt sees only source, query, target and perspective; it sees no
adjudication label. All extracted source spans must be exact substrings, all
events reader-only by default, and typed facts pass source/time/scope checks.
The answer model also receives the full source excerpt. Extraction failures are
kept as failures, charged and preserved. No oracle mental state is injected.

Final JSON fields are `assessment`, `reason`, `evidence_quote` and
`unknown_motive`. The assessment is one of `INVALIDATED`,
`CONSISTENT_CONDITIONAL`, `UNRESOLVED`; the quote must be an exact source span.
The deterministic scorer checks JSON validity, status match, quote anchoring and
the open-motive flag. A source-first, arm-masked human audit still judges whether
the cited condition is semantically grounded, whether uncertainty is calibrated,
and whether there is a severe actor/time/access or private-truth error. Such an
error zeroes the case. No invalid output or ambiguous case is dropped post hoc.
Report all 20 arm outputs, four preparation outputs, actual messages, final
cognition contexts, usage/cost, reversals, abstentions and extraction failures.
H may only claim a CG-01 increment if it beats qualified P/G and the gain
disappears in H-new; four cases can falsify gross behavior but cannot alone
establish broad utility.

## Frozen meter and owner gate

Proposed provider/model: existing DeepSeek API, `deepseek-v4-pro` (documented
version `DeepSeek-V4-Pro-0813`). Every request explicitly uses non-thinking
mode and JSON output with no retry, per the
[official API contract](https://api-docs.deepseek.com/api/create-chat-completion/).
Its [published peak rates](https://api-docs.deepseek.com/quick_start/pricing/)
at package freeze are USD 1.32 per million input cache-miss tokens and USD 3.96
per million output tokens. The cap is **24 calls total**: 4 preparation calls
and 20 answers; **16,000 input and 2,000 output tokens per call**. Assuming every
call reaches both caps at peak cache-miss rates, the reservation is USD
**0.69696**; the absolute planned hard cap is **USD 0.75**. The runner makes no
retry, reserves the worst-case amount before each call, charges full reservation
on failure, checks returned model/usage and stops at the cap. Provider prices
must be rechecked before any authorized execution; a price or model change
requires a newly frozen cap, never silent expansion.

The implementation is [provider-injectable](../scripts/cg01_external_package.py):
the DeepSeek adapter requires an explicitly supplied API key, and importing or
preflighting the package makes no provider call. The owner authorized this
specific package and USD 0.75 ceiling on 2026-09-28. The one-time Actions
workflow receives the existing repository secret, checks a unique first-attempt
trigger commit, and preserves a journal after every attempt. There is no
scheduled trigger or retry. The runner records a conservative peak-price,
all-cache-miss cost upper bound alongside token usage; the invoice can be lower.
Provider-free tests cover package integrity, arm isolation, H-new ablation,
metering, scoring, checkpointing and a full 24-call stub run. No provider
execution has occurred as of this workflow preparation. After the one-time
comparison, Phase E requires one RETAIN / SIMPLIFY / DEACTIVATE decision.
Historical budgets do not transfer. LongMemEval remains sealed.
