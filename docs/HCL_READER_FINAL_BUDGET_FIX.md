# Reader final-context budget enforcement

This main-based candidate retains the complete v24 message content and ordinary
reader policy. It contains no additional inference instruction or semantic repair.
The sole runtime file changed is `hcl/cognition/reader_entry.py`.

The old answer adapter checked preparation against the caller's character limit,
then appended a fixed JSON-answer instruction without checking the final request.
On the checked-state regression, preparation occupies 18,053 serialized Unicode
characters and the actual final request occupies 18,290. The old adapter invokes
the answer backend despite a configured limit of 18,053.

The candidate reserves the exact 237-character appended instruction, including its
JSON list separator, checks selected messages against the remaining delivery
allowance, and checks the complete final request before the answer call. The old
instruction is reused verbatim. Standalone preparation keeps its original behavior.

The original intermediate parser ceiling stays unchanged. A regression with an
unexecuted intermediate of 2,226 characters produces a minimized actual final wire
of 739 characters and still succeeds cold and warm at the 2,226-character limit.
Reducing the entire parser ceiling would unnecessarily reject that legal request.

When the local delivered wire already cannot fit, the candidate refuses before
optional extraction and before the answer call. This is not a guarantee that every
budget failure costs zero extraction: a conditional representation's size depends
on the single explicitly opted-in extraction response. Its oversized selected wire
is rejected before the final answer, without retrying or replacing the raw result.

The earlier v25 prepared-only example depended partly on its added instruction
size and is not used as evidence of the same v24 spend issue. Here, the independently
reproduced defect is the missing final request limit, not a claim of measured invoice
savings or answer improvement.

Provider-free acceptance compares current preparation receipts, source/checker
messages, translation requests, final messages, raw answers and citation audits with
the Git-certified v24 reader across no-state, checked-state, translation and fallback
fixtures. All sufficient-budget message bytes remain equal. Historical runtime
pins stay immutable; a separately named budget amendment permits changes only to
the reader-entry runtime file. No paid model, benchmark answer, source rubric or
experimental result is changed by this candidate.
