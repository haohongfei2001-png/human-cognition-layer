# HCL Communication Boundary Failure Adjudication v0.1 — Closure

## Decision

Original boundary raw result remains:

**7 / 10 RAW**

Bounded full-state adjudication result:

**10 / 10 SEMANTIC CONFORMANCE**

The three raw failures are classified as evaluator/fixture false negatives, not
runtime semantic failures.

## Canonical adjudication run

- workflow: `HCL Communication Boundary Failure Adjudication v0.1`
- run: `35720920913`
- launch commit: `a900bc971fa76449208d0cc0414a574b30a82678`
- terminal conclusion: **SUCCESS**
- preflight: **SUCCESS**
- 12 / 12 state builds completed
- artifact: `10690659128`
- digest:
  `sha256:148f3492d473917670e2eef102bce4fd7d6d9d04c92930183ef4d96f2cf07827`

## cb02_direct_teacher

Classification:

**EVALUATOR_FALSE_NEGATIVE**

Across 4 / 4 repeats:
- target agent Imani represented;
- mode SIMPLE;
- uncertainty low;
- missing bridges empty;
- state explicitly records that the lab starts at the communicated time;
- `knows` contains the communicated proposition itself;
- no unsupported conflict or reliability doubt.

The raw evaluator required the literal substring `10 AM`.
The model rendered the semantically identical time using localized natural
language (`10 点`).

Exact lexical spelling of a time is not part of the frozen cognition semantics.

## cb06_unread_notice

Classification:

**FIXTURE_DESIGN_FALSE_NEGATIVE**

Across 4 / 4 repeats:
- target agent Ayla represented;
- mode EPISTEMIC;
- uncertainty low;
- observed / knows / believes are empty;
- state explicitly says the notice was not opened and nobody communicated the
  deadline;
- decision summary consistently says the target does not know the new deadline;
- no invented secret receipt path.

The raw fixture required `missing_bridges` to be non-empty.

Under the frozen semantics, however, the relevant evidence-path absence is
explicitly established rather than unknown. At the actual yes/no question
granularity there is no unresolved bridge to fill.

Therefore requiring a missing bridge in this case overstates uncertainty and is
a fixture-design error.

One repeat included a rejected positive hypothesis with zero support and explicit
counterevidence. This is unnecessary representational sprawl but does not
change the decision-relevant state; it is advisory rather than a gate failure.

## cb10_conflicting_sources

Classification:

**EVALUATOR_FALSE_NEGATIVE**

Across 4 / 4 repeats:
- target agent is represented;
- mode EPISTEMIC;
- uncertainty high;
- two conflicting directly received propositions are represented;
- target `knows` remains empty;
- both candidate dates remain unresolved;
- a missing bridge explicitly states that evidence is needed to resolve the
  conflict;
- decision summary says the target cannot determine the inspection day.

Agent-key serialization:
- one repeat uses `Chen`;
- three repeats use the localized equivalent `陈`.

The raw evaluator required a case-insensitive literal key match to `Chen` and
therefore missed the localized but semantically identical agent key.

The predeclared adjudication protocol explicitly allowed a harmless localized
alias and rejected only total target-agent omission. No omission occurred.

## Methodological accounting

Do not rewrite history:

- original boundary run `35720589183`: **7/10 raw**
- adjudication run `35720920913`: all three raw failures satisfy frozen
  semantic criteria in **4/4** repeated states each
- semantic boundary result: **10/10 adjudicated**

No HCL behavior was changed between the raw boundary and adjudication runs.

## Consequence

The runtime STATE_SYSTEM conformance repair is allowed to advance to the
already-predeclared broader synthetic regression gate.

It is not yet closed.

Required next gates under the same frozen behavior:
1. state-generation reliability: 24/24, zero runtime failures;
2. fresh semantic-faithfulness answer suite: 12/12;
3. original information-state/output-interface audit: 8/8 + 8/8;
4. production-path state fidelity: 100%;
5. existing answer-checker fresh suite: 100%.

No external benchmark evidence is authorized.

## Claim boundary

Supported:
- runtime direct-communication semantics satisfy the fresh boundary after
  transparent adjudication of evaluator/fixture defects.

Not supported:
- repair closure;
- external benchmark efficacy;
- cross-base transfer;
- HCL 1.0 certification.
