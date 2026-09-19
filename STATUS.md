# Canonical Status

## Project

Human Cognition Layer (HCL)

## Current phase

**PHASE-01 — Module-first cognition architecture / state fidelity**

## Core thesis

The HCL module is the research asset.

The base model is replaceable. Benchmarks are measurement instruments.

Canonical architecture:

```text
Input
  ↓
HCL cognition state
  ↓
Base model
  ↓
HCL consistency / calibration
  ↓
Answer
```

Every input passes through HCL. HCL may use different internal depths, but canonical HCL is not bypassed merely to protect benchmark score.

See:
- `docs/MODULE_FIRST_DOCTRINE.md`
- `hcl/HCL_V0_3_SPEC.md`

## Current HCL version

**HCL v0.3 — Always-On Cognition Layer**

Internal modes:

- `SIMPLE`
- `EPISTEMIC`
- `CAUSAL_AMBIGUITY`

Portable state schema:
- `hcl/v03/state_schema.json`

State-builder protocol:
- `hcl/v03/STATE_BUILDER_PROMPT.md`

## Research-owner seed insight

The owner directly audited two CogToM failures.

The reusable principles extracted from those judgments are:

1. narrator/world truth != character knowledge;
2. second-order belief requires an evidence bridge;
3. an observed outcome does not uniquely reveal its hidden cause when multiple causes remain compatible;
4. genuine underdetermination should remain uncertain rather than being collapsed into a forced interpretation.

These owner judgments are recorded separately from AI-assisted screening:

- `reports/HUMAN_AUDIT_SEED_CASES_01_02.md`
- `reports/COGTOM_FAILURES_PROVISIONAL_SCREEN.md`

## CogToM baseline history

Pinned upstream revision:
`28c6781b6ea7d7ef7d491f61adc18f076f8b993c`

Representative 200-group DeepSeek Flash baseline:
- run: `35407860416`
- 46 / 46 CogToM subcategories covered
- mean group accuracy: **96.0%**
- strict all-5-variants-correct: **92.5%**
- semantic consistency: **93.5%**
- groups with any error: **15**

CogToM remains useful as a diagnostic/regression suite, but its gold labels are not treated as unquestionable human-state truth. Items that are underdetermined or normatively ambiguous must not become HCL training targets merely because a benchmark provides one answer.

## Historical HCL task-performance experiments

### HCL v0.1 — always-on heavy epistemic analysis

Disjoint 100-group CogToM holdout:
- vanilla DeepSeek: **98.6%**
- DeepSeek + HCL v0.1: **96.8%**
- delta: **-1.8 pp**

Diagnosis:
- module over-analysis introduced an intervention tax;
- some non-epistemic tasks were made worse;
- this is evidence to improve HCL, not evidence to remove the module.

### HCL v0.2 — selective safeguard experiment

Fresh 40-group CogToM holdout:
- vanilla: **97.0%**
- HCL v0.2: **97.0%**
- activated: **10 / 40**
- improved: **0**
- harmed: **0**

Interpretation:
- selective routing removed v0.1 regressions;
- however, bypassing HCL is not the canonical project direction;
- v0.2 is retained as historical evidence only.

## HCL v0.3 state-fidelity history

### Suite v0.1 — 12 synthetic cases, first run

Run `35413204446`

Reported:
- 8 / 12 pass
- mode accuracy: 66.7%
- uncertainty accuracy: 91.7%
- schema validity: 91.7%

Failure analysis showed:
- excessive EPISTEMIC mode selection on explicit evidence;
- over-generation of speculative alternatives in a humor case;
- one completion-budget failure.

### Suite v0.1 — second run after minimal-model correction

Run `35413506240`

Reported:
- 10 / 12 pass
- mode accuracy: **100%**
- uncertainty accuracy: **100%**
- schema validity: **100%**

The two nominal failures were evaluator false negatives:
- one state correctly expressed high uncertainty but did not use the exact phrase `信息不足`;
- one state correctly represented “other members already know” as a rejected/unsupported hypothesis, but a global forbidden-substring check treated any mention as failure.

Conclusion:
**Do not tune HCL to satisfy lexical test artifacts. Fix the evaluator.**

The evaluator has now been changed so lexical checks are advisory only. Gating uses structural semantics:
- schema validity;
- mode;
- uncertainty level;
- hypothesis-count bounds;
- missing-bridge requirements;
- optional field-scoped agent assertions.

## Current experiment

**Fresh State Fidelity Suite v0.2**

Files:
- `eval/state_fidelity/fixtures_v02_fresh.json`
- `eval/state_fidelity/SUITE_V02.md`

Composition:
- 12 SIMPLE
- 12 EPISTEMIC
- 12 CAUSAL_AMBIGUITY
- total: **36 fresh cases**

These cases were created after the first 12-case prompt iteration and therefore serve as a fresh boundary test rather than a tuning set.

Current GitHub Actions run:
`35414125494`

Status:
**IN_PROGRESS**

## Current gate

Do not train yet.

The next transition is allowed only after the fresh 36-case suite is analyzed.

Possible outcomes:

1. **High state fidelity**
   - freeze HCL v0.3 state semantics;
   - add task-answer integration;
   - run CogToM regression diagnostics;
   - begin SOTOPIA-Hard method evaluation.

2. **Systematic state failures**
   - identify the representation/update rule that failed;
   - revise HCL itself;
   - rerun on another fresh boundary set.

3. **Ambiguous cases requiring genuine human judgment**
   - stop automation at those cases;
   - ask the research owner for the minimal semantic judgment needed.

## Long-term evaluation route

```text
HCL state fidelity
    ↓
CogToM diagnostic / regression
    ↓
SOTOPIA-Hard multi-turn method validation
    ↓
cross-base-model transfer
    ↓
independent training data / adapter if justified
    ↓
EQ-Bench 4 public visibility
```

## Training policy

No benchmark test item or gold answer becomes a training example.

Permitted learning loop:

```text
evaluation failure
→ abstract failure mechanism
→ independently created new cases
→ module/data revision
→ fresh evaluation
```

Current status:
**WAITING_FOR_FRESH_STATE_FIDELITY_V02_RESULT**
