# HCL v0.4 — GPT-5.6 Pro Capability Architecture Review

## Role

You are reviewing HCL as a practical capability project.

The primary goal is **not** to optimize for a paper.

The goal is:

1. make HCL genuinely better at complex human cognition;
2. keep the cognition substantively correct;
3. build a portable module that improves multiple base models;
4. eventually demonstrate that improvement on a valuable external benchmark /
   leaderboard.

Publication may be a later by-product. Do not reject an effective mechanism
merely because it is prior art.

## Material to review

Primary:

- `docs/HCL_V04_CAPABILITY_DEVELOPMENT_PLAN_V01.md`

Also read:

- `STATUS.md`
- `README.md`
- `docs/MODULE_FIRST_DOCTRINE.md`
- `docs/HCL_V04_PHASE0_RESEARCH_QUESTION_FREEZE.md`
- `docs/HCL_V04_EVALUATION_EXPOSURE_REGISTER.md`
- relevant v0.3 runtime files as needed.

## Confidentiality

The owner has unpublished conceptual examples and private ideas that are
intentionally not in the public repo.

Do not infer, invent, expand, or recommend publishing them.

## Core principle

**Correctness first; score second.**

Evaluate separately:

### A. Cognition correctness

Does HCL represent facts, evidence, perspective, time, uncertainty and latent
human-state estimates correctly?

### B. Functional capability

Does that correct cognition improve understanding, prediction, answering or
action?

### C. External outcome

Can the frozen capability eventually produce strong results on a valuable
benchmark / leaderboard?

A lower benchmark score does not automatically mean HCL cognition is wrong.

A higher benchmark score does not automatically mean HCL cognition is correct.

## Your task

Review the v0.1 plan as a capability architect and skeptical systems designer.

### 1. Capability architecture review

Ask:

- Is the proposed first slice the right capability to build first?
- Is it too broad or too narrow?
- Which components are likely to create real capability?
- Which components are unnecessary complexity?
- Which existing research mechanisms should be directly borrowed or adapted
  rather than reinvented?
- Is there a better architecture for the same practical goal?

Do not optimize for novelty.

### 2. Correctness review

Evaluate whether the plan can actually tell when the cognition state is right.

Check:

- facts vs source claims;
- system knowledge vs agent-accessible information;
- received information vs accepted belief;
- present state vs historical state;
- evidence vs inference;
- uncertainty and underdetermination;
- latent belief / goal / intention claims.

Identify any place where the proposed architecture could become internally
consistent but factually or psychologically wrong.

Recommend the smallest corrections needed.

### 3. Persistent-state review

Determine whether persistent state is worth implementing.

Compare it practically against:

- full-history reconstruction;
- ordinary memory;
- summary memory;
- event sourcing;
- temporal knowledge graphs;
- belief-state methods already in the literature.

If a simpler known mechanism is better, recommend using it.

Do not require HCL to invent its own version.

### 4. Error-recovery review

Persistent state can accumulate mistakes.

Design the best practical recovery strategy:

- provenance;
- checkpoints;
- local invalidation;
- recomputation;
- confidence / uncertainty;
- when to rebuild from source history;
- how to prevent one bad semantic parse from poisoning later reasoning.

Prioritize robustness over architectural elegance.

### 5. LLM vs deterministic split

Review which work should be done by:

- LLM semantic inference;
- deterministic code;
- structured memory / graph;
- optional probabilistic scoring.

Avoid both extremes:

- everything is just another LLM prompt;
- hard-coded symbolic rules pretending to model psychology.

Recommend a practical split.

### 6. Minimal implementation

Propose the smallest implementation that could create a meaningful capability
gain.

It should:

- reuse the existing v0.3 infrastructure where helpful;
- avoid a giant ontology;
- avoid training unless justified;
- not expose owner-private ideas;
- be small enough to diagnose;
- be extensible later.

Specify:

- components;
- data structures;
- update flow;
- query flow;
- what **not** to implement yet.

### 7. Practical comparisons

Review A/B/C/D/E/F:

- A — vanilla base
- B — strong ordinary reasoning
- C — full-history static reconstruction
- D — dynamic HCL
- E — ordinary persistent memory
- F — useful existing published method

These are diagnostic controls, not publication gates.

Ask:

- what comparison most directly tells us whether HCL is genuinely more capable?
- what can be simplified?
- what fairness controls are actually necessary?
- what would be over-engineering?

### 8. Development loop

Design a practical iteration loop where failures improve general capability
without turning HCL into benchmark answer memorization.

Clarify:

- what kinds of benchmark failures may legitimately inspire changes;
- how to validate a general fix;
- when to abandon a mechanism;
- when to simplify;
- when external evaluation should be consumed.

### 9. Leaderboard strategy

The project explicitly wants to eventually “冲一个有价值的榜”.

Analyze what kind of benchmark / leaderboard best rewards the intended HCL
capability.

Do not assume the previously discussed benchmark is automatically the right one.

Criteria:

- measures complex human/social cognition meaningfully;
- meaningful headroom;
- external visibility / recognition;
- compatible submission rules;
- robust enough that score is not mostly style/judge noise;
- HCL architecture can realistically participate.

Give:

- candidate benchmark / leaderboard classes;
- which should be development environments;
- which should be final external targets;
- what needs current verification before commitment.

### 10. Use existing research as a mechanism library

Review relevant work such as:

- BeliefBank
- TimeToM
- ThoughtTracing / Hypothesis-Driven ToM
- Hypothetical Minds
- AutoToM
- DEL-ToM
- Belief Engine
- SAVeR
- BeliefShift
- ScioMind
- other recent work you find

For each useful mechanism, say:

- borrow;
- adapt;
- reject;
- defer.

The question is practical value, not originality.

### 11. GO / REVISE decision

Return one of:

- `PROCEED TO MINIMAL IMPLEMENTATION`
- `REVISE CAPABILITY PLAN BEFORE IMPLEMENTATION`
- `CHANGE THE FIRST CAPABILITY SLICE`
- `KEEP V0.3 AND SEARCH FOR A DIFFERENT UPGRADE`

Base the verdict on:

- expected correctness improvement;
- expected real capability value;
- implementation risk;
- recoverability;
- cost/complexity;
- eventual leaderboard potential.

## Required output

1. Executive verdict
2. Best interpretation of the actual HCL goal
3. Strongest three capability risks
4. Recommended v0.4 architecture
5. What to reuse from v0.3
6. What to borrow from existing research
7. What to delete / defer
8. Minimal Implementation Contract draft
9. Correctness validation plan
10. Practical capability comparison
11. Leaderboard strategy
12. Exact next 3 development steps
13. Final GO / REVISE decision

Be skeptical, but optimize for building the strongest, most correct HCL—not for
producing the cleanest paper.
