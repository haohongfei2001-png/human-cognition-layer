# Module-First Doctrine

## Core thesis

The Human Cognition Layer (HCL) is the research program.

The base model is replaceable. Benchmarks are measurement instruments. The
primary research objective is to build a cognition mechanism that is
**substantively correct before it is competitively scored**.

HCL must therefore be judged on two separate axes:

1. **correctness / validity** — whether its state, perspective boundaries,
   evidence dependencies, uncertainty and updates are faithful to the available
   evidence and to the human-state construct being modeled;
2. **utility / efficacy** — whether a correct mechanism actually improves
   downstream reasoning, prediction or action under fair comparison.

These axes must not be collapsed.

Therefore:

- a lower benchmark score does **not** automatically mean that the HCL cognition
  is wrong;
- a higher benchmark score does **not** automatically validate an incorrect
  cognition mechanism;
- benchmark disagreement must be diagnosed as possible cognition error,
  construct/gold ambiguity, evaluator mismatch, output-interface failure,
  tradeoff, or genuine task-performance loss;
- a frozen HCL treatment must not be silently bypassed during evaluation just to
  improve its score;
- a cognition claim may be rejected when the mechanism is substantively wrong
  under independently grounded evidence;
- a utility/necessity claim may be rejected when a substantively correct HCL
  fails to add downstream value beyond strong alternatives;
- these are different conclusions and must be reported separately.

**Correctness first; benchmark score is evidence, not authority.**

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

Benchmark score is useful external evidence, but it is not the definition of
cognitive correctness.

When HCL score decreases, we must distinguish:

- genuine cognitive or reasoning error;
- benchmark-gold ambiguity or construct mismatch;
- overthinking / representation overload;
- output-interface failure;
- evaluator mismatch;
- a valid uncertainty representation being punished by forced-choice scoring;
- a genuinely correct cognition state that does not translate into better task
  performance.

The response is first to determine **what is actually correct**, using the
strongest available grounding: explicit task evidence, formal environment
state, information-access constraints, independently collected human behavior,
or other construct-valid evidence.

Only after correctness is assessed should benchmark performance be interpreted.

If HCL is substantively correct but does not beat a strong simpler alternative,
that weakens or falsifies the **incremental utility / necessity claim**, not the
correctness claim itself.

If HCL scores well while producing substantively wrong human-state inferences,
the score does not validate the mechanism.

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

