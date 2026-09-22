# HCL State-Generation Reliability Audit v0.1

Status: **PREDECLARED / AUDIT FROZEN HCL BEFORE REPAIR**

## Trigger

Hi-ToM external validation v0.1 attempted all 60 frozen rows but completed only
36 paired rows. Twenty-four rows terminated with persisted exception class
`RuntimeError`.

The consumed Hi-ToM artifacts intentionally do not contain exception text,
prompts, responses, or cognition state. The current HCL state builder contains a
known `RuntimeError` path after three consecutive state responses cannot be
parsed as a JSON object, but the Hi-ToM evidence alone does not prove that this
was the cause of every failure.

This audit tests that abstract reliability question independently.

## Evidence isolation

This audit:
- uses **no Hi-ToM story, question, choice, answer, wording, or response**;
- uses no FANToM or SOTOPIA benchmark content;
- uses deterministic synthetic scenarios generated from repository-owned
  recipes;
- does not inspect the 36 completed Hi-ToM outcomes;
- does not rerun any consumed Hi-ToM row.

## Frozen implementation under audit

Behavior anchor:
`ce36d7e6f911910f97437c23455dee33e0e7bc82`

Before audit evidence is observed, do not change:
- `hcl/v03/answer_loop.py`;
- `hcl/v03/backends.py`;
- `hcl/v03/state_schema.json`;
- `hcl/v03/FROZEN_STATE_SEMANTICS.md`;
- state token budget;
- model / provider / endpoint / seed.

Provider configuration:
- model: `deepseek-flash`;
- endpoint: existing DeepSeek endpoint;
- seed: 42;
- temperature: 0 through the frozen state builder;
- state max tokens: 8192.

## Synthetic fixture design

Twenty-four deterministic cases are frozen before provider calls.

Six strata, four cases each:
1. short / simple;
2. short / recursive;
3. medium / simple;
4. medium / recursive;
5. long / simple;
6. long / recursive.

The generated text uses generic laboratories, lockers, markers, notices and
agents. Event count and recursive-belief structure vary independently of any
external benchmark.

This is a reliability stress audit, not a semantic-accuracy benchmark. No gold
answer is used.

## Content-free observation

The audit wraps the real frozen backend used by `HCLAnswerLoop.build_state()`.

For each HCL-level state-generation attempt it may persist only:
- attempt ordinal;
- response byte count;
- SHA-256 of response bytes;
- whether the response was empty;
- whether `extract_json()` accepted a JSON object;
- exception class if the backend call itself raised.

It must not persist:
- synthetic input text;
- prompt/messages;
- response text;
- parsed JSON body;
- normalized cognition state;
- credentials;
- exception text.

Per case it may additionally persist:
- fixture ID and frozen stratum metadata;
- generated input byte count and SHA-256;
- attempt count;
- success/failure;
- failure class;
- backend exception class, if any.

## Failure classification

`state_json_exhaustion`:
- the real frozen `build_state()` raises the exact known internal
  `RuntimeError` corresponding to no parseable JSON object after all three
  HCL-level attempts.

`backend_or_other_exception`:
- any other propagated exception.

No exception text is persisted.

## Predeclared interpretation

A repeatable **state-generation JSON reliability defect** is established only if:
- at least **2 distinct synthetic cases** terminate as
  `state_json_exhaustion`.

A repeatable **provider/transport/other runtime defect** is separately flagged
if:
- at least **2 distinct synthetic cases** terminate as
  `backend_or_other_exception`.

Interpretation:
- both thresholds met -> `MIXED_RUNTIME_RELIABILITY_DEFECT`;
- JSON threshold only -> `STATE_JSON_RELIABILITY_DEFECT_ESTABLISHED`;
- backend/other threshold only -> `BACKEND_OR_OTHER_RELIABILITY_DEFECT_ESTABLISHED`;
- neither threshold -> `NO_REPEATABLE_DEFECT_ESTABLISHED`.

The thresholds are diagnostic gates, not efficacy claims.

## Repair boundary

This audit is observation only.

No HCL behavior change is authorized before the audit closes.

If an abstract defect is independently reproduced, a later repair must:
1. address the abstract failure class rather than any consumed benchmark row;
2. preserve frozen cognition semantics unless separately justified;
3. pass independent synthetic tests;
4. pass existing state / answer-loop regressions;
5. only then permit a separately predeclared fresh external validation.

## Claim boundary

This audit can establish or fail to establish an execution-reliability defect in
HCL state generation.

It cannot establish:
- Hi-ToM accuracy;
- HCL efficacy;
- cross-model transfer;
- SOTOPIA behavior;
- HCL 1.0 certification.
