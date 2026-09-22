# HCL Fresh Semantic Failure Causal Diagnosis v0.1 — Closure

## Decision

**TARGET_DRAFT_DOMINANT**

The bounded fresh causal diagnosis completed 24/24 frozen repetitions and
localized the remaining fresh semantic failure to draft generation.

## Canonical run

- workflow: `HCL Fresh Semantic Failure Causal Diagnosis v0.1`
- run: `35718992914`
- launch commit: `48786d195908044a8d37b42f7fd266fda9e76e74`
- terminal conclusion: **SUCCESS**
- artifact: `10690876098`
- digest:
  `sha256:551654b9b9e8964acf555eb6b9ec755c5210f1c0f37eb489aec5ba7c0ea413ea`

## Target result

Target:
`sf07_exact_positive_signal`

Across 8 repetitions:

- completed: **8/8**
- runtime exceptions: **0**
- target agent found: **8/8**
- state direct support for gold semantics: **8/8**
- draft semantic success: **0/8**
- final semantic success: **0/8**

First inversion:
- STATE: **0**
- DRAFT: **8**
- FIRST_REVISION: **0**
- SECOND_REVISION: **0**
- NONE: **0**

Therefore the predeclared interpretation is:

**TARGET_DRAFT_DOMINANT**

## Checker / revision control findings

Across the 8 target runs:

- first checker false-pass on an incorrect draft: **6/8**
- final checker false-pass on an incorrect candidate: **7/8**
- when revision was triggered, it did not recover the correct semantics.

Thus the primary inversion is draft generation, with checker control failing to
detect or recover it in most runs.

## Controls

A/B direct-positive control:
`sf02_direct_positive_schedule`

- state support: **8/8**
- draft success: **8/8**
- final success: **8/8**
- first inversion NONE: **8/8**

EPISTEMIC direct-positive control:
`sf03_direct_positive_location`

- state support: **8/8**
- draft success: **8/8**
- final success: **8/8**
- first inversion NONE: **8/8**

This rules against:
- broad A/B output failure;
- broad EPISTEMIC direct-positive failure;
- broad answer-loop collapse.

## Remaining ambiguity

The target state includes direct observed/knows support, but the target also
consistently enters EPISTEMIC mode with medium uncertainty.

The content-free diagnosis does not reveal whether other state fields contain
competing hypotheses, missing bridges, or uncertainty text that the draft model
incorrectly treats as overriding direct evidence.

Before another repair changes answer prompts or pipeline logic, inspect the
repository-owned synthetic target state's internal field consistency.

## Next canonical work

Run a bounded synthetic state-conflict audit on:
- target sf07;
- control sf02;
- control sf03.

The audit may persist the synthetic state bodies because the fixtures are
repository-owned and contain no user/private data.

It must determine whether the structured state simultaneously contains:
- direct observed/knows evidence for the gold proposition;
- contradictory hypotheses, missing bridges, or summary/uncertainty claims that
  deny or weaken that same direct proposition.

No answer-loop behavior change is authorized before that audit closes.

## Boundaries

Do not:
- rerun the failed fresh validation as fresh evidence;
- alter state semantics/schema;
- special-case target fixture text in a repair;
- consume new external benchmark evidence.

## Claim boundary

Supported:
- the remaining fresh failure is stable and draft-dominant;
- target state direct-evidence fields support the gold answer 8/8;
- checker control also fails frequently.

Not yet supported:
- whether the root cause is contradictory state content versus answer-model
  weighting of a non-contradictory medium-uncertainty state.
