# HCL v0.5 LongMemEval ingest compatibility diagnostic v0.1 closure

Status: **COMPATIBILITY PASS / DEVELOPMENT ROWS CONSUMED / NO EFFICACY CLAIM**

## Immutable evidence

- Frozen contract: `docs/HCL_V05_LONGMEMEVAL_INGEST_DIAGNOSTIC_V01.md`
- Frozen candidate: `6f464408757e34b2ce7b4269a5919c606664d0c7`
- One-shot trigger and run head: `52b8a7502a3b0ea42f08e159e503487ab7a6fe4f`
- Workflow run: [36098161768](https://github.com/haohongfei2001-png/human-cognition-layer/actions/runs/36098161768), attempt 1, SUCCESS
- Job: `107954738243`, SUCCESS
- Unique artifact: `10848441320`
- Artifact ZIP SHA-256: `07cf92c76619ab542e56e42883e0e669508e62fc8a348047cb1bb17df6b6e542`
- `result.json` SHA-256: `1aafe1186fcc1df2b566d37ef2a562576006f3d76c1b590646e3effd0591e9f6`
- Pinned cleaned-S SHA-256: `d6f21ea9d60a0d56f34a05b609c79c88a451d2ae03597821ea3d5a9678c3a442`
- Provider: `deepseek-flash`, `deepseek_flash` profile, temperature 0, seed 42.

The one-shot trigger, frozen candidate, provider-free preflight, dataset digest, redacted artifact verification, and artifact upload steps all succeeded. The artifact digest was independently checked after download.

## Observed result

| Measure | `c7dc5443` | `cc5ded98` | Aggregate |
| --- | ---: | ---: | ---: |
| Sessions | 46 | 53 | 99 |
| Attempted events | 478 | 493 | 971 |
| Successful event ingests | 478 | 493 | 971 |
| Semantic failures | 0 | 0 | 0 (0%) |
| Semantic repairs | 0 | 0 | 0 (0%) |
| Stance events committed | 8 | 2 | 10 |
| Current stance records | 5 | 2 | 7 |
| Current state chars | 2,453 | 943 | 3,396 |
| Ingest wall seconds | 388.11 | 385.01 | 773.12 |

Provider account: 971 JSON calls, 3,631,004 input chars, 46,039 output chars, and 772.74 provider wall seconds. The two row wall times sum to 773.12 seconds because they include local work. These values are diagnostic costs, not efficacy outcomes. No token totals or monetary charges were present in the redacted artifact, so neither is estimated here.

## Pre-registered gate decision

The frozen gate requires both rows complete, aggregate semantic failure rate at most 1%, aggregate semantic repair rate at most 5%, and at least one committed stance event. All four conditions passed on the immutable result. **External ingest compatibility PASS.**

This verifies that the current extractor and runtime completed these two realistic histories within the frozen error and repair limits. It does not establish that the 10 extracted stance events are exhaustive or semantically correct. One current stance is marked `CONFLICT`; without task questions or gold this is not classified as a benchmark error. The sparse 10/971 stance yield is a reason to retain an explicit coverage and answer-quality gate in the efficacy protocol, not to change v0.5 against these rows.

The result used only timestamp/session, role, and raw turn content for state construction. It generated no task answer or score. The two development IDs are now provider-backed consumed and must not be reused as fresh evidence. The sealed 32-row efficacy selection remains unconsumed.

## Next gate

Freeze a paired C/D/G LongMemEval efficacy contract with equal external evidence and a competent generic structured-memory comparator. Pin the official judge implementation and model, preserve raw paired answers, and complete provider-free certification. Resolve the second independent model-family credential/profile prerequisite before the first sealed provider run, as required by the frozen diagnostic contract. No efficacy run is authorized by this closure alone.
