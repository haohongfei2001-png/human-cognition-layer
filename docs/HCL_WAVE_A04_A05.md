# A04–A05 — Retained operations consuming shared semantic material

**A04 CAPABILITY_DELTA:** quoted ordinary speech and scoped semantic candidates
now feed actual retained v0.6 belief/perspective, CG03 responsibility-factor,
CG04 contextual-preference and CG05 local-concept checkers from one shared source
representation. The caller supplies ordinary text/question, not hidden mental
states or operation flags. CG03 still needs an explicit conditional normative
premise; ordinary premise construction belongs to G01.

**A05 CAPABILITY_DELTA:** a source property correction flows through the real
concept criterion checker into the dependent belief/concept comparison. The
expressed belief stays the same while its relation to local criteria changes;
unrelated Noor stays identical. One configured answer adapter receives the actual
current state, original quotes, translation bindings and assumptions.

## Interface and semantic boundary

`prepare_retained(workspace, question, source_ids=(...))` consumes A02 material;
`answer_retained(workspace, question, answer_backend, source_ids=(...))` makes one
configured final call. `result.current_messages(workspace)` rejects stale source
versions or newly challenged dependencies. `result.messages` is the immutable
preparation snapshot for audit, not permission to answer after state changes.

A **literal reported-speech format adapter** changes `Mira said, "In team, ..."`
into a derived `Mira: In team, ...` line. Original text is retained with exact
span identity; the generated line is never represented as verbatim source.
Historical parsers/checkers validate their derived representation. Source and
synthetic ordering time remain explicitly distinct from actual calendar/access time.

Open backend event candidates can propose `canonical_statement`. They are always
`UNVERIFIED_TRANSLATION_HYPOTHESIS`, evaluated under named assumptions, with original
prose and unresolved text alongside the result. Successful checking establishes
only what follows **if that translation is correct**; it cannot certify the
translation, private belief or world truth. Explicit names must remain anchored;
multiple competing translations for one span are not silently collapsed. Local
unparsed qualifiers, ambiguous speakers and conditional quotations fail closed.

The new core has explicit narrowing projections. They preserve observer, source,
time and inherited assumptions; the projected claim also depends on its original
candidate. Challenges/withdrawals propagate through projection → checker → joint
comparison. Copying a normalized line cannot cut that dependency. Checker outputs
are `CONDITIONAL_TOOL_RESULT`; source reports cannot be synthesized from them.

## Positive witness and checks

[Reproducer](../scripts/witness_retained_shared.py) /
[receipt](../reports/HCL_WAVE_A04_A05_WITNESS.json) records original/derived text,
operation graph, before/after states and the exact one stub-adapter input.
Consent false → true changes `CRITERIA_NOT_MET` → `CRITERIA_MET` and
`DIFFERS_FROM_LOCAL_SOURCE_CRITERIA` → `CONSISTENT_WITH_LOCAL_SOURCE_CRITERIA`.
Noor's live input is byte-identical. This is dependency-based composition, not
independent JSON concatenation.

Fourteen targeted checks cover all four real checkers, positive composition,
third-party attribution, conditional premise separation, upstream challenge
propagation, source withdrawal, stale answer rejection, exact final invocation,
quote/translation distinction, hidden-source filtering before extraction, context
budget refusal and unsupported-query zero-call behavior. Full provider-free v1
and historical regressions remain the exact-head/main CI gates; all A01–A05
witnesses are reproduced into the same artifact. Historical frozen packages are
unchanged and remain replayable through their original runtime boundary; new
serialization carries its own source bindings instead of claiming old prompt bytes.

## Limits and next package

CORRECTNESS_VERIFIED / REPLAY_VERIFIED / UNTESTED / OPT_IN. No real provider calls
or spend in this slice. The answer witness is an explicit stub. Broad translation
correctness is not established. Source-local identity does not prove aliases
across documents. Authorized analyst visibility does not prove a character received
or understood information. Unprojected retrospective queries are rejected before
extraction. This is a bounded retained vertical slice, not general human cognition.

Wave A is complete at its engineering scope. **NEXT_READY: B01**, separating
public expression, private-belief interpretation, exposure, comprehension and
knowledge claims, with genuinely bounded higher-order propositions. Continue
construction after exact-main CI; preserve all historical efficacy dispositions.
