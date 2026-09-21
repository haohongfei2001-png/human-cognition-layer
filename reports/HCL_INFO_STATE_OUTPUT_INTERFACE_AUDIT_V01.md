# HCL Info-State / Output-Interface Synthetic Audit v0.1

Status: **PREDECLARED / AUDIT CURRENT FROZEN HCL BEFORE REPAIR**

## Trigger

FANToM v0.2 full-context external pilot closed MIXED.

Primary belief showed a small favorable signal:
- control 12/16
- HCL 13/16
- net +1.

Primary information-state showed a small unfavorable signal:
- control 14/16
- HCL 13/16
- net -1.

One HCL-worsened answerability item produced no parseable yes/no verdict after
both HCL revision passes. Because benchmark response text is intentionally not
persisted, that consumed item cannot be used to tune the system.

This audit therefore tests the abstract failure class using independent
synthetic fixtures only.

## Frozen implementation under audit

Do not change before the audit:

- HCL v0.3 state semantics;
- `hcl/v03/answer_loop.py`;
- DeepSeek model/provider/seed;
- state/answer/check token budgets.

Behavior anchor:
`ce36d7e6f911910f97437c23455dee33e0e7bc82`

## Independent fixture domains

Synthetic scenarios use unrelated domains:
- laboratory access badges;
- conference schedules;
- package delivery;
- museum exhibits;
- office memos;
- library shelves;
- equipment checkout;
- classroom notices;
- reservation systems;
- inventory tags.

No FANToM conversation, question, answer, character, or wording is reused.

## Two audit families

### A. Full-loop strict-format cases

Run the complete frozen HCL answer loop from user input.

Test:
- explicit information access;
- explicit lack of information access;
- false belief;
- second-order belief;
- answerability;
- binary information accessibility;
- two-choice belief questions;
- calibrated uncertainty with a categorical output interface.

For each case predeclare:
- accepted output family: binary or A/B;
- semantic gold verdict;
- parser-valid requirement;
- exact-format requirement recorded separately.

### B. Checker-triggered revision cases

Build HCL state, supply a deliberately flawed synthetic candidate, run the real
HCL checker, and if it returns REVISE run the real revision generator.

Test whether revision:
1. fixes the semantic/epistemic defect;
2. remains parseable under the requested binary/A-B interface;
3. preserves exact requested output format;
4. passes the frozen final checker.

The flawed candidates are independent synthetic test inputs; they are not
benchmark outputs.

## Deterministic parsers

Binary accepted parser:
- leading `yes` / `true` -> yes;
- leading `no` / `false` -> no;
- optional `Answer:` prefix;
- otherwise invalid.

Binary exact format:
- stripped lowercase output is exactly `yes` or `no`.

A/B accepted parser:
- exactly one unambiguous A/B verdict in bracket form, or a leading A/B verdict;
- ambiguous/missing = invalid.

A/B exact format:
- stripped uppercase output is exactly `[A]` or `[B]`.

## Audit gate

This is an audit, not a repair gate.

Raw results must report separately:

- full-loop semantic accuracy;
- full-loop parser-valid rate;
- full-loop exact-format rate;
- forced-revision checker REVISE hit rate;
- forced-revision semantic accuracy after revision;
- forced-revision parser-valid rate;
- forced-revision exact-format rate;
- forced-revision final-check PASS rate.

A repeatable abstract defect is established if either:

1. any semantically correct/incorrect final answer is **not parser-valid** under
   the explicitly requested output interface; or
2. a forced revision corrects semantics but loses parser-valid format; or
3. final checker PASS accepts a revised answer that violates the required
   categorical interface.

Do not change HCL based on individual fixture wording. Any repair must address
the abstract interface invariant and then rerun this entire frozen suite plus
existing answer-loop/state regression gates.

## No external evidence consumption

This audit consumes no new benchmark data and creates no external efficacy
claim.
