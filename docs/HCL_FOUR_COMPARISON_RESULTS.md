# Four-case development comparison: closed results

## Result

The frozen one-pass comparison completed on 2026-10-04. On the four planned cases, independent source-first ratings locked before unmasking give **Base 38/40, HCL 30/40**. Base delivered four acceptable answers; HCL delivered three, with one unavailable answer retained as zero in the four-item denominator. HCL gained two points on D02, lost ten on D01's failed delivery, and tied on D03 and D04.

This is a small, assistant-authored development diagnostic. It does not establish efficacy, representative accuracy, generalization, module causality, production-default performance or I02 completion. The HCL arm had additional planning compute. Unchanged output wording can imperfectly reveal method identity despite the removed labels and metrics.

| Case | Base score | HCL score | Base delivery | HCL delivery |
|---|---:|---:|---|---|
| D01: meeting perspectives | 10 | 0 | Accepted | No canonical final object |
| D02: action reasons | 8 | 10 | Accepted | Accepted |
| D03: social interpretation | 10 | 10 | Accepted | Accepted |
| D04: counterfactual support | 10 | 10 | Accepted | Accepted |
| Planned denominator | **38/40** | **30/40** | **4/4** | **3/4** |

D02's Base answer incorrectly attributes an inferred avoidance motive to the coworker, while the source only says the coworker reported an argument. The independent scorer deducted one content point and one traceability point before unmasking. No listed semantic critical errors were found in the seven available outputs. Missing D01 HCL content is unassessable, not evidence of a particular semantic error.

## D01 HCL failure, preserved without repair

The original D01 HCL arm selected and executed B01, B02 and D02. Its planning and final provider calls both returned with validated model/usage; the public call rows have `RETURNED` status. The final stage has safe status `FINAL_SCHEMA_OR_CITATIONS_REJECTED`, a final-content hash, and null canonical final fields. This means no final object passed the strict public canonical-field check. The public evidence does not retain noncanonical raw output, so it cannot distinguish malformed JSON from a missing/extra/wrongly typed field or malformed citation-object shape. A finer diagnosis would be unsupported. This was neither a transport timeout nor an absent HCL planning call.

No invalid output was rewritten, no fallback was supplied, and no replacement, extraction call or retry was made. The unavailable packet was independently scored zero end-to-end, with content-only score null.

## Costs and latency

Costs below are complete returned-usage estimates at the frozen peak rates, **not verified invoice charges**. Full conservative reservations were retained and unused authority was closed rather than recycled.

| Arm | Calls | Usage-rated estimate (USD) | Total arm wall time | Mean over all 4 planned arms |
|---|---:|---:|---:|---:|
| Base | 4 | 0.04632540 | 103.372 s | 25.843 s |
| HCL | 8 | 0.19002984 | 367.742 s | 91.935 s |
| Batch | 12 | **0.23635524** | 471.124 s batch elapsed | — |

The complete reservation was **US$1.27791840**, below the US$1.28 hard cap. HCL's failed D01 arm took 84.479 s and remains in its mean. The three available HCL arms averaged 94.421 s; that excludes a failure and is disclosed only as a secondary descriptive number. A short failed arm is not a speed improvement.

Primary arm latency starts before arm-specific source setup, prompt creation and reservation, with the shared client ready; it includes schema/citation validation. HCL includes planning, local native work and final generation. Common checkout/install/CI queue, common file loading, scoring and publication are excluded for both. Per-call SDK and per-arm non-SDK times are preserved in the public evidence. The tiny serial alternating schedule cannot establish production latency or causal effects.

## Actual capability selection

The runner imposed no selected-module condition. All four HCL arms reached native execution and final-call admission.

| Case | Selected IDs | Executed IDs | Reported checked-treatment IDs |
|---|---|---|---|
| D01 | B01, B02, D02 | B01, B02, D02 | Empty |
| D02 | C02 | C02 | Empty |
| D03 | B01, B02, C04 | B01, B02, C04 | Empty |
| D04 | G04, C03 | G04, C03 | Empty |

These are runtime-reported IDs and flags, not independent certificates of relevance, faithfulness or useful treatment. Empty checked-treatment arrays do not establish that every native result was useless; successful native invocation does not establish a beneficial cognitive intervention. D04 did not select G05. Neither the answer gain on D02 nor the other outcomes can be causally attributed to a specific module from this experiment.

## Independent review and exact evidence

An independent reviewer received only original source/question, frozen rubric, unchanged final fields and unavailable placeholders under shuffled packet IDs. Arm labels, planning, capability IDs, costs and latency were absent. All eight ratings and reasons were locked before the mapping was opened. The reviewer did not author these cases. The implementer did not substitute its own scores or modify the locked scores after unmasking.

The independent review checked exact visible quotes and schema; it explicitly left the unchanged canonical citation-audit execution pending. After scores were locked, the unchanged audit was rerun on all seven final-field objects using the same original source payload and passed. This resolves only delivery acceptance and does not certify semantic truth or change any content rating.

- [Original public evidence](../reports/HCL_FOUR_COMPARISON_PUBLIC_EVIDENCE.json): SHA256 `646153dfbde20dea80008cd2699d3d2073c97882fb91059d57ac6ab481eb9e79`
- [Unchanged anonymized packets](../reports/HCL_FOUR_COMPARISON_BLIND_PACKETS.json): SHA256 `788eb9fbd8c325c0034fff33e5a2d3ce35071707709fc465036ecaba1706f58f`
- [Locked independent scores and reasons](../reports/HCL_FOUR_COMPARISON_INDEPENDENT_SCORES.json): SHA256 `73a797141a3a7c8a0b7e45e87acf9c4d85301e63d14d38dc68950c22d0ad640c`
- [Joined scores, identity, gates and metrics](../reports/HCL_FOUR_COMPARISON_RESULTS.json)
- [Frozen preparation](HCL_FOUR_COMPARISON.md) and [unchanged original proposal](../.github/frozen/hcl-four-comparison/README.md)
- [Single execution run 37202844362](https://github.com/haohongfei2001-png/human-cognition-layer/actions/runs/37202844362), head `e9467de0a018e7e454092220d999712fb975236c`, attempt 1
- GitHub artifact 11304010732, ZIP SHA256 `4cbae04c54a8d9ce2a2a549308b1b0f5d85d928c245fd4625ff5914fe99289fd`; retrieved bytes verified before extraction
- Package SHA256 `290e5c572d1d4e4b11ab1317469d08259b7d4da8e1314fea306c92b873ed058a`; runtime `90737b3ed772f65851553d8a673112eae50f2781185d8b5b4ccd127cdfb8663b`
- Trusted-main same-run existing-secret check reported PRESENT at 12:39:30 UTC; the complete once-history gate admitted the run before provider execution. No secret value was recorded.

The [repository grant](../.github/HCL_FOUR_COMPARISON_GRANT.json) was closed at main `fbda17ff3d33164b1c35b32abdd3f0f8a3863288`, with remaining calls **0** and remaining authorized USD **0**. Its exact [closure-main provider-free CI](https://github.com/haohongfei2001-png/human-cognition-layer/actions/runs/37203530029) passed. Reexecution is rejected by the closed grant and the consumed one-run history. The prior G05 grant was not reopened or changed.
