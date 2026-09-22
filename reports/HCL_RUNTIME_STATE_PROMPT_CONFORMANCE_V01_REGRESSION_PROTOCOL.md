# HCL Runtime State-Prompt Conformance Repair v0.1 — Full Synthetic Regression Protocol

Status: **PREDECLARED / REGRESSION ONLY**

## Trigger

Runtime direct-communication prompt conformance repair:
- behavior anchor:
  `da09c1fc8b82a538f6b0fdbbbe101e58b839241b`
- fresh communication boundary:
  - raw 7/10;
  - adjudicated semantic conformance 10/10;
  - three raw failures transparently classified as evaluator/fixture false
    negatives;
- no behavior change occurred during adjudication.

Boundary success is insufficient for repair closure.

## Frozen behavior

The regression must use exactly the behavior anchored at:

`da09c1fc8b82a538f6b0fdbbbe101e58b839241b`

No regression job may alter:
- answer_loop.py;
- backends.py;
- state schema;
- frozen state semantics.

This anchor includes:
- state JSON non-thinking repair v0.2;
- generic answer-loop semantic-faithfulness prompt repair v0.1;
- runtime direct-communication STATE_SYSTEM conformance repair v0.1.

## Stage 1 — state-generation reliability

Reuse unchanged:
- `eval/answer_loop/state_generation_reliability_v01.json`
- `scripts/run_state_json_repair_validation_v02.py`
- `scripts/aggregate_state_json_repair_validation_v02.py`

Execution:
- 24 frozen independent synthetic cases;
- 6 shards x 4;
- max parallelism 3.

Strict pass gate:
- 24/24 success;
- 0 state_json_exhaustion;
- 0 backend/other exception;
- all state attempts use structured JSON path.

If this stage fails, all later provider-backed regressions are blocked.

## Stage 2 — four parallel regressions

Run only after Stage 1 passes.

### A. Fresh semantic-faithfulness answer suite

Reuse unchanged:
- `eval/answer_loop/semantic_faithfulness_fresh_v01.json`
- `scripts/run_generic_answer_loop_semantic_repair_v01.py`

Pass:
- 12/12 semantic correct;
- 12/12 parser valid;
- all exact-output cases exact;
- 0 runtime exceptions.

### B. Original information-state/output-interface audit

Reuse unchanged:
- `eval/answer_loop/info_state_output_interface_v01.json`
- `scripts/run_info_state_output_interface_audit_v01.py`

Pass:
- full_loop semantic 8/8;
- full_loop parser 8/8;
- forced_revision semantic 8/8;
- forced_revision parser 8/8;
- abstract_interface_defect_established=false.

### C. Production-path state fidelity

Reuse:
- `eval/state_fidelity/fixtures_v01.json`
- `scripts/run_hcl_v03_state_fidelity_repair_v02.py`
- existing evaluator semantics from `scripts/run_hcl_v03_state_fidelity.py`.

Pass:
- gated failed=0;
- pass_rate=1.0;
- schema_valid_rate=1.0.

### D. Existing answer-checker fresh suite

Reuse unchanged:
- `eval/answer_loop/checker_fixtures_v02_fresh.json`
- `scripts/run_hcl_v03_answer_checker.py`

Pass:
- failed=0;
- passed=fixture_count;
- pass_rate=1.0.

## Closure rule

Runtime state-prompt conformance repair v0.1 and the currently stacked generic
answer-loop semantic repair may close synthetically only if:

1. Stage 1 state reliability passes;
2. all four Stage 2 regressions pass;
3. relevant zero-provider freeze/invariant tests pass.

Any provider-backed failure is canonical evidence and blocks closure.

## No rerun-until-pass

Do not rerun a failed frozen regression as fresh evidence under the same
behavior merely to obtain a green result.

Investigate first; any behavior/evaluator change requires a separate,
predeclared next round.

## External-evidence boundary

No Hi-ToM, FANToM, SOTOPIA, or other external benchmark calls.

Fresh external evidence remains blocked until this synthetic closure succeeds.

## Claim boundary

Passing this regression gate establishes only synthetic closure for the repaired
HCL v0.3 runtime under the current DeepSeek instantiation.

It does not establish external benchmark efficacy, cross-base transfer, or HCL
1.0 certification.
