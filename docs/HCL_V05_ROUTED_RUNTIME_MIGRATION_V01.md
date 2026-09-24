# HCL v0.5 Routed Runtime Migration v0.1

Status: **PROVIDER-FREE MIGRATION CANDIDATE**

## Purpose

Make the canonical HCLV05Runtime use the routed semantic boundary introduced in
HCL v0.5 Routed Semantic Extraction v0.2.

The migration changes the semantic proposal interface, not the deterministic
current-stance state machine, persistence semantics, or invalidation/recovery
rules.

## Runtime semantic boundary

Canonical runtime now uses:

`extract_routed_stance_events(...)`

instead of the historical v0.1 extractor.

Consequences:

- the model cannot choose the subject of self stance; it is bound to event actor;
- the model cannot choose the subject of revision exposure;
- model revision output is only `issue/new/prior`;
- explicit event recipients/observers determine revision exposure subjects;
- persistence stores the same resulting StanceEvent records as before;
- semantic failure, reprocess, invalidation and restart behavior remain unchanged.

The historical extractor remains in the codebase only for consumed v0.1
evidence and compatibility diagnostics. It is no longer the canonical runtime
path.

## Validation boundary

Provider-free regression must demonstrate that routed runtime preserves:

- current stance transitions;
- raw-evidence-first semantics;
- duplicate/idempotent ingestion;
- semantic failure persistence and explicit reprocess;
- SQLite restart recovery;
- semantic invalidation audit/recovery;
- historical/current stance projection.

No provider call, consumed extraction rerun, long-horizon capability run,
owner-private example, training or benchmark claim is authorized by this
migration.

**Gate: HCL_V05_ROUTED_RUNTIME_MIGRATION_V01_PROVIDER_FREE**
