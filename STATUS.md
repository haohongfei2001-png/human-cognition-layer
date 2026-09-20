# Canonical Status

## Project

Human Cognition Layer (HCL)

## Current phase

**PHASE-04 — Decision-policy repair and fresh holdout validation**

## Core doctrine

The HCL module is the research asset.

The base model is replaceable. Benchmarks are measurement instruments.

HCL remains in the loop for every input. Performance regressions are used to diagnose and improve the module; they are not a reason to silently bypass HCL.

See:
- `docs/MODULE_FIRST_DOCTRINE.md`
- `hcl/HCL_V0_3_SPEC.md`

## State semantics

**HCL v0.3 STATE SEMANTICS: FROZEN**

Frozen contract:
- `hcl/v03/FROZEN_STATE_SEMANTICS.md`
- `hcl/v03/state_schema.json`
- `hcl/v03/STATE_BUILDER_PROMPT.md`

Frozen modes:
- SIMPLE
- EPISTEMIC
- CAUSAL_AMBIGUITY

Frozen principles include:
- world truth != agent knowledge;
- evidence bridges for information transfer;
- first-order vs second-order belief separation;
- world-belief divergence as epistemic;
- preservation of genuine competing causes;
- minimal sufficient modeling;
- question-granularity calibration;
- explicit low/medium/high uncertainty semantics.

## State-fidelity evidence

### Fresh 36-case boundary suite

Independent run `35414125494`:
- raw 32 / 36.

After failure audit and explicit fixes:
Regression run `35414572919`:
- raw 35 / 36;
- 100% mode accuracy;
- 100% schema validity;
- one underdetermined false-belief fixture retained but excluded from the gate.

### Fresh 24-case paired-boundary suite

Run `35415058681`:
- raw 22 / 24;
- mode 95.8%;
- uncertainty 91.7%;
- schema 100%.

The two failures produced the decision-granularity and uncertainty-calibration rules.

### Final fresh 18-case freeze holdout

Run `35415237645`:
- raw **17 / 18**;
- mode 94.4%;
- uncertainty 94.4%;
- schema 100%.

The sole failed fixture expected ambiguity for wet trousers + dripping umbrella immediately after heavy rain. HCL classified the rain explanation as overwhelmingly supported at the question's coarse granularity. This matched principles frozen before the run and was adjudicated as a fixture-design error.

Historical raw scores are preserved; no post-hoc 18/18 claim is made.

See:
- `reports/HCL_V03_STATE_V02_ADJUDICATION.md`
- `reports/HCL_V03_PAIRED_ADJUDICATION.md`
- `reports/HCL_V03_FREEZE_ADJUDICATION.md`

## CogToM status

CogToM remains:
- a diagnostic/regression benchmark;
- not unquestionable human-state truth;
- not training data.

Representative baseline run `35407860416`:
- 200 stratified groups;
- 46 / 46 subcategories;
- mean group accuracy 96.0%;
- 15 groups with any error.

The owner's first two audits demonstrated that some forced-choice gold items can omit information bridges or collapse genuine latent-cause ambiguity.

## Historical HCL task-performance experiments

HCL v0.1 on disjoint 100-group CogToM:
- vanilla 98.6%;
- HCL 96.8%;
- -1.8 pp.

HCL v0.2 selective experiment:
- vanilla 97.0%;
- selective HCL 97.0%.

v0.2 is historical only; selective bypass is not canonical.

## Current engineering target

Implement the always-on full loop:

```text
Input
  ↓
HCL v0.3 cognition state
  ↓
Base-model draft
  ↓
HCL consistency/calibration check
  ↓
Final answer
```

The checker must inspect:
1. explicit-fact consistency;
2. agent information access;
3. first-/second-order belief consistency;
4. unjustified collapse of ambiguity;
5. unjustified over-uncertainty;
6. answer granularity.

## Current gate

**ANSWER_LOOP_CHECKER_GATE_PASSED**

No model training yet.

After answer-loop unit tests:
1. run CogToM regression diagnostics with HCL always-on;
2. move to SOTOPIA-Hard as the main method-validation environment;
3. test cross-base-model transfer;
4. only then decide whether independent training data / adapters are justified.

Long-term route:

```text
HCL state semantics (FROZEN)
→ answer loop
→ CogToM regression
→ SOTOPIA-Hard
→ cross-base transfer
→ training/adapters if justified
→ EQ-Bench 4
```


## Answer-loop checker result

Always-on answer-loop implementation:
- `hcl/v03/answer_loop.py`
- `hcl/v03/backends.py`
- `hcl/v03/ANSWER_LOOP_PROTOCOL.md`

First adversarial checker suite:
- run `35415496804`
- raw 9 / 12
- revision-family hit rate: 100%
- final-check pass rate: 100%
- all raw failures were audit/test expectation issues, not checker logic failures.

Fresh adversarial checker suite:
- run `35415880531`
- raw **11 / 12**
- revision-family hit rate: **100%**
- final-check pass rate: **100%**
- sole raw failure was a fixture expectation that silently assumed an agent's initial knowledge.

See:
- `reports/HCL_V03_ANSWER_CHECKER_V01_ADJUDICATION.md`
- `reports/HCL_V03_ANSWER_CHECKER_V02_ADJUDICATION.md`

Decision:
**HCL v0.3 answer checker gate PASSED.**

Completed:
- SOTOPIA custom-agent smoke: PASS;
- fair single-setting Hard A/B: PASS;
- repaired official-rubric score extraction: PASS.

Scored single-setting run `35430762893`:
- tested-role control overall: **-0.8571**
- tested-role HCL overall: **2.1429**
- paired delta: **+3.0000**
- HCL cognition states: 10

This is one-setting evidence only, not an aggregate efficacy claim.

Fixed 10-setting SOTOPIA-Hard paired slice: **CLOSED**

Primary run `35431739928` + failed-setting closure `35449140294`:
- usable paired settings: **10 / 10**
- control overall mean: **2.7429**
- HCL overall mean: **2.7000**
- paired mean delta: **-0.0429**
- improved / tied / worsened: **4 / 4 / 2**
- relationship mean delta: **+0.80**
- social-rules mean delta: **+1.20**
- knowledge mean delta: **-1.20**
- financial/material mean delta: **-0.60**
- goal mean delta: **-0.30**

Interpretation:
- no aggregate improvement claim;
- strongest repeated weakness is knowledge acquisition (negative in 8/10);
- some raw-score losses arise from benchmark tradeoffs where direct goal
  attainment can conflict with explicit interpersonal boundaries;
- genuine implementation weakness remains: correct cautious cognition can map
  to overly passive / low-information action.

The 10 settings are now a diagnostic set and must not be treated as fresh
generalization evidence after policy changes.

Current canonical execution:
1. validate the new HCL Decision Policy on independent synthetic fixtures;
2. if that gate passes, integrate it after the frozen HCL state and before
   action generation;
3. run a previously unused SOTOPIA-Hard holdout slice;
4. only if the signal survives, add repeated runs / uncertainty estimates;
5. then test cross-base-model transfer.


## Decision-policy repair status

Decision Policy synthetic gate:
- run `35449770050`
- raw **11 / 12**
- sole raw failure was adjudicated as a taxonomy-boundary issue: the policy
  chose DIRECT_PROGRESS for concretizing an already offered coffee alternative,
  while the fixture allowed only COMMIT / ALTERNATIVE_PATH.
- raw 11/12 is preserved; no post-hoc 12/12 claim.
- decision: **synthetic gate PASSED**.

Updated SOTOPIA integration smoke:
- run `35450003786`
- **PASS**
- Decision Policy is present between frozen HCL state and action generation.
- current-observation duplication is removed.
- environment-forced `none` turns now still build and log HCL cognition,
  satisfying the always-on doctrine.

Fresh generalization test:
- workflow: `SOTOPIA-Hard Fresh Holdout 10 A/B`
- run `35450229188`
- settings: previously unused Hard ordinals **10-19**
- sharded into five 2-setting jobs, max parallelism 2
- status at launch: queued/running
- diagnostic settings 0-9 are not reused for this generalization result.


## Fresh SOTOPIA-Hard Decision Policy holdout

Run `35450229188`: **PASS / 10 of 10 paired settings completed**

Previously unused Hard ordinals 10-19:
- control mean overall: **2.4714**
- HCL + Decision Policy mean overall: **2.8857**
- paired mean delta: **+0.4143**
- improved / tied / worsened: **7 / 1 / 2**

Dimension paired deltas:
- believability: **+0.50**
- relationship: **+0.40**
- knowledge: **0.00**
- secret: **0.00**
- social_rules: **+0.50**
- financial/material: **+1.20**
- goal: **+0.30**

This fresh slice is consistent with the intended action-policy repair:
the diagnostic slice's knowledge (-1.20), financial/material (-0.60), and goal
(-0.30) deficits did not reproduce.

Claim boundary:
- encouraging fresh-holdout signal;
- not a final efficacy claim;
- n=10 and one trajectory per arm;
- custom DeepSeek partner/evaluator, not official leaderboard-comparable.

**Current gate: HOLDOUT_SIGNAL_POSITIVE_REQUIRES_REPEATS**

Do not tune against settings 10-19 before repeat-stability testing.
Next execution:
1. freeze current implementation;
2. repeat the same fixed holdout with predefined additional seeds / repeats;
3. estimate paired stability and variance;
4. if stable, move to cross-base-model transfer.


## Repeat stability — seeds 42 / 43 / 44

Runs:
- seed 42: `35450229188`
- seeds 43/44: `35482453412`

Paired overall deltas:
- seed 42: **+0.4143**
- seed 43: **-0.0857**
- seed 44: **+0.0143**
- mean of run-level paired means: **+0.1143**

Stable dimension signs across all three:
- believability: positive
- relationship: positive
- knowledge: non-negative
- social_rules: positive

Unstable:
- financial/material: +1.20, -0.10, -0.10
- goal: +0.30, -1.60, -1.20

**Current gate: REPEAT_STABILITY_MIXED_GOAL_REGRESSION**

The original positive overall holdout does not robustly repeat.
Do not weaken/bypass HCL. Diagnose the remaining goal-pursuit instability at
the Decision Policy/action layer without training on exact SOTOPIA instances.


## Goal-regression component diagnosis and Action Checker

Repeat audit isolated two materially different sources of goal loss:
- some SOTOPIA goal penalties are metric conflicts where literal private-goal
  pursuit rewards behavior that crosses interpersonal boundaries;
- at least one repeated loss is a real control-flow defect: the generic answer
  checker can block a Decision Policy action merely because uncertainty remains,
  conflating "acting under uncertainty" with "claiming uncertainty is resolved".

Independent Decision Policy goal-pursuit audit:
- run `35492464682`
- raw **11 / 12**
- sole raw miss was a taxonomy-boundary case where choosing a lawful alternative
  path was semantically correct.
- conclusion: no broad Decision Policy inability on option value / probe budgets
  was established.

Action-specific checker:
- implementation: `hcl/v03/action_checker.py`
- synthetic run: `35492634398`
- result: **14 / 14 PASS**
- explicitly validates reversible/conditional actions under uncertainty while
  still rejecting false certainty, hard-constraint violations, looping,
  irreversibility mismatch, invalid action types, and plan mismatch.

SOTOPIA integration:
- `HCLSocialAgent` now uses the Action Checker instead of the generic answer
  checker for social actions.
- integration smoke run: `35492711369`
- current state at launch: in progress.

**Current gate: ACTION_CHECKER_INTEGRATION_SMOKE**
