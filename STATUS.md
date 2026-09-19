# Canonical Status

## Project

Human Cognition Layer (HCL)

## Current phase

**PHASE-02 — Always-on answer loop integration**

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

Next canonical execution:
1. small always-on CogToM regression diagnostic;
2. SOTOPIA-Hard custom-agent smoke;
3. then fixed-subset A/B if smoke succeeds.
