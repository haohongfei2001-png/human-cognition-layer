# HCL v0.4 Capability Development Plan v0.1

Status: **DRAFT FOR CAPABILITY-ARCHITECTURE REVIEW**

Public gate: `HCL_V04_CAPABILITY_PLAN_V01_READY_FOR_ARCHITECTURE_REVIEW`

## Disclosure boundary

This document is complete enough for architecture review. It does not include
owner-originated conceptual examples or other material not approved for public
release.

## 1. Actual project goal

The goal is not to optimize for a paper.

Build a Human Cognition Layer that makes replaceable base models genuinely
better at complex human cognition, especially understanding and acting around
people under incomplete, changing, perspective-dependent information.

Then use a valuable external benchmark / leaderboard as external proof,
recognition, and a concrete achievement.

Publication is optional and secondary.

## 2. What “better HCL” means

HCL should improve two things in this order.

### A. Cognition correctness

The system should more correctly represent:

- what happened;
- who observed / received what;
- what the system knows vs what a modeled person could know;
- what is evidence vs what is inference;
- what changed over time;
- what remains uncertain;
- which latent interpretations are plausible rather than established.

For latent mental states, correctness does not mean guessing a unique hidden
truth when the evidence cannot identify it.

### B. Functional capability

A more correct state should help the model:

- answer;
- predict behavior;
- understand social situations;
- decide when to ask / wait / act;
- choose better actions in interaction.

Leaderboard score belongs here as an external capability outcome, not as the
definition of correctness.

## 3. What we learned from v0.3

v0.3 should be retained as the baseline.

Useful assets:

- provider abstraction;
- structured state path;
- answer/check/revision loop;
- Decision Policy;
- Action Checker;
- SOTOPIA integration;
- logging, CI and evaluation infrastructure.

Current limitations:

- state is rebuilt rather than truly maintained across events;
- representation is largely natural-language string fields;
- generated state can become too authoritative;
- direct communication can be over-collapsed into “knowledge”;
- state correctness and final task score were not always cleanly separated;
- too much recent work optimized test/gate closure instead of creating new
  cognitive capability.

## 4. v0.4 capability hypothesis

The first v0.4 cycle should not attempt a complete model of human cognition.

It should implement the smallest capability upgrade likely to matter across many
later HCL abilities:

> A persistent, perspective-aware, evidence-grounded human-state model that can
> be revised over time without rewriting history.

This is not claimed to be novel by itself.

Existing research may already provide good components. Use them if they improve
HCL.

## 5. Minimal capability architecture

### 5.1 Event / Evidence Layer

Record:

- event identity;
- time/order;
- source/speaker/actor;
- who observed/received it when known;
- proposition references;
- raw evidence link where needed.

Key distinction:

> “X said P” must remain distinguishable from “P is true.”

### 5.2 Perspective State

For each relevant agent:

- what they observed;
- what they received;
- what information is available to them;
- unresolved contradictions;
- references to inferred latent states.

Key distinction:

> received(P) does not automatically equal believes(P).

### 5.3 Latent Human-State Hypotheses

Represent uncertain beliefs, goals, intentions, or other latent interpretations
needed by the current capability slice.

Each hypothesis should have:

- supporting evidence;
- counterevidence / missing evidence;
- status / uncertainty;
- dependencies.

Allow:

- multiple hypotheses;
- partial coexistence;
- “current hypotheses are insufficient.”

### 5.4 Temporal / Revision State

New evidence can:

- add information;
- invalidate some inferences;
- revise current estimates;
- leave historical records intact.

Important distinctions:

```text
system learns correction
≠ person A received correction
≠ person A accepted correction
≠ person A changed belief
```

### 5.5 Query / Action Interface

Expose only state relevant to the current query/action.

Do not dump the entire cognition store into the base model if it is unnecessary.

## 6. LLM and deterministic components

Use LLM for semantic work that actually requires language understanding:

- parse events;
- resolve references;
- propose propositions;
- propose plausible latent hypotheses;
- interpret behavior/context.

Use deterministic mechanisms for things that should not drift:

- stable IDs;
- chronology;
- provenance;
- perspective isolation;
- dependency links;
- state versioning;
- update application;
- invalidation boundaries;
- audit logs;
- budgets.

Deterministic bookkeeping does not make a psychological hypothesis true.

## 7. Existing research as mechanism library

Relevant research is a source of mechanisms, not a prohibition list.

For each useful work, ask:

- What mechanism works?
- Can HCL adopt it?
- What failure does it solve?
- What implementation can we avoid reinventing?
- What stronger baseline does it give us?

Known relevant families include BeliefBank, TimeToM, ThoughtTracing /
Hypothesis-Driven ToM, Hypothetical Minds, AutoToM, DEL-ToM, Belief Engine,
SAVeR, BeliefShift, ScioMind, and other dynamic belief / social-cognition work.

If an existing method is better than a proposed component, use or adapt the
stronger idea.

## 8. Minimal first implementation

Do not build the complete final HCL.

Implement one vertical slice:

```text
event stream
→ persistent state
→ perspective separation
→ evidence/provenance
→ limited revisable latent hypotheses
→ query-relevant state
→ answer/prediction interface
```

Initially exclude:

- full personality model;
- large emotion ontology;
- moral/value system;
- long-term identity model;
- unlimited recursive beliefs;
- broad relationship psychology;
- training / adapters.

Add these later only if they produce real capability value.

## 9. Correctness validation

### 9.1 Grounded invariants

Where ground truth is available:

- event history remains intact;
- information does not leak across perspectives;
- later facts do not overwrite earlier agent state;
- source assertion is not silently converted to world truth;
- revisions affect dependent state rather than unrelated state.

### 9.2 Latent-state quality

Where inner state is not directly observable:

- no unsupported certainty;
- alternatives retained when evidence underdetermines the answer;
- explicit evidence/inference distinction;
- calibrated uncertainty;
- independent human behavior/judgments where feasible.

### 9.3 Adversarial correction cases

Include situations where:

- source was wrong;
- person A did not hear the correction;
- A heard it but may not accept it;
- system later learns a fact;
- one interpretation becomes weaker while another stays viable.

## 10. Capability comparison

Use comparisons to understand what really helps:

- **A — Vanilla base**
- **B — Strong ordinary reasoning / structured prompting**
- **C — Full-history static reconstruction**
- **D — Dynamic v0.4 HCL**
- **E — Ordinary persistent memory**
- **F — A useful published method when feasible**

Critical questions:

- Is D more correct than C/E?
- Does D help downstream tasks?
- Is D worth its cost?
- Is a simpler design equally good?

If C/E is equally correct and useful, prefer the simpler design.

## 11. Development loop

```text
capability hypothesis
→ minimal implementation
→ correctness test
→ capability test
→ diagnose general failure mode
→ improve mechanism
→ independent revalidation
→ broader task/model transfer
→ external benchmark / leaderboard
```

Do not use:

```text
see benchmark answer
→ write answer-shaped rule
→ rerun same rows
→ call it progress
```

## 12. How benchmark failures may be used

A benchmark failure can reveal wrong cognition, missing capability,
output/interface problems, benchmark ambiguity, scoring mismatch, or task
tradeoffs.

Abstract lessons may guide HCL improvements, but:

- the observed row is consumed;
- it cannot become fresh evidence again;
- the new mechanism should be validated independently before another external
  attempt.

## 13. Capability roadmap

### Stage 0 — Capability architecture freeze

Current output:

- first capability slice;
- correctness contract;
- state/update boundary;
- minimal implementation contract.

### Stage 1 — Minimal implementation

Build only the vertical slice.

### Stage 2 — Correctness validation

Show that the state/update mechanism behaves more correctly than v0.3 and
strong simple alternatives on independently grounded cases.

### Stage 3 — Functional capability validation

Show that the better state improves actual answer/prediction/action capability.

### Stage 4 — Robustness / transfer

Test new structures, longer sequences, and different base models.

### Stage 5 — Valuable benchmark / leaderboard

Freeze a capable HCL and challenge it externally.

If the leaderboard reveals general weaknesses, learn from them without tuning
on consumed rows.

### Stage 6 — Broader HCL

Add richer goals / intentions / relationships / emotion / conceptual cognition
only when they provide real capability.

## 14. Leaderboard strategy

Leaderboard is a real target, not an afterthought.

Before committing to one, verify:

- it measures a capability HCL is intended to improve;
- it still has meaningful headroom;
- rules permit the eventual submission format;
- it has enough visibility / recognition to be worth optimizing for;
- scoring is not so narrow that it rewards incorrect cognition.

## 15. What counts as progress

Strong progress:

- HCL state is demonstrably more correct;
- fewer perspective / temporal / evidence errors;
- downstream decisions improve;
- improvements survive independent tasks;
- benefits transfer across models;
- cost remains acceptable;
- external leaderboard improves with frozen general mechanisms.

Weak / misleading progress:

- schema gets larger;
- more internal fixtures pass;
- prompt acquires more rules;
- benchmark score rises only on previously observed items;
- evaluator is changed until the result looks positive.

## 16. Simplification rule

If two mechanisms are equally correct and equally capable, choose the simpler,
cheaper, more portable mechanism.

Complexity itself is not cognition.

## 17. Unpublished-material boundary

Additional owner-originated ideas may later expand HCL beyond the current first
slice.

Do not infer or add material not present in the repository.

Additional material should enter the repository only by explicit owner
authorization.

## 18. Immediate next action

GPT-5.6 Pro should review this plan with a practical capability objective:

- What architecture is most likely to make HCL actually better?
- Which existing mechanisms should we borrow?
- Which parts are unnecessary?
- Is the first slice small enough?
- Is correctness testable?
- What is the shortest path to a working capability gain?
- What leaderboard class should eventually reward the intended capability?

After review:

```text
revise Capability Plan v0.1
→ freeze v1.0
→ write Minimal Implementation Contract
→ start coding
```

**Current gate: HCL_V04_CAPABILITY_PLAN_V01_READY_FOR_ARCHITECTURE_REVIEW**
