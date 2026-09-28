# D05 — Multiparty joint plans and bounded authority

## CAPABILITY_DELTA

Three participants retain separate goals, selected plans, opportunities,
endorsements and receipt paths. A sourced rule/role/grant changes whether the
final-action executor has conditional authorization; revocation removes that
permission without erasing goals. New receipt of a peer endorsement can repair
coordination for the affected participant without changing the other views.
Receiving permission does not confer power to delegate it.

`prepare_joint_plan` joins C01 individual plan checks, B02 time-specific delivery,
CG02 proposal/acceptance validation and explicit source-local authorization.
Each acceptance requires receipt of the proposal by its formation point. Current
peer endorsement receipt remains separate. Every selected final-action executor
requires their own received grant. Rule and role evidence must precede a grant;
late assignment cannot authorize it retrospectively. Only the grant issuer's
explicit revocation changes that grant. Third-party reports and unrelated contexts
cannot substitute for an authorized issuer. No group-level private state is made.

These checks establish conditional coordination premises, not plan success,
verified consent, legal authority or infinite common knowledge. The simplest
alternative is a generic participant/message/permission table; post-G-ARCH
comparison should simplify this join if its dependency handling adds no utility.

## Verification and limits

Fifteen targeted tests cover a positive three-person plan, unequal audiences,
missing peer acknowledgment, late/unrelated roles, third-party report, unreceived
grant, revocation, nontransferable authority, every final executor's permission,
different goals, late receipt, source/access/support boundaries and budgets.
Full v1 and 176 historical regressions run in exact-head/main CI. The ordinary
positive witness saves actual inputs in `reports/HCL_WAVE_D05_WITNESS.json` via
`scripts/witness_joint_plan.py`. Preceding D04 exact-main
`a36c3bdad46d5f93be2405a9f77ccbd13a97b276` passed all six workflows (v1
`36493447036`).

**CORRECTNESS_VERIFIED / REPLAY_VERIFIED / UNTESTED / OPT_IN**. Three named
participants, one sourced proposal/local goal, bounded explicit English, at most
24 statements subject to A02's 64-candidate limit and CG02's six-act limit.
Only selected unconditional plans with reported opportunities qualify; unproved
conditions remain unresolved. Source order/accuracy are assumptions. No legal,
moral or efficacy claim. Zero provider calls/spend; LongMemEval sealed. Wave D
construction is complete; NEXT_READY: E01 domain-scoped relationship evidence.
