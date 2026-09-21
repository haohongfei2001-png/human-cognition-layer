# FANToM External Validation v0.1 — Paired Pilot Predeclaration

Status: **FROZEN BEFORE PROVIDER CALLS**

## External source

- benchmark: FANToM
- repository: `skywalker023/fantom`
- pinned commit: `1cae6fa30f5ba04ca0fff5f5716b5ba7055e2e85`
- official dataset archive SHA-256:
  `1d08dfa0ea474c7f83b9bc7e3a7b466eab25194043489dd618b4c5223e1253a4`
- dataset version: 1.0
- use: evaluation only.

FANToM is independent of the consumed SOTOPIA-Hard environment templates.

## Zero-provider inventory

Final inventory:
- run: `35602513859`
- artifact: `10638929742`
- artifact SHA-256:
  `b00425bd66e1747803cc245a3e39e7bcc0fda0ba50152dd3bac08ac807d24e7e`
- FANToM sets: **870**
- provider/model calls: **0**

Candidate counts:
- inaccessible first-order belief: **642**
- inaccessible second-order belief: **351**
- inaccessible answerability binary: **2225**
- inaccessible information-accessibility binary: **2225**
- accessible first-order belief: **228**
- accessible second-order belief: **319**
- fact controls: **870**

The first inventory run failed before selection because the archive member path
assumption required a directory prefix. No provider call occurred. It was fixed
to identify `fantom_v1.json` by exact basename.

A subsequent zero-provider inventory exposed that purely per-stratum selection
could reuse the same conversation across question families. Before any model
outcome existed, the selection protocol was tightened to require global
conversation-level disjointness.

## Frozen selection

Machine-readable manifest:
- `eval/fantom/selection_v01.json`

Selection salt:
- `HCL-FANTOM-EXT-V01-20260921`

Selection is deterministic and metadata-only:
1. fixed stratum order;
2. candidates ranked by SHA256 of fixed salt + question identity;
3. greedily accept only candidates whose FANToM conversation ID has not already
   been selected;
4. belief MC option orientation is fixed by SHA256 before model calls.

Final sample:
- **32 questions**
- **32 distinct FANToM conversations**

Strata:
- 4 inaccessible first-order belief MC;
- 4 inaccessible second-order belief MC;
- 4 inaccessible answerability binary;
- 4 inaccessible information-accessibility binary;
- 4 accessible first-order belief MC;
- 4 accessible second-order belief MC;
- 8 fact controls.

Question texts, benchmark answers and conversation contents are not copied into
this repository. The runner reconstructs the selected records from the
hash-verified official archive.

## Input context

Use FANToM `short_context` only.

This matches the benchmark's easier/current standard reporting surface and
keeps the v0.1 pilot bounded. Full-context FANToM is not consumed in this round.

## Paired model configuration

Common:
- provider: existing DeepSeek endpoint/key;
- model: `deepseek-flash`;
- seed: `42`;
- temperature: `0.0`;
- no new credential/provider;
- no prompt tuning after launch.

Control:
- direct DeepSeek answer to the FANToM task prompt;
- max output tokens: 4096;
- existing backend empty-content behavior unchanged.

Treatment:
- frozen HCL v0.3 answer loop;
- same DeepSeek backend;
- HCL state semantics remain frozen;
- HCL always-on;
- state budget remains 8192;
- answer/check budgets remain 4096;
- Decision Policy v0.2.1a and Action Checker are **not used** for this static QA
  benchmark.

The test therefore targets transfer of the cognition/answer-loop layer, not the
interactive action-policy layer.

## Prompt format

Common benchmark header:

`This is a theory-of-mind test. Answer only from the supplied conversation and follow the requested output format exactly.`

Belief MC:
- deterministic A/B ordering from the frozen manifest;
- request exactly `[A]` or `[B]`.

Answerability binary:
- include FANToM's target fact question;
- request exactly `yes` or `no`.

Information-accessibility binary:
- include FANToM's provided information statement;
- request exactly `yes` or `no`.

Fact control:
- request a short answer phrase only.

## Deterministic scoring

Belief MC:
- parse the first unambiguous A/B answer token;
- correct iff it matches frozen `correct_option`;
- missing/ambiguous format = incorrect.

Binary:
- normalize leading `yes/true` to yes and `no/false` to no;
- anything else = incorrect.

Fact:
- lower-case whitespace token F1 using the benchmark's simple Counter overlap
  formulation.

No LLM judge, embeddings, semantic regrading or post-hoc answer adjudication is
used in v0.1.

## Output/privacy boundary

Artifacts may contain:
- question ID / set ID / stratum;
- normalized prediction;
- correctness/F1;
- response byte count/hash;
- HCL mode/uncertainty/check status/revision flags;
- error type.

Artifacts must not contain:
- FANToM conversation text;
- benchmark question text;
- benchmark correct/wrong answer text;
- HCL full state text;
- prompts;
- credentials.

## Sharding

- 4 deterministic shards;
- 8 selected questions per shard;
- maximum parallelism 2;
- all 32 questions must complete before interpretation.

No partial result may be used for tuning or protocol changes.

## Primary evidence

Primary questions (16):
- 8 inaccessible belief MC;
- 4 inaccessible answerability binary;
- 4 inaccessible information-accessibility binary.

Primary paired outcome:
- improved = control wrong / HCL correct;
- worsened = control correct / HCL wrong;
- net paired gain = improved - worsened.

Primary subblocks:
- inaccessible belief;
- information-state access (answerability + info accessibility).

## Control stability

Control questions:
- 8 accessible belief MC;
- 8 fact controls.

## Predeclared interpretation

A **positive pilot signal** requires all of:

1. primary net paired gain >= **+2** over 16 questions;
2. HCL accuracy is not below control in either primary subblock;
3. accessible-belief net paired gain >= **-1**;
4. fact mean token-F1 delta >= **-0.05**.

A **negative pilot signal** is recorded if either:
- primary net paired gain < 0; or
- accessible-belief net paired gain <= -2; or
- fact mean token-F1 delta < -0.05.

Anything else is **mixed/inconclusive**.

These are pilot interpretation rules, not statistical significance claims.

## Claim boundary

This run can support only:
- bounded independent external cognition-transfer evidence on selected FANToM
  short-context questions.

It cannot support:
- an official FANToM leaderboard result;
- full FANToM performance;
- interactive Decision Policy efficacy;
- cross-base transfer;
- training;
- HCL 1.0 certification.

After launch the 32 selected questions are consumed diagnostic/validation
evidence and cannot be called fresh again.
