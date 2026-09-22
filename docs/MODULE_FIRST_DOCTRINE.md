# Module-First Doctrine

## Core thesis

The Human Cognition Layer (HCL) is the research program.

The base model is replaceable. Benchmarks are measurement instruments. A
portable cognition mechanism is the intended research asset **only if the
evidence shows that it adds value beyond strong simpler alternatives**.

Therefore:

- a frozen HCL treatment must not be silently bypassed during an evaluation just
  to improve its score;
- an early regression is evidence to investigate, not permission to rewrite the
  evaluation after seeing results;
- the research program must nevertheless allow the conclusion that a particular
  HCL mechanism is unnecessary, equivalent to a simpler method, or harmful;
- the project may improve representations, update rules, uncertainty handling
  and decision interfaces only through an independent research cycle, not by
  copying evaluation misses into production rules;
- routing/no-op behavior may exist inside a tested architecture, but whether an
  always-on external cognition layer is necessary is itself an empirical
  question.

**Protect experimental integrity, not the assumption that HCL must be correct.**

## What remains portable

The portable asset should include:

1. cognition schema;
2. state-update rules;
3. epistemic/causal reasoning protocol;
4. uncertainty representation;
5. prompts and orchestration logic;
6. training-data specification;
7. training recipe;
8. optional adapter weights.

No single base-model checkpoint defines the project.

## Benchmark policy

Benchmark score is necessary but not sufficient.

When HCL score decreases, we must distinguish:

- genuine degradation in reasoning;
- benchmark-gold ambiguity;
- overthinking / representation overload;
- output-interface failure;
- evaluator mismatch;
- correct uncertainty being punished by a forced-choice benchmark.

The response is to diagnose the failure under the frozen protocol. A new
mechanism may be proposed only through independent development evidence. If a
strong simpler alternative remains equivalent or better under adequate
evaluation, the correct research conclusion may be that the tested HCL
mechanism is not needed.

## Canonical architecture

Every input passes through:

```
Raw input
   ↓
HCL perception / epistemic parsing
   ↓
HCL state
   ├─ explicit facts
   ├─ agent-specific observations
   ├─ beliefs
   ├─ beliefs about beliefs
   ├─ competing causal explanations
   ├─ uncertainty
   └─ decision-relevant distinctions
   ↓
Base LLM
   ↓
HCL consistency / calibration check
   ↓
Final answer
```

HCL may emit:

`mode = SIMPLE`

when no complex human-state reasoning is required, but that is still an HCL decision and state.

## Research priority

Optimize, in order:

1. research-mechanism validity;
2. representation and state-update correctness;
3. uncertainty/calibration;
4. portability across base models;
5. unseen final-task performance;
6. latency/cost.

Do not optimize leaderboard performance by deleting or benchmark-fitting the
mechanism that is supposed to produce it.

## Research-object clarification

The research object is not the current v0.3 schema, mode taxonomy, prompt text,
or benchmark harness.

Those are implementations and measurement tools.

The intended research asset is a **portable complex-cognition mechanism** that
can represent, update, and use human-relevant cognitive state in ways that
produce measurable gains on unseen reasoning and interaction tasks.

HCL v0.3 is therefore a baseline prototype, not a claim that the final
representation has already been discovered.

## Tests do not create cognition

Testing and cognition development must remain conceptually separate.

Tests may establish:

- implementation conformance;
- reliability;
- regression safety;
- whether a frozen hypothesis survives independent evidence.

Tests do not, by themselves, make the cognition layer more capable.

A synthetic test suite should protect a research hypothesis after the hypothesis
exists. It must not become a loop where every observed failure directly creates
a new benchmark-shaped rule.

The prohibited pattern is:

```text
benchmark miss
→ add narrow cognition rule
→ create confirming synthetic fixture
→ rerun
→ repeat
```

That pattern can produce an internally self-consistent benchmark optimizer
without producing a general cognition module.

## Failure-to-research firewall

External failures may motivate an abstract research question.

They must not be copied directly into the runtime as a benchmark-specific rule.

A legitimate repair path is:

```text
external failure
→ abstract failure class
→ independent mechanism hypothesis
→ independent development evidence
→ freeze
→ new unseen evaluation
```

Once an evaluation slice has been observed, it is evidence, not development
material.

## Recognition and benchmark doctrine

The project explicitly aims for externally recognized research results.

A valuable leaderboard result is desirable because it can provide independent
evidence that a frozen cognition module generalizes.

The leaderboard is not the research artifact.

The desired causal story is:

```text
portable cognition mechanism
→ unseen-task improvement
→ cross-base transfer
→ recognized external result
```

not:

```text
leaderboard optimization
→ accumulated rules
→ apparent module
```

## Public / unpublished research boundary

The public repository must not disclose unpublished owner-originated conceptual
examples, private research derivations, or intentionally withheld mechanism
details without explicit owner authorization.

Public documents should describe the research program at the level necessary
for reproducibility of released work while preserving unpublished intellectual
property intended for later research output.

