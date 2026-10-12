# S2.3: budgeted execution, local recovery and executable common contracts

This is the approved S2.3 offline integration slice, based on main
`8643a82cf909890879fb413f56a7ebe74a44334f` / PR #428. The original S1–S7 goals,
M01–M16, P01–P38, T01–T32, all 61 migration entries and every original slice exit
condition remain unchanged. Neither S1/S2 nor any full acceptance family is
closed. Necessary offline contracts permit dependency-safe S3/S4 construction;
real-model functionality and effectiveness still need their original evidence.

## Entry and the evidence boundary

`HCL.run`, `run_sync` and `stream` use the same authenticated engine. A new
`ExecutionIssue(kind="cognition.execute", goals=(...))` and `ExecutionBudget`
select this versioned protocol on an explicitly upgraded schema 3/4 store.
Goals are host-selected typed cognitive obligations; the question and source
text remain ordinary unmodified Unicode. This does not demonstrate automatic,
source-faithful decomposition of arbitrary natural-language questions.

Available obligations are explicit finite-interpretation checking, candidate
semantic/FOL comparison, persisted scoped revision, source reporting and an
explicit unverified expression path. The planner expands the necessary
compile/compute/delivery prerequisites backwards and schedules ready nodes
forwards. A finite check needs no model call; expression needs one; actual
compiler diagnostics and source-alignment gaps can create additional repair
calls. There is no fixed three-operation or two-call ceiling. No irrelevant
operation is required merely to obtain an execution count.

`OfflineModelPort` remains the only installed transport. Its optional finite
response sequence is a test condition, not an extraction algorithm. Candidate
JSON cannot contain solver labels or executable code. Actual existing finite
checking, isolated FOL calculation, countermodel checking, temporal/identity
and truth-revision kernels determine the downstream results. Changed inputs,
late evidence and withdrawn roots change those results and their consumed
claim fields. Open extraction, alignment and completeness remain unproved.

## Common contracts for S3/S4

The new protocol is `hcl-execution-1`. Existing `TaskRequest`, `Issue`,
`BudgetSlice`, `Snapshot`, `Delta`, `OpResult`, `QuerySnapshot`, `QueryDelta`
and their encoded field sets remain unchanged. New dataclasses have separate
registered codec names. An old request re-encodes byte-for-byte identically,
including its task fingerprint and old request-ID conflicts.

`LocalModelOperator.run(snapshot, issue, allowance) -> OpResult` is an executable
three-argument interface. A `ModelIssue` binds an immutable `LocalModel` and,
only for revision, a prior computed inference used for local recomputation.
Current allowlisted dialects are:

- `finite-interpretation-1`: exact reference to the source's supplied finite model;
  calls the existing finite checker.
- `semantic-readings-1`: source-bound candidate AST and exact original slices;
  recompiles those candidates and calls the actual isolated FOL operator.
- `scoped-revision-1`: an exact indexed signed query; uses the actual revision
  operator on a `QuerySnapshot`, including its current absence dependencies.

Each model carries `domain_assumptions`, `fit_residuals` and
`unmodeled_observations`. These qualifications survive in the computed result,
its identity and the checkpoint; residuals/unmodeled observations keep the task
partial. They cannot be erased to make a model fit. This does not make these
three dialects a completed implementation of S3/S4's future local models.
Those domains must add reviewed typed dialects and real operators under the
same bounds, without arbitrary Python, imports, filesystem or network effects.

Snapshots stay immutable, including recursive checkpoint maps. Repeated source
snapshots are losslessly interned inside each checkpoint using a content hash;
references are checked on restoration and before each model reservation. No
source bytes or historical failure are discarded by this interning.

Every computed operation declares actual `append_inference` effects. The
controller checks source/principal/session/version/read-set identity, result
IDs, resources and the effect declaration before accepting a commit.
Delivery eligibility binds the complete accepted operation hash, including values,
read sets and effects, across repair iterations and checkpoint recovery. It is the
only writer. A stored, byte-identical committed candidate may be recognized
after a crash; a mismatching result or dependency cannot masquerade as that
commit. Only committed accepted effects are eligible for final delivery.

## Dynamic scheduling and shared hard budgets

Independent ready pure computations run concurrently in worker threads. Their
checkpoints, reservations and commits remain serialized by the event-loop
controller and SQLite transactions. The store's exact positive/query dependency
checks permit disjoint append rebasing and reject relevant changes. A changed
revision query invalidates only the dependent local computation and its delivery
node; the already returned proposal and independent results are retained. The
controller never resends a model call to repair a commit conflict.

Task-wide limits cover steps, feedback attempts, local computation reservations,
model-call holds, per-request bytes, cumulative request bytes, per-return visible
bytes, cumulative output bytes and final delivery. The existing local unit is
operator-specific (finite formula evaluations, FOL classification batches or
truth-kernel runs); it is not a claim of equivalent compute or calibrated VOC.
A full declared local slice is reserved before revision work and unused capacity
is released only after observed accounting. In-flight independent reservations
are awaited before declaring a shared-budget failure. Interrupted local work
retains its hold and has unknown rather than invented-zero usage.

Model call reservations bind the exact persisted graph node, call ID, snapshot,
serialized packet hash, authenticated task question and original allowance.
Changing a per-step context is legal only through this explicit binding; the
old exact-context gate is not removed. All branches still share the same task
call ledger. Cumulative output admission also reserves room for final delivery.
Unknown sends block further graph dispatch, including attempts with new call IDs.

The no-progress key contains the Issue, model ID/version, input source versions,
operation, concrete diagnosis and normalized candidate already obtained.
Confidence/certainty/explanation-only changes do not create progress. A repeated
invalid proposal stops with `NO_PROGRESS`; field-distinct valid repair attempts
may continue within the already granted task budget. Source gaps generate exact
segment-alignment obligations. Contradictory formal premises are not silently
removed to force consistency; their actual unresolved result remains visible.

## Complete evidence and bounded model context

Complete original sources, raw model requests/returns, failed validation events,
local models, computed proofs and graph checkpoints remain in authorized storage.
The model receives only its currently relevant typed contract, exact selected
source slices, unchanged question and bounded field/segment-specific challenge.
The old duplicated full-source plus segment payload is not used by this path.
There is no full catalog or complete audit-log dump in a model request.

The context compiler covers all source characters, splitting long paragraphs at
Unicode boundaries and preserving source version, full-source hash, character
positions and byte positions. It greedily packs exact fragments against the
complete serialized request limit. Mechanical segmentation is streamed once;
source hashes/byte-offset indexes and empty-source contract templates are reused.
Packing accumulates exact encoded segment sizes without repeated whole-source
construction, including thousands of short lines. An oversized question/necessary contract
fails before reservation. Tests include Chinese/emoji evidence exceeding 36KB
and a decisive final negative fragment; every fragment is processed or an
explicit unresolved obligation is returned.

This slice does not certify cross-chunk semantic composition. Each chunk's FOL
result is explicitly local; multiple chunks force `CROSS_CHUNK_COMPOSITION_UNPROVED`
and retain conflicting results. Exhausting calls before late material cannot
produce a global completed conclusion. Revision programs requiring cross-packet
ID composition currently report a capacity frontier rather than overwriting a
source's full index with its final fragment. Complete cross-fragment meaning and
S6-scale memory/retrieval remain open.

For the built-in fixture, UTF-8 byte count is a conservative token upper bound,
not observed token usage. Declared context/output capacities and explicit task
limits are both enforced; unknown capabilities are not fabricated. A new live
port must negotiate its own reviewed tokenizer/estimator and transport authority.
The execution profile currently bounds each goal's loaded sources and each
complete checkpoint to 4 MiB, up to 32 original goals, 1,024 chunks/steps and
16 feedback attempts. Default limits are smaller. Exceeding a bound produces a
specific safe capacity diagnostic; these are not S6 capacity or effect claims.

Final output is a compact deterministic projection of checked actual fields.
`ProjectedResultField` binds exact nested paths and allowlisted key selections,
never a generated summary.
Frame, perspective, time/cutoff and model qualifications remain visible. Full
countermodels and source slices remain in storage instead of being copied into
every final receipt. The byte allowance is checked against the encoded complete
TaskResult as well as its visible text and cumulative output consumption, including
metadata added to cached/restarted delivery. A replay capacity refusal preserves
the original known call usage and completed task object. A
refusal retains verified intermediate results, without emitting partial unchecked
prose. `stream` emits status then the same verified result as `run`.

## Persistent recovery, errors and current ACL

Checkpoints and task transitions use the existing hash-checked object/event
ledger. No new projection table or implicit database upgrade is introduced.
`RecoveryManager.resume_execution(request, expected_owner_id=...)` is an
explicit authenticated host handoff, never a timer, reopen side effect or model
instruction. It fences the old task owner and returns a versioned ResumeToken.
Ordinary repeated `run` cannot claim a still-active graph.

- RESERVED abandonment preserves a known-zero attempt and its reservation; it
  is not silently replaced with a fresh call.
- SEND_STARTED becomes UNKNOWN under explicit recovery. UNKNOWN cannot resume
  the graph or release its cost hold.
- A durable RETURNED response is revalidated and recompiled without transport.
  Recovery rechecks the same encoding, byte/token constraints and current ACL.
- A checkpointed computed candidate resumes commit without rerunning its solver;
  a crash after commit recognizes only exact already committed effects.
- Semantic profile and model capabilities are bound in the checkpoint. Recovery
  cannot silently enlarge limits or switch calculation profiles.
- Source/epoch/rule/query changes are checked before reservation, send, returned
  content, commit, final delivery and cached replay. Failures/revocation rebuild
  a source-free receipt, including run/stream and restarted paths.

Compiler failures record stage and specific field alongside the original
RETURNED row; repairs are new budgeted calls. A valid independent branch can
still yield a clearly partial answer. Invalid input, missing evidence, budget,
unknown transport, local solver uncertainty, storage failure and stale state
remain distinguishable. Complete raw audit is available through
`RecoveryManager.execution_audit`; because it includes failed branches, it uses
a stricter current-owner/all-session-source ACL gate and a fresh post-read check.

## Exact S2.2 runtime side-copy migration

Adding runtime files changes the whole-runtime bundle, so current code must not
simply open the old S2.2 schema 3/4 store. `RevisionCutover` now accepts the exact
shipped S2.2 predecessor from main `8643a82...`:

`ff8d68236a625b575c4d39f4eabf7aeba7da034ae5277338d6a518b4723fecea`

It validates ACTIVE mode, exact schema/rules/index version, original published
path and, for schema 4, both matching control bundles. It preserves old domain
rows, objects, events, task fingerprints, call states, owner IDs and UNKNOWN
holds. Only the fully verified unpublished copy replaces its revision control;
the source retains its old control and receives a terminal schema-91 fence.
The target remains schema 3/4. Existing S2.2-created schema 2 also has an exact
predecessor path; older accepted pins are unchanged.

The existing fsynced ownership, serialized same-target recovery, unique staging,
final-path binding and atomic directory publication remain. Rollback is terminal
and retains new audit events; it never reactivates the old writer. Original and
quarantined package ACLs remain authoritative for read-only legacy material.

Tests materialize only the 162 inventoried Python runtime files from that fixed
Git commit into a temporary process. That real old runtime creates schema 2/3/4,
completed ordinary and revision/query tasks, RESERVED/SEND_STARTED/UNKNOWN rows
and a quarantined private package. Current tests verify unchanged object bytes,
request fingerprints, zero-send replay, already-open old-writer rejection,
post-fence crashes, concurrent recovery, final-path denial, ACLs and bad-bundle
rejection. This is an actual predecessor exercise, not changing a current test
store's version string to pretend it was old.

## Verification and limits

`tests/test_unified_s23*.py` cover real calculations, variable repair counts,
actual parallelism, shared budgets, long Unicode coverage, error surfaces,
no-progress, accepted-effect gates, recovery, migration and current ACL. Existing
unified/logic tests, all 1,643 legacy IDs and all 60 diagnostic checks retain their
established current/historical partition. No old guard, pin or behavioral assert
is weakened. `scripts/witness_unified_s23.py` records exact commit/runtime hashes,
actual values and consumed fields for zero-call computation, three-call repair,
known-return recovery and late-evidence absence revision.

During implementation, an effect-rejection test exposed that an uncommitted
candidate could still enter partial delivery. Delivery now requires exact
committed result references. A 4-MiB checkpoint test then exposed repeated full
snapshot expansion; lossless in-checkpoint interning fixed the real long-input
case without deleting source evidence or raising the limit. The failing tests
and subsequent positive/negative regressions are retained in the development
verification history. Independent review additionally found a repeated-ID repair
collision, quadratic short-line context preprocessing and replay metadata capacity
overrun. Full operation-hash eligibility, streamed additive packing and shared
initial/replay delivery checks address them; run/stream/restart and exact-usage
negative regressions retain the original failures.

This is offline functional integration under supplied interpretations. It does
not establish open task/semantic decomposition, cross-chunk meaning, independent
alignment/completeness, learned scheduling, arbitrary generated programs,
real-model functionality, full T20/T21/T22/T25/T28, full S1/S2, S6 scale or S7
independent effectiveness. These original requirements remain on the formal plan.
No paid provider, credentials, new service, sealed material or historical grant
was used or created.
