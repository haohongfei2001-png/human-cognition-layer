# HCL Info-State / Output-Interface Synthetic Audit v0.1 — Closure

## Decision

**NO ABSTRACT PARSER/INTERFACE DEFECT ESTABLISHED**

This conclusion follows the predeclared audit gate.

## Canonical run

- workflow: `HCL Info-State Output-Interface Audit v0.1`
- run: `35613640456`
- launch commit: `3ad8f018772d7b60a91829db5f654a2f482b88ec`
- result: **SUCCESS**
- artifact: `10645726589`
- artifact SHA-256:
  `edb86e1cb469510c3243a5015032c8450bbcf7cd41c56e061f8441ad7c8f9bff`

Fixture boundary:
- 16 independent synthetic fixtures;
- 8 complete HCL answer-loop cases;
- 8 forced-revision cases;
- unrelated domains;
- no FANToM or SOTOPIA content reused.

Frozen behavior:
- HCL v0.3 state semantics unchanged;
- answer loop unchanged;
- model/provider/seed unchanged.

## Full-loop raw result

- n = **8**
- semantic correct = **8/8**
- semantic accuracy = **100%**
- parser-valid = **8/8**
- parser-valid rate = **100%**
- exact requested format = **8/8**
- exact-format rate = **100%**
- final-check PASS = **7/8**
- final-check PASS rate = **87.5%**

One full-loop case had a correct, parser-valid, exact-format final answer while
its final checker status was REVISE. This is a checker-calibration/strictness
signal, not an output-interface failure under the predeclared gate.

## Forced-revision raw result

- n = **8**
- initial checker REVISE hit = **8/8**
- checker REVISE rate = **100%**
- semantic correct after revision = **8/8**
- parser-valid after revision = **8/8**
- exact requested format = **7/8**
- final-check PASS = **8/8**

The sole exact-format miss:
- `io13_revision_binary_answerability`
- semantic verdict: correct;
- deterministic yes/no parser: valid;
- final checker: PASS;
- exact-only format: false.

The audit deliberately separated parser-valid format from exact-only formatting.
This miss therefore does not satisfy the predeclared abstract-defect criterion.

## Predeclared defect gate

A repeatable abstract defect required any of:

1. final answer not parser-valid under the required categorical interface;
2. forced revision fixes semantics but loses parser-valid format;
3. final checker PASS accepts a revised answer that violates the parser-valid
   categorical interface.

Observed:
- parser-invalid final answers: **0**
- forced-revision parser-invalid outputs: **0**
- final-check PASS + parser-invalid outputs: **0**
- semantic failures: **0**

Therefore:

**abstract_interface_defect_established = false**

## Relation to FANToM v0.2

FANToM v0.2 contained one HCL-worsened answerability item whose normalized
prediction was null after both revision passes.

This independent audit does **not reproduce** that failure class:
- all 16 final outputs are parser-valid;
- all 16 are semantically correct.

Therefore the consumed FANToM item is insufficient evidence for a general
answer-loop parser/format defect and must not be used to justify a behavioral
repair.

The second FANToM information-state regression (yes -> no) also does not
establish a general state-semantic defect in this audit. Independent synthetic
information-access fixtures were semantically correct.

## Secondary signals

Two non-gating observations remain:

1. **checker strictness / false-positive signal**
   - one full-loop exact, semantically correct answer received final-check
     REVISE.

2. **exact-format discipline signal**
   - one forced revision was semantically correct and parser-valid but not
     exact-only format.

Neither establishes a behavior-bearing defect under the frozen gate.

Do not tune HCL based on either single fixture.

## Decision

No HCL state, answer-loop, checker, prompt, parser, token budget or retry policy
is changed by this audit.

FANToM v0.1/v0.2 remain consumed external evidence.

## Next methodological direction

Because:
- FANToM v0.2 produced a small favorable inaccessible-belief signal (+1 net);
- independent interface audit does not establish the suspected parser defect;
- no repair is justified;

the next high-value external question is whether the belief signal transfers to
a benchmark designed specifically for **higher-order recursive Theory of Mind**.

A suitable next source is Hi-ToM:
- independent dataset;
- Apache-2.0;
- 1.2k higher-order ToM QA pairs;
- ToM order 0 through 4;
- communication / no-communication variants;
- no new provider credential is required for a bounded paired DeepSeek-vs-HCL
  pilot.

Hi-ToM must first undergo zero-provider inventory and deterministic
predeclaration before any model call.
