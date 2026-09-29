# F02 — Narrative time and disclosure

## CAPABILITY_DELTA

HCL can keep the time a source says an event occurred apart from when someone
recalled it, when the recollection was disclosed, the order in which it appears in
a chapter, and when that chapter entered the analyst's records. An old event
recalled late appears in the later disclosure view while retaining its old story
date. A source-reported challenge marks that recollection contested. A reported
receipt changes the named person's information view only after the receipt date;
receipt does not establish belief or comprehension.

`NarrativeTimeline` reads bounded dated narration, preserves exact source quotes,
and uses F01's local event/span references. Its chapter versions are selected by
system record time before the story/disclosure projection. A later analyst
correction changes the current reading while an earlier known-at snapshot still
uses the earlier source version. Current access revocation prevents an old
snapshot from exposing material to that observer. Story-order sorting excludes
contradictory declared dates rather than silently repairing them.

Recall, challenge and receipt links require a unique source-local named anchor.
Same names in separate chapters are not treated as a shared identity. Ambiguous
pronouns, missing dates, inconsistent dates and unmatched links remain unresolved.
Source-reported speech is not world truth, and a challenge is not a verdict of
falsity. Source availability is not character receipt.

The simplest alternative is a generic dated note table with separate event and
record dates. Serious evaluation should simplify this operation if its
source-linked disclosure and revision behavior adds no useful reasoning.

## Verification and limits

Nineteen targeted tests cover the ordinary positive witness, five time axes,
flashback order, late disclosure, explicit receipt and challenge, ambiguous links,
source correction, system known-at cutoff, ACL revocation, hidden-source
non-interference, F01 source recovery, budget and refusal cases. The witness saves
actual model inputs for early, later, contested, before-receipt and after-receipt
views in `reports/HCL_WAVE_F02_WITNESS.json`. Full v1 and 176 historical regressions
run in exact-head/main CI.

Bounded explicit English, at most 16 chapters and 256 current events by default;
source accuracy and named identity across chapters are not established. No
independent efficacy claim. State:
**CORRECTNESS_VERIFIED / REPLAY_VERIFIED / UNTESTED / OPT_IN**.
Provider calls/spend: zero. LongMemEval sealed. NEXT_READY: F03 evidence closure
selection and incremental recomputation.
