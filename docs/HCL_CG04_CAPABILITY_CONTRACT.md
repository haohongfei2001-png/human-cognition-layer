# HCL-CG-04 — Contextual Value Conflict and Preference

Status: **CG04-A–D/CERT COMPLETE; CG04-E FROZEN; READY / DEFERRED_OWNER_AUTHORIZATION**

## User-visible capability delta

Explain which explicitly expressed preferences apply to a particular actor,
role and context, which conditions remain unresolved, and which competing
preferences the source leaves in conflict. A change in one role/context revises
only that preference. An observed choice, a third-party judgment or a later
statement must not become the actor's enduring values or a universal moral
ranking.

Example: Alice says that as a medic in fieldwork she prefers safety over speed
when it rains, and as a courier in deliveries she prefers speed over safety.
The checker should preserve both local statements, check the rain condition
from accessible source evidence, and refrain from declaring Alice inconsistent
or assigning global safety/speed weights. If Alice explicitly revises a local
statement, only its referenced lineage changes. Opposed unrevised statements in
the same scope remain a conflict, not a reason to invent a hidden priority.

## Bounds and evidence discipline

- One focal actor, up to four named actors and 24 source events.
- Up to eight explicit pairwise preference statements, six source-named values,
  two roles, two contexts and four boolean conditions. No value ontology,
  numeric weights, profile store, utility optimizer or autonomous recommendation.
- Every statement/condition is anchored to an exact source quote, actor, event
  time and record time. Self reports, explicit narrator reports and third-party
  attributions remain distinguishable. Source support does not prove sincerity,
  private psychology or moral truth.
- Reader/character/observer availability uses existing v0.6 boundaries. Hidden
  statements, conditions and revision references must not leak into any receipt.
- A requested role/context is a caller-selected scenario, not proof that the actor
  occupies that role. Applicability requires matching source scope and condition
  evidence. Unknown conditions remain unknown; inaccessible evidence does not
  imply their negation. Opposed source condition claims remain contested.
- A different role/context or a later choice does not revise a preference.
  Revision requires an explicit source-bound reference to the prior statement,
  the same actor/role/context, and later source time. Preserve other scopes.
- No inferred preference, transitive global ranking, majority vote or automatic
  moral winner. Uncompared alternatives stay unresolved.

Implementation and bounded grammar: [HCL_CG04_IMPLEMENTATION.md](HCL_CG04_IMPLEMENTATION.md).

## Canonical execution order

1. **CG04-A:** Explicit v1 operation/routing and source-projected case surface;
   generic preference/value words alone do not activate it.
2. **CG04-B:** Source/time/access grounding, conditional applicability and
   attribution distinction for the bounded statements.
3. **CG04-C:** Scope-local explicit revision and unresolved pairwise conflict;
   no global fixed weights or inferred cross-context consistency verdict.
4. **CG04-D:** Conservative ordinary-text preparation, exact anchoring,
   fail-closed ambiguity and actual debug state/final messages.
5. **CG04-CERT:** Positive, negative, privacy, temporal and regression checks
   on exact PR head and merged main; zero paid provider calls.
6. **CG04-E:** Freeze a fair C/P/G/H/H-new development package only after CERT;
   identical source/question/output vocabulary and H/H-new difference solely
   from the executed CG-04 checks. No source hunt or leaderboard work.

If provider-free implementation, certification and package freeze are complete
and paid validation is the sole remaining action, preserve the existing proposal
as **READY / DEFERRED_OWNER_AUTHORIZATION** during the owner-authorized night,
and immediately continue provider-free work under DEVELOPMENT_PLAN section 14.
CG-03's consumed authorization and unused money do not transfer. No new paid
experiment is authorized; LongMemEval remains sealed.

## Current evidence

PR #135 exact-head and exact-main receipts both record 142 v1 + 176 historical
provider-free PASS with identical runtime digest. See
[certification](../reports/HCL_CG04_PROVIDER_FREE_CERTIFICATION.json). CG04-E is
[frozen](../reports/HCL_CG04_EXTERNAL_PACKAGE.json), with all four treatment
gates passing and a [prospective protocol](HCL_CG04_EXTERNAL_DEVELOPMENT_PROTOCOL.md).
No paid call is authorized or executed. This certifies bounded correctness and
treatment presence, not external utility or broad value understanding.
