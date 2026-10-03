# Recovered A02 structural scope candidate

This local candidate is based on adopted main
`a588cbc45400bea5e51078d1447a48f437972033`, the authorized PR355 merge. All seven
exact-main checks passed, and its tree is
`cfa7aa14a903623f6882c643bbf23e7244f6a5f0`.

The earlier local candidate `39d805354dc5c4b447f895cfa3b82fdd1216379b` was lost
in a workspace rollback. Its A02 runtime change was reconstructed from recorded
tool history. Replacing only the newly adopted B04 file hash with the old base
hash reproduces the earlier candidate runtime SHA256 exactly:
`847b332d2c50a2bf4488f0eadf53176464993a8c416a1fb1e1542a9c5e95f5df`.
The two frozen fixture files also reproduce their original SHA256 hashes. Current
B04 remains byte-identical to adopted main. This is a source review candidate;
the runtime amendment and publication gates have not been advanced.

## Defect and bounded behavior

A02 previously counted quote, bracket and fence delimiters separately. Speech
inside fences/directions could receive `SOURCE_REPORT`; a delimiter inside a
closed fence could corrupt later scope. All colon bodies were masked, so an
explicit Narrator scene transition could not reach the outer narration channel.

One offset-preserving structural view now supplies both candidate containment and
scene-cue eligibility. Existing candidate matchers, fields, original quotations,
source versions, timestamps, source text and backend schema remain unchanged.
Existing narrator mental-report eligibility uses that same structural view; no
new mental predicate form or report channel is admitted.

`CONDITIONAL_OR_EMBEDDED` is an existing ambiguity category. It means this bounded
path cannot treat a span as an unconditional outer source report. Formatting
alone does not establish that a scene is hypothetical or that the described
speech never occurred. A fenced actual transcript is retained as embedded until
a separate explicit source-frame admission contract exists. No new source-frame
flag, semantic fact, world-truth claim or automatic actual-transcript promotion
is added here.

## Supported structural grammar

- Straight double quotes and opening/closing curly double quotes isolate their
  contents. Quoted brackets and inline backticks do not change the outer scope.
- Square brackets nest; a stray closing bracket cannot cancel a later opener.
- Backtick fences start on a line, after optional spaces/tabs, with at least
  three backticks and an optional label containing no backticks. They close on
  a line with at least the opener's backtick count and trailing whitespace only.
  Inside a fence, quote/bracket contents and inline backticks are inert.
- Unclosed admitted containers continue to EOF. Existing colon and script actor
  turns have their existing bounded bodies masked as a unit; a literal delimiter
  in such a body cannot contaminate a later turn.
- An unembedded exact `Narrator:` label exposes its body to the existing scene
  cue grammar. Actual character speech, quoted Narrator wording and contained
  labels cannot issue outer scene transitions.
- A recognized outer scene cue affects later candidates only. Ending structural
  containment does not itself cancel a hypothetical scene. An actual-scene
  resumption does not retroactively restore earlier candidates or override a
  later qualification. A cue cannot be assembled across masked source content.

This is not a general Markdown, screenplay or discourse parser. Escape syntax,
additional fence styles, narrator aliases, inch marks versus quotation marks,
and ambiguous malformed quotation recovery remain outside the declared grammar.
No automatic correction or source rewriting is performed.

## Engineering evidence and limits

The original 12-case proposal and nine additional boundary cases are recovered
byte-for-byte in `eval/a02_scope_proposal_v1.json` and
`eval/a02_scope_boundary_review_v1.json`; their prior PASS/FAIL observations remain
unchanged. The 19 reconstructed test methods assert all 21 expectations and paired
controls, original Unicode/CRLF offsets, actual quoted discussion, explicit
Narrator transitions, retained source payload and local scope derivation for a
simulated backend's minimal event object. A backend's conflicting SOURCE_REPORT
claim remains unverified and cannot create checked epistemic records. These are
engineering contracts, not model-selection or efficacy gold.

After recovery, 71 focused A02/narrator and adopted B04 tests pass. Pinned openai
and z3 dependencies were lost; polling their restoration process returned
`automatic approval review was cancelled`. Read-only inspection found no matching
process, no target directory and neither package importable; the original exit
result is unknown. No install retry or alternate retrieval was performed. Full
local gates remain pending those dependencies and the reviewed runtime amendment;
prior successful checks are not represented as current full validation.

B04 copy-cue selection must eventually require exact eligible source support
using adopted A02 scope. Its native payload/36,000-byte transport boundary remains
a separate integration gate. No new adapter, live answer validation, complete
flow or efficacy result is claimed by this source candidate.

All paid grants remain closed. This work makes zero provider calls and introduces
no live trigger, allowance, credential or provider change.
