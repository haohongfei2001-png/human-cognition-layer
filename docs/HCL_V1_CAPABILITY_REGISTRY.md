# HCL v1 executable capability registry

Canonical implementation: `hcl/v1/capabilities.py`. No inventory entry alone causes activation. Base model direct has ZERO HCL overhead. All selected deterministic projections and bounded local tools are LOW; semantic extraction is MEDIUM and multiple provider extraction passes HIGH, neither is scheduled by v1. Failure closes to system-insufficient evidence without inventing character state.

| ID | Type / status | Implementation | Evidence | Default activation | Dependencies | Cost | Failure |
|---|---|---|---|---|---|---|---|
| evidence | CORE_RETAIN / RETAIN | `hcl/v04/model.py:EventRecord` | FOUNDATION_CORRECTNESS | only selected HCL paths |  | LOW | SYSTEM_INSUFFICIENT; preserve evidence; no inferred private truth |
| provenance | CORE_RETAIN / RETAIN | `hcl/v05/store.py` | FOUNDATION_CORRECTNESS | retain source and evidence kind | evidence | LOW | SYSTEM_INSUFFICIENT; preserve evidence; no inferred private truth |
| temporal | CORE_RETAIN / RETAIN | `hcl/v05/store.py;hcl/v06/perspective.py` | FOUNDATION_CORRECTNESS | event and record-time bounds | evidence | LOW | SYSTEM_INSUFFICIENT; preserve evidence; no inferred private truth |
| actor_source | CORE_RETAIN / RETAIN | `hcl/v04/model.py` | FOUNDATION_CORRECTNESS | actor is not source | evidence | LOW | SYSTEM_INSUFFICIENT; preserve evidence; no inferred private truth |
| source_visibility | CORE_RETAIN / RETAIN | `hcl/v06/perspective.py` | FOUNDATION_CORRECTNESS | scope every selected context | temporal, actor_source | LOW | SYSTEM_INSUFFICIENT; preserve evidence; no inferred private truth |
| uncertainty | CORE_RETAIN / RETAIN | `hcl/v06/belief.py` | FOUNDATION_CORRECTNESS | missing system evidence is not character uncertainty | evidence | LOW | SYSTEM_INSUFFICIENT; preserve evidence; no inferred private truth |
| perspective | CORE_RETAIN / RETAIN | `hcl/v06/runtime.py:HCLV06Runtime` | FRESH_DEVELOPMENT_C11_P19_G22_D30_OF32_D_ONLY8_G_ONLY0 | information access/asymmetry/second-order tasks only | source_visibility, provenance, uncertainty | LOW | SYSTEM_INSUFFICIENT; preserve evidence; no inferred private truth |
| belief | CORE_RETAIN / RETAIN | `hcl/v06/belief.py` | FRESH_DEVELOPMENT_C11_P19_G22_D30_OF32_D_ONLY8_G_ONLY0 | knowledge/belief/revision tasks only | perspective | LOW | SYSTEM_INSUFFICIENT; preserve evidence; no inferred private truth |
| cg01_explanation | CORE_RETAIN / SIMPLIFY_CLOSED | `hcl/v1/cg01.py` | SIMPLIFY_ORDINARY_TEXT_CLOSED_CHECKER_UTILITY_INCONCLUSIVE | optional typed action-condition checks; ordinary route has no demonstrated increment | source_visibility, provenance, uncertainty | LOW | SYSTEM_INSUFFICIENT; preserve evidence; no inferred private truth |
| cg02_social_commitment | CORE_RETAIN / INCONCLUSIVE_CLOSED | `hcl/v1/cg02.py` | SOURCE_FIRST_INCONCLUSIVE_CLOSED_MEASUREMENT_CONTRACT | explicit bounded social-act and expectation correctness only; no qualified external utility | source_visibility, provenance, uncertainty | LOW | SYSTEM_INSUFFICIENT; preserve evidence; no inferred private truth |
| cg03_responsibility_structure | CORE_RETAIN / RETAIN_DEVELOPMENT_ONLY | `hcl/v1/cg03.py` | DEVELOPMENT_ONLY_RETAIN_C19_P21_G20_H28_HNEW23_OF28 | explicit source/time/access factors and caller-premise checks only; no broad moral competence | source_visibility, provenance, uncertainty | LOW | SYSTEM_INSUFFICIENT; preserve evidence; no inferred private truth |
| cg04_contextual_preference | OPTIONAL_STRUCTURED_SIMPLIFIED / RETAIN_DEVELOPMENT_ONLY | `hcl/v1/cg04.py` | DEVELOPMENT_ONLY_RETAIN_C26_P23_G25_H28_HNEW26_OF28 | explicit scoped preference checks only; select for uncertainty/applicability risk, no global values | source_visibility, provenance, uncertainty | LOW | SYSTEM_INSUFFICIENT; preserve evidence; no inferred private truth |
| cg05_local_concept | OPTIONAL_STRUCTURED_SIMPLIFIED / RETAIN_DEVELOPMENT_ONLY | `hcl/v1/cg05.py` | DEVELOPMENT_ONLY_RETAIN_C21_P23_G21_H28_HNEW23_OF28 | explicit scoped concept checks only; source uncertainty/counterexamples, no universal meaning | source_visibility, provenance, uncertainty | LOW | SYSTEM_INSUFFICIENT; preserve evidence; no inferred private truth |
| intention | OPTIONAL_STRUCTURED_SIMPLIFIED / SIMPLIFY | `hcl/v07/runtime.py` | SIMPLIFY_NO_SPECIALIZED_UTILITY | explicit goal/plan query; source-grounded optional context | provenance, source_visibility, uncertainty | LOW | SYSTEM_INSUFFICIENT; preserve evidence; no inferred private truth |
| goal | OPTIONAL_STRUCTURED_SIMPLIFIED / SIMPLIFY | `hcl/v07/runtime.py:GoalEstimate` | SIMPLIFY_NO_SPECIALIZED_UTILITY | explicit goals only | intention | LOW | SYSTEM_INSUFFICIENT; preserve evidence; no inferred private truth |
| motivation_evidence | OPTIONAL_STRUCTURED_SIMPLIFIED / SIMPLIFY | `hcl/v07/runtime.py` | SIMPLIFY_NO_SPECIALIZED_UTILITY | retain attribution as evidence, never invent motive | intention | LOW | SYSTEM_INSUFFICIENT; preserve evidence; no inferred private truth |
| affect | OPTIONAL_STRUCTURED_SIMPLIFIED / SIMPLIFY | `hcl/v08/runtime.py` | SIMPLIFY_NO_SPECIALIZED_UTILITY | feeling/appraisal question only; no action-to-emotion promotion | provenance, source_visibility, uncertainty | LOW | SYSTEM_INSUFFICIENT; preserve evidence; no inferred private truth |
| causal | GENERIC_EXACT_TOOL / CONDITIONAL_TOOL_ONLY | `hcl/v09/runtime.py` | GENERIC_TOOL_DEVELOPMENT_SIGNAL_ONLY | counterfactual request plus declared source-scoped model | source_visibility, provenance | LOW | SYSTEM_INSUFFICIENT; preserve evidence; no inferred private truth |
| argumentation | GENERIC_EXACT_TOOL / CONDITIONAL_TOOL_ONLY | `hcl/v10/runtime.py` | NONFRESH_GENERIC_TOOL_DEVELOPMENT_SIGNAL_ONLY | formal request plus complete declared attack graph | source_visibility, provenance | LOW | SYSTEM_INSUFFICIENT; preserve evidence; no inferred private truth |
| formal_verifier | GENERIC_EXACT_TOOL / CONDITIONAL_TOOL_ONLY | `hcl/quantified_logic.py` | PROVIDER_FREE_CORRECTNESS_ONLY | explicit formulas only | source_visibility, provenance | LOW | SYSTEM_INSUFFICIENT; preserve evidence; no inferred private truth |
| countermodel | GENERIC_EXACT_TOOL / CONDITIONAL_TOOL_ONLY | `hcl/quantified_logic.py` | NO_EXTERNAL_SEMANTIC_INCREMENT | explicit formulas and witness/domain bounds | formal_verifier | LOW | SYSTEM_INSUFFICIENT; preserve evidence; no inferred private truth |
| formal_reading | GENERIC_EXACT_TOOL / CONDITIONAL_TOOL_ONLY | `hcl/argument_readings.py` | PROVIDER_FREE_CORRECTNESS_ONLY | explicit alternative readings; never choose a winner | formal_verifier | LOW | SYSTEM_INSUFFICIENT; preserve evidence; no inferred private truth |
| pragmatics_research | INACTIVE_RESEARCH_ONLY / FROZEN | `hcl/pragmatics.py` | SIMPLIFY_NO_INCREMENT | never router-activated |  | LOW | SYSTEM_INSUFFICIENT; preserve evidence; no inferred private truth |
| value_research | INACTIVE_RESEARCH_ONLY / FROZEN | `hcl/value_perspective.py` | SIMPLIFY_NO_SEMANTIC_INCREMENT | never router-activated |  | LOW | SYSTEM_INSUFFICIENT; preserve evidence; no inferred private truth |
| narrative_research | INACTIVE_RESEARCH_ONLY / FROZEN | `hcl/narrative_order.py` | NO_GENERIC_TOOL_INCREMENT | never router-activated |  | LOW | SYSTEM_INSUFFICIENT; preserve evidence; no inferred private truth |
| historical_harnesses | INACTIVE_RESEARCH_ONLY / FROZEN | `eval/;scripts/;reports/` | CONSUMED_OR_INVALID_OR_INCONCLUSIVE | never runtime-imported |  | ZERO | SYSTEM_INSUFFICIENT; preserve evidence; no inferred private truth |
| longmemeval_sealed | INACTIVE_RESEARCH_ONLY / FROZEN | `eval/v05/` | SEALED_DEPRIORITIZED_32_ROWS | never access/trigger/consume; new owner scope required |  | ZERO | SYSTEM_INSUFFICIENT; preserve evidence; no inferred private truth |

Perspective/belief is the strongest retained specialized component; its historical fresh development signal is bounded, not general efficacy. v0.7/v0.8 are optional evidence infrastructure. v0.9/v0.10 are generic exact tools, not psychological superiority. Quantifier/witness/reading tools have correctness certificates without external semantic increment. Consumed harnesses and sealed LongMemEval are outside the import boundary.

CG-05 `cg05_local_concept`: OPTIONAL / RETAIN_DEVELOPMENT_ONLY; explicit speaker/context definitions and source-grounded applicability, counterexamples and local revision. Registry now contains 27 capabilities.

CG-02 registry disposition is INCONCLUSIVE_CLOSED, reflecting the consumed source-first closure; CG-04 is now development-only RETAIN after its one consumed frozen comparison; CG-05 is now also development-only RETAIN after its separate consumed comparison. Zero active implemented-unvalidated candidate slots. Lossless context transport is integration, not another capability candidate.

CG-01 registry disposition is SIMPLIFY_CLOSED for ordinary text, with optional source-validated typed checker efficacy inconclusive; no new pending candidate or historical reclassification.

CG04 source-first closure: bounded optional RETAIN, C26/P23/G25/H28/H-new26 of28, authored development-only, 20 calls, conservative USD0.03948384. No independent generalization claim or automatic activation expansion. [Receipt/closure](../reports/HCL_CG04_EXTERNAL_DEVELOPMENT_CLOSURE.md).

CG05 source-first closure: bounded optional RETAIN, C21/P23/G21/H28/H-new23 of28, authored development-only, 20 calls, conservative USD0.04263072. No independent generalization claim. NI10–14 remain provider-free correctness integrations with external utility INCONCLUSIVE, not five new validated cognition families. [Receipt/closure](../reports/HCL_CG05_EXTERNAL_DEVELOPMENT_CLOSURE.md).

[POST-CG05 disposition inventory](../reports/HCL_POST_CG05_CAPABILITY_DISPOSITIONS.json) includes v0.6, CG01–05 and NI10–14 without counting integration as new externally validated cognition. Current active unvalidated candidates0; new paid grants0.

## Current development integration — owner validation amendment 2026-10-01

The candidate-slot cap and per-capability immediate five-arm comparison are superseded
by the Master Plan; counts above are historical POST-CG05 snapshots. Registry27 remains
an executable inventory, not an external-validity count. A–H41/G-HC/G-ARCH carry
correctness/architecture evidence, not broad efficacy. NI10–14 are integrations.

Development Reality Checks are active; final sealed confirmation is separate and later.
DRC001 is development-only/attribution INCONCLUSIVE, checked treatment0/20; DRC002 is
INCONCLUSIVE/incomplete output-limit run, checked treatment0/13. Both grants closed,
no rerun or final evidence upgrade. Historical v0.6/CG01–05 dispositions unchanged.

[Shared reader v14](HCL_DEVELOPMENT_SHARED_READER_V14.md) is an
IMPLEMENTED_UNVALIDATED utility integration, not capability28: ordinary actual
B01/C01/C03 state can enter shared revision/challenge dependencies and a one-call
answer path. Positive/negative/composition/revision/smoke are authored correctness
evidence. Ordinary nonliteral conditional semantic entry is next; unsupported
semantics/private states remain unknown. LongMemEval SEALED_NOT_ACCESSED.
