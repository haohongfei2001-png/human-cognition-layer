# C05 — Integrated agency and appraisal

## CAPABILITY_DELTA

Correcting a pre-action belief now changes the plan-dependent action explanation.
Adding a later belief revision changes current plan feasibility while preserving
the earlier conditional explanation. Reported goal appraisal remains separate;
no unsupported emotion or unique motive is generated from plan failure.

`prepare_agency_chain` accepts an ordinary actor/action/appraisal question. C02
identifies the exact action span; C03 is checked on both its source prefix and the
current source; C04 supplies the separate appraisal/feeling channels. Goal/action
keys connect C02 candidates to actual C03 results. Unsupported or contradictory
plan conditions weaken or suspend the joint candidate rather than being hidden
behind a supported goal. Multiple plan readings remain unresolved. Explicit model
failure never implies the character knew the plan would fail.

The action-prefix computation is rooted in an exact original-document span and
registered for source-version invalidation. It is a conditional source-order
projection, not verified chronology or an independent source. Current source
knowledge is never silently reused as past knowledge. All final conditional claims
have support dependencies; changed source or withdrawn support rejects stale input.
`SemanticWorkspace` shares question-neutral preparation across operations, filters
access before any backend call, and bounds configured extraction attempts. A local
prefix replay does not consume another backend call. Actual final model inputs
contain the joined results, source text, separate past/current checks and cautions.

## Verification and limits

Thirteen targeted tests cover positive dependency changes, source/actor/access/time
boundaries, uncertainty, absent action, misleading expression, competing/unique
motive refusal, source revision, stale support, final-input budgets and one shared
extraction replay. Full v1 and 176 historical regressions run in exact-head/main CI.
`scripts/witness_agency_chain.py` saves positive actual inputs in
`reports/HCL_WAVE_C05_WITNESS.json`. PR CI records SHA and runtime hash; preceding
C04 exact-main `d07ae442bd35add0c73f6de970137c3093598dab` passed all six workflows
(v1 run `36489365166`).

**CORRECTNESS_VERIFIED / REPLAY_VERIFIED / UNTESTED / OPT_IN**. Explicit bounded
English forms and exact source-local keys; 16 statements from C03. No broad motive
or emotion understanding claim. Zero actual provider calls/spend in this package;
LongMemEval remains sealed. A useful real extraction/final functional check remains
part of operational readiness, not independent efficacy. Wave C construction is
complete. NEXT_READY: D01 social-act/commitment lifecycle, then D02–D05.
