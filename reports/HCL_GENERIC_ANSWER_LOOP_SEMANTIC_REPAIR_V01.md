# HCL Generic Answer-Loop Semantic Faithfulness Repair v0.1

Status: **PREDECLARED / IMPLEMENTATION AUTHORIZED AFTER CAUSAL DIAGNOSIS**

## Trigger

Repair v0.2 fixed state-generation reliability:
- 24/24 frozen reliability fixtures passed;
- state-fidelity regression passed.

The remaining blocker is answer-loop semantic faithfulness.

Causal diagnosis on the stable synthetic direct-information-access regression
established:
- target state supported the gold semantics in 8/8;
- first semantic inversion occurred at DRAFT in 5/8;
- first semantic inversion occurred at FIRST_REVISION in 3/8;
- checker/revision secondary failures were also observed;
- matched control remained 8/8.

Therefore the repair must preserve the successful state path and operate only
below the state layer.

## Frozen HCL components

This repair must not change:
- hcl/v03/FROZEN_STATE_SEMANTICS.md;
- hcl/v03/state_schema.json;
- STATE_SYSTEM;
- build_state() control flow;
- state max_tokens;
- repair-v0.2 thinking-disabled state request;
- state retry budgets;
- Decision Policy;
- Action Checker.

Consumed Hi-ToM / FANToM / SOTOPIA content is forbidden.

## Generic repair contract

Only these answer-loop instruction constants may change:
- DRAFT_SYSTEM;
- CHECK_SYSTEM;
- REVISION_SYSTEM.

No fixture-specific name, literal token, or known gold answer may appear in the
repair.

### A. Draft semantic-grounding contract

Add generic rules:

1. The structured HCL state is authoritative cognitive context.
2. Explicit facts and an agent's observed/knows entries are directly
   established evidence at their stated granularity.
3. For a user question about whether an agent knows, observed, received, or has
   access to information:
   - directly established observed/knows evidence must not be negated;
   - explicit no-access / missing-evidence state must not be upgraded to
     knowledge;
   - if neither direction is established, preserve calibrated uncertainty.
4. Uncertainty, hypotheses, or EPISTEMIC mode do not override a directly
   established explicit fact or observed/knows entry at the asked granularity.
5. If the user explicitly requires an exact output form (for example exact
   yes/no or one option token), obey that form exactly and add no explanation.

### B. Checker semantic-monotonicity contract

Add generic rules:

1. Judge state faithfulness before style.
2. Denying directly established observed/knows evidence is an
   INFORMATION_ACCESS violation.
3. Contradicting explicit facts is a FACT_CONTRADICTION violation.
4. Do not request revision merely because the state is EPISTEMIC or uncertain
   about unrelated details when the asked proposition is directly established.
5. If the user explicitly requires an exact output form, failure to obey that
   form is a GRANULARITY violation.
6. PASS requires both semantic faithfulness and compliance with explicit answer
   granularity/format.

### C. Revision semantic-preservation contract

Add generic rules:

1. The HCL state outranks checker prose if they conflict.
2. Preserve any part of the draft that is already semantically supported by the
   state.
3. Never flip a directly supported answer merely to satisfy a checker request.
4. Correct only genuine material violations.
5. Direct observed/knows evidence must remain affirmative for the relevant
   access/knowledge proposition unless the state itself contains contrary
   evidence.
6. Obey explicit exact-output requirements exactly.

## Zero-provider invariants

Before provider calls, tests must prove:
- only DRAFT_SYSTEM / CHECK_SYSTEM / REVISION_SYSTEM changed in answer_loop.py;
- STATE_SYSTEM is byte-identical to repair-v0.2 behavior anchor;
- build_state() implementation is unchanged;
- backends.py is unchanged from repair-v0.2;
- each new generic grounding rule is present;
- no known target fixture ID, target-agent literal, target token, or gold literal
  from the causal investigation is embedded in the repair text.

## Fresh synthetic semantic-faithfulness suite

Create a new repository-owned suite with 12 cases not copied from the prior
io01/io02 fixtures:

- 3 direct positive information-access cases;
- 3 explicit negative/no-access cases;
- 2 direct positive exact-output-format cases;
- 2 negative exact-output-format cases;
- 2 second-order / transferred-information cases with explicit evidence path.

Use varied names, settings, propositions, and output forms.

Each case contains:
- input;
- gold parser target;
- format;
- expected state direction:
  DIRECT_POSITIVE / DIRECT_NEGATIVE / EXPLICIT_TRANSFER.

The fresh suite is frozen before provider validation.

Pass gate:
- 12/12 final semantic correctness;
- 12/12 parser validity;
- 12/12 exact-format compliance for cases that require exact output;
- 0 runtime exceptions.

## Required regressions after fresh-suite pass

The repair cannot close until all pass under one frozen behavior anchor:

1. original 16-case information-state/output-interface audit:
   - full_loop 8/8 semantic and parser;
   - forced_revision 8/8 semantic and parser;
   - no abstract interface defect;

2. existing answer-checker fresh suite:
   - 12/12 pass;

3. repair-v0.2 production-path state-fidelity regression:
   - 100% gated pass and schema validity;

4. repair-v0.2 state-generation reliability behavior remains statically
   unchanged from its passed anchor.

## No rerun-until-pass

A failed provider-backed validation is evidence. Do not alter prompts or retry
the same frozen validation as fresh evidence without a separately predeclared
next repair.

## External-evidence boundary

No new external benchmark evidence is authorized until this repair and all
synthetic regressions close.

## Claim boundary

A pass establishes generic synthetic answer-loop semantic faithfulness for the
specified information-access class and preserves prior state reliability.

It does not establish external benchmark efficacy, cross-base transfer, or HCL
1.0 certification.
