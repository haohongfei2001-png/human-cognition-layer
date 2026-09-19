# HCL v0.3 — Always-On Cognition Layer

## Motivation

v0.1 applied a heavy epistemic analysis universally and regressed on a high-ceiling CogToM holdout.

v0.2 avoided the regression by selectively bypassing the HCL. That is useful diagnostically, but it shifts the project away from its actual thesis.

v0.3 restores the module as the central architecture.

## Principle

**HCL always participates.**

The module does not need to perform maximal reasoning on every item. Instead, it should adapt its internal depth.

The key distinction is:

- **adaptive depth**: allowed;
- **bypassing the cognition layer**: not the canonical design.

## Three internal modes

### SIMPLE

For direct, low-ambiguity tasks.

Output only:
- explicit facts;
- relevant agent;
- confidence that no hidden epistemic inference is needed.

### EPISTEMIC

For knowledge-access / nested-belief tasks.

Output:
- who observed what;
- who knows what;
- what each agent believes;
- beliefs about others' beliefs;
- missing information-transfer bridges.

### CAUSAL-AMBIGUITY

For human-behavior interpretation with multiple latent causes.

Output:
- observed behavior;
- plausible hidden causes;
- support/counterevidence;
- uncertainty;
- which additional evidence would discriminate among causes.

## Canonical state

```json
{
  "mode": "SIMPLE|EPISTEMIC|CAUSAL_AMBIGUITY",
  "explicit_facts": [],
  "agents": {},
  "hypotheses": [],
  "missing_bridges": [],
  "uncertainty": {
    "level": "low|medium|high",
    "reason": "..."
  },
  "decision_relevant_summary": "..."
}
```

## Design constraints

1. Never import narrator knowledge into a character without an evidence path.
2. Never collapse multiple compatible hidden causes unless the text discriminates among them.
3. Avoid unnecessary interpretive branches in SIMPLE mode.
4. Preserve ambiguity when ambiguity is real.
5. Keep the state compact enough that the base model is not distracted by the representation.
6. HCL output should be model-agnostic and serializable.
7. The same HCL state should be usable by GPT, Claude, DeepSeek, Qwen, or future models.

## Evaluation strategy

Do not judge HCL solely by CogToM accuracy.

Use four classes of evidence:

### A. State fidelity
Is HCL's representation faithful to the text?

### B. Calibration
Does HCL distinguish known / plausible / unknown?

### C. Transfer
Does the same module help more than one base model / benchmark?

### D. Task performance
Does final benchmark/social-interaction performance improve?

## Immediate next work

1. implement the v0.3 state builder;
2. test state fidelity on a small mixed suite, including:
   - direct cases;
   - second-order belief;
   - hidden-cause ambiguity;
   - humor/non-epistemic cases;
3. only after state fidelity is acceptable, run larger CogToM/SOTOPIA tests.

No model training yet.
