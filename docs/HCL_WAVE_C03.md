# C03 — Belief-dependent plans versus declared-model conditions

## CAPABILITY_DELTA

A character's reported belief can conditionally support a selected plan while an
explicit declared model contradicts its condition. HCL now preserves that divergence
without claiming the character knowingly chose an infeasible plan. Explicit belief
revision changes the dependent plan check. An explicitly abandoned/replaced plan
can retain the same goal, with no inferred value change.

## Mechanism and boundaries

`prepare_plan_feasibility` joins C01 goal/plan/opportunity checks, B03 reported-belief
revision and source-anchored declared-model conditions through A01 dependencies.
Both use A02 ordinary quoted input. Native B03 basis records are rebound to original
shared source candidates, including earlier revision anchors. Narrator model
statements are conditional model declarations, never actual world truth or evidence
that a character believed/understood them.

`I do not believe p` means no affirmed belief in p, not belief in not-p. Explicit
`I believe it is false that p` is a different condition. Unknown, uncertainty,
conflicting beliefs/models and absent opportunity never become a positive feasible
plan. Explicit model conditions are local literal propositions, not a global model
or ontology. Model checks cover the declared condition only; they do not certify
all requirements of real-world feasibility.

The B03 adapter clock encodes source order, visibly, not verified calendar/event
time. Actor-visible B02 prefixes exclude later revisions and unseen model text.
Source changes or challenged support invalidate saved final inputs. Actual final
messages preserve original sources, goal/plan state, belief transition receipts,
model assumptions and the dependent result. No condition is silently filled from
the other perspective.

## Verification and state

Eleven targeted tests cover the positive divergence and two revision kinds,
negation scope, actor/source/access/time separation, model-to-belief leakage,
conflict, uncertainty, missing opportunity, refusal, stale support and budgets.
Full v1 and 176 historical regressions run in exact-head/main CI with SHA/runtime
hash. `scripts/witness_plan_feasibility.py` produces the ordinary authored witness
and actual final inputs in `reports/HCL_WAVE_C03_WITNESS.json`.

**CORRECTNESS_VERIFIED / REPLAY_VERIFIED / UNTESTED / OPT_IN**. Bounded explicit
English, one literal condition per plan, one source identity/model domain, at most
16 statements. No open-world planning, generic solver expansion, private-state
truth or independent efficacy claim. Zero provider calls/spend; LongMemEval
untouched. NEXT_READY: C04 goal-linked appraisal, mixed affect and reappraisal.
