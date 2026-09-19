# HCL v0.1 — Epistemic Uncertainty Layer

## Purpose

HCL v0.1 is the first portable cognition module. It is designed from the research owner's direct audit of CogToM cases 01–02.

The module does **not** modify base-model weights. It adds an explicit intermediate representation before the final answer.

## Core hypothesis

Many human-state reasoning errors come from collapsing an underdetermined situation into one certain interpretation.

A better process is:

[
Observation
ightarrow
Epistemic access
ightarrow
Competing hypotheses
ightarrow
Evidence / Counterevidence
ightarrow
Confidence
ightarrow
Answer
]

## Non-negotiable distinctions

### 1. World truth vs agent knowledge

What the narrator says happened is not automatically known by every character.

### 2. First-order vs second-order belief

- First-order: what A believes about the world.
- Second-order: what A believes B believes.

Second-order belief requires a credible evidence path.

### 3. Observation vs hidden cause

An observed action/outcome can have multiple latent causes.

Example:
- observed: mother returns without hangers;
- possible causes: she did not find them / she changed her mind / she saw the action / another event occurred.

The module should not silently pick one hidden cause unless the text supports it.

### 4. Plausibility vs entailment

A hypothesis can be plausible without being established.

## Intermediate schema

Each reasoning pass should produce an internal structured state:

```json
{
  "explicit_facts": [],
  "agents": {
    "<agent>": {
      "observed": [],
      "knows": [],
      "believes": [],
      "beliefs_about_others": []
    }
  },
  "candidate_interpretations": [
    {
      "hypothesis": "...",
      "support": [],
      "counterevidence": [],
      "confidence": 0.0
    }
  ],
  "underdetermined": false,
  "missing_bridge": []
}
```

## Decision policy

1. Prefer interpretations directly supported by explicit observation/access.
2. Penalize hypotheses that require hidden information transfer.
3. If multiple hypotheses remain compatible, keep them alive.
4. If the benchmark forces one option, choose the best-supported option **without inventing a missing evidence bridge**.
5. The module may disagree with benchmark gold when the item itself is underdetermined; such cases must be flagged rather than used for training.

## What v0.1 is NOT

- not an empathy prompt;
- not a personality model;
- not a chain-of-thought dump;
- not a benchmark-answer memorizer;
- not a model fine-tune.

## First evaluation

Compare on a fresh unseen CogToM holdout:

- DeepSeek Flash vanilla
- DeepSeek Flash + HCL v0.1

Use the same base model, seed, benchmark revision, output format, and scoring.

Primary questions:
1. Does HCL improve genuine epistemic/ToM items?
2. Does HCL reduce option-order instability?
3. Does it hurt items where the benchmark rewards forced certainty?
4. Are any gains concentrated in second-order belief / knowledge-access tasks?

Only after this evaluation should training or SOTOPIA integration be considered.
