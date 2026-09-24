# HCL v0.5 Seeded Semantic Catalog v0.1

Status: **PROVIDER-FREE EVALUATION FAIRNESS SUPPORT**

## Purpose

Allow a caller to provide a frozen issue/value catalog to the routed semantic
extractor before any stance event has been observed.

This is needed for the next end-to-end comparison so both HCL and the ordinary
memory baseline receive the same pre-registered ontology. The experiment should
test persistent cognition/state tracking, not open-ended ontology induction.

## Semantics

- seed catalog is optional;
- issue keys and values must be non-empty;
- duplicate values fail closed;
- seed is normalized deterministically;
- observed stance values are unioned with the seed;
- existing runtime behavior is unchanged when no seed is supplied;
- the seed does not create any stance, belief, exposure, or evidence by itself.

This milestone is provider-free and contains no capability evidence.

**Gate: HCL_V05_SEEDED_SEMANTIC_CATALOG_V01_PROVIDER_FREE**
