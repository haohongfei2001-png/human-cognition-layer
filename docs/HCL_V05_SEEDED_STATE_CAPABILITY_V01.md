# HCL v0.5 Seeded State Capability Pilot v0.1

Status: **FROZEN / PROVIDER RUN NOT STARTED**

## Research question

Can the routed v0.5 HCL maintain a person's current or historical stance over a
long noisy event stream more accurately than a strong ordinary persistent-memory
baseline when both systems receive the same pre-registered issue/value ontology?

This is a controlled internal state-tracking test. It is not an external
benchmark or general HCL claim.

## Why this differs from v0.4

The consumed v0.4 long-horizon v0.2 comparison was confounded by two defects
that have since been changed:

1. v0.4 exposed an append-mostly assertion bag to an answer model rather than a
   deterministic current-stance projection;
2. the semantic interface mixed revision recognition with exposure-subject
   inference.

v0.5 now uses:
- routed semantic extraction;
- deterministic recipient/observer exposure routing;
- issue-centered current stance;
- deterministic state-to-label output for D.

The ordinary-memory baseline remains deliberately strong.

## Frozen package

- 3 streams;
- 72 events per stream;
- 216 events total;
- 8 scored queries per stream;
- 24 scored queries total;
- 3 seeded issues per stream: one queried issue + two distractor issues;
- D/E query-time context budget: 8000 characters;
- E persistent-memory cap: 6000 characters.

Fresh target domains:
- release channel / target Iris;
- backup cadence / target Jonah;
- invoice currency / target Kei.

Fixture:
- `eval/v05/seeded_state_capability_v01_fixture.json`
- SHA-256:
  `5879f487f3b5b92079c091733074600233e3de0da3ae87a01061f09badd2d2ef`

Gold:
- `eval/v05/seeded_state_capability_v01_gold.json`
- SHA-256:
  `e4813c41b5863799c0e3f9d4954a6338a35cbd986fadf879c6651dd619f6fed8`

Provider-free exact-head evidence:
- v0.5 workflow `36008112636`: SUCCESS;
- v0.5 provider-free suite: **59 / 59**;
- seeded capability validate-only: PASS, **3 streams / 216 events / 24 queries**;
- HCL integration workflow `36008112663`: SUCCESS.

The package is independent of consumed v0.4 long-horizon v0.2 concrete event
texts and target agents.

## Arms

### D — routed v0.5 HCL

- same base model performs event-local routed semantic extraction;
- frozen ontology is supplied through `semantic_catalog_seed`;
- deterministic stance state machine updates persistent state;
- query answer is a deterministic projection:
  - AFFIRMED(value) -> value;
  - UNRESOLVED / CONFLICT / NO_AFFIRMED_VALUE -> UNCERTAIN;
- no query-time answer-model call is used for D.

This is intentional: the pilot measures whether the HCL state itself is correct
and avoids reintroducing the v0.4 answer-stage interpretation defect.

### E — strong ordinary persistent memory

- same base model processes every event incrementally;
- receives the identical frozen issue/value ontology;
- may rewrite/compress a free-form memory up to 6000 characters;
- query context may include the memory plus deterministic observable-content
  retrieval up to the shared 8000-character budget;
- same base model answers the query from that bounded context;
- no HCL typed schema or state-transition rules are provided.

Do not deliberately weaken E.

### C — full-history diagnostic

- same base model;
- complete raw history through the query point plus the same ontology;
- diagnostic only, not the primary fairness comparison.

## Capability coverage

The fresh rows cover:

- explicit initial acceptance;
- correction known only to another agent;
- relay accepted;
- relay rejected;
- direct revision pending without stance;
- repeated confirmation of an already accepted revision;
- later explicit acceptance;
- authoritative world update not delivered to the target;
- explicit rejection restoring the prior accepted value;
- final acceptance of a later revision;
- historical replay after subsequent changes;
- long distractor histories containing other seeded issues and agents.

## Metrics

Primary:
- exact semantic correctness of the 24 stance labels.

Also record:
- failures by predeclared risk class;
- D semantic repairs and extraction errors;
- D persistent state size;
- E memory repairs and memory size;
- provider calls and input/output characters;
- provider wall time and total arm wall time;
- query-time context sizes.

Correctness is primary. Lower cost cannot override grounded semantic errors.

## Pre-registered interpretation

This pilot supports only a controlled internal signal.

- **Positive incremental signal:** D is at least 2/24 queries more correct than E,
  with no concentrated severe extraction/recovery failure explaining the gain.
- **No established incremental utility:** D and E differ by at most 1 correct
  query, regardless of cost advantage.
- **Evidence against current v0.5 on this slice:** E is at least 2/24 queries
  more correct than D.
- If both D and E fail a row that C gets right, inspect the bounded persistent
  representations.
- If C also fails, do not patch from that consumed row and rerun it as fresh
  evidence.

Per-row semantic analysis overrides simplistic score storytelling.

## Anti-overfitting boundary

- Fixture contains no gold/risk fields.
- Gold is separate and scoring is post-hoc.
- D and E receive the same frozen ontology.
- E is not given HCL internal types.
- All scored rows are consumed after the first provider execution.
- Do not tune against observed rows and reuse this package as fresh evidence.
- No external benchmark, owner-private example, cross-model run, training,
  publication claim, or leaderboard action is authorized by this pilot.

**Gate: HCL_V05_SEEDED_STATE_CAPABILITY_V01_FROZEN_PREFLIGHT_PASS_PROVIDER_NOT_STARTED**
