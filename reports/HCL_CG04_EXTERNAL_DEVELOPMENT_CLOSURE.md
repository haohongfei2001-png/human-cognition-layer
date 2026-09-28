# CG04 source-first Phase E closure

**Disposition: RETAIN — bounded optional development evidence only. One run consumed.**

## Immutable execution and receipts

Owner baseline main1185b981 authorized one USD0.30/20-call/zero-retry/512-output-token run. Activation PR156 head6dd0d2f had exact-head run36463217203 PASS; merged c4ed314 had exact-main run36463364888 PASS (329 v1 +176 historical). Unique single-parent trigger f6c76a6 ran [36463463452](https://github.com/haohongfei2001-png/human-cognition-layer/actions/runs/36463463452), attempt1 SUCCESS. Trigger exact-main provider-free run36463463573 PASS.

Paid execution checkout was **018afbc93c645975d7f6f1077c8c8380635d9f2f**, runtime digest **b700aaef4a27d6beda7b4abd79b6801d29947583adaa1dc00ca45b3f50ccd006**, identical to certified implementation88b5cfb. Latest runtime was not substituted. Package SHA256 **0ffcfdfae3d9d5130c96205f2247991d1d88a872edbb144b701ad01da3202ce9** and all four frozen engineering hashes matched. All actual source grounding, checker execution, checked-state inclusion, ablation, same-task/full-vocabulary/fairness gates passed before payment. Rebuilding the whole package at this isolated checkout matched exactly. Frozen source/gold/prompts/scorer/arms/treatment were unchanged.

Artifact10988468609 ZIP digest **8dcd61ddc13ae265e5b3af07be77d2a1c880e37ef7c6fd98920bddfb96a106e6** was independently recomputed and matched GitHub. Byte-preserved [raw result](HCL_CG04_EXTERNAL_RUN_36463463452.json) digest **665e9f32e3c96c750575b2c69fdd09d4592edf2d9ed6148b034e3540ef2403fb**. [Journal](HCL_CG04_EXTERNAL_RUN_36463463452/journal.json), [control](HCL_CG04_EXTERNAL_RUN_36463463452/control-receipt.json), [actual treatment preflight](HCL_CG04_EXTERNAL_RUN_36463463452/preflight.json) and [receipt audit](HCL_CG04_EXTERNAL_RECEIPT_AUDIT.json) preserve the full execution. Journal/result bytes agree; all 20 raw requests/final messages match frozen arms; unchanged scorer recomputes exactly.

## Usage, cost and comparison

20 calls, zero retries, all responses `stop`, thinking disabled, default tier, existing secret only. Actual returned model IDs all `deepseek-v4-pro`; published frozen version DeepSeek-V4-Pro-0813, returned alias alone does not independently attest backend revision. 21,311 input +2,867 output tokens. Conservative frozen peak all-cache-miss cost **USD0.03948384**, below USD0.30. Timestamp/cache published-rate estimate **USD0.016720352**; invoice/account charge unavailable from completion API. The budget uses conservative rating, never the estimate. Official current [pricing](https://api-docs.deepseek.com/quick_start/pricing/) was rechecked and matches frozen peak rates. No balance query, new API/account/plan, old budget transfer or LongMemEval access.

| Arm | Exact fields /28 | Complete cases /4 | Input/output tokens | Conservative USD |
|---|---:|---:|---:|---:|
| C |26|3|1599/576|0.00439164|
| P |23|1|1751/560|0.00452892|
| G |25|2|1867/574|0.00473748|
| H |28|4|9063/575|0.01424016|
| H-new |26|3|7031/582|0.01158564|

## Source-first interpretation

All arms had identical task, all seven fields, complete preference/condition/conflict vocabularies and identical source. P explicitly instructs scope, missing evidence, attribution and revision; G gives ordered source rows and generic tables. Qualification is adequacy of those prospective comparators, not a claim that every returned enum is correct or every possible prompt was optimized. P's invented preference-state CONTESTED is an observed error despite receiving the full allowed vocabulary, not evidence that the vocabulary was missing. All responses have the required seven-field top-level structure; the frozen scorer's `valid` flag checks structure, not each enum. A condition key `rain is true` instead of `rain` is partly encoding, so exact-field gains alone do not establish cognitive increment.

1. **Conditional scope:** source explicitly says rain is true in fieldwork. H/C/H-new preserve a met condition and applicable medic preference; P marks UNKNOWN yet CONDITION_NOT_MET. G recognizes the condition (with an expanded key) but still marks the preference CONDITION_NOT_MET. Their applicability errors are substantive; the G key mismatch alone is not.
2. **Unknown condition plus observed choice:** source does not supply rain. H leaves UNKNOWN and CONDITION_UNRESOLVED. G/P/C mark CONDITION_NOT_MET despite unknown evidence (P/C also use the expanded key). H-new explicitly changes rain to NOT_MET_BY_SOURCE_CLAIM with no supporting source. This is the attributable new-mechanism delta: evidence absence remains unresolved rather than negative. Every arm correctly refrains from making an enduring value out of the observed choice; no increment on that field.
3. **Local revision:** all arms correctly supersede only the old medic/fieldwork preference and preserve courier/deliveries. No new increment.
4. **Unresolved conflict and attribution:** H/C/G/H-new preserve opposite active preferences and Bob's report as attributed, not Alice's endorsed private value. P preserves unresolved conflict but invents a preference enum and promotes Bob's claim. H has no new gain over G/H-new on this case.

H exceeds qualified P and G on actual applicability/evidence-boundary behavior; H-new's unsupported negative on case2 supports attribution. No observed H reverse harm. This satisfies the prospective **RETAIN** rule for the bounded optional checker, with attribution supported on only one case, no population estimate. The strongest cheap baseline C is already26/28; default base-model use remains appropriate. H costs3.14xP/3.01xG and1.23xH-new. Keep selective checks for explicit condition/applicability risk; these costs do not establish the eventual typical-cost maturity target or justify universal routing.

Four public HCL-authored synthetic development cases, not independent/fresh external evidence. No broad value understanding, moral truth, global value weights or optimal-choice claim. Independent generalization remains untested. No case change, rerun or appended sample is authorized. Grant zero and trigger removed by this closure; unused money extinguished, never transferred. After exact-main CI, immediately execute separately authorized CG05.
