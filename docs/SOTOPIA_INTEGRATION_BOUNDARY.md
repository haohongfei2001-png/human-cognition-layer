# SOTOPIA Integration Boundary

## Purpose

Define how the frozen HCL v0.3 cognition semantics will enter SOTOPIA without modifying SOTOPIA's benchmark evaluator or silently bypassing HCL.

## Pinned upstream

- Repository: `sotopia-lab/sotopia`
- Commit: `a0aaafb440e570e5e61b7c44a44e5e417c545383`
- Benchmark mechanism: custom agent class passed to `_benchmark_impl`

The upstream revision is pinned so HCL experiments remain reproducible if SOTOPIA later changes.

## Integration principle

HCL is implemented as a custom social agent compatible with SOTOPIA's `LLMAgent` interface.

Do not fork or modify:
- SOTOPIA environment rules;
- task definitions;
- benchmark evaluators;
- scoring dimensions;
- partner-agent behavior for an A/B comparison.

Only the tested agent changes.

## Per-turn HCL loop

Each social turn should execute:

```text
SOTOPIA Observation
+ agent profile
+ private goal
+ interaction history
        ↓
HCL multi-turn cognition state
        ↓
draft AgentAction
        ↓
HCL consistency / calibration check
        ↓
final AgentAction
        ↓
SOTOPIA environment
        ↓
new observation
        ↓
HCL state update
```

## State boundary

The existing frozen HCL v0.3 state semantics remain authoritative.

SOTOPIA adds multi-turn persistence, not new state meaning.

Future turn state should preserve:
- explicit observations;
- current beliefs;
- beliefs about the partner;
- competing hypotheses about goals/motives;
- missing evidence bridges;
- uncertainty;
- evidence that strengthened or weakened prior hypotheses.

## A/B requirement

For each evaluation slice:

### Control
Standard SOTOPIA LLMAgent with the same base model.

### Treatment
HCLSocialAgent with the same base model.

Keep fixed:
- scenario;
- agent profile;
- private goal;
- partner model;
- evaluator model;
- benchmark revision;
- episode limits;
- generation settings where SOTOPIA exposes them.

## Initial scope

Do not immediately run the full >100-episode hard benchmark.

First:
1. install pinned SOTOPIA with local storage;
2. reproduce one standard episode using the base model;
3. run the same episode with HCLSocialAgent;
4. verify action-format compatibility and episode completion;
5. run a small fixed hard subset;
6. only then expand.

## Current gate

Do not start SOTOPIA execution until the HCL answer-loop checker suite has completed and its failures, if any, have been audited.
