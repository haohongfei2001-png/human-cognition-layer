# Conditional reader context transport — v17

**CAPABILITY_DELTA:** the same complete original text and existing conditional
B01/C01/C03 state fit a smaller user-context budget, using exact reversible aliases
for repeated opaque identifiers. This is integration capacity/cost correctness;
answer utility remains IMPLEMENTED_UNVALIDATED/INCONCLUSIVE.

The simplest alternative is original complete-text reading. The opt-in conditional
path now accepts `compact_context=True`: only repeated full opaque IDs in derived
state/bindings become short aliases. The table is explicitly conditional, never
quotable source or new evidence. Original text, query, actors, conditions, negation,
time/access unknowns, normative assumptions, checked state and revision dependencies
are untouched. Expansion must exactly equal the original payload. Aliases that
collide with existing meanings fall back; invalid/unknown/duplicate tables or key
collisions fail. Payloads that would grow are kept unencoded. JSON whitespace is
minified only in the opt-in path; default/typed legacy wire remains unchanged.

[Authored provider-free witness](../reports/HCL_DEVELOPMENT_READER_COST_V17_WITNESS.json):
user context 25888→22913 characters (11.49% smaller); serialized complete
messages 30876→28390 bytes including reference policy. Same operation IDs, original
source and expanded state; valid original-quoted stub response preserved with one
final call. A 22913-character user-context budget now fits this whole state, whereas
the previous representation does not. This is an authored capacity witness, not
actual token measurement or provider saving/answer gain claim.

11 new correctness checks cover exact round trip, literal source, original quote
boundary, default compatibility, post-encoding capacity, revisions/composition,
negative inference, unauthorized access/source identity, namespace collisions and
corrupt references.114 combined focused/current/historical/archive checks pass
locally; exact-head/main cloud CI remains the merge gate. Source citation location
still does not certify meaning, narrator-as-speech or private/world/moral truth.

Simplify/remove this optional encoding if fresh checks show comprehension harm or
no practical cost value. No case-specific rule, new ontology or cognitive module;
0 provider calls/spend, no rerun/rescore of DRC001/002/DRE001. Chained v17 amendment
preserves historical frozen runtimes, receipts and dispositions. LongMemEval SEALED.
Next independently freeze fresh public development tasks/config/scorer and compare
strong Base/current HCL, including actual preparation overhead and missing treatment.
Final reviewer/source perfection does not gate daily Development Reality Checks.
