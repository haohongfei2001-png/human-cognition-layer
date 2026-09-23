# HCL v0.4 Evidence-Scoped Revision v0.1 — Frozen Internal Capability Contract

Status: **FROZEN FOR BOUNDED IMPLEMENTATION**

Baseline: remote `main` `025b5095d2b494d7ac7d87a01cb674e194534418` and the controlled hypothesis-guided action closure in `STATUS.md`.

## Capability question

Can an always-on, provenance-preserving event ledger with query-time, target-scoped hypothesis revision support a correct probe and final action after intervening events, while avoiding unnecessary per-event hypothesis calls? This tests a capability/cost tradeoff left open by the prior C/D/E result, where ordinary full-history reasoning E matched D and was cheaper. It does not assume the new mechanism wins.

## Bounded mechanism

1. Append every valid raw event to the existing persistent `CognitionStore` in receipt order. Never discard, rewrite, or silently translate an assertion into world truth.
2. Maintain an explicit per-target pending-event cursor. A query for a target must bring its derived hypothesis state current with all relevant unprocessed events before a probe, answer, or action can use it. Unknown target relevance is included conservatively; only explicit, validated target binding may exclude an event.
3. Keep evidence IDs, agent exposure, valid/record time, support, counterevidence, `OTHER_UNKNOWN`, and revision history visible to the existing hypothesis validator. A system correction is not automatically a person's correction or changed belief.
4. If a revision cannot be validated or persisted, the action interface reports unavailable/uncertain. It may not use a stale state or silently fall back to an apparently certified action.
5. Limit this slice to one subject, at most three named competing hypotheses plus `OTHER_UNKNOWN`, one probe, and one final action. Reuse the current store, tracker, policy, and JSON option interface. No new ontology, training, cross-agent mind reading, or production integration.

## Precommitted validation

Before any provider-backed capability run, freeze an independent repository-owned synthetic scenario file and its hash. Prior six guided-action scenarios are regression only and cannot become fresh efficacy evidence. The new file must contain 6–8 distinct multi-event cases with correction, partial exposure, competing interpretations, irrelevant events, and delayed query. Author them without owner-private examples or consumed external benchmark rows.

Correctness gates are deterministic and blocking: complete immutable event history; no perspective leakage; no unstated acceptance of a correction; target cursor idempotence; conservative handling of unscoped events; no unrelated-target revision; evidence-ID validity; failed revision leaves no apparently current derived state; no stale action. A new synthetic capability comparison may run only after these gates and fixture freeze pass.

Compare the same base model and allowed options across: C, full-history reconstruction at each decision; D, existing eager persistent hypothesis maintenance; E, ordinary direct full-history reasoning; and F, this evidence-scoped revision. Run one frozen pass with a fixed model/seed, record final-action exact correctness, high-information probe rate, grounded-state errors, calls, tokens/characters, and revision latency. Use the existing approved provider only if available; no new paid service, cross-model experiment, benchmark, or real-person data is authorized. A provider outage is pending evidence, not a pass.

## Falsifying and decision rules

Any grounded-state violation, lost evidence, exposure leak, or stale action fails F regardless of score. If F does not improve decision correctness or useful probe selection over E, and does not justify its cost, do not claim incremental HCL utility; retain the simpler mechanism. If F matches D but only reduces maintenance cost, label that as engineering efficiency, not new cognitive efficacy. One observed miss cannot be tuned and rerun as fresh evidence. After a behavior change, freeze independent new holdout cases before making a fresh claim.

This contract authorizes only bounded internal implementation and validation. It does not authorize new external benchmark rows, owner-unapproved research examples, cross-model transfer, public research claims, publication, or broader architecture expansion.
