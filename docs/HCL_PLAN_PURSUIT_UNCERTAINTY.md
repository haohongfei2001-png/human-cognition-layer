# Unknown pursuit is not negative plan evidence

This is a source-bound classification repair in the existing C03 plan checker.
It adds no extraction grammar, planner rule, native capability or model call.

## Demonstrated failure

At baseline `61da904bd5de34a974316c0d8188f582d21b9646`, a selected conditional plan,
reported opportunity and belief, and a contradictory declared model were prepared
without a separate recognized goal statement. C01 correctly retained
`goal_status=SYSTEM_INSUFFICIENT`; C03 nevertheless returned
`subjective_feasibility=NOT_CURRENTLY_PURSUED`. The same happened with an uncertain
goal and unresolved selection conflict. It also occurred when the original source
explicitly stated a goal in ordinary wording outside the bounded parser: complete
source preservation did not remove the misleading negative prepared result.

The negative label reached the actual ordinary-reader final input in offline
tests. C05's code treats that label as plan counterevidence, which confirms it is
not merely a private eligibility flag. However, the audited single-plan examples
were filtered earlier by C02, so no natural downstream wrong-motive result or
model-answer failure was demonstrated. A separate consumer-state test checks how
C05 handles the new unresolved label; it is not claimed as a natural failure.

## Minimal change

- Positive eligibility still requires a reported selected plan and active goal.
- Explicit considered-but-unselected, abandoned or completed plans, and explicitly
  abandoned/completed goals retain the existing conditional nonpursuit result.
- Other missing, uncertain or conflicting prerequisite evidence now yields
  `PURSUIT_UNRESOLVED`. Selection and goal status remain separately visible.
- Belief/opportunity checks, independent declared-model checks, source support,
  revisions, original text and quoted evidence are unchanged. A plan's purpose
  does not silently create an active goal or verified private intention.
- Only unresolved-pursuit results receive a short fixed code-owned qualification
  explaining that missing evidence is neither nonpursuit nor infeasibility. The
  text is selected from code, never copied from a payload policy string. Existing
  positive long-source cases do not acquire needless repeated policy text.

C05 code is unchanged. Its existing fallback classifies unresolved plan evidence
as unresolved, not counterevidence. Explicit opposite belief and explicit
opportunity/selection/lifecycle negatives keep their existing distinctions.

## Verification and evidence boundaries

Eight behavior test methods cover missing/unprepared/uncertain goals, unresolved
selection, active and explicit-negative controls, actual ordinary final input,
source revision/support withdrawal, code-owned policy generation and the bounded
C05 consumer-state check. Two further witness tests require the exact three-path migration and reject unrelated drift. The exact prior runtime fails nine assertions in the eight behavior tests; the
corrected targeted suite and existing C01/C03/long-plan/C05 regressions pass with
networking disabled. Exact-head/main CI identifies final adoption evidence.

The new exact runtime amendment changes only `hcl/cognition/plan_feasibility.py`.
It preserves all 51 prior history pins and three native-policy amendment artifacts.
The archived-v23 development witness now explicitly reports its three changed paths (classification, exact dependent claim identity and fixed policy); every other payload path must remain equal. Its original archive and report remain unchanged. Current validator references are retargeted; old grants, paid executors, reports,
scores and exact historical replay commands remain unchanged. Source-snapshot
and complete native-policy/shared-context repairs remain in place.

This is correctness evidence, not answer-quality, utility or I02–I06 confirmation.
There are zero provider calls in the repair. Any separately approved fresh
diagnostic remains subject to its exact runtime/package, case qualification,
source-first semantic review, disclosure permission, budget and deadline gates.
