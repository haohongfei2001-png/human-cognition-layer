# HCL v0.4 Minimal Slice Correctness Pilot v0.1 — Closure

Status: **COMPLETE / DEVELOPMENT CORRECTNESS GATE ONLY**

This closure records the first provider-backed correctness pilot for the HCL v0.4
minimal cognition slice.

It is **not** an external efficacy result and makes no leaderboard claim.

## Frozen capability plan

- `docs/HCL_V04_CAPABILITY_PLAN_V1_0.md`
- `docs/HCL_V04_MINIMAL_IMPLEMENTATION_CONTRACT_V1_0.md`

## Minimal implementation

Implemented under `hcl/v04/`:

- typed event/evidence records;
- typed cognition assertions;
- explicit belief stance `AFFIRM|DENY`;
- persistent SQLite-backed derived state;
- source/provenance references;
- perspective-safe query views;
- state versioning;
- local invalidation;
- full rebuild fallback;
- bounded semantic schema repair;
- bounded semantic-invariant repair with rejected-patch audit;
- preservation of independently valid assertions during repair;
- final-answer checker bound to the exact returned answer;
- capability-aware provider adapter.

v0.3 remains unchanged as the historical baseline.

## Contract CI

Canonical minimal-slice contract run:

- workflow: `HCL v0.4 Minimal Slice`
- run: **35845149540**
- head: `e03e64edf5408bd379458b5440919426e4e945ce`
- result: **SUCCESS**

The contract suite covers:

- source assertion != scene fact;
- received != believed;
- perspective isolation;
- correction not received;
- explicit rejection;
- historical-state preservation;
- atomic invalid patch rejection;
- dependency invalidation;
- full rebuild;
- deterministic replay;
- bounded semantic repair;
- typed belief stance;
- exact final-answer checking.

These are implementation/correctness boundaries, not broad cognition evidence.

## Provider-backed correctness pilot

Final canonical development run:

- workflow: `HCL v0.4 Correctness Pilot v0.1`
- run: **35845184484**
- head: `bb6583482853c0da849f3fbb5fbe8aaf88fd7001`
- model: `deepseek-flash`
- seed: 42
- cases: **7**
- hard-check failures: **0**
- workflow result: **SUCCESS**
- artifact: **10743530241**
- artifact digest:
  `sha256:aae37f1c73cd92bd324497daff0f0bb085c02402a41c9715f08ead8e68f01d33`

The seven development scenarios cover:

1. neutral source report without acceptance;
2. explicit acceptance;
3. explicit rejection;
4. hidden scene fact outside an agent's perspective;
5. correction received by one agent but not another;
6. later system discovery without historical-agent overwrite;
7. conflicting sources without forced belief collapse.

## Manual artifact review

The final artifact was manually reviewed after the automated hard checks.

Confirmed:

### Neutral report

- source assertion preserved;
- Alice exposure preserved;
- no scene fact invented;
- no Alice belief inferred from exposure alone.

### Explicit acceptance

- Alice exposure present;
- belief represented as
  `BELIEF_ESTIMATE + AFFIRM`;
- belief points to the object-level proposition;
- no source assertion promoted to world truth.

### Explicit rejection

- Alice exposure to "meeting at four" preserved;
- `DENY(meeting at four)` preserved;
- `AFFIRM(meeting at three)` preserved;
- no scene fact invented.

### Correction not received

- Alice's earlier `AFFIRM(meeting at three)` preserved;
- correction event excluded from Alice's perspective;
- system perspective retains the legitimate scene fact that the meeting changed
  to four;
- Bob's correction exposure is retained;
- no Alice exposure to the correction is created.

A bounded semantic-invariant repair was used in this scenario. The rejected
proposal and repair reason remain auditable.

### Later system discovery

- Alice's historical belief remains queryable;
- later archive/world evidence does not leak into Alice's perspective;
- `knowledge_cutoff` uses event/system receipt time rather than CI wall-clock
  time;
- a belief report is no longer misclassified as a goal/intention.

### Conflicting sources

- both source assertions remain;
- both exposures remain;
- no scene fact is invented;
- no unsupported unique belief is forced.

## Important development history

Earlier pilot attempts are preserved and must not be rewritten as success:

- run `35841107352`: import/bootstrap failure before provider execution;
- run `35841214908`: provider output exposed an undeclared support-level value;
- run `35841426397`: one hard failure exposed semantic recovery weaknesses;
- run `35844646910`: stricter typed-belief gate exposed an evaluator false
  negative caused by an over-broad exposure check;
- run `35844890786`: automated checks passed, but manual review found an
  incorrect system-record-time default and a belief-report/goal-intention
  misclassification;
- run `35845184484`: final corrected pilot, automated hard checks + manual
  artifact review both pass.

This history is retained because it demonstrates why a green workflow alone is
not treated as cognitive correctness.

## Claim boundary

This closure establishes only:

> The current v0.4 minimal slice can represent and preserve the tested
> evidence/perspective/time/belief distinctions on a small provider-backed,
> human-auditable development set, while recovering from one bounded semantic
> invariant error without corrupting valid state.

It does **not** establish:

- superiority over full-history reconstruction;
- superiority over ordinary memory;
- broad human cognition validity;
- cross-model transfer;
- external benchmark improvement;
- leaderboard competitiveness.

## Next canonical work

Proceed to a small internal **C/D/E capability comparison**:

- C: full-history reconstruction;
- D: dynamic persistent v0.4 HCL;
- E: ordinary persistent memory.

Primary question:

> Does the dynamic v0.4 state produce any real downstream capability advantage,
> stability advantage, recovery advantage, or cost tradeoff relative to simpler
> alternatives?

No new external benchmark rows are authorized by this closure.

**Gate: HCL_V04_MINIMAL_SLICE_CORRECTNESS_COMPLETE_CAPABILITY_COMPARISON_READY**
