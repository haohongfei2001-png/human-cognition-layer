# Hi-ToM External Validation v0.1 — Paired Pilot Closure

## Decision

**EFFICACY NOT EVALUABLE — EXECUTION RELIABILITY FAILURE**

The predeclared efficacy interpretation is not computed.

The frozen protocol required all 60 paired rows to complete with zero failures
before aggregation. That integrity requirement was not met.

## Canonical run

- workflow: `Hi-ToM External Validation v0.1 Paired Pilot`
- run: `35675119858`
- launch commit: `888426d64f3d92a852a2dfc111fd1ae442e85e04`
- result: **FAILURE**
- preflight: **SUCCESS**
- paired shards: **6 / 6 terminal, all six shard jobs failed**
- aggregate: **FAILURE by frozen integrity gate**
- aggregate summary artifact: **none**

Frozen source / behavior:
- Hi-ToM source commit: `4279d3f783ff4f3b9fcced2a2fec9f6328683f82`
- Hi-ToM data blob: `23ab2aee6b2e80115dd645d88b91529ad2a29309`
- protocol anchor: `02effce47e02585d88844a3555279ce80170952f`
- HCL behavior anchor: `ce36d7e6f911910f97437c23455dee33e0e7bc82`

## Execution completeness

Frozen sample:
- 60 questions
- 60 distinct stories
- 6 deterministic shards × 10
- maximum parallelism 2

Observed terminal execution:
- requested: **60**
- completed paired rows: **36**
- failed rows: **24**
- persisted failure type: **RuntimeError for all 24 failures**

By shard:
- shard 0: 6 completed / 4 RuntimeError
- shard 1: 7 completed / 3 RuntimeError
- shard 2: 7 completed / 3 RuntimeError
- shard 3: 6 completed / 4 RuntimeError
- shard 4: 4 completed / 6 RuntimeError
- shard 5: 6 completed / 4 RuntimeError

Shard artifacts:
- shard 0: artifact `10673378397`, digest
  `sha256:eb4b03d8b824ac3bfb1110441b67f10b115f2ad680ae2d664220dafd71317fe9`
- shard 1: artifact `10673741821`, digest
  `sha256:21e459f1634349a0052d2ef7d8a4e8b48ac1d2b04e2c29bc09cfb22ff3a79047`
- shard 2: artifact `10674425658`, digest
  `sha256:f807a4083539ac2c9d122c32e0c7069dd7b0104bcbd1693a96bbab74101f9685`
- shard 3: artifact `10674942540`, digest
  `sha256:774c8db7845987ccb85161a2b6961ed8da90d0d170f848bcb383b3394d54a1b9`
- shard 4: artifact `10675821553`, digest
  `sha256:8f5a63e04efbfdfb8e96e6ac392c66c3af47f7b29e440acd42b9c4687235336d`
- shard 5: artifact `10675502283`, digest
  `sha256:98765558d3ea13408bc4c2701c8988a86312fcbb2ca04125f6bbeff434a67d6a`

All shard privacy-boundary checks passed before upload.

## Aggregate integrity behavior

The frozen aggregator downloaded all six shard artifacts and then rejected the
run with:

`RuntimeError: Hi-ToM aggregate integrity failure`

This is expected protective behavior because failures were present and only 36
of 60 paired rows completed.

No aggregate summary was produced. No partial accuracy, paired gain, subgroup
score, or positive / negative / mixed interpretation is canonical.

The aggregate failure is therefore not evidence of a second efficacy defect; it
is the intended integrity gate preventing interpretation of incomplete data.

## Failure provenance boundary

The persisted shard artifacts intentionally record only:
- sample identity / non-content metadata;
- completed result metadata;
- failure sample ID;
- exception class.

They do **not** persist exception text, prompts, stories, questions, choices,
responses, messages, cognition state, or credentials.

Therefore the 24 RuntimeError rows cannot be retrospectively assigned a more
specific cause from the canonical artifacts alone.

The frozen HCL answer loop does contain an explicit RuntimeError path when
state generation produces no parseable JSON after three attempts. The observed
failure class is consistent with that known path, but this run does **not**
prove that every RuntimeError arose from that cause.

Do not overclaim the root cause.

## Efficacy interpretation

The predeclared efficacy gate required all 60 rows to complete before any result
interpretation.

Observed:
- complete paired rows: 36 / 60
- failures: 24 / 60

Therefore:
- positive gate: **NOT EVALUATED**
- negative gate: **NOT EVALUATED**
- mixed / inconclusive gate: **NOT EVALUATED**

This run does not establish that HCL helps or harms Hi-ToM performance.

The correct result class is:

**INCOMPLETE / EFFICACY NOT EVALUABLE**

## Consumption boundary

Paid execution began on all selected evidence.

All 60 selected Hi-ToM rows are therefore **consumed** under the frozen
predeclaration and must not be used for:
- prompt tuning;
- state-schema tuning;
- retry-policy tuning;
- parser tuning;
- behavioral repair;
- promotion decisions based on rerunning the same rows as fresh evidence.

Do not rerun the failed rows as a replacement efficacy result.

## Engineering / research implication

The immediate blocker is execution reliability, not benchmark score.

Before consuming another external benchmark sample:
1. keep HCL v0.3 state semantics frozen;
2. do not tune against these consumed Hi-ToM rows;
3. create an independent synthetic, non-Hi-ToM state-generation reliability
   audit;
4. distinguish state JSON parse exhaustion from provider / transport and other
   runtime failures using content-free diagnostics;
5. reproduce any abstract failure class independently before changing behavior;
6. if a repair is justified, validate it on independent synthetic fixtures and
   existing regressions;
7. only then predeclare any new external evidence.

No model training, cross-base transfer, or additional Hi-ToM holdout is
authorized by this closure.
