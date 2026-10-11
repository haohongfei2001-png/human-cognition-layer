# S1.2: persistent execution of the same real computation

The approved S1.2 slice extends the S1.1 engine. `StateStore.sqlite(path)` opens
SQLite WAL state; `StateStore()` remains the small in-memory test fixture.
`HCL.run`, `stream`, the source-bound finite checker and actual-value answer
validation retain one execution path. This is offline integration, not complete
S1/T-family closure, ordinary-language compilation, or effectiveness evidence.

## Storage and replay

- SQLite records versioned session, source, inference, task and call projections
  alongside an append-only integrity-linked event ledger in the same transaction.
- Canonical, typed JSON content objects hold source/formal input, raw model
  returns and TaskResults. The writer fsyncs and atomically renames an object
  before committing its reference. Interrupted work can leave orphan objects;
  it cannot publish references to incomplete objects. Metadata contains hashes,
  rather than another plaintext copy of source/question/return bodies.
- The typed decoder uses an explicit contract registry, never pickle, import,
  source execution, or an arbitrary class name. Object hashes and the replay
  chain are checked. Rebuilding projections is a trusted-host operation under
  an exclusive write transaction. A failed rebuild leaves prior projections.
- The current schema is version 1. A newer schema is refused; S1.3 supplies the
  bounded migration/rollback path. Event integrity is not protection against an
  administrator rewriting all storage, and deletion/retention is not yet closed.

## Conflict, access and scope

All reads authenticate tenant and session membership before source access.
Commit checks exact positive read versions, ACL epoch, rule version, delta
consistency and non-future base revision. Revoke-then-restore changes the epoch.
The only supported write effect is appending fresh inference identities. Such
disjoint writes can rebase after unrelated changes when actual dependencies are
unchanged; base and actual committed revisions remain recorded. A source change
or identity collision rejects rather than overwriting a result. Query/absence
dependencies and derived retrieval indexes remain later work, not inferred from
this positive-read-set proof.

The engine validates the actual operator read set at delivery and replay. A
cached result cannot survive a dependency change or access epoch change. Every
failure delivery is source-free, even when a prior simulated send is recorded.

## Task budget and recovery

`TaskBudgetLedger` binds principal/session/request identity to the whole request,
including its immutable budget. Every branch uses that task lease and a distinct
call ID. A transaction checks access, context and shared remaining capacity,
then persists a unique reservation. Separate connections cannot reset capacity
by presenting another CallSpec or replaying a request with larger limits.

Calls progress through `RESERVED`, `SEND_STARTED`, `RETURNED`,
`FAILED_BEFORE_SEND`, `UNKNOWN` and `VALIDATION_REJECTED`. Raw returned content is
persisted before output validation. Unknown usage is `None`, with an occupied
hold, not a zero estimate. All reservations conservatively occupy the task's
mock-call limit, including confirmed pre-send failures. Request/output byte
limits remain per complete call; the mock-call count is task-aggregate. Real
token/currency pricing and provider capability negotiation are not implemented.

Opening another connection does not recover live work. After the host confirms
the execution owner is abandoned, `RecoveryManager.recover_abandoned` requires
its exact owner identity and atomically marks possible sends unknown. A reserved
but unstarted call is a known pre-send failure. Returned content stays preserved.
The interrupted task cannot resend. Completed tasks replay the checked result
after fresh authorization; a separate replay counter records zero new calls.
No network exactly-once guarantee or automatic provider retry is claimed.

## Verification

`tests/test_unified_s12.py` exercises the real finite-result/answer chain after
reopen, opposite inputs, rebuilding all projections, independent-connection
commit/call-budget races, unchanged versus changed dependencies, ACL restoration,
corrupt objects/events, write interruption, unknown send, invalid raw returns,
and failure at reservation/send/return/final-result boundaries. One test starts
a fresh Python process, terminates it with `os._exit` after durable send-start,
then recovers from a separate connection without another attempt. All inputs
are synthetic; the only transport is the built-in offline fixture.

Independent review of candidate `d5c9fb2` exposed four concrete failures, retained
as negative regressions: late revocation left source/derived fields in a failure
receipt; cached delivery could use an old WAL snapshot after revocation; pending
or interrupted tasks reported unknown held usage as zero; and object filesystem
errors escaped the safe diagnostic boundary. Failure receipts now start from a
source-free base, both cached paths perform a fresh delivery authorization check,
restart accounting aggregates every branch's known/unknown holds, and object I/O
errors become `STORAGE_FAILURE`. Tests cover run/stream and repeated/reopened
delivery, multiple known/unknown branches, and bind/reserve/return/finish writes.
The final check does not promise atomic cancellation after delivery has occurred.

```
python -B -m unittest tests.test_unified_s12 tests.test_unified_s1 tests.test_quantified_logic tests.test_argument_readings -v
```

S1.3 migration/compatibility remains next. Full M01–M16, T01–T32 and S1–S7
research goals remain unchanged. Current evidence does not authorize paid work
or upgrade historical A–H/G-ARCH results to new-system capability proof.
