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

### A. Isolated stochastic interface instability
All are true:
- io01 has at least one pass and at least one fail across 8 repeats;
- io02 passes parser+semantic gate at least 7/8;
- io01 state mode remains EPISTEMIC in all completed repeats;
- no runtime exception prevents completion.

This establishes output-interface instability under frozen behavior. It does
not authorize weakening the existing 8/8 regression gate.

### B. Stable io01 regression
io01 parser+semantic success is <=2/8 while io02 is >=7/8.

This supports a reproducible fixture-specific regression and requires a
separate repair investigation before v0.2 can close.

### C. Broad output instability
io02 parser+semantic success is <=6/8, or both fixtures show repeated failures.

This supports broader answer/checker/revision instability and blocks repair
closure.

### D. One-off failure not reproduced
io01 and io02 each pass parser+semantic gate >=7/8, with no more than one io01
failure.

This supports a transient provider/output event. The original failed regression
remains historical evidence; repair v0.2 still cannot close automatically.
A separate, predeclared full regression confirmation would then be required.

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
