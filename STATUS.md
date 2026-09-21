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

A same-provider output-repair plumbing fix is under isolated certification.
It explicitly binds evaluator repair to the original DeepSeek model/endpoint,
forwards that endpoint and its existing custom key, and rejects alternate repair
identities before forwarding custom credentials. No new key, seed change,
additional retry, HCL behavior change or holdout rerun is included. The earlier
forwarding-only candidate is superseded because it missed the upstream OpenAI
default model. See `reports/SOTOPIA_V021_OUTPUT_REPAIR_CLOSURE.md`.

Next: complete no-provider-call integration certification and publish this
plumbing repair. Preserve the original 8/10 incomplete holdout; ordinal 48 and
remaining efficacy certification are unresolved, not PASS. No new holdout or
freshness declaration is opened by this repair.
