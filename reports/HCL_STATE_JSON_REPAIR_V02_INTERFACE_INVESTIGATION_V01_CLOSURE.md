# HCL State-JSON Repair v0.2 — Output-Interface Regression Investigation v0.1 Closure

## Decision

**STABLE_IO01_REGRESSION**

The bounded 8+8 repeatability investigation completed successfully and the
original output-interface regression reproduced strongly on the target fixture
while the matched control remained stable.

## Canonical run

- workflow: `HCL v0.2 Interface Regression Investigation v0.1`
- run: `35713019987`
- launch commit: `9b1e67f23d6af925abced2188b42af699081cd4c`
- terminal conclusion: **SUCCESS**
- preflight: **SUCCESS**
- bounded investigation: **SUCCESS**
- evidence artifact: `10688945137`
- artifact digest:
  `sha256:475013eec79d156dada22d80be34ed50418927a6a3f027fc4ff9dbe0745483e6`

Workflow success means the bounded investigation executed correctly; it does not
mean repair v0.2 passed all regressions.

## Frozen design

Exactly:
- 8 full-loop repetitions of target `io01_full_binary_direct_access`;
- 8 full-loop repetitions of control `io02_full_binary_missing_access`;
- deepseek-flash;
- seed 42;
- frozen repair-v0.2 behavior;
- no extra retries outside the normal HCL pipeline;
- original output-interface parser / fixture expectations unchanged.

No HCL behavior was changed during the investigation.

## Target result — io01

Gold: `yes`

Across 8 repetitions:
- parser + semantic success: **1 / 8**
- parser_valid: **6 / 8**
- semantic_correct: **1 / 8**
- exact_format: **5 / 8**
- runtime exceptions: **0**
- state mode: **EPISTEMIC in 8 / 8**
- distinct canonical state SHA-256 values: **8 / 8**
- revision_performed: **8 / 8**
- second_revision_performed: **6 / 8**
- final_check PASS: **2 / 8**

Parsed outcome distribution:
- correct `yes`: **1**
- wrong `no`: **5**
- parser-invalid: **2**

Therefore the failure is not merely formatting noise. Most repetitions produced
a parser-valid but semantically wrong binary answer.

## Control result — io02

Gold: `no`

Across 8 repetitions:
- parser + semantic success: **8 / 8**
- parser_valid: **8 / 8**
- semantic_correct: **8 / 8**
- exact_format: **8 / 8**
- runtime exceptions: **0**

This rules against a broad binary-output or general answer-loop collapse in this
bounded investigation.

## Predeclared interpretation

The interpretation was frozen before provider calls:

- broad instability if control <=6/8;
- stable io01 regression if control >=7/8 and target <=2/8;
- isolated stochastic instability if control >=7/8 and target 3-6/8;
- low-repeatability original failure if control >=7/8 and target >=7/8.

Observed:
- control = **8/8**
- target = **1/8**

Therefore:

**STABLE_IO01_REGRESSION**

## Relation to prior evidence

Repair v0.2 still retains a strong state-generation reliability result:

- canonical reliability run `35709921859`;
- **24 / 24** state builds succeeded;
- 0 state_json_exhaustion;
- 0 backend/other exceptions.

Post-reliability regressions:
- state fidelity: PASS;
- answer checker: PASS;
- output-interface: FAIL because full-loop was 7/8;
- sole original failure: io01.

This investigation shows that io01's failure is not a one-off event. It
reproduces as a fixture-specific output/semantic failure under the frozen v0.2
behavior.

## What this does and does not establish

Established:
- the io01 regression is stable under repeated frozen-v0.2 execution;
- the matched control does not show broad output instability;
- the failure is predominantly semantic (`no` instead of `yes`), not merely
  parser formatting;
- state mode classification remains EPISTEMIC, so the defect lies below the
  coarse mode label;
- state content is not deterministic across repeats (8 distinct state hashes),
  so a finer state-content diagnosis is required.

Not yet established:
- whether the wrong answer originates in the state content itself, the draft,
  checker calibration, revision, or their interaction;
- whether disabling thinking on state generation caused a systematic semantic
  loss for this class;
- whether a repair should modify state generation, checker/revision behavior, or
  output enforcement.

## Next canonical work

Do not close repair v0.2 yet.

The next work should be a targeted synthetic causal diagnosis of io01 under
frozen v0.2 behavior, designed to determine where the semantic inversion first
appears:

1. inspect/evaluate state-level facts relevant to direct information access;
2. determine whether the state says Priya observed/knows the code;
3. compare state verdict to draft answer;
4. compare checker verdict to the draft;
5. compare revision verdict to the final answer;
6. keep the matched control;
7. predeclare the diagnostic before provider calls.

No external benchmark evidence and no HCL behavior change are authorized until
that causal diagnosis closes.

## Claim boundary

This result establishes a stable synthetic fixture-specific regression under
repair v0.2. It does not establish external benchmark efficacy, cross-base
transfer, or HCL 1.0 certification.
