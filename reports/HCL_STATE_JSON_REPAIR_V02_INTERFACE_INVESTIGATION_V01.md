# HCL State-JSON Repair v0.2 — Output-Interface Regression Investigation v0.1

Status: **PREDECLARED / INVESTIGATION ONLY / NO BEHAVIOR CHANGE**

## Trigger

State-JSON reliability repair v0.2 passed its strict 24/24 synthetic reliability
gate, then failed the post-reliability regression workflow `35710695556` only
on the information-state/output-interface regression.

Passed in the same workflow:
- production-path state fidelity: PASS;
- answer-checker regression: PASS;
- zero-provider gates: PASS.

Failed:
- output-interface full_loop: 7/8 instead of required 8/8;
- forced_revision: 8/8.

The sole failing fixture was:
`io01_full_binary_direct_access`.

Observed v0.2 regression result for io01:
- expected binary gold: yes;
- parser_valid: false;
- semantic_correct by benchmark parser: false;
- response_chars: 48;
- state mode: EPISTEMIC;
- uncertainty: medium;
- first checker: REVISE;
- final checker: PASS;
- first revision performed: true;
- second revision performed: false.

Original independent audit result for the same unchanged fixture:
- parsed: yes;
- semantic_correct: true;
- exact_format: true;
- state mode: EPISTEMIC;
- uncertainty: medium;
- first checker: REVISE;
- final checker: REVISE;
- first revision performed: true;
- second revision performed: true.

This pattern suggests the regression may lie in stochastic checker/revision
output-interface behavior rather than cognition-state semantics, but one run is
insufficient to establish that.

## Frozen behavior

Investigation must not change HCL runtime behavior.

Behavior anchor:
`37df0afaacfa819abafe1979002100c645fab1c2`

The following must remain unchanged:
- backends.py;
- answer_loop.py;
- state schema and frozen semantics;
- repair v0.2 thinking-disabled state path;
- output-interface fixture file and parser.

## Fixtures

Target:
- `io01_full_binary_direct_access`

Matched stable control:
- `io02_full_binary_missing_access`

The control is included to detect broad provider/output instability. No fixture
text or expected answer may change.

## Bounded repeatability design

Run exactly:
- 8 independent full-loop repetitions of io01;
- 8 independent full-loop repetitions of io02.

Each repetition:
- uses deepseek-flash;
- seed 42;
- current frozen v0.2 HCL behavior;
- fresh backend / loop instance;
- same parser and scoring semantics as the original output-interface audit.

No retries outside the normal HCL pipeline are permitted.

## Persisted content-free evidence

For every repetition persist:
- fixture ID;
- repetition index;
- gold;
- parsed value;
- parser_valid;
- semantic_correct;
- exact_format;
- response character count;
- state mode;
- uncertainty level;
- SHA-256 of canonical normalized state JSON;
- first checker status;
- final checker status;
- revision_performed;
- second_revision_performed.

Do not persist:
- input text;
- final-answer text;
- draft text;
- state body;
- checker explanations;
- credentials.

## Predeclared interpretation

Use `parser_valid && semantic_correct` as the repetition success gate.

Interpretation is mutually exclusive and evaluated in this order:

### C. Broad output instability
io02 control success is <=6/8.

This supports broader answer/checker/revision instability and blocks repair
closure.

### B. Stable io01 regression
io02 control success is >=7/8 and io01 success is <=2/8.

This supports a reproducible fixture-specific regression and requires a
separate repair investigation before v0.2 can close.

### A. Isolated stochastic interface instability
io02 control success is >=7/8 and io01 success is 3-6/8.

This establishes material output-interface instability under frozen behavior.
It does not authorize weakening the existing 8/8 regression gate.

### D. Original failure has low repeatability
io02 control success is >=7/8 and io01 success is >=7/8.

This supports a transient/low-repeatability provider-output event rather than a
stable fixture-specific regression. The original failed regression remains
historical evidence; repair v0.2 still cannot close automatically. A separate,
predeclared full regression confirmation would then be required.

For A/B/D, io01 state mode must remain EPISTEMIC in every successfully executed
repeat. Any runtime exception or unexpected state-mode drift is reported
separately and blocks automatic progression.

## No rerun-until-pass

This investigation is bounded to 16 repetitions fixed in advance. It must not be
extended because of intermediate results.

## External-evidence boundary

Repository-owned synthetic fixtures only. No Hi-ToM, FANToM, SOTOPIA, or other
external benchmark evidence is authorized.

## Claim boundary

This investigation may distinguish stable regression from stochastic output
instability. It cannot establish external efficacy or erase the original failed
regression run.
