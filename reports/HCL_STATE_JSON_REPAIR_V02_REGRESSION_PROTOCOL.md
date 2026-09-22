# HCL State-JSON Repair v0.2 — Post-Reliability Regression Protocol

Status: **PREDECLARED / REGRESSION ONLY**

## Trigger

State-JSON reliability repair v0.2 passed its strict independent synthetic gate:

- canonical run: `35709921859`;
- 24 / 24 frozen reliability fixtures succeeded;
- 0 state_json_exhaustion;
- 0 backend/other exceptions;
- all six strata: 4 / 4;
- 23 cases succeeded on HCL attempt 1;
- 1 long/recursive case succeeded on HCL attempt 2.

Reliability success alone is insufficient for repair closure.

## Frozen repair under regression

Behavior anchor:

`37df0afaacfa819abafe1979002100c645fab1c2`

The only runtime change from failed repair v0.1 is the state-JSON request
override:

`extra_body={"thinking":{"type":"disabled"}}`

No regression job may alter HCL behavior.

## Regression A — state fidelity

Use the existing frozen fixture set:

`eval/state_fidelity/fixtures_v01.json`

Use the existing evaluator semantics from:

`scripts/run_hcl_v03_state_fidelity.py`

Important execution correction:

The historical runner constructs its own direct provider request and therefore
does not exercise the repaired production state path. For this repair
regression only, a wrapper must reuse the same fixtures and the same
`evaluate_fixture()` evaluator but obtain each state through:

`HCLAnswerLoop.build_state()`

with `OpenAICompatibleBackend`.

Pass gate:
- every non-excluded/gated fixture passes the existing evaluator;
- schema-valid rate on gated fixtures is 100%.

No expected labels may change.

## Regression B — answer checker / revision loop

Run the existing unchanged runner:

`scripts/run_hcl_v03_answer_checker.py`

against the existing unchanged fresh fixture set:

`eval/answer_loop/checker_fixtures_v02_fresh.json`

with:
- model: deepseek-flash;
- workers: 4.

Pass gate:
- runner exits 0;
- all fixtures pass its existing status / violation-family / final-check gate;
- failed count is 0.

## Regression C — information-state/output-interface audit

Reuse unchanged:

- `scripts/run_info_state_output_interface_audit_v01.py`
- `eval/answer_loop/info_state_output_interface_v01.json`

The original audit protocol remains unchanged. Only the HCL behavior anchor is
updated to the v0.2 repaired behavior for this regression rerun.

Pass gate:
- all 16 fixtures execute;
- full_loop semantic_correct = 8/8;
- full_loop parser_valid = 8/8;
- forced_revision semantic_correct = 8/8;
- forced_revision parser_valid = 8/8;
- `abstract_interface_defect_established == false`.

## Zero-provider gate

Before provider calls:
- repair v0.2 runtime tests must pass;
- repair v0.2 validation tests must pass;
- historical interface parser unit/static checks must compile;
- HCL behavior files must match the v0.2 behavior anchor.

## External-evidence boundary

These regressions use repository-owned synthetic fixtures only.

No new Hi-ToM, FANToM, SOTOPIA, or other external benchmark evidence is
authorized by this protocol.

## Closure rule

Repair v0.2 may close as reliability-repaired only if:

1. 24/24 reliability gate already passed;
2. state-fidelity regression passes;
3. answer-checker regression passes;
4. output-interface regression passes;
5. relevant zero-provider tests pass.

Any regression failure blocks closure and must be investigated without changing
the frozen repair candidate mid-run.
