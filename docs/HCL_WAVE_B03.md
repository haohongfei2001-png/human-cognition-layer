# B03 — Character revision versus analyst revision

## CAPABILITY_DELTA

Ordinary dialogue now yields two observably different updates. An explicit
`I now believe q instead of p` can supersede that speaker's earlier supported
self-report. A later correction to the same source record instead changes the
analyst's current interpretation of the past; the earlier known-at snapshot
remains byte-identical. Correcting an old affirmation to uncertainty removes the
anchor for the reported supersession, while preserving the new self-report and
unrelated Noor's state. This is conditional interpretation of self-reports, not
proof of a private psychological change.

## Mechanism and reuse

`RevisionTimeline` holds immutable record versions within one declared source-local
identity domain. Source event time, system record time and observer access time
are separate. A snapshot selects the latest known version before applying event
and access boundaries. It never resurrects an obsolete record when a correction
moves the event outside the requested time. Unknown event times remain explicit
and do not enter temporal belief projection.

A02 binds ordinary quoted speech to shared source evidence. B01 distinguishes
belief from nested attribution, exposure and knowledge claims. Source-anchored
conditional operation claims and estimates enter A01's dependency graph. The
retained v0.6 projector performs belief/challenge/acceptance/rejection transitions;
the adapter groups simultaneous events together, so disclosure order cannot
manufacture a psychological ordering. Original disclosure times remain in receipts.
No retained runtime or frozen paid package is changed.

Explicit challenge receipt preserves the challenge without inferring acceptance.
`I accept that p` and `I reject that p` are distinct reported responses. Supersession
requires an earlier same-actor affirmed anchor; other actors, hidden records,
uncertain anchors and simultaneous evidence do not qualify. Final input contains
the selected original text, versions, conditional estimates, source-correction
audit and actual dependency receipt. Context overflow fails without silently
dropping counterevidence.

## Verification

- Fourteen targeted unit/negative/composition/ordinary-input checks cover both
  revision types, late disclosure, record correction, same-time conflict, actor and
  source boundaries, unknown event time, later access and evidence budgets.
- `scripts/witness_revision_time.py` produces the positive authored replay and
  actual final messages in `reports/HCL_WAVE_B03_WITNESS.json`.
- Full v1 suite and 176 frozen historical regressions; exact PR-head and merged
  main certification through `HCL v1 Provider-Free Integration`. The artifact
  records actual SHA, runtime digest, test counts and the regenerated witness.

## State and limits

**CORRECTNESS_VERIFIED / REPLAY_VERIFIED / UNTESTED / OPT_IN**. Zero provider
calls/spend; LongMemEval sealed and untouched. No independent efficacy claim.
Explicit bounded English self-report forms, exact proposition strings and supplied
source metadata; no arbitrary temporal phrase grounding, automatic identity
linking, sincerity inference or general belief-revision solver. At most 16 source
records/128 versions; unsupported forms remain diagnostics, not inferred states.
The snapshot rebuilds selected evidence; it does not yet claim incremental compute
savings. B04 next handles correlated reports and bounded higher-order conflict.
