# HCL v0.5 Strong-Baseline Replication v0.1 — Closure

Verdict: **COMPLETE / ROUTE B PASS / ROUTE A NOT ESTABLISHED / INTERNAL SYNTHETIC LOOP CLOSED**

This is controlled internal evidence. It is not an external benchmark,
cross-model transfer result, real-user result, publication claim, or leaderboard
evidence.

## Frozen execution

- Trigger/main commit:
  `a32b50d3c01ad0e7a9165a1a61ab0b6e2546e70a`
- Workflow run:
  `36024803238` — SUCCESS
- Job:
  `107718494395`
- Artifact:
  `10824356781`
- Artifact ZIP digest:
  `sha256:c0ccfa937336484461e3914275506b151df40e5583217d6cd12c9e05f3bbd193`
- Result JSON SHA-256:
  `1860b6b2fb6712187ce2d51481e4d0b3ff29848904a01dbd69dbb56843ada316`
- Model:
  `deepseek-flash`
- Seed:
  `42`
- Fixture SHA-256:
  `478c9e8dbd4255ba418e743faa9627db71807a390b61d105fb33e22270ea9faa`
- Gold SHA-256:
  `7900e7cb5c49def7e4f9800c1e1188211115f0fcd3fde73bab43c09c5ee17eff`
- Shape:
  4 streams / 384 events / 48 scored queries
- E/G persistent-state cap:
  6000 characters
- E query-time context cap:
  8000 characters

All one-shot, digest, candidate-drift, provider-free, artifact-completeness
and manual frozen-gold gates passed before or during the single provider run.

The package is consumed.

## Primary result

| Arm | Correct | Accuracy | Provider calls | Input chars | Output chars | Provider wall time |
|---|---:|---:|---:|---:|---:|---:|
| D routed deterministic HCL | **48 / 48** | **100.0%** | 384 | 1,049,475 | 53,129 | 312.75 s |
| G generic structured state | 36 / 48 | 75.0% | 515 | 4,837,973 | 3,283,723 | 2902.85 s |
| E strong free-form memory | 38 / 48 | 79.2% | 432 | 1,383,163 | 449,276 | 2575.03 s |
| C full-history diagnostic | 34 / 48 | 70.8% | 48 | 924,839 | 970 | 38.67 s |

Per-stream correctness:

| Stream | D | G | E | C |
|---|---:|---:|---:|---:|
| r1 | 12/12 | 8/12 | 10/12 | 9/12 |
| r2 | 12/12 | 7/12 | 9/12 | 9/12 |
| r3 | 12/12 | 9/12 | 9/12 | 8/12 |
| r4 | 12/12 | 12/12 | 10/12 | 8/12 |

Paired D-vs-G:
- D-only correct queries: 12;
- G-only correct queries: 0;
- net D minus G: +12.

D:
- semantic repairs: **0**;
- semantic extraction errors: **0**;
- max query projection: **758 chars**.

## Critical G-baseline integrity finding

The raw score difference cannot be interpreted as a clean specialized-HCL
capability win.

G was constrained to the frozen 6000-character state limit and used one bounded
model repair when its candidate state was invalid or over budget. The artifact
shows:

- **54 distinct event updates ultimately failed after repair**;
- failures occurred in r1/r2/r3, not r4;
- failure mode was overwhelmingly:
  `GenericStateError: generic state invalid after bounded repair:
  generic state exceeds limit ... > 6000`;
- r4 had no such accumulated failure class and G scored 12/12 there.

Because the implementation preserved the previous valid G state when an update
failed, later evidence could be lost. Several G scored failures therefore occur
after substantial accumulated update failures.

This violates Route A condition 4:

> G must not be weakened by truncation/schema errors that an ordinary competent
> implementation could avoid.

A more competent generic-state implementation could use deterministic
compaction/budgeting rather than relying on one model repair and dropping the
event when the repaired JSON remains slightly over the limit.

Therefore:

> **Route A capability advantage is NOT established by this run.**

The observed 48/48 vs 36/48 raw score is real for the frozen implementations,
but it must not be restated as proof that specialized HCL reasoning capability
is superior to a competent generic structured-memory system.

No rerun of this consumed package is permitted to repair G and reclaim a fresh
comparison.

## Route B — practical efficiency advantage

The pre-registered Route B criteria were:

1. D correctness >= G correctness - 1;
2. no severe HCL perspective/stance failure;
3. D provider character volume <= 60% of G;
4. D provider wall time <= 60% of G;
5. D state/query representation mechanically valid and auditable.

Observed:

1. **PASS** — D 48/48 vs G 36/48.
2. **PASS** — D had 0 scored errors, 0 semantic repairs and 0 semantic errors.
3. **PASS** — D total provider chars:
   1,102,604;
   G total provider chars:
   8,121,696;
   D/G = **13.58%**.
4. **PASS** — D provider wall:
   312.75 s;
   G provider wall:
   2902.85 s;
   D/G = **10.77%**.
5. **PASS** — D's deterministic current-state projection remained valid and
   auditable across all 48 rows.

Therefore:

> **Route B PASS: current HCL v0.5 establishes controlled internal practical
> module utility on this slice.**

The defensible claim is not "HCL makes the base model smarter." It is:

> The current routed deterministic HCL maintained the tested multi-agent,
> multi-issue stance state with perfect correctness and substantially lower
> provider-state-management cost than the frozen generic structured-state
> implementation.

The magnitude of the D-vs-G efficiency gap should still be interpreted
cautiously because G's repeated repair/failure loop inflated G's provider cost.
Route B passes the frozen contract, but external validation should use a
competently budgeted generic baseline.

## Secondary evidence

E free-form memory:
- 38/48;
- failures concentrated in pending/undecided states:
  - revision_pending: 4;
  - second_issue_pending: 4;
  - parallel_issue_pending: 2;
- no memory repair events were required.

C full-history diagnostic:
- 34/48;
- failed all 12 current pending-state questions across the three pending
  classes, plus two historical replay rows.

This is consistent with the intended capability distinction: raw access to
history does not itself guarantee correct perspective/current-stance
projection.

## Interpretation across v0.4 -> v0.5

The internal evidence trajectory is now:

1. v0.4 long-horizon:
   HCL D 14/18 vs ordinary memory E 17/18 — negative evidence.
2. v0.5 seeded-state fresh pilot:
   D 24/24 vs E 23/24 — strong positive signal but below the pre-registered
   +2 correctness threshold.
3. v0.5 final strong-baseline replication:
   D 48/48, G 36/48, E 38/48, C 34/48;
   Route A not established because G suffered avoidable budget-update failures;
   Route B practical module utility passes.

The important result is not the raw 48/48 alone. The architectural redesign
from append-mostly assertion projection toward routed event-local semantics plus
deterministic issue-centered current stance eliminated every observed HCL
scored failure on two consecutive fresh capability packages (24 + 48 queries).

That is sufficient to stop tuning against internal synthetic packages.

## Stop rule / next phase

The frozen contract states that if Route A or Route B passes:

- stop internal synthetic tuning;
- proceed to external benchmark selection and cross-base-model transfer.

Route B passes.

Therefore:

- **Do not create another near-identical internal synthetic package.**
- **Do not patch G and rerun these 48 rows as fresh evidence.**
- **Do not tune HCL against any observed failure in this consumed package.**
- Next work is external benchmark selection plus cross-base-model transfer.
- Any external comparison against generic structured memory should use a
  competent deterministic state-budget/compaction mechanism so the baseline is
  not weakened by the failure mode observed here.

No owner-private example, publication, leaderboard submission, training, or
external claim is authorized by this closure.
