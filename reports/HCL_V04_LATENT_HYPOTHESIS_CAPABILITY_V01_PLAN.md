# HCL v0.4 Latent-Hypothesis Capability Comparison v0.1

Status: **FROZEN INTERNAL DEVELOPMENT DIAGNOSTIC**

## Objective

Test whether bounded competing human-state hypotheses improve prediction of
later observable behavior beyond strong full-history reasoning.

This is the first capability diagnostic after explicit first-order belief
tracking reached ceiling.

## Controlled hidden-state design

Each scenario declares a hidden target state for evaluation only.

The model never receives the hidden target.

Visible events are constructed to:
- support more than one interpretation early;
- add discriminating evidence over time;
- culminate in later observable behavior.

Primary outcome:
- exact-label prediction of the later observable behavior.

Secondary diagnostics:
- whether the hidden candidate becomes appropriately supported;
- whether OTHER_UNKNOWN remains available when evidence is incomplete.

This does not claim real-human mind reading.

## Candidate sets

Each scenario provides 3 named candidates plus mandatory OTHER_UNKNOWN.

All arms receive the same candidate definitions.

Candidate generation is intentionally excluded from v0.1 so the value of state
maintenance/revision can be isolated.

## Arms

### C — static hypothesis reconstruction

At each query:
- create a fresh target;
- provide all visible history up to that query in one hypothesis-update call;
- predict from the reconstructed hypothesis state.

### D — dynamic hypothesis tracking

- create one target;
- update after each event as it arrives;
- persist hypothesis versions across queries;
- predict from the current state.

### E — ordinary full-history reasoning

- no hypothesis store;
- receive the same candidate definitions and full visible event history;
- directly predict behavior.

## Prediction interface

All arms use:
- same base model;
- same exact JSON-label output;
- no answer checker;
- no Decision Policy;
- no Action Checker.

C/D prediction receives:
- target definition;
- current hypothesis state;
- raw evidence excerpts referenced by the current hypotheses.

E receives:
- target definition;
- full raw visible history.

## Frozen scenarios

Six generic controlled scenarios:
- teammate delay;
- buyer negotiation;
- client silence;
- reviewer delay;
- route choice;
- meeting reschedule.

Two prediction points per scenario.

Total:
- 12 behavior predictions.

Owner-private examples are not used.

## Metrics

Primary:
- behavior-prediction exact-label accuracy.

Secondary:
- hidden-candidate qualitative rank at each query;
- OTHER_UNKNOWN preservation;
- C/D state agreement;
- model calls;
- input/output volume;
- repair counts.

## Interpretation

- D > C/E: candidate incremental dynamic-cognition signal;
- C > E and D ~= C: structured hypotheses help, persistence not necessary;
- E ~= C/D: no incremental hypothesis utility established;
- D < E: dynamic tracker currently hurts;
- all arms at ceiling: scenarios are not discriminative enough.

No result here is external efficacy evidence.

**Gate: HCL_V04_LATENT_HYPOTHESIS_CAPABILITY_V01_FROZEN_READY**
