# HCL Runtime State-Prompt Conformance v0.1 — Synthetic Closure

## Decision

**ADJUDICATED SYNTHETIC PASS**

The frozen runtime behavior passed all substantive synthetic gates after bounded
adjudication of the two raw evaluator failures from canonical regression run
`35721321301`.

The original workflow remains raw **FAILURE** and is preserved unchanged.

## Frozen behavior

Behavior anchor:

`da09c1fc8b82a538f6b0fdbbbe101e58b839241b`

No HCL runtime behavior changed during post-regression adjudication.

## Canonical full regression

Run:
- `35721321301`
- terminal workflow result: **FAILURE**

### Stage 1 — state-generation reliability

- 24 / 24 success
- 0 state_json_exhaustion
- 0 backend/other exceptions
- aggregate gate: PASS

### Stage 2A — fresh semantic-faithfulness answer suite

- 12 / 12 semantic correct
- 12 / 12 parser valid
- exact-output gate: PASS
- runtime exceptions: 0

### Stage 2B — original output-interface audit

- full-loop semantic: 8 / 8
- full-loop parser: 8 / 8
- forced-revision semantic: 8 / 8
- forced-revision parser: 8 / 8
- abstract interface defect: false

### Stage 2C — production-path state fidelity

Raw:
- 11 / 12
- sole raw failed ID:
  `epistemic_private_message`

The sole raw failure was caused by the legacy evaluator requirement that
`missing_bridges` must be non-empty.

### Stage 2D — answer-checker fresh suite

Raw:
- 11 / 12
- sole raw failed ID:
  `fresh11_absence_of_evidence`

The checker correctly returned REVISE and the corrected answer passed final
verification. The raw failure was only the fixture's narrow violation-family
expectation.

## Bounded adjudication

Canonical adjudication:
- workflow: `HCL Runtime Conformance Regression Adjudication v0.1`
- run: `35723696097`
- terminal result: **SUCCESS**
- artifact: `10691499923`
- digest:
  `sha256:ddfd60af8ea360bfed679de82bd96d5bb640525ed41c8d5cb4398143f47b63b2`
- 8 / 8 bounded repetitions completed
- runtime exceptions: 0

### A. State-fidelity raw failure

Fixture:
`epistemic_private_message`

Across 4 repetitions:
- semantic state behavior: correct in **4 / 4**
- raw evaluator pass: 3 / 4
- one raw failure contained only:
  `missing_bridge`

All 4 states:
- mode = EPISTEMIC;
- uncertainty = low;
- preserve the explicit private-only communication facts;
- preserve absence of retransmission/public disclosure;
- do not attribute the information to other members;
- conclude that the other members cannot be treated as already knowing the
  delay.

In the single raw-failed repetition, `missing_bridges=[]` because the state
had already resolved the relevant no-access path at the asked granularity.

Classification:

**EVALUATOR_FALSE_NEGATIVE**

### B. Answer-checker raw failure

Fixture:
`fresh11_absence_of_evidence`

Across 4 repetitions:
- first checker REVISE: **4 / 4**
- revised answer removes unsupported certainty: **4 / 4**
- final checker PASS: **4 / 4**

First-check violation families:
- PREMATURE_COLLAPSE: 4 / 4
- UNSUPPORTED_INVENTION: 1 / 4
- BELIEF_LEVEL: 0 / 4

The behavioral semantics are stable:
- absence of evidence is not treated as evidence of absence;
- the candidate's unsupported certainty is rejected;
- calibrated epistemic uncertainty is restored.

The raw fixture expected only BELIEF_LEVEL, so its family-overlap gate rejected
a behaviorally correct result.

Classification:

**TAXONOMY_EVALUATOR_FALSE_NEGATIVE**

## Adjudicated accounting

Raw historical accounting remains:

- full regression workflow: FAILURE
- state fidelity raw: 11 / 12
- answer checker raw: 11 / 12

Adjudicated semantic accounting:

- state-generation reliability: PASS
- fresh semantic-faithfulness answer suite: PASS
- original output-interface audit: PASS
- production-path state fidelity: **12 / 12 semantic pass after adjudication**
- answer-checker fresh suite: **12 / 12 behavioral pass after adjudication**

Therefore the frozen repaired runtime receives:

**ADJUDICATED SYNTHETIC PASS**

## What is closed

This closes the synthetic validation package for:
- state-JSON non-thinking reliability repair v0.2;
- generic answer-loop semantic-faithfulness repair;
- runtime state-prompt conformance repair v0.1;

under the current DeepSeek instantiation and frozen HCL v0.3 semantics.

## What is not established

This does not establish:
- fresh external benchmark efficacy;
- cross-provider or cross-base transfer;
- HCL 1.0 certification;
- that evaluator taxonomy should be rewritten retroactively.

## Historical-evidence rule

Do not:
- rewrite run `35721321301` as successful;
- delete the two raw failures;
- alter historical artifacts;
- lower raw gates retroactively.

Any evaluator improvement is a separate future maintenance change, not part of
this closure.

## Next boundary

Fresh external evidence may be considered only under a separately predeclared
protocol that:
- excludes all previously consumed Hi-ToM / FANToM / SOTOPIA rows;
- preserves the current frozen repaired runtime;
- does not tune on fresh evaluation rows;
- clearly separates execution reliability from efficacy claims.
