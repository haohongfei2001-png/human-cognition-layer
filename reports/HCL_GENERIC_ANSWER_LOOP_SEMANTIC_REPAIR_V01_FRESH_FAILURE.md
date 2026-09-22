# HCL Generic Answer-Loop Semantic Faithfulness Repair v0.1 — Fresh Validation Failure

## Decision

**FRESH VALIDATION FAILED — 11 / 12**

The generic answer-loop semantic-faithfulness repair improved the tested class
substantially but did not satisfy the predeclared strict fresh-suite gate.

## Canonical run

- workflow: `HCL Generic Answer-Loop Semantic Repair v0.1`
- run: `35718513459`
- launch commit: `1c3b72a3c22cb75ef29dc62b980e34fe0707ca2b`
- terminal workflow conclusion: **FAILURE**
- preflight: **SUCCESS**
- fresh validation runner: **SUCCESS**
- strict fresh gate: **FAIL**
- broader regressions: **SKIPPED by gate**
- artifact: `10690414547`
- artifact digest:
  `sha256:03c5eec60aee0fac9494123d20f6c6d4f3eae1e7e39a9ac20e0916334b6e0ea5`

## Fresh-suite result

Across 12 frozen fresh synthetic cases:

- completed: **12 / 12**
- runtime exceptions: **0**
- semantic correct: **11 / 12**
- parser valid: **12 / 12**
- exact format: **12 / 12**

By direction:

- DIRECT_POSITIVE: **4 / 5 semantic correct**
- DIRECT_NEGATIVE: **5 / 5 semantic correct**
- EXPLICIT_TRANSFER: **2 / 2 semantic correct**

The sole failure was:

`sf07_exact_positive_signal`

Observed content-free result:
- direction: DIRECT_POSITIVE
- format: A/B
- gold: A
- parsed: B
- parser_valid: true
- exact_format: true
- semantic_correct: false
- state mode: EPISTEMIC
- uncertainty: medium
- first checker: PASS
- final checker: PASS
- no revision performed

## Interpretation boundary

The failure is not a parser or exact-output-format failure.

The semantic answer was wrong while both checker passes accepted it.

The current artifact does not persist enough state-level semantic evidence to
determine whether the first inversion was in:
- the state;
- the draft;
- checker control.

Therefore no additional prompt change is authorized from this result alone.

## No rerun-until-pass

The failed fresh run remains canonical evidence. It must not be rerun as fresh
evidence under the same frozen repair.

The next authorized work is a bounded causal diagnosis of the sole new failure
with matched fresh positive controls, while keeping HCL behavior frozen.

## External-evidence boundary

No external benchmark evidence was used or is authorized.

## Claim boundary

Supported:
- the generic repair passes 11/12 fresh semantic cases;
- parser and exact-output compliance are 12/12;
- one direct-positive semantic failure remains.

Not supported:
- repair closure;
- broader regression pass;
- external benchmark efficacy.
