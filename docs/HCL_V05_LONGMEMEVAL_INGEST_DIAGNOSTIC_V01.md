# HCL v0.5 LongMemEval External Ingest Compatibility Diagnostic v0.1

Status: **FROZEN / PROVIDER RUN NOT STARTED**

## Purpose

Before consuming the sealed 32-row LongMemEval efficacy selection, test whether
canonical HCL v0.5 can reliably ingest realistic external long-history streams.

This diagnostic does **not** answer LongMemEval questions and does not score
task performance.

## Frozen development rows

Source:
- LongMemEval cleaned-S pinned by EQ-02.

Rows:
- `c7dc5443`: 46 sessions / 478 turns
- `cc5ded98`: 53 sessions / 493 turns

Selection was deterministic from the 46 knowledge-update rows outside the sealed
32-row efficacy set, using the independent salt:
`HCL-LONGMEMEVAL-KU-INGEST-DIAG-V01-20260925`.

Selection evidence:
- run `36097682544`: SUCCESS
- artifact `10847493961`
- artifact ZIP digest:
  `sha256:0a48afcc5be425cba558e7a3e821fecfed3d767da0fca4ee4294bca49ab8584f`
- manifest SHA-256:
  `134dd872e25905e5a76fe1bb6fb81ad97892f0e7c2157a3dea1ba6e6f54d6643`

The two rows are development evidence and become consumed when provider-backed
ingestion starts.

They are disjoint from:
- `eval/longmemeval/knowledge_update_selection_v01.json`.

## Evidence firewall

The runner ingests only the EQ-02 state view:
- timestamp/session order;
- role;
- raw turn content.

It never reads task question/answer/evidence labels into HCL state.

No task prediction is generated.

## Mechanism

Every cleaned turn becomes the already-qualified EventRecord shape.

Canonical:
- HCL v0.5 routed extractor;
- no seeded ontology;
- canonical deterministic stance projector;
- DeepSeek continuity provider/profile;
- no semantic prompt or state-machine modification.

Semantic failures are recorded and ingestion continues to measure real failure
rate. Failed event semantics are not repaired outside canonical bounded repair.

## Pre-registered compatibility gate

PASS requires all:
1. both selected rows complete;
2. aggregate semantic failure rate <= 1%;
3. aggregate semantic repair rate <= 5%;
4. at least one stance event is committed.

These are engineering compatibility gates only. PASS does not imply LongMemEval
efficacy.

No requirement is placed on task accuracy because no question is asked.

## Stop rule

If compatibility fails:
- do not consume the sealed 32 efficacy rows;
- do not alter v0.5 from these two rows and then call them fresh;
- diagnose whether the failure is transport/runtime versus a fundamental
  mismatch of explicit-stance semantics to LongMemEval.

If compatibility passes:
- close these two development rows as consumed;
- freeze the C/D/G efficacy protocol for the sealed 32;
- before the first sealed provider run, resolve the second-base-model
  credential/profile gate so cross-model transfer can be predeclared rather
  than appended after seeing DeepSeek outcomes.

**Gate: HCL_V05_LONGMEMEVAL_INGEST_DIAGNOSTIC_V01_FROZEN_PROVIDER_NOT_STARTED**
