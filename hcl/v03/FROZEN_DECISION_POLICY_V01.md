# HCL v0.3 + Decision Policy v0.1 — Repeat-Stability Freeze

## Purpose

Freeze the implementation that produced the first positive fresh SOTOPIA-Hard
holdout before any repeat-stability testing.

No HCL cognition, Decision Policy, checker, or SOTOPIA agent-policy logic may be
changed while repeat runs on Hard ordinals 10-19 are being collected.

## Frozen implementation

Evidence-producing fresh holdout:
- workflow run: `35450229188`
- SOTOPIA-Hard ordinals: `10-19`
- result: control 2.4714 vs HCL+DecisionPolicy 2.8857
- paired mean delta: `+0.4143`
- outcome counts: 7 improved / 1 tied / 2 worsened

Frozen file content SHAs:
- `hcl/v03/answer_loop.py`: `f62781da3621689dbed07e3a34dd444f7fd80d37`
- `hcl/v03/decision_policy.py`: `eb0cace3b95f38a6b595cc892a5c39d5b097b693`
- `hcl/integrations/sotopia_agent.py`: `06a252732fece67e92e11e40a0859235298f15dc`
- `hcl/v03/backends.py`: `df16a1020c4b95f84c9c6e71946ff25dc8e423af`

Frozen upstream SOTOPIA revision:
- `a0aaafb440e570e5e61b7c44a44e5e417c545383`

## Allowed changes during repeat testing

Only evaluation-harness changes are allowed, including:
- exposing a predeclared generation seed;
- sharding jobs;
- artifact naming/aggregation;
- retry/transport handling that does not change model-visible cognition or
  action-policy instructions.

The frozen HCL module itself must remain byte-for-byte unchanged.

## Repeat plan

The original fresh holdout used agent-generation seed `42`.

Two additional repeats are predefined before seeing outcomes:
- repeat A: seed `43`
- repeat B: seed `44`

Each repeat covers the same ordinals `10-19` with the same profiles, tested
roles, partner configuration, evaluator rubric, and model.

The purpose is to estimate run-to-run stability, not to tune on these settings.

## Claim boundary

The DeepSeek API / SOTOPIA environment and evaluator may contain sources of
stochasticity not fully controlled by the agent seed. Therefore the repeats
measure end-to-end run stability under predefined agent seeds rather than a
perfectly isolated random-seed experiment.
