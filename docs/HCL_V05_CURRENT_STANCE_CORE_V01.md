# HCL v0.5 Issue-Centered Current Stance Core v0.1

Status: **PROVIDER-FREE MECHANISM CANDIDATE**

## Motivation

The frozen HCL v0.4 long-horizon v0.2 result established no incremental utility:
persistent D scored 14/18 while strong ordinary-memory E scored 17/18 under the
same bounded query-time context. The preserved D evidence localized the largest
failure class to current-state convergence rather than raw information loss.

v0.5 therefore starts from a narrower architecture claim:

> Historical cognition evidence may remain append-only, but the query-facing
> current stance must be a deterministic issue-centered state projection rather
> than an unfiltered assertion bag.

This package does not rerun consumed v0.2 evidence and does not claim capability
improvement.

## Core representation

A stance event is keyed by:

- subject agent;
- issue key;
- value key;
- valid time;
- system-record time;
- one signal: AFFIRM, DENY, REVISION_EXPOSURE, or UNRESOLVED.

A current stance contains:

- status: AFFIRMED / UNRESOLVED / NO_AFFIRMED_VALUE / CONFLICT;
- one affirmed value when supported;
- explicitly rejected values;
- pending revision value;
- suspended prior value while a newly received revision is unresolved;
- provenance and transition event IDs.

## Frozen transition invariants

1. **Later explicit stance closes older uncertainty.**
   AFFIRM(value) produces a current affirmative stance and clears a pending
   revision.

2. **Receipt is not acceptance.**
   A revision exposure to a genuinely different candidate suspends the prior
   affirmative stance and yields UNRESOLVED until later stance evidence.

3. **Repeated confirmation is not a new uncertainty event.**
   If the agent already AFFIRMS the revision's new value, another exposure to
   that same revision leaves the stance affirmed.

4. **Explicit rejection can restore the suspended prior stance.**
   If a pending revision is denied and no alternative is affirmed in that
   transition, the previously suspended value becomes current again.

5. **AFFIRM(old) + DENY(new) at the same semantic time is unambiguous.**
   Current stance is old; new remains explicitly rejected.

6. **Unexposed world revision cannot update the target agent.**
   State transitions are agent-scoped; a revision event for another subject
   does not affect the target.

7. **History is replayable.**
   event_time / knowledge_cutoff filters are applied before state projection.

8. **Conflicting simultaneous affirmative values fail closed.**
   The result is CONFLICT rather than choosing one.

## Architectural boundary

This v0.1 core is intentionally independent from LLM extraction. It proves only
the deterministic update semantics.

The next integration stage may map semantic evidence into stance events, but it
must not use string heuristics to guess issue equivalence. Issue/value identity
must be explicit semantic data with provenance.

No provider-backed capability run, external benchmark, owner-private example,
training, cross-model comparison, publication claim, or leaderboard action is
authorized by this package.

**Gate: HCL_V05_CURRENT_STANCE_CORE_V01_PROVIDER_FREE_IMPLEMENTATION**
