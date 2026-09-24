# HCL v0.5 Semantic Invalidation and Recovery v0.1

Status: **PROVIDER-FREE RECOVERY CANDIDATE**

## Purpose

Allow a derived semantic interpretation to be withdrawn and recomputed without
mutating or deleting the raw evidence event.

## Frozen recovery semantics

- Raw events are immutable and are never invalidated by this mechanism.
- Only events with COMMITTED stance semantics may be invalidated.
- Invalidation removes the current derived stance events from active projection.
- Before removal, the complete prior stance payloads and prior semantic receipt
  are copied into append-only invalidation history with reason and timestamp.
- The current semantic status becomes INVALIDATED.
- Reprocessing an INVALIDATED event may commit a new semantic interpretation.
- Successful reprocessing clears only the current invalidation marker; audit
  history remains.
- If reprocessing fails, current semantics become FAILED and the old stance is
  not resurrected.
- Invalidation/reprocessing survives process restart.

This milestone provides current-state recovery and durable audit evidence. It
does not yet claim a full bitemporal query API over old invalidated semantics;
the archived payloads make such reconstruction possible later without silently
rewriting history.

## Boundary

No provider-backed run, consumed v0.2 rerun, external benchmark, owner-private
example, training or capability claim is authorized here.

**Gate: HCL_V05_SEMANTIC_INVALIDATION_RECOVERY_V01_PROVIDER_FREE**
