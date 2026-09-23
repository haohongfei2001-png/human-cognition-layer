# HCL v0.4 Capability Development Plan v1.0

Status: **FROZEN FOR MINIMAL IMPLEMENTATION**

This plan supersedes v0.1 as the canonical v0.4 capability plan.

It incorporates the completed GPT-5.6 Pro capability-architecture review while
preserving the capability-first objective:

> build an HCL that is substantively more correct and more useful at complex
> human cognition, then use valuable external evaluation / leaderboard results
> as proof and recognition.

Publication novelty is not an implementation gate.

## 1. First capability slice

The first v0.4 slice is deliberately narrow:

> **belief tracking and revision under multi-party information asymmetry**

The system must track:

- what happened;
- who was exposed to which information;
- what information remains available to each relevant agent;
- first-order belief estimates;
- explicit goals / intentions when directly stated;
- limited alternative latent interpretations;
- changes caused by later evidence, correction, contradiction or rejection.

The first slice must support:

- current-state queries;
- historical-state queries;
- simple behavior prediction / communication decisions;
- explicit uncertainty when evidence is insufficient.

Deferred:

- general personality modeling;
- large emotion ontologies;
- full relationship dynamics;
- arbitrary recursive higher-order beliefs;
- broad hidden-goal inference;
- long-term identity modeling;
- model training / adapters.

## 2. Correctness before score

HCL correctness and downstream utility are independent axes.

### 2.1 Correctness

A state is substantively correct when it respects:

- scene/world facts that are actually established;
- source assertions as assertions, not automatically truth;
- agent-specific information access;
- temporal ordering;
- historical state;
- evidence/inference boundaries;
- genuine uncertainty and underdetermination.

For latent human state, correctness means bounded, evidence-grounded inference,
not claiming unique hidden truth when the evidence does not identify one.

### 2.2 Utility

A correct state is useful only if it improves downstream:

- answering;
- prediction;
- communication choice;
- information acquisition;
- action.

A higher score cannot validate substantively wrong cognition.

A lower score cannot by itself invalidate substantively correct cognition.

## 3. Canonical semantic types

v0.4 must not use one undifferentiated string bucket for all cognitive content.

The minimal semantic record types are:

### 3.1 SCENE_FACT

A fact explicitly established by the controlled task/environment or another
declared fact source.

Does **not** imply that every agent knows it.

### 3.2 SOURCE_ASSERTION

Source S asserted proposition P at time t.

Does **not** imply that P is true.

### 3.3 INFORMATION_EXPOSURE

Agent A observed / received / was explicitly told content at time t.

Does **not** imply:

- successful comprehension;
- acceptance;
- long-term memory;
- belief;
- truth.

### 3.4 BELIEF_ESTIMATE

Evidence supports the estimate that agent A believes proposition P at a
particular time/version.

Does **not** imply that P is true or that A will act consistently with it.

### 3.5 STATED_GOAL_INTENTION

Agent A explicitly stated a goal, plan or intention.

Does **not** imply that it is the only true motive or that the plan was executed.

### 3.6 LATENT_HYPOTHESIS

A candidate interpretation of an unobserved belief / intention / motive needed
for the current capability slice.

It must remain explicitly inferential and revisable.

### 3.7 OTHER_UNKNOWN

The maintained candidate set may be incomplete.

The system must preserve the possibility that no current latent hypothesis is
adequate.

## 4. Time model

v0.4 uses at least two explicit clocks.

### 4.1 Valid / event time

When the event occurred or the represented state applied.

### 4.2 System record time

When HCL received, parsed, corrected or revised the record.

Where relevant, information exposure also records the modeled agent's receipt /
observation time.

This supports two distinct historical questions:

- what we now estimate agent A believed at past time t;
- what HCL itself believed / had evidence for as of past system time t.

A later parser correction must not fabricate a new event in the modeled
person's timeline.

## 5. Evidence-first architecture

Canonical v0.4 flow:

```text
raw event / source evidence
→ semantic candidate extraction
→ deterministic structure / source / time / access validation
→ versioned perspective state + bounded latent hypotheses
→ query-specific evidence projection
→ answer / prediction / action
→ source-grounded validation and repair when needed
```

The raw evidence layer is persistent.

Derived cognition is revisable.

No derived cognition record is authoritative merely because HCL generated it.

## 6. Persistent state semantics

Persistent state is a derived cache / model over immutable evidence, not a new
source of truth.

The implementation must support:

- append-only raw event/evidence storage;
- versioned semantic interpretation;
- explicit dependencies from derived cognition to source evidence;
- local invalidation;
- selective recomputation;
- checkpointed rebuild;
- full-history rebuild fallback.

Persistent state must not overwrite history to make later cognition look
consistent.

## 7. Candidate hypothesis semantics

For latent beliefs / goals / intentions needed by the first slice:

- keep at most three main materially distinct hypotheses per target query or
  modeled latent question;
- always retain `OTHER_UNKNOWN`;
- record support;
- record counterevidence;
- record unresolved evidence;
- record dependencies;
- do not treat repeated retellings of one source as independent evidence;
- do not recycle HCL's own previous prediction as external evidence.

Scores may be qualitative initially:

- DIRECT_SUPPORT
- INDIRECT_SUPPORT
- COUNTEREVIDENCE
- INSUFFICIENT

Do not emit pseudo-precise probabilities until their interpretation and
calibration are justified.

## 8. LLM vs deterministic responsibilities

### 8.1 LLM

LLM may propose:

- semantic event parses;
- reference resolution;
- proposition candidates;
- candidate belief / goal / intention interpretations;
- whether new evidence strengthens / weakens a latent hypothesis;
- query-relevant explanations.

Every LLM proposal is a candidate update, not committed state.

### 8.2 Deterministic code

Deterministic mechanisms own:

- IDs;
- chronology;
- provenance;
- versioning;
- idempotency;
- perspective-access boundaries;
- reference existence;
- dependency indexing;
- atomic commit;
- invalidation;
- checkpoints;
- rebuild boundaries;
- budgets;
- audit logs;
- schema validation.

Hard access / provenance violations are rejected before state commit.

## 9. Recovery protocol

Recovery is part of HCL capability, not an exceptional afterthought.

Canonical repair sequence:

```text
locate source record or semantic-version defect
→ mark affected derived records invalid
→ traverse dependent records
→ preserve unaffected historical state
→ reparse affected raw evidence when required
→ recompute affected cognition
→ validate rebuilt state
```

Full rebuild is required when:

- agent identity merge/split is wrong;
- event timeline is wrong;
- dependency scope is unreliable;
- a semantic parser/prompt version change invalidates too much cached state;
- local repair cannot establish a trustworthy boundary.

A deterministic replay of already accepted patches must be reproducible.

A semantic reparse that calls an LLM is explicitly a new interpretation and may
produce a different result.

## 10. Query / action projection

Downstream components receive a `QueryContext`, not the unrestricted whole
state.

It must contain:

- relevant assertions;
- source evidence references;
- relevant perspective state;
- unresolved conflicts;
- bounded hypotheses;
- explicit non-entailments / unsupported conclusions when relevant.

For acting-agent use, inaccessible private information must be filtered before
the downstream model receives the view. Do not rely on a prompt saying
"ignore private information" after exposing it.

## 11. v0.3 reuse and v0.4 fixes

Reuse:

- backend abstraction;
- execution logging;
- answer/check/revision orchestration pattern;
- separate answer checker vs action checker concept;
- Decision Policy as a fixed downstream consumer during the first cognition
  experiment;
- SOTOPIA adapter infrastructure;
- historical regression assets.

Do not mutate v0.3 into v0.4. Keep v0.3 as frozen baseline.

v0.4 must correct these interface defects:

1. parsed JSON must also pass full schema validation before commit;
2. checker `PASS` must correspond to no substantive violation;
3. the actual returned final answer must have a check bound to that exact
   answer version;
4. provider-specific JSON/thinking options must be capability-negotiated rather
   than treated as universal transport behavior.

## 12. First implementation boundary

The first implementation is one vertical slice:

```text
append event
→ propose semantic patch
→ validate + atomically commit
→ update persistent perspective state
→ build query view
→ produce answer/prediction
→ inject / detect state defect
→ invalidate / rebuild
→ produce corrected view
```

No external leaderboard execution is part of this implementation round.

## 13. Capability comparisons

Keep these comparisons available:

- A: vanilla base model;
- B: strong ordinary reasoning;
- C: full-history reconstruction using the same state semantics;
- D: dynamic v0.4 persistent HCL;
- E: ordinary persistent memory;
- F: useful published method when practical.

First comparison order:

1. B / C / D / E on a small complete correctness-and-capability set;
2. A as a low-cost reference;
3. add the most relevant F only after the dominant source of gain/loss is clear.

C, D and E must share the same downstream answer/prediction interface.

Do not simultaneously change cognition, planner and checker.

## 14. Correctness validation

### 14.1 Hard invariants

Must detect or prevent:

- nonexistent evidence references;
- cross-agent private-information leakage;
- use of future information;
- source assertion promoted to fact without evidence;
- unexecuted plan promoted to action;
- historical state overwritten by later correction;
- duplicate application of retry/update;
- stale derived state surviving invalidation.

### 14.2 Semantic cases

Small human-auditable scenarios must include:

- explicit receipt;
- explicit non-receipt;
- receipt but explicit rejection;
- conflicting sources;
- correction visible to one agent but not another;
- later system discovery without agent exposure;
- repeated retelling from one underlying source;
- ambiguous reference;
- parse error followed by recovery.

Evaluation must compare propositions, agents, times and evidence relations, not
string membership heuristics.

### 14.3 Latent-state validation

Measure:

- supported-answer coverage;
- unsupported certainty;
- unnecessary abstention;
- alternative-hypothesis preservation;
- behavior-prediction quality when observable outcomes exist.

"Always unknown" is not a passing strategy.

## 15. Leaderboard route

Do not make one benchmark prove correctness, utility and recognition
simultaneously.

Current route:

- dynamic-ToM style tasks: mechanism / state-tracking validation;
- Sotopia-ToM-like interactive tasks: practical information-management /
  interaction validation if freshness and submission compatibility are
  confirmed;
- EQ-Bench 4: conditional later public leaderboard target for interactive social
  understanding / repair, subject to current rule verification.

Before committing to any leaderboard, re-verify:

- current headroom;
- submission eligibility for an HCL composite system;
- call/budget constraints;
- state reset rules;
- judge stability;
- data overlap / exposure;
- official acceptance path.

## 16. Capability-first development loop

```text
general capability hypothesis
→ minimal implementation
→ correctness diagnosis
→ capability diagnosis
→ smallest mechanism-level repair
→ independent revalidation
→ broader transfer
→ frozen external evaluation
```

Observed benchmark rows remain consumed after use.

No answer-shaped rule patches.

## 17. Freeze decision

This v1.0 plan is frozen for the first minimal implementation.

Changes to the capability objective, semantic type system, time model, evidence
authority model or recovery contract require an explicit plan amendment.

Implementation details inside the frozen boundary may evolve normally.

**Gate: HCL_V04_CAPABILITY_PLAN_V1_FROZEN_MINIMAL_IMPLEMENTATION_READY**
