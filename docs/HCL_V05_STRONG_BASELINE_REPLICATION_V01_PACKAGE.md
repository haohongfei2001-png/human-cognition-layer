# HCL v0.5 Strong-Baseline Replication v0.1 — Frozen Package

Status: **FROZEN / PROVIDER RUN NOT STARTED**

Canonical design:
- `docs/HCL_V05_STRONG_BASELINE_REPLICATION_V01.md`

## Fresh package

- 4 streams;
- 96 events per stream;
- 384 events total;
- 12 scored queries per stream;
- 48 scored queries total;
- 8 named agents per stream;
- 4 seeded issues per stream;
- exactly 2 queried target agents per stream;
- exactly 2 queried issues per stream;
- G/E persistent state limit: 6000 characters;
- E query-time context limit: 8000 characters.

Fixture:
- `eval/v05/strong_baseline_replication_v01_fixture.json`

Gold:
- `eval/v05/strong_baseline_replication_v01_gold.json`

The fixture/gold digests are recorded after provider-free validation.

## Compared arms

- D: canonical routed deterministic HCL v0.5;
- G: generic LLM-managed structured JSON state, deterministic readout;
- E: strong free-form persistent memory;
- C: full-history diagnostic.

D vs G is primary.

G receives the same frozen ontology as D/E, but no HCL semantic types,
deterministic exposure router, suspended-state machinery, or HCL transition
algorithm.

## Evidence boundary

No provider-backed row has been consumed.

The provider-free gate must verify:
- fresh concrete event IDs/texts;
- 384/48 shape;
- chronological query execution;
- multi-agent/multi-issue coverage;
- gold separation;
- G generic schema validity and historical readout;
- G prompt contains no HCL-specific mechanism;
- post-hoc scoring;
- exact fixture/gold digests.

**Gate: HCL_V05_STRONG_BASELINE_REPLICATION_V01_PACKAGE_FROZEN_PREFLIGHT_PENDING**
