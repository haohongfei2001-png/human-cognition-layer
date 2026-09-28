# Lossless source-record pool for composed cognition

## CAPABILITY_DELTA

A tighter composed-context budget can now carry all three existing checked
operations where the previous transport refused the whole context. Source
projection happens first; storage pooling changes no operation's access or
inference. This is integration/cost work, not a third candidate.

Opt in with `prepare_composed_answer(..., pool_sources=True)`. Identical
actor/raw-text/event-time/record-time fields are stored once in `source_records`.
Every operation retains its own event/source IDs and evidence list. Records
with different actor/event/record time are not pooled. Storage sharing never
means shared access, belief, agreement, identity or cross-operation support.
The codec verifies a complete lossless round trip. `expand_composed_sources`
restores all raw records before `expand_cognition_context` restores stage state.
Missing, changed or colliding references fail; unique records stay literal.

Seven tests cover actual final-input equality, all three operations fitting a
formerly insufficient budget, private hidden-source exclusion, actor/time/
record-time differences, missing/tampered references, immutability and whole
budget refusal without selecting a partial operation or retaining a source pool.
An existing integrated authored narrative's complete input shrinks from
21392 to 20341 bytes (4.91%), including new policy overhead. [Receipt](../reports/HCL_NIGHT_SOURCE_POOL_BYTE_AUDIT.json).
This measures transport bytes only, not token bills, model efficacy or independent
external evidence. Direct/frozen CG04/05 inputs remain unchanged.
