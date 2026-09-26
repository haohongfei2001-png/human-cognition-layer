# HCL v0.8 Affect & Appraisal Final Development Closure

Status: **FROZEN / SIMPLIFY / CAREBench development direction closed**

## Execution

On 2026-09-27 Asia/Shanghai, the owner separately authorized the frozen
8-case C/P/D development check within USD 0.25. Trigger-only PR #82 merged
as `6a1a807d009d052d5afc6a80511c82167744a2a4`, exact parent
`0b77dd6180938567a70270d1a0cdfdec5fdb7a08`.
[Run 36263323431](https://github.com/haohongfei2001-png/human-cognition-layer/actions/runs/36263323431)
completed SUCCESS, attempt 1, 8/8. Source digest, frozen selection,
zero-provider validation and runtime regressions passed before paid calls.
The previously certified candidate passed 93 regressions at exact main
`f81aa762e83fcdf1e1ae7382c4c7c596dae48bdf`.

Artifact `10913375300` downloaded ZIP digest matches GitHub:
`3f83e2577907d1e1949353c7235283316feae2ed10a85c9dc14b1c90f95d281d`.
The structured receipt is `reports/HCL_V08_CAREBENCH_DEV_V01_RECEIPT.json`.
Authorization is reset to zero; the historical trigger remains. Eight
narrative and source-key families are development-consumed. No annotation
values were inspected or supplied to state, answer construction or scoring.
LongMemEval remains sealed and provider-unconsumed.

## Frozen rubric and diagnostic audit

All 24 answers were reviewed with method names shuffled independently per
case before aggregate comparison. Source narratives and raw answers were
visible, withheld human emotion/appraisal ratings were not. Notes saved
before unmasking have SHA-256 `f8f464a3b20aaabee012744a16152574830dbfa6520364fb0d5c0fb0fe740592`.
This is one agent's development diagnosis, not independent human adjudication;
style can reveal methods. No private-emotion truth score is computed.

The predeclared material-error rubric detected zero errors for C/P/D;
D-versus-P and D-versus-C discordances are both 0/0 (eight without a detected
material error). This does **not** mean all explanations are correct. The
rubric has a narrow material threshold and several conceptual ambiguities.
Format invalidity is separate: C=0, P=1, D=0. The P response in case 07
lowercased a quoted sentence's initial letter, failing the frozen exact-quote
validator. Its raw response still preserves the core feelings. It is retained
as invalid, not repaired, silently normalized or rescored.

| Case | Source-grounding diagnosis after unmasking |
|---|---|
| 01 | All retain reported pride and goal importance; C/P positive congruence is explicitly inferred. |
| 02 | All retain upset/distance and helping goal; D retains hope in appraisal/uncertainty. Hope as affect versus epistemic attitude and low-certainty mapping remain ambiguous. |
| 03 | All retain anger/stress/depleted metaphor with narrated timing; obstacle/control claims stay inferred. |
| 04 | All retain discouragement/stress. C's worry is inferred. P classifies a need for answers as emotion: category confusion recorded separately. Direct congruence mappings remain interpretive. |
| 05 | All retain awkwardness/mediator discomfort and qualify later relief as inferred. All place peacemaking desire in emotion; this category ambiguity is not a newly invented private feeling. |
| 06 | All retain author sadness and avoid importing another person's emotionality. D uses a desired understanding under goal congruence rather than relevance, a dimension mismatch. |
| 07 | All raw answers preserve doubt/unsettled feeling despite a favorable outcome; no direct joy is invented. P is format-invalid. Acceptance-as-affect and mixed goal congruence are ambiguous. |
| 08 | All retain author anger/sadness and preserve partner separation. D's claim of no goal-relevance evidence is overbroad given the stated counting aim; record this issue without retrofitting the frozen material-error criterion. |

Reasonable hypotheses, emotion/goal category boundaries and appraisal
mapping differences are not retroactively turned into a new numerical score.
The receipt preserves every masked observation and its arm mapping.

## Mechanism and causal limits

D constructed 24 semantic evidence rows across 6/8 narratives. Three sources
needed one extraction repair; two remained invalid (05: unbounded appraisal
dimension; 07: expression promoted to direct feeling). Atomic fail-closed
handling created zero claims for those sources and retained all eight full
reports. This check did not test separate event chronology, revision or goal
links. Provider-free correctness of those features remains distinct from
external explanation utility.

The predeclared continuation condition requires at least two P-material-error/
D-grounded cases, no more than one reverse case and visible typed support
consistent with the gains. Observed material-error discordances are 0/0.
Even counting format invalidity gives only one D/P difference, in 07 where
D has zero semantic evidence. The condition is not met.

The artifact stores state hashes/counts rather than actual typed evidence
rows. It cannot establish those rows' entailment or a causal contribution;
no reconstruction or further provider run is performed. This audit limitation
must not be hidden behind the reported evidence count. Any future capability
runner requiring mechanism diagnosis must archive the exact source-scoped
state actually supplied to its answer arm, alongside hashes. This is an audit
receipt requirement, not tuning on these consumed outcomes.

## Operations and cost

All reported response model identities are `deepseek-flash`; temperature 0,
seed 42, thinking disabled and equal 512-token answer maximum. The alias does
not guarantee an immutable checkpoint. Peak rates were rechecked against
[official pricing](https://api-docs.deepseek.com/quick_start/pricing/) on
2026-09-27. Ledger cost is conservative provider-token rated usage, not invoice.

| Component | Calls | Input chars | Output chars | Peak-rated USD |
|---|---:|---:|---:|---:|
| C | 8 | 12,142 | 10,744 | 0.00432930 |
| P | 8 | 13,318 | 10,130 | 0.00422010 |
| D answer | 8 | 31,204 | 9,883 | 0.00566471 |
| D semantic | 11 | 34,704 | 18,410 | 0.00731755 |
| Total | 35 | 91,368 | 49,167 | **0.02153166** |

Provider wall summed to 64.425639 seconds. Character-as-token peak upper
bound USD 0.086411; all call/character/budget caps respected. No transport,
model-drift or budget failure occurred. D construction plus answer cost USD
0.01298226; C USD 0.00432930. P's one format failure is recorded separately
from operational SUCCESS.

## Final decision

**SIMPLIFY** the affect explanation method to the frozen strong C instruction
with the complete source, evidence strength, mixed feelings and uncertainty.
P's added reminder shows no material increment; D adds extraction cost and
failure modes without satisfying its development continuation criterion.
Retain the typed runtime as audit/integration infrastructure with no downstream
utility claim. Do not expand affect architecture, tune the consumed cases or
launch fresh CAREBench efficacy merely to obtain a favorable result.

This small filtered source set neither demonstrates a stable current-model
affect deficit nor exhausts affect capability. It closes this development
candidate. Continue a short capability-direction audit and one next minimal
capability with independent provider-free correctness; provider-backed work
requires separately scoped budget authorization.
