# HCL v0.7 Evidence-Constrained Intention & Motivation — Minimal Runtime

Status: **V07-A PROVIDER-FREE CANDIDATE**

The v0.7 runtime consumes immutable `EventRecord` evidence and typed,
source-anchored `IntentionEvidenceEvent` records. It composes the v0.6
perspective runtime; actor/time/access semantics are not reimplemented.

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

This is a typed cognition-state core. An external narrative-to-evidence
extractor must be audited separately before provider-backed utility claims.
The runtime itself does not read benchmark question, answer or gold fields.

Independent provider-free tests cover action/intention separation, direct
completion, explicit revision, unresolved goals, third-party attribution,
character uncertainty, first/second-order privacy and narrator-only evidence.
The v0.4/v0.5/v0.6 regressions run alongside the new tests.

Files: `hcl/v07/runtime.py`, `tests/test_v07_intention_runtime.py`.
