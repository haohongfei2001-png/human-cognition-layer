# Adaptive source-bearing ordinary reader — v19

**CAPABILITY_DELTA:** ordinary reported dialogue now selects actual existing
B01/C01/C03 state before any optional provider extraction. Source-local checked
belief/goal/plan/opportunity composition reaches final input with the caller's
actual source ID and current revision. The same entry optionally admits one
source-anchored conditional translation for prose it cannot parse locally. No
manual correct private state or new ontology/module is required.

**Failure / simplest alternative:** the prior opt-in conditional adapter always
requested extraction when supplied a backend, including already parseable dialogue;
unsupported representations raised instead of preserving a complete-source reader.
The simplest alternative remains whole-source Base or zero-call local H reading.

**Mechanism:** `CognitionWorkspace.prepare_reader_entry` first runs the existing
literal reader on one complete authorized source. Actual checked treatment selects
that path. Otherwise, an explicitly supplied backend may make at most one translation
call. Only known representation coverage failures fall back to the whole original
local input; the raw extraction request/response/failure and absence are recorded.
Transport errors, budget overflow before extraction, missing/challenged/revised support
and unexpected implementation errors propagate, never retry. No semantic confidence
score or invented treatment. `answer_reader_entry` makes one final call, audits actual
primary source references and blocks bad or stale delivery without rewriting raw output.

**Boundaries:** analyst authorization is not character information access. Source
order is not calendar/receipt chronology; explicit statement snapshots require prior
source projection and are refused here. One source is one identity domain; cross-document
alias joins are refused. Another actor's opportunity cannot complete the focal plan.
Source quotes certify provenance only; nonliteral translations stay assumptions.
Private intention, world feasibility, moral truth and answer gain are not established.
Default and historical adapters remain available, and all four consumed exact archives,
source/gold/prompts/scorers/raw results and dispositions remain unchanged.

**Evidence:**12 new unit checks and89 focused integration/historical/archive checks
pass locally. [Authored witness](../reports/HCL_DEVELOPMENT_ADAPTIVE_READER_V19_WITNESS.json)
starts with ordinary typographic dialogue, performs actual B01/C01/C03 composition,
selects0 extraction despite an available backend, delivers an unchanged stub answer,
and invalidates after a local source correction. Tests cover optional real checker
state, negative treatment absence, raw fallback receipt, actor/time/source boundaries,
uncertainty, stale support, cache independence, transport failure and no retry.
Cloud exact-head/main certification gates merge.0 live calls/spend; utility remains
IMPLEMENTED_UNVALIDATED. No broad reading or efficacy claim.

**Simplification criterion:** remove optional extraction on task scopes where fresh
Base/H checks show no incremental benefit over complete-source reading, or costs/
false assumptions outweigh improvement. Do not alter individual gold or add rules
for consumed benchmark questions. Next freeze fresh legally usable development items
for strong Base vs this current adaptive H entry with same output contract, actual
source frames, bounded costs and explicit treatment-absence reporting. Final sealed
confirmation is separate and later; LongMemEval SEALED, leaderboard inactive.
