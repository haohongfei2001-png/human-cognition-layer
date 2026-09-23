# HCL v0.4 C/D/E Capability Comparison v0.2 — Closure

Status: **COMPLETE / FIRST-ORDER EXPLICIT-BELIEF SLICE AT CEILING**

This is an internal development result, not external benchmark evidence.

## Frozen protocol

- plan: `reports/HCL_V04_CDE_CAPABILITY_COMPARISON_V02_PLAN.md`
- fixtures: `eval/v04/cde_capability_v02.json`
- six new scenarios;
- eight events per scenario;
- three queries per scenario;
- 48 total events;
- 18 exact-label queries;
- model: `deepseek-flash`;
- seed: 42.

v0.1 fixtures were not reused.

## Canonical run

- workflow: `HCL v0.4 CDE Capability Comparison v0.2`
- run: **35848146884**
- head: `7fbbd876d663200bf646142fcda4bfc72d981e39`
- result: **SUCCESS**
- artifact: **10743883875**
- artifact digest:
  `sha256:978ae6511529f90d1aa6e750394f6747b05f6071ac3e86feb2f0f99a03f52020`

## Accuracy

- C — full-history cognition reconstruction: **18/18 = 100%**
- D — dynamic persistent v0.4 HCL: **18/18 = 100%**
- E — ordinary full-history memory: **18/18 = 100%**

No arm produced an answer error.

Therefore this independent internal set provides:

> **no incremental accuracy signal for structured or persistent HCL on explicit
> first-order belief tracking.**

The task slice is at ceiling for the tested base model.

## Cost

### C

- calls: 103
- input characters: 340,689
- output characters: 87,483
- semantic repairs: 9

### D

- calls: 68
- input characters: 238,066
- output characters: 42,497
- semantic repairs: 3

### E

- calls: 18
- input characters: 42,656
- output characters: 313
- semantic repairs: 0

D is substantially cheaper than reconstructing structured cognition C.

However, ordinary memory E remains dramatically cheaper than either structured
arm while matching their perfect task accuracy.

## C vs D state stability

C and D normalized states were identical on:

- **8 / 18** query points.

They differed on ten query points.

Despite this semantic variation, all downstream answers matched and were
correct.

Interpretation:

- repeated semantic reconstruction is measurably less stable;
- dynamic persistence reduces repeated parsing and repairs;
- that stability/reuse benefit did not create an answer-accuracy benefit on
  this explicit first-order task slice.

## Capability decision

Do **not** keep increasing first-order belief-tracking complexity merely to find
a task where D wins.

The result supports the following design decision:

1. retain the v0.4 evidence / perspective / time / recovery substrate because it
   has correctness, audit and reuse value;
2. treat persistent structured belief state as infrastructure, not as a proven
   cognition capability advantage;
3. use the simpler ordinary-memory path where the task does not require richer
   cognition;
4. move capability development to a harder construct that is part of the
   original HCL objective:
   - bounded competing latent human-state hypotheses;
   - explicit evidence and counterevidence;
   - revision as behavior unfolds;
   - prediction / communication usefulness.

## Why this is not an HCL failure

The long-term HCL objective is not to force every input through the most complex
state representation.

A component that does not add value on a simple capability slice should not be
used merely to preserve architecture.

The v0.4 substrate remains useful for:
- provenance;
- perspective boundaries;
- temporal history;
- recovery;
- auditability.

The next question is whether those foundations enable **more complex human-state
inference** that ordinary history prompting handles less reliably.

## Next capability slice

Canonical next slice:

> **Bounded Latent-Hypothesis Tracking and Revision**

Target:
- maintain multiple plausible beliefs/goals/intentions when hidden state is not
  directly observed;
- preserve support, counterevidence and unknown alternatives;
- update hypotheses from later behavior without treating a hypothesis as fact;
- test whether the maintained hypotheses improve behavior prediction or
  communication decisions.

This next slice must not disclose owner-originated unpublished conceptual
examples.

No new external benchmark rows are authorized yet.

**Gate: HCL_V04_EXPLICIT_BELIEF_SLICE_COMPLETE_LATENT_HYPOTHESIS_SLICE_READY**
