# FANToM External Validation v0.1 — Paired Pilot Closure

## Decision

**MIXED / INCONCLUSIVE**

This is the predeclared interpretation from the frozen v0.1 protocol.

It is not a post-hoc relabeling.

## Canonical run

- workflow: `FANToM External Validation v0.1 Paired Pilot`
- run: `35603955200`
- launch commit: `862f2471eb0269bf24bd135a9400d1ca24335af0`
- result: **SUCCESS**
- aggregate artifact: `10641159030`
- aggregate artifact SHA-256:
  `80b08aff9a4ea6ca996d5ca674333b18bd392a98c9a0b472a187ef09646210aa`

Source:
- FANToM repository: `skywalker023/fantom`
- pinned upstream commit:
  `1cae6fa30f5ba04ca0fff5f5716b5ba7055e2e85`
- official dataset SHA-256:
  `1d08dfa0ea474c7f83b9bc7e3a7b466eab25194043489dd618b4c5223e1253a4`

Sample:
- **32 questions**
- **32 distinct FANToM conversations**
- short-context input
- fixed selection salt
- exact question IDs frozen before provider calls
- no LLM judge or semantic regrading.

## Execution history

Zero-provider inventory:
- final run `35602513859`: SUCCESS
- provider calls: 0
- 870 FANToM sets inventoried
- final selection made globally conversation-disjoint before model launch.

First paired launch:
- run `35603596148`
- preflight: PASS
- all four paid shards failed before any provider call with
  `ModuleNotFoundError: No module named 'hcl'`
- provider calls: **0**
- model outcomes observed: **0**
- protocol/sample/prompt/scoring were not changed.

Minimal recovery:
- commit `cf6acc22bc7c00f23e8785dfb8f1c81501b76e52`
- only script-entrypoint import bootstrapping changed;
- recovery preflight added real `--help` runner startup checks.

Recovery run:
- `35603955200`
- preflight: PASS
- shard 0: PASS
- shard 1: PASS
- shard 2: PASS
- shard 3: PASS
- aggregate: PASS
- artifact privacy checks: PASS.

## Primary result

Primary information-asymmetry block:
- n = **16**
- control correct = **14 / 16**
- HCL correct = **14 / 16**
- control accuracy = **87.5%**
- HCL accuracy = **87.5%**
- improved = **0**
- worsened = **0**
- both correct = **14**
- both wrong = **2**
- net paired gain = **0**

The positive-signal threshold required net paired gain >= +2.

Therefore the predeclared positive gate is **not met**.

## Primary subblocks

### Inaccessible belief

Combined first-/second-order:
- n = **8**
- control = **6 / 8 = 75%**
- HCL = **6 / 8 = 75%**
- improved = 0
- worsened = 0
- both wrong = 2
- net paired gain = 0

First-order inaccessible belief:
- n = 4
- control = 3/4
- HCL = 3/4
- net paired gain = 0

Second-order inaccessible belief:
- n = 4
- control = 3/4
- HCL = 3/4
- net paired gain = 0

### Information-state access

Answerability + information accessibility:
- n = **8**
- control = **8 / 8 = 100%**
- HCL = **8 / 8 = 100%**
- improved = 0
- worsened = 0
- net paired gain = 0

By individual stratum:
- inaccessible answerability binary: 4/4 vs 4/4
- inaccessible information-accessibility binary: 4/4 vs 4/4

## Stability controls

### Accessible belief

- n = **8**
- control = **8 / 8 = 100%**
- HCL = **8 / 8 = 100%**
- improved = 0
- worsened = 0
- net paired gain = 0

This satisfies the predeclared no-regression stability condition.

### Fact control

- n = **8**
- control mean token-F1:
  **0.3005864506**
- HCL mean token-F1:
  **0.3156938487**
- paired mean delta:
  **+0.0151073982**

This is above the predeclared negative threshold of -0.05 and therefore does not
indicate a fact-control regression.

## Question-level structural observation

Across all **24 categorical questions**:
- there were **zero** control-wrong/HCL-correct pairs;
- there were **zero** control-correct/HCL-wrong pairs.

Thus HCL changed no categorical correctness outcome in this bounded pilot.

The two primary misses were both shared by control and HCL:
- one inaccessible first-order belief item;
- one inaccessible second-order belief item.

On the second-order shared miss, HCL entered `EPISTEMIC` mode with high
uncertainty and performed both revision passes, but the final categorical answer
was still not scored correct.

This is useful diagnostic metadata, but the consumed FANToM items must not be
used for tuning.

## Predeclared interpretation

Positive required all of:
1. primary net paired gain >= +2;
2. no primary-subblock accuracy regression;
3. accessible-belief net >= -1;
4. fact F1 delta >= -0.05.

Negative was triggered by any of:
- primary net < 0;
- accessible-belief net <= -2;
- fact F1 delta < -0.05.

Observed:
- primary net = 0;
- no primary-subblock regression;
- accessible-belief net = 0;
- fact F1 delta = +0.0151.

Therefore:

**predeclared interpretation = MIXED**

## What this establishes

Supported:
- frozen HCL v0.3 answer-loop transfers cleanly to a benchmark independent of
  the consumed SOTOPIA-Hard environment templates;
- on this bounded sample, HCL did not degrade accessible-belief or factual
  controls;
- HCL handled all selected information-accessibility/answerability questions at
  the same ceiling accuracy as direct DeepSeek;
- no categorical efficacy gain was observed.

Not supported:
- HCL improves FANToM;
- HCL improves Theory-of-Mind accuracy generally;
- official FANToM leaderboard performance;
- full-context FANToM performance;
- interactive Decision Policy efficacy;
- cross-base-model transfer;
- HCL 1.0 efficacy certification.

## Research interpretation

The most important fact is not merely the 87.5% tie.

The paired outcomes show a near-complete **ceiling / identity problem** for this
32-question pilot:

- information-state questions were 100% in both arms;
- accessible beliefs were 100% in both arms;
- inaccessible beliefs produced the same six correct and same two incorrect
  outcomes.

That means this pilot has little power to distinguish the frozen HCL cognition
layer from a strong direct DeepSeek baseline.

The correct response is **not** to tune HCL against the two consumed failures.
The next validation should increase discriminative power while remaining
independent of these consumed questions.

Potential future directions must be separately predeclared, for example:
- a harder independent benchmark;
- FANToM full-context on a completely disjoint unused conversation sample;
- cross-base transfer where the base model has more headroom for HCL to help.

No next benchmark is authorized by this closure.
