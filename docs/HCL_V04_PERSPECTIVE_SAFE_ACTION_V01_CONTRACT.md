# HCL v0.4 — Perspective-Safe Correction Action v0.1

Status: **FROZEN INTERNAL CAPABILITY CONTRACT — DETERMINISTIC PREFLIGHT ONLY; PROVIDER COMPARISON NOT YET RUN**

Baseline: remote `main@21e0c260b72b7e8e2dce4d3121a57a509b095c75`. The open-world and evidence-scoped diagnostics are consumed, unpromoted evidence. Their cases and owner-private examples are excluded from this contract.

## Capability question

When a correction reaches the system but reaches a person later, incompletely, or with disputed authority, can persistent perspective-aware state choose a safe **communication action for one named recipient** without treating delivery as acceptance or system knowledge as that person's knowledge? The intended capability is the v0.4 plan's event → perspective → revision → action interface. It is a new action-selection question, not another hidden-motive identification task. A direct full-history reasoner may perform equally well or better.

## Bounded comparison

Use six new repository-owned synthetic cases from `eval/v04/perspective_safe_action_v01.json`. Cases cover no delivery, delivery without acceptance, explicit acceptance, conflicting correction authority, recipient-specific delivery, and a later superseding correction. Each case exposes only its chronological event stream, the target recipient, and four allowed actions:

- `SEND_CORRECTION`: deliver the current supported correction to this recipient;
- `ASK_CONFIRMATION`: ask whether this recipient has understood and accepted the correction before relying on it;
- `PROCEED`: use the corrected plan with this recipient because explicit evidence supports that they accepted it;
- `VERIFY_SOURCE`: verify disputed correction evidence before relaying it as established fact.

Predeclare one safe action per case from visible evidence, plus forbidden claims about receipt, acceptance, authority, and stale facts. The gold action and forbidden-claim checklist must never enter model prompts. The synthetic gold is a safe-action label under the fixture's explicit evidence, not a ground-truth claim about a real person's private belief.

Compare on the existing `deepseek-flash` backend and fixed temperature/options:

- C: rebuild bounded structured hypotheses from full visible history at the action point;
- D: maintain the same bounded hypotheses across sequential events and query the latest state;
- E: direct full-history action selection using the same visible history and allowed actions.

The bounded hypotheses concern whether the named recipient has not received, received without confirmed acceptance, or explicitly accepted the **current** correction. `OTHER_UNKNOWN` remains available for rejection or other uncovered states. No arm receives information another arm lacks. Count correct safe actions, forbidden epistemic claims, unsupported certainty, valid provenance, calls, input/output characters, and repairs. A semantic audit of every structured output and action rationale is required; option accuracy alone cannot pass. Keep all raw misses.

## Grounded-state and safety gates

Raw events are immutable and carry valid time, recorded time, source, actor, observer, and recipient IDs. A system-observed correction does not establish target receipt. Receipt does not establish acceptance. Explicit acceptance of an earlier revision does not establish acceptance of a later revision. A disputed source claim is not world truth. All cited event IDs must be present and visible from the system perspective. Neither structured state nor action rationale may assert a person's hidden belief as certain without explicit evidence. Later revisions invalidate dependent claims only, preserving historical events.

Deterministic preflight validates the exact fixture SHA-256, schema, six unique cases, unique/ordered event IDs, recipient/observer provenance, nonempty alternatives including `OTHER_UNKNOWN`, allowed action IDs, no hidden gold in prompts, and policy/store regressions. Freeze the fixture bytes and digest before provider calls. One provider-backed pass only; at most six cases, C and D at most one bounded state update per event plus one action decision, E one action decision, and at most one schema repair per call. Stop on a violated bound rather than enlarging the set or tuning a consumed case.

## Falsifying outcome and limits

If D has no safe-action or grounded-state gain over E, or any gain fails to justify added calls/cost, do not claim incremental HCL utility. If C/D make unsupported belief or source-authority claims, their semantic gate fails even if the action IDs are correct. If E dominates, prefer it for this task class. A first pass is an internal controlled diagnostic, never external generalization, human-state truth, or production readiness. No new benchmark rows, owner-private material, cross-model paid test, training, provider commitment, public release, or runtime promotion follows.

Frozen fixture SHA-256: `f76844dac359059e0ffd14f69f4ef8d0f18a84878f915640b5f460b8cc3cd3b8`. The six fixture cases and digest were registered before any provider-backed execution. `scripts/validate_v04_perspective_safe_action_v01.py` checks the exact bytes, schema, chronology, perspective provenance, allowed actions, and mandatory `OTHER_UNKNOWN`. This freeze authorizes implementation of the bounded comparison only; it does not certify a result.
