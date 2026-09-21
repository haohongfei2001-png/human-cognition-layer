# Decision Policy v0.2.1a — Ordinal 48 Consumed Diagnostic Confirmation

Status: **PREDECLARED / CONSUMED DIAGNOSTIC ONLY**

## Purpose

Test whether the owner-authorized Decision Policy output-budget amendment
(`4096 -> 8192`) removes the already-confirmed ordinal48
reasoning-output-budget exhaustion.

This is not:
- a fresh holdout;
- an efficacy test;
- a rescore of the original 8/10 holdout;
- permission to promote the old combo-3 slice.

## Fixed behavior

Behavior anchor:
`ce36d7e6f911910f97437c23455dee33e0e7bc82`

SOTOPIA smoke:
- run `35595222418`
- PASS
- behavior-anchor check PASS.

The only authorized behavior difference from pre-amendment HCL is:
- Decision Policy default `max_tokens=8192`.

## Fixed consumed setting

- environment ordinal: `9`
- combo ordinal: `3`
- expanded ordinal: `48`
- seed: `42`
- treatment only
- same `deepseek-flash` model/provider/endpoint/key
- pinned SOTOPIA commit unchanged
- same-provider evaluator repair unchanged
- both metadata-only diagnostic observers enabled
- maximum two episode attempts, stop after first success.

No retries, prompt, temperature, taxonomy, state semantics, Action Checker or
provider identity change is allowed.

## Predeclared success criterion

Primary diagnostic success:

1. at least one bounded episode completes successfully; and
2. no Decision Policy call ends in the exact frozen
   `no valid JSON after 3 attempts` RuntimeError.

Provider-level confirmation:

- Decision Policy calls must request `max_tokens=8192`;
- if any provider attempt still returns empty final content, preserve its
  finish reason/token metadata;
- a successful episode is sufficient to establish that the historical failure
  is not forced under the amended budget, but does not prove zero future
  stochastic failures.

## If failure reproduces

Do not increase budget or retries automatically.

Preserve metadata and classify:
- whether `reasoning_tokens=8192` with `finish_reason=length` again exhausts
  the new ceiling;
- whether malformed non-empty content dominates instead;
- whether any transport/provider exception occurs.

Any further behavior/cost amendment requires a new explicit decision.

## Claim boundary

Regardless of outcome:
- original post-repair holdout remains **8/10 INCOMPLETE**;
- ordinal48 remains consumed;
- this confirmation cannot restore freshness or create an efficacy result;
- no new holdout is automatically authorized.
