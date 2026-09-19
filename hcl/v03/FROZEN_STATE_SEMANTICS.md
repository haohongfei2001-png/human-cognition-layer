# HCL v0.3 Frozen State Semantics

status: **FROZEN**
freeze_scope: **state semantics / schema / interpretation rules**
implementation_status: **still evolvable**
frozen_after_run: `35415237645`

## What is frozen

This freeze covers the semantic contract of the Human Cognition Layer state, not a specific model checkpoint or prompt wording.

Canonical state modes:

- `SIMPLE`
- `EPISTEMIC`
- `CAUSAL_AMBIGUITY`

Canonical uncertainty levels:

- `low`
- `medium`
- `high`

Canonical state fields:

- explicit facts;
- agent-specific observations;
- agent knowledge;
- agent beliefs;
- beliefs about other agents;
- competing hypotheses;
- missing evidence bridges;
- calibrated uncertainty;
- decision-relevant summary.

## Frozen cognition rules

1. **World truth != agent knowledge.**
2. **First-order belief != second-order belief.**
3. Information transfer requires an evidence path.
4. World-truth / agent-belief divergence is epistemic.
5. Genuine hidden-cause ambiguity must preserve competing explanations.
6. Do not manufacture exotic alternatives merely because they are logically possible.
7. Prefer the **minimal sufficient model** of the situation.
8. Uncertainty is evaluated at the **granularity of the actual question**.
9. Fine-grained unknowns must not inflate a coarser question's uncertainty.
10. SIMPLE does not mean “HCL absent”; it means the always-on cognition layer found a direct, low-ambiguity state.
11. HCL should preserve uncertainty when evidence is insufficient, but should not confuse epistemic humility with indiscriminate skepticism.
12. Protocol enum tokens remain canonical English even when explanatory strings use another language.

## Uncertainty semantics

### low

The decision-relevant proposition is:
- explicitly stated;
- directly observed;
- directly communicated without relevant conflict;
- or overwhelmingly supported at the required granularity.

### medium

One interpretation is materially better supported, but credible alternatives remain.

### high

Two or more materially different interpretations remain comparably plausible, or a critical evidence bridge is missing such that no interpretation is clearly privileged.

## Evidence supporting the freeze

### Initial 12-case suite

First run `35413204446`:
- raw 8 / 12;
- exposed over-analysis, mode over-sensitivity, and one completion-budget issue.

Second run `35413506240`:
- raw 10 / 12;
- 100% mode accuracy;
- 100% uncertainty accuracy;
- 100% schema validity;
- two nominal failures were evaluator false negatives.

### Fresh 36-case boundary suite

First independent run `35414125494`:
- raw 32 / 36;
- four failures audited individually.

Regression run `35414572919`:
- raw 35 / 36;
- 100% mode accuracy;
- 100% schema validity;
- the one remaining item was explicitly underdetermined because its false-belief premise omitted the agent's initial knowledge.

Adjudicated gate:
- **35 / 35 determinate fixtures passed**;
- one ambiguous fixture retained but excluded from the gate.

### Fresh 24-case paired-boundary suite

Run `35415058681`:
- raw 22 / 24;
- mode accuracy 95.8%;
- uncertainty accuracy 91.7%;
- schema validity 100%.

The two failures exposed:
- question-granularity calibration;
- medium-vs-high uncertainty semantics.

Those principles were formalized only after the fresh run.

### Final fresh 18-case freeze holdout

Run `35415237645`:
- raw **17 / 18**;
- mode accuracy 94.4%;
- uncertainty accuracy 94.4%;
- schema validity 100%.

The sole failed fixture asked why wet trouser legs and a dripping umbrella were wet immediately after heavy rain. HCL used SIMPLE/low and identified rainwater as overwhelmingly supported. The fixture expected causal ambiguity.

Adjudication:
- HCL followed the already-frozen-before-run minimal-sufficient-model and question-granularity principles;
- the fixture over-penalized ordinary-context inference by treating merely logical alternatives as decision-relevant ambiguity;
- this is recorded as a fixture-design error, not silently relabeled as a perfect raw score.

## What is NOT frozen

The following may still evolve:

- exact prompt wording;
- provider/API adapter;
- state compression;
- latency/cost optimization;
- model used to instantiate HCL;
- consistency-check implementation;
- multi-turn state update mechanism;
- training recipe;
- optional learned adapter.

Any future semantic change to the 12 frozen cognition rules requires a new HCL state-semantics version.

## Next phase

Build the always-on answer loop:

```text
Input
  ↓
HCL v0.3 State
  ↓
Base Model Draft Answer
  ↓
HCL Consistency / Calibration Check
  ↓
Final Answer
```

The consistency check must not bypass HCL. Its role is to detect whether the draft answer:
- contradicts explicit facts;
- imports unavailable information into an agent;
- collapses genuine ambiguity;
- becomes more uncertain than the evidence warrants;
- answers at the wrong granularity.
