# HCL v0.4 C/D/E Capability Comparison v0.2 — Plan

Status: **FROZEN INDEPENDENT INTERNAL VALIDATION**

This is a disjoint internal validation after v0.1.

v0.1 is consumed development evidence and is not reused.

## Purpose

Test whether the v0.4 cognition layer creates practical value when:

- histories are longer;
- multiple agents hold asymmetric information;
- queries recur over time;
- irrelevant events are interleaved;
- corrections may be hidden, relayed, rejected or explicitly accepted.

The objective is not to make D win.

If ordinary memory E remains equally correct and cheaper, record that result.

## Arms

### C — full-history cognition reconstruction

At each query point:
- rebuild v0.4 cognition from raw history from the beginning;
- use the same semantic/update rules as D;
- answer from the reconstructed QueryContext.

### D — dynamic persistent v0.4

- ingest each event once;
- retain derived state across queries;
- answer from the current QueryContext.

### E — ordinary full-history memory

- no structured cognition state;
- give the same base model the complete raw event history available at the query;
- use the same perspective reasoning instruction and exact-label interface.

## Shared answer interface

All arms use:
- the same base model;
- JSON exact-label output;
- the same perspective semantics;
- no HCL answer checker;
- no Decision Policy;
- no Action Checker.

For C/D:

> a supported BELIEF_ESTIMATE remains the current best estimate until later
> evidence supports revision; source assertion or exposure alone does not
> supersede it.

## Frozen data

Six new scenarios.

Each contains:
- eight events;
- three query points;
- multiple agents;
- irrelevant/distractor events;
- explicit evidence boundaries.

Total:
- 48 events across scenarios;
- 18 query points.

Domains are disjoint from v0.1 examples at the surface level and use new event
structures.

## Gold policy

Gold labels are based only on:
- explicit prior belief statements;
- explicit acceptance;
- explicit rejection;
- direct target observation;
- explicit undecided state.

No gold requires guessing a hidden belief after ambiguous evidence.

## Metrics

- exact-label accuracy;
- per-arm failure list;
- C/D normalized-state equality;
- total model calls;
- input/output character volume;
- semantic-repair count.

Interpretation:

- D > C/E: candidate incremental capability signal;
- D = C with lower maintenance cost: persistence engineering value;
- D = E with materially higher cost: no incremental utility signal for this
  slice;
- E > D: structured cognition is currently hurting;
- all arms near ceiling: this slice is too easy to establish incremental value.

No single internal result establishes external efficacy.

## Exposure

These scenarios are repository-owned and internal.

They are independent of v0.1 but are not external benchmark evidence.

No previously consumed CogToM, SOTOPIA, FANToM or Hi-ToM row is used.

## Gate

Run once under the frozen protocol.

**Gate: HCL_V04_CDE_V02_FROZEN_READY_TO_RUN**
