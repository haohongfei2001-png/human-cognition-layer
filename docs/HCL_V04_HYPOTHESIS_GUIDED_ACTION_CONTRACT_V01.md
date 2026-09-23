# HCL v0.4 Hypothesis-Guided Action Minimal Contract v0.1

Status: **FROZEN / AUTHORIZED**

Create:
- `hcl/v04/probe_policy.py`

Required types:
- `ProbeOption`
- `ActionOption`
- `ProbeDecision`
- `ActionDecision`
- `HypothesisGuidedPolicy`

Required API:

```python
choose_probe(
    target,
    hypothesis_state,
    evidence,
    probes,
    backend,
) -> ProbeDecision

choose_action(
    target,
    hypothesis_state,
    evidence,
    actions,
    backend,
) -> ActionDecision
```

Validation:
- returned probe/action ID must be one of the allowed options;
- output must be JSON;
- rationale required;
- at most one bounded format repair;
- no state mutation occurs in the policy.

Probe prompt:
- hypotheses are uncertain;
- choose evidence that separates plausible candidates;
- do not treat the leading hypothesis as fact;
- do not request inaccessible/private evidence outside allowed probes.

Action prompt:
- use the updated evidence/hypotheses;
- select one allowed action;
- do not claim uncertainty is resolved if it is not.

Tests:
- invalid ID rejected/repaired;
- exact option set enforced;
- no mutation of hypothesis state;
- rationale required.

**Gate: HCL_V04_HYPOTHESIS_GUIDED_ACTION_V01_AUTHORIZED**
