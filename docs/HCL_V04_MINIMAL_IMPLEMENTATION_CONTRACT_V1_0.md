# HCL v0.4 Minimal Implementation Contract v1.0

Status: **FROZEN / AUTHORIZED FOR IMPLEMENTATION**

Parent plan:
- `docs/HCL_V04_CAPABILITY_PLAN_V1_0.md`

## 1. Round objective

Implement one end-to-end v0.4 cognition slice that can:

1. append raw events/evidence;
2. represent source, time and perspective explicitly;
3. accept LLM-proposed semantic patches only after deterministic validation;
4. maintain derived first-order belief state and bounded latent hypotheses;
5. build a query-specific perspective-safe view;
6. invalidate and rebuild derived cognition from source evidence;
7. produce auditable receipts for every state-changing operation.

This round does **not** claim broad HCL efficacy.

## 2. Package boundary

Create a new package:

`hcl/v04/`

v0.3 remains frozen.

Minimum files:

- `hcl/v04/__init__.py`
- `hcl/v04/model.py`
- `hcl/v04/store.py`
- `hcl/v04/semantic.py`
- `hcl/v04/runtime.py`
- `hcl/v04/schema.py`

Names may change only if responsibilities remain equivalent.

## 3. Core data model

### EventRecord

Required:
- event_id
- valid_time
- recorded_at
- raw_text
- source_id
- actor_id optional
- observer_ids / recipient_ids
- semantic_version
- supersedes optional
- metadata

EventRecord is immutable after commit except explicit supersession metadata.

### Proposition

Required:
- proposition_id
- canonical_text
- polarity / relation metadata where available
- valid_time scope optional
- source_event_ids

### CognitiveAssertion

Required:
- assertion_id
- assertion_type enum:
  - SCENE_FACT
  - SOURCE_ASSERTION
  - INFORMATION_EXPOSURE
  - BELIEF_ESTIMATE
  - STATED_GOAL_INTENTION
  - LATENT_HYPOTHESIS
  - OTHER_UNKNOWN
- subject_agent_id optional
- proposition_id / hypothesis_text
- valid_time
- system_record_time
- evidence_event_ids
- depends_on_assertion_ids
- status enum:
  - ACTIVE
  - INVALID
  - SUPERSEDED
  - UNRESOLVED
- support_level enum optional:
  - DIRECT_SUPPORT
  - INDIRECT_SUPPORT
  - COUNTEREVIDENCE
  - INSUFFICIENT
- semantic_version

### StateSnapshot

Required:
- state_version
- through_event_id / event_index
- created_at
- semantic_version
- active_assertion_ids
- checksum

### Receipts

Required typed receipts:
- EventReceipt
- StateReceipt
- InvalidationReceipt
- RebuildReceipt

Every mutation returns a receipt.

## 4. Public API

Minimum API:

```python
append_event(event) -> EventReceipt

propose_patch(event_id, backend) -> SemanticPatch

apply_patch(expected_version, patch) -> StateReceipt

build_view(
    viewer,
    event_time,
    knowledge_cutoff,
    query,
) -> QueryContext

invalidate(affected_records, reason) -> InvalidationReceipt

rebuild(scope, checkpoint=None, backend=None) -> RebuildReceipt
```

The exact Python types may differ but the observable semantics may not.

## 5. SemanticPatch rules

SemanticPatch is untrusted until validation.

It may propose:

- propositions;
- scene facts only when the input contract marks them as facts;
- source assertions;
- information exposure;
- belief estimates;
- stated goals/intentions;
- latent hypotheses;
- dependencies.

Validation must reject:

- missing referenced events/assertions;
- invalid enum values;
- impossible time ordering under declared constraints;
- cross-agent information exposure with no evidence path;
- duplicate mutation IDs;
- schema-invalid records.

A proposal failure must not mutate committed state.

## 6. Source authority

Priority:

1. raw event/evidence and explicitly declared environment fact;
2. validated structural metadata;
3. derived cognition.

Derived cognition may be invalidated by source evidence.

A downstream checker must be allowed to challenge a derived state record by
tracing its evidence.

No prompt may declare the whole derived state unconditionally authoritative.

## 7. Time semantics

All stored derived assertions carry:

- valid/event time;
- system record time.

Information exposure additionally preserves agent exposure time when available.

Historical query behavior must distinguish:

- current reconstruction of a past mental state;
- historical HCL knowledge as-of a previous system cutoff.

## 8. Perspective isolation

`build_view(viewer=...)` must exclude inaccessible private content before the
LLM sees the context.

Tests must include paired worlds where hidden background changes but the
viewer's accessible information is identical; the resulting QueryContext must
remain identical for accessibility-restricted fields.

## 9. Latent hypotheses

First slice:

- maximum 3 active named hypotheses per latent target;
- `OTHER_UNKNOWN` always available;
- no default numeric probabilities;
- each hypothesis must cite evidence or be marked insufficient;
- HCL-generated predictions cannot become external evidence unless a later real
  event independently confirms them.

## 10. Recovery

### Local invalidation

Given a source/assertion defect:

- mark affected derived assertions INVALID;
- traverse declared dependencies;
- preserve unrelated active assertions;
- rebuild only affected scope when dependency boundary is trustworthy.

### Full rebuild

Required for:
- identity merge/split defect;
- timeline defect;
- corrupted dependency index;
- semantic-version incompatibility;
- local boundary uncertainty.

Rebuild must start from raw source evidence, not from old derived text.

## 11. Checkpoints and replay

Checkpoint at configurable event intervals.

A deterministic replay of accepted patches must reproduce the same state
checksum.

An LLM semantic reparse is not deterministic replay; store it as a new semantic
version.

## 12. QueryContext

Minimum fields:

- viewer
- event_time
- knowledge_cutoff
- relevant assertions
- evidence references
- unresolved conflicts
- latent hypotheses
- unsupported / non-entailed conclusions
- state_version
- semantic_version

It must be serializable.

## 13. Downstream answer/prediction path

First implementation may reuse the v0.3 backend and answer/check orchestration,
but:

- do not mark derived state as unconditionally authoritative;
- full schema validation is required;
- `PASS` cannot coexist with substantive violations;
- the check recorded as final must correspond to the exact final returned
  answer;
- provider-specific structured-output/thinking options must be capability-aware.

Decision Policy and Action Checker remain fixed during the first cognition
comparison.

## 14. First test suite

Add:

- `tests/test_v04_store.py`
- `tests/test_v04_perspective.py`
- `tests/test_v04_recovery.py`
- `tests/test_v04_runtime.py`

Minimum cases:

1. source assertion != scene fact;
2. received != believed;
3. correction not received by A does not alter A state;
4. correction received but explicitly rejected preserves old belief estimate;
5. later system discovery does not rewrite past agent state;
6. conflicting sources remain unresolved when evidence does not decide;
7. duplicate retelling of one source is not independent evidence;
8. invalid patch is atomic/no mutation;
9. dependency invalidation preserves unrelated state;
10. full rebuild after identity/timeline defect;
11. perspective-safe paired-world view;
12. final answer check binds exact returned answer version.

These are engineering/correctness tests, not external efficacy evidence.

## 15. First comparison harness

Implement local comparison support for:

- C: full-history reconstruction;
- D: dynamic persistent v0.4;
- E: ordinary persistent memory.

B may be added as a prompt baseline using the same backend.

Do not consume new external benchmark rows in this round.

## 16. Instrumentation

Record:

- model/provider identity;
- semantic version;
- state version;
- calls;
- retries;
- finish reasons;
- token usage when available;
- latency;
- rebuild counts;
- invalidation counts;
- parse/schema failures;
- cognition validation failures.

Never persist secrets.

## 17. Completion gate

This implementation round passes only if:

- all minimum APIs exist;
- invalid proposals cannot mutate state;
- perspective isolation tests pass;
- historical state survives later corrections correctly;
- local invalidation and full rebuild both work;
- deterministic replay checksum is stable;
- query contexts remain evidence-traceable;
- returned answer is checked at its actual final version;
- all new tests pass;
- existing v0.3 tests required by the touched interfaces remain green.

No external efficacy claim is made by passing this gate.

**Gate: HCL_V04_MINIMAL_SLICE_IMPLEMENTATION_AUTHORIZED**
