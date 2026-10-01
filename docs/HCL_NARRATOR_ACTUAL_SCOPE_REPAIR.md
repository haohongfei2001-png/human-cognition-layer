# Restore explicit actual narrator-report scope

After an imagined-scene declaration, the ordinary reader conservatively suppressed
later literal narrator mental reports even when an explicit narrator-level
`In reality,` or `In the actual scene,` transition had ended that scene. Existing
quoted speech could resume, but existing narrator-report handling could not.

This successor reuses the offset-preserving narration view introduced by the
qualified-speech repair. It restores only later, otherwise-eligible literal named
narrator reports. Spoken transition words, bracketed directions and fenced content
do not end an imagined scene. A later hypothetical qualifier suspends reports
again. Earlier hypothetical reports are never restored retroactively.

The original source and exact spans remain unchanged. A restored narrator report
is still a source attribution, not the named subject's public expression, private
belief or objective truth. It cannot supply a subject's direct plan-belief premise.
No prompt, provider, ontology, budget, source privacy or evaluation boundary changes.

## Verification

The twelve new tests cover explicit transitions, repeated transitions, prior
reports, quoted/colon/script transitions, stage directions and fences, subsequent
qualifiers, source revision invalidation, plan composition and a raw-preserving
stub answer. The test plan includes an explicit goal so that failure to satisfy a
belief condition is genuinely tested, rather than hidden by an inactive goal.

An initial unpublished test expected `NOT_AFFIRMED_NOT_NEGATION` for an absent
subject belief. The existing contract uses `UNKNOWN`; the former requires a
reported denial. The corrected test checks `UNKNOWN` and
`BELIEF_CONDITION_UNRESOLVED`, with no runtime change to plan semantics.

The six authored contrasts in `reports/HCL_NARRATOR_ACTUAL_SCOPE_WITNESS.json`
compare the exact previous merged semantic implementation at
`97b9bf187360860327ab573bae2217401b779ff0` against this successor. Only the explicit
actual-resumption case changes from zero to one narrator report. All sources are
complete, all private interpretations remain absent and no provider is constructed.
The witness validates the previous source hash and reconstructable runtime chain.

The separate successor amendment pins the previous qualified-speech report and
validator bytes, reconstructs its full runtime hash using the previous semantic
file hash, and continues validating the original budget and certified-v24 chain.
Historical reports and consumed archives are not rewritten. Current CI entrypoints
use the new validator; all historical drift assertions remain in place.

Local validation passes 1,172 provider-free v1 tests, 176 historical regressions,
36 consumed-archive tests and the full existing integration witness sequence.
Hosted exact-head checks and review are recorded separately in the PR.

## Limits

This remains bounded syntactic coverage, not general discourse interpretation.
Literal report blocks must still satisfy all pre-existing qualification and
structure checks. No model answer improvement, native-task utility or version
ranking is established. SID001 authorization remains closed and consumed; this
work makes zero live calls. LongMemEval remains sealed and final confirmation
remains separate from development tests.
