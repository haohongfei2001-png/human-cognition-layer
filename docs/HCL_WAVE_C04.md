# C04 — Goal-linked appraisal, mixed reports and reappraisal

## CAPABILITY_DELTA

The same episode can support one evidenced goal and hinder another. HCL now derives
mixed goal congruence while retaining reported feelings as a separate channel.
Explicit reappraisal retires only its matching earlier appraisal. Changing the
evidenced goal set changes a conditional relevance check without automatically
retracting the character's reported relief/worry or inventing a new actual feeling.

## Mechanism and reuse

`prepare_appraisal` combines C01 goal state, A01/A02 source dependencies and the
retained v0.8 affect runtime. v0.7 validates prior source goals before goal-linked
appraisal; v0.8 validates speaker, source quotation, episode and explicit revision
anchors. Reported emotion, observed expression, third-party judgment, uncertainty,
control and certainty appraisals remain distinct. Multiple direct feeling reports
can coexist without a global score or an inferred unique emotion.

Current goal-sensitive projection includes evidenced active/completed goals;
abandoned or uncertain goals suspend that conditional link while original appraisal
and feeling reports remain available. Conflicting appraisals of one goal are not
mislabelled as mixed independent goals. Missing or ambiguous reappraisal anchors
remain diagnostics. No rule turns smiling, an outcome, goal completion or a
reported appraisal into an actual emotion. Reported control/certainty establish
neither actual control nor knowledge.

Ordinary actor/episode questions select a source-local view; B02 observer/past
prefixes can be used without importing later disclosure. Source-order adapter
timestamps are explicit ordinal assumptions, not calendar facts. Source/support
changes invalidate prepared input. The actual final payload includes native
current/historical evidence, source events, goal context and conditional results.

## Verification and limits

Fourteen targeted tests cover positive mixed appraisal, different people/goals,
explicit reappraisal, goal revision, expressions/attributions, control/certainty,
uncertainty, missing/future goals, source/actor/access/time/episode boundaries,
negative forms, stale support and budgets. Full v1 and 176 historical regressions
run in exact-head/main CI with SHA/runtime hash. The ordinary authored witness is
`scripts/witness_appraisal.py`; actual final inputs are saved in
`reports/HCL_WAVE_C04_WITNESS.json`.

**CORRECTNESS_VERIFIED / REPLAY_VERIFIED / UNTESTED / OPT_IN**. Bounded explicit
English forms and exact source-local episode/goal keys; no emotion diagnosis,
global value weights, automatic motive inference or independent efficacy claim.
At most 20 source statements, bounded by C01's focal-actor limit. Zero provider
calls/spend; LongMemEval untouched. NEXT_READY: C05 integrated belief → plan →
conditional action explanation → appraisal, preserving unsupported emotion as unknown.
