# HCL v0.5 Seeded State Capability v0.1 — Closure

Verdict: **COMPLETE / STRONG POSITIVE SIGNAL / PRE-REGISTERED INCREMENTAL-UTILITY THRESHOLD NOT MET**

This is controlled internal evidence. It is not an external benchmark,
cross-model transfer result, real-user result, production result, publication
claim, or leaderboard evidence.

## Frozen execution

- Trigger/main commit: `e835d975abced2670a5162bfd791c16d4bcc9e9b`
- Candidate anchor: `7222c33ace692b414556339a03ba40a35e8cdfff`
- Workflow run: `36008684122` — SUCCESS
- Job: `107663416271`
- Artifact: `10812927658`
- Artifact ZIP digest:
  `sha256:fe0974c1d7fa0b706dc13ace503dd2c157ae8cfca41d564f1b55925627e59614`
- Result JSON SHA-256:
  `e8890e3154eff54eff720c0db7edf852af0b5dd6667d72a4550a17c200ddb322`
- Model: `deepseek-flash`; seed: 42
- Fixture SHA-256:
  `5879f487f3b5b92079c091733074600233e3de0da3ae87a01061f09badd2d2ef`
- Gold SHA-256:
  `e4813c41b5863799c0e3f9d4954a6338a35cbd986fadf879c6651dd619f6fed8`
- Shape: 3 streams / 216 events / 24 scored queries
- D/E query-time context budget: 8000 characters
- E memory cap: 6000 characters

All one-shot, candidate-drift, digest, provider-free fairness and evidence
artifact gates passed. Manual gold/timeline audit also found no frozen label
error.

## Primary result

| Arm | Correct | Accuracy | Provider calls | Input chars | Output chars | Provider wall time | Max query context | Max persistent state |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| C full-history diagnostic | 22/24 | 91.7% | 24 | 371,924 | 408 | 22.48 s | 21,700 | n/a |
| D routed v0.5 HCL | **24/24** | **100%** | 216 | 572,646 | 26,993 | 194.61 s | **844** | 4,351 chars |
| E strong ordinary memory | 23/24 | 95.8% | 240 | 738,976 | 264,182 | 1515.37 s | 7,993 | 3,142 chars |

D had:
- **0 semantic repairs**;
- **0 semantic errors**;
- no query-time answer-model calls;
- deterministic `CurrentStance -> label` answers.

Relative to E in this implementation, D used:
- about **22.5% fewer input characters**;
- about **89.8% fewer output characters**;
- about **87.2% less provider wall time**;
- 216 rather than 240 provider calls.

These are practical efficiency signals, but the frozen contract makes
correctness primary.

## Pre-registered interpretation

The contract required D to exceed E by at least **2 / 24** correct queries for a
positive incremental-utility signal.

Observed difference:
- D: 24/24
- E: 23/24
- difference: **+1**

Therefore the formal verdict is:

> **Incremental utility is not yet established under the pre-registered
> threshold.**

The threshold is not relaxed post hoc merely because D achieved 24/24.

At the same time, this result is materially different from the consumed v0.4
long-horizon result where D scored 14/18 and E 17/18. The routed semantic
interface + issue-centered deterministic stance state eliminated the observed
v0.4 failure classes on this fresh package.

## Failure structure

D:
- no scored failures;
- no semantic repair;
- no semantic extraction error.

E:
- one failure: `c2-q8`, historical replay;
- predicted DAILY, frozen gold WEEKLY.

The E artifact shows why this is informative but insufficient as a standalone
win: its final free-form memory had heavily rewritten the backup-cadence
history, while retrieval still supplied several relevant old/new events. The
answer model selected the wrong historical stance.

C:
- `c3-q5` unseen-world-change: predicted USD, gold EUR;
- `c3-q6` revision-pending: predicted USD, gold UNCERTAIN.

D handled both correctly through deterministic perspective/state projection.

## Research interpretation

The current evidence supports four bounded statements:

1. **The v0.5 architecture fixed the concrete v0.4 state-convergence defects on
   this fresh package.**
2. **D is at least competitive with a strong free-form persistent-memory
   baseline on this slice and achieved perfect semantic correctness.**
3. **D has a large implementation-level efficiency advantage on this run.**
4. **A unique HCL capability advantage is still not established**, because the
   primary D-vs-E correctness gap was only one query and E was already near the
   ceiling.

The correct next question is no longer "fix another v0.5 bug." It is:

> Does routed deterministic HCL still add value when compared against a stronger
> non-HCL structured-memory baseline on a harder fresh multi-agent/multi-issue
> package?

## Next gate

One final internal replication should add a strong generic structured-memory
baseline rather than merely making the same free-form comparison larger.

If HCL shows a clear advantage there, internal synthetic iteration should stop
and the project should move to external benchmark / cross-model transfer.

If generic structured memory matches HCL, the unique value of the specialized
HCL state machine remains unproven and should be reconsidered.

## Consumption boundary

This 216-event / 24-query package is consumed.

- Do not rerun it as fresh evidence.
- Do not tune against `c2-q8` and reuse this package.
- Abstract capability classes such as historical replay may appear in a fresh
  independent package.
- Any next provider-backed comparison requires fresh events, queries and gold.

No owner-private example, external benchmark, training, publication or
leaderboard action is authorized by this closure.
