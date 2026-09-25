# HCL v0.7 Evidence-Constrained Intention & Motivation — Minimal Runtime

Status: **V07-A PROVIDER-FREE CANDIDATE**

The v0.7 runtime consumes immutable `EventRecord` evidence and typed,
source-anchored `IntentionEvidenceEvent` records. It composes the v0.6
perspective runtime; actor/time/access semantics are not reimplemented.
Each evidence item must quote an exact excerpt of its source event; citing an
event ID alone cannot introduce an invented intention sentence.

## Semantics

- Explicit self-report or reader-only narrator evidence can establish an
  intention or goal. Third-party reports remain attributions.
- An observed action and a plausible inferred motivation are recorded
  separately. Neither proves a private intention or a unique motive.
- Directly evidenced revision names a previously evidenced goal. A change of
  action alone never revises a goal.
- Explicit completion or abandonment changes goal status. Counterevidence
  makes an active goal `UNRESOLVED`, not automatically abandoned.
- `CHARACTER_UNCERTAIN` records the subject's own uncertainty;
  `SYSTEM_INSUFFICIENT` means the system lacks direct evidence. The latter
  does not assert that the person lacks a motive.
- The first-order answer context includes only the target's accessible
  source events. The bounded second-order context includes only evidence that
  the observer can establish was available to the target. Reader-only
  narrator facts remain available to the system but do not leak into
  character views.

The event-local semantic adapter emits only source-excerpt-grounded evidence,
keeps provenance, and gets at most one bounded structural repair. Invalid
extraction leaves goal state unchanged. Duplicate event ingestion reuses the
first committed extraction without a second provider call. This is still a
provider-free candidate: no external narrative extraction quality or utility
has yet been established. The runtime and adapter never read benchmark
question, answer or gold fields.

Independent provider-free tests cover action/intention separation, direct
completion, explicit revision, unresolved goals, third-party attribution,
character uncertainty, first/second-order privacy and narrator-only evidence.
The v0.4/v0.5/v0.6 regressions run alongside the new tests.

Files: `hcl/v07/runtime.py`, `hcl/v07/semantic.py`,
`tests/test_v07_intention_runtime.py`, `tests/test_v07_semantic.py`.
