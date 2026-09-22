# HCL Research Positioning v0.4

Status: **PUBLIC RESEARCH POSITIONING / DESIGN-ONLY**

This document repositions the Human Cognition Layer project after completion of
the HCL v0.3 synthetic reliability and conformance cycle.

It does not disclose unpublished conceptual examples, private research notes, or
proprietary mechanism details. Those remain outside the public repository unless
the owner explicitly authorizes publication.

## 1. Research objective

The goal of HCL is not to maximize a particular benchmark by accumulating
benchmark-specific rules.

The research objective is to build a **portable complex-cognition module** that
can sit on top of replaceable base models and improve their ability to model,
update, and use structured representations of human cognition in unseen tasks.

The intended research asset is the cognition module itself.

Benchmarks are external measurement instruments and recognition channels.

## 2. What HCL is trying to become

A successful HCL should provide a model-independent mechanism for maintaining
and using structured human-cognition state across reasoning and interaction.

The target capability class includes, at a public high level:

- structured representation of human-relevant state;
- explicit evidence/provenance boundaries;
- calibrated uncertainty and competing interpretations;
- state change as new observations arrive;
- reasoning over other agents' informational and behavioral state;
- an interface from cognition to answer and action;
- portability across base models.

This public description intentionally stays above unpublished mechanism-level
details.

## 3. What HCL is not

HCL is not:

- a benchmark-answer memorizer;
- a SIMPLE / EPISTEMIC / CAUSAL_AMBIGUITY classifier;
- a collection of prompt patches derived from leaderboard failures;
- a single DeepSeek-specific prompt;
- a substitute for final-task evidence;
- a claim that structured JSON by itself constitutes cognition.

The three v0.3 modes are implementation devices in a baseline prototype, not the
research contribution by themselves.

## 4. Status of HCL v0.3

HCL v0.3 is retained as a **baseline epistemic/social-cognition prototype**.

It established useful infrastructure:

- an always-on structured cognition pass;
- answer checking and bounded revision;
- a decision-policy layer for interactive agents;
- an action-specific checker;
- SOTOPIA integration;
- provider abstraction;
- a substantial evaluation and audit harness.

It also exposed important failure classes, including the difference between
correct cautious cognition and effective action.

However, passing the v0.3 synthetic suite does not establish that the project
has already discovered the final Human Cognition Layer architecture.

## 5. Research contribution standard

Future HCL work must be evaluated against a stronger standard.

**Correctness is primary; score is not the ontology.**

For directly observable or formally specified states, correctness should be
grounded in facts, event history and information-access constraints.

For latent human states that are not directly observable, correctness means the
module stays within the evidence, preserves genuine alternatives, represents
uncertainty honestly, and is validated against independent human behavior or
other construct-valid evidence where available. A benchmark gold label is not
automatically treated as unquestionable psychological truth.

A meaningful research contribution should establish that a cognition module:

1. adds a capability not reducible to benchmark-specific prompt patching;
2. operates on a coherent representation/update mechanism;
3. improves unseen downstream reasoning or interaction;
4. survives ablations that identify which module components create the gain;
5. transfers across more than one base model;
6. is evaluated with development/evaluation separation strong enough to make
   memorization and test-driven patching implausible.

Internal conformance is necessary but not sufficient.

## 6. Evaluation hierarchy

Evaluation evidence has different meanings:

### Level 0 — implementation tests

Unit tests, schema tests, parser tests, retry tests and deterministic invariants.

They answer:

> Did the implementation behave as specified?

They do not answer whether the specification is a useful cognition theory.

### Level 1 — independent synthetic capability tests

Synthetic examples created to test abstract capabilities without copying
external benchmark rows.

They answer:

> Does the module implement the intended capability class?

They must not become the primary research result.

### Level 2 — unseen external task evidence

Previously unconsumed external tasks or environments.

They answer:

> Does the frozen module generalize outside its development examples?

### Level 3 — cross-base transfer

The same frozen module is evaluated with multiple replaceable base models.

They answer:

> Is the cognition layer itself contributing, rather than one base-model/prompt
> interaction?

### Level 4 — recognized external benchmark / leaderboard result

A valuable public benchmark can provide external recognition, but it is a
measurement target, not the design source.

## 7. Development firewall

Effective immediately for v0.4 research:

- do not add cognition rules merely because a leaderboard item was missed;
- do not consume fresh evaluation rows and then tune against them;
- benchmark failures may suggest abstract research questions, but any resulting
  mechanism must be developed on independent evidence;
- once a module version is frozen for evaluation, its evaluation set is
  read-only evidence;
- raw scores and failures must remain visible;
- synthetic tests may protect a design, but cannot be cited as proof of broad
  cognitive improvement.

## 8. v0.4 research reset

Canonical Phase-0 controls:
- `docs/HCL_V04_PHASE0_RESEARCH_QUESTION_FREEZE.md`
- `docs/HCL_V04_EVALUATION_EXPOSURE_REGISTER.md`


The next phase is **design-first**, not benchmark-first.

Before new implementation, v0.4 must specify at least:

- the public research thesis and falsifiable claims;
- the module boundary;
- the representation/update contract at an appropriate public abstraction level;
- persistent-state requirements;
- the interface from cognition to reasoning/action;
- ablation plan;
- cross-base transfer plan;
- external-evaluation firewall;
- publication/IP boundary.

No new v0.4 runtime implementation is authorized merely by this positioning
document.

The research program must also remain falsifiable: a frozen HCL treatment must
not be bypassed during evaluation, but sufficiently strong evidence may conclude
that the tested HCL mechanism is unnecessary, equivalent to a simpler method, or
harmful. Experimental integrity is protected; HCL's usefulness is not assumed.

## 9. Recognition objective

The project explicitly aims for research results that can earn external
recognition.

A high-value leaderboard result is desirable when it provides an independent,
credible demonstration of the frozen module.

The intended order is:

```text
research mechanism
→ independent internal validation
→ freeze
→ unseen external evidence
→ cross-base transfer
→ recognized benchmark / leaderboard
```

not:

```text
leaderboard miss
→ patch rule
→ rerun
→ patch rule
```

## 10. Public / unpublished boundary

The public repository may document:

- high-level research goals;
- published architecture;
- frozen public contracts;
- reproducible evaluation methods;
- released experimental evidence.

It must not publish unpublished owner-originated conceptual examples, private
research reasoning, or mechanism details that have been intentionally withheld
for future research output, unless the owner explicitly authorizes release.

## 11. Immediate gate

HCL v0.3 remains frozen as the baseline.

The next canonical work is a v0.4 **research-design package only**.

No new external benchmark consumption and no new v0.4 runtime implementation
should begin until that design package is reviewed and frozen.
