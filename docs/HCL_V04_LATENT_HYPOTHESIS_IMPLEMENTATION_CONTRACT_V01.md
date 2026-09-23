# HCL v0.4 Latent-Hypothesis Minimal Implementation Contract v0.1

Status: **FROZEN / AUTHORIZED**

Parent:
- `docs/HCL_V04_LATENT_HYPOTHESIS_SLICE_V01.md`

## Required runtime

Create:
- `hcl/v04/hypotheses.py`

Required public types:
- `HypothesisStatus`
- `HypothesisCandidate`
- `HypothesisTarget`
- `HypothesisState`
- `HypothesisUpdateReceipt`
- `HypothesisTracker`

## HypothesisTarget

Required:
- target_id
- subject_agent_id
- target_kind
- question
- candidate definitions
- mandatory OTHER_UNKNOWN

## HypothesisCandidate

Required:
- label
- description
- status
- support_event_ids
- counterevidence_event_ids
- unresolved_event_ids
- rationale

## Persistence

Use the same SQLite connection owned by `CognitionStore`.

Minimum tables:
- hypothesis_targets
- hypothesis_versions

Every update creates a new immutable version row.

## Public API

```python
tracker = HypothesisTracker(store)

tracker.create_target(target) -> HypothesisUpdateReceipt

tracker.update(
    target_id,
    new_event_ids,
    backend,
) -> HypothesisUpdateReceipt

tracker.current(target_id) -> HypothesisState

tracker.history(target_id) -> tuple[HypothesisState, ...]

tracker.rebuild(
    target_id,
    backend,
) -> HypothesisUpdateReceipt
```

## Validation

Reject updates that:
- reference unknown event IDs;
- omit a frozen candidate;
- add an unregistered candidate;
- omit OTHER_UNKNOWN;
- use invalid status;
- duplicate evidence IDs across malformed fields;
- return empty rationale for a changed candidate.

No mutation on rejection.

At most one bounded repair.

## LLM update boundary

LLM receives:
- target definition;
- current hypothesis state;
- new raw events;
- referenced prior raw evidence when needed.

It returns the complete candidate state.

The prompt must state:
- hypotheses are not facts;
- preserve alternatives;
- OTHER_UNKNOWN remains available;
- cite raw events only;
- do not use prior HCL outputs as evidence.

## First tests

Add:
- target always contains OTHER_UNKNOWN;
- invalid event reference rejected atomically;
- candidate labels cannot mutate;
- support/counterevidence preserved through update;
- previous version remains queryable;
- rebuild from raw events produces a valid state;
- rejected update does not contaminate current state.

## Completion boundary

Passing this contract means only that bounded hypothesis tracking works as an
auditable mechanism.

It does not establish predictive value.

**Gate: HCL_V04_LATENT_HYPOTHESIS_V01_IMPLEMENTATION_AUTHORIZED**
