# HCL v0.3 State Fidelity Suite v0.4 — Freeze Holdout

This is a final fresh state-semantics holdout created after the paired-boundary run was observed and after the following principles were formalized:

- decision granularity;
- explicit uncertainty-level semantics;
- world-truth / agent-belief divergence as epistemic;
- minimal sufficient modeling.

The 18 cases were not used to tune HCL before their first execution.

Composition:
- 6 SIMPLE
- 6 EPISTEMIC
- 6 CAUSAL_AMBIGUITY

Freeze criterion:
- no new systematic representation failure;
- schema validity 100%;
- mode / uncertainty errors, if any, must be individually audited rather than papered over;
- ambiguous fixtures must be explicitly excluded rather than silently relabeled.

A satisfactory result allows HCL v0.3 state semantics to be frozen and the project to move from state construction to answer-loop / multi-turn evaluation.
