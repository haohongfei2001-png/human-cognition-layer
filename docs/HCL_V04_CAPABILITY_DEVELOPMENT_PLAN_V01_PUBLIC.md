# HCL v0.4 Capability Development Plan v0.1 — Public Summary

Status: **DRAFT READY FOR CAPABILITY-ARCHITECTURE REVIEW / NOT FROZEN**

This document replaces novelty-first / paper-first planning as the primary v0.4
development route.

The long-term objective is practical:

> build an HCL that is substantively more correct and more capable at complex
> human cognition, then demonstrate that capability on valuable external
> benchmarks / leaderboards.

Research rigor remains important because it prevents self-deception and
benchmark overfitting. It is a means to build a better HCL, not the end goal.

This public summary intentionally excludes unpublished owner-originated examples,
private conceptual derivations, and protected mechanism details.

## 1. Primary success objective

HCL v0.4 should improve real cognition capability, especially where an AI must
reason over people across incomplete, changing and perspective-dependent
information.

Success has three ordered requirements:

1. **cognitive correctness**
   - state and updates respect facts, evidence, perspective, time and genuine
     uncertainty;

2. **functional capability**
   - correct cognition improves downstream understanding, prediction, response
     or action;

3. **external recognition**
   - the frozen system demonstrates competitive performance on a valuable
     external benchmark / leaderboard without benchmark-specific answer
     memorization.

A leaderboard score is an important outcome and reward signal, but not the
definition of cognitive truth.

## 2. What v0.4 is allowed to use

v0.4 may freely reuse good ideas from existing research when they improve HCL.

Prior art is not a prohibition list.

Published mechanisms may be:

- adopted;
- adapted;
- combined;
- simplified;
- replaced when a better mechanism is found.

The project does not require every component to be novel before implementation.

Literature review serves three practical purposes:

1. avoid rebuilding weaker versions of known methods;
2. identify mechanisms that already work;
3. understand failure modes and strong baselines.

Novelty matters if/when a scientific publication claim is made, but it is not
the primary gate for capability development.

## 3. v0.3 baseline

HCL v0.3 remains frozen as the current engineering baseline.

Useful retained infrastructure includes:

- provider abstraction;
- structured state generation;
- answer/check/revision orchestration;
- Decision Policy;
- Action Checker;
- SOTOPIA integration;
- execution logging and regression infrastructure.

v0.3 is not assumed to be the final cognition architecture.

Known limitations include:

- the main answer path rebuilds state rather than maintaining a true persistent
  state transition;
- much of the representation is natural-language strings;
- an initially generated interpretation can become overly authoritative;
- state correctness and downstream score were not always cleanly separated;
- previous development spent too much effort on test/gate closure relative to
  capability creation.

## 4. v0.4 capability priorities

The first v0.4 development cycle should improve the smallest set of mechanisms
most likely to create real capability.

Priority 1 — evidence and perspective integrity
- preserve what happened;
- preserve who observed/received what;
- do not confuse system knowledge with another person's information state;
- do not turn a statement into world truth merely because it was communicated.

Priority 2 — temporal / persistent state
- preserve relevant state across sequential events;
- distinguish past state from later state;
- allow new evidence to revise current estimates without rewriting history.

Priority 3 — revisable latent-state hypotheses
- treat beliefs / goals / intentions that are not directly observable as
  hypotheses rather than facts;
- preserve genuine alternatives;
- support uncertainty and revision.

Priority 4 — cognition-to-action usefulness
- expose only decision-relevant cognitive state;
- test whether better state actually improves response, prediction or action;
- keep cognition effects separable from checker/planner effects.

This priority list is a development hypothesis, not a claim that these
mechanisms are novel.

## 5. Correctness before score

Correctness and task performance are separate measurements.

Directly grounded state should be checked against:

- explicit facts;
- event order;
- formal environment state where available;
- information-access paths;
- source/provenance records.

Latent human state should be checked by:

- staying within available evidence;
- not converting plausibility into certainty;
- preserving real underdetermination;
- calibration;
- independent human behavior / judgment or other construct-valid evidence where
  feasible.

A benchmark gold label is not automatically psychological truth.

## 6. Capability comparison

The minimum comparison structure remains useful because it tells us what
actually created a capability gain:

- **A — Vanilla base model**
- **B — Strong ordinary prompting/reasoning**
- **C — Full-history static reconstruction**
- **D — Dynamic HCL v0.4 candidate**
- **E — Ordinary persistent-memory control**
- **F — Useful closest published implementation when practical**

This is not a publication novelty gate.

It is a capability diagnosis tool.

If C or E performs as well as D while remaining equally correct, HCL should
adopt the simpler design unless D has another meaningful advantage such as
lower cost, better stability or better transfer.

## 7. Development loop

The canonical v0.4 loop is:

```text
capability hypothesis
→ minimal implementation
→ correctness check
→ capability comparison
→ failure diagnosis
→ mechanism-level improvement
→ independent revalidation
→ broader external evaluation
→ leaderboard attempt
```

The prohibited loop remains:

```text
see benchmark answer
→ add answer-shaped prompt rule
→ write confirming fixture
→ rerun same evidence
```

Failures may guide general capability improvements, but consumed evaluation
items do not become fresh evidence again.

## 8. Minimal first implementation target

The first implementation should be a small vertical slice, not a general
cognitive operating system.

At a public abstraction level it should support:

- sequential event ingestion;
- persistent state;
- perspective separation;
- evidence/provenance tracking;
- revisable human-state estimates;
- query-relevant state retrieval;
- auditability of why a state changed.

It should not initially attempt to model every aspect of:

- personality;
- emotion;
- values;
- morality;
- long-term identity;
- arbitrary recursive Theory of Mind.

Additional dimensions should be added only when they create demonstrated
capability value.

## 9. Evaluation order

### Gate A — state correctness

Does v0.4 maintain a more faithful cognitive state than v0.3 and strong static
alternatives?

### Gate B — downstream capability

Does the improved state actually help answer, predict or act better?

### Gate C — robustness / transfer

Does the benefit survive new task structures, longer sequences and different
base models?

### Gate D — external benchmark / leaderboard

Freeze the system, then use a valuable external benchmark as a real external
test and recognition target.

The project may iterate after a benchmark attempt, but observed benchmark rows
remain consumed evidence.

## 10. How existing research is used

Nearest work such as BeliefBank, TimeToM, ThoughtTracing, Hypothetical Minds,
AutoToM and later dynamic-belief / social-agent systems should be studied for:

- mechanisms worth adopting;
- useful representations;
- known failure modes;
- evaluation methods;
- implementation shortcuts;
- strong competing baselines.

The practical question is:

> What makes HCL more correct, more useful and more robust?

not:

> Is every component publishably novel?

## 11. Stop / revise conditions

A mechanism should be removed or redesigned when:

- it produces substantively incorrect cognition;
- it creates unjustified certainty;
- it accumulates unrecoverable state errors;
- a simpler mechanism is equally correct and equally capable;
- it improves a score only through benchmark-specific artifacts;
- it adds cost/latency without meaningful capability benefit.

The HCL program itself does not need to stop merely because one candidate
mechanism lacks publication novelty.

## 12. Leaderboard objective

The project explicitly intends to pursue a valuable external leaderboard once
the capability is mature enough.

The target leaderboard should:

- measure abilities materially related to complex human/social cognition;
- retain meaningful headroom;
- permit a submission format compatible with the eventual HCL system;
- provide credible external comparison / recognition;
- not become the source of answer-specific development rules.

The exact target leaderboard remains a separate selection decision and should
be re-verified before final commitment.

## 13. Immediate next steps

1. review this Capability Plan v0.1 for architecture quality, correctness and
   likely capability value;
2. use existing literature as a mechanism library rather than an originality
   veto;
3. freeze the first minimal capability slice;
4. write a Minimal Implementation Contract;
5. implement only that slice;
6. validate correctness before consuming new external benchmark evidence.

**Gate: HCL_V04_CAPABILITY_PLAN_V01_READY_FOR_ARCHITECTURE_REVIEW**
