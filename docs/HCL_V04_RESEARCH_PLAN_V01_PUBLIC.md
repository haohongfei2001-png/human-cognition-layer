# HCL v0.4 Research Plan v0.1 — Public Summary

Status: **DRAFT READY FOR ADVERSARIAL REVIEW / NOT FROZEN**

This public summary records the research program boundary without disclosing
unpublished owner-originated conceptual examples, private derivations, or
protected mechanism details.

The detailed research draft is maintained privately.

## 1. Long-term objective

HCL aims to become a portable complex-cognition module that can work with
replaceable base models and improve their ability to form, maintain, revise and
use human-relevant cognitive state across unseen reasoning and interaction
tasks.

The first v0.4 experiment is intentionally narrower than the long-term HCL
vision.

## 2. Two separate research claims

### Correctness / validity

Does the candidate cognition mechanism represent and update state in a way that
is faithful to facts, information access, perspective, time and the evidence
actually available?

For latent human states, correctness requires bounded inference, explicit
uncertainty and construct-valid external grounding where available.

### Utility / efficacy

If the cognition mechanism is substantively correct, does it improve downstream
reasoning, prediction or action beyond strong simpler alternatives?

These claims must be reported separately.

## 3. Candidate research family

The current candidate family is an **explicit persistent human-state update
mechanism**.

This description is intentionally high level.

The project does **not** claim that persistence, belief revision, temporal state,
hypothesis tracking, memory, probabilistic inference or planning are individually
novel. Recent literature already covers substantial parts of that design space.

Phase 0 must identify a narrower mechanism-level difference before any novelty
claim is made.

## 4. First causal comparison

The research plan uses a strong comparison structure:

- **A — Vanilla base model**
- **B — Strong ordinary reasoning / structured prompting**
- **C — Full-history static reconstruction**
- **D — Dynamic HCL candidate**
- **E — Ordinary persistent-memory control**
- **F — Closest feasible published method**

The critical comparison is not merely D vs A.

The candidate mechanism must justify itself against strong C/E/F alternatives.

## 5. Evaluation order

The first experiment is split into stages.

### Stage 1 — Cognition correctness

Evaluate the state/update mechanism on independently grounded evidence.

Final answer score is not the primary gate.

### Stage 2 — Causal downstream utility

Only after correctness is established, test whether use of the state improves
answers, predictions or actions.

### Stage 3 — Human validity where needed

For latent mental-state claims, use independent human behavior, judgments or
other construct-valid evidence where feasible.

### Stage 4 — Cross-base transfer

Only after the mechanism survives the earlier stages.

### Stage 5 — External recognition

A recognized benchmark or leaderboard is an external demonstration, not the
source of the cognition design.

## 6. Required explanations to rule out

A v0.4 result must distinguish the candidate mechanism from:

- better semantic parsing;
- extra model calls / tokens;
- ordinary memory;
- structured state formatting;
- checker/revision effects;
- planner/decision-policy effects;
- the nearest published method;
- generic dynamic state tracking that is not specifically human cognition.

## 7. Research-stop conditions

The claim must be rejected or narrowed if, after adequate evidence:

- the cognition mechanism itself is substantively wrong;
- no mechanism-level novelty remains after nearest-neighbor review;
- a strong static reconstruction or ordinary memory explains the result;
- the state is causally irrelevant to downstream output;
- gains disappear under fair resource comparison;
- gains exist only on the development base model;
- the effect is better described as generic state tracking;
- human-validity evidence contradicts the latent-state interpretation.

A lower benchmark score by itself is not a correctness failure.

A higher benchmark score by itself is not a correctness proof.

## 8. Development firewall

Existing consumed CogToM, SOTOPIA-Hard, FANToM and Hi-ToM evidence remains
historical/diagnostic and may not be converted into fresh v0.4 tuning data.

No new external benchmark rows are consumed while Phase 0 is open.

## 9. Immediate next step

Before implementation:

1. complete a mechanism-level nearest-neighbor literature matrix;
2. subject the v0.1 research plan to an independent adversarial review;
3. revise the plan only from research-level critique, not benchmark outcomes;
4. freeze a v1.0 research plan;
5. only then define a minimal implementation contract.

**Gate: HCL_V04_RESEARCH_PLAN_V01_READY_FOR_ADVERSARIAL_REVIEW**
