# B04 literal last-statement reference repair

The adopted B04 contract resolves a reported copy relation between preceding
explicit utterances. The prior implementation filtered to parsed mental reports
before resolving “last statement”. A later nonmental utterance, or an unsupported
modal statement, was skipped and an older belief was incorrectly linked.

The five-case authored baseline fixture is frozen in
`eval/b04_copy_reference_counterexamples_v1.json` with SHA256
`60167873ae475a197058b470a35ee813fc882db1475d7e8d58ed3d6189b3b021`.
It records the prior incorrect family merges and direct/unrelated-actor controls.
These are engineering reference tests, not model outputs or efficacy evidence.

`prepare_reports` now uses the same single A02 preparation for both B01 checks and
literal reference selection. It selects the latest preceding eligible named
speech candidate before looking for its supported mental expression. If the
latest utterance is nonmental or unsupported, the copy cue rejects instead of
falling back to an older parsed belief. Narrator attributions are not a subject's
own utterance. Existing inline conditional/embedded A02 labels remain exclusions;
quoted inner actors are not independent speakers. No alias, new grammar, extra
semantic extraction, provider call or source/report budget is added.

Existing direct copies, source-local conflict, uncertainty, dependency withdrawal
and revision semantics remain. Nine new tests cover the frozen failures, deeper
unsupported copier content, inline conditionals, quoted examples, narrator
attribution, exactly one semantic preparation, hidden sources and revisions. The
14 existing B04 tests remain unchanged.

## Explicit unresolved scope prerequisite

The broader copy-cue scope defect is not repaired here. A cue inside a fenced
example or after a narrator-labelled hypothetical declaration can still be parsed
from the raw line and merge two families. An initial diagnostic assumption that
A02 already labelled these nonactual was incorrect: the exact default A02 probe
returned `SOURCE_REPORT` for both. A label-only check therefore is not protection.
The existing narrator scene helper does not supply a complete reusable per-span
classifier for this path. No unreviewed parser rewrite is included.

The same source-scope prerequisite also affects prospective C04 integration:
a feeling utterance inside a fenced example currently enters its reported-emotion
channel. Actual emotion still remains unknown, but the report scope is wrong.
Exact authored failing inputs and observed/expected results are frozen in
`reports/HCL_RETAINED_ENTRY_SCOPE_BLOCKERS.json`; all three remain UNRESOLVED_FAIL.
These observations block claiming a safely generalized B04 or C04 adapter ready.
Broader A02 scope repair requires separate frozen counterexamples and review.

B04's six-line native message also measured 42,312 UTF-8 bytes, above the current
36,000-byte transport limit. Its native assessment alone was 4,811 bytes, but using
that instead of the full evidence message requires a separately reviewed projection
and dependency contract. No truncation, transport expansion or B04 adapter is added.

Historical reports, failed paid answers, grants and runtime pins remain unchanged.
The new amendment restores only this module's prior file hash to the exact previous
runtime and verifies all code outside the preparer and its explicit import switch.
This is a bounded retained-implementation repair, with no live validation upgrade.
