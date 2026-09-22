# HCL State-JSON Repair v0.2 — io01 Causal Diagnosis v0.1 Closure

## Decision

**DRAFT_DOMINANT**

The bounded causal diagnosis completed all 16 frozen synthetic repetitions and
localized the primary semantic inversion to the draft-generation stage.

The target state itself consistently supported the gold answer. The matched
control remained stable.

## Canonical run

- workflow: `HCL v0.2 io01 Causal Diagnosis v0.1`
- run: `35715326584`
- launch commit: `5b688bb620cd39ce82a223a47b6fc3ebcf1fae83`
- terminal conclusion: **SUCCESS**
- preflight: **SUCCESS**
- diagnosis: **SUCCESS**
- artifact: `10688104138`
- digest:
  `sha256:154e92c9aa3b156a74b42a2256946d7663718bf0821ea912343e8fd518f3aa4a`

Workflow success means evidence collection completed correctly. It does not mean
repair v0.2 has passed all regressions.

## Target — io01

Across 8 repetitions:

- runtime exceptions: **0**
- target agent found: **8 / 8**
- state mode: **EPISTEMIC in 8 / 8**
- state supports gold answer: **8 / 8**
- distinct normalized-state hashes: **8 / 8**
- final parser+semantic success: **2 / 8**

First semantic inversion:
- STATE: **0 / 8**
- DRAFT: **5 / 8**
- FIRST_REVISION: **3 / 8**
- SECOND_REVISION: **0 / 8**
- NONE: **0 / 8**

Therefore, by the predeclared interpretation rule:

**DRAFT_DOMINANT**

## State-level finding

The target-state probe was positive in every repetition.

In all 8 target runs the structured state contained direct support for the gold
answer through at least one of the target agent's observed/knows fields.

Therefore the stable regression is not explained by loss of the direct-access
fact in the structured cognition state.

## Draft-level finding

In **5 / 8** target repetitions:
- the state supported the gold answer;
- the first user-facing draft was already semantically wrong.

This is the dominant first-inversion path.

## Revision/checker secondary findings

The diagnosis also found substantial secondary control failures:

- first_check_false_revise: **3 / 8**
  - the draft was semantically correct but the first checker still requested
    revision;

- first_revision_inversion: **3 / 8**
  - those revisions changed a correct draft into an incorrect candidate;

- first_revision_failed_to_correct: **5 / 8**
  - when the draft was already wrong, the first revision failed to restore the
    correct semantics;

- final_check_false_pass: **4 / 8**
  - an incorrect candidate was accepted as PASS by the final checker;

- second_revision_failed_to_correct: **2 / 8**
  - even when a second revision was triggered, it failed to recover the correct
    answer.

Thus the primary first inversion is draft generation, but repair design must
also preserve against checker/revision paths that can introduce or fail to
correct semantic errors.

## Matched control

Control `io02_full_binary_missing_access`:

- final success: **8 / 8**
- draft correct: **8 / 8**
- first checker PASS: **8 / 8**
- final checker PASS: **8 / 8**
- no revisions needed.

This argues against a broad binary-output or general answer-loop collapse.

## Consequence for repair design

Repair v0.2 cannot close as-is.

The next repair design must target the answer-generation/control path while
preserving the already successful state-generation reliability repair.

The evidence does **not** justify reverting the non-thinking state-generation
fix:
- state generation passed 24/24 reliability;
- state fidelity regression passed;
- target state semantic probe supported the gold answer 8/8.

A valid next repair should therefore be scoped below the state layer and should
address:

1. draft faithfulness to explicit state-level observed/knows evidence;
2. checker protection against revising a semantically correct direct answer;
3. revision protection against inverting an already-correct answer;
4. final checker rejection of an incorrect candidate.

Any repair must remain generic and derived from abstract information-access
semantics. It must not special-case io01 or its literal token.

## Boundaries

Do not:
- tune against consumed external benchmark rows;
- special-case io01 text or token;
- alter frozen state semantics/schema;
- undo the v0.2 non-thinking state JSON repair without contrary evidence;
- weaken the existing output-interface regression gate;
- consume new external benchmark evidence before synthetic repair/regression
  closure.

## Next gate

Predeclare a generic answer-loop semantic-faithfulness repair focused on direct
information access, with zero-provider invariants and independent synthetic
validation before any broader regression rerun.

## Claim boundary

Supported:
- target state semantics are intact for this causal slice;
- the dominant first semantic inversion occurs at draft generation;
- checker/revision behavior contributes secondary errors.

Not supported:
- external benchmark efficacy;
- generalization beyond the tested synthetic class;
- HCL 1.0 certification.
