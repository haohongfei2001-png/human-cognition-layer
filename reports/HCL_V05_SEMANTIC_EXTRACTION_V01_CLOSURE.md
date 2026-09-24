# HCL v0.5 Semantic Extraction Pilot v0.1 — Closure

Verdict: **COMPLETE / EXTRACTION NOT RELIABLE ENOUGH / PACKAGE CONSUMED**

This is controlled internal evidence about the event-local semantic extraction
boundary. It is not an external benchmark, long-horizon capability result,
cross-model result, production result, publication claim, or leaderboard
evidence.

## Frozen execution

- Trigger/main commit: `706e12928a5e6251f1809f67662cdec4e30d287b`
- Candidate anchor: `0a88c2035e5377a0f157d3a8df24f70d3ded9a17`
- Workflow run: `36000445768` — SUCCESS
- Job: `107635513836`
- Artifact: `10807648913`
- Artifact ZIP digest:
  `sha256:2772dd399c8494a3a58abee4408c8ff444fb4bfea1f864cdfa4e5588c547f260`
- Result JSON SHA-256:
  `db6db98784db9652206350b3bc4297160052aadfe3412aabf7179c15281e2fbb`
- Model: `deepseek-flash`; seed: 42
- Fixture SHA-256:
  `afb653516b10a420eac0eb9cdcc6b740dc04728dc18cd4e07c5b693be8dfbd7a`
- Gold SHA-256:
  `e2d638003b3cf2b0fdd8f742f9594777ec68caa89ec6dc024e86bf02c3d69964`
- Shape: 3 streams / 36 events / 36 gold stance signals

All one-shot, candidate-drift, digest, provider-free validation and artifact
completeness checks passed before the result was accepted. The package was run
once and was not rerun.

## Result

- exact event-level semantic matches: **20 / 36**
- signal true positives: **24**
- signal false positives: **8**
- signal false negatives: **12**
- signal precision: **0.75**
- signal recall: **0.6667**
- extraction/schema errors: **0**
- semantic repair events: **0**
- provider calls: **36**
- provider input characters: **86,177**
- provider output characters: **4,624**
- provider wall time: **29.66 s**

The absence of schema failures is useful but insufficient. The semantic content
itself is not reliable enough to justify a new long-horizon capability run.

## Failure structure

Sixteen events were not exact. The failures were highly structured rather than
random.

### A. Source assertion was misread as source's own stance

All three plain source-information events were incorrectly extracted as an
AFFIRM stance for the source actor:

- `x1-e01`
- `x2-e01`
- `x3-e01`

A source telling another person "the current value is X" does not establish that
the source actor's own mental stance should enter HCL belief state.

### B. Revision relation and exposure subject were entangled

Most revision failures came from asking the model to infer both:

1. that the event contains a replacement relation `new -> old`; and
2. which person is thereby exposed to that revision.

Observed failures included:

- missed exposure to the actual recipient;
- exposure attributed to the sender/quoted source instead of the recipient;
- missed observer-only world update;
- repeated/direct revision messages misread as source AFFIRM;
- relay revision attributed to the relay sender rather than the receiver.

Affected risk classes:
- other-agent revision exposure: 3 failures;
- direct revision exposure: 2;
- second direct revision exposure: 2;
- relay revision exposure: 2;
- repeated revision exposure: 2;
- world-update observer-only: 1.

### C. Self-unresolved event duplicated revision exposure

On `x2-e08`, UNRESOLVED was correctly extracted, but the model also emitted an
extra REVISION_EXPOSURE from a self-report that merely referred back to a
previously received correction.

## Architectural interpretation

The v0.5 deterministic stance state machine remains useful as an internal
mechanism candidate; this result specifically falsifies the current **semantic
interface**, not the state-transition rules.

The primary design mistake is giving the model responsibility for both semantic
relation recognition and information-flow routing.

The next semantic boundary should separate them:

- the model may identify an event-level revision relation:
  `issue, new_value, prior_value`;
- deterministic code must route that revision exposure to the explicit
  recipients/observers in the event;
- the model may identify only explicit self-stance reports from the event actor;
- a source assertion must not become self stance merely because the speaker
  asserted a proposition;
- self-report references to earlier revisions must not recreate exposure.

This change is mechanism-level. It must be tested provider-free with new generic
examples before any new provider extraction package is frozen.

## Consumption boundary

The 36 v0.1 events are consumed.

- Do not rerun them as fresh evidence.
- Do not patch against these event IDs/labels and call the same package fresh.
- Abstract failure modes may be represented with new provider-free examples.
- Any later provider extraction test requires a new independently frozen
  package.

No owner-private research example, long-horizon capability run, external
benchmark, cross-model run, training, publication or leaderboard action is
authorized by this closure.
