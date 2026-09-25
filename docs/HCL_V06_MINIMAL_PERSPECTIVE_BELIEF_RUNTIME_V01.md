# HCL v0.6 Minimal Perspective & Belief Runtime v0.1

Status: **IMPLEMENTED CANDIDATE / PROVIDER-FREE CERTIFICATION REQUIRED / EXTERNAL EFFICACY NOT YET CLAIMED**

## Purpose

This milestone adds an actual cognition capability rather than another benchmark gate.

The v0.6 candidate extends the frozen v0.5 stance foundation with a minimal,
benchmark-independent ability to reason under character-specific information
boundaries and to represent belief evidence/revision without treating exposure
as acceptance.

It does not attempt a complete Theory of Mind system.

## New capability

### 1. First-order information perspective

For a target character A, the runtime deterministically constructs only the raw
events A could access through:
- being the actor;
- explicit recipient membership;
- explicit observer membership;
- an event marked public.

Reader/narrator-only evidence is excluded from character perspective.

The external system/reader may still inspect all stored evidence for audit.

### 2. Bounded second-order perspective

For an observer A and target B, the runtime can construct:

> the events A has evidence that B could access.

An event enters this view only if:
1. A can inspect the event/access metadata; and
2. B has an explicit access path or the event is public.

This supports bounded questions such as "according to A's evidence, what did B
know?" without arbitrary recursive mental-state nesting.

### 3. Belief evidence identity

Belief evidence preserves how it was obtained:

- `SELF_REPORT`
- `NARRATOR_ASSERTION`
- `THIRD_PARTY_REPORT`
- `OBSERVED_ACTION`
- `INFORMATION_EXPOSURE` for challenge receipt only

Only direct self-report and explicitly marked narrator assertion can establish
a firm belief estimate in the minimal v0.6 projector.

Third-party reports and observed actions remain indirect support/counterevidence.
They do not become private-belief truth merely because they are plausible.

### 4. System uncertainty != character uncertainty

The runtime has distinct states:

- `CHARACTER_UNCERTAIN`: direct evidence says the person is uncertain;
- `SYSTEM_INSUFFICIENT`: the available evidence does not determine what the
  person believes.

The latter is not a psychological claim.

### 5. Challenge exposure != belief revision

A challenge delivered to a character is recorded as unresolved challenge
evidence but does not erase or suspend the character's existing belief.

A belief changes only when direct evidence supports an explicit new stance.

This intentionally corrects the broad psychological interpretation that could
otherwise be read into v0.5's `REVISION_EXPOSURE -> UNRESOLVED` stance
projection. v0.5 remains frozen; v0.6 introduces a separate belief semantics
rather than rewriting historical behavior.

### 6. Explicit belief revision

A direct `AFFIRM` may explicitly identify a
`supersedes_proposition_key`.

Example semantic transition:

```text
direct evidence: A affirms X
challenge to X reaches A
=> current belief remains X; challenge is pending evidence

direct evidence: A affirms Y and explicitly revises X
=> X = SUPERSEDED by Y
=> Y = AFFIRMED
```

No revision is inferred merely from chronological proximity or receipt of
counterevidence.

### 7. Perspective-bounded answer interface

The runtime can construct a structured answer context containing:
- the target's evidence-bounded information view;
- belief estimates with provenance/status;
- explicit semantic guardrails.

For second-order answering, it separates:
- what the observer can establish the target had access to; and
- what belief evidence about the target is visible to the observer.

The downstream base model is instructed not to use omniscient narrator/world
information outside the supplied perspective.

## Files

Implementation:
- `hcl/v06/perspective.py`
- `hcl/v06/belief.py`
- `hcl/v06/semantic.py`
- `hcl/v06/runtime.py`
- `hcl/v06/__init__.py`

Provider-free correctness suite:
- `tests/test_v06_perspective_belief_runtime.py`

CI:
- `.github/workflows/hcl-v06-perspective-belief-runtime.yml`

## Semantic extractor boundary

The v0.6 extractor may emit belief evidence and challenge relations, but it is
structurally prevented from silently changing provenance:

- self-report subject must equal the event actor;
- narrator assertion requires narrator/reader-only metadata;
- third-party report requires a distinct event actor;
- observed action belongs to the event actor;
- challenge exposure is routed deterministically from event recipients /
  observers / public metadata rather than model-selected recipients;
- `supersedes_proposition_key` requires a direct affirmative revision.

One bounded JSON repair is permitted. Repeated invalid output fails closed.

## What this milestone does not add

No:
- personality model;
- motive diagnosis;
- emotion dynamics;
- relationship score;
- moral/value ontology;
- philosophical reasoning engine;
- arbitrary-depth Theory of Mind;
- model training;
- benchmark-specific answer rule;
- paid benchmark run.

## Relationship to v0.5

v0.5 remains the frozen explicit-stance / provenance / long-horizon foundation.

v0.6 does not mutate v0.5's historical state machine. It adds a distinct
human-perspective capability with stricter psychological claim boundaries.

Future integration may reuse v0.5 persistence after the v0.6 semantics survive
correctness and external utility testing.

## Current evidence standard

This milestone can establish only:

> the new perspective/belief mechanism is internally coherent and passes
> benchmark-independent provider-free correctness tests.

It cannot yet establish that v0.6 improves external human-cognition task
performance.

After provider-free certification, the next development step is not another
large benchmark framework. It is:
1. fix any correctness defects found by the independent v0.6 suite;
2. freeze this minimal mechanism;
3. run a bounded external C/P/D comparison on fresh FANToM development evidence;
4. add competent G only for the later efficacy stage if specialized D survives.

The existing LongMemEval paid package remains frozen and does not block this
runtime.

**Candidate gate: HCL_V06_MINIMAL_PERSPECTIVE_BELIEF_RUNTIME_PROVIDER_FREE_CERTIFICATION**
