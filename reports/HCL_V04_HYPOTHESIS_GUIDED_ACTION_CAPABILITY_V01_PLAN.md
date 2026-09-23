# HCL v0.4 Hypothesis-Guided Action Capability v0.1 — Predeclaration

Status: **FROZEN INTERNAL INTERACTIVE DIAGNOSTIC**

## Conditions

C:
- one-shot hypothesis reconstruction before probe;
- after response, one-shot reconstruction from full history;
- hypothesis-guided probe and action.

D:
- one-shot initial hypothesis state;
- persistent state across probe;
- one incremental response update;
- hypothesis-guided probe and action.

E:
- no hypothesis state;
- direct probe selection from full history + candidate definitions;
- direct action selection after response.

All arms:
- same base model;
- exact JSON option IDs;
- one probe only;
- same allowed probes/actions.

## Primary metrics

1. final-action exact accuracy;
2. high-information probe rate.

Secondary:
- hidden candidate top-or-tied in C/D;
- calls / input / output;
- C/D state agreement after response.

## Claim boundary

Internal controlled simulator only.

No external benchmark evidence.

**Gate: HCL_V04_HYPOTHESIS_GUIDED_ACTION_CAPABILITY_V01_FROZEN**
