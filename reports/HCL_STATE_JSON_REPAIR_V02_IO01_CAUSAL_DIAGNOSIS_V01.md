# HCL State-JSON Repair v0.2 — io01 Causal Diagnosis v0.1

Status: **PREDECLARED / DIAGNOSIS ONLY / NO BEHAVIOR CHANGE**

## Trigger

Repair v0.2 passed state-generation reliability 24/24 and passed production-path
state fidelity plus the answer-checker regression.

It failed the output-interface regression on exactly one fixture:
`io01_full_binary_direct_access`.

A bounded repeatability investigation then established:
- target success: 1/8;
- matched control success: 8/8;
- target state mode EPISTEMIC: 8/8;
- no runtime exceptions.

The target regression is therefore stable and requires causal localization.

## Frozen behavior

Behavior anchor:
`37df0afaacfa819abafe1979002100c645fab1c2`

No HCL runtime file, schema, prompt, parser, or fixture may change during this
diagnosis.

## Fixtures and repetitions

Use exactly:
- target: `io01_full_binary_direct_access`, 8 repetitions;
- control: `io02_full_binary_missing_access`, 8 repetitions.

Each repetition uses a fresh backend and the full HCL pipeline under:
- deepseek-flash;
- seed 42;
- current repair-v0.2 behavior.

No extra retries beyond the normal HCL pipeline.

## Target state semantic probe

For the target fixture only, inspect the structured HCL state without
persisting its text.

The synthetic target token is extracted at runtime from the unchanged fixture;
it is not duplicated into diagnostic source or artifacts.

Locate the target agent by case-insensitive key match to the named target agent.

Record:
- target_agent_found;
- observed_contains_target_token;
- knows_contains_target_token;
- believes_contains_target_token;
- explicit_facts_contains_target_token;
- summary_contains_target_token.

Predeclared state support rule:

`state_supports_gold = observed_contains_target_token OR knows_contains_target_token`

If the target agent is absent, `state_supports_gold=false`.

## Pipeline stages

Execute manually using unchanged HCL methods:

1. `build_state`
2. `generate_draft`
3. `check` on draft
4. optional `revise` -> candidate
5. `check` on candidate
6. optional second `revise` -> final

Score draft, candidate, and final with the unchanged binary parser from the
original output-interface audit.

For each stage persist only:
- parsed value;
- parser_valid;
- semantic_correct;
- exact_format;
- response_chars.

For each checker persist only:
- status;
- violation type set.

## Derived diagnostic signals

Per target repetition derive:

- state_semantic_loss
- draft_inversion
- first_check_false_pass
- first_check_false_revise
- first_revision_failed_to_correct
- first_revision_inversion
- final_check_false_pass
- final_check_false_revise
- second_revision_failed_to_correct
- second_revision_inversion

## First inversion stage

For the target classify the first semantic break in this order:

1. `STATE` if state_supports_gold is false;
2. `DRAFT` if state supports gold but draft is wrong;
3. `FIRST_REVISION` if draft is correct but candidate is wrong;
4. `SECOND_REVISION` if candidate is correct but final is wrong;
5. `NONE` if the semantic path remains correct.

Checker false-pass/false-revise signals are reported separately.

## Predeclared causal interpretation

Control final success <=6/8 takes precedence and yields:
`BROAD_PIPELINE_INSTABILITY`.

Otherwise evaluate target:

A. `STATE_DOMINANT`
- state_semantic_loss >=5/8.

B. `DRAFT_DOMINANT`
- state_semantic_loss <=2/8;
- first inversion stage DRAFT >=5/8.

C. `REVISION_DOMINANT`
- state_semantic_loss <=2/8;
- first inversion at FIRST_REVISION or SECOND_REVISION totals >=5/8.

D. `CHECKER_CONTROL_FAILURE`
- state_semantic_loss <=2/8;
- checker false-pass or false-revise signals occur in >=5/8;
- and no earlier A/B/C condition applies.

E. `MIXED_CAUSAL_PATH`
- none of A-D applies, but target final success remains <=2/8.

F. `NOT_REPRODUCED_IN_CAUSAL_RUN`
- target final success >=7/8.

Any runtime exception or target-agent probe failure in more than 2 target
repeats yields `DIAGNOSTIC_INCOMPLETE`.

## Content-free boundary

Persist:
- fixture ID and repetition;
- stage parse/semantic booleans and response lengths;
- state probe booleans;
- state SHA-256;
- checker statuses and violation type sets;
- derived diagnostic signals;
- first inversion stage.

Do not persist:
- input text;
- synthetic target-token text;
- draft/candidate/final text;
- state body;
- checker explanations;
- revision instructions;
- credentials;
- exception text.

## Execution

Run exactly 16 repetitions total with at most 4 workers.

No rerun-until-pass and no extension after intermediate results.

## External-evidence boundary

Repository-owned synthetic fixtures only. No external benchmark evidence.

## Claim boundary

This diagnosis may localize the first semantic inversion inside the HCL
state/draft/checker/revision pipeline. It does not authorize a repair until
closure.
