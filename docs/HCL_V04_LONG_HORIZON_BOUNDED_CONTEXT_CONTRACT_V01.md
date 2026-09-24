# HCL v0.4 Long-Horizon Bounded-Context Capability Contract v0.1

Status: **FROZEN / NOT RUN**

## Research question

Does persistent structured HCL provide incremental downstream capability over a
strong ordinary persistent-memory baseline when long multi-party history cannot
simply be reread in full and both systems receive the same bounded query-time
context budget?

This is a utility test, not a test of whether HCL can store structured state.

## Primary comparison

Use the same base model and deterministic decoding settings.

### D — persistent HCL

- canonical v0.4 runtime;
- events arrive in chronological stream order;
- HCL may maintain its typed persistent cognition state;
- query-time model input contains only the bounded HCL projection plus permitted
  supporting evidence;
- no full-history replay at answer time.

### E — strong ordinary persistent memory

- no HCL semantic types or HCL-specific rules;
- same chronological event stream;
- one bounded free-form memory record maintained incrementally by the same base
  model;
- the memory updater may rewrite, compress, retain uncertainty, and keep facts it
  considers useful;
- query-time model input contains only that bounded memory plus the same class of
  permitted supporting evidence;
- no full-history replay at answer time.

D and E receive equal query-time context budgets. Their update cost is measured,
not hidden.

### C — full-history diagnostic oracle

The same base model receives the complete raw history when it fits the declared
provider context window.

C is diagnostic only. It is **not** part of the primary fairness verdict because
it is intentionally not bounded like D/E. It helps distinguish a memory failure
from a base-model reasoning failure.

## Capability domain

The fixture must require persistent human-state tracking rather than isolated
short puzzles. Each stream should include several of:

- 4–8 agents;
- information visible to only a subset of agents;
- source assertions that are not world truth;
- explicit corrections and proposition revisions;
- receipt without acceptance;
- explicit rejection followed by later acceptance or continued rejection;
- delayed system discovery;
- repeated retellings of one underlying source;
- irrelevant/decoy events;
- temporally separated references to the same issue;
- queries requiring current belief, historical belief, communication choice, or
  safe action.

No owner-private conceptual example may be used.

## Bounded pilot size

First run only:

- 3 independently generated/frozen streams;
- 80 events per stream;
- 6 scored queries per stream;
- 18 scored queries total.

This is intentionally smaller than a benchmark campaign. It is large enough for
history compression to matter while keeping provider cost bounded.

The fixture and scoring key must be frozen before any provider-backed execution.

## Context and memory budget

Before the first provider-backed run, the runner must freeze one shared
query-time budget in tokenizer tokens or, if provider-token accounting is not
reliably available before calls, one shared UTF-8 character budget with the
conversion rationale recorded.

The budget must be low enough that the complete 80-event history does not fit,
but high enough for a competent ordinary memory baseline to retain useful state.

D and E must receive the **same** query-time budget.

The E memory record must also have a fixed maximum size. It must not silently
grow into the full history.

## Update fairness

D and E process the same event sequence.

The ordinary-memory updater is allowed to be strong. Its prompt should ask it to
maintain whatever compact memory would best support future reasoning without
copying HCL's typed schema.

Do not deliberately weaken E.

Record for every arm:

- provider calls;
- input tokens/characters;
- output tokens/characters;
- wall-clock time when available;
- schema/repair failures;
- memory/state size at each scored query.

If D costs materially more, that cost is part of the result.

## Ground truth and scoring

The synthetic environment owns the scoring state. Model outputs never define
gold.

Gold must distinguish:

- world/environment truth;
- what each agent was exposed to;
- explicit acceptance/rejection;
- unresolved stance;
- historical vs current state;
- allowed safe actions where action queries are used.

Primary metrics:

1. exact semantic correctness of the 18 final answers/actions;
2. unsupported-certainty errors;
3. perspective-leak errors;
4. stale-revision errors.

Secondary metrics:

- query-time context size;
- total provider input/output;
- provider call count;
- state/memory size.

No score is allowed to override a grounded semantic failure.

## Pre-registered interpretation

The pilot supports only these conclusions:

### Evidence for incremental HCL utility

D shows a credible signal only if it is more semantically correct than E on the
frozen streams without relying on larger query-time context, and the gain is not
explained by an unfairly weak E implementation.

### No established incremental utility

If D and E are effectively tied while D is materially more expensive, the
persistent structured mechanism has not established incremental utility on this
capability slice.

If E is more correct, that is evidence against the current D design on this
slice and must be reported directly.

### Inconclusive

If both D and E fail where C succeeds, the bounded-memory problem may be too
hard or the memory interfaces may be inadequate.

If C also fails, do not repair D from those scored rows and rerun them as fresh
evidence; diagnose a new independent mechanism question.

## Anti-overfitting rules

- scoring/gold is never included in model prompts;
- the 18 scored queries are frozen before provider use;
- observed scored rows are consumed after the first run;
- no answer-shaped prompt patching;
- no rerun of the same rows as fresh evidence after mechanism changes;
- no external benchmark or leaderboard in this pilot;
- no cross-model run until this single-model pilot has a clear interpretation.

## Frozen implementation material

Provider-free preflight candidate:

- fixture: `eval/v04/long_horizon_bounded_context_v01_fixture.json`
- fixture SHA-256:
  `a79b675cf484292a07916141d54d3022862c39851a3fc4b91c73cb13f1a75cfe`
- scoring key: `eval/v04/long_horizon_bounded_context_v01_gold.json`
- gold SHA-256:
  `376fb695eada3b52f7e8fadd395be479f9cbbf47c944c9d3b0c4a56d5f90c988`
- query-time dynamic-context cap for D and E: **8000 characters**
- ordinary free-form E memory cap: **6000 characters**
- streams / events / scored queries: **3 / 240 / 18**
- provider-free preflight run: `35980000546` — SUCCESS
- provider-free fairness / evidence guards: **8 / 8**
- existing v0.4 + long-horizon preflight integration run:
  `35980000406` — SUCCESS
- existing v0.4 deterministic contract suite remains **35 / 35**
- manual gold/timeline audit before provider execution: PASS; all 18 labels were
  rechecked against the frozen event chronology, including revision receipt
  without stance, explicit rejection/acceptance, private world-fact separation,
  and the historical-time query

These digests are frozen before provider-backed execution. Any change to either
file requires a new digest and invalidates the current execution candidate.

Evidence preservation is also frozen before the first scored run:

- every C/D/E scored row stores the exact dynamic query context presented to the
  answer model;
- every D scored row additionally stores the full derived persistent cognition
  snapshot at that query, so state-formation failure can be separated from
  query-projection failure;
- every E scored row stores the ordinary persistent memory inside its exact query
  context;
- per-row query latency plus per-arm provider wall time, total wall time,
  calls/input/output characters, and D/E persistent-state size are recorded.

The provider execution workflow is one-shot by contract. It requires a fixed
trigger nonce, requires the trigger path to be newly created with no prior path
history, and rejects GitHub Actions rerun attempts before any provider call.

## Execution gate

Provider-backed execution is allowed only after:

1. fixture/gold separation preflight passes;
2. D and E query-time budgets are mechanically equal;
3. ordinary-memory E has a human-auditable strong prompt and is not an HCL clone;
4. runner records per-arm cost;
5. exact fixture digest is recorded.

**Gate: HCL_V04_LONG_HORIZON_BOUNDED_CONTEXT_V01_FINAL_EVIDENCE_CONTRACT_FROZEN_PROVIDER_RUN_NOT_STARTED**
