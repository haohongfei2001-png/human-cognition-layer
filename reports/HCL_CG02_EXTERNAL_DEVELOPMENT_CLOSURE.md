# HCL-CG-02 source-first Phase E closure

**Disposition: INCONCLUSIVE. One authorized run consumed; no rerun.** This is a measurement qualification decision, not a claim that the CG-02 checker failed. The provider-free checker remains available for source-valid evidence. No independent or fresh external efficacy claim is made.

## Identity, authorization and treatment

- Owner-named authorized baseline: `main@86e1db9ecdb908cbe67bc561b878a0d37e4cb819`.
- Frozen package SHA-256: `6384b0925a191041de0478aa46cb69618502e553cb0c4f5838087f4a6c95c694`.
- One-shot trigger commit: `ed63aeeba1da3a0f86406562ebddd06f98415321`.
- [GitHub Actions run 36413088075](https://github.com/haohongfei2001-png/human-cognition-layer/actions/runs/36413088075), artifact ID `10966520253`, downloaded ZIP SHA-256 `8df77c2c2ba5c48bfccf08d28614ef07c93cfe2eda933747cbce3433359560c9`.
- [Full raw receipt](HCL_CG02_EXTERNAL_RUN_36413088075.json) SHA-256 `ca271347f343647f190d2c9ba55140865421ff13d79aaebdd46250b308e9b972` contains every exact request payload, full provider response object, raw answer, usage, score, final H/H-new messages, checked state and preflight result.

The workflow rebuilt the frozen package and reran treatment-presence preflight before any paid request. All four cases passed source validity, grounded act, executed expectation check, checked H state, H-new ablation, and a final-input difference caused only by that checked state. The receipt's 20 final message lists match the frozen package exactly. No case, gold field, prompt, scorer, arm, treatment or price basis was changed after freeze. The four dialogues are HCL-authored synthetic development cases and publicly source-audit-exposed.

## Provider and cost receipt

All **20 of 20** calls returned a `stop` finish reason; there were **zero retries** and no tool calls. The request model was `deepseek-v4-pro`, with thinking disabled and JSON response mode; the provider returned `deepseek-v4-pro` on every call. Responses reported 13,353 input and 1,648 output tokens. The frozen conservative peak all-cache-miss rating sums to **USD 0.02415204**, below the **USD 0.30 hard cap**. Using each response's cache-hit/miss tokens and 2026-09-28 off-peak time, the published-rate usage estimate is **USD 0.01125938**; this is not an independently verified account invoice. The budget basis used for gating remained the frozen conservative peak rate. No historical budget was transferred. LongMemEval was not accessed.

## Frozen scorer and source-first audit

The predeclared strict scorer requires exactly seven JSON fields and exact values. All 20 answers were parseable with exactly those fields. The table gives exact-field matches out of 28 across four cases, and fully correct cases out of four.

| Arm | Exact fields | Fully correct cases | Conservative rated cost |
|---|---:|---:|---:|
| C | 8/28 | 0/4 | USD 0.00235092 |
| P | 7/28 | 0/4 | USD 0.00265452 |
| G | 9/28 | 0/4 | USD 0.00280500 |
| H | 24/28 | 1/4 | USD 0.00947100 |
| H-new | 9/28 | 0/4 | USD 0.00687060 |

The source-first review keeps the source act separate from the reported expectation:

1. **Conditional omission.** Alice's act says `If I finish by Friday`; Bob's later report omits it. H and G identify the stronger later expectation. C reverses the relation and P calls it compatible. H preserves the exact condition and access state, but emits `UNKNOWN` rather than the required `NONE` for `response_reference`.
2. **Conditional preservation.** Theo repeats Maya's condition. H matches all seven frozen fields. C/P/G also recognize a compatible expectation in ordinary language, while their access and label choices differ from the frozen gold.
3. **Proposal and acceptance.** Nora proposes and Eli accepts before reporting an expectation. All arms broadly recognize the proposal. H's checked state is present, but its answer emits the internal `act-1` reference rather than `ACCEPTANCE_REFERENCES_PRIOR`, and `UNKNOWN` rather than the gold `NONE` for a nonapplicable access check. G identifies the acceptance as event order 2, which the strict scorer does not credit as the frozen label.
4. **Later withdrawal.** Leah's condition is omitted in Omar's report; Leah withdraws afterward. H captures both the stronger expectation and later timing. C reverses the relation, P/G call it compatible, and G sets `unsupported_moral_claim` to true without source support. H-new identifies the stronger relation but does not preserve the access state or required timing label.

H outscored P and G, and H-new was much weaker on exact fields. The source review shows some useful CG-02 behavior, particularly preserving the condition/expectation distinction and the withdrawal order. **The strict comparison cannot establish a qualified specialized increment:** the C/P/G/H-new task instruction listed allowed expectation-relation labels but did not enumerate the act, access, response-reference or withdrawal labels required by the gold, whereas H's checked context supplied those exact labels. Much of the 24-versus-7/9 gap can therefore be output-contract compliance rather than social reasoning. The semantic advantages in these four synthetic cases are too narrow to separate from that measurement bias. H also cost about 3.6 times P and 3.4 times G on the conservative rating, which raises the bar for retaining the extra context. This is **INCONCLUSIVE** under the predeclared source/measurement-failure rule; it is not RETAIN, SIMPLIFY or DEACTIVATE evidence.

## Closure and next capability

This source family, frozen scorer and one-time authorization are consumed. Do not rerun, change cases or gold, add samples, or seek a positive CG-02 result through another prompt/benchmark search. The deterministic checker remains an optional provider-free correctness component; external utility is unresolved. The one-time workflow grant and trigger are closed in the closure change.

The next capability-first candidate from `DEVELOPMENT_PLAN.md` section 8 is **responsibility-structure explanation**: distinguish causal contribution, knowledge, foreseeability, control, intention and responsibility basis under explicit normative premises. Its first development work should implement a bounded source/assumption-scoped mechanism rather than start a leaderboard or source qualification campaign.
