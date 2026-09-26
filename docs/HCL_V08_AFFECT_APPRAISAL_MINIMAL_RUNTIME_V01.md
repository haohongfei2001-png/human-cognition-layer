# HCL v0.8 Evidence-Constrained Affect and Appraisal Runtime v0.1

Status: **IMPLEMENTED CANDIDATE / EXTERNAL UTILITY NOT RUN**

`HCLV08Runtime` wraps `HCLV07Runtime` and reuses immutable `EventRecord`, goal
evidence and first-order/bounded second-order source visibility. It supplies
source-grounded evidence to a downstream model; no rule maps an action,
outcome or appraisal score to a unique private emotion.

`AffectEvidenceEvent` stores subject, episode, free-text value, exact quote,
event/record time, provenance and DIRECT/INFERRED/ATTRIBUTED strength. Kinds:
EMOTION, APPRAISAL, EXPRESSION, CHARACTER_UNCERTAIN. Five appraisal dimensions:
goal relevance, goal congruence, control, certainty, accountability.

- Direct mental evidence requires self-report or reader-only narrator evidence.
- Expression is behavior, not a direct internal feeling. Inferences stay hypotheses.
- Third-party judgments remain attributed and cannot overwrite direct reports.
- Mixed feelings/episodes coexist. Only later explicit direct evidence can
  supersede an earlier direct record for the same subject/episode/kind/dimension.
- Goal links require already directly evidenced goals. Hidden goal/revision
  pointers are removed from answers and semantic extraction context.
- Narrator-only evidence does not become character knowledge. Temporal views
  reuse the perspective layer; system lack of evidence differs from a
  character explicitly reporting uncertainty.

`answer_context` returns current and superseded visible evidence, visible goal
context and scoped status: SUPPORTED_REPORT, HYPOTHESIS_ONLY,
CHARACTER_UNCERTAIN, SYSTEM_INSUFFICIENT. A supported report means a feeling
was reported, not guaranteed psychological truth.

## Semantic adapter and verification

The adapter receives one event, only earlier visible direct records and goal
keys, without task/benchmark labels/ratings/persona. It validates bounded
shape, source actor/provenance, exact excerpts, chronology and relation targets.
One repair is allowed; persistent failure retains source without false claims.
Batch commit is atomic, replay idempotent and ID collisions fail closed.
An exact quote proves anchoring, not semantic entailment; source support still
requires external review. Empty states are recorded explicitly.

Independent fixtures cover expressions/outcome uncertainty, mixed feelings,
revision/history, attribution/uncertainty, narrator and first/second-order
boundaries, hidden relation pointers, future/private extraction context,
quote/time/identity checks, repair, replay and atomic failure. Existing
v0.4–v0.7 regressions remain required; external cases did not design these rules.

The development adapter treats each narrative as one authored source report,
with an ingestion-order placeholder timestamp. It invents no calendar dates
or hidden timeline. Answers must qualify narrated earlier/later feelings.
The small check does not externally certify every runtime transition.

No personality or clinical inference is supported. Correct state behavior is
separate from model utility; retain the simplest externally useful method.
