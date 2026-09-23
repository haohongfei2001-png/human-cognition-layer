# HCL v0.4 Hypothesis-Guided Information Acquisition and Action v0.1

Status: **FROZEN FOR MINIMAL IMPLEMENTATION**

## Objective

Test whether an explicit competing-hypothesis state improves active social
inference:

1. choose a discriminating question/probe;
2. observe the response;
3. update hypotheses;
4. choose a task-relevant action.

The target is not passive hidden-state classification.

## Inputs

Each controlled scenario defines:
- one target agent;
- three named latent hypotheses + OTHER_UNKNOWN;
- visible initial events;
- three allowed probes;
- hidden-state-specific probe responses;
- three allowed final actions;
- one correct final action for each hidden state.

The hidden state and response table are evaluator-only.

## Arms

### C — static hypotheses

- reconstruct hypotheses from full visible history before choosing a probe;
- after the probe response, reconstruct again from full history;
- choose final action from the reconstructed state.

### D — persistent hypotheses

- maintain the hypothesis state;
- choose a probe;
- append the response;
- update only from new evidence;
- choose final action.

### E — ordinary reasoning

- no explicit hypothesis store;
- choose probe from full raw history + candidate definitions;
- append response;
- choose final action from full history.

## Probe objective

Prefer a probe that:
- distinguishes currently plausible hypotheses;
- avoids redundant questions;
- advances the task;
- is reversible / low-cost when possible.

The harness records:
- exact probe selection;
- whether the selected probe is in the scenario's predeclared
  high-information probe set.

## Action objective

Choose the final action most appropriate to the evidence after the response.

Primary metric:
- final-action exact accuracy.

Secondary:
- high-information probe rate;
- calls / input / output volume;
- C/D hypothesis-state agreement;
- semantic repair count.

## Claim boundary

This is a controlled simulator diagnostic.

It does not prove real-human psychological validity.

If E matches C/D at much lower cost, no incremental HCL utility is established.

## Gate

**Gate: HCL_V04_HYPOTHESIS_GUIDED_ACTION_V01_IMPLEMENTATION_READY**
