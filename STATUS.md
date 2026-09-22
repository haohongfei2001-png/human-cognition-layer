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

Action-checker integration smoke:
- run `35492711369`
- **PASS / SUCCESS**

Fresh SOTOPIA-Hard action-checker holdout:
- run `35493750111`
- previously unused Hard ordinals **20-29**
- five 2-setting shards, max parallelism 2
- current state at launch: running

**Current gate: FRESH_ACTION_CHECKER_HOLDOUT_20_29_RUNNING**


## Fresh 20-29 preflight correction

Run `35493750111` failed during dataset preflight **before any SOTOPIA episode ran**.

Observed from the pinned official dataset:
- Hard environment list length: **20**
- agent_index length: **20**

The attempted ordinals 20-29 therefore did not exist in the environment-level
list. No fresh benchmark trajectories were consumed by this failed run.

Important upstream audit:
SOTOPIA's official benchmark implementation does **not** collapse each hard
environment to one agent pair. It iterates every `EnvAgentComboStorage` that
matches each hard environment. Our earlier slice helper selected only the first
stable agent combo per environment.

Current corrective gate:
1. inventory the full expanded Hard env-agent-combo set exactly;
2. mark all previously consumed first-combo settings as non-fresh;
3. if unused Hard combos exist, select the next 10 previously unseen expanded
   combos before running the Action Checker holdout;
4. if no unused Hard combos exist, stop claiming fresh Hard evidence and move
   to a different external validation source.

**Current gate: HARD_EXPANDED_COMBO_INVENTORY**


## Expanded Hard inventory and combo-level holdout

Inventory run `35495418673`: **SUCCESS**

Exact pinned Hard inventory:
- 20 environment positions
- 5 env-agent combos per position
- **100 expanded settings total**
- 20 previously consumed first-combo settings
- **80 unused env-agent combos remain**

The previous 20-29 environment-ordinal attempt consumed no episodes and is
methodologically void.

Predeclared fresh-combo robustness holdout:
- run `35496131831`
- environment ordinals: `0,2,4,6,8,10,12,14,16,18`
- combo ordinal: `1`
- expanded ordinals: `1,11,21,31,41,51,61,71,81,91`
- seed: `42`
- current state at launch: running
- claim boundary: fresh env-agent combinations inside previously seen
  environment templates; not fresh-scenario evidence.

**Current gate: EXPANDED_COMBO_HOLDOUT_RUNNING**


## Expanded-combo Action Checker holdout result

Run `35496131831`: **SUCCESS / 10 of 10 paired settings**

Previously unused env-agent combos:
`1,11,21,31,41,51,61,71,81,91`

Aggregate:
- control overall: **2.2714**
- HCL + Decision Policy + Action Checker: **2.4286**
- paired delta: **+0.1571**
- improved / tied / worsened: **4 / 2 / 4**

Dimension deltas:
- believability: **+0.2**
- relationship: **+0.4**
- knowledge: **0.0**
- secret: **+0.4**
- social_rules: **+1.0**
- financial/material: **+0.3**
- goal: **-1.2**

Interpretation:
- Action Checker repair survives new persona pairing at the overall level;
- the old systematic knowledge deficit remains absent;
- **goal pursuit remains the principal unresolved weakness** and reproduces the
  negative repeat signal seen under seeds 43/44.

Freshness boundary:
- fresh env-agent/persona combinations only;
- environment templates were previously seen.

Unused expanded combos remaining after this run: **70**.

**Current gate: GOAL_PURSUIT_REMAINS_UNRESOLVED_AFTER_ACTION_CHECKER**


## Goal-negative audit and Decision Policy v0.2

Expanded-combo goal-negative audit:
- source run: `35496131831`
- six goal-negative cases classified as:
  - 2 metric conflicts that must **not** be optimized away;
  - 2 infeasible-bargaining / evaluator-granularity cases with no established
    policy defect;
  - 2 genuine Decision Policy defects:
    1. adverse self-anchoring;
    2. premature constraint crystallization.

Unified failure pattern:
- v0.1 can overvalue information probing even when the probe itself shapes the
  counterpart's commitment;
- v0.1 can upgrade a soft opening position into a hard constraint too early.

Independent synthetic baseline on frozen v0.1:
- run `35511100930`
- raw **11 / 12**
- sole miss was adjudicated as a strategy-label boundary: actual behavior made
  the correct bounded counterproposal despite the INFORMATION_PROBE label.
- interpretation: the capability existed latently; the external failure is a
  reliability problem, not total conceptual absence.

Decision Policy v0.2:
- adds explicit soft-position vs hard-constraint semantics;
- treats probes as interventions with possible anchoring cost;
- allows concrete proposals to serve as information acquisition;
- requires probe-to-progress transition when enough information exists;
- requires a bounded counterproposal before EXIT when no incompatible hard
  boundary is known.

v0.2 synthetic gate:
- run `35511183476`
- **12 / 12 PASS**
- no HCL state-semantic change.

Integration smoke:
- run `35511266476`
- current state: running.

Next predeclared external holdout after smoke:
- environment ordinals: `1,3,5,7,9,11,13,15,17,19`
- combo ordinal: `2`
- expanded ordinals: `7,17,27,37,47,57,67,77,87,97`
- seed: `42`
- all 10 env-agent combinations are previously unused.

**Current gate: DECISION_POLICY_V02_INTEGRATION_SMOKE**


## Decision Policy v0.2 external validation launch

Integration smoke:
- run `35511266476`
- **SUCCESS**

Predeclared v0.2 fresh expanded-combo holdout:
- run `35511421008`
- expanded ordinals: `7,17,27,37,47,57,67,77,87,97`
- environment ordinals: `1,3,5,7,9,11,13,15,17,19`
- combo ordinal: `2`
- seed: `42`
- all 10 env-agent combinations were unused before launch
- module frozen before outcomes

**Current gate: DECISION_POLICY_V02_FRESH_EXPANDED_HOLDOUT_RUNNING**


## Decision Policy v0.2 fresh expanded holdout closure

Run `35511421008`: **SUCCESS / 10 of 10 paired settings completed**

Predeclared expanded ordinals:
`7,17,27,37,47,57,67,77,87,97`

Aggregate:
- control overall: **2.5714**
- HCL + Decision Policy v0.2 overall: **2.6857**
- paired delta: **+0.1143**
- improved / tied / worsened: **5 / 3 / 2**

Dimension deltas:
- believability: **+0.3**
- relationship: **+0.8**
- knowledge: **-0.2**
- secret: **0.0**
- social_rules: **+0.1**
- financial/material: **+0.4**
- goal: **-0.6**

Goal-negative expanded settings:
- `27`: -1 — infeasible bargaining / evaluator granularity; no general policy
  defect established.
- `57`: -8 — metric conflict around exclusive scarce-resource possession; do
  not repair for raw goal score.
- `87`: -4 — explicit bodily/health need after one bounded counterproposal;
  evaluator sensitivity, no general policy defect established.
- `97`: -3 — **verification deadlock confirmed**.

Expanded `97` reproduces the previously documented Hard-setting-19 failure
under a different env-agent combination:
- HCL correctly identifies a decision-critical ownership uncertainty;
- repeated verification / external-check actions do not yield a resolving
  observation in the current interaction interface;
- option value decays while HCL remains in INFORMATION_PROBE / defer behavior;
- the episode ends without a bounded fallback.

This is **not** a frozen cognition-state defect. It is a decision/action-layer
stopping-rule and observability defect.

See:
- `reports/SOTOPIA_V02_FRESH_EXPANDED_GOAL_NEGATIVE_AUDIT.md`

Freshness boundary:
- these were fresh env-agent/persona combinations;
- environment templates were previously seen;
- after this run, **60** expanded Hard env-agent combinations remain unused.

**Current gate: VERIFICATION_DEADLOCK_CONFIRMED_REQUIRES_INDEPENDENT_SYNTHETIC_REPAIR**

Next canonical execution:
1. keep HCL v0.3 state semantics frozen and HCL always-on;
2. do not tune against expanded 27 / 57 / 87;
3. design a minimal decision/action-layer repair for the abstract
   non-resolving-verification / option-decay failure class;
4. include probe budget, observable-resolution detection, option-decay
   accounting, bounded constraint-respecting fallback, and no fabricated
   verification result;
5. validate first on independent synthetic fixtures using unrelated domains;
6. only after that gate passes may another previously unused SOTOPIA expanded
   combo set be consumed;
7. do not start model training or cross-base transfer until this reliability
   gate is closed.


## Verification-deadlock v0.2.1 synthetic repair closure

Independent synthetic repair:
- canonical run: `35518761327`
- commit under test: `e5714e522e2cb0e02749c370f0a563d498c74f98`
- raw artifact: `10607148842`
- verification Decision Policy suite: **12 / 12**
- Action Checker anti-loop suite: **5 / 5**
- negotiation-position regression: **12 / 12**
- goal-pursuit regression: **11 / 12 raw**

The sole raw goal-pursuit miss is the same historical
`gp03_irreversible_legal_uncertainty` taxonomy boundary already present in
pre-repair run `35492464682`:
- actual strategy remains `ALTERNATIVE_PATH`;
- goal state is `BLOCKED`;
- ownership/legal hard constraints are preserved;
- verification is `UNRESOLVABLE_IN_INTERFACE`;
- bounded fallback is required.

A dedicated regression checker accepts only this exact previously adjudicated
case with the safe structure above. New/multiple failures still fail. Raw 11/12
is preserved; no post-hoc 12/12 claim is made.

Failure history before canonical success is preserved:
- `35517862848`: 11/12 — fallback structural invariant exposed;
- `35517997649`: 11/12 — probe-family counting across a genuinely new channel
  exposed a fixture-semantics error;
- `35518116442`: new repair suites passed, negotiation regression 11/12 exposed
  a strategy-taxonomy compatibility issue;
- `35518350648`: repair + negotiation gates passed, historical raw goal 11/12
  still blocked workflow success;
- `35518711508`: same historical raw boundary still blocked until the exact,
  bounded adjudication gate was wired;
- `35518761327`: canonical raw evidence + bounded adjudication succeeded.

Independence audit:
- repair fixtures use unrelated domains and copy no SOTOPIA persona, dialogue,
  exact price, evaluator answer, or record-sale wording;
- only the abstract failure class is transferred into synthetic validation.

Frozen-state audit:
- no HCL v0.3 frozen state-semantics file changed;
- HCL remains always-on;
- no training started;
- no cross-base-model transfer started.

SOTOPIA integration smoke:
- run `35519183891`
- commit `f6e591db8d22ae0e2175769852a1a8aa9c3e106a`
- **SUCCESS**
- raw smoke artifact `10607982455`;
- HCL state, Decision Policy, turn log, repaired verification fields, and
  forced-noop always-on path are present and asserted.

The smoke is adapter/integration-path evidence only, not a benchmark episode or
efficacy result.

See:
- `reports/HCL_VERIFICATION_DEADLOCK_V021_SYNTHETIC_GATE.md`

**Current gate: VERIFICATION_DEADLOCK_SYNTHETIC_AND_SMOKE_PASSED_REQUIRES_PREDECLARED_UNUSED_COMBO_HOLDOUT**

Next canonical execution:
1. freeze the smoke-tested v0.2.1 decision/action implementation;
2. predeclare a previously unused expanded Hard env-agent combo slice and its
   freshness boundary before viewing outcomes;
3. explicitly state that the holdout is fresh persona/pairing evidence inside
   already-seen environment templates, **not fresh-scenario evidence**;
4. run complete paired control vs HCL episodes on the pinned SOTOPIA dataset;
5. preserve raw outcomes and do not tune against the holdout before closure.


## Decision Policy v0.2.1 post-repair holdout predeclaration

Smoke-tested behavior-bearing implementation is frozen at:
`f6e591db8d22ae0e2175769852a1a8aa9c3e106a`

Freeze contract:
- `hcl/v03/FROZEN_DECISION_POLICY_V021.md`

Predeclaration:
- `hcl/v03/FRESH_EXPANDED_COMBO_V021_PREDECLARATION.md`

Predeclared unused expanded-combo slice:
- environment ordinals: `1,3,5,7,9,11,13,15,17,19`
- combo ordinal: `3`
- expanded ordinals: `8,18,28,38,48,58,68,78,88,98`
- seed: `42`

Freshness:
- all 10 selected env-agent combinations are previously unused;
- combo ordinal 3 was untouched by the recorded expanded-combo holdouts;
- the selected expanded ordinals are disjoint from the 40 previously consumed
  successful expanded settings;
- **all environment templates have been seen before**.

Therefore the only allowed freshness claim is:
**fresh persona/pairing combinations inside already-seen environment templates**.

This is explicitly **not fresh-scenario evidence**.

Selection is deterministic:
- untouched combo ordinal 3;
- odd environment parity across the full Hard list;
- environment 19 is included by parity rule, not cherry-picked.

No behavior-bearing code change is allowed between the smoke-tested freeze anchor
and holdout execution. The holdout workflow verifies this invariant before each
paired job.

**Current gate: V021_POST_REPAIR_UNUSED_COMBO_HOLDOUT_PREDECLARED_READY**

Next execution:
1. trigger the frozen paired holdout;
2. consume no other expanded combos concurrently;
3. do not tune against partial results;
4. require all 10 paired settings + aggregate before interpretation;
5. preserve raw results and freshness boundary.


## Decision Policy v0.2.1 post-repair holdout launch

Workflow:
- `SOTOPIA-Hard Decision Policy v0.2.1 Post-Repair Expanded Holdout`
- run: `35523303566`
- launch commit: `b5823c48fe7c488c7d8fb9c2079465deeff9ef51`

Predeclared settings:
- expanded ordinals: `8,18,28,38,48,58,68,78,88,98`
- combo ordinal: `3`
- seed: `42`

The workflow verifies that behavior-bearing files are unchanged from the
smoke-tested freeze anchor
`f6e591db8d22ae0e2175769852a1a8aa9c3e106a` before each paired job.

The launch is a complete paired benchmark execution on the pinned official
SOTOPIA dataset. No partial result may be used for tuning.

**Current gate: V021_POST_REPAIR_HOLDOUT_INCOMPLETE — 8/10 paired settings completed; 2 failed.**

Run `35523303566` is completed/failure, not running. Ordinal 48 failed with
`HCL decision policy returned no valid JSON after 3 attempts`; ordinal 88 failed
with an OpenAI missing-key AuthenticationError. The aggregate failed because the
predeclared complete 10-pair set was not produced. These are execution failures,
not an efficacy verdict. All ten attempted combinations are consumed diagnostic
history; no later replay may call this slice fresh.

A same-provider output-repair plumbing fix is COMPLETE on main `af11819b0306fabda4bf4ad408b690456742a29b`. Exact-main integration run `35548423886` succeeded; PR1 candidate run `35548234948` also succeeded.
It explicitly binds evaluator repair to the original DeepSeek model/endpoint,
forwards that endpoint and its existing custom key, and rejects alternate repair
identities before forwarding custom credentials. No new key, seed change,
additional retry, HCL behavior change or holdout rerun is included. The earlier
forwarding-only candidate is superseded because it missed the upstream OpenAI
default model. See `reports/SOTOPIA_V021_OUTPUT_REPAIR_CLOSURE.md`.

The no-provider-call integration certification and publication are complete.
Preserve the original 8/10 incomplete holdout; ordinal 48 and
remaining efficacy certification are unresolved, not PASS. No new holdout or
freshness declaration is opened by this repair.


## Decision JSON diagnostic plumbing closure (2026-09-21)

Execution `HCL-JSON-DIAGNOSTICS-20260921-aem01` is COMPLETE; writer released.
Runtime main `88a6322ea5f32afa437cece39665e20110e016c0` merged PR2 candidate
`ac95f4f33e65d5cf6ca2e10051f9f33aa352bd04`. Independent review accepted the
5-file scope. Exact-main integration run `35558532085` and candidate run
`35558285692` both succeeded: 6 actual pinned-SOTOPIA routing tests and
6 synthetic diagnostic-transparency tests, plus the frozen-file gate.

The optional `HCL_DECISION_DIAGNOSTICS=1` observer is off by default and records
only response metadata. It does not change the frozen behavior, call count,
seed, retry policy, credentials or outcome. No model request or holdout was
launched or replayed. See `reports/DECISION_JSON_DIAGNOSTICS.md`.

The original holdout remains **8/10 INCOMPLETE**. The preserved ordinal48 log
does not identify its raw response or exact cause; no JSON efficacy repair or
fresh evidence is claimed. All ten attempted combinations remain consumed.
Any subsequent behavior change must follow the project freeze/amendment and
new synthetic/smoke gates; this closure grants no new holdout authorization.


## Ordinal 48 bounded Decision-JSON diagnostic replay

The original v0.2.1 post-repair holdout remains **8/10 INCOMPLETE**.
This section does not reopen that holdout and does not create fresh evidence.

Predeclaration:
- `reports/ORDINAL48_DECISION_JSON_DIAGNOSTIC_PREDECLARATION.md`

Fixed diagnostic setting:
- original run: `35523303566`
- environment ordinal: `9`
- combo ordinal: `3`
- expanded ordinal: `48`
- seed: `42`
- treatment only: `HCLSocialAgent`
- same DeepSeek model/provider and existing credential path
- pinned SOTOPIA commit unchanged
- certified same-provider output-repair patch applied
- `HCL_DECISION_DIAGNOSTICS=1`

Bounded execution:
- maximum 2 treatment episode attempts, matching the historical outer retry
  ceiling;
- frozen Decision Policy still has maximum 3 JSON attempts per call;
- stop after the first successful episode;
- no control replay;
- no new seed, temperature, token budget, model, prompt, retry policy,
  behavior-bearing HCL change, or fresh holdout.

Allowed output is metadata only:
- accepted / empty / no-parseable-object / transport-exception outcome;
- response byte count and SHA256 when available;
- episode-level success/failure and exception class;
- no prompt, response text, transcript, persona, credential or efficacy score.

A green diagnostic workflow means that bounded metadata evidence was collected;
it does **not** mean ordinal 48 passed.

**Current gate: ORDINAL48_CONSUMED_DIAGNOSTIC_REPLAY_PREDECLARED_READY**


## Ordinal 48 Decision-JSON diagnostic replay closure

Bounded consumed-setting diagnostic:
- run: `35585685155`
- launch commit: `8dfe862613213933983f4f8c20ae7363e1738732`
- artifact: `10632519832`
- attempts: **2 / 2**
- both attempts reproduced:
  `HCL decision policy returned no valid JSON after 3 attempts`
- no fresh or efficacy claim is permitted.

Raw Decision Policy wrapper metadata:

Attempt 1:
- accepted object 1333 bytes;
- accepted object 1707 bytes;
- empty 0 bytes;
- empty 0 bytes;
- empty 0 bytes.
- classification: **empty-output family**.

Attempt 2:
- accepted object 1502 bytes;
- accepted object 1421 bytes;
- empty 0 bytes;
- accepted object 2263 bytes;
- empty 0 bytes;
- non-empty 1333 bytes with no parseable object;
- empty 0 bytes.
- classification: **mixed invalid-output family**.

No wrapper event was a transport exception.

Important:
`OpenAICompatibleBackend.complete()` internally makes up to four provider
requests before returning one wrapper result. Therefore one wrapper-level
`empty` event means all four underlying provider completions returned empty
final content.

The final three empty wrapper events in attempt 1 therefore establish at least
**12 consecutive underlying provider completions with empty content** at the
failing Decision Policy turn.

This reproduces ordinal 48 as a real Decision Policy output/transport failure,
not merely an original logging ambiguity. It does not identify provider
`finish_reason`, separate reasoning-content usage, or token exhaustion.

See:
- `reports/ORDINAL48_DECISION_JSON_DIAGNOSTIC_RESULT.md`

Do not increase retry count or change Decision Policy prompt based on this
evidence alone.

**Current gate: ORDINAL48_PROVIDER_ATTEMPT_METADATA_REQUIRED**

Next canonical work:
1. add opt-in provider-attempt-level, content-free Decision Policy diagnostics;
2. preserve the existing 4-attempt backend loop exactly;
3. record finish reason, content bytes/hash, optional reasoning-content
   bytes/hash and token usage only;
4. certify observer transparency without provider calls;
5. if certified, run the same consumed ordinal48 bounded diagnostic again;
6. do not create a new holdout or behavior-bearing amendment yet.


## Ordinal 48 provider-attempt diagnostic predeclaration

The wrapper-level diagnostic reproduced ordinal48 twice and established repeated
empty final content. The next step remains diagnostic only.

Predeclaration:
- `reports/ORDINAL48_PROVIDER_ATTEMPT_DIAGNOSTIC_PREDECLARATION.md`

Execution boundary:
- same consumed expanded ordinal 48;
- environment 9 / combo 3 / seed 42;
- HCL treatment only;
- same model/provider/endpoint/key;
- maximum 2 episode attempts;
- existing backend maximum 4 provider requests per `complete()`;
- existing Decision Policy maximum 3 JSON attempts;
- no prompt, retry, model, temperature, token-limit or HCL behavior change.

Provider-attempt observer is opt-in via
`HCL_PROVIDER_ATTEMPT_DIAGNOSTICS=1` and records only:
- provider attempt ordinal;
- finish reason;
- content bytes/hash;
- optional reasoning/refusal bytes/hash;
- token usage;
- transport-exception outcome without exception text.

Synthetic no-network tests must pass before the consumed provider replay can
execute.

**Current gate: ORDINAL48_PROVIDER_ATTEMPT_DIAGNOSTIC_PREDECLARED_READY**


## Ordinal 48 provider-attempt diagnostic closure

Consumed provider-attempt diagnostic:
- run: `35588167021`
- launch commit: `1409f159c57fdb1aab4f959b7e4a2a405c48228b`
- artifact: `10634471138`
- artifact SHA-256:
  `2f17a73edb80bf65ef947691d173309ffbccd0c39cfc9ceb27902546f92d537d`
- attempts: **2 / 2**
- provider events: **37**
- both attempts reproduced the exact frozen Decision Policy no-valid-JSON
  RuntimeError;
- original 8/10 holdout remains incomplete and consumed.

Provider-level result:
- non-empty final-content attempts: **7**
- empty final-content attempts: **30**
- transport exceptions: **0**

For **every one of the 30 empty attempts**:
- `finish_reason=length`;
- `max_tokens=4096`;
- `completion_tokens=4096`;
- `reasoning_tokens=4096`;
- separate reasoning content is non-empty;
- final `content` is zero bytes.

Successful provider attempts in the same replay end with
`finish_reason=stop`, non-empty final content and reasoning usage below the
4096 ceiling.

Attempt 1 is especially decisive:
- two earlier Decision Policy calls succeed;
- the failing turn then produces three outer JSON attempts;
- each outer attempt invokes all four backend provider attempts;
- all **12 consecutive provider attempts** end at the 4096 reasoning-token
  ceiling with zero final content.

**Root cause confirmed: Decision Policy's explicit 4096 completion budget is
exhausted by provider thinking/reasoning before final JSON content is emitted.**

This is not primarily:
- the ordinal88 provider-routing bug;
- a missing credential;
- a transport exception;
- an HCL state-semantic defect;
- an Action Checker defect;
- insufficient retry count.

See:
- `reports/ORDINAL48_PROVIDER_ATTEMPT_DIAGNOSTIC_RESULT.md`

No behavior-bearing repair has been applied.

A minimal amendment proposal is frozen for owner review:
- `hcl/v03/DECISION_POLICY_V021A_OUTPUT_BUDGET_AMENDMENT_PROPOSAL.md`
- proposed sole runtime change: Decision Policy `max_tokens 4096 -> 8192`;
- model/provider/prompt/seed/retry counts/state semantics/checker remain
  unchanged.

The proposal raises the maximum billable output-token envelope:
- current worst-case failing `build_plan`: 49,152 output tokens;
- proposed theoretical ceiling: 98,304 output tokens.

Actual spend could fall if the larger budget avoids repeated failed calls, but
the permitted per-request/token envelope increases.

Per current execution authority this is a **cost-boundary change**.

**Current gate: ORDINAL48_ROOT_CAUSE_CONFIRMED_AWAITING_OWNER_OUTPUT_BUDGET_AUTHORIZATION**

Until owner authorization:
1. do not change Decision Policy `max_tokens`;
2. do not lower/disable thinking as a workaround;
3. do not increase retries;
4. do not rerun ordinal48 again;
5. do not start a new holdout;
6. preserve HCL v0.3 frozen state and always-on behavior;
7. preserve the original 8/10 incomplete verdict.


## Decision Policy v0.2.1a output-budget amendment execution

Owner explicitly authorized the bounded Decision Policy output-budget increase.

Authorized behavior-bearing amendment:
- commit: `ce36d7e6f911910f97437c23455dee33e0e7bc82`
- sole runtime change:
  `HCLDecisionPolicy.max_tokens 4096 -> 8192`

Freeze contract:
- `hcl/v03/FROZEN_DECISION_POLICY_V021A.md`

Authorization does not extend to:
- output budgets above 8192;
- extra retries;
- provider/model changes;
- disabling/lowering thinking;
- a new holdout;
- training or cross-base transfer.

Required validation sequence:
1. exact amendment-scope diff check;
2. no-network budget/retry certification;
3. verification-stopping Decision Policy synthetic;
4. Action Checker anti-loop regression;
5. negotiation-position regression;
6. historical goal-pursuit raw regression with only the existing bounded
   taxonomy adjudication;
7. SOTOPIA integration smoke;
8. consumed ordinal48 diagnostic confirmation.

The original 8/10 holdout remains incomplete regardless of diagnostic replay.

**Current gate: V021A_OUTPUT_BUDGET_AMENDMENT_VALIDATION_RUNNING**


## Decision Policy v0.2.1a synthetic/regression validation closure

Canonical validation:
- run: `35594584730`
- artifact: `10635169895`
- result: **SUCCESS**

Raw evidence:
- verification-stopping Decision Policy: **12/12**
- Action Checker anti-loop: **5/5**
- negotiation-position: **12/12**
- historical goal-pursuit: **11/12 raw**
- sole goal-pursuit miss remains exactly
  `gp03_irreversible_legal_uncertainty`;
- existing exact bounded taxonomy adjudication: PASS;
- raw 11/12 is preserved.

Amendment-scope gate proved the only behavior-bearing change from
pre-amendment main `610344ed7a916ca656b1e8dd23b68a091a8a5e6d` is:
- Decision Policy default output budget `4096 -> 8192`.

Action Checker, state builder, answer/check budgets, prompt, taxonomy, model,
provider, seed, temperature and retry counts remain unchanged.

See:
- `reports/HCL_V021A_OUTPUT_BUDGET_GATE.md`

**Current gate: V021A_SYNTHETIC_PASSED_REQUIRES_INTEGRATION_SMOKE**

Next:
1. run the SOTOPIA custom-agent smoke with behavior locked to
   `ce36d7e6f911910f97437c23455dee33e0e7bc82`;
2. if smoke passes, run only consumed ordinal48 diagnostic confirmation;
3. do not start a new holdout.


## Decision Policy v0.2.1a integration smoke closure

SOTOPIA custom-agent smoke:
- run: `35595222418`
- result: **SUCCESS**
- artifact: `10636505914`
- artifact SHA-256:
  `714a08ec85b0c2c49b9cd5c358767eb775139263abcbf7ec844191f1120e1b5e`

Before execution the workflow verified behavior-bearing files were unchanged
from v0.2.1a anchor
`ce36d7e6f911910f97437c23455dee33e0e7bc82`.

Raw smoke assertions include:
- HCL state present;
- Decision Policy present;
- repaired verification fields present;
- Action Checker first/final checks PASS;
- environment-forced no-op still passes through HCL.

The smoke is integration-path evidence, not efficacy evidence.

Consumed ordinal48 confirmation is predeclared in:
- `reports/ORDINAL48_V021A_CONFIRMATION_PREDECLARATION.md`

The confirmation is constrained to the already-consumed environment9/combo3/
expanded48/seed42 treatment setting and cannot repair the original 8/10 holdout.

**Current gate: V021A_SMOKE_PASSED_REQUIRES_CONSUMED_ORDINAL48_CONFIRMATION**


## Decision Policy v0.2.1a synthetic validation closure

Owner-authorized output-budget amendment:
- behavior commit: `ce36d7e6f911910f97437c23455dee33e0e7bc82`
- sole behavior change:
  `HCLDecisionPolicy.max_tokens 4096 -> 8192`

Canonical validation:
- run `35594584730`
- **SUCCESS**
- artifact `10635169895`

Evidence:
- exact amendment-scope diff: PASS;
- no-network budget/retry certification: PASS;
- verification-stopping Decision Policy: **12/12**;
- Action Checker anti-loop: **5/5**;
- negotiation-position regression: **12/12**;
- goal-pursuit regression: **11/12 raw**, exactly the historical
  `gp03_irreversible_legal_uncertainty` taxonomy boundary;
- exact bounded adjudication: PASS;
- no fixture weakening and no new raw regression.

First validation attempt `35594522038` failed only because pinned SOTOPIA was
not installed before a structural runner test. That CI dependency was fixed;
no HCL behavior changed.

See:
- `reports/HCL_V021A_OUTPUT_BUDGET_VALIDATION.md`

**Current gate: V021A_SYNTHETIC_GATE_PASSED_REQUIRES_SOTOPIA_SMOKE**

Next:
1. run SOTOPIA custom-agent smoke on v0.2.1a;
2. if smoke passes, run consumed ordinal48 diagnostic confirmation only;
3. do not start a new holdout;
4. preserve original post-repair holdout as 8/10 incomplete.


## Decision Policy v0.2.1a final canonical closure

This section **supersedes all earlier v0.2.1a intermediate gates above**.

Owner-authorized runtime amendment:
- behavior anchor: `ce36d7e6f911910f97437c23455dee33e0e7bc82`
- sole behavior change:
  `HCLDecisionPolicy.max_tokens 4096 -> 8192`

Canonical evidence chain:

1. Synthetic/regression gate
   - run `35594584730`: **SUCCESS**
   - verification-stopping Decision Policy: **12/12**
   - Action Checker anti-loop: **5/5**
   - negotiation-position: **12/12**
   - historical goal-pursuit: **11/12 raw**
   - sole raw miss remains exactly
     `gp03_irreversible_legal_uncertainty`
   - existing exact bounded adjudication: PASS.

2. SOTOPIA custom-agent integration smoke
   - run `35595222418`: **SUCCESS**
   - HCL state present;
   - Decision Policy present;
   - Action Checker PASS;
   - repaired verification fields present;
   - forced environment no-op remains HCL always-on.

3. Consumed ordinal48 confirmation
   - run `35595588158`: **SUCCESS**
   - artifact `10636821661`
   - episode attempts executed: **1**
   - final episode outcome: **success**
   - exact no-valid-JSON RuntimeError: **false**
   - provider attempts: **3**
   - every provider call requested `max_tokens=8192`
   - all three provider calls ended `finish_reason=stop`
   - reasoning tokens: **2499, 5878, 6123**
   - no empty final content;
   - no provider retry within a backend call;
   - no outer Decision Policy JSON retry;
   - no transport exception.

The 5878- and 6123-reasoning-token calls directly confirm that the old 4096
budget was insufficient for this consumed setting and that the authorized 8192
budget provided enough headroom for final JSON.

4. Infrastructure baseline
   - same-provider/output-repair CI baseline advanced to the validated v0.2.1a
     behavior anchor;
   - exact-main run `35596299688`: **SUCCESS**.

See:
- `reports/HCL_V021A_OUTPUT_BUDGET_GATE.md`
- `reports/HCL_V021A_OUTPUT_BUDGET_CLOSURE.md`
- `reports/ORDINAL48_V021A_CONFIRMATION_PREDECLARATION.md`

Claim boundary:
- Decision Policy v0.2.1a is the **validated canonical runtime**;
- HCL v0.3 state semantics remain frozen;
- HCL remains always-on;
- no training or cross-base-model transfer has started;
- consumed ordinal48 confirmation is diagnostic only;
- the original post-repair holdout remains **8/10 INCOMPLETE**;
- ordinal48 is not retroactively promoted;
- no old combo-3 setting regains freshness;
- no new holdout is authorized by this closure.

A redundant additional smoke was triggered later while reconciling a stale
STATUS tail. It is non-canonical and does not gate this closure; no downstream
work depends on it.

**Current gate: V021A_VALIDATED_CANONICAL_RUNTIME — NO_NEW_HOLDOUT_AUTHORIZED**

Next research work requires a new explicit validation decision:
- either design a genuinely independent external validation source / unused
  evidence plan;
- or authorize a bounded new holdout with a predeclared freshness boundary.

Until then:
1. do not tune v0.2.1a against consumed SOTOPIA settings;
2. do not start another holdout automatically;
3. do not change the 8192 budget or retry policy;
4. preserve the original 8/10 incomplete holdout verdict.


## FANToM external validation v0.1 authorization

Owner authorized the next independent external validation stage.

Selected external source:
- benchmark: FANToM
- repository: `skywalker023/fantom`
- pinned commit: `1cae6fa30f5ba04ca0fff5f5716b5ba7055e2e85`
- official dataset archive SHA-256:
  `1d08dfa0ea474c7f83b9bc7e3a7b466eab25194043489dd618b4c5223e1253a4`

Rationale:
- directly tests belief, answerability and information access under
  multi-party information asymmetry;
- includes a no-false-belief control condition;
- does not reuse the consumed SOTOPIA-Hard environment templates.

ToMATO was rejected for this gate after source audit because its generation
pipeline uses SOTOPIA agents/environments. EQ-Bench 4 is deferred because its
official methodology introduces additional commercial persona/judge provider
credential and cost boundaries.

Current execution is **inventory only**:
- zero provider/model calls;
- fixed hash salt `HCL-FANTOM-EXT-V01-20260921`;
- deterministic 32-question target across predeclared strata;
- no model result is viewed before exact question IDs are committed.

See:
- `reports/FANTOM_EXTERNAL_VALIDATION_V01_PLAN.md`

**Current gate: FANTOM_EXT_V01_ZERO_PROVIDER_INVENTORY_RUNNING**


## FANToM external validation v0.1 inventory closure and paired predeclaration

Independent external source:
- FANToM repository: `skywalker023/fantom`
- pinned upstream commit:
  `1cae6fa30f5ba04ca0fff5f5716b5ba7055e2e85`
- official dataset SHA-256:
  `1d08dfa0ea474c7f83b9bc7e3a7b466eab25194043489dd618b4c5223e1253a4`

Final zero-provider inventory:
- run: `35602513859`
- **SUCCESS**
- artifact: `10638929742`
- artifact SHA-256:
  `b00425bd66e1747803cc245a3e39e7bcc0fda0ba50152dd3bac08ac807d24e7e`
- FANToM sets inventoried: **870**
- provider/model calls: **0**

Historical inventory attempts are preserved:
- `35602156116`: failed before selection because the archive member lookup
  assumed a directory prefix; no provider call occurred;
- `35602254720`: successful metadata inventory, but pre-launch review found
  that independent per-stratum selection could reuse a conversation;
- before any model outcome existed, selection was tightened to global
  conversation-level disjointness;
- `35602513859`: final successful conversation-disjoint inventory.

Frozen sample:
- machine manifest: `eval/fantom/selection_v01.json`
- **32 questions**
- **32 distinct FANToM conversations**
- selection salt: `HCL-FANTOM-EXT-V01-20260921`
- exact IDs and belief A/B orientation are committed before provider calls.

Strata:
- 4 inaccessible first-order belief MC;
- 4 inaccessible second-order belief MC;
- 4 inaccessible answerability binary;
- 4 inaccessible information-accessibility binary;
- 4 accessible first-order belief MC;
- 4 accessible second-order belief MC;
- 8 fact controls.

Paired protocol:
- `reports/FANTOM_EXTERNAL_VALIDATION_V01_PREDECLARATION.md`
- protocol anchor:
  `2ae1aca1bb1e5b89057a94d10097cbcc8722a7ff`
- HCL behavior anchor:
  `ce36d7e6f911910f97437c23455dee33e0e7bc82`

Common:
- FANToM short context;
- DeepSeek `deepseek-flash`;
- same existing endpoint/key;
- seed 42;
- temperature 0;
- same user benchmark prompt in both arms.

Control:
- direct DeepSeek answer.

Treatment:
- frozen HCL v0.3 answer loop;
- state 8192; answer/check 4096;
- HCL state always-on;
- Decision Policy / Action Checker not used because FANToM v0.1 is static
  cognition QA.

Predeclared primary evidence:
- 16 information-asymmetry questions;
- paired improved/worsened count;
- inaccessible belief and information-state subblocks.

Predeclared stability controls:
- 8 accessible belief MC;
- 8 fact controls.

Interpretation thresholds were frozen before launch in the predeclaration.
No LLM judge, embedding regrade, semantic regrade or post-hoc answer
adjudication is allowed.

Privacy boundary:
artifacts contain only IDs, strata, normalized predictions/scores, hashes and
compact HCL metadata. FANToM conversations/questions/gold text/prompts/full HCL
state are not persisted.

Paid paired workflow has a mandatory **zero-provider preflight**:
1. verify HCL behavior unchanged from v0.2.1a anchor;
2. verify FANToM selection/protocol/runner/aggregator unchanged from protocol
   anchor;
3. rerun deterministic protocol unit tests;
4. redownload/hash-check official FANToM;
5. reconstruct and prove the same frozen 32-question sample.

Only after all preflight checks pass may the four 8-question shards run, with
maximum parallelism 2. No partial model result may be used for tuning.

**Current gate: FANTOM_EXT_V01_PAIRED_PILOT_PREDECLARED_READY**


## FANToM v0.1 first-launch execution recovery

First paired launch:
- run: `35603596148`
- zero-provider preflight: **SUCCESS**
- all four paired shards: **FAILED before provider/model calls**
- common error:
  `ModuleNotFoundError: No module named 'hcl'`
- provider/model calls: **0**
- predictions/paired outcomes observed: **0**
- aggregate: failed because no shard artifacts existed.

This was a script-entrypoint Python path bug. The runner imported `hcl.*`
before adding the repository root to `sys.path`.

Minimal repair:
- commit `cf6acc22bc7c00f23e8785dfb8f1c81501b76e52`
- only startup/import bootstrapping changed;
- selection, prompt, scoring, model/provider, seed/temperature, HCL behavior and
  interpretation thresholds remain unchanged.

Recovery workflow:
- protocol anchor advanced to the import-fix commit;
- preflight now executes both runner and aggregator `--help` entrypoints before
  any provider-backed shard can start.

See:
- `reports/FANTOM_EXTERNAL_VALIDATION_V01_EXECUTION_RECOVERY.md`

Because the failed launch made zero provider calls and exposed no model outcome,
the recovery remains the same frozen 32-question predeclared pilot. The failed
launch remains preserved in history.

**Current gate: FANTOM_EXT_V01_PAIRED_PILOT_EXECUTION_RECOVERY_READY**


## FANToM external validation v0.1 final closure

External source:
- FANToM
- pinned upstream commit:
  `1cae6fa30f5ba04ca0fff5f5716b5ba7055e2e85`
- official dataset SHA-256:
  `1d08dfa0ea474c7f83b9bc7e3a7b466eab25194043489dd618b4c5223e1253a4`

Frozen sample:
- **32 questions**
- **32 distinct FANToM conversations**
- exact IDs frozen before provider calls;
- short-context input;
- deterministic belief option orientation;
- no LLM judge / embedding regrade / post-hoc semantic adjudication.

Canonical paired run:
- `35603955200`
- **SUCCESS**
- all 4 paired shards complete;
- aggregate complete;
- aggregate artifact: `10641159030`
- artifact SHA-256:
  `80b08aff9a4ea6ca996d5ca674333b18bd392a98c9a0b472a187ef09646210aa`

Execution recovery history:
- first launch `35603596148` failed all shards at
  `ModuleNotFoundError: No module named 'hcl'`;
- failure occurred before any provider/model call;
- zero predictions/outcomes were observed;
- minimal import-path repair:
  `cf6acc22bc7c00f23e8785dfb8f1c81501b76e52`;
- sample/prompt/scoring/model/HCL behavior were unchanged;
- recovery preflight added real script-entrypoint startup checks.

Primary information-asymmetry block:
- n = **16**
- control: **14/16 = 87.5%**
- HCL: **14/16 = 87.5%**
- improved: **0**
- worsened: **0**
- both correct: 14
- both wrong: 2
- net paired gain: **0**

Primary subblocks:
- inaccessible belief:
  - control **6/8 = 75%**
  - HCL **6/8 = 75%**
  - net paired gain 0
- inaccessible answerability + information accessibility:
  - control **8/8 = 100%**
  - HCL **8/8 = 100%**
  - net paired gain 0

Stability controls:
- accessible belief:
  - control **8/8 = 100%**
  - HCL **8/8 = 100%**
  - net paired gain 0
- fact control:
  - control mean token-F1 **0.3005864506**
  - HCL mean token-F1 **0.3156938487**
  - paired mean delta **+0.0151073982**

Across all 24 categorical questions:
- control-wrong / HCL-correct: **0**
- control-correct / HCL-wrong: **0**

The two primary belief misses were shared by both arms:
- one inaccessible first-order belief item;
- one inaccessible second-order belief item.

The consumed FANToM items must not be used for tuning.

Predeclared interpretation:
- positive required primary net paired gain >= +2 plus stability conditions;
- negative required primary net < 0 or a predeclared control regression;
- observed primary net = 0 with no control regression.

Therefore:

**FANToM v0.1 interpretation: MIXED / INCONCLUSIVE**

See:
- `reports/FANTOM_EXTERNAL_VALIDATION_V01_PREDECLARATION.md`
- `reports/FANTOM_EXTERNAL_VALIDATION_V01_EXECUTION_RECOVERY.md`
- `reports/FANTOM_EXTERNAL_VALIDATION_V01_CLOSURE.md`

Claim boundary:
- this is bounded independent external cognition-transfer evidence;
- it shows clean transfer and no detected categorical regression;
- it does **not** show categorical efficacy gain;
- it is not an official FANToM leaderboard result;
- it is not full-context FANToM;
- it is not interactive Decision Policy efficacy;
- it is not cross-base transfer;
- it is not HCL 1.0 certification.

Research implication:
the sample is largely ceiling/identity-limited against direct DeepSeek.
Information-state and accessible-belief strata are saturated, while the two
inaccessible-belief errors are identical in both arms.

Do not tune HCL against these consumed failures.

**Current gate: FANTOM_EXT_V01_MIXED_REQUIRES_NEXT_VALIDATION_DECISION**

Next work must be separately predeclared and should increase discriminative
power without reusing these consumed questions. Candidate directions include:
1. a harder independent benchmark;
2. FANToM full-context on completely disjoint unused conversations;
3. cross-base transfer where the base model has more headroom for HCL to help.

No next benchmark is automatically authorized by this closure.


## FANToM external validation v0.2 full-context authorization

Owner authorized continuation after FANToM v0.1 closed MIXED/INCONCLUSIVE.

v0.2 objective:
increase discriminative power without reusing any consumed v0.1 conversation.

Fixed source:
- FANToM upstream commit:
  `1cae6fa30f5ba04ca0fff5f5716b5ba7055e2e85`
- official dataset SHA-256:
  `1d08dfa0ea474c7f83b9bc7e3a7b466eab25194043489dd618b4c5223e1253a4`

Inventory protocol:
- full-context input;
- fixed salt:
  `HCL-FANTOM-FULL-V02-20260921`;
- exclude every conversation in `eval/fantom/selection_v01.json`;
- enforce global conversation-level disjointness;
- follow official FANToM full-context accessibility logic for answerability and
  information-accessibility binary families;
- zero provider/model calls before exact sample freeze.

Target sample:
- 8 inaccessible first-order belief MC;
- 8 inaccessible second-order belief MC;
- 8 full-context inaccessible answerability binary;
- 8 full-context inaccessible information-accessibility binary;
- 4 accessible first-order belief MC;
- 4 accessible second-order belief MC;
- 8 fact controls.

Total:
- **48 questions**
- **48 new conversations**
- **0 v0.1 conversation overlap**

See:
- `reports/FANTOM_EXTERNAL_VALIDATION_V02_PLAN.md`

**Current gate: FANTOM_EXT_V02_ZERO_PROVIDER_INVENTORY_RUNNING**


## FANToM external validation v0.2 full-context predeclaration closure

Zero-provider inventory:
- run: `35608769203`
- result: **SUCCESS**
- artifact: `10642254950`
- artifact SHA-256:
  `99ca92874cbc5cbf1640829e5155ac21a447a0c8dcfcf640bb9d883f9a8f8afd`
- provider/model calls: **0**
- v0.1 conversations excluded: **32**
- final v0.2 sample: **48 questions / 48 distinct conversations**
- v0.1 conversation overlap: **0**

Frozen selection:
- `eval/fantom/selection_v02.json`
- salt: `HCL-FANTOM-FULL-V02-20260921`
- context: **full**
- exact IDs and belief A/B orientation committed before provider calls.

Strata:
- 8 inaccessible first-order belief MC
- 8 inaccessible second-order belief MC
- 8 full-context inaccessible answerability binary
- 8 full-context inaccessible information-accessibility binary
- 4 accessible first-order belief MC
- 4 accessible second-order belief MC
- 8 fact controls

Frozen paired protocol:
- `reports/FANTOM_EXTERNAL_VALIDATION_V02_PREDECLARATION.md`
- protocol anchor:
  `7d0f3f2fedb80e367ae5cfd0a1fcdf7a71dfaa4a`
- HCL behavior anchor:
  `ce36d7e6f911910f97437c23455dee33e0e7bc82`

Common:
- DeepSeek `deepseek-flash`
- existing endpoint/key
- seed 42
- temperature 0
- same full-context user benchmark prompt in both arms

Control:
- direct DeepSeek

Treatment:
- frozen HCL v0.3 answer loop
- state budget 8192
- answer/check budget 4096
- HCL always-on
- Decision Policy / Action Checker excluded because this is static cognition QA

Primary:
- 32 questions
- 16 inaccessible belief
- 16 information-state

Controls:
- 8 accessible belief
- 8 fact

Predeclared positive:
- primary net paired gain >= +3
- no primary-subblock accuracy regression
- accessible belief net >= -1
- fact token-F1 delta >= -0.05

Predeclared negative:
- primary net < 0 OR
- accessible belief net <= -2 OR
- fact token-F1 delta < -0.05

Otherwise:
- MIXED / INCONCLUSIVE

Formal workflow requires zero-provider preflight before paid shards:
1. HCL behavior diff = zero from behavior anchor;
2. v0.2 selection/protocol/runner/aggregator/tests diff = zero from protocol anchor;
3. unit tests + runner/aggregator entrypoint smoke;
4. official FANToM archive hash verification;
5. deterministic reconstruction of the same 48 IDs;
6. explicit proof of v0.1 conversation overlap = 0.

Execution:
- 6 deterministic shards × 8 questions
- max parallelism 2
- no partial outcome inspection/tuning
- aggregate only after all 48 complete.

**Current gate: FANTOM_EXT_V02_FULL_CONTEXT_PAIRED_PREDECLARED_READY**


## FANToM external validation v0.2 full-context execution

Canonical workflow:
- run: `35609498441`
- launch commit: `fae8f8810f63c459b01f8fae7a97159bb976dae1`

Zero-provider preflight:
- HCL behavior freeze: PASS
- FANToM v0.2 protocol freeze: PASS
- protocol unit tests: PASS
- runner/aggregator entrypoint smoke: PASS
- official dataset SHA verification: PASS
- deterministic 48-question reconstruction: PASS
- v0.1 conversation overlap: 0

Paid execution:
- 6 deterministic shards × 8 questions
- maximum parallelism 2
- no partial outcome inspection/tuning
- aggregate required before interpretation.

No behavior/protocol change is permitted while this run is open.

**Current gate: FANTOM_EXT_V02_FULL_CONTEXT_PAIRED_RUNNING**


## FANToM external validation v0.2 full-context final closure

Canonical run:
- `35609498441`
- **SUCCESS**
- 6/6 paired shards complete
- aggregate complete
- aggregate artifact: `10644692374`
- artifact SHA-256:
  `6a6098bf460646f19070e6d8943eb5a0943d18aec972cfba4839e5eea49d82a7`

Sample:
- **48 questions**
- **48 distinct full-context FANToM conversations**
- **0 conversation overlap with v0.1**
- exact sample/protocol frozen before provider calls.

Primary information-asymmetry block:
- n = **32**
- control = **26/32 = 81.25%**
- HCL = **26/32 = 81.25%**
- improved = **2**
- worsened = **2**
- net paired gain = **0**

Primary inaccessible-belief:
- control = **12/16 = 75%**
- HCL = **13/16 = 81.25%**
- improved 1 / worsened 0
- net = **+1**
- the gain occurs in inaccessible second-order belief.

Primary information-state:
- control = **14/16 = 87.5%**
- HCL = **13/16 = 81.25%**
- improved 1 / worsened 2
- net = **-1**

Breakdown:
- full-context answerability:
  - 6/8 vs 6/8
  - improved 1 / worsened 1
  - one HCL-worsened item has normalized prediction **null** after both HCL
    revision passes, so the raw failure includes an output-interface/format
    failure;
- full-context information accessibility:
  - control 8/8
  - HCL 7/8
  - net -1
  - raw categorical regression preserved.

Stability controls:
- accessible belief:
  - control 7/8
  - HCL 7/8
  - net 0
- fact token-F1:
  - control mean **0.2128511971**
  - HCL mean **0.2676538557**
  - paired delta **+0.0548026587**

Predeclared result:
- positive threshold not met;
- negative threshold not met;
- **MIXED / INCONCLUSIVE**.

Compared with v0.1:
- v0.1 had categorical identity/ceiling;
- v0.2 is more discriminative;
- belief shows a small favorable signal;
- information-state shows a small unfavorable signal;
- no net primary efficacy gain is established.

See:
- `reports/FANTOM_EXTERNAL_VALIDATION_V02_PREDECLARATION.md`
- `reports/FANTOM_EXTERNAL_VALIDATION_V02_CLOSURE.md`

All 48 v0.2 questions are now consumed.
Do not tune HCL against these questions.

**Current gate: FANTOM_EXT_V02_MIXED_REQUIRES_INDEPENDENT_INFO_STATE_INTERFACE_AUDIT**

Next canonical work:
1. keep frozen HCL v0.3 state semantics unchanged;
2. create synthetic non-FANToM fixtures for strict yes/no and A/B output
   preservation, answerability, information access and high-uncertainty forced
   categorical answers;
3. evaluate current frozen HCL answer loop before any repair;
4. if a repeatable abstract defect is established, repair only the answer/output
   interface layer on independent synthetic fixtures;
5. repeat existing state/answer-loop regressions before consuming any new
   external benchmark evidence;
6. do not use FANToM v0.1/v0.2 content as training/tuning data.


## HCL independent info-state / output-interface audit v0.1 predeclaration

Triggered by FANToM v0.2 mixed result:
- belief subblock net +1;
- information-state subblock net -1;
- one HCL-worsened answerability item had no parser-valid yes/no verdict after
  both revision passes.

Consumed FANToM content is not used for tuning.

Independent synthetic audit:
- predeclaration:
  `reports/HCL_INFO_STATE_OUTPUT_INTERFACE_AUDIT_V01.md`
- fixtures:
  `eval/answer_loop/info_state_output_interface_v01.json`
- runner:
  `scripts/run_info_state_output_interface_audit_v01.py`
- audit protocol anchor:
  `a1775b5ee6002165776b544aa65ae0fee4a0c9f3`

Fixture design:
- 16 total;
- 8 complete HCL answer-loop cases;
- 8 checker-triggered forced-revision cases;
- binary yes/no and A/B interfaces;
- independent domains unrelated to FANToM/SOTOPIA.

Frozen HCL under audit:
- HCL v0.3 state semantics unchanged;
- answer loop unchanged;
- provider/model/seed unchanged.

Raw audit reports separately:
- semantic accuracy;
- parser-valid rate;
- exact-format rate;
- forced-revision checker hit rate;
- final-check PASS rate.

A CI SUCCESS means the audit executed and evidence was captured. It does not
mean the current HCL passed the interface audit.

**Current gate: INFO_STATE_OUTPUT_INTERFACE_AUDIT_V01_PREDECLARED_READY**


## HCL info-state / output-interface audit v0.1 closure

Canonical audit:
- run: `35613640456`
- result: **SUCCESS as evidence collection**
- artifact: `10645726589`
- artifact SHA-256:
  `edb86e1cb469510c3243a5015032c8450bbcf7cd41c56e061f8441ad7c8f9bff`

Raw results:

Full-loop:
- semantic: **8/8**
- parser-valid: **8/8**
- exact-format: **8/8**
- final-check PASS: **7/8**

Forced revision:
- checker REVISE: **8/8**
- semantic after revision: **8/8**
- parser-valid after revision: **8/8**
- exact-format: **7/8**
- final-check PASS: **8/8**

Predeclared abstract-interface defect criteria:
- parser-invalid final answer: none
- semantic repair that loses parser-valid format: none
- final-check PASS accepting parser-invalid categorical output: none

Therefore:

**NO ABSTRACT PARSER/INTERFACE DEFECT ESTABLISHED**

The independent audit does not reproduce the FANToM v0.2 parser-null
answerability regression.

Secondary non-gating signals:
- one exact, semantically correct full-loop answer receives final-check REVISE;
- one forced-revision output is parser-valid/semantic-correct but not exact-only
  format.

These single synthetic observations do not authorize a behavior repair.

See:
- `reports/HCL_INFO_STATE_OUTPUT_INTERFACE_AUDIT_V01.md`
- `reports/HCL_INFO_STATE_OUTPUT_INTERFACE_AUDIT_V01_CLOSURE.md`

No HCL state/answer-loop/checker/prompt/parser/token/retry change is made.

Next methodological direction:
- test whether FANToM v0.2's small inaccessible-belief signal transfers to an
  independent higher-order ToM benchmark;
- selected candidate: Hi-ToM;
- same existing DeepSeek provider/key only;
- zero-provider inventory/predeclaration required before any paid model call.

**Current gate: INFO_STATE_AUDIT_NO_REPAIR_REQUIRES_HITOM_ZERO_PROVIDER_INVENTORY**


## Hi-ToM external validation v0.1 zero-provider inventory

Triggered after:
- FANToM v0.2 mixed closure;
- independent info-state/output-interface audit found no repeatable parser/interface defect.

Pinned external source:
- repository: `ying-hui-he/Hi-ToM_dataset`
- commit: `4279d3f783ff4f3b9fcced2a2fec9f6328683f82`
- data path: `Hi-ToM_data/Hi-ToM_data.json`
- git blob SHA: `23ab2aee6b2e80115dd645d88b91529ad2a29309`
- license: Apache-2.0.

Zero-provider design:
- use VP rows only;
- do not use dataset CoT prompts;
- fixed salt: `HCL-HITOM-V01-20260922`;
- globally story-disjoint selection;
- 2 rows per `question_order × deception × story_length` cell.

Target sample:
- order 0: 12
- order 1: 12
- order 2: 12
- order 3: 12
- order 4: 12
- total: **60 questions / 60 distinct stories**.

Primary higher-order block:
- orders 2–4, n=36.

Lower-order stability control:
- orders 0–1, n=24.

See:
- `reports/HITOM_EXTERNAL_VALIDATION_V01_PLAN.md`

No provider/model call is permitted before exact sample IDs and story hashes are
committed.

**Current gate: HITOM_EXT_V01_ZERO_PROVIDER_INVENTORY_READY**


## Hi-ToM external validation v0.1 inventory closure and paired predeclaration

Zero-provider inventory:
- first run `35674804556`: failed before selection because the official JSON root
  is `{"data":[...]}`; source pin checks passed; provider calls = 0;
- corrected run `35674853358`: **SUCCESS**;
- inventory artifact: `10672173370`;
- artifact SHA-256:
  `cf32c62c0203c4b8ff8a0d016e2d68bd10abd674b41db29393d4de2a341ab7fc`;
- provider/model calls: **0**.

Pinned source:
- `ying-hui-he/Hi-ToM_dataset`
- commit `4279d3f783ff4f3b9fcced2a2fec9f6328683f82`
- data blob `23ab2aee6b2e80115dd645d88b91529ad2a29309`
- Apache-2.0.

Frozen selection:
- `eval/hitom/selection_v01.json`
- salt `HCL-HITOM-V01-20260922`
- VP only;
- 60 questions / 60 distinct stories;
- exactly 12 rows at each order 0–4;
- within each order, 2 rows from every deception × story-length cell;
- exact sample IDs, story hashes and gold option letters frozen before provider
  calls.

Frozen protocol:
- `reports/HITOM_EXTERNAL_VALIDATION_V01_PREDECLARATION.md`
- protocol anchor:
  `02effce47e02585d88844a3555279ce80170952f`
- HCL behavior anchor:
  `ce36d7e6f911910f97437c23455dee33e0e7bc82`

Paired design:
- same `deepseek-flash`, endpoint/key, seed 42, temperature 0;
- no CoT prompt;
- shared story/question/choices + official Hi-ToM assumptions;
- exact option-letter scoring;
- control = direct DeepSeek;
- treatment = frozen HCL answer loop.

Primary:
- orders 2–4, n=36.

Lower-order stability:
- orders 0–1, n=24.

Predeclared positive:
- primary net >= +4;
- no order 2/3/4 subgroup net <= -2;
- lower-order control net >= -2.

Predeclared negative:
- primary net < 0 OR lower-order net <= -3.

Otherwise:
- MIXED / INCONCLUSIVE.

Formal paid workflow requires:
1. zero-diff HCL behavior check;
2. zero-diff Hi-ToM protocol check;
3. pinned repo commit/blob verification;
4. zero-provider tests and entrypoint smoke;
5. deterministic reconstruction of the same 60 rows;
6. then 6 shards × 10, max parallelism 2;
7. no partial-result tuning;
8. aggregate only after all 60 complete.

**Current gate: HITOM_EXT_V01_PAIRED_PREDECLARED_READY**


## Hi-ToM external validation v0.1 execution

Canonical paired workflow:
- run: `35675119858`
- launch commit: `888426d64f3d92a852a2dfc111fd1ae442e85e04`

Zero-provider preflight:
- HCL behavior freeze: PASS
- Hi-ToM protocol freeze: PASS
- pinned repository commit/blob: PASS
- zero-provider unit tests: PASS
- runner/aggregator entrypoint smoke: PASS
- deterministic 60-row reconstruction: PASS
- 60 distinct story hashes: PASS

Paid execution:
- 6 deterministic shards × 10 rows
- maximum parallelism 2
- no partial outcome inspection/tuning
- aggregate required before interpretation.

No behavior/protocol/sample change is permitted while this run is open.

**Current gate: HITOM_EXT_V01_PAIRED_RUNNING**


## Hi-ToM external validation v0.1 final closure

Canonical run:
- `35675119858`
- terminal result: **FAILURE**
- zero-provider preflight: **SUCCESS**
- 6 / 6 paired shard jobs terminal and failed
- aggregate integrity gate: **FAILURE as designed**

Execution completeness:
- requested: **60**
- completed paired rows: **36**
- failures: **24**
- persisted failure type: **RuntimeError for all 24 failures**
- shard completed/failure counts:
  - 0: 6 / 4
  - 1: 7 / 3
  - 2: 7 / 3
  - 3: 6 / 4
  - 4: 4 / 6
  - 5: 6 / 4

The frozen aggregator rejected incomplete evidence with
`Hi-ToM aggregate integrity failure`.
No aggregate summary artifact was produced.

Therefore no partial accuracy, paired gain, subgroup result, or predeclared
positive / negative / mixed efficacy interpretation is canonical.

**Hi-ToM v0.1 efficacy: INCOMPLETE / NOT EVALUABLE**

Failure provenance boundary:
- canonical shard artifacts persist only exception class, not exception text;
- all 24 failures are `RuntimeError`;
- the frozen HCL state builder has a known RuntimeError path after three
  unparseable state-JSON attempts;
- this run is consistent with that path but does not prove that every failure
  has that exact cause.

All 60 selected Hi-ToM rows are consumed because paid execution began.
Do not tune against them and do not rerun failed rows as fresh efficacy
evidence.

See:
- `reports/HITOM_EXTERNAL_VALIDATION_V01_PREDECLARATION.md`
- `reports/HITOM_EXTERNAL_VALIDATION_V01_CLOSURE.md`

Next canonical work:
1. keep HCL v0.3 state semantics frozen and HCL always-on;
2. do not modify HCL from consumed Hi-ToM content;
3. run an independent synthetic, non-Hi-ToM state-generation reliability audit;
4. use content-free diagnostics to distinguish JSON parse exhaustion from
   provider/transport/other runtime failure classes;
5. only an independently reproduced abstract defect may authorize repair;
6. validate any repair on independent synthetic regressions before consuming
   new external evidence.

**Current gate: HITOM_EXT_V01_INCOMPLETE_REQUIRES_INDEPENDENT_STATE_GENERATION_RELIABILITY_AUDIT**


## HCL state-generation reliability audit v0.1 predeclaration

Triggered by:
- Hi-ToM v0.1 terminal execution: 36/60 paired rows complete;
- 24/60 persisted `RuntimeError`;
- Hi-ToM efficacy not evaluated;
- consumed Hi-ToM content remains forbidden for tuning.

Independent audit:
- predeclaration:
  `reports/HCL_STATE_GENERATION_RELIABILITY_AUDIT_V01.md`
- synthetic recipes:
  `eval/answer_loop/state_generation_reliability_v01.json`
- runner:
  `scripts/run_state_generation_reliability_audit_v01.py`
- zero-provider tests:
  `tests/test_state_generation_reliability_audit_v01.py`
- protocol anchor:
  `822fd9a0d7cad47f50fa588803b9ca38a51ebc1c`
- frozen HCL behavior anchor:
  `ce36d7e6f911910f97437c23455dee33e0e7bc82`

Fixture design:
- 24 deterministic synthetic cases;
- 6 strata × 4 cases:
  short/simple, short/recursive, medium/simple, medium/recursive,
  long/simple, long/recursive;
- no Hi-ToM / FANToM / SOTOPIA content.

Content-free diagnostics persist only:
- fixture/stratum metadata;
- input byte count + SHA-256, never input text;
- HCL-level state attempt count;
- response byte count + SHA-256;
- empty flag;
- JSON-object parseability;
- exception class;
- predeclared failure class.

Predeclared repeatability gates:
- >=2 distinct `state_json_exhaustion` cases:
  state-generation JSON reliability defect established;
- >=2 distinct `backend_or_other_exception` cases:
  backend/transport/other reliability defect established;
- both may be established simultaneously.

No HCL behavior repair is authorized by predeclaration alone.
The audit must run frozen behavior first.

**Current gate: STATE_GENERATION_RELIABILITY_AUDIT_V01_PREDECLARED_READY**


## HCL state-generation reliability audit v0.1 execution

Canonical workflow:
- run: `35685106840`
- launch commit: `8c3141f2256ed954d523bed3a9e63364ef03fbff`

Zero-provider preflight:
- frozen HCL state-generation behavior diff: PASS
- frozen reliability-audit protocol diff: PASS
- Python compile: PASS
- zero-provider unit tests: PASS
- deterministic 24-case / 6-stratum fixture validation: PASS
- runner entrypoint smoke: PASS

Paid synthetic execution:
- 24 independent repository-owned synthetic cases
- no external benchmark content
- content-free observation only
- no HCL behavior change permitted while this run is open

**Current gate: STATE_GENERATION_RELIABILITY_AUDIT_V01_RUNNING**
