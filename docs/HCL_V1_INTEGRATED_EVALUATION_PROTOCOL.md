# HCL v1 integrated human cognition evaluation: source audit and design

Status: **SOURCE_AUDIT_COMPLETED_NO_QUALIFIED_INTEGRATED_SELECTION**. This is an evaluation design, not an executable/frozen paid package. v1 runtime first passed exact-main provider-free certification at `9070bbcf518b5aa69b92502949998413e0960d1d`, run [36347078900](https://github.com/haohongfei2001-png/human-cognition-layer/actions/runs/36347078900): 42 v1 + 176 historical tests. No new provider call, sample scoring or budget authorization occurred.

## Bounded independent source audit

Only two candidates were investigated, after runtime certification. Neither existing consumed FANToM/SAGA/CAREBench/Circa/CLASH/TORQUE/FOLIO examples nor sealed LongMemEval was selected. Search snippets exposed public BigToM paper examples; those families must not later be called unexposed/fresh. Metadata-only inspection never establishes sample freshness or source-semantic validity.

### BigToM: public and licensed, but generated mental-state labels are not an independent source oracle

Author repository pin [`fe647d680bddb69f738519313bed625f9e93b549`](https://github.com/cicl-stanford/procedural-evals-tom/tree/fe647d680bddb69f738519313bed625f9e93b549). [README](https://github.com/cicl-stanford/procedural-evals-tom/blob/fe647d680bddb69f738519313bed625f9e93b549/README.md) identifies LLM-generated causal-template evaluations; [MIT license](https://github.com/cicl-stanford/procedural-evals-tom/blob/fe647d680bddb69f738519313bed625f9e93b549/LICENSE) read. The [author project](https://sites.google.com/view/social-reasoning-lms/home) describes forward-action and backward-belief inference and human quality/performance studies. This genuinely connects beliefs and desires; it is not rejected merely for being synthetic.

Code-level audit of [`generate_conditions.py`](https://github.com/cicl-stanford/procedural-evals-tom/blob/fe647d680bddb69f738519313bed625f9e93b549/code/src/generate_conditions.py), especially lines 59–74 and 144–157, shows that condition identity selects template-generated aware/not-aware action/belief alternatives and correct-answer ordering. Source anchoring and independent human ratings do not, by themselves, prove each hidden-state-derived action alternative is uniquely licensed by the public narrative. No dataset rows, actual gold or model result files were opened. Decision: **NOT_QUALIFIED_FOR_THIS_INTEGRATED_SOURCE_TRUTH_PROTOCOL** without an independent source-first, item-level semantic audit. Do not equate intended generator beliefs or inverse-action motives with private truth. This does not assert that every BigToM item is invalid.

### DREAM: accessible human-authored dialogue, but screened questions do not establish the required composition

Author repository pin [`bb64644c209cb6497bb9e13244fbf220c900a740`](https://github.com/nlpdata/dream/tree/bb64644c209cb6497bb9e13244fbf220c900a740). [README](https://github.com/nlpdata/dream/blob/bb64644c209cb6497bb9e13244fbf220c900a740/README.md) documents unmodified dialogue/question/three-choice/answer records; [paper](https://arxiv.org/abs/1902.00164) describes human examination dialogue comprehension. The actual [dataset license](https://github.com/nlpdata/dream/blob/bb64644c209cb6497bb9e13244fbf220c900a740/license.txt) restricts use to non-commercial research. The paper's publication license must not be substituted for dataset permission. Current research screening fits the stated scope; unrestricted/commercial reuse is not qualified. [Collection websites](https://github.com/nlpdata/dream/blob/bb64644c209cb6497bb9e13244fbf220c900a740/websites.txt) provide corpus-level origin references, not per-item original provenance.

Native dev source downloaded for source-only inspection: SHA256 `9d5af2e580d809c73872a7dd43fe93d0b07c6f6086b04a9a9a1917603009d961`, 1,288 dialogues. Gold fields remain masked: selection and displayed source audit use only IDs, dialogue, question and choices. This is not an external provider evaluation and produces no native score. No raw dataset text is committed.

Pass 1 selected the first four `sha256(dialogue_id + ':' + zero_based_question_index)` sorted candidates whose question matched `why|plan|want|intend|probably do|going to do` (case-insensitive). Pass 2 additionally required source dialogue to match `thought|believe|didn.t know|didn.t realize|misunderstood|mistake|remember|forgot|know`, omitted pass-1 question IDs, and selected the next four sorted candidates. Exactly 119 source-only candidates matched pass 2; keyword eligibility is not cognition qualification.

| Exposed source/question (zero-based) | Source-only audit finding |
|---|---|
| 21-43 / 0 | explicit movie-rental plan; choosing a home location adds a conventional assumption, not perspective/goal composition |
| 9-70 / 0 | job-interview purpose explicitly anchored; no needed belief/access computation |
| 14-83 / 0 | thank-you reason directly stated; no private motivation oracle |
| 12-281 / 0 | reported fatigue/work duration; causal commonsense, no belief-access requirement |
| 5-149 / 3 | financial concern versus an explicit farm plan; plausible goal/appraisal connection, but no validated perspective/belief requirement and no native/source gold audit |
| 20-55 / 3 | stated accommodation suggestion; third-party support must remain attributed, answer is direct retrieval |
| 16-158 / 1 | stated preference reason; speaker attribution is enough, no hidden belief computation |
| 1-34 / 3 | explicit herbal-remedy suggestion; no medical correctness claim or needed perspective/goal combination |

All eight complete dialogue families are now **SOURCE_AUDIT_EXPOSED / NOT_PROVIDER_CONSUMED**; exclude them from any later unexposed claim. Native questions and options were not rewritten. No gold was used for selecting or rejecting candidates. Decision: **NO_QUALIFIED_MULTI_CAPABILITY_SELECTION_FROM_THIS_BOUNDED_SCREEN**. This is not a claim that the entire DREAM corpus lacks integrated questions. Do not promote dialogue length, incidental words, or a potentially useful goal/appraisal example into certified integrated-cognition necessity. A simple strong direct baseline is appropriate for the inspected tasks.

## Predeclared design for a future qualified source

The unit is an unchanged native source plus native question/options. Each selected task must independently and audibly require at least two substantive cognitive operations, such as perspective/belief together with explicitly grounded intention or narrative/social integration. Bookkeeping/provenance does not count as a second cognition capability. No HCL-specific task rewriting, hidden generator truth or forced unique natural-language formalization.

Freeze before any provider call: repository/data revision and license, exact source digest, source-only selection rule and identities, family-level exposure exclusions, item-level source/native semantic audit, target/observer/time interpretation, output contract, all four arm inputs, model identity and pricing/caps, scoring and masked source-first audit rules. If natural-language access or mental-state extraction is required, it must be source-grounded, auditable and separately counted. No oracle state for H. Any upstream normalization/access metadata must be the same public-source asset available to G; interpretation assumptions cannot be hidden privileges.

| Arm | Treatment |
|---|---|
| C | strong direct reasoning with evidence/uncertainty instructions and unchanged source/question/options |
| P | same source plus best simple scaffold frozen without selected-case/outcome tuning |
| G | competent generic structured evidence with actor/time/access/uncertainty support, same source and model; no artificially weak competitor |
| H | actual integrated v1 router and minimum selected runtime context; identical source privileges; charge any semantic extraction and extra context |

All arms share the answer adapter, model version, final-answer allowance and output contract. Preserve invalid outputs, source/native disagreements, unscorable ambiguity and all predeclared samples. No post-hoc exclusions, rescoring, prompt repair or gold-driven routing. Compare semantic gains/reversals versus G as well as P/C, excess unsupported/private-state claims, abstention, actual invocation count, context size, extraction/provider calls, exact-tool work and total cost. Correct synthetic integration is not external utility. Without credible incremental gains simplify or retain direct/generic methods; do not invent v0.11.

## Sole next gate

**HCL_V1_INTEGRATED_SOURCE_QUALIFICATION**: obtain a native source selection with independently auditable multi-capability semantics, permitted research use, source text, gold and exposure ledger. These requirements have not been passed by the current screen. There is no frozen fresh C/P/G/H package and no budget request yet. Owner action: **none**. Paid calls: **zero**.

Only after all package fields are concrete and frozen may the gate become `HCL_V1_INTEGRATED_EVAL_OWNER_BUDGET_AUTHORIZATION`, with exact dataset, selection size, call count, provider/model, input/output caps, USD hard cap, exposure state and expected evidence value. Old budgets cannot transfer. No paid trigger was created.
