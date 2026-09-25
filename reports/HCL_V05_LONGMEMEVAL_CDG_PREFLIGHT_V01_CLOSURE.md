# HCL v0.5 LongMemEval sealed-history digest correction and C/D/G preflight

Status: **PROVIDER-FREE PREFLIGHT PASS / 32 SEALED IDS UNCHANGED / NO EFFICACY ROW CONSUMED**

## Correction evidence

The committed EQ-02 32-row selection contained one malformed 62-character history SHA-256 for `0977f2af`. The immutable EQ-02 qualification evidence already held the complete digest:

- qualification run `36094801638`, artifact `10846604293`;
- downloaded artifact ZIP SHA-256 `d3f9e6545856a9fb0700f412dc7fc9a6f8609460507a0013aae89e93cffe1101`;
- artifact `manifest.json` SHA-256 `80df22912d1a6a82bdd3b820896d58c945072e8be8d407165b09797faef89c7d`;
- canonical `0977f2af` history SHA-256 `f6c0d07d1cd6d6d19405075998ac6f095fd0d90c5f687a0ce8d7ae6905c6b15e`.

The committed value omitted the second `d6` immediately after `1cd6`. All other 31 selected history digests and all 32 selected IDs matched the immutable qualification artifact. The correction changes only that one digest field. Selection order, salt, row IDs, source revision, and dataset hash are unchanged. No provider-backed selected row was run before correction.

## Fresh provider-free verification

- PR candidate head `8c9823faa5c40f78b38ce1572e9116d2ed3231d5`;
- workflow `HCL v0.5 LongMemEval C/D/G Provider-Free Preflight`, run `36100901008`: SUCCESS;
- artifact `10848869835`;
- artifact ZIP SHA-256 `877836e437fb798d2305d2eebe9ab934876359c992e07d9d88c651aff9af3cad`;
- redacted `manifest.json` SHA-256 `4e23b7eb3a3bf5d9fcc53895131f98a216478e1066163212a7810046ab28d17f`;
- v0.5 current-stance CI `36100900959`: SUCCESS;
- v0.4 minimal-slice CI `36100900983`: SUCCESS;
- ingest-diagnostic selection CI `36100900999`: SUCCESS.

The preflight pinned and verified the cleaned-S file SHA-256, checked every selected sanitized history against its corrected immutable digest, enforced the state-input firewall, and emitted only IDs, hashes and counts. It did not read task questions or gold into state construction, call a provider, score an answer, or consume efficacy rows.

Observed package size: **32 rows / 15,601 events / maximum 528 events per row / 2 abstention IDs**. This is a capacity input, not a benchmark outcome.

## Cost and next gate

The prior diagnostic used 3,631,004 input characters and 772.74 provider wall seconds for 971 events. A linear extrapolation to 15,601 D-arm events is approximately **58.34 million input characters** and **3.45 hours provider wall time** for D ingestion alone. This estimate excludes G updates, C/D/G answer calls, judge calls, retries, and any concurrency or state-growth effects. It is not a price quote or spending authorization.

Continue provider-free implementation of the frozen C/D/G contract. Before a sealed provider run, verify second model-family access/profile, official judge access, and an explicit bounded cost plan. No efficacy or cross-model claim follows from this preflight.

**Gate: HCL_V05_LONGMEMEVAL_CDG_V01_SEALED_HASH_CORRECTED_PREFLIGHT_PASS_PROVIDER_FREE_IMPLEMENTATION_NEXT**
