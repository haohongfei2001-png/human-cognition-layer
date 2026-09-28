# D01 — Conditional commitment lifecycle

## CAPABILITY_DELTA

HCL distinguishes a condition that is false in the provided source, an unknown
condition, a recipient who did not receive it, and an explicit withdrawal. The
original conditional promise survives a later withdrawal in the audit. Later
receipt updates current delivery without becoming evidence that an earlier
expectation included the condition. Acceptance and reported fulfillment remain
separate from comprehension, verified outcome, obligation, blame and trust.

`prepare_commitment` grounds explicit conditional promises and named responses
from ordinary speech. A01/A02 provide source and support boundaries; B02 supplies
receipt semantics; the existing CG02 source checker validates acts, conditions,
response references and reported expectation comparisons. A new lifecycle join
uses explicit source condition reports, acceptance/refusal, withdrawal and
fulfillment. Conflicts remain visible. Each expectation gets its own source-prefix
receipt check. No addressing-to-receipt or receipt-to-understanding promotion.
CG02's historical INCONCLUSIVE disposition is unchanged; reuse of its bounded
checker does not turn this correctness work into efficacy evidence.

## Verification and limits

Fourteen targeted tests cover positive state changes, missing/false/conflicting
conditions, absent/late receipt, acceptance/refusal, withdrawal, reported
fulfillment, source/actor/access/time boundaries, early/ambiguous references,
negative promise forms, source revision, support withdrawal and context budget.
Full v1 and 176 historical regressions run in exact-head/main CI. Actual final
inputs are saved by `scripts/witness_commitment.py` in
`reports/HCL_WAVE_D01_WITNESS.json`. Preceding C05 exact-main
`df9d66cf1f0cbfe436548ec0450161cf85bc42ce` passed all six workflows (v1
`36490715053`).

**CORRECTNESS_VERIFIED / REPLAY_VERIFIED / UNTESTED / OPT_IN**. Minimal explicit
English conditional promises, exact action/condition keys, one matching promise
per query; no legal or moral obligation inference. Native CG02 bounds (six acts,
four actors, two reported expectations per act) remain enforced. Source order is
not verified chronology, and current narrator facts are source claims, not world
truth or the recipient's knowledge. Broader social repair is D02–D05 work. Zero
provider calls/spend; LongMemEval sealed. NEXT_READY: D02.
