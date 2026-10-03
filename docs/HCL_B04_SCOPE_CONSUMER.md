# B04 exact copy-cue consumption

B04 previously recognized a copy line again from raw text after semantic
preparation. Even when A02 correctly labelled that occurrence embedded or
hypothetical, B04 created a fresh raw-source relation and joined the reports.
This repair uses the existing single preparation to admit the exact cue.

An eligible cue must be a currently supported, bounded-literal `SPEECH_REPORT`
with `speaker_surface` Narrator and `assertion_scope` SOURCE_REPORT. Its source
ID, source revision, complete source-line bounds and original quotation must
match the occurrence B04 is considering. Narrator is a source channel, so it is
not required to have a fictional actor candidate list of `[Narrator]`.

Full-line matching preserves original trailing spaces and the carriage return
in CRLF. The existing copy grammar and A02 matchers are unchanged. A raw line
with leading indentation has no eligible A02 event under the current matcher;
it receives an occurrence-specific diagnostic and cannot borrow another
occurrence's event. Embedded, unmatched, ambiguous, stale, unverified, withdrawn
or challenged candidates cannot authorize a copy relation. The original reports
remain separate, with independence still unknown.

## Provenance and retraction

Every relation includes its eligible cue candidate ID and depends conjunctively
on that candidate, both antecedent report expressions and original source
support. A raw-source claim alone cannot support the relation. Identical repeated
copy cues have distinct relation identities because their source occurrences
have distinct candidate IDs; they cannot create duplicate family obligations or
act as alternate support for the same relation after one cue is withdrawn.

The PR355 rule remains: resolve the literal latest eligible named speech before
checking its mental content. A later unsupported utterance still rejects an
eligible copy request instead of reviving an older parsed belief. No additional
semantic preparation, model call, grammar, source/report budget or adapter is
introduced.

## Evidence and remaining work

Ten new test methods cover the two frozen scope failures, literal/CRLF controls,
real versus embedded resumption, identical text at different locations, missing
and malformed candidate authority, and cue/antecedent withdrawal. Existing
literal-last-statement, copy-chain, conflict, access and budget tests remain.
Independent review also checked repeated preparation and challenge propagation.

The original blocker reports, their failing observations, prior A02 recovery and
validation records remain immutable. A new receipt records current outcomes.
The new amendment preserves all113 prior pins and adds eight historical records,
for121 pinned artifacts. Only `prepare_reports` changes in runtime; restoring its
file hash reproduces adopted A02 runtime exactly.

This closes the two recorded B04 cue-consumption failures. It does not prove all
provenance semantics or establish private belief, independent support, model
selection, final answer validity or efficacy. The retained-state transport gate
and ordinary-entry adapter remain separate. All paid grants stay closed.
