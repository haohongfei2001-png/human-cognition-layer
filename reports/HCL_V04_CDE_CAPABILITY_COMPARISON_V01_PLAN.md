# HCL v0.4 C/D/E Capability Comparison v0.1 — Plan

Status: **FROZEN DEVELOPMENT DIAGNOSTIC**

This is an internal capability diagnostic after the v0.4 minimal-slice
correctness closure.

It is not an external benchmark and does not establish broad HCL efficacy.

## Question

Does dynamic persistent HCL (D) provide a real downstream capability, stability
or cost advantage relative to simpler alternatives?

## Conditions

### C — full-history reconstruction

For every query point:

1. create a fresh v0.4 runtime;
2. replay the legal raw event history from the beginning;
3. rebuild cognition from raw evidence;
4. answer from the reconstructed QueryContext;
5. discard the runtime after the query.

C uses the same cognition semantics as D but receives no persisted derived state
from a previous query.

This is intentionally strong: if C matches D, persistence may be mainly a cache /
efficiency mechanism rather than a cognition capability.

### D — dynamic persistent HCL

For each scenario:

1. maintain one v0.4 runtime;
2. ingest each event once as it arrives;
3. preserve versioned state across query points;
4. answer from the current QueryContext.

### E — ordinary persistent memory

No structured cognition state.

At each query point:

1. provide the complete legal raw event history so far;
2. include source/time/recipient metadata;
3. use a strong perspective-reasoning instruction;
4. answer directly.

E tests whether ordinary memory + a strong model is already enough.

## Downstream answer isolation

C and D use the same answer prompt and the same base model.

The first comparison does not use the HCL answer checker, Decision Policy or
Action Checker. This prevents those components from being mistaken for cognition
gain.

E uses the same base model and exact-label answer format.

## Development scenarios

The frozen set contains six multi-event scenarios across unrelated domains.

Each has two query points.

The target is first-order belief / uncertainty under:

- correction not received;
- correction received and accepted;
- correction received but rejected;
- conflicting sources without acceptance;
- hidden world change not observed by the agent;
- explicit trust / rejection of later information.

Answers use exact labels so no LLM judge is required.

## Metrics

Primary diagnostic metrics:

- exact-label accuracy per arm;
- C vs D state-checksum agreement where comparable;
- model-call count;
- observable input/output character volume;
- semantic-repair count;
- failure count.

Interpretation:

- D > C/E in correctness: evidence that dynamic state may add capability;
- D = C but cheaper across repeated queries: engineering/persistence value;
- D = C and C is simpler/competitive: do not claim persistence as a cognition
  capability;
- E = C/D: ordinary memory may already be sufficient for this slice;
- any substantively wrong high-scoring arm is not treated as cognitively valid.

## Exposure

These are new repository-owned development scenarios.

They are not fresh external evidence and must never be presented as a leaderboard
result.

No CogToM, SOTOPIA, FANToM or Hi-ToM row is used.

## Gate

Run the frozen comparison once, preserve all results, then decide the next
mechanism step.

**Gate: HCL_V04_CDE_CAPABILITY_COMPARISON_V01_PREDECLARED**
