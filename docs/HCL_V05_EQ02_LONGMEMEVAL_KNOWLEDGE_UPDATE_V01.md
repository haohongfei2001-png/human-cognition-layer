# HCL v0.5 EQ-02 — LongMemEval Knowledge-Update Qualification v0.1

Status: **FROZEN / ZERO-PROVIDER ONLY**

## Purpose

Determine whether LongMemEval's independently authored `knowledge-update`
subset can test current HCL v0.5 without changing cognition semantics or using
gold/evidence labels during state construction.

This is a qualification stage, not an efficacy run.

## Upstream pin

Canonical code/docs:
- repository: `xiaowu0162/LongMemEval`
- pinned GitHub main:
  `9e0b455f4ef0e2ab8f2e582289761153549043fc`

Canonical dataset family:
- Hugging Face: `xiaowu0162/longmemeval-cleaned`
- use the cleaned release, not deprecated `xiaowu0162/longmemeval`;
- cleaned dataset repository revision observed at:
  `98d7416c24c778c2fee6e6f3006e7a073259d48f`;
- candidate file:
  `longmemeval_s_cleaned.json`;
- candidate file SHA-256 reported for that upstream revision:
  `d6f21ea9d60a0d56f34a05b609c79c88a451d2ae03597821ea3d5a9678c3a442`.

Before any selected row is inspected by a provider, local acquisition must
verify the exact file digest. If the upstream file or revision changes, stop and
refresh the contract rather than silently following `main`.

## Why knowledge-update is a plausible fit

LongMemEval's construction logic for `knowledge_update` inserts:
- an older answer session;
- a newer answer session;
- explicit timestamps ordering old before new;
- filler sessions around them;
- a question after the newer evidence.

The public benchmark therefore supplies a real temporal interaction stream
rather than requiring HCL to invent chronology.

This is closer to v0.5's tested capability:
persistent state under updates and historical evidence.

## Strict evidence firewall

The state-construction arm may use only:
- session timestamps;
- session/turn order;
- turn role (`user` / `assistant`);
- turn content.

The following MUST NOT enter HCL state construction, semantic prompts, ontology
construction or memory baselines:
- `answer`;
- `has_answer`;
- `answer_session_ids`;
- any gold evaluation label;
- any field derived from those labels.

Question text is also withheld from state construction.

The question and evaluator may be used only after all memory/state arms have
finished ingesting the same history.

This prevents query/gold-driven issue discovery.

## Adapter principle

Each user turn becomes an external event:
- actor = one stable `user` subject;
- assistant turns are retained as observable conversation evidence but do not
  automatically become the user's stance;
- valid_time is derived from the benchmark session timestamp plus stable
  within-session ordering;
- raw text is preserved.

No benchmark-specific semantic rule is added to the v0.5 extractor.

The qualification must verify whether the existing routed extractor naturally
produces useful user stance/update state from the selected knowledge-update
histories.

If it does not, that is a legitimate negative qualification result; the adapter
must not be repaired from benchmark answers.

## Arms for a future paid run

A future execution may be authorized only after EQ-02 passes.

Candidate arms:
- C: direct/control reader over the same bounded retrieved evidence;
- D: same reader plus canonical HCL v0.5 state;
- G: competent generic structured-memory baseline with deterministic
  compaction/budgeting and no event-drop failure class.

Do not use the flawed internal G implementation unchanged.

Retrieval must be held constant between C/D/G so the test measures
state/consolidation value rather than retrieval quality.

## Scoring

The official LongMemEval `knowledge-update` evaluation uses an LLM judge.

Because this introduces judge variance:
- raw model answers must be preserved;
- paired C/D/G outcomes must be reported;
- judge model/version and prompt must be pinned;
- a result cannot be treated as a leaderboard-equivalent number unless it uses
  the official evaluation procedure unchanged.

EQ-02 itself runs no answer model and no judge.

## Qualification gates

EQ-02 passes only if provider-free audit demonstrates all of:

1. exact cleaned dataset digest verified;
2. selected rows are `question_type == knowledge-update`;
3. state constructor never receives gold/evidence labels or question text;
4. event conversion is deterministic and timestamp preserving;
5. HCL state can be built from raw user/assistant history without
   benchmark-specific semantic code;
6. no current-v0.5 semantic invariant is relaxed;
7. exact selection rule is frozen before any provider call;
8. selected question IDs are stored, but question/answer/history text is not
   copied into the public repository;
9. previous external-exposure registers show no prior provider-backed
   LongMemEval execution in this project.

If any of 3–6 fail, stop the target rather than modify v0.5 against the
benchmark.

## Selection plan

Qualification may inspect schema/metadata for the whole cleaned-S file.

It must not manually browse selected row contents for outcome-oriented choice.

If the file contains the expected 78 knowledge-update questions:
- choose a fixed deterministic subset by SHA-256 rank over `question_id`;
- selection size for first external pilot: **32 rows**;
- freeze IDs before provider execution;
- no stratification using model outcomes or answer text.

If the count differs, record the actual count and freeze a revised deterministic
selection rule before any provider call.

## Cross-model relationship

EQ-02 first establishes an adapter/evidence contract.

Cross-model paid execution is a later gate. The same frozen selected rows and
adapter must be used within each base-model family; raw scores across different
base models are not an HCL effect.

**Gate: HCL_V05_EQ02_LONGMEMEVAL_KNOWLEDGE_UPDATE_ZERO_PROVIDER_QUALIFICATION**
