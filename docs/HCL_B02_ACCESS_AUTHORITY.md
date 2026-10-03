# B02 source authority for access and visible expressions

The retained communication view now requires the shared A02 scope of the exact
source occurrence before a cue can establish access, before its literal target
can be used, and before an own expression can enter visible text. An actual
promise followed by a hypothetical receipt no longer establishes that its
conditions were received. An actual later receipt also cannot expose a preceding
hypothetical statement, including when the statement names the viewing actor.

The prior implementation matched raw access cues and prepared other statements
one line at a time. That lost outer scene scope. The new view applies its existing
per-line stripping once to the selected source prefix, obtains local A02 candidates
once, and maps each whole single-line occurrence back to its exact original
character offsets. Cross-line recovery and duplicate-text authority borrowing
are refused. Original proof quotations, visible event identity and audit shape
remain unchanged. Native A02 grammar and the D01 promise lifecycle are unchanged.

## Earlier snapshots and literal references

Only lines through the requested cutoff enter semantic preparation. Later source
material cannot establish access or alter an earlier snapshot. The empty prefix
stays empty. CRLF, tabs and edge whitespace retain their original proof text and
line position even though B02's existing syntactic representation strips them.

A structurally valid statement with unresolved or embedded scope stays in the
ordered statement table as an ineligible, untransmitted entry. Removing it would
make a named last-statement cue incorrectly fall back to older speech. Every cue
kind requires both eligible narrator authority and an eligible selected target:
positive receipt, nonreceipt, public availability and private addressing.
Own-expression admission enforces the same target authority.

This also preserves actual-scene resumption. A02 can mark the resumption marker
itself embedded at its start while restoring the scope of later statements. The
marker remains untransmitted with EXPOSURE_UNKNOWN, which establishes neither
access nor actuality. A later previous-statement or Narrator-last cue cannot
transmit that marker. There is no blanket narrator exemption.

Unsupported or ambiguous line forms and malformed access language still refuse.
All named speakers count toward the existing actor limit, including ineligible
entries. The 80-line, 4,000-character line, 64,000-character source and eight-actor
bounds remain unchanged. No source truncation, semantic provider or cache change
is introduced. A02 source scope describes report authority, not verified world
truth or a claim that every embedded transcript is hypothetical.

## Evidence and remaining work

The new tests were run before the change and recorded 23 failing assertions.
They cover the original D01 receipt counterexample, all cue types, nonactual own
speech, literal latest targets, actual resumption, repeated occurrences,
whitespace/CRLF, prior snapshots, actor limits and unsupported source forms.
Existing D01 tests preserve condition/receipt/acceptance/expectation distinctions,
withdrawal history and no later-receipt backfill. Current validation is recorded
separately; older reports, runtime pins and provider receipts remain immutable.

This is a prerequisite repair for the existing D01 lifecycle. It does not add a
D01 ordinary-entry adapter or establish live planner quality, private knowledge,
comprehension, moral obligation or model efficacy. Twelve bounded ordinary-entry
adapters remain available. B04 complete-evidence transport remains unresolved.
All paid campaigns remain closed and this repair makes no provider calls.
