# HCL v0.4 — Evaluation Exposure Register

Status: **CANONICAL EXPOSURE ACCOUNTING / PHASE 0**

Purpose:

This register prevents previously observed benchmark evidence from being relabeled
as fresh evidence during HCL v0.4.

It summarizes the exposure boundary at the benchmark/task-family level. Exact
historical run IDs, selection manifests and raw evidence remain in `STATUS.md`,
`reports/` and `eval/`.

## Rules

1. Once provider-backed evaluation begins on a selected row/setting, that
   evidence is consumed for fresh-efficacy purposes.
2. A failed run can still consume evidence if model/provider execution began.
3. Rephrasing an observed failure into an abstract rule does not restore
   freshness.
4. Previously seen environment templates cannot be called fresh-scenario
   evidence merely because a new persona/pairing is used.
5. Public literature review does not itself consume benchmark rows, but no
   benchmark execution may start during the open Phase 0 gate.
6. v0.4 development must not use consumed benchmark content as tuning data.

## CogToM

Status: **EXPOSED / DEVELOPMENT-DIAGNOSTIC ONLY**

Historical use includes:
- representative 200-group baseline across all 46 subcategories;
- HCL v0.1 disjoint 100-group experiment;
- additional diagnostic/regression use.

Phase-0 rule:

> Treat CogToM as historically exposed. Do not use it as v0.4 fresh
> generalization evidence.

It may be used only for explicitly labeled historical regression or analysis
whose interpretation does not rely on freshness.

## SOTOPIA-Hard

Status: **ENVIRONMENT TEMPLATES EXPOSED; MULTIPLE PERSONA/COMBO SLICES CONSUMED**

Historical use includes:
- initial fixed 10-setting paired diagnostic slice;
- environment ordinals 10–19 paired holdout with repeat seeds;
- expanded Hard inventory proving 20 environment positions × 5 combinations;
- multiple previously unused persona/pairing combo slices;
- the Decision Policy v0.2.1 combo-3 slice, where all ten attempted
  combinations became consumed despite an 8/10 incomplete execution result;
- additional consumed-setting diagnostic replays.

Critical freshness boundary already established by the project:

> all SOTOPIA-Hard environment templates have been seen.

Therefore:

- remaining unused persona/pairing combinations, if any, are **not**
  fresh-scenario evidence;
- SOTOPIA may remain useful as a development or robustness environment;
- it must not be presented as sealed v0.4 scenario-level external
  generalization evidence.

## FANToM

Status: **80 DISTINCT CONVERSATIONS CONSUMED ACROSS v0.1/v0.2**

### FANToM v0.1

- 32 questions;
- 32 distinct conversations;
- short-context paired evaluation;
- final interpretation: MIXED / INCONCLUSIVE;
- all selected conversations consumed.

### FANToM v0.2

- 48 questions;
- 48 distinct full-context conversations;
- zero conversation overlap with v0.1;
- final interpretation: MIXED / INCONCLUSIVE;
- all selected conversations consumed.

Phase-0 rule:

> The 80 consumed FANToM conversations may not be used for tuning or relabeled
> as fresh evidence after any v0.4 mechanism change.

Any future FANToM use would require a separately audited, disjoint selection and
would still need to satisfy the new Phase-0 mechanism/evaluation design. No such
execution is currently authorized.

## Hi-ToM

Status: **60 SELECTED STORIES/ROWS CONSUMED**

Hi-ToM v0.1:
- 60 questions / 60 distinct stories;
- orders 0–4;
- paid paired execution began;
- 36 rows completed;
- 24 RuntimeError failures;
- efficacy result: INCOMPLETE / NOT EVALUABLE.

Because provider-backed execution began:

> all 60 selected Hi-ToM rows are consumed.

They may not be rerun as fresh efficacy evidence and may not be used for v0.4
mechanism tuning.

## Repository-owned synthetic suites

Status: **ENGINEERING / CAPABILITY INSTRUMENTS, NOT EXTERNAL EFFICACY EVIDENCE**

Existing synthetic suites remain useful for:
- regression;
- parser/schema/retry reliability;
- frozen-contract conformance;
- bounded capability checks.

They are not evidence that:
- the cognition theory is correct;
- HCL improves broad human cognition;
- HCL transfers across models or tasks.

A v0.4 mechanism may create new independent synthetic capability tests, but
those tests cannot become the primary research efficacy result.

## External literature-reviewed but not executed in v0.4

The Phase-0 literature review currently includes public work such as:
- BeliefBank;
- TimeToM;
- ThoughtTracing / Hypothesis-Driven ToM;
- Hypothetical Minds;
- AutoToM;
- DynToM;
- newer 2026 belief-dynamics / social-agent work.

Reading papers or benchmark documentation is not a provider-backed benchmark
consumption event.

However, **no new external benchmark execution is authorized while Phase 0 is
open**.

## Freshness claim vocabulary for v0.4

Use these labels precisely:

- **fresh scenario** — the scenario/task structure was sealed and unseen by the
  development process;
- **fresh combination** — a new pairing/persona/configuration inside an already
  seen scenario/template;
- **cross-seed repeat** — same evaluation unit under a different predefined
  stochastic seed;
- **diagnostic replay** — already consumed evidence, never fresh efficacy;
- **synthetic independent test** — repository-owned capability check, not
  external generalization evidence;
- **sealed external evaluation** — externally sourced evidence whose selected
  units and statistical plan were frozen before outcomes were observed.

## Current Phase-0 rule

Until the v0.4 research question, nearest-neighbor gap, comparison contract and
statistical/evaluation protocol are frozen:

**DO NOT CONSUME ANY NEW EXTERNAL BENCHMARK ROWS.**
