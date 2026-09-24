# HCL v0.5 Routed Semantic Extraction v0.2

Status: **PROVIDER-FREE ARCHITECTURE CANDIDATE**

## Why this change exists

The consumed semantic extraction v0.1 package scored only 20/36 exact events.
Most failures came from one interface mistake: the model was asked to infer both
the revision relation and the person exposed to it.

v0.2 separates semantic relation recognition from information-flow routing.

## New model output

The model may output only:

### self_stances

```text
(issue_key, AFFIRM|DENY|UNRESOLVED, value_key)
```

No subject is supplied by the model. Deterministic code binds self stance to the
event actor.

### revision_relations

```text
(issue_key, new_value_key, prior_value_key)
```

No person/subject is supplied by the model.

## Deterministic routing

For each extracted revision relation, deterministic code creates
REVISION_EXPOSURE stance events for the explicit event recipients and observers.

The event actor is not automatically considered exposed merely because the
actor stated or relayed the revision.

Consequences:

- source -> recipient correction routes to recipient, not source;
- relay -> recipient routes to relay receiver, not relay sender;
- system/world update routes to explicit observers;
- self-report that merely references a previous correction creates no new
  exposure when it has no recipient/observer audience;
- duplicate recipient/observer identities are collapsed.

## Self-stance boundary

The model may create self stance only for an explicit actor self-report.

The prompt explicitly distinguishes:
- source assertion / announcement / information != source belief;
- third-party claim about another person's belief != self stance;
- explicit "I accept/believe" -> AFFIRM;
- explicit "I reject/deny" -> DENY;
- explicit "I have not decided" -> UNRESOLVED.

This remains a semantic-model responsibility and must be tested on fresh
provider evidence later. v0.2 does not pretend deterministic code can infer
mental-state semantics from arbitrary natural language.

## Compatibility boundary

The prior extraction function remains available for consumed v0.1 evidence and
historical regression. This package adds `extract_routed_stance_events`
without switching production HCLV05Runtime yet.

Runtime migration is a separate gated step after provider-free routed tests pass.

No provider call, v0.1 rerun, long-horizon capability run, owner-private
example, training or benchmark claim is authorized here.

**Gate: HCL_V05_ROUTED_SEMANTIC_EXTRACTION_V02_PROVIDER_FREE**
