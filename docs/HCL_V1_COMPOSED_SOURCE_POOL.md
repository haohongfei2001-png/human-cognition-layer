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


## Per-stage preparation defaults and shared access policy

Thev2 encoding additionally restores exactly declared zero per-stage semantic-
preparer/extraction calls and extraction cost, zero stage answer calls, null answer
cost, and `DEFERRED_TO_SINGLE_COMPOSED_ANSWER`. Only stages with all six exact
values/types may use `preparation_defaults=true`. The final answer anticipation
remains one at the composition receipt; defaults are not aggregate usage.
Nonzero, missing or float-typed values, method/failure, local validator count,
source-access status and time basis stay literal. No cognition state or source
is selected, inferred or removed. The existing decoder accepts oldv1 and newv2;
unmarked, incompatible, duplicate or malformed defaults fail closed.

Default encoding is considered only with a real duplicate source pool and at
least two eligible stages. It must save bytes including additional decoder-policy
overhead. `pool_preparation=False` keeps the previous literal audit representation.
Shared narrated-access policy appears once per composed input; per-operation
access links and proof decisions stay unchanged.

**CAPABILITY_DELTA:** all existing checked operations can fit a tighter total
context budget without dropping any state, source or uncertainty. Seven new tests
cover actual decoded equality, backward compatibility, strict counter types,
private access, tampering, policy sharing and whole-budget behavior. The committed
byte audit measures complete transmitted JSON including policy on four existing
integration inputs. Bytes are not token cost, actual provider cost or model
utility. No default frozen-case change, third candidate, paid run or evidence upgrade.
