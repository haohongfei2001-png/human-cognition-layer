# HCL v0.4 Long-Horizon Bounded-Context Capability Contract v0.2

Status: **FROZEN FRESH-EVIDENCE CANDIDATE / PROVIDER RUN NOT AUTHORIZED YET**

## Why v0.2 exists

The v0.1 one-shot execution was consumed without a capability verdict because
persistent D hit a general semantic-schema reliability defect before scoring.
That failure is closed separately. v0.1 must not be rerun as fresh evidence.

v0.2 keeps the same research question and fairness design while replacing the
entire scored evidence package with independently written concrete scenarios.

The v0.1 provider outputs, partial execution behavior, and hidden per-row
performance are not used to design v0.2 answer rules. Only the abstract
pre-registered capability domain and the general runtime failure mechanism are
carried forward.

## Research question

Does persistent structured HCL provide incremental downstream capability over a
strong ordinary persistent-memory baseline when long multi-party history cannot
be reread in full and both systems receive the same bounded query-time context
budget?

## Comparison

Primary comparison remains:

- **D — persistent HCL:** canonical v0.4 runtime, persistent typed cognition,
  bounded structured query projection, no full-history replay at answer time.
- **E — strong ordinary persistent memory:** same base model, incrementally
  rewritten free-form memory, deterministic observable-content retrieval, no HCL
  types/rules, no full-history replay at answer time.
- **C — full-history diagnostic oracle:** complete raw history when provider
  context permits; diagnostic only, not part of the primary fairness verdict.

D and E use the same **8000-character query-time dynamic-context cap**.
E uses a **6000-character ordinary-memory cap**.

The same already-audited D/E harness mechanics are reused. v0.2 changes the
fresh evidence package, not the comparison logic.

## Fresh evidence package

- 3 streams;
- 80 events per stream;
- 240 events total;
- 6 scored queries per stream;
- 18 scored queries total.

Concrete v0.2 domains are new:

- briefing-room assignment / target Lin;
- project budget cap / target Maya;
- shipping-dock assignment / target Nora.

The event IDs, query IDs, target agents, primary event texts, concrete values,
and gold labels are separate from v0.1.

Fixture:
- `eval/v04/long_horizon_bounded_context_v02_fixture.json`
- SHA-256:
  `5aad883a58ddfb12c1089381bc1471898eb21cdbe6e143b1d5a5e256d816b110`

Gold:
- `eval/v04/long_horizon_bounded_context_v02_gold.json`
- SHA-256:
  `a50be5387f97cc9de8b6b83868518d5c765b2298348029d8d3939dcca5a348af`

Runner:
- `scripts/run_v04_long_horizon_bounded_context_v02.py`

Provider-free evidence:
- v0.2 preflight run `35984108570`: PASS;
- v0.2 freshness/fairness guards: **6 / 6**;
- combined v0.4 minimal-slice run `35984108490`: SUCCESS;
- manual gold/timeline audit: PASS for all 18 labels before provider use.

## Capability coverage

The fresh package includes:

- direct information and explicit acceptance;
- corrections visible only to other agents;
- relays that are explicitly rejected;
- a relay that is explicitly accepted;
- direct revisions received without an immediate stance;
- explicit rejection after direct correction;
- later explicit acceptance;
- authoritative world-state changes not delivered to the target;
- long irrelevant event spans;
- one historical-state query after the full stream.

Gold distinguishes current belief, unresolved stance, private-world-fact
separation, relay acceptance/rejection, accepted revisions, and historical
state.

## Evidence and leakage discipline

Harness-only `track` / `sequence` metadata may exist in fixture files for
provider-free auditing but is stripped before all model inputs and is not used
by E retrieval.

For every scored query, the artifact must preserve:

- exact model-visible dynamic query context;
- prediction and post-hoc gold/risk class;
- query latency;
- D full derived cognition snapshot and persistent-state size;
- E ordinary memory inside the exact query context and memory size.

Per arm, record calls, input/output characters, provider wall time, total wall
time, and maximum query-context/persistent-state size.

Gold is never included in model prompts.

## Freshness guards

Provider-free preflight must establish before any provider run:

1. v0.2 has 3 / 240 / 18 shape;
2. fixture contains no gold/risk fields;
3. v0.2 event IDs and query IDs are disjoint from v0.1;
4. v0.2 primary event texts are disjoint from v0.1;
5. harness-only annotations are absent from model inputs;
6. D/E context limits are mechanically enforced;
7. provider-free C/D/E paths preserve required diagnostic evidence;
8. scoring remains post-hoc and does not mutate predictions.

## Interpretation

Use the same pre-registered interpretation as v0.1:

- D must be more semantically correct than E under the same bounded query-time
  context to provide a credible incremental-utility signal.
- If D and E are effectively tied while D is materially more expensive, no
  incremental HCL utility is established on this slice.
- If E is more correct, that is evidence against the current D design on this
  slice.
- If D and E fail where C succeeds, the bounded-memory interfaces may be
  inadequate.
- If C also fails, do not repair from scored rows and rerun them as fresh
  evidence.

Correctness remains primary; a numeric score does not override grounded semantic
failure.

## Anti-overfitting and execution boundary

- Freeze fixture/gold digests before provider execution.
- Manually audit all 18 gold labels against the frozen timeline before execution.
- Run the scored package once.
- After first provider exposure, v0.2 is consumed and cannot be rerun as fresh
  evidence.
- No external benchmark, owner-private material, cross-model run, training,
  publication claim, or leaderboard action is authorized by this contract.

**Gate: HCL_V04_LONG_HORIZON_BOUNDED_CONTEXT_V02_FROZEN_PREFLIGHT_AND_GOLD_AUDIT_PASS_PROVIDER_NOT_STARTED**
