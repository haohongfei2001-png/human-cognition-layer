# S1.3: bounded migration and same-engine compatibility

This implements the approved S1.3 slice on S1.2/main
`21b63e227ead583ded0575f2ab65b073ba26733c`. It hands an offline executable
backbone to S2.1. S1 and the full T20/T24/T30 acceptance families remain open;
there is no live-model or effectiveness claim. Global legacy export cutover,
all historical experiment migrations, and domain-wide compatibility remain S5.

## Actual inputs and preserved meaning

`hcl.memory.migrations.legacy.LegacyAdapter` accepts the actual old
`AuthorizedText`, `CognitionWorkspace`, scoped evidence receipt,
`ReportAssessment`, `EventRecord`, and `NarrativeOrder` types. It reads snapshots
without calling preparation or answer backends. `LegacySnapshot` also accepts
explicit typed source versions and records supplied by the embedding host.
There is no assumed legacy database and no overwrite of the old objects.

The bounded import is at most 4,096 source/record entries and 16 MiB of encoded
snapshot data; excess input is refused, never truncated. Canonical objects
retain exact Unicode/CRLF source text and version, original report/interpretation
payloads, support AND-groups/OR-alternatives, challenges, analyst revisions,
withdrawn membership, order anchors, scope and recoverable fields. Deterministic
old-to-new IDs include the namespace; equal source-local names never establish a
global Entity. Legacy story `permitted_observers` remain metadata. Only separately
supplied host readers provision authenticated system access; the default is the
import owner alone. This explicit policy covers every imported source identity,
including historical, withdrawn and quarantined versions. All whole-package
views require the intersection of the immutable import policies and current
active source permissions; conflicting versions never union their readers.

Only unambiguous CURRENT sources with complete valid original text enter the
active source projection. Complete historical versions remain distinct in the
side copy. Missing originals, invalid offsets/hashes, unsupported types,
unresolved references, incomplete scoped receipts, and old event text without
exact original offsets have explicit quarantine records. The adapter never
reconstructs documents by concatenating quotes. The old workspace does not keep
all historical full text; those absences are retained rather than invented.

Mapped reports and interpretations are typed provenance, not new executable
semantic IR. Their original `grounded`/`SUPPORT_AVAILABLE` values mean recorded
live derivation roots, not truth. They create no new InferenceResult. Old report
families preserve correlation; independent support remains unestablished. The
known `v1.prepare_narrative` order-only provenance maps pseudo-UTC labels to
SOURCE_ORDER, preserving the original labels without asserting calendar/event/
access time. Arbitrary dates are not classified by their apparent value.

## Atomic import and terminal read-only rollback

`MigrationNamespace.import_snapshot` constructs a new isolated directory in a
same-filesystem unpublished staging area. A single transaction writes the
session, current sources, object references, immutable migration package and
schema-2 control row. It publishes the whole directory only after committed
objects and database are closed. Interruptions leave the destination absent;
repeating the identical import after reopen creates no events or revisions.
A different package or reader mapping cannot replace an existing namespace.
Concurrent publication cannot overwrite a prior import.

Ordinary stores keep schema 1. Only this explicit side-copy procedure creates
schema 2; no old database is silently upgraded. The actual fixed S1.2 store
implementation is tested to reject schema 2. The control row binds namespace,
owner/tenant, package hash, code-file digest, schema, rules, indexes, mode,
active target and a monotonic generation. Missing control or version mismatch
fails closed. One transaction changes both target and mode to the immutable
legacy snapshot and increments generation; no second file pointer can split.

Every normal runtime transaction checks this persistent control. Already-open
connections cannot write, rebuild, dispatch, resume cached tasks or deliver new
results after rollback. Cached and ordinary result delivery retain a separate
fresh transaction check after leaving earlier WAL snapshots. The fixed old
view has a separate read-only SQLite URI, never the writable store initializer
or an old generation callback. Its content and mapping delivery also recheck
current source access in a fresh transaction. Namespace administration does not
bypass a revoked source-read permission.

Rollback is deliberately terminal for this bounded slice. There is no automatic
reactivation API, new-schema-to-old-schema writer, or unreviewed resume path.
A future reactivation must validate code/rules/indexes, source permissions and
versions, and the complete budget ledger before opening execution. New events,
objects, inferences and call holds remain isolated and auditable. An in-flight
simulated send cannot be undone; an already persisted SEND_STARTED reservation
is retained if the fence prevents its result write. It is never cleared or
resent. Normal projection rebuild cannot delete or reset namespace control.

## Compatibility and real computation

`hcl.compat.CognitionWorkspace` requires the explicit durable store, authenticated
principal and session. `put_source`, `prepare`, `answer`, `run` and `stream` use
that same state and HCL engine. Prepared requests retain exact source versions;
stale versions reject. The adapter returns current typed TaskRequest/TaskResult
contracts, not fabricated old domain receipts. Story-observer provisioning,
partial narrative preparation and arbitrary legacy answer callbacks fail
explicitly. ModelGateway remains the sole execution gateway, with the existing
built-in offline port only.

The witness imports actual legacy sources and interpretations, executes the
existing real finite checker on separately explicit formal input, verifies
actual values in the delivered answer, reopens and replays, then rolls back and
proves the old connection cannot deliver the cached answer. Opposite explicit
models change both computed values and answer in the tests. This does not claim
that old interpretation prose has been compiled into formal truth.

## Verification

`tests/test_unified_s13.py` covers complete/missing historical versions,
withdrawal, exact source bytes, typed reports/order/support, quarantine, source
ACL and cross-tenant denial, ordinary and cached run/stream delivery races,
atomic failure before publication/rollback commit, independent writers, actual
predecessor schema refusal, no callbacks, idempotence and isolated unknown holds.
Original S1.1/S1.2 and unchanged legacy behavior tests still run. Hosted CI adds
the new tests and `scripts/witness_unified_s13.py` at exact PR head, alongside all
prior workflows. Evidence records this bounded offline slice only.

Independent review of initial candidate `a49a401` reproduced an ACL bypass when
two conflicting CURRENT versions were quarantined and consequently absent from
the active source table. The original content view checked only active rows.
The retained regression covers Bob-only conflicting originals, mixed public and
quarantined sources, mapping/receipt/legacy views, and read-only rollback. The
corrected gate checks every import policy before any content projection and
again in the fresh delivery transaction, including absent historical rows.
