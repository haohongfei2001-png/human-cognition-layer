# HCL Generic Answer-Loop Semantic Repair v0.1 — Fresh Failure Causal Diagnosis v0.1

Status: **PREDECLARED / DIAGNOSIS ONLY / NO BEHAVIOR CHANGE**

## Trigger

Fresh semantic-faithfulness validation under the frozen generic answer-loop
repair completed 12/12 cases with:

- semantic correct: 11/12;
- parser valid: 12/12;
- exact format: 12/12;
- runtime exceptions: 0.

The sole failure was `sf07_exact_positive_signal`:
- DIRECT_POSITIVE;
- A/B exact output;
- parser-valid wrong answer;
- first checker PASS;
- final checker PASS;
- no revision.

The fresh artifact does not contain enough state-level semantic evidence to
determine whether the first inversion was state, draft, or checker control.

## Frozen behavior

Behavior anchor:
`4ab45463bbeacbe3eb8eaa91be7ec908130ce980`

The following must remain unchanged during diagnosis:
- hcl/v03/answer_loop.py;
- hcl/v03/backends.py;
- state schema and frozen state semantics;
- fresh fixture file;
- original output-interface parser.

No prompt or runtime change is authorized until this diagnosis closes.

## Bounded fixtures

Target:
- `sf07_exact_positive_signal`

Matched fresh positive controls:
- `sf02_direct_positive_schedule`
  - same A/B exact-output family;
- `sf03_direct_positive_location`
  - positive direct-access case whose fresh state was EPISTEMIC.

Run exactly:
- target: 8 repetitions;
- control sf02: 8 repetitions;
- control sf03: 8 repetitions.

Total: exactly 24 full-pipeline repetitions.

Each repetition uses:
- deepseek-flash;
- seed 42;
- frozen current HCL behavior;
- a fresh backend / loop instance;
- no retries outside the normal HCL pipeline.

## State semantic probes

Probe metadata is diagnostic-only and must not be copied into the repair.

For each fixture, define:
- target agent;
- two required semantic terms that identify the directly observed/known fact.

State support is true if one item in the target agent's `observed` or
`knows` fields contains both required terms, case-insensitive.

The diagnostic source may contain these repository-owned synthetic probe terms.
Artifacts persist only booleans and hashes, never state text.

## Pipeline stages

Execute the unchanged HCL methods manually:

1. build_state
2. generate_draft
3. check(draft)
4. optional revise -> candidate
5. check(candidate)
6. optional second revise -> final

Score draft, candidate and final using the unchanged parser from
`run_info_state_output_interface_audit_v01.py`.

Persist only:
- parsed value;
- parser_valid;
- semantic_correct;
- exact_format;
- response_chars;
- state mode / uncertainty;
- state SHA-256;
- state-support booleans;
- checker status and violation type sets;
- revision booleans;
- first inversion stage.

No raw response text, state body, checker explanation or input text may be
persisted.

## First inversion stage

For every positive fixture:

1. STATE — state_supports_gold is false;
2. DRAFT — state supports gold but draft semantic answer is wrong;
3. FIRST_REVISION — draft is correct but candidate becomes wrong;
4. SECOND_REVISION — candidate is correct but final becomes wrong;
5. NONE — final path stays semantically correct.

Checker false-pass / false-revise counts are reported separately.

## Predeclared interpretation

Control stability is evaluated first.

### BROAD_POSITIVE_PIPELINE_INSTABILITY
Either control final success <=6/8.

### TARGET_STATE_DOMINANT
Both controls final success >=7/8 and target state support <=2/8.

### TARGET_DRAFT_DOMINANT
Both controls final success >=7/8,
target state support >=7/8,
and target first-inversion DRAFT >=5/8.

### TARGET_CHECKER_REVISION_DOMINANT
Both controls final success >=7/8,
target state support >=7/8,
target draft semantic success >=7/8,
and target final success <=2/8.

### TARGET_MIXED_CAUSAL_PATH
Both controls final success >=7/8,
target final success <=2/8,
and none of the dominant rules above apply.

### TARGET_FAILURE_LOW_REPEATABILITY
Both controls final success >=7/8 and target final success >=7/8.

Any runtime exception in more than 2 target repetitions or target-agent probe
failure in more than 2 target repetitions yields `DIAGNOSTIC_INCOMPLETE`.

## No rerun-until-pass

The diagnosis is fixed at 24 repetitions. Do not extend it based on intermediate
results.

## External-evidence boundary

Repository-owned synthetic fixtures only. No external benchmark evidence.

## Claim boundary

This diagnosis may localize the fresh semantic failure. It does not authorize a
repair until closure and cannot erase the failed fresh validation run.
