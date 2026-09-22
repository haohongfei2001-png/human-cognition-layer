# HCL State-JSON Repair v0.2 — Regression Failure Record

## Canonical regression run

- run: `35710695556`
- launch commit: `658ad0d25ec0662cb55ec13e649c8455e0bfd61c`
- terminal result: **FAILURE**

Passed:
- preflight / frozen repair checks;
- production-path state fidelity;
- answer-checker regression.

Failed:
- information-state/output-interface regression;
- aggregate regression gate.

## Sole observed interface failure

Fixture:
`io01_full_binary_direct_access`

Original independent audit:
- parser_valid: true
- semantic_correct: true
- exact_format: true
- state mode: EPISTEMIC
- uncertainty: medium
- first checker: REVISE
- final checker: REVISE
- second revision performed: true

v0.2 regression:
- parser_valid: false
- semantic_correct by parser: false
- exact_format: false
- response_chars: 48
- state mode: EPISTEMIC
- uncertainty: medium
- first checker: REVISE
- final checker: PASS
- second revision performed: false

All other 15 interface fixtures passed parser+semantic gates.

## Interpretation boundary

This run is a real regression-gate failure and remains historical evidence.

It is not yet sufficient to distinguish:
- a stable v0.2 behavior regression;
- stochastic provider/checker/revision output instability.

No HCL behavior change is authorized from this single failure.

The next authorized work is the bounded, predeclared investigation in:
`reports/HCL_STATE_JSON_REPAIR_V02_INTERFACE_INVESTIGATION_V01.md`.

No rerun-until-pass and no external benchmark evidence are permitted.
