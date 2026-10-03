# Explicit final-answer citation contract

## Evidence and scope

The closed [planner-contract smoke](HCL_PLANNER_CONTRACT_SMOKE.md) naturally
selected and executed G05, but its returned final answer was rejected. Both
original quotations, source IDs, versions and offsets matched; citation objects
contained an unsupported `end` field. Internal prepared-state anchors expose that
field, while the answer validator accepts a narrower object schema. The shared
answer policy named the top-level fields without disclosing this element schema.

The original failed answer remains private and unchanged. The receipt, scalar
closure, grants and all prior evidence stay pinned. A separate copied-object
structural probe isolated the mismatch; it did not repair or reclassify the live
result. No model output, including its private answer text, is copied into these
new tests.

This amendment only appends truthful contract guidance to the shared final-answer
policy in `hcl/cognition/reader_entry.py`. The ordinary reader and UniversalHCL
both receive it. Runtime AST outside that policy constant and the complete
citation validator are unchanged. No normalization, hidden field removal, retry,
new provider call, changed model limit, forced G05 routing or parser repair is added.

## Declared output shape

The four top-level fields remain `answer`, `source_citations`, `uncertainty`, and
`assumptions`; the policy requests string prose fields. Citations are an array of
at most 32 entries. The canonical object contains `source_id` and `quote`, with
only optional `version` and `start`. `end`, span IDs, ordering metadata and other
internal anchor fields are not output citation fields.

Use a supplied original source ID and an exact, nonblank, contiguous quotation
of at most 4000 characters. Optional version is the matching supplied integer,
not a boolean. Omit an unknown start. A non-null start is a nonnegative integer
in zero-based Unicode character positions, not bytes or UTF-16 code units.
Repeated quotations should carry their correct exact offset. The validator's
legacy single-source quote-string form and empty array remain accepted; multiple
sources require explicit source identity. Source-free analysis requires an empty
citation array and retains its explicit unsourced-knowledge limitation.

## Existing validator semantics stay intact

The policy recommends exact original text and exact offsets. This does not
change the validator's compatibility behavior:

- An exact match at supplied `start` is used. Otherwise a uniquely located exact
  quote may relocate; a wrong nonnegative offset alone does not guarantee failure.
- If no exact match exists, unique whitespace-layout-only location may succeed.
  The audit retains original/submitted text and labels that location mode.
- Repeated exact quotes need a correct exact offset. Repeated whitespace-layout
  alternatives are still ambiguous when the submitted text is not exact, even
  with a proposed start. Exact matches take precedence over layout alternatives.
- Stale versions, unknown IDs, booleans/noninteger offsets, unsupported fields,
  fabricated text and noncontiguous word combinations remain rejected.
- The validator's existing non-overlapping match enumeration is unchanged. This
  amendment is not a stronger semantic, uniqueness, world-truth or answer-quality
  certificate. Historical loose top-level reader audit behavior is not tightened.

No rejected answer is automatically rewritten or accepted. The original raw
answer remains separate from the audit; UniversalHCL still fails delivery on an
invalid source citation.

## Engineering checks and historical integrity

Authored tests cover policy delivery to both actual answer interfaces, exact and
multi-source citations, Unicode offsets, repeated quotes, unique relocation,
whitespace-only behavior, strict fields/version types, fabricated/noncontiguous
text, source-free results and unchanged rejected raw responses. Complete final
reader messages are measured after the appended policy; exact-fit budget passes,
one character short refuses before the answer call, without truncation.

The new amendment imports every transitive historical byte pin, validates the
consumed archive chain, and reconstructs the exact prior whole-runtime digest by
restoring only the previous reader-policy file hash. A frozen non-policy byte hash
also rejects any reader change outside the one literal policy constant; it does
not depend on Python-version-specific AST dump formatting. Earlier live-tree validators
mask different paths, so they are preserved rather than rewritten or monkeypatched.
Current witness imports advance to the new amendment; historical executors,
packages, closed grants, request fixtures and independent challenge checker remain
on their original runtime. Later historical checks must use that recorded runtime.

This is provider-free interface completeness. No live model-compliance improvement,
selection generalization, answer gain or efficacy has been established. Campaign
accounting remains eleven calls / US$0.69163776 full reservations; this change
authorizes zero additional calls and does not reuse the one unallocated call.
