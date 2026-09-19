# Module-First Doctrine

## Core thesis

The Human Cognition Layer (HCL) is the research object.

The base model is replaceable. Benchmarks are measurement instruments. The HCL itself is the asset.

Therefore:

- HCL must not be discarded merely because an early version lowers benchmark score.
- A score regression is evidence about **how the module is wrong**, not a reason to avoid using the module.
- The project should improve the HCL's representations, update rules, uncertainty handling, and decision interface.
- Routing/no-op behavior may exist **inside** HCL, but HCL remains in the loop for every input.
- "Do not intervene" is an HCL output state, not bypassing HCL.

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

The response is to diagnose and improve HCL, not to minimize HCL usage.

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

1. representation correctness;
2. uncertainty/calibration;
3. portability across base models;
4. final-task performance;
5. latency/cost.

Do not optimize #4 by deleting #1–#3.
