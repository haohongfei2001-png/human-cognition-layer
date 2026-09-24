# HCL v0.5 Persistent Stance Store v0.1

Status: **PROVIDER-FREE PERSISTENCE CANDIDATE**

## Purpose

Make the v0.5 evidence/stance architecture survive process restarts without
changing its cognition semantics.

The persistent source of truth is split into:

1. immutable raw events;
2. derived stance events;
3. semantic extraction receipts (COMMITTED / FAILED).

Current stance is always recomputed from persisted stance events by the
deterministic v0.5 projector.

## Persistence invariants

- Raw events are committed before semantic extraction.
- Reusing an event ID with different content fails closed.
- A semantic failure persists separately from the raw event.
- Failed semantics may be explicitly reprocessed after restart.
- Ordinary duplicate ingest never silently retries a failed extraction.
- A successful empty semantic extraction is still recorded as COMMITTED.
- Stance-event commit and semantic receipt are transactional.
- Duplicate stance IDs within one semantic commit fail before mutation.
- Restarting the runtime must reproduce the same current stance from the same
  persistent state.

SQLite is used only as a persistence mechanism. It does not introduce new
cognitive rules.

## Boundary

This milestone remains provider-free. It does not rerun consumed v0.2 rows,
call an external model, use owner-private examples, train a model, or make a
capability claim.

The next stage may add deterministic invalidation/rebuild/version receipts before
any new provider-backed capability experiment.

**Gate: HCL_V05_PERSISTENT_STANCE_STORE_V01_PROVIDER_FREE**
