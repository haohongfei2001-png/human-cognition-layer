# HCL v0.4 — Phase 0 Research Question Freeze

Status: **IN_PROGRESS / NOT FROZEN**

This document defines the public research gate for HCL v0.4.

It intentionally excludes unpublished owner-originated conceptual examples,
private derivations, and mechanism details that have not been authorized for
public release.

## 1. Purpose

HCL v0.4 is not authorized to begin by expanding the v0.3 schema or adding more
benchmark-shaped prompt rules.

Phase 0 must first establish a falsifiable research question and an evaluation
design capable of distinguishing a real cognition-mechanism contribution from:

- stronger prompting;
- more inference-time compute;
- ordinary persistent memory;
- full-history reconstruction;
- state-format effects;
- checker / planner effects;
- an already-published Theory-of-Mind method.

The project may continue only if a meaningful mechanism-level gap remains.

## 2. Falsifiability principle

HCL is a research program, not a conclusion that must be protected.

But falsifiability must not be reduced to leaderboard score.

Phase 0 separates two claims:

### 2.1 Correctness / validity claim

Is the cognition state itself faithful to the evidence, perspective boundaries,
temporal state and human construct being modeled?

A cognition mechanism is rejected or revised when it is substantively wrong
under independently grounded evidence.

Examples of relevant grounding include:

- explicit facts in the task;
- formal environment state;
- who actually had access to which information;
- time-stamped event history;
- independently collected human judgments or behavior when the claim concerns
  real people;
- construct-valid expert adjudication where no single benchmark gold can serve
  as unquestionable truth.

### 2.2 Utility / efficacy claim

If the cognition mechanism is substantively correct, does it improve downstream
reasoning, prediction or action beyond strong alternatives?

A lower benchmark score does not automatically reject the correctness claim.

A higher benchmark score does not automatically establish the correctness claim.

If HCL is correct but fails to outperform a simpler method, the appropriate
conclusion may be:

> the tested cognition mechanism is valid but has not established incremental
> utility or necessity for this task/resource regime.

If HCL scores well while making substantively wrong cognitive inferences, the
mechanism has not been validated.

During a frozen evaluation, the assigned HCL treatment must not be silently
bypassed or modified to improve its score.

**Correctness first; benchmark performance is secondary evidence about utility.**

## 3. Public research question

At a deliberately high public abstraction level, Phase 0 asks:

> Can an explicit, persistent human-state mechanism add measurable value on
> unseen reasoning or interaction tasks beyond strong equal-resource
> alternatives, and does that value transfer across replaceable base models?

This question does not yet define the unpublished internal mechanism.

The final Phase 0 thesis must be narrower and must identify a concrete,
testable mechanism difference before implementation begins.

## 4. Strong comparison design

The minimum causal comparison is:

### A — Vanilla base model

- receives the task-allowed history;
- no HCL state;
- no HCL-specific update mechanism.

Question:

> Does any external cognition treatment improve over the base system?

### B — Strong ordinary reasoning

A competitive non-HCL setup, potentially including:

- carefully designed structured prompting;
- chain-of-thought / reflection where allowed;
- self-consistency or comparable inference-time reasoning;
- an ordinary memory variant.

Question:

> Is the gain just better prompting, more thinking, or basic memory?

### C — Static reconstruction

- uses the same class of representation exposed to the downstream answer/action
  interface as the HCL treatment;
- reconstructs state from the allowed history at query time;
- does not use the candidate persistent update mechanism.

Question:

> Is the state format alone sufficient?

C must be a strong baseline. It must not be intentionally crippled by freezing a
stale one-shot state.

### D — Dynamic HCL candidate

- uses the frozen candidate mechanism;
- uses the same downstream answer/action interface as C;
- remains unchanged throughout the sealed evaluation.

Question:

> Does the candidate mechanism provide incremental value beyond state format and
> full-history reconstruction?

### E — Ordinary persistent-memory control

- receives comparable storage/retrieval/history access;
- does not use the HCL-specific mechanism.

Question:

> Is the gain just persistence or memory capacity?

### F — Nearest-neighbor research method

Where technically applicable, compare against the closest published method
rather than only against internal baselines.

Candidate families identified for Phase 0 literature review include:

- BeliefBank;
- TimeToM;
- Hypothesis-Driven / ThoughtTracing approaches;
- Hypothetical Minds;
- AutoToM;
- dynamic-ToM evaluation work such as DynToM;
- newer structured belief-dynamics / human-agent reasoning work as relevant.

This list is a review target, not a claim that the novelty gap is already known.

## 5. Required causal questions

A v0.4 experiment must be able to separate at least these explanations:

1. better semantic parsing;
2. more tokens / more model calls;
3. memory capacity;
4. representation format;
5. persistent update mechanism;
6. checker / revision effects;
7. planner / decision-policy effects.

If these are changed together, a downstream score gain cannot be attributed to
the cognition mechanism.

## 6. Failure criteria

Failure must be classified by claim type.

### 6.1 Correctness failure

The cognition mechanism is substantively wrong when, under independently
grounded evidence, it systematically:

- attributes information to an agent who did not have access to it;
- confuses later system knowledge with an agent's earlier belief;
- overwrites historical mental state with later correction;
- treats unsupported interpretations as established;
- violates the stated evidence/provenance/update semantics;
- produces human-state predictions contradicted by sufficiently strong
  construct-valid human evidence.

These failures can reject or revise the cognition mechanism itself even if a
benchmark score happens to be high.

### 6.2 Utility / necessity failure

A substantively correct mechanism may still fail to establish practical or
scientific utility if:

- D is statistically indistinguishable from or worse than a strong C/E/F;
- the advantage disappears under comparable observable resource budgets;
- the same downstream benefit is fully explained by ordinary memory, extra
  compute, state formatting, checker or planner effects;
- the effect exists only on the development base model;
- the apparent contribution is already explained by a nearest-neighbor method.

These results weaken the **incremental utility / necessity** claim. They do not
by themselves prove that the cognition representation is false.

### 6.3 Scope failure

The claim must be narrowed if:

- the effect is equally strong on non-human generic state tracking;
- the mechanism only works with hidden/oracle information unavailable at
  deployment time;
- the measured benchmark construct does not validly represent the human-state
  phenomenon being claimed.

A failed hypothesis must not be converted into a pass by adding benchmark-shaped
rules and reusing the same observed evaluation evidence.

## 7. Evaluation firewall

Phase 0 freezes the following governance rules:

- consumed evaluation rows remain consumed;
- observing a failure does not restore freshness by merely restating it as an
  abstract rule;
- mechanisms are developed on independent evidence;
- code, semantic protocol, budgets, models, metrics, failure handling and
  statistical plan freeze before sealed evaluation;
- raw failures remain visible;
- synthetic tests are implementation/capability instruments, not proof of broad
  cognition improvement;
- cross-base transfer must not involve per-model cognition-rule rewriting.

## 8. Current v0.3 status

HCL v0.3 remains an immutable research baseline for comparison.

Its useful infrastructure is retained:

- provider abstraction;
- state / answer / action execution paths;
- logging and audit machinery;
- synthetic regression infrastructure;
- historical negative and positive evidence;
- SOTOPIA integration.

Its current schema, mode taxonomy, prompts, checker and decision policy are not
assumed to be the final HCL architecture.

In particular, passing the v0.3 synthetic suite establishes implementation
conformance and reliability, not the truth of a cognition theory.

## 9. Public / private research boundary

The public repository may contain:

- the falsifiable research question;
- comparison design;
- evaluation firewall;
- released mechanism specifications after authorization;
- reproducible experimental evidence.

The public repository must not contain, without explicit owner authorization:

- unpublished owner-originated conceptual examples;
- private conceptual derivations;
- candidate mechanism details being protected for future research output;
- private novelty notes or unpublished research strategy.

The private novelty analysis is therefore maintained outside this repository.

## 10. Phase 0 deliverables

Before Phase 0 can be marked complete, the project must have:

1. a one-page falsifiable core thesis;
2. a nearest-neighbor literature/difference matrix;
3. the strongest alternative explanation;
4. the experiment that distinguishes that alternative from the HCL candidate;
5. an A/B/C/D/E/F comparison contract;
6. explicit failure / stop criteria;
7. development-vs-evaluation exposure accounting;
8. an initial resource-budget policy;
9. a reviewed public/private IP boundary.

## 11. Phase 0 exit gate

Phase 0 **PASSES** only if all of the following are true:

- a mechanism difference remains after nearest-neighbor review;
- the proposed cognitive state/update has an independent correctness criterion,
  not just a benchmark score;
- the difference is measurable independently of prompt wording;
- at least one experiment can falsify the correctness claim;
- at least one experiment can test incremental utility beyond a strong simpler
  alternative;
- correctness and downstream utility are reported separately;
- the research design allows the conclusion that HCL is cognitively wrong,
  useful but unnecessary, correct but not incrementally useful, or both correct
  and useful;
- the owner has approved the public disclosure boundary.

Phase 0 **FAILS / STOPS** if:

- the remaining difference is only naming, schema fields, prompt wording or
  additional model calls;
- no independent measurement exists;
- the claimed mechanism cannot be separated from memory / compute / planner
  effects;
- the research program refuses to accept a negative HCL conclusion.

## 12. Current gate

No v0.4 runtime implementation and no new fresh external benchmark consumption
are authorized while this Phase 0 gate remains open.

**Gate: HCL_V04_PHASE0_RESEARCH_QUESTION_FREEZE_IN_PROGRESS**
