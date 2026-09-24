# HCL v0.4 Proposition Revision and Stance Amendment v0.1

Status: **BOUNDED CORRECTNESS AMENDMENT — IMPLEMENTATION CANDIDATE**

## Why this amendment exists

Recent controlled internal diagnostics exposed a general representation defect:
a later correction can be received without being accepted, while a prior
belief estimate can remain in state and be mistaken for a certified current
stance.

This amendment addresses that mechanism-level defect. It does not tune or rerun
any consumed diagnostic fixture.

## Frozen boundary

The amendment adds one first-class semantic relation:

```text
PROPOSITION_REVISION
  proposition_id = new proposition
  related_proposition_id = specific prior proposition being revised
```

The relation means only that the current evidence presents the new proposition
as correcting, replacing, or superseding the prior proposition.

It does **not** imply:

- that the new proposition is world truth;
- that any agent received it;
- that receipt caused comprehension;
- that receipt caused acceptance or rejection;
- that a previous belief automatically flips to the new proposition.

The semantic proposer may create this relation only when the current evidence
explicitly indicates correction/replacement and the referenced prior
proposition already exists in the bounded known-proposition catalog.

## Deterministic projection rule

When all of the following are present:

1. agent A has a prior supported BELIEF_ESTIMATE toward proposition P_old;
2. P_new is explicitly represented as revising P_old;
3. A is later exposed to P_new;
4. there is no later evidence-supported BELIEF_ESTIMATE for A toward P_old or
   P_new after that exposure;

then the prior belief estimate remains historical evidence but is marked in the
query projection as:

```text
projection_status = STALE_AFTER_REVISION_EXPOSURE
```

and the query context emits:

```text
REVISION_STANCE_UNRESOLVED
```

This is deliberately conservative. It does not infer acceptance, rejection, or
continued commitment.

A later explicit stance resolves the projection-level uncertainty.

## Correctness requirements

The amendment must preserve:

- source assertion != world fact;
- exposure != belief;
- correction receipt != correction acceptance;
- historical views before the correction;
- perspective filtering;
- evidence provenance;
- invalidation and rebuild;
- existing v0.4 minimal-slice contracts.

A revision relation must fail closed if the related proposition does not exist.

## Validation boundary

This round uses deterministic mechanism tests only. The existing
`HCL v0.4 Minimal Slice` workflow must pass on the PR head before merge.

It does **not** authorize:

- tuning or rerunning consumed six-case diagnostics as fresh evidence;
- a new provider-backed synthetic capability comparison;
- external benchmark rows;
- owner-private examples;
- cross-model paid runs;
- training/adapters;
- leaderboard submission.

After deterministic correctness passes, the next research contract should test
whether persistent HCL provides value under long-horizon, bounded-context,
multi-party cognition against a strong ordinary memory/retrieval baseline with
a fair shared context budget.
