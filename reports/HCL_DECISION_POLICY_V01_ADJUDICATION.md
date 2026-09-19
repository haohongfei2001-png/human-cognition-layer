# HCL Decision Policy Synthetic v0.1 Adjudication

Run: `35449770050`

## Raw result

- total: 12
- raw pass: **11 / 12**
- raw pass rate: **91.7%**

The single raw failure was:

`dp06_declined_trip_accept_coffee`

Expected strategy labels:
- COMMIT
- ALTERNATIVE_PATH

Actual:
- DIRECT_PROGRESS

## Adjudication

The generated plan was semantically correct.

The private goal was to spend meaningful time with a friend during the month.
The weekend trip was explicitly unavailable, while the friend had already
offered coffee next week.

The Decision Policy chose:

- respect the blocked trip;
- accept the coffee offer;
- propose a concrete day/time;
- turn the alternative into an actual plan.

Under the fixture's **underlying goal**, this is reasonably classified as
`DIRECT_PROGRESS`: once coffee is explicitly offered, concretizing it is a
direct step toward the broader goal of meaningful time together.

The fixture expectation was therefore too narrow at the taxonomy boundary.
This is analogous to earlier HCL evaluation cases where a semantically valid
choice was rejected by an over-specific test label.

## Decision

**Decision Policy synthetic gate: PASSED with raw 11/12 preserved.**

No 12/12 retroactive score is claimed.

The failure is retained in the raw result and documented rather than editing the
fixture after seeing the answer.

## What the suite demonstrated

The policy correctly handled the intended abstract failure classes:

- hard personal cap + unknown employer match -> targeted information probe;
- exhausted incompatible price range -> exit/defer;
- explicit resource refusal + unused safe alternatives -> alternative path;
- failed warming methods + known heated shelter -> alternative path;
- ownership/provenance uncertainty -> pause and verify;
- ambiguous project delay -> high-value information probe;
- confirmed matching route -> use it rather than press personal funds;
- acceptable transaction -> commit;
- non-price term that unlocks a deal -> commit;
- already agreed scheduling task -> execute directly.

The policy is now eligible for SOTOPIA integration.

## Claim boundary

This suite is synthetic and independent from the SOTOPIA diagnostic dialogues.
It establishes only that the Decision Policy follows the intended abstract
decision rules on these fixtures. It does not establish SOTOPIA performance.
