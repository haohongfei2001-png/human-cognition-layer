# M10 retained-content governance: implementation in progress

This document describes the isolated development increment after the bounded
retrieval implementation. It is not a completed M10/T22/T24/T27/S4 acceptance
record. The approved S1–S7 goals and all research acceptance conditions remain
unchanged. The new maintenance tests operate only on disposable synthetic data.
No user database, production source, provider account or public frozen evidence
package has been erased by these tests.

## Retention identity and write ordering

Minimal final-answer dependencies are not sufficient deletion provenance. The
same authoritative SQLite store records retention provenance for every historical
source version, inference, task request, serialized call, return and execution
checkpoint, including failed/unused branches. The walk accepts typed contracts,
not source-looking dictionary keys or text similarity. Retrieval retention
includes the actual search corpus and transitive stored proof origins, even when
the nested proof's source lies outside a later query's scan scope.

Provenance belongs to each reference/owner, not globally to a CAS hash. Two
independent authorized references to identical bytes remain independent. Legacy
query rows that lack an authenticated principal get an explicit scoped
conservative retention superset; this does not invent read authority or stronger
evidence. Unclassified old bytes are not considered independent by default.

Before a governed private payload is written, an atomic content-free journal is
fsynced with its salted source identities, intended CAS digest and temporary-file
prefix. Only then may the payload be written. The committed event/reference
removes the journal; a crash before commit leaves attributable payloads/fragments.
Torn unpublished journal metadata precedes all private payload writes and is not
mistaken for a published corrupt journal. A corrupt published journal fails closed.

The mandatory governance control fields and version bundle require explicit
side-copy migration. Old writers fail the schema fence; old read-only cutover
helpers also fail a terminal control-state fence, including chained cutovers.
The pinned predecessor runtime and old wire contracts are not silently rewritten.

## Host maintenance protocol

These are explicit authenticated host methods, never actions requested by source
text, model candidates, a planner node or an automatic recovery timer:

1. `plan_source_erasure(session, principal, source_id, expected_version=...)`
   verifies the owner and exact current version, and returns a read-only closure
   plan. Planning reads retention metadata, not private content objects.
2. `begin_source_erasure(..., plan_hash=..., erasure_id=...)` requires the exact
   still-current plan and a scoped opaque identity. One transaction records the
   source tombstone, redacts every affected owner's historical references, fences
   affected tasks, and preserves mechanical accounting. A stale plan cannot act.
3. `resume_source_erasure(session, principal, erasure_id)` idempotently cleans
   only explicitly owned current-namespace CAS/temp references, fsyncs directories,
   vacuums SQLite and checks that old WAL pages can be truncated. Interruptions
   leave the already committed logical fence and can be resumed explicitly.
4. `source_erasure_receipt(...)` exposes the authenticated content-free status.

Original requests, raw responses, snapshots, model values and free-form
request/call/source identifiers do not survive in the redacted event projections.
Opaque identities, digests, authorization/accounting fields and redaction
certificates do survive for integrity and no-resend enforcement. These local
integrity records are not protection against an administrator rewriting the
entire database or directly copying its files.

An erased task cannot replay, resume, export its checkpoint audit, dispatch or
persist a late provider return. UNKNOWN call consumption remains UNKNOWN and its
hold is retained. Mechanical local/model/output accounting remains available on
the authenticated denial. A fresh final delivery check fences a cached result
loaded from an older WAL snapshot. Erasure does not increment the session-wide
ACL epoch: independent B-only tasks retain their authorization and replay.
Public original/snapshot/query/inference read exits also leave the content-read
WAL transaction before a fresh authorization/dependency check. Loaded inference
rows must still be the exact current references; a deleted or changed owner row
cannot deliver its old object. Each fresh check has a new retrieval work context.
Unmodified historical source events retain their authenticated original identity
even when the physical event hash chain is rebuilt after an A redaction.

Rollback continues to forbid ordinary execution and ingestion. A narrowly marked
host maintenance transaction can still inspect or finish erasure under READ_ONLY;
it cannot reactivate an old writer. An upgrade retry validates authorized redaction
certificates instead of repairing missing erased payloads from an old source.

## Completion and explicit limits

`LOCAL_REFERENCE_ERASURE_COMPLETE` means the authorized target reference closure
has been removed from this managed namespace, attributable unshared objects and
fragments removed, and SQLite old-page cleanup completed. It is not a statement
that identical bytes under an independent B reference, an external backup,
filesystem snapshot, device remanence or a prior provider delivery were erased.
Independently owned same-CAS references are retained and counted.

A reader holding an old WAL snapshot prevents physical completion and yields
`DATABASE_SCRUB_PENDING`. Unattributed files are preserved and produce
`UNATTRIBUTED_OBJECTS_RETAINED`. They are not guessed to belong to A, deleted by a
broad directory sweep, or ignored to claim completion. Cleanup I/O failure returns
a safe failure and leaves the durable intent resumable.

Migrated predecessor copies remain terminally fenced and are explicitly reported
as `PREDECESSOR_COPY_RETAINED`; this increment never unlinks another namespace.
An unresolved schema-4 mixed legacy capsule currently produces
`LEGACY_CAPSULE_REQUIRES_SCOPED_REDACTION`. Whole-ledger historical exports cannot
reopen it after a tombstone, and maintenance retries do not decode that mixed
capsule. These conditions are partial erasure, not successful whole-system erasure.

## Source-scoped legacy originals

Before an erasure, an authenticated owner may explicitly call
`prepare_legacy_capsules(session, principal)` on a schema-4 namespace. This copies
all original versions, lifecycle flags, mappings and migration descriptors into
source-scoped immutable capsules without running the old compiler again. Missing
originals, invalid Unicode, historical/withdrawn sources, conflicting current
versions and quarantine reasons remain exactly as imported. Capsules are not new
current sources or inferences. Original host ACLs and current source ACLs must
permit the conversion.
Separate original/descriptor ordinals preserve cross-source and record order
without adding fields to old records. Prepared content-free roots always retain
hash, schema, namespace and import-identity validation, including after erasure;
only an unprepared mixed package has the explicit no-redecode exception.

The same governed event ledger owns every capsule reference. Fsynced staging
journals precede object writes; a single transaction publishes all references
and replaces the mixed delivery root with a content-free root. A crash retries
the same immutable conversion. The old mixed object remains explicitly tracked
until an authorized erasure can remove it without losing independent originals.
No physical cleanup occurs merely from preparing capsules.

`legacy_source_view(session, principal, source_ids)` returns only the requested
source originals and closed, exactly verified source-span records. Current ACL,
import authorization ceiling and source tombstones are checked before object
loads and again in a fresh transaction before delivery, including after rollback.
`set_legacy_readers` permits an owner to restrict or restore historical-only
source readers within the original host ceiling; it never grants current model
execution authority. Source erasure covers every imported version even if no
usable current source exists, using the highest imported version as its explicit
expected-version identity.

Free-form reports, unsupported records, extra span fields and nonstandard origin
labels do not acquire exclusive source provenance from logical support edges or
matching text. Their exact old bytes and descriptors remain in non-deliverable
unknown-provenance capsules. They produce `UNKNOWN_LEGACY_PROVENANCE_RETAINED`
after erasure and prevent a complete-erasure claim. A selected B original remains
available when A is erased; this does not imply the unknown records or fenced
predecessor copy have been erased. This protocol is tested only on disposable
synthetic namespaces.

## Work still required

- Independently review and integrate the scoped capsule protocol with all
  remaining governed lifecycle consumers.
- Handle explicit provenance for opaque legacy records without guessing from
  logical supports, dropping unrelated originals, or regrading old evidence.
- Close the approved managed-copy deletion scope and source lifecycles without
  touching immutable public evidence packages or claiming provider retraction.
- Finish layered revisable/deletable personal/domain memory policies and the
  remaining M10 semantics, all-consumer integration and full research acceptance.
- Obtain a fixed-candidate independent review and exact remote regression/CI
  evidence. Development test results alone are not the publication gate.

## Qualified predecessor inheritance

The rebuilt retrieval predecessor is an additional exact 195-file runtime,
`542e2ea5c91bca24dd8983cf6a6b0c701f843fc8` (PR437 main merge), code hash
`96e5bf0fb7099dd6c4d98ca4cb80fc2bc3147a26a85a4a935ead3cdd8289d5f7`.
The published main has the identical runtime as reviewed local `71161ff`; its
complete Git tree matches local published-baseline candidate `d46e2e1`.
The historical 194-file baseline is the exact Python-only evidence snapshot
`c80d48eca23147e31802614f249dbbf7ac25e9d7`; its original code hash and
all migration assertions are retained. See `HCL_HISTORICAL_RUNTIME_SNAPSHOTS.md`.
The original 194-file retrieval runtime and its whole migration test class remain
unchanged. A second class repeats every original governance migration scenario
against the actual qualified predecessor, including retention inventory, controlled
cutover recovery, terminal legacy exports, synthetic erasure and retained predecessor
limitations. The upstream M09 current-eligibility gate remains on old cached
numerical results; immutable historical objects are not rewritten. These checks
use disposable synthetic stores only and do not erase user data.
